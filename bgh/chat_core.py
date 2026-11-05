"""Nucleo do chat: a mesma logica para a tela fixa (tui.py) e o modo classico.

Comandos com barra (/ajuda, /nov, /modelo...), atalhos @ e /, turno do modelo e
menu de licenca vivem aqui. A saida passa por um "sink", assim cada tela decide
como mostrar (rich no modo classico; area de texto na tela fixa).
"""

import datetime
import getpass
import os
import re
import traceback
from pathlib import Path

from rich.console import Console

from .agent import Agent, STOPPED_NOTE
from .approvals import Gate
from .config import CONFIG_PATH, SESSION_FILE, ConfigError, load_config, save_config, sync_profile
from .llm import LLM, LLMError, LLMRateLimitError
from .setup_wizard import CHARS_POR_TOKEN, FOLGA_LEITURA
from .tools import files as files_mod

LINE = "-" * 46  # separador visual (ASCII puro; nao depende de unicode no terminal)


def log_error(exc: BaseException, contexto: str) -> None:
    """Guarda o detalhe tecnico no arquivo; a tela ve apenas frase humana.

    Publico do TEO e leigo: traceback python na tela assusta e nao ajuda ninguem.
    A pilha completa vai para ~/.bgh/erro.log, onde quem da suporte consegue ler.
    """
    try:
        with open(CONFIG_PATH.parent / "erro.log", "a", encoding="utf-8") as fh:
            fh.write("\n===== " + datetime.datetime.now().isoformat(timespec="seconds")
                     + " | " + contexto + "\n")
            fh.write(type(exc).__name__ + ": " + str(exc) + "\n")
            fh.write(traceback.format_exc())
    except OSError:
        pass  # registrar nunca e emergencia; falhar aqui nao pode derrubar o chat


def set_window_title(texto: str) -> None:
    """Da nome a janela do terminal ('TEO Agent'); ajuda a achar no Windows."""
    try:
        if os.name == "nt":
            import ctypes

            ctypes.windll.kernel32.SetConsoleTitleW(texto)
        else:
            print("\x1b]0;" + texto + "\x07", end="", flush=True)
    except Exception:  # noqa: BLE001 - titulo e cortesia, nunca necessidade
        pass


def maximize_window() -> None:
    """Deixa a janela do TEO maximizada desde a abertura.

    Motivo: em janela estreita o rodape perde pedacos (o medidor de contexto e as
    teclas brigam pelo mesmo espaco) e o publico do TEO nao vai ficar arrastando
    borda de janela. Windows tem API propria (funciona de verdade); Linux/macOS
    recebem a sequencia padrao do xterm e o terminal que nao conhece simplesmente
    ignora. Sempre antes de a tela desenhar: redimensionar com a tela viva
    bagunca o layout.
    """
    try:
        if os.name == "nt":
            import ctypes

            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        else:
            print("\x1b[9;0t", end="", flush=True)  # xterm: maximizar janela
    except Exception:  # noqa: BLE001 - cortesia, nunca necessidade
        pass


def prepare_console() -> None:
    """Nome na janela + tela maximizada: chamado ANTES da primeira tela."""
    set_window_title("TEO Agent")
    maximize_window()


def ctx_parts(cfg: dict, usage: dict) -> tuple[str, str]:
    """(medidor, extra) separados: a tela decide se o extra cabe na janela.

    Funcao pura (le so cfg/usage): testavel sem instanciar o ChatCore.
    """
    txt = (f"contexto: {usage['pct']}% de {usage['budget']} chars "
           f"({usage['messages']} mensagens)")
    extra = ""
    srv = cfg.get("server_context_tokens")
    if isinstance(srv, (int, float)) and srv > 0:
        entrega_chars = int(srv * CHARS_POR_TOKEN * FOLGA_LEITURA)
        if entrega_chars > usage["budget"]:
            extra = f" | teto; o servidor entrega {int(srv):,} tokens".replace(",", ".")
    return txt, extra


def md_clean(text: str) -> str:
    """Tira ruido de markdown para leitura simples (idoso/crianca le em texto puro).

    Remove ** e cercas de codigo, cabecalhos # e linhas '---'; normaliza marcadores
    de lista para '- '. As quebras de linha do modelo sao PRESERVADAS (a tela as
    mostrava esmagadas, virando um bloco corrido).
    """
    text = text.replace("**", "").replace("```", "")
    text = re.sub(r"^#{1,6}[ ]?", "", text, flags=re.M)
    text = re.sub(r"^[ \t]*[*\u2022][ \t]+", "  - ", text, flags=re.M)
    text = re.sub(r"^[ \t]*-{3,}[ \t]*$", "", text, flags=re.M)
    return text

PURPLE = "#af87ff"  # roxo suave: usado SO nos comandos da ajuda

# O gatinho de abertura: o harness se chama TEO (nome do gato preto do autor)
CAT_ART = (
    '     /\\_/\\',
    '    ( o.o )',
    '     > ^ <',
    '      TEO',
)

HELP_SECTIONS = [
    ("Atalhos rapidos (nao precisam de permissao):", [
        ("/", "lista a pasta atual (pastas e arquivos)"),
        ("/ <pasta> ou /ls <pasta>", "lista uma pasta especifica"),
        ("@", "lista so os arquivos da pasta atual"),
        ("@<arquivo>", "anexa um arquivo; depois faca sua pergunta sobre ele"),
    ]),
    ("Parar e reler:", [
        ("CTRL+C ou ESC durante a resposta", "para de responder na hora (igual ao Hermes)"),
        ("digitar ENTER durante a resposta", "avisa o turno em andamento; o modelo le na proxima rodada"),
        ("Roda do mouse ou PageUp/PageDown", "reler o texto que subiu na tela"),
        ("CTRL+C com a linha vazia", "fecha o TEO"),
        ("Seta para cima / para baixo", "repete o que voce ja digitou (historico guardado)"),
    ]),
    ("Comandos:", [
        ("/ajuda", "esta lista"),
        ("/nov", "conversa nova (limpa contexto; memoria e skills continuam)"),
        ("/mem <texto>", "grava uma preferencia sua na memoria permanente"),
        ("/modelo", "lista os modelos do servidor; /modelo <nome ou numero> troca (fica salvo)"),
        ("/provedor", "lista os provedores; /provedor <nome ou numero> troca na hora (fica salvo)"),
        ("/pensamento liga|desliga", "mostra ou esconde o pensamento na tela; avancado (nivel "
                                     "enviado ao servidor): auto off minimum low medium high xhigh max ultra"),
        ("/palco liga|desliga", "mostra ou esconde a trilha do pedido durante a resposta (so na tela fixa)"),
        ("/ctx", "medidor do contexto; /ctx <numero> define o limite e fica salvo "
                 "(ex.: /ctx 65000; aceita 65k, 65.000, 65 mil)"),
        ("/configurar", "conserta ou cria um provedor sem sair do TEO (o mesmo assistente do 'bgh setup')"),
        ("/doctor", "diagnostico da conexao e da maquina, na propria tela"),
        ("/atualizar", "confere se ha versao nova no GitHub; se houver, pede sua licenca e instala"),
        ("/skills", "lista as skills conhecidas"),
        ("/sair", "encerra"),
    ]),
]


def help_lines() -> list[list]:
    """Ajuda em pedacos: o COMANDO em roxo suave, a explicacao na cor normal."""
    out: list[list] = []
    for header, pairs in HELP_SECTIONS:
        out.append([(header, None)])
        width = max(len(c) for c, _ in pairs) + 3
        for cmd, desc in pairs:
            color = PURPLE if cmd.startswith(("/", "@")) else None
            out.append([(f"  {cmd:<{width}}", color), (desc, None)])
        out.append([("", None)])
    return out


def build_approval_options(allow_always: bool) -> tuple[list[str], list[str]]:
    """Menu numerico simples para o usuario; por dentro mapeia para o fluxo Hermes o/s/a/d."""
    options = ["Sim, fazer desta vez", "Sim, e nao perguntar de novo nesta conversa"]
    codes = ["o", "s"]
    if allow_always:
        options.append("Sim, e sempre permitir isso depois")
        codes.append("a")
    options.append("Nao / cancelar")
    codes.append("d")
    return options, codes


def parse_approval_choice(raw: str, codes: list[str], default: str = "d") -> str:
    """Numero digitado vira o codigo; Enter sozinho ou algo invalido = 'default' (falha fechada)."""
    raw = (raw or "").strip()
    if raw.isdigit() and 1 <= int(raw) <= len(codes):
        return codes[int(raw) - 1]
    return default


def parse_budget(raw: str) -> int | None:
    """Aceita '65000', '65k', '65.000', '65 mil' e devolve o numero de caracteres.

    None quando nao e numero ou esta fora do intervalo util (8000 a 1000000).
    """
    texto = str(raw or "").strip().lower().replace(" ", "")
    if not texto:
        return None
    multiplicador = 1
    for sufixo in ("mil", "k"):
        if texto.endswith(sufixo):
            multiplicador = 1000
            texto = texto[: -len(sufixo)]
            break
    texto = texto.replace(".", "").replace(",", "")
    if not texto.isdigit():
        return None
    valor = int(texto) * multiplicador
    return valor if 8000 <= valor <= 1000000 else None


class ConsoleSink:
    """Affiche classica (rich), usada quando nao ha tela fixa."""

    def __init__(self):
        self.console = Console()

    def line(self, text: str, style: str | None = None) -> None:
        self.console.print(text, style=style or "", markup=False)

    def parts(self, segments: list) -> None:
        """Uma linha montada em pedacos com cores diferentes (ex.: ajuda)."""
        for text, style in segments:
            self.console.print(text, end="", style=style or "", markup=False)
        self.console.print("")

    def sep(self, title: str | None = None) -> None:
        self.console.print(f"\n{LINE}")
        if title:
            self.console.print(title, style="bold", markup=False)
            self.console.print(LINE)

    def border(self) -> None:
        """Divisor '=' ate a borda da tela (abre e fecha blocos importantes)."""
        width = max(20, int(getattr(self.console, "width", 0) or 46))
        self.console.print("=" * width, style="dim", markup=False)

    def thinking(self, text: str) -> None:
        self.console.print(text, end="", style="#808080 italic", markup=False)

    def answer(self, text: str) -> None:
        self.console.print(text, end="", style="white", markup=False)

    def tool_event(self, name: str, preview: str) -> None:
        self.console.print(f"> {name}: {preview}", style="dim", markup=False)

    def status(self, text: str) -> None:
        pass  # sem barra de status no modo classico

    def read_prompt(self) -> str:
        return self.console.input("\n[bold cyan]voce> [/bold cyan]")

    def ask_line(self, prompt: str, default: str = "", secret: bool = False) -> str:
        """Pergunta de texto livre (assistente do /configurar); Enter sozinho = padrao."""
        fn = getpass.getpass if secret else input
        label = f"{prompt}{f' [{default}]' if default else ''}: "
        try:
            raw = fn(label).strip()
        except (EOFError, KeyboardInterrupt):
            return default
        return raw or default

    def ask_approval(self, label: str, detail: str, allow_always: bool) -> str:
        options, codes = build_approval_options(allow_always)
        self.console.print()
        self.console.print("== O TEO precisa da sua licenca ==", style="bold yellow", markup=False)
        self.console.print(label, style="bold", markup=False)
        for ln in str(detail).splitlines()[:8]:
            if ln.strip():
                self.console.print(f"   {ln}", markup=False)
        self.console.print("O que voce quer fazer?", markup=False)
        for i, opt in enumerate(options, start=1):
            self.console.print(f"  [{i}] {opt}", markup=False)
        try:
            raw = input(f"  Digite o numero (se so Enter, vale {len(options)}): ")
        except (EOFError, KeyboardInterrupt):
            return "d"
        return parse_approval_choice(raw, codes)

    def ask_choice(self, title: str, label: str, options: list) -> str:
        """Menu numerico de escolha (ex.: nivel de pensamento); Enter = opcao 1."""
        self.console.print()
        self.console.print(f"== {title} ==", style="bold cyan", markup=False)
        self.console.print(label, markup=False)
        for i, opt in enumerate(options, start=1):
            self.console.print(f"  [{i}] {opt}", markup=False)
        try:
            raw = input(f"  Digite o numero (Enter = {options[0]}): ")
        except (EOFError, KeyboardInterrupt):
            return options[0]
        return parse_approval_choice(raw, options, default=options[0])


class ChatCore:
    """Logica de chat igual nas duas telas. submit() roda um turno completo."""

    def __init__(self, cfg: dict, sink, llm: LLM | None = None):
        self.cfg = cfg
        self.sink = sink
        self.llm = llm or LLM(cfg)
        self.gate = Gate(cfg, sink.ask_approval)
        self.agent = Agent(cfg, self.llm, self.gate, on_event=sink.tool_event)
        self.model_list: list[str] = []
        self.pending_attach: str | None = None
        # Estado do streaming: pensamento e resposta em blocos separados.
        self.st = {"thinking": False, "resposta": False}
        self._pend = ""  # '*' do fim de um pedaco aguarda o proximo ('**' dividido)
        self.agent.on_reasoning_delta = self._on_reasoning
        self.agent.on_text_delta = self._on_text
        # Avisos do cliente (espera longa, fallback sem streaming) viram linha na tela:
        # espera nunca pode ser lida como programa travado.
        self.llm.on_note = lambda texto: self.sink.line(texto, style="yellow")
        # Avisos do agente (compactando, contexto estourou) seguem o mesmo canal.
        self.agent.on_note = lambda texto: self.sink.line(texto, style="yellow")
        # Cada chamada do modelo (rodada de ferramenta ou fechamento) comeca bloco
        # novo: sem isso o cabecalho 'resposta' ficava preso da rodada anterior e a
        # resposta final saia colada no bloco de pensamento.
        self.agent.on_round_start = self._reset_stream_state
        # Contador de tokens do pedido vai para a tela (palco mostra por etapa),
        # quando a tela sabe desenhar isso (a tela fixa sabe; o modo classico nao).
        if hasattr(self.sink, "on_usage"):
            self.agent.on_usage = self.sink.on_usage
        # Abertura: se o teto gravado pertence a outro servidor/modelo, re-sonda
        # antes de qualquer barra ser desenhada (barra nunca mostra numero emprestado).
        self._refresh_server_context(troca=False, render=False)

    # ----- streaming -> sink ---------------------------------------------------
    def _reset_stream_state(self) -> None:
        """Cabecalhos de pensamento/resposta valem por chamada do modelo, nao por turno."""
        self._flush_pend()
        self.st = {"thinking": False, "resposta": False}

    def steer(self, text: str) -> None:
        """Mensagem digitada durante o processamento: vai ao modelo na proxima
        fronteira de rodada (estilo Hermes), sem derrubar o turno."""
        self.agent.steer(text)

    def _refresh_server_context(self, *, troca: bool, render: bool) -> None:
        """Assume o teto de contexto publicado pelo servidor do provedor/modelo atual.

        Regra pedida pelo dono do projeto: a barra mostra o que o servidor entrega
        AGORA, nunca o numero gravado por um servidor/modelo anterior. Troca de
        provedor ou de modelo sempre re-sonda. Na abertura, re-sonda so quando o
        numero gravado pertence a outro servidor/modelo (estado estavel nao paga
        rede nem atrasa a tela).
        """
        chave_atual = f"{self.cfg.get('base_url', '')}|{self.cfg.get('model', '')}"
        if not troca and self.cfg.get("server_context_key") == chave_atual:
            return  # o numero gravado e exatamente o deste servidor com este modelo
        probe = getattr(self.llm, "discover_context", None)
        tokens = None
        if probe is not None:
            try:
                tokens = probe()
            except Exception:  # noqa: BLE001 - sondagem nunca derruba o comando
                tokens = None
        if isinstance(tokens, (int, float)) and tokens > 0:
            self.cfg["server_context_tokens"] = int(tokens)
            self.cfg["server_context_key"] = chave_atual
            entrega = int(int(tokens) * CHARS_POR_TOKEN * FOLGA_LEITURA)
            budget = int(self.cfg.get("context_budget_chars", 156000))
            if entrega < budget:
                # Teto real menor que o orcamento: comprimir mais cedo evita turno
                # quebrando no meio por contexto (mesma conta do assistente de setup).
                self.cfg["context_budget_chars"] = max(8000, entrega)
                for dono in (self.agent, self.llm):
                    dono_cfg = getattr(dono, "cfg", None)
                    if dono_cfg is not None and dono_cfg is not self.cfg:
                        dono_cfg["context_budget_chars"] = self.cfg["context_budget_chars"]
            save_config(self.cfg)
        elif self.cfg.pop("server_context_key", None) is not None or troca:
            # Sem publicacao nova: numero de outro servidor/modelo nao pode mentir na barra.
            self.cfg.pop("server_context_tokens", None)
            save_config(self.cfg)
        if render:
            self.print_ctx()

    def _on_reasoning(self, chunk: str) -> None:
        if not self.cfg.get("show_thinking", True):
            return  # pensamento desligado na tela: o modelo pode reasoning, mas nao pintamos
        if not self.st["thinking"]:
            self.sink.sep("pensamento do modelo (raciocinio; pode ignorar e ir direto para a resposta)")
            self.st["thinking"] = True
        self.sink.thinking(chunk)

    def _on_text(self, chunk: str) -> None:
        if not self.st["resposta"]:
            if self.st["thinking"]:
                self.sink.line("")
                self.st["thinking"] = False
            self.sink.sep("resposta")
            self.st["resposta"] = True
        buf = self._pend + chunk
        trail = len(buf) - len(buf.rstrip("*"))
        self._pend = buf[len(buf) - trail:] if 0 < trail <= 2 else ""
        body = buf[:len(buf) - len(self._pend)]
        if body:
            self.sink.answer(md_clean(body))

    def _flush_pend(self) -> None:
        if self._pend:
            self.sink.answer(md_clean(self._pend))
            self._pend = ""

    # ----- janela de contexto ---------------------------------------------------
    def print_ctx(self) -> None:
        usage = self.agent.ctx_usage()
        limite_pct = self.agent._compress_pct()  # o aviso e a compactacao no mesmo ponto
        core, extra = self._ctx_parts(usage)
        txt = core + extra
        if hasattr(self.sink, "set_ctx"):
            # tela fixa: o medidor mora na ULTIMA linha da tela, nao no historico;
            # o 'extra' so aparece quando cabe inteiro (a tela decide a ordem de corte)
            self.sink.set_ctx(core, usage["pct"], limite_pct, extra=extra)
            if self.agent.last_compressed:
                self.sink.line("Contexto compactado: as partes antigas viraram um resumo.", style="dim")
            elif usage["pct"] >= limite_pct:
                self.sink.line("Contexto enchendo; sera compactado na proxima rodada pesada.", style="dim")
            return
        color = "green" if usage["pct"] < 50 else ("yellow" if usage["pct"] < 80 else "red")
        self.sink.sep()
        self.sink.line(txt, style=color)
        if self.agent.last_compressed:
            self.sink.line("Contexto compactado: as partes antigas viraram um resumo.", style="dim")
        elif usage["pct"] >= limite_pct:
            self.sink.line("Contexto enchendo; sera compactado na proxima rodada pesada.", style="dim")

    def _ctx_parts(self, usage: dict) -> tuple[str, str]:
        return ctx_parts(self.cfg, usage)

    def _ctx_footer_text(self, usage: dict) -> str:
        """Texto do rodape; quando o provedor entrega mais que o orcamento, avisa
        que o numero exibido e o teto de leitura do TEO, nao o limite do servidor."""
        core, extra = ctx_parts(self.cfg, usage)
        return core + extra

    def banner(self) -> None:
        set_window_title("TEO Agent")  # janela com nome: mais facil de achar (no Windows vale mais)
        self.sink.line("")
        for art_line in CAT_ART:          # o gatinho TEO abre a tela
            self.sink.line(art_line)
        self.sink.line("")
        self.sink.border()   # abre o bloco de boas-vindas
        self.sink.line("TEO - agente local (comandos seguros rodam direto; perigosos pedem sua licenca)",
                       style="bold")
        self.sink.line(f"Modelo: {self.cfg['model']} em {self.cfg['base_url']} "
                       f"(thinking: {self.cfg.get('thinking', 'auto')})", style="cyan")
        if SESSION_FILE.exists():
            self.sink.line("Conversa anterior retomada. /nov para comecar do zero.", style="dim")
        for seg_line in help_lines():
            self.sink.parts(seg_line)
        self.sink.border()   # fecha o bloco de boas-vindas

    def _list_models(self) -> None:
        try:
            self.model_list = self.llm.list_models()
            if not self.model_list:
                self.sink.line("O servidor nao publica lista de modelos.")
            em_uso_marcado = False
            for i, m in enumerate(self.model_list, start=1):
                marca = " (em uso)" if m == self.cfg["model"] else ""
                if marca:
                    em_uso_marcado = True
                self.sink.line(f"  {i}. {m}{marca}")
            if self.model_list and not em_uso_marcado:
                # Provedores as vezes renomeiam IDs: sem igual exato, a lista ficaria
                # sem marca nenhuma e o usuario acharia que o medidor esta quebrado.
                self.sink.line(f"  (modelo em uso: {self.cfg['model']}; nao apareceu na lista "
                               "do servidor - escolher um numero acima alinhara o nome)",
                               style="dim")
        except LLMError as exc:
            log_error(exc, "lista de modelos")
            self.sink.line("O servidor nao respondeu a lista de modelos agora. Tente de novo "
                           "em instantes (o detalhe tecnico foi guardado no erro.log).",
                           style="yellow")
        except Exception as exc:  # noqa: BLE001 - servidor estranho nunca derruba a tela
            log_error(exc, "lista de modelos")
            self.sink.line("O servidor mandou uma lista que o TEO nao conseguiu ler. "
                           "Rode /doctor para ver a conexao (detalhe no erro.log).",
                           style="yellow")

    def _list_profiles(self) -> None:
        from .config import list_profiles as lp

        names = lp(self.cfg)
        if not names:
            self.sink.line("(nenhum provedor cadastrado ainda)")
        for i, p in enumerate(names, start=1):
            prof = self.cfg["profiles"][p]
            marca = " (em uso)" if p == self.cfg.get("active_profile") else ""
            self.sink.line(f"  {i}. {p}{marca} - {prof['model']} em {prof['base_url']}")

    THINKING_OPTIONS = ["manter atual", "off", "minimum", "low", "medium",
                        "high", "xhigh", "max", "ultra", "auto"]

    def _ask_thinking_level(self) -> None:
        """Depois de trocar de modelo/provedor, oferece o nivel de pensamento."""
        if not hasattr(self.sink, "ask_choice"):
            return
        escolha = self.sink.ask_choice(
            "NIVEL DE PENSAMENTO DO MODELO",
            "O quanto o modelo deve 'pensar' antes de responder? (Enter = manter atual)",
            self.THINKING_OPTIONS,
        )
        if escolha and escolha != self.THINKING_OPTIONS[0]:
            self.cfg["thinking"] = escolha
            save_config(self.cfg)
            self.llm.cfg["thinking"] = escolha
            self.sink.line(f"Pensamento: {escolha} (salvo)", style="cyan")

    def stop(self) -> None:
        """UI chama isto quando o usuario manda parar."""
        self.agent.stop_event.set()

    def _run_setup_wizard(self) -> str:
        """Assistente do 'bgh setup' rodando DENTRO da tela (/configurar).

        Caso real: pessoa instalou, errou a chave e ficou no 'voce>' sem saber
        como consertar. Aqui ela conserta sem sair do TEO; serve para o provedor
        atual ou para cadastrar um novo (os antigos continuam salvos).
        """
        from .setup_wizard import run as run_setup

        ask_fn = getattr(self.sink, "ask_line", None)
        if ask_fn is None:
            self.sink.line("Este modo nao consegue perguntar na tela; rode 'bgh setup' "
                           "na janela de comando.", style="yellow")
            return "continue"
        run_setup(ask=ask_fn,
                  say=lambda *a: self.sink.line(" ".join(str(x) for x in a)),
                  from_chat=True)
        try:
            novo = load_config()
        except ConfigError as exc:
            self.sink.line(str(exc), style="red")
            return "continue"
        # Mesmo objeto de dict: agente, gate e tela passam a ver a conexao nova.
        self.cfg.clear()
        self.cfg.update(novo)
        self.llm = LLM(self.cfg)
        self.llm.on_note = lambda texto: self.sink.line(texto, style="yellow")
        self.agent.llm = self.llm
        self.sink.line(f"Conexao agora: {self.cfg['model']} @ {self.cfg['base_url']}. "
                       "Ja vale na proxima mensagem.", style="cyan")
        self._ask_thinking_level()
        return "continue"

    # ----- turno -----------------------------------------------------------------
    def submit(self, text: str) -> str:
        """Processa uma linha digitada. Devolve 'continue' ou 'exit'."""
        text = text.strip()
        if not text:
            return "continue"

        # Atalho @ : listar arquivos ou anexar arquivo.
        if text.startswith("@"):
            arg = text[1:].strip()
            if not arg:
                self.sink.line(files_mod.list_dir(os.getcwd(), files_only=True))
                return "continue"
            target = Path(os.path.expanduser(arg))
            if target.is_dir():
                self.sink.line(files_mod.list_dir(str(target), files_only=True))
            elif target.is_file():
                try:
                    content = target.read_text(encoding="utf-8", errors="replace")[:8000]
                except OSError as exc:
                    log_error(exc, f"anexo de arquivo {target}")
                    self.sink.line(f"Nao consegui ler {target} (o arquivo pode estar aberto em "
                                   "outro programa ou protegido). O detalhe tecnico ficou no "
                                   "erro.log.", style="yellow")
                    return "continue"
                self.pending_attach = f"[arquivo anexado: {target}]\n{content}"
                self.sink.line(f"Arquivo anexado: {target}. Agora faca sua pergunta sobre ele.", style="dim")
            else:
                self.sink.line(f"Nao encontrei esse arquivo: {target}")
            return "continue"

        # Atalho / e /ls : listar pastas.
        if text in ("/", "/ls") or text.startswith("/ls ") or text.startswith("/ "):
            alvo = (text[3:] if text.startswith("/ls") else text[1:]).strip()
            alvo = os.path.expanduser(alvo) if alvo else os.getcwd()
            self.sink.line(files_mod.list_dir(alvo))
            return "continue"

        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            name = parts[0].lower()
            rest = parts[1].strip() if len(parts) > 1 else ""
            if name in ("/sair", "/exit", "/quit"):
                return "exit"
            elif name == "/ajuda":
                self.sink.border()   # abre a lista
                for seg_line in help_lines():
                    self.sink.parts(seg_line)
                self.sink.border()   # fecha a lista
            elif name == "/nov":
                self.agent.new_session()
                self.pending_attach = None
                self.sink.line("Conversa zerada (memoria e skills preservadas).", style="dim")
                self.print_ctx()   # rodape tem que mostrar a leitura nova na hora, nao a velha
            elif name == "/mem" and rest:
                from .tools import memory

                self.sink.line(memory.add(rest, target="user"))
            elif name == "/skills":
                from .tools.skills import discover, index_lines

                lines = index_lines(discover())
                self.sink.line("\n".join(f"- {line}" for line in lines) or "(nenhuma skill ainda)")
            elif name in ("/modelos", "/modelo"):
                if name == "/modelos" or not rest:
                    self._list_models()  # sozinho lista; '/modelos' continua aceito (alias oculto)
                else:
                    alvo2 = rest
                    if rest.isdigit() and self.model_list:
                        idx = int(rest) - 1
                        if 0 <= idx < len(self.model_list):
                            alvo2 = self.model_list[idx]
                        else:
                            self.sink.line("Numero fora da lista. Digite /modelo para ver.")
                            return "continue"
                    self.cfg["model"] = alvo2
                    save_config(self.cfg)
                    # Perfil salvo anda junto: sem isso, trocar de provedor depois
                    # devolvia o modelo antigo sem avisar.
                    sync_profile(self.cfg)
                    self.sink.line(f"Modelo agora: {alvo2} (salvo no config)", style="cyan")
                    self._ask_thinking_level()
                    self._refresh_server_context(troca=True, render=True)
            elif name in ("/provedores", "/provedor"):
                if name == "/provedores" or not rest:
                    self._list_profiles()  # sozinho lista; alias antigo aceito
                else:
                    from .config import list_profiles as lp, set_active_profile

                    names = lp(self.cfg)
                    alvo3 = rest
                    if rest.isdigit() and 1 <= int(rest) <= len(names):
                        alvo3 = names[int(rest) - 1]
                    if set_active_profile(self.cfg, alvo3):
                        self.llm = LLM(self.cfg)
                        self.agent.llm = self.llm
                        prof = self.cfg["profiles"][alvo3]
                        self.sink.line(
                            f"Provedor agora: {alvo3} - {prof['model']} em {prof['base_url']} "
                            "(salvo; a conversa continua)",
                            style="cyan",
                        )
                        self._ask_thinking_level()
                        self._refresh_server_context(troca=True, render=True)
                    else:
                        self.sink.line("Provedor nao encontrado. Digite /provedor sozinho para ver a lista.")
            elif name in ("/pensamento", "/thinking"):
                levels = ("auto", "off", "minimum", "low", "medium", "high",
                          "xhigh", "max", "ultra")
                alvo_t = rest.lower()
                if alvo_t in ("liga", "ligar"):
                    # Controla a TELA: mostra o bloco cinza. O que vai ao servidor nao muda.
                    self.cfg["show_thinking"] = True
                    save_config(self.cfg)
                    self.sink.line("Pensamento na tela: LIGADO (salvo)", style="cyan")
                elif alvo_t in ("desliga", "desligar", "parar"):
                    # Controla a TELA: esconde o bloco cinza. O modelo segue pensando
                    # (em provedores hospedados quem decide pensar e o provedor).
                    self.cfg["show_thinking"] = False
                    save_config(self.cfg)
                    self.sink.line("Pensamento na tela: DESLIGADO (salvo); o modelo segue "
                                   "trabalhando por dentro e a resposta chega igual", style="cyan")
                elif alvo_t in levels:
                    self.cfg["thinking"] = alvo_t
                    save_config(self.cfg)
                    self.llm.cfg["thinking"] = alvo_t
                    self.sink.line(f"Nivel de raciocinio enviado ao servidor: {alvo_t} (salvo). "
                                   "Obs.: provedores hospedados podem ignorar o nivel pedido.",
                                   style="cyan")
                elif not rest:
                    tela = "ligado" if self.cfg.get("show_thinking", True) else "desligado"
                    self.sink.line(
                        f"Pensamento na tela: {tela} | nivel enviado ao servidor: "
                        f"{self.cfg.get('thinking', 'auto')}. Uso: /pensamento liga | "
                        "desliga | auto | off | minimum | low | medium | high | xhigh | max | ultra")
                else:
                    self.sink.line(
                        "Nao entendi. Use /pensamento liga ou /pensamento desliga (tela); "
                        "avancado (servidor): auto off minimum low medium high xhigh max ultra")
            elif name == "/palco":
                alvo_p = rest.lower()
                if alvo_p in ("liga", "ligar"):
                    self.cfg["palco"] = True
                    save_config(self.cfg)
                    self.sink.line("Palco: LIGADO (a trilha do pedido aparece durante a resposta).",
                                   style="cyan")
                elif alvo_p in ("desliga", "desligar", "parar"):
                    self.cfg["palco"] = False
                    save_config(self.cfg)
                    self.sink.line("Palco: DESLIGADO (tela como antes; salvo)", style="cyan")
                elif not rest:
                    estado = "ligado" if self.cfg.get("palco", True) else "desligado"
                    self.sink.line(f"Palco: {estado}. Uso: /palco liga | /palco desliga")
                else:
                    self.sink.line("Nao entendi. Use /palco liga ou /palco desliga", style="yellow")
            elif name == "/ctx":
                if rest:
                    novo = parse_budget(rest)
                    if novo is None:
                        # Silenciar argumento era lido como bug na maquina do cliente.
                        self.sink.line("Esse numero nao vale. Uso: /ctx 65000 (aceita 65k, "
                                       "65.000, 65 mil). Intervalo: 8000 a 1000000.", style="yellow")
                    else:
                        self.cfg["context_budget_chars"] = novo
                        for dono in (self.agent, self.llm):
                            if getattr(dono, "cfg", None) is not None and dono.cfg is not self.cfg:
                                dono.cfg["context_budget_chars"] = novo
                        save_config(self.cfg)
                        self.sink.line(f"Orcamento de contexto ajustado para {novo} caracteres "
                                       "(salvo). Vale ja na proxima resposta.", style="cyan")
                self.print_ctx()
            elif name in ("/configurar", "/configure", "/setup"):
                return self._run_setup_wizard()
            elif name == "/doctor":
                from .cli import doctor_report

                doctor_report(lambda texto: self.sink.line(str(texto)))
            elif name in ("/atualizar", "/update"):
                from . import __version__
                from .updater import apply_update, fetch_latest, python_bin, update_needed

                info, err_upd = fetch_latest()
                if info is None or err_upd:
                    self.sink.line(f"Nao consegui verificar a versao nova: {err_upd}", style="yellow")
                    return "continue"
                if not update_needed(__version__, info["version"]):
                    # Mesma versao: avisa que esta atualizado e pronto, sem oferecer instalacao.
                    self.sink.line(f"O TEO ja esta atualizado (versao {info['version']}). "
                                   "Pode continuar usando.", style="cyan")
                    return "continue"
                if not python_bin():
                    # Aberto pelo icone/arquivo executavel: nao ha pip por dentro para atualizar.
                    self.sink.line(f"Existe versao nova ({info['version']}). Como o TEO foi aberto pelo "
                                   "icone/arquivo executavel, baixe e rode o INSTALAR_TEO.bat outra vez "
                                   "(dois cliques) - ele faz a atualizacao inteira.", style="yellow")
                    return "continue"
                escolha = None
                if hasattr(self.sink, "ask_choice"):
                    escolha = self.sink.ask_choice(
                        "ATUALIZAR O TEO",
                        f"Encontrei a versao {info['version']} (a sua e a {__version__}). "
                        "Atualizar agora?",
                        ["Sim, atualizar", "Nao, deixar como esta"],
                    )
                if escolha != "Sim, atualizar":
                    self.sink.line("Atualizacao cancelada (nada mudou).", style="dim")
                    return "continue"
                self.sink.line(f"Baixando e instalando a versao {info['version']}...", style="cyan")
                ok_upd, msg_upd = apply_update(info["wheel_url"])
                if ok_upd:
                    self.sink.line(f"Atualizado para {info['version']}. Feche (/sair) e abra o TEO de novo "
                                   "para o codigo novo comecar a valer.", style="cyan")
                else:
                    self.sink.line(f"A atualizacao nao completou: {msg_upd}", style="red")
                    self.sink.line("Alternativa que funciona em qualquer maquina: baixar e rodar o "
                                   "INSTALAR_TEO.bat da pagina de downloads do TEO.", style="yellow")
            else:
                self.sink.line("Comando desconhecido. /ajuda mostra a lista.")
            return "continue"

        # Turno normal do modelo (com anexo pendente, se houver).
        user_text = f"{self.pending_attach}\n\n{text}" if self.pending_attach else text
        self.pending_attach = None
        # Continuacao estilo Hermes: mensagens digitadas durante o turno que chegaram
        # tarde viram o proximo turno automaticamente (nada se perde).
        fila_turnos: list[str] = [user_text]
        while fila_turnos:
            turno = fila_turnos.pop(0)
            self.st["thinking"] = False
            self.st["resposta"] = False
            self._pend = ""
            try:
                answer = self.agent.run_turn(turno)
            except KeyboardInterrupt:
                # CTRL+C no modo classico tambem para o turno.
                self.agent.stop_event.set()
                answer = STOPPED_NOTE
            except LLMRateLimitError as exc:
                # Limite de uso/cota nao e defeito: amarelo (aviso) e dica certa,
                # sem mandar a pessoa reconferir URL e chave.
                self.sink.line(str(exc), style="yellow")
                self.sink.line("Dica: /provedor mostra os outros provedores cadastrados.",
                               style="dim")
                return "continue"
            except LLMError as exc:
                self.sink.line(str(exc), style="red")
                self.sink.line("Dica: digite /configurar aqui mesmo para conferir URL e chave "
                               "(ou /doctor para o diagnostico completo).", style="yellow")
                return "continue"
            except Exception as exc:  # noqa: BLE001 - falha tecnica nunca vira traceback na tela
                log_error(exc, "turno do modelo")
                self.sink.line("Algo deu errado no TEO durante a resposta. A conversa continua; "
                               "o detalhe tecnico foi guardado no arquivo erro.log da pasta .bgh.",
                               style="yellow")
                return "continue"

            self._flush_pend()
            if self.st["thinking"]:
                self.sink.line("")
            if answer == STOPPED_NOTE:
                # Usuario mandou parar: confirmar em uma linha proprio visivel.
                self.sink.line(STOPPED_NOTE, style="yellow")
            elif self.agent.last_streamed:
                self.sink.line("")  # fecha a linha do texto que ja apareceu ao vivo
            else:
                if self.agent.last_reasoning:
                    self.sink.sep("pensamento do modelo (raciocinio; pode ignorar e ir direto para a resposta)")
                    for r in self.agent.last_reasoning:
                        trecho = r if len(r) <= 1200 else r[:1200] + "..."
                        self.sink.line(trecho, style="#808080 italic")
                    self.sink.sep("resposta")
                elif not self.st["resposta"]:
                    self.sink.sep("resposta")
                self.sink.line(md_clean(answer))
            if (not answer and answer != STOPPED_NOTE and not self.agent.last_streamed
                    and not self.st["resposta"]):
                # Caso medido no servidor: o pensamento comeu todo o max_tokens e o pedido
                # voltou sem texto. Sem esta linha a pessoa acha que o programa travou.
                self.sink.line("O modelo terminou sem texto de resposta (apenas pensou). Pergunte "
                               "de novo ou aumente o limite de saida (max_tokens no config.json).",
                               style="yellow")
            if answer == STOPPED_NOTE:
                # Turno parado nao emenda as mensagens guardadas: quem mandou parar
                # decide se quer continuar. Elas sao devolvidas como aviso.
                descartadas = 0
                while self.agent.pop_steer() is not None:
                    descartadas += 1
                if descartadas:
                    self.sink.line(f"({descartadas} mensagem(s) digitadas durante o turno parado "
                                   "nao foram enviadas; digite de novo quando quiser)", style="yellow")
                break
            while True:
                sobra = self.agent.pop_steer()
                if sobra is None:
                    break
                self.sink.line(f"voce> {sobra}", style="cyan")
                fila_turnos.append(sobra)
        self.print_ctx()
        return "continue"

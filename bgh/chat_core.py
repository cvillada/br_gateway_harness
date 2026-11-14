"""Nucleo do chat: a mesma logica para a tela fixa (tui.py) e o modo classico.

Comandos com barra (/ajuda, /nov, /modelo...), atalhos @ e /, turno do modelo e
menu de licenca vivem aqui. A saida passa por um "sink", assim cada tela decide
como mostrar (rich no modo classico; area de texto na tela fixa).
"""

import datetime
import getpass
import os
import re
import threading
import traceback
from pathlib import Path

from rich.console import Console

from . import i18n, limpeza, tela, voz
from .agent import Agent, STOPPED_NOTE
from .i18n import t
from .approvals import Gate
from .config import CONFIG_PATH, SESSION_FILE, ConfigError, load_config, save_config, sync_profile
from .llm import LLM, LLMError, LLMRateLimitError
from .palco import abrevia
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


def prepare_console(cfg: dict | None = None) -> None:
    """Nome na janela + tela maximizada (+ letra no Windows): antes da 1a tela."""
    set_window_title("TEO Agent")
    maximize_window()
    if os.name == "nt":
        # Tamanho da letra escolhido no /fonte vale ja nesta abertura (Windows tem
        # API para isso; Linux/macOS dependem do proprio terminal).
        tela.fonte_windows(tela.nivel(cfg))


def ctx_parts(cfg: dict, usage: dict) -> tuple[str, str]:
    """(medidor, extra) separados: a tela decide se o extra cabe na janela.

    Funcao pura (le so cfg/usage): testavel sem instanciar o ChatCore. Quando o
    servidor ja informou os tokens do ultimo pedido, o numero mostrado e o REAL;
    antes disso e a estimativa de 3,5 caracteres por token, marcada com '~' para
    ninguem confundir estimativa com contagem do provedor.
    """
    tokens = usage.get("tokens")
    teto = usage.get("tokens_teto")
    if tokens:
        marca = "" if usage.get("tokens_reais") else "~"
        if teto:
            # "usado de teto": escrever o numero depois do teto em chars fazia
            # parecer que o teto inteiro valia esses tokens (confusao real).
            tok_txt = t("ctx.tokens_teto", marca=marca, tokens=abrevia(tokens),
                        teto=abrevia(teto))
        else:
            tok_txt = t("ctx.tokens", marca=marca, tokens=abrevia(tokens))
    else:
        tok_txt = ""
    txt = t("ctx.meter", pct=usage["pct"], budget=usage["budget"], tokens=tok_txt,
            messages=usage["messages"])
    extra = ""
    srv = cfg.get("server_context_tokens")
    if isinstance(srv, (int, float)) and srv > 0:
        entrega_chars = int(srv * CHARS_POR_TOKEN * FOLGA_LEITURA)
        if entrega_chars > usage["budget"]:
            extra = t("ctx.extra", tokens=f"{int(srv):,}".replace(",", "."))
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

def help_lines() -> list[list]:
    """Ajuda em pedacos: o COMANDO em roxo suave, a explicacao na cor normal.

    O conteudo (tres idiomas lado a lado) mora em bgh/i18n.py; aqui so o desenho.
    """
    out: list[list] = []
    for header, pairs in i18n.help_table():
        out.append([(header, None)])
        width = max(len(c) for c, _ in pairs) + 3
        for comando, desc in pairs:
            color = PURPLE if comando.startswith(("/", "@")) else None
            out.append([(f"  {comando:<{width}}", color), (desc, None)])
        out.append([("", None)])
    return out


def build_approval_options(allow_always: bool) -> tuple[list[str], list[str]]:
    """Menu numerico simples para o usuario; por dentro mapeia para o fluxo Hermes o/s/a/d."""
    options = [t("common.approve_once"), t("common.approve_conv")]
    codes = ["o", "s"]
    if allow_always:
        options.append(t("common.approve_always"))
        codes.append("a")
    options.append(t("common.cancel"))
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

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg if cfg is not None else {}
        self.pendente = ""     # texto ditado que vira a proxima linha digitada
        self.console = Console(style=tela.estilo_rich(tela.cor(self.cfg)) or None)

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

    def aplicar_tema(self) -> None:
        """Cor de fundo no modo classico: OSC 11 + letra de contraste no rich."""
        nome = tela.cor(self.cfg)
        seq = tela.escape_fundo(nome)
        if not seq and getattr(self, "_cor_pintada", "padrao") != "padrao":
            seq = tela.RESET_FUNDO      # voltou ao padrao: devolve a cor do terminal
        self._cor_pintada = nome
        tela.escrever(seq)
        self.console = Console(style=tela.estilo_rich(nome) or None)

    def preencher(self, texto: str) -> None:
        """Modo classico: nao existe linha editavel; o texto vira a proxima entrada."""
        self.pendente = str(texto)

    def bipar(self) -> None:
        """Campainha do terminal: aviso sonoro do ditado (nao depende de audio)."""
        try:
            print("\a", end="", flush=True)
        except (OSError, ValueError):
            pass

    def read_prompt(self) -> str:
        if self.pendente:
            texto, self.pendente = self.pendente, ""
            # mostra o que vai ser enviado, com o mesmo rotulo da linha de digitar
            self.console.print(f"{t('sink.prompt')}{texto}", markup=False)
            return texto
        return self.console.input(f"\n[bold cyan]{t('sink.prompt')}[/bold cyan]")

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
        self.console.print(t("approval.header"), style="bold yellow", markup=False)
        self.console.print(label, style="bold", markup=False)
        for ln in str(detail).splitlines()[:8]:
            if ln.strip():
                self.console.print(f"   {ln}", markup=False)
        self.console.print(t("approval.question"), markup=False)
        for i, opt in enumerate(options, start=1):
            self.console.print(f"  [{i}] {opt}", markup=False)
        try:
            raw = input(t("approval.prompt_deny", n=len(options)))
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
            raw = input(t("approval.prompt_choice", first=options[0]))
        except (EOFError, KeyboardInterrupt):
            return options[0]
        return parse_approval_choice(raw, options, default=options[0])


class ChatCore:
    """Logica de chat igual nas duas telas. submit() roda um turno completo."""

    def __init__(self, cfg: dict, sink, llm: LLM | None = None):
        self.cfg = cfg
        i18n.set_lang(cfg.get("lang"))   # toda frase da tela sai no idioma salvo
        self.sink = sink
        self.llm = llm or LLM(cfg)
        self.gate = Gate(cfg, sink.ask_approval)
        self.agent = Agent(cfg, self.llm, self.gate, on_event=sink.tool_event)
        self.model_list: list[str] = []
        self.pending_attach: str | None = None
        self.pending_image: str | None = None   # foto anexada (vai para a visao)
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
        if hasattr(self.sink, "rodada_nova"):
            self.sink.rodada_nova()   # palco mostra em que rodada esta

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
            self.sink.sep(t("turn.sep.thinking"))
            self.st["thinking"] = True
        self.sink.thinking(chunk)

    def _on_text(self, chunk: str) -> None:
        if not self.st["resposta"]:
            if self.st["thinking"]:
                self.sink.line("")
                self.st["thinking"] = False
            self.sink.sep(t("turn.sep.answer"))
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
                self.sink.line(t("ctx.compacted"), style="dim")
            elif usage["pct"] >= limite_pct:
                self.sink.line(t("ctx.filling"), style="dim")
            return
        color = "green" if usage["pct"] < 50 else ("yellow" if usage["pct"] < 80 else "red")
        self.sink.sep()
        self.sink.line(txt, style=color)
        if self.agent.last_compressed:
            self.sink.line(t("ctx.compacted"), style="dim")
        elif usage["pct"] >= limite_pct:
            self.sink.line(t("ctx.filling"), style="dim")

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
        self.sink.line(t("banner.title"), style="bold")
        self.sink.line(t("banner.model", model=self.cfg["model"],
                         base_url=self.cfg["base_url"],
                         thinking=self.cfg.get("thinking", "auto")), style="cyan")
        if SESSION_FILE.exists():
            self.sink.line(t("banner.resumed", new=i18n.cmd("new")), style="dim")
        for seg_line in help_lines():
            self.sink.parts(seg_line)
        self.sink.border()   # fecha o bloco de boas-vindas

    def check_update_on_start(self) -> None:
        """Confere versao nova UMA vez, na abertura, sem segurar a tela.

        Roda em segundo plano de proposito: no cliente a rede pode estar lenta
        ou fora, e a abertura nao pode ficar esperando o GitHub. A tela recebe
        uma linha so quando ha o que dizer (versao nova ou falha de acesso).
        """
        if not self.cfg.get("update_check", True):
            return
        from . import __version__
        from .updater import startup_check

        def _worker() -> None:
            try:
                texto, versao = startup_check(__version__)
            except Exception:  # noqa: BLE001 - cortesia de abertura nunca derruba o TEO
                return
            if texto:
                self.sink.line(texto, style="cyan" if versao else "dim")

        self._update_thread = threading.Thread(target=_worker, daemon=True)
        self._update_thread.start()

    def _list_models(self) -> None:
        try:
            self.model_list = self.llm.list_models()
            if not self.model_list:
                self.sink.line(t("cmd.model.no_list"))
            em_uso_marcado = False
            for i, m in enumerate(self.model_list, start=1):
                marca = t("common.in_use") if m == self.cfg["model"] else ""
                if marca:
                    em_uso_marcado = True
                self.sink.line(f"  {i}. {m}{marca}")
            if self.model_list and not em_uso_marcado:
                # Provedores as vezes renomeiam IDs: sem igual exato, a lista ficaria
                # sem marca nenhuma e o usuario acharia que o medidor esta quebrado.
                self.sink.line(t("cmd.model.not_in_list", model=self.cfg["model"]),
                               style="dim")
        except LLMError as exc:
            log_error(exc, "lista de modelos")
            self.sink.line(t("cmd.model.no_answer"), style="yellow")
        except Exception as exc:  # noqa: BLE001 - servidor estranho nunca derruba a tela
            log_error(exc, "lista de modelos")
            self.sink.line(t("cmd.model.bad_answer", doctor=i18n.cmd("doctor")),
                           style="yellow")

    def _list_profiles(self) -> None:
        from .config import list_profiles as lp

        names = lp(self.cfg)
        if not names:
            self.sink.line(t("cmd.provider.none"))
        for i, p in enumerate(names, start=1):
            prof = self.cfg["profiles"][p]
            marca = t("common.in_use") if p == self.cfg.get("active_profile") else ""
            self.sink.line(t("cmd.provider.row", n=i, name=p, marca=marca,
                             model=prof["model"], base_url=prof["base_url"]))

    def _thinking_options(self) -> list[str]:
        """Niveis oferecidos apos trocar modelo/provedor (no idioma da tela)."""
        return [t("common.keep_current"), "off", "minimum", "low", "medium",
                "high", "xhigh", "max", "ultra", "auto"]

    def _ask_thinking_level(self) -> None:
        """Depois de trocar de modelo/provedor, oferece o nivel de pensamento."""
        if not hasattr(self.sink, "ask_choice"):
            return
        opcoes = self._thinking_options()
        escolha = self.sink.ask_choice(
            t("ask.thinking.title"),
            t("ask.thinking.label"),
            opcoes,
        )
        if escolha and escolha != opcoes[0]:
            self.cfg["thinking"] = escolha
            save_config(self.cfg)
            self.llm.cfg["thinking"] = escolha
            self.sink.line(t("ask.thinking.done", level=escolha), style="cyan")

    def _set_lang(self, codigo: str) -> None:
        """Troca o idioma na hora: config, tela e o pedido que vai ao modelo."""
        self.cfg["lang"] = codigo
        i18n.set_lang(codigo)
        save_config(self.cfg)
        if isinstance(getattr(self.agent, "cfg", None), dict):
            self.agent.cfg["lang"] = codigo
        ferramentas = getattr(self.agent, "tools", None)
        if hasattr(ferramentas, "relocalize"):
            ferramentas.relocalize()   # descricoes das ferramentas tambem trocam
        if hasattr(self.agent, "refresh_prompt"):
            self.agent.refresh_prompt()   # o modelo passa a responder no idioma novo
        self.sink.line(t("lang.changed", name=i18n.LANG_NAMES[codigo]), style="cyan")
        # A lista de ajuda no idioma novo e a prova visivel da troca.
        self.sink.border()
        for seg_line in help_lines():
            self.sink.parts(seg_line)
        self.sink.border()
        self.print_ctx()   # o medidor do rodape tambem troca de idioma na hora

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
            self.sink.line(t("cmd.setup.no_menu"), style="yellow")
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
        # O assistente tambem pode ter mudado o idioma (primeira configuracao):
        # a tela e o pedido ao modelo passam a valer no idioma escolhido.
        i18n.set_lang(self.cfg.get("lang"))
        self.agent.refresh_prompt()
        self.sink.line(t("cmd.setup.connected", model=self.cfg["model"],
                         base_url=self.cfg["base_url"]), style="cyan")
        self._ask_thinking_level()
        return "continue"

    # ----- menu de arquivos (tela fixa) ----------------------------------------
    MENU_MAX = 18  # itens por menu: numero alto demais nao se acha na tela

    def _escolher_caminho(self, inicio: str, para_anexar: bool = False) -> str | None:
        """Menu numerado de pastas/arquivos: navega, pagina e devolve o arquivo.

        Motivo (pedido do usuario): pessoa idosa ou crianca nao deve digitar
        caminho. Cada linha DIZ o que acontece se escolher ("entrar em: ...",
        "anexar: ..."), o rotulo ensina a digitar o numero e a opcao 1 sempre
        cancela (Enter/ESC nao escolhem nada por engano).

        Pasta com muita coisa: a lista PAGINA de MENU_MAX em MENU_MAX e a opcao
        "mais itens" mostra o resto (antes ela existia mas cancelava a escolha -
        o usuario digitava o numero dela e o TEO simplesmente saia).
        """
        atual = os.path.abspath(os.path.expanduser(inicio) or os.getcwd())
        deslocamento = 0
        while True:
            pastas, arquivos, erro = files_mod.entries(atual)
            if erro:
                self.sink.line(erro, style="yellow")
                return None
            itens: list[tuple[str, str]] = [
                (t("menu.enter_folder", nome=nome), os.path.join(atual, nome))
                for nome in pastas
            ]
            chave_item = "menu.attach" if para_anexar else "menu.view"
            itens += [(t(chave_item, nome=nome), os.path.join(atual, nome))
                      for nome in arquivos]
            opcoes: list[str] = [t("menu.cancel")]
            alvos: list[str | None] = [None]
            pai = os.path.dirname(atual.rstrip(os.sep))
            if pai and pai != atual:
                opcoes.append(t("menu.up"))
                alvos.append(pai)
            fatia = itens[deslocamento:deslocamento + self.MENU_MAX]
            for rotulo, caminho in fatia:
                opcoes.append(rotulo)
                alvos.append(caminho)
            restantes = len(itens) - (deslocamento + len(fatia))
            if restantes > 0:
                opcoes.append(t("menu.more", n=restantes))
                alvos.append("__proxima__")
            if deslocamento > 0:
                opcoes.append(t("menu.back_start"))
                alvos.append("__inicio__")
            escolha = self.sink.ask_choice(
                t("menu.title_attach") if para_anexar else t("menu.title_open"),
                t("menu.label", atual=atual),
                opcoes,
            )
            if escolha not in opcoes:
                return None      # quem chamou avisa (uma vez so) que nada foi escolhido
            alvo = alvos[opcoes.index(escolha)]
            if alvo == "__proxima__":
                deslocamento += self.MENU_MAX
                continue
            if alvo == "__inicio__":
                deslocamento = 0
                continue
            if alvo is None:
                return None      # quem chamou avisa (uma vez so) que nada foi escolhido
            if os.path.isdir(alvo):
                self.sink.line(t("menu.entering", alvo=alvo), style="dim")
                atual = alvo
                deslocamento = 0
                continue
            return alvo

    # ----- turno -----------------------------------------------------------------
    # ------------------------------------------------------------------
    # Ditado (acessibilidade): o comando /ditar e a tecla F2/espaco chamam AQUI
    # ------------------------------------------------------------------
    def ditar(self, forcar_baixar: bool = False) -> str:
        """Escuta o microfone e poe o texto na linha. Devolve 'continue'.

        Chamado pelo `/ditar` e, na tela fixa, pela tecla F2 (ou espaco com a
        linha vazia) - quem nao enxerga nao pode depender de digitar comando.
        O reconhecedor segue o idioma da TELA (/lingua).
        """
        from . import ditar

        idioma_d = i18n.get_lang()
        nome_idioma = i18n.LANG_NAMES.get(idioma_d, idioma_d)
        if not ditar.tem_motor():
            self.sink.line(t("cmd.ditar.sem_motor"), style="yellow")
            return "continue"
        if not ditar.tem_modelo(idioma_d):
            quer = bool(forcar_baixar)
            opcoes_d = [t("common.approve_once"), t("common.cancel")]
            if not quer and hasattr(self.sink, "ask_choice"):
                escolha_d = self.sink.ask_choice(
                    t("cmd.ditar.title"),
                    t("cmd.ditar.baixar_ask", idioma=nome_idioma,
                      mb=ditar.tamanho_mb(idioma_d)),
                    opcoes_d)
                quer = escolha_d == opcoes_d[0]
            if not quer:
                self.sink.line(t("cmd.ditar.baixar_hint", idioma=nome_idioma,
                                 cmd=i18n.cmd("dictate")), style="dim")
                return "continue"
            ultimo = {"pct": -10}

            def _progresso(pct: int) -> None:
                # uma linha a cada 20%: barulho na tela nao ajuda ninguem
                if pct - ultimo["pct"] >= 20:
                    ultimo["pct"] = pct
                    self.sink.line(t("cmd.ditar.baixando", idioma=nome_idioma,
                                     pct=pct), style="dim")

            baixou_d, detalhe_d = ditar.baixar_modelo(idioma_d, ao_progresso=_progresso)
            if not baixou_d:
                motivo_d = ("sem internet" if detalhe_d == "sem_conexao"
                            else "o arquivo veio com problema")
                self.sink.line(t("cmd.ditar.baixou_falhou", motivo=motivo_d,
                                 cmd=i18n.cmd("dictate")), style="yellow")
                return "continue"
            _quantos_d, bytes_d = limpeza.varrer(ditar.modelo_dir(idioma_d))
            self.sink.line(t("cmd.ditar.baixou", idioma=nome_idioma,
                             tam=limpeza.tamanho_legivel(bytes_d)), style="cyan")
        voz.parar()          # a voz do TEO nao pode cair no microfone
        self.sink.line(t("cmd.ditar.ouvindo"), style="cyan")
        bipar = getattr(self.sink, "bipar", None)
        if bipar is not None:
            bipar()          # bip = "pode falar" (quem nao ve a tela precisa ouvir)
        # CTRL+C/ESC durante a escuta para a gravacao na hora (o mesmo botao que
        # a pessoa ja usa para parar o modelo).
        evento_d = getattr(self.agent, "stop_event", None)
        if evento_d is not None:
            evento_d.clear()
        falado = ditar.escutar(idioma_d, parar=evento_d.is_set if evento_d else None)
        if bipar is not None:
            bipar()          # bip = "parei de ouvir"
        if evento_d is not None and evento_d.is_set():
            # A pessoa mandou parar (ESC/CTRL+C): nao e "nao entendi", e "parei".
            self.sink.line(t("cmd.ditar.parado"), style="dim")
            return "continue"
        if not falado.strip():
            self.sink.line(t("cmd.ditar.vazio", cmd=i18n.cmd("dictate")),
                           style="yellow")
            return "continue"
        self.sink.line(t("cmd.ditar.entendi", texto=falado), style="cyan")
        preencher = getattr(self.sink, "preencher", None)
        if preencher is not None:
            # Tela fixa/modo classico: o texto entra na linha para conferir.
            preencher(falado)
            self.sink.line(t("cmd.ditar.revisar"), style="dim")
        else:
            self.sink.line(t("cmd.ditar.revisar_simples"), style="dim")
        return "continue"

    def submit(self, text: str) -> str:
        """Processa uma linha digitada. Devolve 'continue' ou 'exit'."""
        text = text.strip()
        if not text:
            return "continue"

        # Atalho @ : menu de arquivos (tela fixa) ou lista de arquivos.
        if text.startswith("@"):
            arg = text[1:].strip()
            if not arg:
                if getattr(self.sink, "menu_arquivos", False):
                    # Menu numerado: escolher o arquivo e anexar, sem digitar caminho.
                    arg = self._escolher_caminho(os.getcwd(), para_anexar=True) or ""
                    if not arg:
                        self.sink.line(t("common.nothing_chosen"), style="dim")
                        return "continue"
                else:
                    self.sink.line(files_mod.list_dir(os.getcwd(), files_only=True))
                    return "continue"
            target = Path(os.path.expanduser(arg))
            if target.is_dir():
                self.sink.line(files_mod.list_dir(str(target), files_only=True))
            elif target.is_file() and files_mod.is_image(str(target)):
                # Imagem: vai para o modelo como IMAGEM (visao), nao como texto.
                _url, tamanho, erro_img = files_mod.image_data_url(str(target))
                if erro_img:
                    self.sink.line(erro_img, style="yellow")
                    return "continue"
                self.pending_image = str(target)
                self.pending_attach = None
                self.sink.line(t("attach.image_ok", target=target,
                                 size=files_mod.human_size(tamanho)), style="cyan")
            elif target.is_file():
                try:
                    content = target.read_text(encoding="utf-8", errors="replace")[:8000]
                except OSError as exc:
                    log_error(exc, f"anexo de arquivo {target}")
                    self.sink.line(t("attach.read_fail", target=target), style="yellow")
                    return "continue"
                self.pending_attach = f"[arquivo anexado: {target}]\n{content}"
                try:
                    tamanho = files_mod.human_size(os.path.getsize(target))
                except OSError:
                    tamanho = "?"
                cortado = t("attach.truncated") if len(content) >= 8000 else ""
                self.sink.line(t("attach.file_ok", target=target, size=tamanho,
                                 cortado=cortado), style="cyan")
            else:
                self.sink.line(t("attach.not_found", target=target))
            return "continue"

        # Atalho / e /ls : menu da pasta (tela fixa) ou listagem.
        if text in ("/", "/ls") or text.startswith("/ls ") or text.startswith("/ "):
            alvo = (text[3:] if text.startswith("/ls") else text[1:]).strip()
            if not alvo and getattr(self.sink, "menu_arquivos", False):
                # Menu numerado: navegar por numero e escolher o arquivo.
                escolhido = self._escolher_caminho(os.getcwd())
                if not escolhido:
                    self.sink.line(t("common.nothing_chosen"), style="dim")
                elif os.path.isfile(escolhido):
                    try:
                        tamanho = files_mod.human_size(os.path.getsize(escolhido))
                    except OSError:
                        tamanho = "?"
                    self.sink.line(t("listing.file", path=escolhido, size=tamanho))
                    self.sink.line(t("listing.hint"), style="dim")
                return "continue"
            alvo = os.path.expanduser(alvo) if alvo else os.getcwd()
            self.sink.line(files_mod.list_dir(alvo))
            return "continue"

        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            what = i18n.canon(parts[0].lower().lstrip("/"))
            rest = parts[1].strip() if len(parts) > 1 else ""
            if what == "exit":
                voz.parar()        # sair cala a voz antes de fechar a tela
                return "exit"
            elif what == "help":
                self.sink.border()   # abre a lista
                for seg_line in help_lines():
                    self.sink.parts(seg_line)
                self.sink.border()   # fecha a lista
            elif what == "new":
                self.agent.new_session()
                self.pending_attach = None
                self.pending_image = None
                self.sink.line(t("cmd.new.done"), style="dim")
                self.print_ctx()   # rodape tem que mostrar a leitura nova na hora, nao a velha
            elif what == "mem" and rest:
                from .tools import memory

                self.sink.line(memory.add(rest, target="user"))
            elif what == "skills":
                from .tools.skills import discover, index_lines

                lines = index_lines(discover())
                self.sink.line("\n".join(f"- {line}" for line in lines)
                               or t("cmd.skills.empty"))
            elif what == "model":
                if not rest:
                    self._list_models()   # sozinho lista; nome ou numero trocam
                else:
                    alvo2 = rest
                    if rest.isdigit() and self.model_list:
                        idx = int(rest) - 1
                        if 0 <= idx < len(self.model_list):
                            alvo2 = self.model_list[idx]
                        else:
                            self.sink.line(t("cmd.model.off_list",
                                             model=i18n.cmd("model")))
                            return "continue"
                    self.cfg["model"] = alvo2
                    save_config(self.cfg)
                    # Perfil salvo anda junto: sem isso, trocar de provedor depois
                    # devolvia o modelo antigo sem avisar.
                    sync_profile(self.cfg)
                    self.sink.line(t("cmd.model.now", model=alvo2), style="cyan")
                    self._ask_thinking_level()
                    self._refresh_server_context(troca=True, render=True)
            elif what == "provider":
                if not rest:
                    self._list_profiles()   # sozinho lista
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
                        self.sink.line(t("cmd.provider.now", name=alvo3,
                                         model=prof["model"],
                                         base_url=prof["base_url"]), style="cyan")
                        self._ask_thinking_level()
                        self._refresh_server_context(troca=True, render=True)
                    else:
                        self.sink.line(t("cmd.provider.not_found",
                                         provider=i18n.cmd("provider")))
            elif what == "thinking":
                levels = ("auto", "off", "minimum", "low", "medium", "high",
                          "xhigh", "max", "ultra")
                alvo_t = rest.lower()
                if alvo_t in ("liga", "ligar", "on", "enable", "show", "mostrar",
                              "activar", "activa", "encender"):
                    # Controla a TELA: mostra o bloco cinza. O que vai ao servidor nao muda.
                    self.cfg["show_thinking"] = True
                    save_config(self.cfg)
                    self.sink.line(t("cmd.thinking.on"), style="cyan")
                elif alvo_t in ("desliga", "desligar", "parar", "hide", "esconder",
                                "ocultar", "disable", "desactivar", "desactiva",
                                "apagar"):
                    # Controla a TELA: esconde o bloco cinza. O modelo segue pensando
                    # (em provedores hospedados quem decide pensar e o provedor).
                    self.cfg["show_thinking"] = False
                    save_config(self.cfg)
                    self.sink.line(t("cmd.thinking.off"), style="cyan")
                elif alvo_t in levels:
                    self.cfg["thinking"] = alvo_t
                    save_config(self.cfg)
                    self.llm.cfg["thinking"] = alvo_t
                    self.sink.line(t("cmd.thinking.level", level=alvo_t), style="cyan")
                elif not rest:
                    # (nome diferente de "tela": bgh/tela.py e o modulo de cores/fonte)
                    estado_tela = (t("onoff.on") if self.cfg.get("show_thinking", True)
                            else t("onoff.off"))
                    self.sink.line(t("cmd.thinking.status", onoff=estado_tela,
                                     level=self.cfg.get("thinking", "auto"),
                                     cmd=i18n.cmd("thinking")))
                else:
                    self.sink.line(t("cmd.thinking.bad", cmd=i18n.cmd("thinking")))
            elif what == "stage":
                alvo_p = rest.lower()
                if alvo_p in ("liga", "ligar", "on", "enable", "show", "mostrar",
                              "activar", "activa", "encender"):
                    self.cfg["palco"] = True
                    save_config(self.cfg)
                    self.sink.line(t("cmd.stage.on"), style="cyan")
                elif alvo_p in ("desliga", "desligar", "parar", "off", "hide",
                                "esconder", "ocultar", "disable", "desactivar",
                                "desactiva", "apagar"):
                    self.cfg["palco"] = False
                    save_config(self.cfg)
                    self.sink.line(t("cmd.stage.off"), style="cyan")
                elif not rest:
                    estado = (t("onoff.on") if self.cfg.get("palco", True)
                              else t("onoff.off"))
                    self.sink.line(t("cmd.stage.status", onoff=estado,
                                     cmd=i18n.cmd("stage")))
                else:
                    self.sink.line(t("cmd.stage.bad", cmd=i18n.cmd("stage")),
                                   style="yellow")
            elif what == "ctx":
                if rest:
                    novo = parse_budget(rest)
                    if novo is None:
                        # Silenciar argumento era lido como bug na maquina do cliente.
                        self.sink.line(t("cmd.ctx.bad", ctx=i18n.cmd("ctx")),
                                       style="yellow")
                    else:
                        self.cfg["context_budget_chars"] = novo
                        for dono in (self.agent, self.llm):
                            if (getattr(dono, "cfg", None) is not None
                                    and dono.cfg is not self.cfg):
                                dono.cfg["context_budget_chars"] = novo
                        save_config(self.cfg)
                        self.sink.line(t("cmd.ctx.set", n=novo), style="cyan")
                self.print_ctx()
            elif what == "lang":
                if rest:
                    codigo = i18n.lang_from_answer(rest)
                    if codigo is None:
                        self.sink.line(t("lang.bad"))
                    else:
                        self._set_lang(codigo)
                else:
                    opcoes = i18n.lang_options()
                    escolha = self.sink.ask_choice(
                        t("lang.title"),
                        t("lang.ask", first=opcoes[0]),
                        opcoes,
                    )
                    if escolha in opcoes:
                        self._set_lang(i18n.LANGS[opcoes.index(escolha)])
            elif what == "voice":
                # Acessibilidade: le a resposta em voz alta com a voz do SISTEMA.
                # Sem argumento, cada /voz inverte o estado (mais facil de lembrar).
                alvo_v = rest.lower()
                if alvo_v in ("liga", "ligar", "on", "enable", "activar", "activa",
                              "encender", "sim", "yes", "si"):
                    novo_v = True
                elif alvo_v in ("desliga", "desligar", "off", "parar", "disable",
                                "desactivar", "desactiva", "apagar", "nao", "no"):
                    novo_v = False
                elif not rest:
                    novo_v = not bool(self.cfg.get("voz", False))
                else:
                    self.sink.line(t("cmd.voz.bad", cmd=i18n.cmd("voice")),
                                   style="yellow")
                    return "continue"
                if novo_v and not voz.disponivel():
                    # Nao ha como falar nesta maquina: avisa e NAO liga. Ligar sem voz
                    # deixaria a barra dizendo "voz ligada" com a tela muda.
                    self.cfg["voz"] = False
                    save_config(self.cfg)
                    self.sink.line(t("cmd.voz.no_backend"), style="yellow")
                    return "continue"
                self.cfg["voz"] = novo_v
                save_config(self.cfg)
                if not novo_v:
                    voz.parar()
                    self.sink.line(t("cmd.voz.off"), style="cyan")
                else:
                    self.sink.line(t("cmd.voz.on", voz=voz.nome_do_backend(),
                                     cmd=i18n.cmd("voice")), style="cyan")
                    voz.falar(t("cmd.voz.hello"))
            elif what == "clean":
                # Rascunhos do TEO: scripts do run_python e textos da voz. Nada de
                # conversa/memoria/skills mora aqui - a frase final diz isso.
                quantos, tamanho = limpeza.varrer()
                if not quantos:
                    self.sink.line(t("cmd.clean.empty"), style="dim")
                    return "continue"
                tam_txt = limpeza.tamanho_legivel(tamanho)
                apagar = str(rest).strip().lower() in ("sim", "yes", "si", "s", "sì")
                if not apagar:
                    if hasattr(self.sink, "ask_choice"):
                        escolha = self.sink.ask_choice(
                            t("cmd.clean.title"),
                            t("cmd.clean.ask", n=quantos, size=tam_txt),
                            [t("cmd.clean.yes"), t("cmd.clean.no")],
                        )
                        apagar = escolha == t("cmd.clean.yes")
                    else:
                        # Sem menu: nunca apagar sozinho. Ensina o jeito certo.
                        self.sink.line(t("cmd.clean.ask", n=quantos, size=tam_txt))
                        self.sink.line(t("cmd.clean.confirm_hint",
                                         cmd=i18n.cmd("clean")), style="dim")
                        return "continue"
                if not apagar:
                    self.sink.line(t("cmd.clean.cancel"), style="dim")
                    return "continue"
                apagados, liberado = limpeza.limpar()
                self.sink.line(t("cmd.clean.ok", n=apagados,
                                 size=limpeza.tamanho_legivel(liberado),
                                 nota=t("cmd.clean.nota")), style="cyan")
            elif what == "background":
                alvo_f = tela.nome_do_texto(rest) if rest else None
                if rest and not alvo_f:
                    self.sink.line(t("cmd.fundo.bad", cmd=i18n.cmd("background")),
                                   style="yellow")
                    return "continue"
                if not rest:
                    opcoes_f = [t("cor." + nome) for nome in tela.NOMES]
                    if hasattr(self.sink, "ask_choice"):
                        escolha_f = self.sink.ask_choice(
                            t("cmd.fundo.title"),
                            t("cmd.fundo.ask", first=opcoes_f[0]), opcoes_f)
                        if escolha_f in opcoes_f:
                            alvo_f = tela.NOMES[opcoes_f.index(escolha_f)]
                    if not alvo_f:
                        # Sem menu: mostra o atual e as opcoes numa linha so.
                        self.sink.line(t("cmd.fundo.list",
                                         atual=t("cor." + tela.cor(self.cfg)),
                                         cores=", ".join(t("cor." + n) for n in tela.NOMES),
                                         cmd=i18n.cmd("background")))
                        return "continue"
                if not alvo_f:
                    return "continue"
                self.cfg["cor_fundo"] = alvo_f
                save_config(self.cfg)
                aplicar = getattr(self.sink, "aplicar_tema", None)
                if aplicar:
                    aplicar()          # pinta a tela AGORA, sem precisar reabrir
                if alvo_f == "padrao":
                    self.sink.line(t("cmd.fundo.off"), style="cyan")
                else:
                    self.sink.line(t("cmd.fundo.now", cor=t("cor." + alvo_f),
                                     cmd=i18n.cmd("background")), style="cyan")
            elif what == "font":
                novo_n = tela.nivel_do_texto(rest) if rest else None
                if rest and novo_n is None:
                    self.sink.line(t("cmd.fonte.bad", cmd=i18n.cmd("font")),
                                   style="yellow")
                    return "continue"
                if not rest:
                    opcoes_n = [t("fonte." + tela.NIVEIS[n]) for n in sorted(tela.NIVEIS)]
                    if hasattr(self.sink, "ask_choice"):
                        escolha_n = self.sink.ask_choice(
                            t("cmd.fonte.title"),
                            t("cmd.fonte.ask", first=opcoes_n[0]), opcoes_n)
                        if escolha_n in opcoes_n:
                            novo_n = sorted(tela.NIVEIS)[opcoes_n.index(escolha_n)]
                    if novo_n is None:
                        self.sink.line(t("cmd.fonte.list",
                                         atual=t("fonte." + tela.NIVEIS[tela.nivel(self.cfg)]),
                                         niveis=", ".join(
                                             f"{n} {t('fonte.' + tela.NIVEIS[n])}"
                                             for n in sorted(tela.NIVEIS)),
                                         cmd=i18n.cmd("font")))
                        return "continue"
                if novo_n is None:
                    return "continue"
                self.cfg["fonte"] = novo_n
                save_config(self.cfg)
                nome_n = t("fonte." + tela.NIVEIS[novo_n])
                if os.name == "nt":
                    # Windows: a altura da letra muda de verdade, na hora.
                    if tela.fonte_windows(novo_n):
                        self.sink.line(t("cmd.fonte.now_win", nivel=nome_n), style="cyan")
                    else:
                        self.sink.line(t("cmd.fonte.teclas",
                                         teclas=tela.teclas_do_terminal("")), style="yellow")
                elif tela.reabrir(novo_n):
                    # Linux/macOS: janela nova do terminal com zoom; esta fecha em seguida.
                    self.sink.line(t("cmd.fonte.now_linux", nivel=nome_n), style="cyan")
                    return "exit"
                else:
                    self.sink.line(t("cmd.fonte.teclas",
                                     teclas=tela.teclas_do_terminal(tela.terminal_atual())),
                                   style="yellow")
            elif what == "dictate":
                return self.ditar(forcar_baixar=str(rest).strip().lower()
                                  in ("baixar", "download", "bajar"))
            elif what == "setup":
                return self._run_setup_wizard()
            elif what == "doctor":
                from .cli import doctor_report

                doctor_report(lambda texto: self.sink.line(str(texto)))
            elif what == "update":
                from . import __version__
                from .updater import (apply_update, fetch_latest, garantir_dependencias,
                                      python_bin, update_needed)

                info, err_upd = fetch_latest()
                if info is None or err_upd:
                    self.sink.line(t("cmd.update.check_fail", err=err_upd),
                                   style="yellow")
                    return "continue"
                if not update_needed(__version__, info["version"]):
                    # Mesma versao: avisa que esta atualizado e pronto, sem oferecer instalacao.
                    self.sink.line(t("cmd.update.uptodate", version=info["version"]),
                                   style="cyan")
                    return "continue"
                if not python_bin():
                    # Aberto pelo icone/arquivo executavel: nao ha pip por dentro para atualizar.
                    self.sink.line(t("cmd.update.no_pip", version=info["version"]),
                                   style="yellow")
                    return "continue"
                escolha = None
                if hasattr(self.sink, "ask_choice"):
                    escolha = self.sink.ask_choice(
                        t("cmd.update.title"),
                        t("cmd.update.ask", new=info["version"], cur=__version__),
                        [t("cmd.update.yes"), t("cmd.update.no")],
                    )
                if escolha != t("cmd.update.yes"):
                    self.sink.line(t("cmd.update.cancelled"), style="dim")
                    return "continue"
                self.sink.line(t("cmd.update.downloading", version=info["version"]),
                               style="cyan")
                ok_upd, msg_upd = apply_update(info["wheel_url"])
                if ok_upd:
                    self.sink.line(t("cmd.update.done", version=info["version"],
                                     exit=i18n.cmd("exit")), style="cyan")
                    # O wheel vai com --no-deps: sem esta passada, uma dependencia
                    # NOVA (ex.: vosk do ditado) nunca chegaria a quem atualiza.
                    ok_dep, msg_dep = garantir_dependencias()
                    if ok_dep:
                        self.sink.line(t("upd.deps_ok"), style="dim")
                    else:
                        self.sink.line(t("upd.deps_fail", erro=msg_dep), style="yellow")
                else:
                    self.sink.line(t("cmd.update.failed", err=msg_upd), style="red")
                    self.sink.line(t("cmd.update.fallback"), style="yellow")
            else:
                self.sink.line(t("cmd.unknown", help=i18n.cmd("help")))
            return "continue"

        # Caminho de imagem escrito na propria mensagem: manda a FOTO para o modelo
        # olhar (antes o TEO tentava ler como texto e ate instalava Pillow).
        if not self.pending_image:
            citadas = files_mod.achar_imagens(text)
            if citadas:
                self.pending_image = citadas[0]
                extra = ""
                if len(citadas) > 1:
                    extra = t("turn.image_more", n=len(citadas))
                self.sink.line(t("turn.image_seen",
                                 nome=os.path.basename(citadas[0]), extra=extra),
                               style="cyan")

        # Turno normal do modelo (com anexo pendente, se houver).
        user_text = f"{self.pending_attach}\n\n{text}" if self.pending_attach else text
        self.pending_attach = None
        imagem = self.pending_image
        self.pending_image = None
        # Pergunta nova cala a leitura da resposta anterior (a pessoa quer a nova).
        voz.parar()
        # Continuacao estilo Hermes: mensagens digitadas durante o turno que chegaram
        # tarde viram o proximo turno automaticamente (nada se perde).
        fila_turnos: list[str] = [user_text]
        while fila_turnos:
            turno = fila_turnos.pop(0)
            self.st["thinking"] = False
            self.st["resposta"] = False
            self._pend = ""
            try:
                # a imagem vale para o primeiro turno; os de continuacao (steering)
                # seguem so com texto
                answer = self.agent.run_turn(turno, imagem=imagem)
                imagem = None
            except KeyboardInterrupt:
                # CTRL+C no modo classico tambem para o turno (e cala a voz).
                voz.parar()
                self.agent.stop_event.set()
                answer = STOPPED_NOTE
            except LLMRateLimitError as exc:
                # Limite de uso/cota nao e defeito: amarelo (aviso) e dica certa,
                # sem mandar a pessoa reconferir URL e chave.
                self.sink.line(str(exc), style="yellow")
                self.sink.line(t("turn.rate_hint", provider=i18n.cmd("provider")),
                               style="dim")
                return "continue"
            except LLMError as exc:
                self.sink.line(str(exc), style="red")
                self.sink.line(t("turn.err_hint", setup=i18n.cmd("setup"),
                                 doctor=i18n.cmd("doctor")), style="yellow")
                return "continue"
            except Exception as exc:  # noqa: BLE001 - falha tecnica nunca vira traceback na tela
                log_error(exc, "turno do modelo")
                self.sink.line(t("turn.crash"), style="yellow")
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
                    self.sink.sep(t("turn.sep.thinking"))
                    for r in self.agent.last_reasoning:
                        trecho = r if len(r) <= 1200 else r[:1200] + "..."
                        self.sink.line(trecho, style="#808080 italic")
                    self.sink.sep(t("turn.sep.answer"))
                elif not self.st["resposta"]:
                    self.sink.sep(t("turn.sep.answer"))
                self.sink.line(md_clean(answer))
            if (not answer.strip() and answer != STOPPED_NOTE and not self.st["resposta"]):
                # Caso medido em maquina de cliente (Windows, streaming ligado): o
                # modelo gastou todo o max_tokens pensando e voltou sem texto. O aviso
                # antigo so valia para o modo SEM streaming, entao a tela ficava muda e
                # a pessoa achava que o TEO tinha travado no meio.
                if str(getattr(self.llm, "last_finish", "") or "") == "length":
                    self.sink.line(t("turn.length_thinking",
                                     thinking=i18n.cmd("thinking")), style="yellow")
                else:
                    self.sink.line(t("turn.empty", thinking=i18n.cmd("thinking")),
                                   style="yellow")
            elif (answer.strip() and answer != STOPPED_NOTE
                  and str(getattr(self.llm, "last_finish", "") or "") == "length"):
                # Resposta cortada no meio pelo teto de saida: avisa e ensina a seguir.
                self.sink.line(t("turn.cut"), style="yellow")
            if (self.cfg.get("voz") and answer.strip() and answer != STOPPED_NOTE):
                # Acessibilidade: a resposta inteira em voz alta (o raciocinio e as
                # ferramentas ficam de fora: quem ouve nao quer o rascunho).
                voz.falar(answer)
            if answer == STOPPED_NOTE:
                # Turno parado nao emenda as mensagens guardadas: quem mandou parar
                # decide se quer continuar. Elas sao devolvidas como aviso.
                descartadas = 0
                while self.agent.pop_steer() is not None:
                    descartadas += 1
                if descartadas:
                    self.sink.line(t("turn.dropped", n=descartadas), style="yellow")
                break
            while True:
                sobra = self.agent.pop_steer()
                if sobra is None:
                    break
                self.sink.line(t("turn.echo", texto=sobra), style="cyan")
                fila_turnos.append(sobra)
        self.print_ctx()
        return "continue"

"""Nucleo do chat: a mesma logica para a tela fixa (tui.py) e o modo classico.

Comandos com barra (/ajuda, /nov, /modelo...), atalhos @ e /, turno do modelo e
menu de licenca vivem aqui. A saida passa por um "sink", assim cada tela decide
como mostrar (rich no modo classico; area de texto na tela fixa).
"""

import os
import re
from pathlib import Path

from rich.console import Console

from .agent import Agent, STOPPED_NOTE
from .approvals import Gate
from .config import SESSION_FILE, save_config
from .llm import LLM, LLMError
from .tools import files as files_mod

LINE = "-" * 46  # separador visual (ASCII puro; nao depende de unicode no terminal)


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
        ("Roda do mouse ou PageUp/PageDown", "reler o texto que subiu na tela"),
        ("CTRL+C com a linha vazia", "fecha o TEO"),
        ("Seta para cima / para baixo", "repete o que voce ja digitou (historico guardado)"),
    ]),
    ("Comandos:", [
        ("/ajuda", "esta lista"),
        ("/nov", "conversa nova (limpa contexto; memoria e skills continuam)"),
        ("/mem <texto>", "grava uma preferencia sua na memoria permanente"),
        ("/modelos", "lista os modelos disponiveis no servidor"),
        ("/modelo <nome ou numero>", "troca o modelo usado (fica salvo)"),
        ("/provedores", "lista os provedores cadastrados (deepseek, local...)"),
        ("/provedor <nome ou numero>", "troca o provedor em uso na hora (fica salvo)"),
        ("/thinking <nivel>", "nivel: auto off minimum low medium high xhigh max ultra"),
        ("/ctx", "medidor do contexto atual"),
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

    # ----- streaming -> sink ---------------------------------------------------
    def _on_reasoning(self, chunk: str) -> None:
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
        txt = (f"contexto: {usage['pct']}% de {usage['budget']} chars "
               f"({usage['messages']} mensagens)")
        if hasattr(self.sink, "set_ctx"):
            # tela fixa: o medidor mora na ULTIMA linha da tela, nao no historico
            self.sink.set_ctx(txt)
            if self.agent.last_compressed:
                self.sink.line("Contexto compactado: as partes antigas viraram um resumo.", style="dim")
            elif usage["pct"] >= 70:
                self.sink.line("Contexto enchendo; sera compactado na proxima rodada pesada.", style="dim")
            return
        color = "green" if usage["pct"] < 50 else ("yellow" if usage["pct"] < 80 else "red")
        self.sink.sep()
        self.sink.line(txt, style=color)
        if self.agent.last_compressed:
            self.sink.line("Contexto compactado: as partes antigas viraram um resumo.", style="dim")
        elif usage["pct"] >= 70:
            self.sink.line("Contexto enchendo; sera compactado na proxima rodada pesada.", style="dim")

    def banner(self) -> None:
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
                    self.sink.line(f"Nao consegui ler {target}: {exc}", style="red")
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
            elif name == "/mem" and rest:
                from .tools import memory

                self.sink.line(memory.add(rest, target="user"))
            elif name == "/skills":
                from .tools.skills import discover, index_lines

                lines = index_lines(discover())
                self.sink.line("\n".join(f"- {line}" for line in lines) or "(nenhuma skill ainda)")
            elif name == "/modelos":
                try:
                    self.model_list = self.llm.list_models()
                    if not self.model_list:
                        self.sink.line("O servidor nao publica lista de modelos.")
                    for i, m in enumerate(self.model_list, start=1):
                        marca = " (atual)" if m == self.cfg["model"] else ""
                        self.sink.line(f"  {i}. {m}{marca}")
                except LLMError as exc:
                    self.sink.line(str(exc), style="red")
            elif name == "/modelo" and rest:
                alvo2 = rest
                if rest.isdigit() and self.model_list:
                    idx = int(rest) - 1
                    if 0 <= idx < len(self.model_list):
                        alvo2 = self.model_list[idx]
                    else:
                        self.sink.line("Numero fora da lista. Use /modelos para ver.")
                        return "continue"
                self.cfg["model"] = alvo2
                save_config(self.cfg)
                self.sink.line(f"Modelo agora: {alvo2} (salvo no config)", style="cyan")
                self._ask_thinking_level()
            elif name == "/provedores":
                from .config import list_profiles as lp

                names = lp(self.cfg)
                if not names:
                    self.sink.line("(nenhum provedor cadastrado ainda)")
                for i, p in enumerate(names, start=1):
                    prof = self.cfg["profiles"][p]
                    marca = " (em uso)" if p == self.cfg.get("active_profile") else ""
                    self.sink.line(f"  {i}. {p}{marca} - {prof['model']} em {prof['base_url']}")
            elif name == "/provedor" and rest:
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
                else:
                    self.sink.line("Provedor nao encontrado. /provedores mostra a lista.")
            elif name == "/thinking":
                levels = ("auto", "off", "minimum", "low", "medium", "high",
                          "xhigh", "max", "ultra")
                alvo_t = rest.lower()
                if alvo_t in levels + ("on",):
                    self.cfg["thinking"] = alvo_t
                    save_config(self.cfg)
                    self.llm.cfg["thinking"] = alvo_t
                    self.sink.line(f"Pensamento: {alvo_t} (salvo)", style="cyan")
                elif not rest:
                    self.sink.line(
                        f"Pensamento atual: {self.cfg.get('thinking', 'auto')}. Uso: "
                        "/thinking auto|off|minimum|low|medium|high|xhigh|max|ultra")
                else:
                    self.sink.line(
                        "Nivel desconhecido. Use: "
                        "/thinking auto|off|minimum|low|medium|high|xhigh|max|ultra")
            elif name == "/ctx":
                self.print_ctx()
            else:
                self.sink.line("Comando desconhecido. /ajuda mostra a lista.")
            return "continue"

        # Turno normal do modelo (com anexo pendente, se houver).
        self.st["thinking"] = False
        self.st["resposta"] = False
        self._pend = ""
        user_text = f"{self.pending_attach}\n\n{text}" if self.pending_attach else text
        self.pending_attach = None
        try:
            answer = self.agent.run_turn(user_text)
        except KeyboardInterrupt:
            # CTRL+C no modo classico tambem para o turno.
            self.agent.stop_event.set()
            answer = STOPPED_NOTE
        except LLMError as exc:
            self.sink.line(str(exc), style="red")
            self.sink.line("Dica: rode 'bgh doctor' para checar a conexao com o modelo.", style="yellow")
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
        self.print_ctx()
        return "continue"

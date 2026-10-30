"""Tela do Motor (estilo Hermes): a linha de digitar fica SEMPRE embaixo
e as mensagens vao direto para o historico natural do proprio terminal.

Mudanca 0.2.0: em vez de uma "tela alternativa" isolada, o
Motor agora escreve as mensagens no rolamento de verdade do terminal - igual
aos programas de sempre. A rodinha do mouse e a barra lateral que funcionam
sao as DO PROPRIO TERMINAL (nada de rolagem interna), e ao sair a conversa
continua visivel para cima e para baixo.

Pensado para pessoa idosa e crianca:
  - cores claras e grandes de longe: resposta em BRANCO, pensamento do modelo em
    CINZA ESCURO (facil de separar o que e "rascunho" do que e a resposta final);
  - barra de baixo sempre visivel: medidor de contexto, sinal de "rodando" com
    bonequinho de espera (| / - \\) e o que apertar para falar/parar/sair;
  - PARAR a resposta do modelo = CTRL+C ou ESC (um toque, como no Hermes);
  - reler o texto que subiu = roda do mouse ou barra lateral do SEU terminal;
  - setas cima/baixo recuperam o que voce ja digitou (como no bash);
  - menu de licenca aparece na propria tela e a resposta e um numero + ENTER.

Sem prompt_toolkit instalado (ou sem terminal interativo), o cli cai no modo
classico de rolagem automaticamente.
"""

import asyncio
import shutil
import textwrap
import threading

from prompt_toolkit.application import Application
from prompt_toolkit.application.run_in_terminal import run_in_terminal
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Label

from .chat_core import LINE, ChatCore, build_approval_options, help_lines, parse_approval_choice
from .config import INPUT_HISTORY_FILE

FRAMES = "|/-\\"  # bonequinho de espera do "rodando..." na barra de baixo


class LineBoard:
    """Agrupa os pedacos coloridos em linhas logicas (cores preservadas).

    Cada bloco guarda (estilo, texto, aberto?). O streaming vai engrossando o
    ultimo bloco ABERTO do mesmo estilo; estilo novo ou bloco fechado comecam
    outro. Assim cada pedaco mantem a sua cor.
    """

    def __init__(self):
        self.entries: list[list] = []  # [estilo, texto, aberto?]

    def add(self, text: str, style: str | None, newline: bool) -> None:
        if not newline:
            if self.entries and self.entries[-1][2] and self.entries[-1][0] == style:
                self.entries[-1][1] += text
                return
            self.entries.append([style, str(text), True])
            return
        if self.entries:
            self.entries[-1][2] = False
        for part in str(text).split("\n"):
            self.entries.append([style, part, False])

    def close_last(self) -> None:
        if self.entries:
            self.entries[-1][2] = False

    def rows(self, width: int) -> list[list]:
        """Linhas: cada linha e uma lista de pedacos (estilo, texto).

        Segmentos abertos (parts do streaming e da ajuda) pertencem a MESMA
        linha; o texto junto e quebrado na largura da janela sem perder as cores.
        """
        # margem de 2 colunas: o texto nunca encosta na borda da tela (estilo Hermes)
        width = max(10, width - 2)
        groups: list[list] = []
        cur: list = []
        for style, text, is_open in self.entries:
            cur.append((style, text))
            if not is_open:
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)

        lines: list[list] = []
        for g in groups:
            combined = "".join(t for _, t in g)
            if not combined:
                lines.append([(g[0][0], "")])
                continue
            if len(g) == 1:
                style = g[0][0]
                # quebra dura do modelo (\n) vira linha propria; so embrulha o que
                # passar da largura - assim lista aparece uma por linha, nao corrida
                for hard in combined.split("\n"):
                    for w in textwrap.wrap(hard, width=width) or [""]:
                        lines.append([(style, w)])
                continue
            # varios pedacos numa linha (ex.: ajuda): corta na largura exata
            # para manter as colunas alinhadas; cada pedaco mantem sua cor
            spans: list[list] = []
            pos = 0
            for st, t in g:
                spans.append([pos, pos + len(t), st])
                pos += len(t)
            for off in range(0, len(combined), width):
                pieces = []
                for a, b, st in spans:
                    s, e = max(a, off), min(b, off + width)
                    if s < e:
                        pieces.append((st, combined[s:e]))
                lines.append(pieces or [(g[0][0], "")])
        return lines


def flush_plan(rows: list, open_tail: bool, printed: int, wrap_width: int) -> tuple[int, list]:
    """Quais linhas ja podem sair para o historico do terminal (e nao repetem).

    A ultima linha ainda 'aberta' (streaming pode engrossar) so sai quando ja
    esta cheia - assim texto longo aparece aos poucos, sem reimprimir nada.
    """
    if not rows:
        return printed, []
    if open_tail:
        last_len = sum(len(t) for _, t in rows[-1])
        safe = len(rows) if last_len >= wrap_width else len(rows) - 1
    else:
        safe = len(rows)
    safe = max(printed, safe)
    return safe, rows[printed:safe]


STYLE = Style.from_dict(
    {
        "th": "#808080",       # pensamento do modelo: cinza escuro
        "an": "#ffffff",       # resposta: branco claro
        "tool": "#5f87af",     # eventos de ferramenta: azul suave
        "voce": "#5fd7ff",     # eco da fala do usuario: azul-claro
        "rule": "dim",
        "input": "bold",
        "footer": "bg:#333333 #ffffff",
        "footer.hot": "bg:#333333 #ffcc00 bold",
    }
)


class TuiSink:
    """Affiche do Motor: tudo vira texto colorido no historico do terminal."""

    def __init__(self, emit, close_line, state, width_fn=None):
        self.emit = emit
        self.close_line = close_line
        self.state = state
        self.width_fn = width_fn  # devolve a largura util da janela (para os divisores)

    def line(self, text: str, style: str | None = None) -> None:
        self.emit(str(text), style=style)

    def parts(self, segments: list) -> None:
        """Uma linha montada em pedacos com cores diferentes (ex.: ajuda)."""
        for text, style in segments:
            self.emit(text, newline=False, style=style)
        self.close_line()

    def sep(self, title: str | None = None) -> None:
        self.emit(LINE)
        if title:
            self.emit(title)
            self.emit(LINE)

    def border(self) -> None:
        """Divisor '=' ate perto da borda da tela (abre e fecha blocos)."""
        width = max(20, (self.width_fn() if self.width_fn else 46) - 2)
        self.emit("=" * width, style="class:rule")

    def thinking(self, text: str) -> None:
        self.emit(text, newline=False, style="th")

    def answer(self, text: str) -> None:
        self.emit(text, newline=False, style="an")

    def tool_event(self, name: str, preview: str) -> None:
        self.emit(f"> {name}: {preview}", style="tool")

    def status(self, text: str) -> None:
        pass  # a barra de baixo monta o status sozinha a partir do estado

    def set_ctx(self, text: str) -> None:
        """Medidor de contexto vai na ULTIMA linha da tela, nao no historico."""
        self.state["ctx"] = text
        self.emit("", newline=False)  # payload vazio so forca o repaint da barra

    def ask_approval(self, label: str, detail: str, allow_always: bool) -> str:
        """Menu de licenca impresso no historico; o worker aguarda a resposta."""
        options, codes = build_approval_options(allow_always)
        self.line("")
        self.line("== O TEO precisa da sua licenca ==")
        self.line(label)
        for ln in str(detail).splitlines()[:8]:
            if ln.strip():
                self.line(f"   {ln}")
        self.line("O que voce quer fazer? Digite o numero e ENTER:")
        for i, opt in enumerate(options, start=1):
            self.line(f"  [{i}] {opt}")
        self.line(f"(Enter sozinho = [{len(options)}] nao / cancelar; ESC tambem nega)")
        ev = threading.Event()
        holder = {"codes": codes, "choice": "d", "ev": ev, "deny_code": "d",
                  "hot": "LICENCA PENDENTE: digite o numero e ENTER (ESC = nao)"}
        self.state["approval"] = holder  # GIL: atribuir dict simples e seguro
        self.emit("", newline=False)  # payload vazio so forca o repaint da barra
        ev.wait()
        self.state["approval"] = None
        return holder["choice"]

    def ask_choice(self, title: str, label: str, options: list) -> str:
        """Menu numerico de escolha (ex.: nivel de pensamento).

        Enter sozinho ou ESC = opcao 1 ('manter atual') - nunca escolhe algo
        por engano.
        """
        self.line("")
        self.line(f"== {title} ==")
        self.line(label)
        for i, opt in enumerate(options, start=1):
            self.line(f"  [{i}] {opt}")
        self.line("(Enter sozinho = [1] manter; ESC tambem mantem)")
        ev = threading.Event()
        holder = {"codes": options, "choice": options[0], "ev": ev,
                  "deny_code": options[0],
                  "hot": "OPCAO PENDENTE: digite o numero e ENTER (ESC = manter)"}
        self.state["approval"] = holder
        self.emit("", newline=False)  # forca o repaint da barra
        ev.wait()
        self.state["approval"] = None
        return holder["choice"]


def run_tui(cfg: dict) -> int:
    board = LineBoard()
    # Historico estilo bash: setas cima/baixo repetem o que ja foi digitado;
    # sobrevive ao fechar/abrir (arquivo em ~/.bgh/input_history.txt).
    in_buf = Buffer(multiline=False, history=FileHistory(str(INPUT_HISTORY_FILE)))
    state = {"busy": False, "approval": None, "stop_hits": 0, "spin": 0, "ctx": None}
    printed = {"n": 0, "cols": 0}
    app: Application | None = None

    def _term_size() -> tuple[int, int]:
        try:
            size = app.output.get_size()
            return max(40, size.columns), max(12, size.rows)
        except Exception:  # noqa: BLE001 - antes do primeiro paint nao ha output
            ts = shutil.get_terminal_size()
            return max(40, ts.columns), max(12, ts.rows)

    # ----- saida: linhas prontas vao direto para o rolamento do terminal -------
    def _schedule(fn, *args) -> None:
        loop = getattr(app, "loop", None)
        if loop is not None and threading.current_thread() is not threading.main_thread():
            try:
                loop.call_soon_threadsafe(fn, *args)
                return
            except RuntimeError:
                pass  # app fechando; ignora o resto da saida
        fn(*args)

    def _flush_print() -> None:
        cols, _ = _term_size()
        if cols != printed["cols"]:
            # janela mudou de largura: o que ja saiu nao volta a ser impresso
            printed["cols"] = cols
            printed["n"] = len(board.rows(cols))
        rows = board.rows(cols)
        open_tail = bool(board.entries and board.entries[-1][2])
        n_new, to_print = flush_plan(rows, open_tail, printed["n"], max(10, cols - 2))
        printed["n"] = n_new
        for segs in to_print:
            frags = []
            for style, piece in segs:
                cls = f"class:{style}" if style in ("th", "an", "tool", "voce") else (style or "")
                frags.append((cls, piece))
            frags.append(("", "\n"))  # print_text NAO acrescenta a quebra sozinho
            run_in_terminal(lambda f=frags: app.print_text(f))

    def _apply(text: str, style: str | None, newline: bool) -> None:
        board.add(text, style, newline)
        _flush_print()
        app.invalidate()

    def _close_line() -> None:
        board.close_last()
        _flush_print()
        app.invalidate()

    def _refresh() -> None:
        app.invalidate()

    def emit(text: str = "", newline: bool = True, style: str | None = None) -> None:
        """Thread-safe: do worker, agenda no loop do app; da UI, aplica na hora."""
        if not text and not newline:
            _schedule(_refresh)
            return
        _schedule(_apply, text, style, newline)

    def close_line() -> None:
        _schedule(_close_line)

    sink = TuiSink(emit, close_line, state, width_fn=lambda: _term_size()[0])
    core = ChatCore(cfg, sink)

    # ----- layout: so a parte fixa (o resto e o historico do proprio terminal) --
    rule_top = Window(height=1, char="-", style="class:rule")
    input_win = Window(BufferControl(in_buf), height=1, style="class:input")
    input_row = VSplit([Label(text="voce> ", dont_extend_width=True), input_win])
    rule_bottom = Window(height=1, char="-", style="class:rule")
    footer_win = Window(FormattedTextControl(lambda: _status_text(state)),
                        height=1, style="class:footer")
    root = HSplit([rule_top, input_row, rule_bottom, footer_win])
    layout = Layout(root)

    kb = KeyBindings()

    def resolve_approval(raw_text: str) -> None:
        holder = state.get("approval")
        if holder is None:
            return
        holder["choice"] = parse_approval_choice(
            raw_text, holder["codes"], holder.get("deny_code", "d"))
        state["approval"] = None
        holder["ev"].set()

    def request_stop_or_exit() -> None:
        """CTRL+C/ESC: nega licenca > para resposta em andamento > fecha o TEO."""
        holder = state.get("approval")
        if holder is not None:
            resolve_approval(holder.get("deny_code", "d"))
            emit("(cancelado)")
            return
        if state["busy"]:
            state["stop_hits"] += 1
            if state["stop_hits"] >= 2:
                app.exit()  # segunda pressao: saida de seguranca se algo travar
                return
            core.stop()
            emit("(parando...)")
            return
        if in_buf.text:
            in_buf.reset()
            return
        app.exit()

    @kb.add("enter")
    def _enter(event):
        text = in_buf.text
        # guarda para as setas cima/baixo; saida nao entra (crianca nao pode
        # sem querer dar ENTER duas vezes e fechar o TEO)
        if text.strip() and text.strip().lower() not in ("/sair", "/exit", "/quit"):
            in_buf.append_to_history()
        in_buf.reset()
        if state.get("approval") is not None:
            resolve_approval(text)
            return
        if state["busy"]:
            in_buf.text = text  # nao deixa a pessoa perder o que digitou
            emit("(estou respondendo; para parar: CTRL+C ou ESC)")
            return
        if not text.strip():
            return
        state["busy"] = True
        state["stop_hits"] = 0
        emit(f"voce> {text}", style="voce")  # eco na hora: a tela nunca fica muda

        def _worker():
            try:
                action = core.submit(text)
                if action == "exit":
                    _schedule(app.exit)
            except Exception as exc:  # noqa: BLE001 - UI nunca cai junto com o turno
                emit(f"(erro interno inesperado: {type(exc).__name__}: {exc})")
            finally:
                state["busy"] = False
                state["stop_hits"] = 0
                _schedule(app.invalidate)

        threading.Thread(target=_worker, daemon=True).start()

    @kb.add("c-c")
    def _ctrl_c(event):
        request_stop_or_exit()

    @kb.add("escape")
    def _esc(event):
        # ESC para/licenca/limpa linha, mas NUNCA fecha o app sozinho (crianca
        # apertando ESC por engano nao perde a conversa; fechar e so CTRL+C).
        if state.get("approval") is not None or state["busy"]:
            request_stop_or_exit()
        elif in_buf.text:
            in_buf.reset()

    @kb.add("c-d")
    def _eof(event):
        if not state["busy"] and not in_buf.text:
            app.exit()

    @kb.add("up")
    def _hist_up(event):
        in_buf.history_backward()  # linha anterior digitada (como no bash)

    @kb.add("down")
    def _hist_down(event):
        in_buf.history_forward()   # volta para a mais nova / rascunho atual

    def _start_ui() -> None:
        """Relogio do bonequinho + carga do historico das setas + boas-vindas.

        Tudo aqui ja roda DENTRO do loop do app (pre_run): timer via task de
        fundo (call_later em pre_run pega loop antigo), historico carregando
        na abertura, e o banner saindo pelo caminho normal de impressao.
        """
        async def spin() -> None:
            while True:
                await asyncio.sleep(0.3)
                if state["busy"]:
                    state["spin"] = (state["spin"] + 1) % 4
                    app.invalidate()

        app.create_background_task(spin())
        in_buf.load_history_if_not_yet_loaded()
        core.banner()      # boas-vindas + ajuda ja no historico do terminal
        core.print_ctx()   # medidor comeca na barra de baixo, sem esperar a 1a resposta

    app = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,  # historico natural do terminal (rodinha/barra dele)
        style=STYLE,
    )
    layout.focus(input_win)

    try:
        app.run(pre_run=_start_ui)
    finally:
        # Se a pessoa fechou o app com uma licenca pendente, nega e libera o worker.
        holder = state.get("approval")
        if holder is not None:
            holder["choice"] = "d"
            holder["ev"].set()
    return 0


def _status_text(state: dict):
    holder = state.get("approval")
    width = max(40, shutil.get_terminal_size().columns)
    def fit(txt: str) -> str:
        # a barra de baixo NUNCA pode embrulhar: cortamos com folga de 2 colunas
        return txt if len(txt) <= width - 2 else txt[:width - 3]
    if holder is not None:
        hot = holder.get("hot", "LICENCA PENDENTE: digite o numero e ENTER (ESC = nao)")
        return [("class:footer.hot", fit(hot))]
    ctx = state.get("ctx")
    if state["busy"]:
        pieces = [FRAMES[state["spin"]], "rodando...", "PARA PARAR: CTRL+C ou ESC"]
        if ctx:
            pieces.append(ctx)
        return [("class:footer.hot", fit(" | ".join(pieces)))]
    base = ("ENTER = falar | CTRL+C com linha vazia = sair | /ajuda | "
            "reler: roda do mouse ou barra lateral do seu terminal")
    if ctx and len(ctx) + len(base) + 3 > width:
        # com o medidor de contexto na frente, encurta a explicacao para caber
        base = "ENTER = falar | CTRL+C vazio = sair | /ajuda"
    return [("class:footer", fit(f"{ctx} | {base}" if ctx else base))]

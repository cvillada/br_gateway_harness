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
import re
import shutil
import textwrap
import threading
import time
from collections.abc import Callable

from prompt_toolkit.application import Application
from prompt_toolkit.application.run_in_terminal import run_in_terminal
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.filters import Condition
from prompt_toolkit.styles import Style
from prompt_toolkit.utils import get_cwidth

from . import i18n, palco, tela, voz
from .chat_core import (LINE, ChatCore, build_approval_options, help_lines, log_error,
                        parse_approval_choice)
from .config import INPUT_HISTORY_FILE
from .i18n import t

FRAMES = "|/-\\"  # bonequinho de espera do "rodando..." na barra de baixo


def linhas_de_tela(texto: str, largura: int) -> int:
    """Quantas linhas DE TELA o texto ocupa numa janela de 'largura' colunas.

    Uma frase longa nao tem '\n' nenhum, mas ocupa varias linhas de tela. Quem
    dimensiona a janela de digitar pela contagem de '\n' deixa o texto sem
    lugar para a continuacao e ele e empurrado para a esquerda ate sumir.
    """
    livre = max(10, int(largura))
    total = 0
    for linha in str(texto or "").split("\n"):
        total += max(1, -(-get_cwidth(linha) // livre))
    return total


def quer_continuar(texto: str) -> bool:
    """Terminou com barra invertida? Entao o ENTER pula linha em vez de enviar.

    Regra de shell, que funciona em qualquer terminal (inclusive no cmd do
    Windows, onde Alt+Enter e o atalho de tela cheia): "primeira linha \\" + Enter
    continua na linha de baixo.
    """
    return str(texto or "").rstrip().endswith("\\")


def tira_barra_final(texto: str) -> str:
    """Remove a barra invertida de continuacao e devolve o que fica no buffer."""
    bruto = str(texto or "").rstrip()
    return bruto[:-1].rstrip() if bruto.endswith("\\") else bruto


class LineBoard:
    """Agrupa os pedacos coloridos em linhas logicas (cores preservadas).

    Cada bloco guarda (estilo, texto, aberto?). O streaming vai engrossando o
    ultimo bloco ABERTO do mesmo estilo; estilo novo ou bloco fechado comecam
    outro. Assim cada pedaco mantem a sua cor.
    """

    def __init__(self):
        self.entries: list[list] = []  # [estilo, texto, aberto?]
        # Cache das linhas ja quebradas. Sem isso, CADA pedaco de streaming
        # re-quebrava TODA a conversa (textwrap em texto gigante): num turno longo
        # com saida grande de ferramenta/navegador a tela travava e nem o CTRL+C
        # era atendido (crash real em maquina de cliente, Windows).
        self._rows_cache: list[list] = []
        self._rows_consumidas = 0   # entradas que ja viraram linha no cache
        self._rows_width = 0        # largura usada no cache
        self._fechadas = 0          # entradas FECHADAS (podem ser cacheadas)

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
        self._fechadas = len(self.entries)

    def close_last(self) -> None:
        if self.entries:
            self.entries[-1][2] = False
            self._fechadas = len(self.entries)

    def rows(self, width: int) -> list[list]:
        """Linhas: cada linha e uma lista de pedacos (estilo, texto).

        Segmentos abertos (parts do streaming e da ajuda) pertencem a MESMA
        linha; o texto junto e quebrado na largura da janela sem perder as cores.
        As linhas FECHADAS ficam em cache (nunca mudam); so a cauda aberta e
        re-quebrada a cada pedaco.
        """
        # margem de 2 colunas: o texto nunca encosta na borda da tela (estilo Hermes)
        width = max(10, width - 2)
        if width != self._rows_width:
            # janela mudou de largura: tudo tem que ser quebrado de novo
            self._rows_cache = []
            self._rows_consumidas = 0
            self._rows_width = width
        alvo = min(self._fechadas, len(self.entries))
        if alvo < self._rows_consumidas:      # entradas sumiram (reset): refaz
            self._rows_cache = []
            self._rows_consumidas = 0
        if alvo > self._rows_consumidas:
            self._rows_cache = self._rows_cache + self._rows_de(
                self.entries[self._rows_consumidas:alvo], width)
            self._rows_consumidas = alvo
        cauda = self._rows_de(self.entries[self._rows_consumidas:], width)
        return self._rows_cache + cauda

    def _rows_de(self, entries: list, width: int) -> list[list]:
        """Quebra um pedaco de entradas (sempre comecando em fronteira de grupo)."""
        groups: list[list] = []
        cur: list = []
        for style, text, is_open in entries:
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
            for st, pedaco in g:
                spans.append([pos, pos + len(pedaco), st])
                pos += len(pedaco)
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


# Cores da tela viva em bgh/tela.py: o /fundo escolhe a paleta e a letra de
# contraste (fundo claro -> letra escura). Aqui fica so a paleta PADRAO, usada
# quando a pessoa nao escolheu cor nenhuma.
STYLE = Style.from_dict(tela.estilo_prompt("padrao"))


class TuiSink:
    """Affiche do Motor: tudo vira texto colorido no historico do terminal."""

    # A tela fixa sabe abrir menu numerado de pastas/arquivos (o nucleo pergunta).
    menu_arquivos = True

    def __init__(self, emit, close_line, state, width_fn=None):
        # callback que repinta a tela quando o /fundo muda
        self.tema_fn: Callable[[], None] | None = None
        # callback que poe o texto ditado (/ditar) na linha de digitar
        self.preencher_fn: Callable[[str], None] | None = None
        # callback do bip do terminal (aviso sonoro do ditado)
        self.bipar_fn: Callable[[], None] | None = None
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
        self.state["fase"] = "modelo"   # palco: o pedido chegou no modelo
        self.emit(text, newline=False, style="th")

    def answer(self, text: str) -> None:
        self.state["fase"] = "resposta"  # palco: a resposta comecou a voltar
        self.emit(text, newline=False, style="an")

    def on_usage(self, uso) -> None:
        """Contagem de tokens que o servidor informou neste pedido (palco)."""
        self.state["tokens"] = dict(uso) if uso else None

    def rodada_nova(self) -> None:
        """Cada chamada do modelo e uma rodada: o palco mostra em que rodada esta."""
        self.state["rodada"] = int(self.state.get("rodada") or 0) + 1

    def tool_event(self, name: str, preview: str) -> None:
        # guarda o que esta rodando agora: a barra de baixo mostra a ferramenta e ha
        # quantos segundos ela esta em andamento (espera longa deixa de parecer trava)
        self.state["tool"] = name
        self.state["tool_since"] = time.time()
        self.state["fase"] = "ferramenta"  # palco: o pedido esta na mesa de trabalho
        self.emit(f"> {name}: {preview}", style="tool")

    def status(self, text: str) -> None:
        pass  # a barra de baixo monta o status sozinha a partir do estado

    def aplicar_tema(self) -> None:
        """Repinta a tela com a cor escolhida no /fundo (callback de run_tui)."""
        fn = getattr(self, "tema_fn", None)
        if fn is not None:
            fn()

    def preencher(self, texto: str) -> None:
        """Texto ditado entra na linha de digitar: a pessoa confere antes do ENTER."""
        fn = getattr(self, "preencher_fn", None)
        if fn is not None:
            fn(str(texto))

    def bipar(self) -> None:
        """Bip do terminal: avisa "pode falar" / "parei de ouvir" sem olhar a tela."""
        fn = getattr(self, "bipar_fn", None)
        if fn is not None:
            fn()

    def set_ctx(self, text: str, pct: int | None = None, hot_pct: int | None = None,
                extra: str = "") -> None:
        """Medidor de contexto vai na ULTIMA linha da tela, nao no historico.

        extra: trecho opcional ('| teto; o servidor entrega N tokens'); a barra
        so mostra o extra quando cabe inteiro na janela - em janela estreita ele
        e' descartado antes de cortar qualquer outra parte do medidor.
        """
        self.state["ctx"] = text
        self.state["ctx_extra"] = extra or ""
        self.state["ctx_pct"] = pct
        self.state["ctx_hot_pct"] = hot_pct
        self.emit("", newline=False)  # payload vazio so forca o repaint da barra

    def ask_line(self, prompt: str, default: str = "", secret: bool = False) -> str:
        """Pergunta de texto livre na tela fixa (assistente do /configurar).

        A pergunta sai no historico e a resposta entra pela MESMA linha de sempre
        (embaixo): Enter sozinho = valor padrao, ESC = padrao tambem. Na tela fixa
        o que se digita aparece na linha; para chave em segredo, o caminho segue
        sendo 'bgh setup' na janela de comando (usa getpass la).
        """
        self.line("")
        self.line(prompt + (t("tui.default", default=default) if default else ""))
        if secret:
            self.line(t("tui.secret_hint"))
        ev = threading.Event()
        holder = {"codes": [], "choice": default, "ev": ev, "deny_code": default,
                  "free_text": True, "default": default,
                  "hot": t("tui.hot.config")}
        self.state["approval"] = holder  # GIL: atribuir dict simples e seguro
        self.emit("", newline=False)  # payload vazio so forca o repaint da barra
        ev.wait()
        self.state["approval"] = None
        return holder["choice"]

    def ask_approval(self, label: str, detail: str, allow_always: bool) -> str:
        """Menu de licenca impresso no historico; o worker aguarda a resposta."""
        options, codes = build_approval_options(allow_always)
        self.line("")
        self.line(t("approval.header"))
        self.line(label)
        for ln in str(detail).splitlines()[:8]:
            if ln.strip():
                self.line(f"   {ln}")
        self.line(t("tui.approval_question"))
        for i, opt in enumerate(options, start=1):
            self.line(f"  [{i}] {opt}")
        self.line(t("tui.approval_hint", n=len(options)))
        ev = threading.Event()
        holder = {"codes": codes, "choice": "d", "ev": ev, "deny_code": "d",
                  "hot": t("tui.hot.license")}
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
        self.line(t("tui.choice_hint"))
        ev = threading.Event()
        holder = {"codes": options, "choice": options[0], "ev": ev,
                  "deny_code": options[0],
                  "hot": t("tui.hot.choice")}
        self.state["approval"] = holder
        self.emit("", newline=False)  # forca o repaint da barra
        ev.wait()
        self.state["approval"] = None
        return holder["choice"]


def run_tui(cfg: dict) -> int:
    board = LineBoard()
    # Historico estilo bash: setas cima/baixo repetem o que ja foi digitado;
    # sobrevive ao fechar/abrir (arquivo em ~/.bgh/input_history.txt).
    # multiline=True: o buffer aceita "\n" (Ctrl+J / barra invertida). O ENTER
    # continua enviando - quem manda nisso e o binding abaixo, nao o padrao.
    in_buf = Buffer(multiline=True, history=FileHistory(str(INPUT_HISTORY_FILE)))
    state = {"busy": False, "approval": None, "stop_hits": 0, "spin": 0, "ctx": None,
             "ctx_pct": None, "fase": None, "palco_frame": 0, "tokens": None, "palco_hold": 0,
             "busy_since": 0.0, "tool": None, "tool_since": 0.0}
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
        try:
            rows = board.rows(cols)
        except Exception as exc:  # noqa: BLE001 - desenho nunca pode derrubar o app
            log_error(exc, "quebra de linha da tela")
            return
        open_tail = bool(board.entries and board.entries[-1][2])
        n_new, to_print = flush_plan(rows, open_tail, printed["n"], max(10, cols - 2))
        printed["n"] = n_new
        tem_fundo = bool(tela.paleta(tela.cor(cfg)).get("bg"))
        for segs in to_print:
            frags = []
            usado = 0
            for style, piece in segs:
                if style in ("th", "an", "tool", "voce"):
                    cls = f"class:{style}"
                else:
                    cls = tela.classe(style, tem_fundo)
                frags.append((cls, piece))
                usado += get_cwidth(piece)
            if tem_fundo:
                # completa a linha com a cor de fundo ate a borda: sem isso a
                # resposta seria uma faixa clara no meio de uma tela escura.
                sobra = " " * max(0, cols - usado)
                if sobra:
                    frags.append(("class:bg", sobra))
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

    pintado = {"cor": tela.cor(cfg)}

    def _aplicar_tema() -> None:
        """Pinta o fundo AGORA e troca a paleta (letra de contraste junto)."""
        if app is None:
            return
        nome = tela.cor(cfg)
        seq = tela.escape_fundo(nome)
        if not seq and pintado["cor"] != "padrao":
            seq = tela.RESET_FUNDO     # /fundo padrao: devolve a cor do terminal AGORA
        pintado["cor"] = nome
        try:
            app.output.write_raw(seq)
            app.output.flush()
        except Exception as exc:  # noqa: BLE001 - cor e enfeite, nunca necessidade
            log_error(exc, "cor de fundo da tela")
        app.style = Style.from_dict(tela.estilo_prompt(nome))
        app.invalidate()

    sink.tema_fn = _aplicar_tema    # o /fundo chama por aqui (ver chat_core)

    def _preencher(texto: str) -> None:
        """Poe o texto ditado na linha de digitar, com o cursor no fim."""
        def _aplica() -> None:
            try:
                atual = in_buf.text
                in_buf.text = (atual + " " + texto).strip() if atual.strip() else texto
                in_buf.cursor_position = len(in_buf.text)
            except Exception as exc:  # noqa: BLE001 - linha nunca derruba o app
                log_error(exc, "texto ditado na linha")
            if app is not None:
                app.invalidate()

        _schedule(_aplica)

    sink.preencher_fn = _preencher

    def _bipar() -> None:
        """BEL do terminal: som curto que nao depende de audio do sistema."""
        if app is None:
            return
        try:
            app.output.write_raw("\a")
            app.output.flush()
        except Exception:  # noqa: BLE001 - terminal sem campainha: segue sem bip
            pass

    sink.bipar_fn = _bipar
    core = ChatCore(cfg, sink)

    # ----- layout: so a parte fixa (o resto e o historico do proprio terminal) --
    rule_top = Window(height=1, char="-", style="class:rule")

    def _altura_entrada():
        """Altura da janela de digitar em linhas DE TELA (nao em '\\n').

        Linha comprida quebra em varias linhas de tela: se a janela ficasse com
        a contagem de linhas logicas (1), o prompt_toolkit nao teria onde
        desenhar a continuacao e empurrava o texto para a esquerda, comendo o
        comeco da frase (reclamacao real: "a linha desaparece no canto direito").
        Cresce ate 8 linhas e nunca empurra a barra de baixo para fora da tela.
        """
        try:
            cols, rows = _term_size()
            visuais = linhas_de_tela(in_buf.text, cols - get_cwidth(t("sink.prompt")))
            try:                       # palco aberto come 5 linhas da tela
                ocupado = 5 if _palco_largo_visivel() else 0
            except Exception:          # noqa: BLE001 - primeira pintura
                ocupado = 0
            return max(1, min(8, visuais, rows - 4 - ocupado))
        except Exception:  # noqa: BLE001 - desenho nunca derruba a tela
            return 1

    # wrap_lines=True: a linha de digitar QUEBRA embaixo em vez de rolar para a
    # esquerda. Precisa vir junto com a altura acima - so um dos dois nao basta
    # (com altura 1 o texto quebrado aparece cortado; sem a quebra ele sai da tela).
    input_win = Window(BufferControl(in_buf), height=_altura_entrada,
                       style="class:input", wrap_lines=True)

    # Rotulo da linha de digitar desenhado A CADA pintura: o /lingua troca
    # 'voce>' por 'you>'/'tu>' na mesma tela, sem reiniciar.
    prompt_win = Window(FormattedTextControl(lambda: [("", t("sink.prompt"))]),
                        dont_extend_width=True, height=1, style="class:input")
    input_row = VSplit([prompt_win, input_win])
    rule_bottom = Window(height=1, char="-", style="class:rule")

    def _largura() -> int:
        # Largura da JANELA do app (a mesma que o resto da tela usa), nunca a do
        # buffer do console: no Windows as duas divergem e a barra quebrava.
        try:
            return int(getattr(app, "output").get_size().columns)
        except Exception:  # noqa: BLE001 - antes do primeiro paint nao ha output
            return int(shutil.get_terminal_size().columns)

    def _footer_frags():
        return _status_text(state, _largura())

    footer_win = Window(FormattedTextControl(_footer_frags),
                        height=1, style="class:footer")

    # ----- palco: o caminho do pedido, so enquanto o TEO trabalha --------------
    palco_ligado = bool(cfg.get("palco", True))

    def _palco_frags():
        return palco.stage_lines(state, _largura(), time.time(),
                                 int(state.get("palco_frame") or 0))

    def _palco_visivel_agora() -> bool:
        """Ligado e com pedido em curso OU mostrando a entrega por 1,6s."""
        return palco.visivel(palco_ligado, state.get("fase"), bool(state["busy"]),
                             float(state.get("palco_hold") or 0), time.time())

    def _palco_largo_visivel() -> bool:
        return bool(_palco_visivel_agora() and _largura() >= palco.MIN_WIDTH)

    def _palco_curto_visivel() -> bool:
        return bool(_palco_visivel_agora() and _largura() < palco.MIN_WIDTH)

    palco_largo = ConditionalContainer(
        content=Window(FormattedTextControl(_palco_frags), height=5, style="class:palco"),
        filter=Condition(_palco_largo_visivel))
    palco_curto = ConditionalContainer(
        content=Window(FormattedTextControl(_palco_frags), height=1, style="class:palco"),
        filter=Condition(_palco_curto_visivel))

    root = HSplit([rule_top, palco_largo, palco_curto, input_row, rule_bottom, footer_win])
    layout = Layout(root)

    kb = KeyBindings()

    def resolve_approval(raw_text: str) -> None:
        holder = state.get("approval")
        if holder is None:
            return
        if holder.get("free_text"):
            # Texto livre (assistente /configurar): o que foi digitado e a resposta;
            # Enter sozinho ou ESC fica com o padrao da pergunta.
            holder["choice"] = raw_text.strip() or holder.get("default", "")
        else:
            holder["choice"] = parse_approval_choice(
                raw_text, holder["codes"], holder.get("deny_code", "d"))
        state["approval"] = None
        holder["ev"].set()

    def request_stop_or_exit() -> None:
        """CTRL+C/ESC: cala a voz > nega licenca > para a resposta > fecha o TEO."""
        voz.parar()      # a voz nunca continua falando depois do pedido de parar
        holder = state.get("approval")
        if holder is not None:
            resolve_approval(holder.get("deny_code", "d"))
            emit(t("tui.cancelled"))
            return
        if state["busy"]:
            state["stop_hits"] += 1
            if state["stop_hits"] >= 2:
                app.exit()  # segunda pressao: saida de seguranca se algo travar
                return
            core.stop()
            emit(t("tui.stopping"))
            return
        if in_buf.text:
            in_buf.reset()
            return
        app.exit()

    def _pula_linha() -> None:
        """Insere uma quebra de linha no lugar de enviar a mensagem."""
        if state.get("approval") is not None:
            return  # menu/licenca pendente: ENTER resolve a escolha, nao o texto
        in_buf.insert_text("\n")

    @kb.add("c-j")
    def _ctrl_j(event):
        _pula_linha()          # Ctrl+J: funciona em qualquer terminal

    @kb.add("escape", "enter")
    def _alt_enter(event):
        _pula_linha()          # Alt+Enter: Linux/macOS com Meta; no cmd e tela cheia

    @kb.add("enter")
    def _enter(event):
        text = in_buf.text
        # Barra invertida no fim = continuar na linha de baixo (regra de shell),
        # que funciona em qualquer terminal - inclusive no cmd do Windows.
        if text.strip() and state.get("approval") is None and quer_continuar(text):
            in_buf.text = tira_barra_final(text) + "\n"
            in_buf.cursor_position = len(in_buf.text)
            return
        # guarda para as setas cima/baixo; saida nao entra (crianca nao pode
        # sem querer dar ENTER duas vezes e fechar o TEO)
        if text.strip() and i18n.canon(text.strip().lower().lstrip("/")) != "exit":
            in_buf.append_to_history()
        in_buf.reset()
        if state.get("approval") is not None:
            resolve_approval(text)
            return
        if state["busy"]:
            digitado = text.strip()
            if digitado and not digitado.startswith("/"):
                core.steer(digitado)  # estilo Hermes: o modelo recebe na proxima rodada
                emit(t("turn.echo", texto=digitado), style="voce")
                emit(t("tui.steer_hint"), style="cyan")
                return
            if digitado:
                in_buf.text = text  # comando / fica na linha, para enviar depois
                emit(t("tui.busy_cmd"))
                return
            emit(t("tui.busy_hint"))
            return
        if not text.strip():
            return
        state["busy"] = True
        state["stop_hits"] = 0
        state["busy_since"] = time.time()   # a barra de baixo conta os segundos da espera
        state["tool"] = None
        # O palco e do PEDIDO ao agente/modelo. Comando de barra (/ajuda, /modelo),
        # menu de arquivo e /doctor nao passam pelo modelo: nao desenham a trilha.
        eh_pedido = not text.strip().startswith(("/", "@"))
        state["fase"] = "pedido" if eh_pedido else None
        state["tokens"] = None              # contador do turno anterior nao serve
        state["palco_hold"] = 0             # recolhimento do palco: turno novo manda
        state["rodada"] = 0                 # contador de rodadas do turno
        emit(t("turn.echo", texto=text), style="voce")  # eco na hora: a tela nunca fica muda

        def _worker():
            try:
                action = core.submit(text)
                if action == "exit":
                    _schedule(app.exit)
            except Exception as exc:  # noqa: BLE001 - UI nunca cai junto com o turno
                log_error(exc, "tela do TEO")   # traceback completo so no arquivo, nunca na tela
                emit(t("tui.crash"), style="yellow")
            finally:
                state["busy"] = False
                state["stop_hits"] = 0
                state["tool"] = None
                if not eh_pedido:
                    # Comando/menu: nada de palco depois de terminar.
                    state["fase"] = None
                    state["palco_hold"] = 0
                    if app is not None:
                        _schedule(app.invalidate)
                else:
                    # O palco fica 1,6s mostrando a entrega (e os tokens do ultimo
                    # pedido, que o servidor so informa no fim): sem esse respiro o
                    # numero chegaria junto com o recolhimento e nunca apareceria.
                    state["fase"] = "pronto"
                    alvo_recolha = time.time() + 1.6
                    state["palco_hold"] = alvo_recolha
                    if app is not None:
                        _schedule(app.invalidate)

                    def _recolhe(espera_ate=alvo_recolha) -> None:
                        time.sleep(1.7)
                        if state.get("palco_hold") == espera_ate and not state["busy"]:
                            state["fase"] = None
                            state["palco_hold"] = 0
                            if app is not None:
                                _schedule(app.invalidate)

                    threading.Thread(target=_recolhe, daemon=True).start()

        threading.Thread(target=_worker, daemon=True).start()

    @kb.add("c-c")
    def _ctrl_c(event):
        request_stop_or_exit()

    def _ditar_agora() -> None:
        """Tecla de ditado: mesma coisa que o /ditar, sem digitar comando.

        Quem nao enxerga nao pode depender de lembrar de um comando: a tecla faz
        o mesmo caminho (baixa o modelo na primeira vez, ouve, poe o texto na
        linha). Roda em thread como o ENTER, para a tela nao travar.
        """
        if state["busy"] or state.get("approval") is not None:
            return
        state["busy"] = True
        state["stop_hits"] = 0
        state["busy_since"] = time.time()
        state["tool"] = t("tui.listening")   # a barra de baixo diz "ouvindo Ns"
        state["tool_since"] = time.time()
        state["fase"] = None
        state["tokens"] = None
        state["palco_hold"] = 0

        def _worker() -> None:
            try:
                core.ditar()
            except Exception as exc:  # noqa: BLE001 - a tela nunca cai pelo ditado
                log_error(exc, "ditado pela tecla")
                emit(t("tui.crash"), style="yellow")
            finally:
                state["busy"] = False
                state["stop_hits"] = 0
                state["tool"] = None
                if app is not None:
                    _schedule(app.invalidate)

        threading.Thread(target=_worker, daemon=True).start()

    @kb.add("f2")
    def _f2(event):
        _ditar_agora()          # F2: falar em vez de digitar (qualquer tamanho)

    @kb.add(" ")
    def _espaco(event):
        # A tecla mais facil de achar no teclado. Com a linha VAZIA ela comeca a
        # ouvir; com texto (ou menu/licenca aberto), e espaco normal.
        if in_buf.text or state.get("approval") is not None:
            in_buf.insert_text(" ")
        else:
            _ditar_agora()

    @kb.add("escape")
    def _esc(event):
        # ESC cala a VOZ e para/licenca/limpa linha, mas NUNCA fecha o app sozinho
        # (crianca apertando ESC por engano nao perde a conversa; fechar e CTRL+C).
        # Decisao de projeto: CTRL+C com a linha vazia SAI, entao nao serve para calar -
        # a tecla de calar e o ESC (o texto digitado fica, so a voz para).
        calava = voz.falando()
        voz.parar()
        if state.get("approval") is not None or state["busy"]:
            request_stop_or_exit()
        elif in_buf.text and not calava:
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

    def _pinta_fundo() -> None:
        """Manda a cor de fundo para o terminal (OSC 11); ignorada se nao aceitar."""
        if app is None:
            return
        try:
            app.output.write_raw(tela.escape_fundo(tela.cor(cfg)))
            app.output.flush()
        except Exception as exc:  # noqa: BLE001 - cor e enfeite, nunca necessidade
            log_error(exc, "cor de fundo da abertura")

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

        _pinta_fundo()      # cor escolhida ANTES de a primeira tela desenhar
        app.create_background_task(spin())
        in_buf.load_history_if_not_yet_loaded()
        core.banner()      # boas-vindas + ajuda ja no historico do terminal
        core.print_ctx()   # medidor comeca na barra de baixo, sem esperar a 1a resposta
        core.check_update_on_start()   # uma vez, em segundo plano (versao nova?)

    app = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,  # historico natural do terminal (rodinha/barra dele)
        style=Style.from_dict(tela.estilo_prompt(tela.cor(cfg))),
    )
    layout.focus(input_win)

    try:
        app.run(pre_run=_start_ui)
    except KeyboardInterrupt:
        # CTRL+C durante o desenho (ex.: texto gigante sendo quebrado) saia como
        # traceback na cara do usuario. Agora fecha limpo, como o /sair.
        pass
    finally:
        # Sair da tela cala a voz: nada de resposta falando num terminal ja fechado.
        voz.parar()
        # Devolve a cor de fundo do terminal (o TEO nao sequestra a janela).
        if tela.paleta(tela.cor(cfg)).get("bg"):
            tela.escrever(tela.RESET_FUNDO)
        # Se a pessoa fechou o app com uma pergunta/licenca pendente, devolve o
        # padrao dela (negar no menu, valor padrao no assistente) e libera o worker.
        holder = state.get("approval")
        if holder is not None:
            holder["choice"] = holder.get("deny_code", "d")
            holder["ev"].set()
    return 0


def compact_ctx(ctx: str, espaco: int) -> str:
    """Versao curta do medidor de contexto que ainda caiba em 'espaco' colunas.

    'contexto: 80% de 160000 chars (45.71k toks) (102 mensagens)' vira
    'ctx 80% de 160k (45.71k toks) (102 msg)'. Devolve '' quando nem o mais curto
    cabe: ai a barra mostra so o aviso, que e o que a pessoa precisa ler.
    """
    texto = str(ctx or "")
    m = re.match(r"(?:contexto|context): (\d+)% (?:de|of) (\d+) chars"
                 r"(?: \((~?[\d.]+[kM]?)(?: (?:de|of) ([\d.]+[kM]?))? toks\))?"
                 r" \((\d+) (?:mensagens|messages|mensajes)\)", texto)
    if not m:
        return texto if len(texto) <= espaco else ""
    pct, orcamento, toks, teto, msgs = (m.group(1), int(m.group(2)), m.group(3),
                                        m.group(4), m.group(5))
    base = (f"{orcamento // 1000}k" if orcamento >= 1000 and orcamento % 1000 == 0
            else str(orcamento))
    de, msg, toks_u = t("tui.of"), t("tui.msg"), t("tui.toks")
    candidatos = []
    if toks and teto:
        candidatos.append(f"ctx {pct}% {de} {base} ({toks}/{teto} {toks_u}) ({msgs} {msg})")
    if toks:
        candidatos.append(f"ctx {pct}% {de} {base} ({toks} {toks_u}) ({msgs} {msg})")
    candidatos.append(f"ctx {pct}% {de} {base} ({msgs} {msg})")
    if toks:
        candidatos.append(f"ctx {pct}% {de} {base} ({toks} {toks_u})")
    candidatos.extend([f"ctx {pct}% {de} {base}", f"ctx {pct}%"])
    for candidato in candidatos:
        if len(candidato) <= max(0, espaco):
            return candidato
    return ""


def _status_text(state: dict, columns: int | None = None):
    """Barra de baixo: o aviso manda, o medidor cede espaco.

    Regra (pedido do usuario, medida no cliente): o aviso - rodando/parar,
    licenca pendente, teclas - NUNCA pode cair. O medidor de contexto e o
    primeiro a encolher (versao compacta) e, se ainda nao couber, sai da barra.
    A largura vem da JANELA do app: shutil.get_terminal_size pode devolver a
    largura do BUFFER do console no Windows, e cortar pela medida errada faz a
    linha quebrar em duas e a segunda metade desaparecer da tela.
    """
    holder = state.get("approval")
    if columns is None:
        columns = shutil.get_terminal_size().columns
    width = max(40, int(columns))

    def fit(txt: str) -> str:
        # a barra de baixo NUNCA pode embrulhar: cortamos com folga de 2 colunas
        return txt if len(txt) <= width - 2 else txt[:width - 3]

    if holder is not None:
        hot = holder.get("hot", t("tui.hot.license"))
        return [("class:footer.hot", fit(hot))]

    ctx = state.get("ctx") or ""
    if state["busy"]:
        # Espera vira numero visivel: 'rodando... 47s' + a ferramenta em andamento.
        # Sem isso, silencio na tela e lido como programa travado (reclamacao real).
        decorrido = int(time.time() - float(state.get("busy_since") or time.time()))
        pieces = [FRAMES[state["spin"]], t("tui.running", s=decorrido)]
        tool = state.get("tool")
        if tool:
            tool_s = int(time.time() - float(state.get("tool_since") or time.time()))
            pieces.append(f"{tool} {tool_s}s")
        pieces.append(t("tui.stop_keys"))
        linha = " | ".join(pieces)
        if ctx:
            # Medidor so entra se caber inteiro: o aviso de parar e mais importante.
            medidor = compact_ctx(ctx, width - 3 - len(linha) - 3)
            if medidor:
                linha = f"{linha} | {medidor}"
        return [("class:footer.hot", fit(linha))]

    base_longa = t("tui.footer_long", help=i18n.cmd("help"))
    base_curta = t("tui.footer_short", help=i18n.cmd("help"))
    extra = state.get("ctx_extra") or ""
    medidor_longo = ctx
    if ctx and extra and len(ctx) + len(extra) + len(base_curta) + 3 <= width:
        medidor_longo = ctx + extra
    candidatos: list[str] = []
    if medidor_longo:
        candidatos.append(f"{medidor_longo} | {base_longa}")
        candidatos.append(f"{medidor_longo} | {base_curta}")
        curto = compact_ctx(ctx, width - 3 - len(base_curta) - 3)
        if curto:
            candidatos.append(f"{curto} | {base_curta}")
    candidatos.append(base_longa)
    candidatos.append(base_curta)
    # Primeira combinacao que cabe INTEIRA: nada de corte no meio de palavra nem
    # numero de contexto picado no fim da linha.
    escolhida = next((c for c in candidatos if len(c) <= width - 2), base_curta)

    # Contexto perto do limite: a barra fica na cor de alerta (amarelo) tambem
    # quando esta parada, no MESMO ponto em que a compactacao vai comecar.
    pct = state.get("ctx_pct") or 0
    hot = state.get("ctx_hot_pct") or 85
    estilo = "class:footer.hot" if pct >= hot else "class:footer"
    return [(estilo, fit(escolhida))]

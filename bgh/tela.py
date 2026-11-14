"""Cor de fundo e tamanho da letra da tela do TEO (acessibilidade visual).

Publico do TEO e crianca, idoso e pessoa com baixa visao. Duas coisas que o
terminal nao deixa um programa fazer do jeito facil, resolvidas assim:

- COR DE FUNDO: o padrao OSC 11 (`ESC ] 11 ; #RRGGBB BEL`) pinta a janela INTEIRA,
  inclusive o texto que ja rolou, e o TEO escolhe letra de contraste - fundo claro
  vira letra escura, fundo escuro vira letra clara. Terminal que nao conhece a
  sequencia ignora sem quebrar nada. Ao sair, a cor volta a ser a do terminal
  (OSC 111).
- TAMANHO DA LETRA: no Windows o console tem API de verdade
  (SetCurrentConsoleFontEx) e o tamanho muda na hora. No Linux/macOS a letra e do
  terminal: o TEO reabre uma janela nova com zoom (gnome-terminal, xterm, kitty...)
  ou ensina as teclas do terminal da pessoa.

Regra do projeto: nada aqui pode derrubar a conversa. Toda funcao publica devolve
True/False e engole excecao de terminal exotico.
"""

import os
import shutil
import subprocess
import sys

# ---------------------------------------------------------------------------
# Cores: nome -> (fundo, letra, letra fraca, destaque, eco do usuario, rodape)
# Fundo claro pede letra escura e vice-versa; os pares abaixo passam no teste de
# contraste da suite (WCAG), que roda em tests/test_smoke.py.
# ---------------------------------------------------------------------------
CORES = {
    "padrao": {"bg": None, "fg": "#ffffff", "dim": "#808080", "accent": "#5f87af",
               "user": "#5fd7ff", "footer_bg": "#333333", "footer_fg": "#ffffff",
               "hot": "#ffcc00",
               # cores que so a tela padrao usa (mantem o visual de antes do /fundo)
               "sel": "#000000 bg:#5fd7ff bold", "tk": "#87d7ff", "dim2": "#d7d7d7"},
    "preto": {"bg": "#000000", "fg": "#ffffff", "dim": "#9e9e9e", "accent": "#5f87af",
              "user": "#5fd7ff", "footer_bg": "#333333", "footer_fg": "#ffffff",
              "hot": "#ffcc00", "warn": "#ffcc00", "err": "#ff5f5f"},
    "branco": {"bg": "#ffffff", "fg": "#101010", "dim": "#55606b", "accent": "#0b5394",
               "user": "#6a1b9a", "footer_bg": "#d7d7d7", "footer_fg": "#101010",
               "hot": "#8a3b00", "warn": "#8a3b00", "err": "#a1171a"},
    "amarelo": {"bg": "#ffd54f", "fg": "#1a1a1a", "dim": "#4a3f00", "accent": "#0b5394",
                "user": "#4a148c", "footer_bg": "#e8c23c", "footer_fg": "#1a1a1a",
                "hot": "#7a2e00", "warn": "#6b2f00", "err": "#a1171a"},
    "verde": {"bg": "#a5d6a7", "fg": "#102010", "dim": "#2f5d34", "accent": "#0b5394",
              "user": "#4a148c", "footer_bg": "#8bc38e", "footer_fg": "#102010",
              "hot": "#7a2e00", "warn": "#5a3300", "err": "#a1171a"},
    "azul": {"bg": "#10457f", "fg": "#ffffff", "dim": "#c3d8ef", "accent": "#7fd7ff",
             "user": "#ffd75f", "footer_bg": "#0b3160", "footer_fg": "#ffffff",
             "hot": "#ffd75f", "warn": "#ffd75f", "err": "#ff9b9b"},
    "vermelho": {"bg": "#7f1d1d", "fg": "#ffffff", "dim": "#f3d0d0", "accent": "#ffd75f",
                 "user": "#8fd7ff", "footer_bg": "#5f1515", "footer_fg": "#ffffff",
                 "hot": "#ffd75f", "warn": "#ffd75f", "err": "#ffc2c2"},
}

# Ordem do menu (/fundo): comeca no padrao (nao mexe em nada) e nas seis cores.
NOMES = ("padrao", "branco", "amarelo", "verde", "azul", "vermelho", "preto")

RESET_FUNDO = "\x1b]110\x07\x1b]111\x07"   # devolve letra e fundo do terminal


def cor(cfg: dict | None) -> str:
    """Cor escolhida no config; qualquer valor estranho volta para 'padrao'."""
    nome = str((cfg or {}).get("cor_fundo") or "padrao").strip().lower()
    return nome if nome in CORES else "padrao"


_SINONIMOS = {
    "branco": "branco", "blanco": "branco", "white": "branco",
    "amarelo": "amarelo", "amarillo": "amarelo", "yellow": "amarelo",
    "verde": "verde", "green": "verde",
    "azul": "azul", "blue": "azul",
    "vermelho": "vermelho", "rojo": "vermelho", "red": "vermelho",
    "preto": "preto", "negro": "preto", "black": "preto",
    "padrao": "padrao", "default": "padrao", "estandar": "padrao",
    "normal": "padrao", "nenhuma": "padrao",
}

_NIVEIS_SINONIMOS = {"normal": 1, "grande": 2, "large": 2, "maior": 3, "larger": 3,
                     "mayor": 3, "enorme": 4, "huge": 4, "grande+": 4}


def nome_do_texto(texto: str) -> str | None:
    """'branco', 'white', 'blanco' -> 'branco'; None quando nao e cor conhecida."""
    return _SINONIMOS.get(str(texto or "").strip().lower())


def nivel_do_texto(texto: str) -> int | None:
    """'grande', 'maior', 'enorme' (nos tres idiomas) -> numero do nivel."""
    limpo = str(texto or "").strip().lower()
    if limpo.isdigit() and int(limpo) in NIVEIS:
        return int(limpo)
    return _NIVEIS_SINONIMOS.get(limpo)


def paleta(nome: str) -> dict:
    return CORES.get(nome, CORES["padrao"])


def escape_fundo(nome: str) -> str:
    """Sequencias que pintam fundo E letra do terminal ('' = cor do terminal).

    OSC 11 pinta o fundo da janela inteira (inclusive o texto ja rolado) e OSC 10
    troca a letra padrao - sem o OSC 10, o texto sem cor propria continuaria sendo
    a letra do tema do terminal (branco no branco, por exemplo).
    """
    p = paleta(nome)
    fundo = p.get("bg")
    if not fundo:
        return ""
    return f"\x1b]10;{p['fg']}\x07\x1b]11;{fundo}\x07"


_BASE = {"dim": "th", "cyan": "accent", "yellow": "warn", "red": "err", "bold": "an"}


def classe(estilo: str | None, com_fundo: bool) -> str:
    """Estilo cru do sink -> classe da paleta legivel sobre a cor de fundo."""
    if not com_fundo:
        return estilo or ""
    if not estilo:
        return "class:an"          # texto sem estilo usa a letra de contraste
    cru = str(estilo).strip().lower()
    if cru in _BASE:
        return "class:" + _BASE[cru]
    if "#" in cru:                 # cor fixa (ex.: "#808080 italic"): letra fraca
        return "class:th"
    return estilo or ""


def escrever(texto: str, saida=None) -> None:
    """Manda a sequencia para o terminal; terminal que nao conhece ignora."""
    if not texto:
        return
    try:
        (saida or sys.stdout).write(texto)
        (saida or sys.stdout).flush()
    except Exception:  # noqa: BLE001 - cor e enfeite, nunca necessidade
        pass


def _luminancia(cor_hex: str) -> float:
    """Luminancia relativa (WCAG 2.x) de '#rrggbb'."""
    valor = cor_hex.lstrip("#")
    canais = []
    for i in (0, 2, 4):
        c = int(valor[i:i + 2], 16) / 255.0
        canais.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canais[0] + 0.7152 * canais[1] + 0.0722 * canais[2]


def contraste(fundo: str, letra: str) -> float:
    """Razao de contraste entre duas cores (1 = invisivel, 21 = preto no branco)."""
    a, b = _luminancia(fundo), _luminancia(letra)
    claro, escuro = max(a, b), min(a, b)
    return (claro + 0.05) / (escuro + 0.05)


def estilo_prompt(nome: str) -> dict:
    """Classes de estilo da tela fixa para esta cor (prompt_toolkit Style)."""
    p = paleta(nome)
    rodape = f"bg:{p['footer_bg']} {p['footer_fg']}"
    classes = {
        "th": p["dim"],                 # pensamento do modelo
        "an": p["fg"],                  # resposta
        "tool": p["accent"],            # ferramenta
        "voce": p["user"],              # eco do que a pessoa digitou
        "rule": p["dim"] if p.get("bg") else "dim",
        "input": f"bold {p['fg']}",
        "footer": rodape,
        "footer.hot": f"{rodape} bold {p['hot']}",
        "palco": p["fg"],
        "palco.sel": p.get("sel") or f"{p['fg']} bg:{p['accent']} bold",
        "palco.on": f"{p['accent']} bold",
        "palco.tk": p.get("tk") or p["accent"],
        "palco.dim": p.get("dim2") or p["dim"],
        # classes usadas pela traducao de estilo cru (aviso/erro/destaque)
        "accent": p.get("accent") or p["fg"],
        "warn": p.get("warn") or "#ffcc00",
        "err": p.get("err") or "#ff5f5f",
    }
    if p.get("bg"):
        classes["bg"] = f"bg:{p['bg']}"          # preenchimento das linhas impressas
        classes["root"] = f"bg:{p['bg']} {p['fg']}"
        classes["input"] = f"bold bg:{p['bg']} {p['fg']}"
        classes["th"] = f"bg:{p['bg']} {p['dim']}"
        classes["an"] = f"bg:{p['bg']} {p['fg']}"
        classes["rule"] = f"bg:{p['bg']} {p['dim']}"
        classes["palco"] = f"bg:{p['bg']} {p['fg']}"
        classes["palco.dim"] = f"bg:{p['bg']} {p.get('dim2') or p['dim']}"
        classes["footer"] = f"bg:{p['footer_bg']} {p['footer_fg']}"
        for chave, cor_txt in (("accent", classes["accent"]), ("warn", classes["warn"]),
                               ("err", classes["err"])):
            classes[chave] = f"bg:{p['bg']} {cor_txt}"
    return classes


def estilo_rich(nome: str) -> str:
    """Estilo do modo classico (rich): 'letra on fundo' ou so a letra."""
    p = paleta(nome)
    return f"{p['fg']} on {p['bg']}" if p.get("bg") else ""


def eh_claro(nome: str) -> bool:
    fundo = paleta(nome).get("bg")
    return bool(fundo) and _luminancia(fundo) > 0.5


# ---------------------------------------------------------------------------
# Tamanho da letra
# ---------------------------------------------------------------------------
NIVEIS = {1: "normal", 2: "grande", 3: "maior", 4: "enorme"}
_PX = {1: 16, 2: 20, 3: 24, 4: 30}      # Windows: altura da celula em pixels
_ZOOM = {1: 1.0, 2: 1.3, 3: 1.6, 4: 2.0}  # Linux/macOS: fator de zoom do terminal


def nivel(cfg: dict | None) -> int:
    try:
        n = int((cfg or {}).get("fonte") or 1)
    except (TypeError, ValueError):
        return 1
    return n if n in NIVEIS else 1


def pixels(cfg: dict | None) -> int:
    return _PX[nivel(cfg)]


def zoom(cfg: dict | None) -> float:
    return _ZOOM[nivel(cfg)]


def fonte_windows(nivel_escolhido: int) -> bool:
    """Aplica a altura da letra no console do Windows (API de verdade)."""
    altura = _PX.get(int(nivel_escolhido), 16)
    try:
        import ctypes
        from ctypes import wintypes

        class COORD(ctypes.Structure):
            _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

        class FONT_INFOEX(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.ULONG), ("nFont", wintypes.DWORD),
                        ("dwFontSize", COORD), ("FontFamily", wintypes.UINT),
                        ("FontWeight", wintypes.UINT),
                        ("FaceName", wintypes.WCHAR * 32)]

        info = FONT_INFOEX()
        info.cbSize = ctypes.sizeof(FONT_INFOEX)
        info.dwFontSize = COORD(0, altura)   # largura 0 = a do sistema
        info.FontFamily = 54                 # FF_MODERN | TMPF_TRUETYPE
        info.FontWeight = 400
        info.FaceName = "Consolas"
        windll = getattr(ctypes, "windll")                 # so existe no Windows
        saida = windll.kernel32.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        return bool(windll.kernel32.SetCurrentConsoleFontEx(
            saida, False, ctypes.byref(info)))
    except Exception:  # noqa: BLE001 - console exotico: segue como esta
        return False


# Emuladores que aceitam abrir uma janela ja com zoom/fonte maior.
# {programa: molde com {zoom} ou {px} + como passar o comando}
_TERMINAIS = {
    "gnome-terminal": (["gnome-terminal", "--zoom={zoom}"], "--"),
    "xfce4-terminal": (["xfce4-terminal", "--zoom={zoom}"], "-x"),
    "xterm": (["xterm", "-fs", "{px}"], "-e"),
    "kitty": (["kitty", "--override", "font_size={px}"], "-e"),
    "alacritty": (["alacritty", "-o", "font.size={px}"], "-e"),
    "urxvt": (["urxvt", "-fn", "xft:monospace:size={pt}"], "-e"),
}

_TECLAS = {
    "gnome-terminal": "CTRL e + (ou CTRL e a roda do mouse para cima)",
    "xfce4-terminal": "CTRL e + (ou CTRL e a roda do mouse para cima)",
    "konsole": "CTRL e + (ou CTRL e a roda do mouse para cima)",
    "kitty": "CTRL e + (ou CTRL e SHIFT e =)",
    "alacritty": "CTRL e +",
    "xterm": "CTRL e o botao direito do mouse (menu de tamanho)",
}


def terminal_atual() -> str:
    """Qual emulador esta rodando o TEO ('' quando nao da para saber)."""
    ambiente = os.environ
    pistas = ((ambiente.get("KITTY_WINDOW_ID"), "kitty"),
              (ambiente.get("ALACRITTY_LOG"), "alacritty"),
              (ambiente.get("KONSOLE_VERSION"), "konsole"),
              (ambiente.get("XTERM_VERSION"), "xterm"),
              (ambiente.get("XFCE4_TERMINAL"), "xfce4-terminal"),
              (ambiente.get("VTE_VERSION"), "gnome-terminal"))
    for marca, nome in pistas:
        if marca and shutil.which(nome):
            return nome
    for nome in ("gnome-terminal", "xfce4-terminal", "konsole", "xterm", "kitty",
                 "alacritty"):
        if ambiente.get("DISPLAY") and shutil.which(nome):
            return nome
    return ""


def teclas_do_terminal(nome: str) -> str:
    return _TECLAS.get(nome, "CTRL e + (ou o menu do seu terminal: Aumentar fonte)")


def argv_teo() -> list[str]:
    """Comando que reabre o TEO (executavel empacotado ou 'python -m bgh')."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "bgh"]


def comando_zoom(nome_terminal: str, nivel_escolhido: int) -> list[str] | None:
    """Linha de comando que abre o terminal com letra maior rodando o TEO."""
    molde = _TERMINAIS.get(nome_terminal)
    if not molde:
        return None
    base, separador = molde
    gabarito = {"zoom": f"{_ZOOM.get(int(nivel_escolhido), 1.0):.1f}",
                "px": str(_PX.get(int(nivel_escolhido), 16)),
                "pt": str(max(9, _PX.get(int(nivel_escolhido), 16) * 3 // 4))}
    argv = [parte.format(**gabarito) for parte in base]
    return argv + [separador] + argv_teo()


def reabrir(nivel_escolhido: int) -> bool:
    """Abre uma janela nova do TEO com a letra maior (Linux/macOS)."""
    comando = comando_zoom(terminal_atual(), nivel_escolhido)
    if not comando:
        return False
    try:
        subprocess.Popen(comando, cwd=os.getcwd(), stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except OSError:
        return False

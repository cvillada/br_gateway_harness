"""ver_tela: print da TELA da pessoa (o que esta na frente dela agora).

Para que serve: site que exige login. O TEO nao digita senha e nao automatiza
sessao - quem loga e a pessoa. Ela deixa a pagina aberta e pede "olha a minha
tela": aqui a gente fotografa os pixels, e o modelo (com visao) le o que esta ali.
Vale para qualquer coisa logada: e-mail, WhatsApp Web, painel, ERP.

Regra de ouro desta ferramenta: e a acao MAIS INVASIVA do TEO (o print leva tudo
que estiver aberto, inclusive o que nao tem nada a ver com o pedido). Por isso
ela pede licenca ANTES de fotografar (`Gate.print_screen_ok`), com opcao "sempre"
guardada no allowlist - e o `ver_pagina` (arquivo/URL) continua SEM licenca, que
e o que mantem o laco de TDD sem interrupcao.

O print sai como marca "IMAGEM: <caminho>" no resultado: o agent le e manda a
imagem para o modelo (resultado de ferramenta nao carrega imagem).
"""

from __future__ import annotations

import os
import secrets
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

from ..config import BGH_HOME
from .guard import STOPPED_NOTE, stopped

SPEC = {
    "type": "function",
    "function": {
        "name": "ver_tela",
        "description": (
            "Tira um print da TELA da pessoa (todas as janelas visiveis) e devolve a "
            "imagem para voce olhar. Use quando a pessoa pedir para ver algo que esta "
            "na tela dela e que exige login (caixa de e-mail, painel, conversa): ela "
            "loga, deixa aberto e pede. Pede licenca antes de fotografar. NAO use para "
            "site que voce mesmo abriu com abrir_navegador - nesse caso use ver_pagina "
            "com o endereco do site (ou origem=aba): a janela do TEO pode ficar aberta e "
            "a leitura sai do texto da pagina, sem print de tela."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "espera": {
                    "type": "integer",
                    "description": ("Segundos antes de fotografar (padrao 1, maximo 10), "
                                    "para a pessoa clicar na janela que quer mostrar"),
                },
            },
            "required": [],
        },
    },
}

MAX_ESPERA_S = 10
TIMEOUT_S = 20
# Print da tela nao e arquivo de trabalho: some em 2h, nao em 24h.
RETENCAO_HORAS = 2


def pasta() -> Path:
    alvo = BGH_HOME / "telas"
    alvo.mkdir(parents=True, exist_ok=True)
    return alvo


def limpar(horas: float = RETENCAO_HORAS) -> int:
    removidos = 0
    limite = time.time() - max(0.0, horas) * 3600
    try:
        for item in pasta().iterdir():
            if not item.is_file():
                continue
            try:
                if item.stat().st_mtime >= limite:
                    continue
                item.unlink()
                removidos += 1
            except OSError:
                continue
    except OSError:
        return removidos
    return removidos


def _ambiente_x() -> dict:
    """Ambiente com DISPLAY/XAUTHORITY quando a sessao nao herdou (SSH/servico).

    Caso real: rodando por SSH o processo nao tem DISPLAY e o scrot responde
    "Can't open X display" mesmo com o dono da maquina logado na frente.
    """
    env = dict(os.environ)
    if not env.get("DISPLAY") and not env.get("WAYLAND_DISPLAY"):
        if Path("/tmp/.X11-unix/X0").exists():
            env["DISPLAY"] = ":0"
        env.setdefault("XAUTHORITY", str(Path.home() / ".Xauthority"))
    return env


def _tamanho_png(png: Path) -> tuple[int, int] | None:
    """(largura, altura) lidos do proprio PNG (sem Pillow)."""
    try:
        with open(png, "rb") as fonte:
            cabecalho = fonte.read(24)
    except OSError:
        return None
    if len(cabecalho) < 24 or cabecalho[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    try:
        largura, altura = struct.unpack(">II", cabecalho[16:24])
    except struct.error:
        return None
    return largura, altura


def _tentativas_linux() -> list[tuple[str, list[str]]]:
    return [
        ("scrot", ["scrot", "-o"]),
        ("gnome-screenshot", ["gnome-screenshot", "-f"]),
        ("grim", ["grim"]),
        ("import", ["import", "-window", "root"]),
    ]


def _capturar(png: Path) -> tuple[bool, str]:
    """(ok, ferramenta_usada_ou_erro). Tenta os capturadores do sistema."""
    env = _ambiente_x()
    if os.name == "nt":
        return _capturar_windows(png)
    if sys.platform == "darwin":
        return _capturar_mac(png)

    tentados = []
    for nome, base in _tentativas_linux():
        exe = shutil.which(nome)
        if not exe:
            continue
        tentados.append(nome)
        comando = [exe] + base[1:]
        # scrot, gnome-screenshot e import aceitam o arquivo no fim; grim tambem.
        comando.append(str(png))
        try:
            subprocess.run(comando, capture_output=True, text=True,
                           timeout=TIMEOUT_S, env=env)
        except (OSError, subprocess.SubprocessError):
            continue
        if png.is_file() and png.stat().st_size > 0:
            return True, nome
        # falhou: apaga o resto e tenta o proximo capturador
    if not tentados:
        return False, ("nao achei programa de captura de tela nesta maquina "
                       "(instale scrot, gnome-screenshot ou grim)")
    return False, ("nenhum capturador funcionou (" + ", ".join(tentados) +
                   "). Se a sessao for Wayland puro, tente gnome-screenshot ou grim")


def _capturar_windows(png: Path) -> tuple[bool, str]:
    """Print da area de trabalho inteira pelo proprio Windows (sem dependencia)."""
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$b = [System.Windows.Forms.SystemInformation]::VirtualScreen;"
        "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height;"
        "$g = [System.Drawing.Graphics]::FromImage($bmp);"
        "$g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size);"
        f"$bmp.Save('{png}', [System.Drawing.Imaging.ImageFormat]::Png);"
        "$g.Dispose(); $bmp.Dispose();"
    )
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", script],
                              capture_output=True, text=True, timeout=TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"powershell falhou: {exc}"
    if png.is_file() and png.stat().st_size > 0:
        return True, "powershell"
    return False, (proc.stderr or proc.stdout or "").strip()[:300] or "print vazio"


def _capturar_mac(png: Path) -> tuple[bool, str]:
    """macOS: screencapture. Precisa de permissao de Gravacao de Tela (TCC)."""
    try:
        proc = subprocess.run(["screencapture", "-x", "-o", "-t", "png", str(png)],
                              capture_output=True, text=True, timeout=TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"screencapture falhou: {exc}"
    if png.is_file() and png.stat().st_size > 0:
        return True, "screencapture"
    return False, ((proc.stderr or "").strip()[:300]
                   or "sem permissao de Gravacao de Tela para o Terminal/TEO")


def run(args: dict, ctx) -> str:
    if stopped(ctx):
        return STOPPED_NOTE
    try:
        espera = max(0, min(int(args.get("espera") or 1), MAX_ESPERA_S))
    except (TypeError, ValueError):
        espera = 1

    ok, bloqueio = ctx.gate.print_screen_ok()
    if not ok:
        return bloqueio or "BLOQUEADO: a pessoa nao autorizou o print da tela."

    if espera:
        # Tempo para a pessoa clicar na janela que ela quer mostrar.
        time.sleep(espera)
    try:
        limpar()
    except OSError:
        pass

    png = pasta() / f"tela-{secrets.token_hex(4)}.png"
    capturou, detalhe = _capturar(png)
    if not capturou:
        return (f"ERRO: nao consegui tirar o print da tela ({detalhe}). "
                "Se a sessao for remota/sem area de trabalho, peca para a pessoa "
                "tirar o print e anexar no clipe.")

    tamanho = _tamanho_png(png)
    linhas = [f"PRINT DA TELA INTEIRA: {png}"]
    if tamanho:
        linhas.append(f"RESOLUCAO: {tamanho[0]}x{tamanho[1]}")
    linhas.append(
        "OBSERVACAO: a imagem mostra TODAS as janelas abertas. Procure a janela que a "
        "pessoa quer mostrar e leia o que esta dentro dela. Se o TEO estiver na frente "
        "cobrindo a pagina, peca para a pessoa clicar na pagina e chame de novo com "
        "espera. Tela bloqueada aparece so como tela de bloqueio.")
    linhas.append(f"IMAGEM: {png}")
    return "\n".join(linhas)

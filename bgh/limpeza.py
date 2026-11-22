"""Limpeza da pasta scratch do TEO (/limpar).

O que mora em `~/.bgh/scratch`: os scripts que a ferramenta run_python cria
(`run_<carimbo>.py`) e os textos que a VOZ grava para os backends que leem
arquivo (`fala_*.txt`). Sao rascunhos: apagar nunca perde conversa, memoria,
skills nem configuracao - isso tudo mora um nivel acima, em `~/.bgh`.

Regras de seguranca:
- so se apaga DENTRO da pasta scratch (o caminho e conferido a cada arquivo);
- a propria pasta scratch nao e removida (o TEO precisa dela na proxima execucao);
- nada de erro na cara do usuario: arquivo ocupado e pulado e continua.
"""

import os
import re
from pathlib import Path

from .config import SCRATCH_DIR

GB = 1024 ** 3
# Mesmo numero do config (scratch_aviso_gb): aqui e o piso, usado quando a
# configuracao nao tem a chave ou tem valor invalido.
AVISO_GB_PADRAO = 3.0


def _dentro(caminho: Path, raiz: Path) -> bool:
    """O caminho esta mesmo dentro da raiz? (nada de '../' escapar da limpeza)"""
    try:
        caminho.resolve().relative_to(raiz.resolve())
        return True
    except (ValueError, OSError):
        return False


def varrer(pasta: Path | None = None) -> tuple[int, int]:
    """(quantos arquivos, quantos bytes) a limpeza teria para apagar."""
    raiz = Path(pasta or SCRATCH_DIR)
    arquivos = 0
    total = 0
    if not raiz.is_dir():
        return (0, 0)
    for base, _dirs, nomes in os.walk(raiz):
        for nome in nomes:
            alvo = Path(base) / nome
            if not _dentro(alvo, raiz):
                continue
            try:
                total += alvo.stat().st_size
                arquivos += 1
            except OSError:
                continue
    return (arquivos, total)


def limpar(pasta: Path | None = None) -> tuple[int, int]:
    """Apaga os arquivos do scratch e devolve (apagados, bytes liberados)."""
    raiz = Path(pasta or SCRATCH_DIR)
    apagados = 0
    total = 0
    if not raiz.is_dir():
        return (0, 0)
    for base, dirs, nomes in os.walk(raiz, topdown=False):
        for nome in nomes:
            alvo = Path(base) / nome
            if not _dentro(alvo, raiz):
                continue
            try:
                tamanho = alvo.stat().st_size
                alvo.unlink()
            except OSError:
                continue          # arquivo em uso/sem licenca: pula, nao trava a limpeza
            apagados += 1
            total += tamanho
        for nome in dirs:
            sub = Path(base) / nome
            if not _dentro(sub, raiz):
                continue
            try:
                sub.rmdir()       # so sai se ficou vazia
            except OSError:
                continue
    return (apagados, total)


def tamanho_legivel(bytes_: int) -> str:
    """'0 bytes', '512 bytes', '12 KB', '3,4 MB' - do jeito que se fala."""
    valor = float(bytes_ or 0)
    if valor < 1024:
        return f"{int(valor)} bytes"
    for unidade in ("KB", "MB", "GB"):
        valor /= 1024.0
        if valor < 1024 or unidade == "GB":
            texto = f"{valor:.1f}".replace(".", ",")
            return f"{texto} {unidade}"
    return f"{int(valor)} GB"


def gb_legivel(valor: float) -> str:
    """'3 GB', '2,5 GB', '512 MB' - o numero do aviso como a pessoa escreveu.

    Abaixo de 1 GB sai em MB: `/limpar 512MB` nao pode virar '0 GB' na frase.
    """
    gb = float(valor or 0)
    if 0 < gb < 1:
        mb = gb * 1024.0
        inteiro = round(mb)
        texto = (f"{inteiro}" if abs(mb - inteiro) < 0.05
                 else f"{mb:.1f}".replace(".", ","))
        return f"{texto} MB"
    texto = f"{gb:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{texto} GB"


def gb_de_texto(texto: str) -> float | None:
    """Le o tamanho digitado no /limpar: '3GB', '3 gb', '512MB', '2,5'.

    Devolve o tamanho em GB ou None quando nao e um tamanho valido (nesse caso
    o comando segue o caminho de sempre: perguntar antes de apagar).
    """
    bruto = str(texto or "").strip().lower().replace(",", ".")
    achado = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*(gb|g|mb|m|tb|t)?", bruto)
    if not achado:
        return None
    try:
        valor = float(achado.group(1))
    except (TypeError, ValueError):
        return None
    unidade = achado.group(2) or "gb"
    if unidade in ("mb", "m"):
        valor /= 1024.0
    elif unidade in ("tb", "t"):
        valor *= 1024.0
    if valor <= 0:
        return None
    return valor


def aviso_gb(cfg: dict | None = None) -> float:
    """Tamanho (GB) a partir do qual a abertura avisa. Vem do /limpar NGB."""
    try:
        valor = float((cfg if isinstance(cfg, dict) else {}).get(
            "scratch_aviso_gb", AVISO_GB_PADRAO))
    except (TypeError, ValueError):
        valor = AVISO_GB_PADRAO
    return valor if valor > 0 else AVISO_GB_PADRAO


def precisa_aviso(cfg: dict | None = None, pasta: Path | None = None) -> tuple[int, int] | None:
    """(quantos arquivos, quantos bytes) se o scratch passou do aviso; senao None."""
    arquivos, total = varrer(pasta)
    if total < int(aviso_gb(cfg) * GB):
        return None
    return (arquivos, total)

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
from pathlib import Path

from .config import SCRATCH_DIR


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

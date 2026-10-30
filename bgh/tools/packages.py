"""Instalacao autonoma de bibliotecas Python: o Motor procura, pede licenca e instala."""

import re
import shutil
import subprocess
import sys

# Nome PyPI simples (opcionalmente com versao). Sem meta-caracteres de shell.
PKG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(==[0-9][0-9.]*)?$")

SPEC = {
    "type": "function",
    "function": {
        "name": "instalar_pacote",
        "description": (
            "Instala uma biblioteca Python que esta faltando para a tarefa (PyPI oficial). "
            "Use quando um import falhar com ModuleNotFoundError. O usuario ve o motivo em "
            "linguagem simples e aprova ou nega. Instale so o que a tarefa precisa."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pacote": {
                    "type": "string",
                    "description": "Nome exato no PyPI, ex.: requests, openpyxl, pandas==2.2.0",
                },
                "motivo": {
                    "type": "string",
                    "description": "Frase curta em portugues explicando ao usuario por que precisa",
                },
            },
            "required": ["pacote", "motivo"],
        },
    },
}


def python_bin() -> str:
    """Interpretador onde as libs vao morar (funciona tambem dentro do binario congelado)."""
    if getattr(sys, "frozen", False):  # PyInstaller: sys.executable e o proprio binario
        return shutil.which("python3") or shutil.which("python") or ""
    return sys.executable


def run(args: dict, ctx) -> str:
    pacote = str(args.get("pacote", "")).strip()
    motivo = str(args.get("motivo", "")).strip() or "necessario para continuar a tarefa"
    if not PKG_RE.match(pacote):
        return (
            "ERRO: nome de biblioteca invalido. Use o nome PyPI simples "
            "(letras, numeros, ponto, traco; opcional ==versao)."
        )
    allowed, msg = ctx.gate.install_ok(pacote, motivo)
    if not allowed:
        return msg
    py = python_bin()
    if not py:
        return (
            "ERRO: nao encontrei um Python no sistema para receber a biblioteca. "
            "Rode 'bgh doctor' e explique ao usuario que precisa do Python instalado."
        )
    try:
        p = subprocess.run(
            [py, "-m", "pip", "install", "--disable-pip-version-check", pacote],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return "ERRO: a instalacao passou de 5 minutos (rede lenta?). Nao repita igual; avise o usuario."
    out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
    if p.returncode != 0:
        return (
            f"FALHOU (codigo {p.returncode}):\n{out[-1200:]}\n"
            "Verifique o nome certo da biblioteca no PyPI (web_search) antes de tentar outra."
        )
    return f"INSTALADO: {pacote}. Ja pode importar no run_python.\n{out[-400:]}"

"""Ferramenta run_python: roda codigo Python no scratch do Motor e devolve saida/erro."""

import subprocess
import sys
from datetime import datetime

from bgh.config import SCRATCH_DIR, ensure_dirs

SPEC = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "Executa um script Python na maquina local e devolve stdout/stderr. "
            "Use para calcular, validar dados, testar o codigo que voce escreveu e diagnosticar o sistema. "
            "O codigo roda no venv do Motor (tem requests/openai/rich)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Script Python completo"},
                "timeout": {"type": "integer", "description": "Tempo limite em segundos (padrao 60)"},
            },
            "required": ["code"],
        },
    },
}


def run(args: dict, ctx) -> str:
    code = str(args.get("code", "")).strip()
    if not code:
        return "ERRO: codigo vazio"
    ok, blocked = ctx.gate.python_code_ok(code)
    if not ok:
        return blocked
    timeout = min(int(args.get("timeout") or 60), 300)
    ensure_dirs()
    stamp = datetime.now().strftime("%H%M%S_%f")
    script = SCRATCH_DIR / f"run_{stamp}.py"
    script.write_text(code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(SCRATCH_DIR),
        )
    except subprocess.TimeoutExpired:
        return f"ERRO: o script excedeu {timeout}s e foi interrompido."
    parts = [f"exit_code={proc.returncode}"]
    if proc.stdout:
        parts.append(proc.stdout)
    if proc.stderr:
        parts.append("STDERR:\n" + proc.stderr)
    return "\n".join(parts)

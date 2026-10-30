"""Ferramenta run_python: roda codigo Python no scratch do Motor e devolve saida/erro."""

import os
import subprocess
import sys
from datetime import datetime

from bgh.config import SCRATCH_DIR, ensure_dirs

from .guard import STOPPED_NOTE, stopped, wait_with_stop

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
    if stopped(ctx):
        return STOPPED_NOTE
    ok, blocked = ctx.gate.python_code_ok(code)
    if not ok:
        return blocked
    timeout = min(int(args.get("timeout") or 60), 300)
    ensure_dirs()
    stamp = datetime.now().strftime("%H%M%S_%f")
    script = SCRATCH_DIR / f"run_{stamp}.py"
    script.write_text(code, encoding="utf-8")
    try:
        # Popen + espera vigiada (em vez de run()): assim o 'parar' do usuario derruba
        # o script em andamento em ~1 s, em vez de esperar ate o timeout da ferramenta.
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(SCRATCH_DIR),
            start_new_session=True,
            **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {}),
        )
    except OSError as exc:
        return f"ERRO: nao consegui iniciar o script: {exc}"
    box = wait_with_stop(proc, timeout, getattr(ctx, "stop_event", None))
    if box.get("stopped"):
        return STOPPED_NOTE
    if box.get("timeout"):
        return f"ERRO: o script excedeu {timeout}s e foi interrompido."
    out, err = box.get("io") or ("", "")
    parts = [f"exit_code={proc.returncode}"]
    if out:
        parts.append(out)
    if err:
        parts.append("STDERR:\n" + err)
    return "\n".join(parts)

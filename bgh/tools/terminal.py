"""Ferramenta run_command: shell local. Aprovacao segue o modelo do Hermes (ver approvals.py).

Comando seguro roda direto. So' padrao perigoso dispara o prompt [o/s/a/d].
Se ctx.stop_event for setado (usuario apertou o botao de parar), o comando em
andamento e' encerrado na hora em vez de esperar ate o fim.
"""

import os
import signal
import subprocess
import threading
import time

SPEC = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Executa um comando shell na maquina local (ls, df, journalctl, systemctl status, "
            "nvidia-smi, apt list, smartctl etc.). Comandos de leitura rodam sem perguntar; "
            "perigosos pedem aprovacao do usuario."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "O comando shell completo"},
                "timeout": {"type": "integer", "description": "Tempo limite em segundos (padrao 120)"},
            },
            "required": ["command"],
        },
    },
}


def _stopped(ctx) -> bool:
    ev = getattr(ctx, "stop_event", None)
    return ev is not None and ev.is_set()


def run(args: dict, ctx) -> str:
    command = str(args.get("command", "")).strip()
    if not command:
        return "ERRO: comando vazio"
    timeout = min(int(args.get("timeout") or 120), 600)

    ok, blocked = ctx.gate.command_ok(command)
    if not ok:
        return blocked

    if _stopped(ctx):
        return "PARADO: o comando nem chegou a comecar porque voce mandou parar."

    try:
        proc = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,  # grupo proprio: matar o shell mata os filhos tambem
            **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {}),  # Windows: grupo novo (sem API POSIX aqui)
        )
    except OSError as exc:
        return f"ERRO: nao consegui executar o comando: {exc}"

    def _kill(proc, sig) -> None:
        if os.name == "nt":
            # Windows nao tem killpg; taskkill /T derruba a arvore inteira
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True, timeout=15)
                return
            except Exception:
                pass
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (OSError, ProcessLookupError, AttributeError):
            try:
                proc.kill() if sig == signal.SIGKILL else proc.terminate()
            except OSError:
                pass

    box: dict = {}

    def _wait() -> None:
        # communicate() numa thread: le os pipes sem travar mesmo com saida grande.
        try:
            box["io"] = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                _kill(proc, signal.SIGKILL)
            except OSError:
                pass
            try:
                box["io"] = proc.communicate()
            except ValueError:
                box["io"] = ("", "")
            box["timeout"] = True
        except Exception as exc:  # noqa: BLE001 - pipe fechado por parada externa
            box["io"] = ("", f"(interrompido: {exc})")

    waiter = threading.Thread(target=_wait, daemon=True)
    waiter.start()

    stopped_mid = False
    while waiter.is_alive():
        if _stopped(ctx):
            stopped_mid = True
            _kill(proc, signal.SIGTERM)
            time.sleep(0.4)
            if proc.poll() is None:
                _kill(proc, signal.SIGKILL)
            break
        time.sleep(0.2)
    waiter.join(timeout=5)

    if stopped_mid:
        return "PARADO: o comando foi interrompido porque voce mandou parar."
    if box.get("timeout"):
        return f"ERRO: o comando excedeu {timeout}s e foi interrompido."

    out, err = box.get("io") or ("", "")
    parts = [f"exit_code={proc.returncode}"]
    if out:
        parts.append(out)
    if err:
        parts.append("STDERR:\n" + err)
    return "\n".join(parts)
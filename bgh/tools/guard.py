"""Guardas compartilhados das ferramentas: parada do usuario e tetos de tempo/arquivos.

Toda ferramenta que pode demorar (busca em arvore, script python, download de pagina)
olha o stop_event antes de comecar e durante o trabalho. Sem isso o botao de parar
(CTRL+C / ESC na tela) so vale entre rodadas do modelo: a ferramenta roda ate o fim
sozinha e o usuario enxerga isso como trava.
"""

import os
import signal
import subprocess
import threading
import time

# Toda ferramenta parada pelo usuario comeca com esta palavra: o agente reconhece
# e fecha o turno na hora (ver agent.run_turn).
STOPPED_NOTE = "PARADO: voce mandou parar e a ferramenta parou ai."


def stopped(ctx) -> bool:
    """True quando o usuario mandou parar (ESC / CTRL+C na tela)."""
    ev = getattr(ctx, "stop_event", None)
    return ev is not None and ev.is_set()


def limit_s(cfg: dict, key: str, default: int) -> int:
    """Teto de tempo (segundos) de uma ferramenta, ajustavel no config.json."""
    try:
        val = int(cfg.get(key) or default)
    except (TypeError, ValueError):
        val = default
    return max(1, min(val, 600))


def limit_n(cfg: dict, key: str, default: int) -> int:
    """Teto de quantidade (arquivos, itens), ajustavel no config.json."""
    try:
        val = int(cfg.get(key) or default)
    except (TypeError, ValueError):
        val = default
    return max(1, min(val, 200000))


def kill_tree(proc, sig=signal.SIGTERM) -> None:
    """Mata o processo e os filhos (POSIX: grupo; Windows: taskkill /T)."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=15)
            return
        except Exception:  # noqa: BLE001 - sem taskkill disponivel, cai no kill simples
            pass
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (OSError, ProcessLookupError, AttributeError):
        try:
            proc.kill() if sig == signal.SIGKILL else proc.terminate()
        except OSError:
            pass


def wait_with_stop(proc, timeout_s: int, stop_event=None) -> dict:
    """Espera um Popen acabando, com teto de tempo e parada pelo usuario.

    communicate() roda numa thread (le os pipes sem travar em saida grande).
    Devolve {'io': (stdout, stderr)} | {'timeout': True} | {'stopped': True}.
    """
    box: dict = {}

    def _wait() -> None:
        try:
            box["io"] = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            kill_tree(proc, signal.SIGKILL)
            try:
                box["io"] = proc.communicate()
            except ValueError:
                box["io"] = ("", "")
            box["timeout"] = True
        except Exception as exc:  # noqa: BLE001 - pipe fechado por parada externa
            box["io"] = ("", f"(interrompido: {exc})")

    waiter = threading.Thread(target=_wait, daemon=True)
    waiter.start()
    while waiter.is_alive():
        if stop_event is not None and stop_event.is_set():
            kill_tree(proc, signal.SIGTERM)
            time.sleep(0.4)
            if proc.poll() is None:
                kill_tree(proc, signal.SIGKILL)
            break
        time.sleep(0.2)
    waiter.join(timeout=5)

    if stop_event is not None and stop_event.is_set():
        return {"stopped": True}
    return box

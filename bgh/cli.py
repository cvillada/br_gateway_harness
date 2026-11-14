"""CLI do Motor: chat interativo, setup e doctor. Licenca em menu numerico simples.

Chat tem duas telas:
- tela fixa (bgh/tui.py, padrao): entrada sempre embaixo, mensagens sobem,
  CTRL+C/ESC para parar a resposta (igual ao Hermes);
- modo classico (rolagem simples): sem terminal interativo ou com tui=false.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console

from . import i18n
from .i18n import t

console = Console()


def chat(_args) -> int:
    from .chat_core import ChatCore, ConsoleSink
    from .config import ConfigError, load_config, saved_lang

    # Idioma salvo manda ate quando o config esta incompleto (ex.: falta a chave).
    i18n.set_lang(saved_lang())
    try:
        cfg = load_config()
    except ConfigError as exc:
        # Primeira execucao na maquina do cliente: emenda o assistente na hora,
        # sem mandar a pessoa decorarle comando. Sem terminal interativo, orienta.
        console.print(f"[yellow]{exc}[/yellow]")
        if not sys.stdin.isatty():
            console.print(t("cli.noninteractive"))
            return 1
        console.print(t("cli.first_run"))
        from .setup_wizard import run as run_setup

        if run_setup() != 0:
            return 1
        try:
            cfg = load_config()
        except ConfigError as exc2:
            console.print(f"[red]{exc2}[/red]")
            return 1

    # Tela fixa quando faz sentido; senao, rolagem classica (que continua funcionando).
    use_tui = bool(cfg.get("tui", True)) and sys.stdin.isatty() and sys.stdout.isatty()
    if sys.stdout.isatty():
        # Janela ja com nome e maximizada ANTES de a tela desenhar (rodape inteiro).
        from .chat_core import prepare_console

        prepare_console(cfg)
    if use_tui:
        try:
            from .tui import run_tui as _run_tui
        except ImportError:
            _run_tui = None       # sem prompt_toolkit instalado: modo simples
        if _run_tui is not None:
            try:
                return _run_tui(cfg)
            except Exception as exc:  # noqa: BLE001 - console exotico no cliente
                # Janela que nao aceita a tela fixa nao pode ficar MUDA (relato real
                # no Windows: "a tela nao roda"). Cai no modo simples e avisa.
                from .chat_core import log_error

                log_error(exc, "abertura da tela fixa")
                console.print(t("cli.tui_fail"))
                use_tui = False

    from . import tela

    sink = ConsoleSink(cfg)
    sink.aplicar_tema()            # cor de fundo escolhida (se houver)
    core = ChatCore(cfg, sink)
    core.banner()
    core.check_update_on_start()   # uma vez, em segundo plano (aviso de versao nova)
    try:
        while True:
            try:
                user = sink.read_prompt()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if core.submit(user) == "exit":
                break
    finally:
        # Sair devolve a cor de fundo do terminal (o TEO nao sequestra a janela).
        if tela.paleta(tela.cor(cfg)).get("bg"):
            tela.escrever(tela.RESET_FUNDO)
    return 0


def approvals(args) -> int:
    """bgh approvals [list|clear|remove <n>] - revisar as permissoes 'sempre' guardadas."""
    from .approvals import clear_allowlist, list_allowlist, remove_allowlist
    from .chat_core import ConsoleSink
    from .config import load_config

    cfg = load_config()
    i18n.set_lang(cfg.get("lang"))
    entries = list_allowlist(cfg)
    action = getattr(args, "action", "list")
    if action == "clear":
        if not entries:
            console.print(t("cli.no_always"))
            return 0
        choice = ConsoleSink().ask_approval(
            t("cli.clear_ask"),
            "\n".join(f"{i}. {e}" for i, e in enumerate(entries, start=1)),
            allow_always=False,
        )
        if choice in ("o", "s"):
            n = clear_allowlist(cfg)
            console.print(t("cli.clear_done", n=n))
        else:
            console.print(t("cli.nothing_removed"))
    elif action == "remove":
        removed = remove_allowlist(cfg, int(args.index))
        console.print(t("cli.removed", item=removed) if removed else t("cli.bad_index"))
    else:
        if not entries:
            console.print(t("cli.no_always"))
        for i, e in enumerate(entries, start=1):
            console.print(f"  {i}. {e}")
    return 0


def _console_report(say) -> None:
    """Estado da tela/console: e o que explica "nao abriu" ou "ficou estranho".

    Roda nos tres sistemas (o resto do /doctor usa comandos de Linux).
    """
    say(t("doctor.screen"))
    try:
        cols, rows = shutil.get_terminal_size()
    except OSError:
        cols, rows = (0, 0)
    say(t("doctor.size", cols=cols, rows=rows))
    from .config import load_config as _load

    try:
        tui_on = bool(_load().get("tui", True))
    except Exception:  # noqa: BLE001 - config quebrado ja e relatado depois
        tui_on = False
    say(t("doctor.tui", onoff=t("state.on") if tui_on else t("state.off")))
    pasta = Path(tempfile.gettempdir())
    gravavel = False
    try:
        teste = pasta / "teo_teste_escrita.txt"
        teste.write_text("x", encoding="utf-8")
        teste.unlink()
        gravavel = True
    except OSError:
        gravavel = False
    say(t("doctor.temp", ok=t("state.on") if gravavel else t("state.off"), path=pasta))
    if os.name == "nt":
        admin = False
        try:
            import ctypes

            admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001 - API ausente: segue como desconhecido
            admin = False
        say(t("doctor.admin", onoff=t("state.on") if admin else t("state.off")))


def doctor_report(say) -> None:
    """Diagnostico impresso linha a linha por 'say' (console do cli ou tela fixa)."""
    def sh(cmd: str) -> str:
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            out = (p.stdout or p.stderr).strip()
            return out or t("doctor.no_output")
        except Exception as exc:  # noqa: BLE001
            return t("doctor.failed", erro=exc)

    say(t("doctor.title"))
    _console_report(say)
    say("")
    say(t("doctor.machine"))
    say(sh("uname -sr && lscpu | grep -E 'Model name|^CPU\\(s\\)' | head -3"))
    say(sh("free -h | head -2"))
    say(sh("df -h ~ | tail -1"))
    say("")
    say(t("doctor.gpu"))
    if shutil.which("nvidia-smi"):
        say(sh("nvidia-smi --query-gpu=name,memory.total,temperature.gpu --format=csv,noheader"))
    else:
        say(t("doctor.no_nvidia"))
    say("")
    say(t("doctor.conn"))
    from .config import ConfigError, load_config
    from .llm import LLM, LLMError

    try:
        cfg = load_config()
    except ConfigError as exc:
        say(t("doctor.no_conn", erro=exc))
        return
    try:
        llm = LLM(cfg)
        names = ", ".join(llm.list_models()[:5]) or t("doctor.empty_list")
        extra = ""
        teto_tokens = llm.discover_context()
        if teto_tokens:
            extra = t("doctor.context", tokens=teto_tokens)
        say(t("doctor.ok", url=cfg["base_url"], names=names, extra=extra))
    except LLMError as exc:
        say(t("doctor.fail", erro=exc))
        say(t("doctor.hint", setup=i18n.cmd("setup")))


def doctor(_args) -> int:
    doctor_report(lambda texto: console.print(str(texto), markup=False))
    return 0


def setup(args) -> int:
    from .setup_wizard import run

    return run(non_interactive=args.provider is not None,
               provider=getattr(args, "provider", None),
               api_key=getattr(args, "api_key", None),
               lang=getattr(args, "lang", None))


def main(argv=None) -> int:
    from .config import saved_lang

    i18n.set_lang(saved_lang())   # --help e as mensagens tambem no idioma salvo
    parser = argparse.ArgumentParser(prog="bgh", description=t("cli.help.prog"))
    sub = parser.add_subparsers(dest="cmd")
    chat_p = sub.add_parser("chat", help=t("cli.help.chat"))
    chat_p.set_defaults(func=chat)
    setup_p = sub.add_parser("setup", help=t("cli.help.setup"))
    setup_p.add_argument("--provider", choices=["deepseek", "nubesbr", "local"], default=None)
    setup_p.add_argument("--api-key", default=None)
    setup_p.add_argument("--lang", choices=["pt", "en", "es"], default=None,
                         help="idioma da interface (o instalador passa o que a pessoa escolheu)")
    setup_p.set_defaults(func=setup)
    doctor_p = sub.add_parser("doctor", help=t("cli.help.doctor"))
    doctor_p.set_defaults(func=doctor)
    appr_p = sub.add_parser("approvals", help=t("cli.help.approvals"))
    appr_p.add_argument("action", nargs="?", default="list", choices=["list", "clear", "remove"])
    appr_p.add_argument("index", nargs="?", type=int, default=0)
    appr_p.set_defaults(func=approvals)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        return chat(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

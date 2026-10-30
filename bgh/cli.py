"""CLI do Motor: chat interativo, setup e doctor. Licenca em menu numerico simples.

Chat tem duas telas:
- tela fixa (bgh/tui.py, padrao): entrada sempre embaixo, mensagens sobem,
  CTRL+C/ESC para parar a resposta (igual ao Hermes);
- modo classico (rolagem simples): sem terminal interativo ou com tui=false.
"""

import argparse
import shutil
import subprocess
import sys

from rich.console import Console

console = Console()


def chat(_args) -> int:
    from .chat_core import ChatCore, ConsoleSink
    from .config import ConfigError, load_config

    try:
        cfg = load_config()
    except ConfigError as exc:
        # Primeira execucao na maquina do cliente: emenda o assistente na hora,
        # sem mandar a pessoa decorarle comando. Sem terminal interativo, orienta.
        console.print(f"[yellow]{exc}[/yellow]")
        if not sys.stdin.isatty():
            console.print("Em modo nao-interativo, configure antes com: bgh setup")
            return 1
        console.print("\nVamos configurar juntos agora, em poucas perguntas de uma linha cada.")
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
    if use_tui:
        try:
            from .tui import run_tui
        except ImportError:
            use_tui = False
        if use_tui:
            return run_tui(cfg)

    sink = ConsoleSink()
    core = ChatCore(cfg, sink)
    core.banner()
    while True:
        try:
            user = sink.read_prompt()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if core.submit(user) == "exit":
            break
    return 0


def approvals(args) -> int:
    """bgh approvals [list|clear|remove <n>] - revisar as permissoes 'sempre' guardadas."""
    from .approvals import clear_allowlist, list_allowlist, remove_allowlist
    from .chat_core import ConsoleSink
    from .config import load_config

    cfg = load_config()
    entries = list_allowlist(cfg)
    action = getattr(args, "action", "list")
    if action == "clear":
        if not entries:
            console.print("Nenhuma permissao 'sempre' guardada.")
            return 0
        choice = ConsoleSink().ask_approval(
            "Apagar todas as permissoes 'sempre' guardadas?",
            "\n".join(f"{i}. {e}" for i, e in enumerate(entries, start=1)),
            allow_always=False,
        )
        if choice in ("o", "s"):
            n = clear_allowlist(cfg)
            console.print(f"Pronto: {n} permissao(oes) removida(s).")
        else:
            console.print("Nada removido.")
    elif action == "remove":
        removed = remove_allowlist(cfg, int(args.index))
        console.print(f"Removido: {removed}" if removed else "Numero invalido (veja 'bgh approvals').")
    else:
        if not entries:
            console.print("Nenhuma permissao 'sempre' guardada.")
        for i, e in enumerate(entries, start=1):
            console.print(f"  {i}. {e}")
    return 0


def doctor(_args) -> int:
    def sh(cmd: str) -> str:
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            out = (p.stdout or p.stderr).strip()
            return out or "(sem saida)"
        except Exception as exc:  # noqa: BLE001
            return f"(falhou: {exc})"

    console.print("[bold]Diagnostico do TEO[/bold]\n")
    console.print("[bold cyan]Maquina[/bold cyan]")
    console.print(sh("uname -sr && lscpu | grep -E 'Model name|^CPU\\(s\\)' | head -3"))
    console.print(sh("free -h | head -2"))
    console.print(sh("df -h ~ | tail -1"))
    console.print("\n[bold cyan]GPU[/bold cyan]")
    if shutil.which("nvidia-smi"):
        console.print(sh("nvidia-smi --query-gpu=name,memory.total,temperature.gpu --format=csv,noheader"))
    else:
        console.print("(nvidia-smi nao encontrado; pode ser AMD/intel ou placa sem driver)")
    console.print("\n[bold cyan]Conexao com o modelo[/bold cyan]")
    from .config import ConfigError, load_config
    from .llm import LLM, LLMError

    try:
        cfg = load_config()
    except ConfigError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        return 0
    try:
        names = ", ".join(LLM(cfg).list_models()[:5]) or "(lista vazia)"
        console.print(f"[green]OK[/green] - {cfg['base_url']} responde. Modelos: {names}")
    except LLMError as exc:
        console.print(f"[red]Falha[/red] - {exc}")
        console.print("Confira: o servidor do modelo esta ligado? A URL e a chave estao certas? (bgh setup)")
    return 0


def setup(args) -> int:
    from .setup_wizard import run

    return run(non_interactive=args.provider is not None,
               provider=getattr(args, "provider", None),
               api_key=getattr(args, "api_key", None))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="bgh", description="TEO - agente local simples")
    sub = parser.add_subparsers(dest="cmd")
    chat_p = sub.add_parser("chat", help="conversa interativa (padrao)")
    chat_p.set_defaults(func=chat)
    setup_p = sub.add_parser("setup", help="configurar o modelo em 1 minuto")
    setup_p.add_argument("--provider", choices=["deepseek", "nubesbr", "local"], default=None)
    setup_p.add_argument("--api-key", default=None)
    setup_p.set_defaults(func=setup)
    doctor_p = sub.add_parser("doctor", help="diagnostico da maquina e da conexao")
    doctor_p.set_defaults(func=doctor)
    appr_p = sub.add_parser("approvals", help="ver/limpar permissoes 'sempre' guardadas")
    appr_p.add_argument("action", nargs="?", default="list", choices=["list", "clear", "remove"])
    appr_p.add_argument("index", nargs="?", type=int, default=0)
    appr_p.set_defaults(func=approvals)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        return chat(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

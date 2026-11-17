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

    # --maximizar vale SO nesta execucao (o padrao de fabrica e a janela como o
    # terminal abriu: a maximizacao forcada incomodou gente no Windows).
    if getattr(_args, "maximizar", False):
        cfg["maximizar"] = True

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
            # /tela sai do terminal e abre a tela do navegador (interceptado aqui,
            # antes do nucleo: o chat_core nao conhece a outra tela).
            if tela.eh_troca_para_app(user):
                print()
                return tela.TROCA_APP
            if core.submit(user) == "exit":
                break
    finally:
        # Sair devolve a cor de fundo do terminal (o TEO nao sequestra a janela).
        if tela.paleta(tela.cor(cfg)).get("bg"):
            tela.escrever(tela.RESET_FUNDO)
    return 0


def app(args) -> int:
    """bgh app: a mesma conversa, na tela do navegador (o agente e o mesmo).

    Nao chama prepare_console nem a tela fixa: aqui nao existe terminal para
    pintar - quem desenha e o navegador.
    """
    from .app_servidor import run_app
    from .config import ConfigError, load_config, saved_lang

    i18n.set_lang(saved_lang())
    try:
        cfg = load_config()
    except ConfigError as exc:
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
    # --rede liga para esta execucao; --local fecha (mesmo que o config diga sim);
    # sem nenhum dos dois vale o que a pessoa escolheu no menu de Configuracoes.
    rede_flag = bool(getattr(args, "rede", False))
    local_flag = bool(getattr(args, "local", False))
    rede = True if rede_flag else (False if local_flag else None)
    return run_app(cfg, rede=rede,
                   porta=int(getattr(args, "porta", 0) or 0),
                   abrir=not getattr(args, "no_browser", False))


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


def _opcao_do_menu(resposta: str) -> str:
    """Numero (ou nome) digitado no menu -> 'app'|'chat'|'config'|'sair'.

    '' significa "nao entendi" (o menu repete em vez de escolher por conta).
    """
    r = (resposta or "").strip().lower()
    if r in ("", "1", "a", "app", "navegador", "tela", "webapp"):
        return "app"
    if r in ("2", "c", "chat", "terminal", "tui"):
        return "chat"
    if r in ("3", "config", "configuracoes", "ajustes", "settings"):
        return "config"
    if r in ("4", "s", "sair", "exit", "0"):
        return "sair"
    return ""


def escolher_tela() -> str:
    """Pergunta de entrada: app, terminal, configuracoes ou sair.

    Publico do TEO e crianca e idoso: quem abre o programa ganha um menu em vez
    de precisar saber um subcomando. Enter sozinho vai para a tela bonita.

    Sem terminal interativo (script, pipe, cron, teste) NAO pergunta nada: vai
    direto para o terminal, como sempre foi. Menu nunca pode travar automacao.
    """
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return "chat"
    for _ in range(3):
        print("")
        print(f"  {t('cli.menu.titulo')}")
        print("")
        print(f"    1. {t('cli.menu.app')}")
        print(f"    2. {t('cli.menu.chat')}")
        print(f"    3. {t('cli.menu.config')}")
        print(f"    4. {t('cli.menu.sair')}")
        print("")
        try:
            resposta = input(f"  {t('cli.menu.prompt')}")
        except (EOFError, KeyboardInterrupt):
            print()
            return "chat"
        opcao = _opcao_do_menu(resposta)
        if opcao:
            return opcao
        print(f"  {t('cli.menu.bad')}")
    return "chat"


def _alternar_rede(cfg: dict, ligado: bool) -> None:
    """Liga/desliga o 'abrir para a rede'. Desligar nunca pergunta: fechar e seguro."""
    from .config import save_config

    if ligado:
        cfg["rede"] = False
        save_config(cfg)
        print(f"  {t('cfg.rede.desligou')}")
        return
    print("")
    for linha in t("cfg.rede.aviso").splitlines():
        print(f"  {linha}")
    print("")
    try:
        resposta = input(f"  {t('cfg.rede.prompt')}").strip().upper()
    except (EOFError, KeyboardInterrupt):
        resposta = ""
    if resposta in ("SIM", "S", "SI", "YES", "Y"):
        cfg["rede"] = True
        save_config(cfg)
        print(f"  {t('cfg.rede.ligou')}")
    else:
        print(f"  {t('cfg.rede.cancelou')}")


def _trocar_idioma(cfg: dict) -> None:
    from .config import save_config

    opcoes = i18n.lang_options()
    for i, nome in enumerate(opcoes, start=1):
        print(f"    {i}. {nome}")
    try:
        resposta = input(f"  {t('cfg.lingua.prompt', first=opcoes[0])}").strip()
    except (EOFError, KeyboardInterrupt):
        return
    codigo = i18n.lang_from_answer(resposta)
    if not codigo:
        return
    cfg["lang"] = codigo
    save_config(cfg)
    i18n.set_lang(codigo)
    print(f"  {t('cfg.lingua.ok', nome=i18n.LANG_NAMES[codigo])}")


def _trocar_modelo(cfg: dict) -> None:
    from .config import save_config

    atual = cfg.get("model", "")
    try:
        novo = input(f"  {t('cfg.modelo.prompt', atual=atual)}").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not novo or novo == atual:
        return
    cfg["model"] = novo
    save_config(cfg)
    print(f"  {t('cfg.modelo.ok', modelo=novo)}")


def menu_config() -> None:
    """Configuracoes que a pessoa alcanca sem decorar comando nem editar arquivo."""
    from .config import ConfigError, load_config, save_config

    while True:
        try:
            cfg = load_config()
        except ConfigError as exc:
            console.print(f"[yellow]{exc}[/yellow]", markup=False)
            return
        i18n.set_lang(cfg.get("lang"))
        ligado = bool(cfg.get("rede", False))
        print("")
        print(f"  {t('cfg.titulo')}")
        print("")
        valor = t("cfg.rede.on") if ligado else t("cfg.rede.off")
        cheia = t("onoff.on") if cfg.get("maximizar") else t("onoff.off")
        # As opcoes sao montadas em lista: o numero do "Voltar" e o tamanho dela
        # (a frase do prompt dizia "Enter = 4" com Voltar em 5 - reclamacao do
        # dono, 17/11). Assim nunca mais desencontra ao somar uma opcao.
        opcoes = [
            (t("cfg.rede"), valor),
            (t("cfg.idioma"), i18n.LANG_NAMES[i18n.get_lang()]),
            (t("cfg.modelo"), cfg.get("model", "")),
            (t("cfg.janela"), cheia),
        ]
        for numero, (rotulo, estado) in enumerate(opcoes, start=1):
            if estado:
                print(f"    {numero}. {rotulo}: {estado}")
            else:
                print(f"    {numero}. {rotulo}")
        voltar = len(opcoes) + 1
        print(f"    {voltar}. {t('cfg.voltar')}")
        print("")
        try:
            escolha = input(f"  {t('cfg.prompt', voltar=voltar)}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if escolha in ("", str(voltar), "v", "voltar", "back", "sair"):
            return
        if escolha == "1":
            _alternar_rede(cfg, ligado)
        elif escolha == "2":
            _trocar_idioma(cfg)
        elif escolha == "3":
            _trocar_modelo(cfg)
        elif escolha == "4":
            cfg["maximizar"] = not bool(cfg.get("maximizar"))
            save_config(cfg)
            estado = t("onoff.on") if cfg["maximizar"] else t("onoff.off")
            print(f"  {t('cfg.janela')}: {estado}")
        else:
            print(f"  {t('cli.menu.bad')}")


def _rodar_tela(qual: str, args) -> int:
    """Roda a tela escolhida e troca de tela quando ela pedir (ida e volta).

    Quem pede a troca devolve um codigo de saida (ver bgh/tela.py); aqui ele vira
    a outra tela. Assim /tela no terminal e o botao Terminal no navegador
    funcionam sem o nucleo saber que existe mais de uma tela.
    """
    from . import tela

    while True:
        codigo = app(args) if qual == "app" else chat(args)
        if codigo == tela.TROCA_APP:
            qual = "app"
            continue
        if codigo == tela.TROCA_CHAT:
            # Sem terminal de verdade (rodou em segundo plano, cron, pipe) nao ha
            # onde desenhar o TUI: encerra em vez de despejar o banner num log.
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                return 0
            qual = "chat"
            continue
        return codigo


def main(argv=None) -> int:
    from .config import saved_lang

    i18n.set_lang(saved_lang())   # --help e as mensagens tambem no idioma salvo
    parser = argparse.ArgumentParser(prog="bgh", description=t("cli.help.prog"))
    sub = parser.add_subparsers(dest="cmd")
    chat_p = sub.add_parser("chat", help=t("cli.help.chat"))
    chat_p.add_argument("--maximizar", action="store_true", help=t("cli.chat.maximizar"))
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
    app_p = sub.add_parser("app", help=t("cli.help.app"))
    app_p.add_argument("--rede", action="store_true", help=t("cli.app.rede"))
    app_p.add_argument("--local", action="store_true", help=t("cli.app.local"))
    app_p.add_argument("--porta", type=int, default=0, help=t("cli.app.porta"))
    app_p.add_argument("--no-browser", dest="no_browser", action="store_true",
                       help=t("cli.app.no_browser"))
    app_p.set_defaults(func=app)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        # Sem subcomando: o menu de entrada decide (e as Configuracoes voltam pro menu).
        escolha = escolher_tela()
        if escolha == "config":
            menu_config()
            escolha = escolher_tela()
        if escolha == "sair":
            return 0
        return _rodar_tela(escolha, args)
    if args.func is app:
        return _rodar_tela("app", args)
    if args.func is chat:
        return _rodar_tela("chat", args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

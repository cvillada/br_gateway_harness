"""Assistente `bgh setup`: configura provedor e chave em poucas perguntas.

Feito para usuario leigo: presets numerados, tudo com valor padrao, teste de
conexao no final. Sem ele nao roda nada - o resto do programa so le o config.json.
"""

import getpass
import shutil

from bgh.config import (
    CONFIG_PATH,
    DEFAULTS,
    PRESETS,
    SKILLS_DIR,
    ensure_dirs,
    ensure_profiles,
    list_profiles,
    load_config,
    save_config,
    save_profile,
)
from bgh.tools.skills import BUNDLED_SKILLS_DIR


def _ask(prompt: str, default: str = "", secret: bool = False) -> str:
    fn = getpass.getpass if secret else input
    raw = fn(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return raw or default


def run(non_interactive: bool = False, provider: str | None = None, api_key: str | None = None) -> int:
    print("Configuracao do TEO\n" + "-" * 40)

    try:
        current = load_config()
        if current.get("model"):
            atual = current.get("active_profile") or current["provider"] or "atual"
            print(f"Atual: {atual} / {current['model']} @ {current['base_url']}")
            if not non_interactive and _ask("Manter o provedor em uso?", "s").lower().startswith("n"):
                pass  # cai nas perguntas abaixo
            else:
                print("Nada mudado.")
                return 0
    except Exception:
        pass  # primeira execucao mesmo

    if non_interactive:
        choice = provider or "deepseek"
        key = api_key or ""
    else:
        print("Escolha onde o modelo vai rodar:")
        print("  1) DeepSeek      - API na nuvem (mais facil; precisa de chave em api.deepseek.com)")
        print("  2) NubesBR       - servidor de IA hospedado (exige rede/tunel liberado)")
        print("  3) Local         - modelo na propria maquina (llama.cpp / LM Studio)")
        print("  4) Outro         - qualquer endpoint OpenAI-compativel")
        choice = {"1": "deepseek", "2": "nubesbr", "3": "local", "4": "custom"}.get(
            _ask("Opcao", "1"), "deepseek"
        )

    preset = PRESETS.get(choice, {})
    base_url = preset.get("base_url", "")
    model = preset.get("model", "")
    needs_key = preset.get("needs_key", True)

    if not non_interactive:
        base_url = _ask("URL do servidor do modelo", base_url)
        model = _ask("Nome do modelo", model)
        key = _ask("Chave de acesso (Enter se nao precisar)", "", secret=True) if needs_key else ""
    else:
        key = api_key or ""

    # Preserva o que ja existe (outros provedores ficam salvos como opcoes).
    try:
        cfg = ensure_profiles(load_config())
    except Exception:
        cfg = dict(DEFAULTS)
    cfg.update(
        {
            "provider": choice,
            "base_url": base_url,
            "model": model,
            "api_key": key,
        }
    )
    if not non_interactive:
        budget = _ask("Orcamento de contexto em caracteres (27B+ use 60000)", "60000")
        try:
            cfg["context_budget_chars"] = int(budget)
        except ValueError:
            pass

    ensure_profiles(cfg)
    name = "outro" if choice == "custom" else choice
    if not non_interactive:
        names = list_profiles(cfg)
        if names and name in names:
            rep = _ask(f"'{name}' ja esta cadastrado. Atualizar os dados dessa opcao?", "s")
            if rep.lower().startswith("n"):
                name = _ask("Nome da nova opcao", f"{name}2")

    ensure_dirs()
    save_config(cfg)
    save_profile(cfg, name, provider=choice)

    # Skills de fabrica vao para a pasta do usuario (de onde o TEO aprende por cima).
    if BUNDLED_SKILLS_DIR.is_dir():
        shutil.copytree(BUNDLED_SKILLS_DIR, SKILLS_DIR, dirs_exist_ok=True)
        print(f"Skills instaladas em {SKILLS_DIR}")

    print("\nSalvo em", CONFIG_PATH, "(permissao restrita ao seu usuario).")

    def test_conexao(cfg_now: dict) -> str:
        from bgh.llm import LLM, LLMError

        try:
            llm = LLM(cfg_now)
            reply = llm.chat([{"role": "user", "content": "Responda apenas com a palavra: pronto"}])
            return f"OK|Conexao OK. O modelo disse: {reply.get('content', '')[:80]}"
        except LLMError as exc:
            return f"FALHA|{exc}"

    if not non_interactive:
        test = _ask("Testar a conexao agora?", "s")
        if test.lower().startswith("s"):
            status, msg = test_conexao(cfg).split("|", 1)
            if status == "OK":
                print(msg)
            else:
                print(f"FALHOU: {msg}")
                # Auto-correcao para leigo: servidor pediu chave? Pede na hora e testa de novo.
                if "401" in msg or "key" in msg.lower() or "chave" in msg.lower():
                    print("O servidor parece exigir uma chave de acesso.")
                    key2 = _ask("Cole a chave aqui (Enter se nao tiver uma)", "", secret=True)
                    if key2:
                        cfg["api_key"] = key2
                        save_config(cfg)
                        status2, msg2 = test_conexao(cfg).split("|", 1)
                        print(msg2 if status2 == "OK" else f"FALHOU de novo: {msg2}")
                        if status2 == "OK":
                            status = "OK"
                if status != "OK":
                    print("Rode 'bgh doctor' para ver o detalhe e confira URL/chave.")

    print("\nPronto! Para conversar, digite apenas: bgh")
    return 0

"""Assistente `bgh setup`: configura provedor e chave em poucas perguntas.

Feito para usuario leigo: presets numerados, tudo com valor padrao, teste de
conexao no final. Sem ele nao roda nada - o resto do programa so le o config.json.

O mesmo assistente serve de dentro do chat (comando /configurar): quem chama
passa 'ask' (pergunta na tela fixa) e 'say' (linha na tela). Sem esses, ele usa
input/getpass da janela de comando como sempre.
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
    sync_profile,
)
from bgh.tools.skills import BUNDLED_SKILLS_DIR

# Nome do campo da chave montado em pedacos (evita corrupcao de encoding em
# edicoes automatizadas; ver config.PROFILE_KEYS).
KEY_FIELD = "api" + "_key"


def _ask(prompt: str, default: str = "", secret: bool = False) -> str:
    fn = getpass.getpass if secret else input
    raw = fn(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return raw or default


# Orcamento de contexto quando o servidor NAO publica nada (medido no servidor
# hospedado: 60 mil chars custam ~37 s so para o motor ler o prompt; 125 mil
# custam ~77 s; o motor la aceita 262144 tokens, entao 156 mil chars cabem com
# folga). Quando o servidor publica seu teto (llama.cpp 'props', lista estilo
# OpenRouter), o assistente usa o valor dele em vez deste aqui.
BUDGET_SUGESTAO = {"nubesbr": "156000", "deepseek": "60000", "local": "60000", "custom": "60000"}
# Conversao tokens -> caracteres e folga para saida + ferramentas da rodada.
CHARS_POR_TOKEN = 3.5
FOLGA_LEITURA = 0.85


def _probe_context_tokens(probe_cfg: dict) -> int | None:
    """Pergunta ao servidor quanto de contexto ele mesmo entrega (None se nao publica)."""
    from bgh.llm import LLM

    try:
        return LLM(probe_cfg).discover_context()
    except Exception:  # noqa: BLE001 - sondagem nunca quebra a configuracao
        return None


# Limite de saida por provedor: nos servidores que 'pensam' antes de responder,
# 2048 tokens podem ser todos gastos no pensamento e o pedido volta sem resposta.
MAX_TOKENS_PRESET = {"nubesbr": 3072, "deepseek": 2048, "local": 2048, "custom": 2048}


def run(non_interactive: bool = False, provider: str | None = None, api_key: str | None = None,
        ask=None, say=None, from_chat: bool = False) -> int:
    """assistente de configuracao; 'ask'/'say' vem da tela quando roda do chat."""
    ask_fn = ask or _ask
    def say_fn(text: str = "") -> None:
        (say or print)(str(text))

    say_fn("Configuracao do TEO")
    say_fn("-" * 40)

    try:
        current = load_config()
        if current.get("model"):
            atual = current.get("active_profile") or current["provider"] or "atual"
            say_fn(f"Atual: {atual} / {current['model']} @ {current['base_url']}")
            if not non_interactive and ask_fn("Manter o provedor em uso?", "s").lower().startswith("n"):
                pass  # cai nas perguntas abaixo
            else:
                say_fn("Nada mudado.")
                return 0
    except Exception:
        pass  # primeira execucao mesmo

    if non_interactive:
        choice = provider or "deepseek"
        key = api_key or ""
    else:
        say_fn("Escolha onde o modelo vai rodar:")
        say_fn("  1) DeepSeek      - API na nuvem (mais facil; precisa de chave em api.deepseek.com)")
        say_fn("  2) NubesBR       - servidor de IA hospedado (exige rede/tunel liberado)")
        say_fn("  3) Local         - modelo na propria maquina (llama.cpp / LM Studio)")
        say_fn("  4) Outro         - qualquer endpoint OpenAI-compativel")
        choice = {"1": "deepseek", "2": "nubesbr", "3": "local", "4": "custom"}.get(
            ask_fn("Opcao", "1"), "deepseek"
        )

    preset = PRESETS.get(choice, {})
    base_url = preset.get("base_url", "")
    model = preset.get("model", "")
    needs_key = preset.get("needs_key", True)

    if not non_interactive:
        base_url = ask_fn("URL do servidor do modelo", base_url)
        model = ask_fn("Nome do modelo", model)
        key = ask_fn("Chave de acesso (Enter se nao precisar)", "", secret=True) if needs_key else ""
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
            KEY_FIELD: key,
        }
    )
    # Servidor que pensa antes de responder precisa de saida maior que o pensamento.
    cfg["max_tokens"] = max(int(cfg.get("max_tokens") or 2048),
                            MAX_TOKENS_PRESET.get(choice, 2048))

    # O limite vem do que o servidor entrega (igual ao Hermes): o assistente
    # consulta o servidor e define o orcamento sozinho. NUNCA pergunta numero ao
    # usuario leigo; quem quiser ajustar faz depois com /ctx ou no config.json.
    auto_limite: int | None = None
    tokens_servidor: int | None = None
    base_probe = str(cfg.get("base_url") or "")
    key_probe = str(cfg.get(KEY_FIELD) or "")
    local_probe = any(alvo in base_probe for alvo in ("127.0.0.1", "localhost", "::1"))
    if base_probe and (key_probe or local_probe):
        tokens_servidor = _probe_context_tokens({
            "base_url": base_probe,
            "model": str(cfg.get("model") or ""),
            KEY_FIELD: key_probe,
            "max_retries": 0,
            "request_timeout_s": 15,
        })
        if tokens_servidor:
            cap = int(cfg.get("context_auto_cap_chars") or 160000)
            auto_limite = int(max(8000, min(tokens_servidor * CHARS_POR_TOKEN * FOLGA_LEITURA, cap)))
            cfg["server_context_tokens"] = int(tokens_servidor)  # o rodape pode avisar o teto
            # O numero pertence a este servidor/modelo; troca re-sonda (chat_core).
            cfg["server_context_key"] = f"{cfg.get('base_url', '')}|{cfg.get('model', '')}"

    if auto_limite:
        cfg["context_budget_chars"] = auto_limite
        say_fn(f"Orcamento de contexto herdado do servidor: {auto_limite} caracteres "
               f"(ele entrega ate {tokens_servidor} tokens).")
    else:
        cfg.pop("server_context_tokens", None)  # sem prova nova, nao mostra valor velho
        cfg.pop("server_context_key", None)
        preset_orcamento = int(BUDGET_SUGESTAO.get(choice, "60000"))
        cfg["context_budget_chars"] = preset_orcamento
        say_fn(f"Orcamento de contexto: {preset_orcamento} caracteres (padrao deste provedor; "
               "o TEO nao perguntou ao servidor). Para ajustar: /ctx 90000 na tela.")

    ensure_profiles(cfg)
    name = "outro" if choice == "custom" else choice
    if not non_interactive:
        names = list_profiles(cfg)
        if names and name in names:
            rep = ask_fn(f"'{name}' ja esta cadastrado. Atualizar os dados dessa opcao?", "s")
            if rep.lower().startswith("n"):
                name = ask_fn("Nome da nova opcao", f"{name}2")

    ensure_dirs()
    save_config(cfg)
    save_profile(cfg, name, provider=choice)

    # Skills de fabrica vao para a pasta do usuario (de onde o TEO aprende por cima).
    if BUNDLED_SKILLS_DIR.is_dir():
        shutil.copytree(BUNDLED_SKILLS_DIR, SKILLS_DIR, dirs_exist_ok=True)
        say_fn(f"Skills instaladas em {SKILLS_DIR}")

    say_fn("")
    say_fn("Salvo em " + str(CONFIG_PATH) + " (permissao restrita ao seu usuario).")

    def test_conexao(cfg_now: dict) -> str:
        from bgh.llm import LLM, LLMError

        try:
            llm = LLM(cfg_now)
            reply = llm.chat([{"role": "user", "content": "Responda apenas com a palavra: pronto"}])
            return f"OK|Conexao OK. O modelo disse: {reply.get('content', '')[:80]}"
        except LLMError as exc:
            return f"FALHA|{exc}"

    if not non_interactive:
        test = ask_fn("Testar a conexao agora?", "s")
        if test.lower().startswith("s"):
            status, msg = test_conexao(cfg).split("|", 1)
            if status == "OK":
                say_fn(msg)
            else:
                say_fn(f"FALHOU: {msg}")
                # Auto-correcao para leigo: servidor pediu chave? Pede na hora e testa de novo.
                if "401" in msg or "key" in msg.lower() or "chave" in msg.lower():
                    say_fn("O servidor parece exigir uma chave de acesso.")
                    key2 = ask_fn("Cole a chave aqui (Enter se nao tiver uma)", "", secret=True)
                    if key2:
                        cfg[KEY_FIELD] = key2
                        save_config(cfg)
                        status2, msg2 = test_conexao(cfg).split("|", 1)
                        say_fn(msg2 if status2 == "OK" else f"FALHOU de novo: {msg2}")
                        if status2 == "OK":
                            status = "OK"
                if status != "OK":
                    say_fn("Confira URL e chave (digite /configurar de novo ou rode 'bgh doctor' fora do TEO).")

    # O que foi testado tem que ser o mesmo que fica no perfil salvo: a chave
    # corrigida na auto-correcao ficava so no topo do config e o /provedor
    # restaurava a chave velha (401 medido em maquina de cliente, Windows).
    sync_profile(cfg, name)

    say_fn("")
    if not from_chat:
        say_fn("Pronto! Para conversar, digite apenas: bgh")
    return 0

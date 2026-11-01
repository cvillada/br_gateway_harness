"""Configuracao do Motor: ~/.bgh/config.json + sobrescritas por variaveis de ambiente.

Facil para usuario final: o assistente `bgh setup` escreve este arquivo.
Variaveis de ambiente util para testes/implantacao: BGH_HOME, BGH_BASE_URL,
BGH_API_KEY, BGH_MODEL.
"""

import json
import os
import stat
from pathlib import Path

BGH_HOME = Path(os.environ.get("BGH_HOME", str(Path.home() / ".bgh")))
CONFIG_PATH = BGH_HOME / "config.json"
SKILLS_DIR = BGH_HOME / "skills"
MEMORY_DB = BGH_HOME / "memory.db"
SESSION_FILE = BGH_HOME / "session.json"
INPUT_HISTORY_FILE = BGH_HOME / "input_history.txt"
SCRATCH_DIR = BGH_HOME / "scratch"

# Presets oferecidos no `bgh setup`.
PRESETS = {
    "deepseek": {
        "label": "DeepSeek (API na nuvem, mais simples)",
        "base_url": "https://api.deepseek.com/v1",
        # Nomes antigos (deepseek-chat / deepseek-reasoner) foram aposentados pelo
        # provedor em 24/07/2026; a base_url e a mesma, so o nome do modelo mudou.
        "model": "deepseek-v4-flash",
        "needs_key": True,
    },
    "nubesbr": {
        "label": "NubesBR (servidor de IA hospedado em ia.nubesbr.com)",
        "base_url": "https://ia.nubesbr.com/v1/",
        "model": "qwen3.8-flash-next-iq2_xs",
        "needs_key": True,
    },
    "local": {
        "label": "Modelo local na propria maquina (llama.cpp / LM Studio em :30000)",
        "base_url": "http://127.0.0.1:30000/v1",
        "model": "local",
        "needs_key": False,
    },
}

DEFAULTS = {
    "provider": "",
    "base_url": "",
    "api_key": "",
    "model": "",
    "temperature": 0.3,
    # Teto de saida por resposta do modelo (tool call de documento carrega o texto
    # inteiro na resposta). 2048 limitava HTML grande a ~7 mil chars por rodada;
    # 8192 comporta ~28 mil. DeepSeek V4 aceita ate 384 mil; motor local para no
    # fim natural do texto, entao nao custa nada quando a resposta e curta.
    "max_tokens": 8192,
    # Resposta em streaming (aparece digitada ao vivo); cai para modo normal se o servidor nao suportar.
    "stream": True,
    # thinking: auto | off | minimum | low | medium | high | xhigh | max | ultra
    # (on continua aceito como antigo). Vira reasoning_effort e/ou
    # thinking_budget conforme o que o servidor aceitar (queda em escada).
    "thinking": "auto",        # nivel enviado ao servidor
    "show_thinking": True,     # mostrar ou nao o bloco cinza na tela (/pensamento liga|desliga)
    # Segundos de espera pelo modelo antes de desistir. 0 = automatico:
    # 120 para modelo na propria maquina, 300 para servidor remoto (contexto grande
    # pode levar mais de um minuto so para ser lido).
    "request_timeout_s": 0,
    # Tetos da busca em arquivos: sem eles uma pasta gigante (AppData, Documents)
    # anda a arvore inteira e o turno parece travado.
    "search_time_limit_s": 20,
    "search_max_files": 20000,
    # Orcamento de contexto em caracteres (~3.5 chars/token em pt+codigo).
    # 156000 chars ~= 45 mil tokens: cabe com folga no servidor hospedado (motor
    # la aceita 262144 tokens; leitura medida: 125 mil chars custam ~77 s).
    # Modelo local (llama.cpp) paga contexto grande em VRAM: baixe com /ctx 60000
    # se o servidor da propria maquina reclamar.
    "context_budget_chars": 156000,
    # Compactar comecando aqui (% do orcamento), ANTES de esbarrar no teto.
    "context_compress_pct": 85,
    # Teto da descoberta automatica: por mais que o servidor entregue (ex.: motor
    # com 262144 tokens), o TEO limita o proprio uso para a leitura nao virar espera
    # de minutos na maquina do usuario. Ajustavel; /ctx subiu alem daqui por escolha.
    "context_auto_cap_chars": 160000,
    # Rodadas de ferramenta por turno. 12 deixava pesquisa/redacao longa cair no
    # fechamento no meio do trabalho; 20 comporta sessao pesada. O anti-loop real
    # e outro (chamada identica 3x e 5 falhas em sequencia fecham antes disso).
    "max_tool_rounds": 20,
    # Padroes aprovados com 'always' no prompt de comando perigoso
    # (texto exato ou glob estilo shell; igual ao command_allowlist do Hermes).
    "command_allowlist": [],
    # Tela fixa (entrada sempre embaixo, estilo Hermes). False volta ao modo classico.
    "tui": True,
}


class ConfigError(Exception):
    """Faltam dados de conexao; oriente o usuario a rodar `bgh setup`."""


# --- Perfis de provedor: varios cadastros salvos, um ativo por vez ------
PROFILE_KEYS = ("provider", "base_url", "api" + "_key", "model")


def ensure_profiles(cfg: dict) -> dict:
    """Migracao compativel: config antigo de um provedor vira perfil salvo."""
    profiles = cfg.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        if cfg.get("base_url") and cfg.get("model"):
            name = cfg.get("provider") or "atual"
            cfg["profiles"] = {name: {k: cfg.get(k, "") for k in PROFILE_KEYS}}
            cfg["active_profile"] = name
        else:
            cfg.setdefault("profiles", {})
            cfg.setdefault("active_profile", "")
    # Top-level vazio mas ha perfis: ativa o primeiro (nunca deixa o chat sem conexao).
    if (not cfg.get("base_url") or not cfg.get("model")) and cfg["profiles"]:
        first = next(iter(cfg["profiles"]))
        for k in PROFILE_KEYS:
            cfg[k] = cfg["profiles"][first].get(k, "")
        cfg["active_profile"] = first
    return cfg


def list_profiles(cfg: dict) -> list[str]:
    return [k for k in (cfg.get("profiles") or {}) if isinstance(cfg["profiles"].get(k), dict)]


def save_profile(cfg: dict, name: str, provider: str | None = None) -> None:
    """Grava/atualiza o provedor atual como perfil nomeado e o ativa."""
    cfg.setdefault("profiles", {})[name] = {k: cfg.get(k, "") for k in PROFILE_KEYS}
    cfg["profiles"][name]["provider"] = provider or name
    cfg["active_profile"] = name
    save_config(cfg)


def set_active_profile(cfg: dict, name: str) -> bool:
    """Troca o provedor ativo (usado pelo /provedor no chat). True se existe."""
    profiles = cfg.get("profiles") or {}
    prof = profiles.get(name)
    if not isinstance(prof, dict):
        return False
    for k in PROFILE_KEYS:
        cfg[k] = prof.get(k, "")
    cfg["active_profile"] = name
    save_config(cfg)
    return True


def ensure_dirs() -> None:
    for d in (BGH_HOME, SKILLS_DIR, SCRATCH_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except (json.JSONDecodeError, OSError) as exc:
            raise ConfigError(f"config.json corrompido em {CONFIG_PATH}: {exc}")
    env_map = {
        "base_url": "BGH_BASE_URL",
        "api_key": "BGH_API_KEY",
        "model": "BGH_MODEL",
    }
    for field, var in env_map.items():
        val = os.environ.get(var)
        if val:
            cfg[field] = val
    ensure_profiles(cfg)
    if not cfg.get("base_url") or not cfg.get("model"):
        raise ConfigError(
            "TEO ainda nao configurado. Rode um unico comando: bgh setup"
        )
    return cfg


def save_config(cfg: dict) -> None:
    ensure_dirs()
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # Guarda a API key com permissao de dono apenas.
    os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)

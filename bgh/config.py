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
    # Janela maximizada na abertura: DESLIGADO de fabrica. Forcar a janela
    # inteira atrapalha quem usa o TEO ao lado de outro programa (reclamacao de
    # cliente); quem gosta liga em /configurar ou roda `bgh chat --maximizar`.
    "maximizar": False,
    # Tamanho da TELA DO NAVEGADOR (o /zoom). 75% de fabrica: e o que cabe numa
    # janela de notebook sem o rodape sair da tela (decisao do dono, 17/11 - "que
    # ja abra em 75"). Em monitor grande quem quiser aumenta com /zoom 100.
    # "auto" tambem e aceito: a tela escolhe (75% se a janela for baixa, 100% se
    # for alta).
    "zoom_web": 75,
    # Acessibilidade (/voz): le cada resposta em voz alta com a voz do SISTEMA
    # (spd-say/espeak-ng, SAPI do Windows, say do Mac). Desligado por padrao.
    "voz": False,
    # Acessibilidade visual (/fundo): cor de fundo da tela. "padrao" = a do
    # terminal; as outras pintam a janela e escolhem letra de contraste.
    "cor_fundo": "padrao",
    # Tamanho da letra (/fonte): 1 normal, 2 grande, 3 maior, 4 enorme.
    "fonte": 1,
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
    # 250000 chars ~= 71 mil tokens. No servidor hospedado (motor de la aceita
    # 262144 tokens) isso custa leitura longa com cache FRIO: medido na P40,
    # 30 mil tokens = 60 s, entao 71 mil ficam perto de 143 s (dentro dos 300 s
    # do timeout remoto). Com cache quente o KV e reaproveitado e o turno fica
    # barato. Modelo local pequeno paga isso em espera: baixe com /ctx 60000 se
    # o servidor da propria maquina reclamar - e, quando o servidor publica o
    # n_ctx, o assistente de setup ja herda o teto real sozinho.
    "context_budget_chars": 250000,
    # Compactar comecando aqui (% do orcamento), ANTES de esbarrar no teto.
    "context_compress_pct": 85,
    # Teto da descoberta automatica: por mais que o servidor entregue (ex.: motor
    # com 262144 tokens), o TEO limita o proprio uso para a leitura nao virar espera
    # de minutos na maquina do usuario. Fica ACIMA do orcamento padrao de proposito:
    # se fosse menor, um servidor que publica contexto puxaria o budget para baixo
    # e o padrao novo nunca valeria. Ajustavel; /ctx subiu alem daqui por escolha.
    "context_auto_cap_chars": 260000,
    # Rodadas de ferramenta por ETAPA do turno. 12 deixava pesquisa/redacao longa
    # cair no fechamento no meio do trabalho; 20 comporta sessao pesada. Ao chegar
    # na etapa, se o turno esta progredindo o TEO prorroga sozinho ate o teto
    # (max_tool_rounds_teto) - nao e parede, mas tambem nao vira loop sem fim.
    "max_tool_rounds": 20,
    # Teto do turno. Projeto/tarefa longa passa de 40 ferramentas de verdade: com 40
    # o TEO fechava no meio do trabalho e o modelo preenchia o buraco por invencao.
    # Ao bater o teto ele NAO entrega documento: avisa que esta parcial, salva a
    # conversa e espera 'continue'. 0 = SEM parede (prorroga enquanto progride; os
    # anti-loop de chamada repetida e de 5 falhas continuam valendo).
    "max_tool_rounds_teto": 120,
    # Aviso ao MODELO em % do teto (padrao do Hermes: budget_warning_ratio). Entra UMA
    # vez no ultimo resultado de ferramenta: "anote o progresso e continue". Serve para
    # o modelo nao ser surpreendido pelo teto - e nao para encerrar antes da hora.
    # 0 ou 1 = desligado.
    "tool_warning_ratio": 0.8,
    # Padroes aprovados com 'always' no prompt de comando perigoso
    # (texto exato ou glob estilo shell; igual ao command_allowlist do Hermes).
    "command_allowlist": [],
    # Tela fixa (entrada sempre embaixo, estilo Hermes). False volta ao modo classico.
    "tui": True,
    # Modelos que JA recusaram imagem ("base_url|model"): na proxima vez o TEO
    # avisa antes, em vez de mandar a foto e levar 400 outra vez.
    "vision_blocklist": [],
    # Palco: trilha do pedido (chefe -> agente -> ferramenta -> modelo -> tela)
    # desenhada acima da linha de digitar, SO enquanto o TEO trabalha. False =
    # tela exatamente como antes (o /palco liga|desliga no chat faz o mesmo).
    "palco": True,
    # Checagem de versao nova na ABERTURA (uma vez, em segundo plano). False =
    # nao consulta o GitHub ao abrir (maquina sem internet, rede restrita).
    "update_check": True,
    # Idioma da interface: pt | en | es. O instalador pergunta no inicio e o
    # comando /lingua troca a qualquer momento (fica salvo aqui).
    "lang": "pt",
    # A partir de quantos GB de rascunhos a ABERTURA avisa que a pasta `scratch`
    # esta cheia. Ajustado pelo proprio comando: `/limpar 5GB` grava 5 aqui.
    # 3 de fabrica: abaixo disso a limpeza nao muda nada no uso da maquina.
    "scratch_aviso_gb": 3,
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


def sync_profile(cfg: dict, name: str | None = None) -> bool:
    """Copia a conexao EM USO (topo do config) para o perfil salvo.

    Motivo medido (cliente em Windows, v0.2.8): a chave corrigida na auto-correcao
    do assistente era gravada so no topo do config; o perfil guardava a chave da
    primeira tentativa (vazia) e o /provedor a restaurava - o resultado era 401 de
    novo logo depois de a mesma chave ter sido testada com sucesso. O mesmo vale
    para o modelo trocado com /modelo: sem sincronizar, voltar para o provedor
    desfazia a troca em silencio.
    """
    alvo = name or cfg.get("active_profile") or ""
    prof = (cfg.get("profiles") or {}).get(alvo)
    if not isinstance(prof, dict):
        return False
    for k in PROFILE_KEYS:
        prof[k] = cfg.get(k, "")
    save_config(cfg)
    return True


def ensure_dirs() -> None:
    for d in (BGH_HOME, SKILLS_DIR, SCRATCH_DIR):
        d.mkdir(parents=True, exist_ok=True)


def scratch_env() -> dict:
    """Ambiente dos comandos e scripts: o TEMP do sistema DENTRO do scratch.

    Motivo (Mac do dono): o que a ferramenta criava em /tmp ficava fora da pasta
    que o `/limpar` apaga, entao limpar deixava metade dos rascunhos para tras.
    Com TMPDIR, TEMP e TMP apontando para `scratch/tmp`, o que o comando (e os
    programas que ele chama) grava de temporario cai no mesmo lugar que a
    limpeza conhece - um lugar so para apagar.
    """
    env = dict(os.environ)
    tmp = SCRATCH_DIR / "tmp"
    try:
        tmp.mkdir(parents=True, exist_ok=True)
    except OSError:
        return env      # sem permissao: melhor o TEMP do sistema do que nada
    for var in ("TMPDIR", "TEMP", "TMP"):
        env[var] = str(tmp)
    return env


def saved_lang() -> str:
    """Idioma gravado no config.json, sem validar o resto do arquivo.

    A tela precisa falar o idioma do usuario ANTES de saber se a conexao esta
    certa (ex.: config quebrado, primeira execucao): aqui so se le esse campo.
    """
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return str(data.get("lang") or "pt")
    except (OSError, json.JSONDecodeError):
        pass
    return "pt"


# Chave que carimba o config.json do cliente como ja migrado (0.2.18).
MAX_TOKENS_MIGRADA = "max_tokens_migrado"


def _migra_max_tokens(cfg: dict, gravado: dict | None) -> bool:
    """Sobe uma vez o teto de saida das instalacoes antigas para o padrao novo.

    Antes de 0.2.18 o assistente gravava 2048 (3072 no nubesbr) no config.json
    de cada cliente. O padrao subiu para 8192, mas o valor gravado no arquivo
    tem prioridade sobre o padrao - entao so quem instalasse do zero escapava
    do corte no meio da resposta (aviso amarelo do 'continue'). Aqui o valor
    antigo sobe para o padrao atual UMA vez e o arquivo ganha um carimbo:
    ajuste manual do usuario depois da migracao (para baixo ou para cima)
    passa a ser sempre respeitado. Devolve True se o config precisa ser
    regravado com o novo valor e o carimbo.
    """
    if gravado is None or gravado.get(MAX_TOKENS_MIGRADA):
        return False
    padrao = int(DEFAULTS["max_tokens"])
    try:
        valor = int(gravado.get("max_tokens", padrao))
    except (TypeError, ValueError):
        valor = padrao
    if valor < padrao:
        cfg["max_tokens"] = padrao
    cfg[MAX_TOKENS_MIGRADA] = True
    return True


# Carimbo da migracao do teto de leitura da descoberta (0.2.42).
CAP_CONTEXTO_MIGRADA = "cap_contexto_migrado"


def _migra_cap_contexto(cfg: dict, gravado: dict | None) -> bool:
    """Sobe uma vez o teto de leitura antigo (160000) para o padrao atual.

    O teto da descoberta automatica ficava GRAVADO no config.json de quem ja
    rodou o assistente. Com o orcamento padrao subindo para 250000, esse numero
    velho passaria a puxar o budget PARA BAIXO na proxima vez que o assistente
    herdasse o contexto do servidor - um downgrade que ninguem pediu (caso real:
    o dono tem budget 350000 e cap 160000 no arquivo). Aqui o valor antigo sobe
    para o padrao uma vez e o arquivo ganha carimbo; ajuste manual depois do
    carimbo e sempre respeitado.
    """
    if gravado is None or gravado.get(CAP_CONTEXTO_MIGRADA):
        return False
    padrao = int(DEFAULTS["context_auto_cap_chars"])
    try:
        valor = int(gravado.get("context_auto_cap_chars", padrao))
    except (TypeError, ValueError):
        valor = padrao
    if valor < padrao:
        cfg["context_auto_cap_chars"] = padrao
    cfg[CAP_CONTEXTO_MIGRADA] = True
    return True


# Carimbo da migracao do teto de ferramentas do turno (0.2.43).
TOOL_ROUNDS_MIGRADA = "tool_rounds_migrado"


def _migra_tool_rounds(cfg: dict, gravado: dict | None) -> bool:
    """Sobe UMA vez a etapa/teto de ferramentas de quem tem o valor antigo gravado.

    Quem instalou antes da 0.2.10 ficou com `max_tool_rounds: 12` (e
    `max_tool_rounds_teto: 40`) no config.json. O valor do arquivo vence o padrao,
    entao a instalacao continuava fechando o turno no meio de pesquisa/redacao -
    caso real do dono (12 -> 24 -> 36 -> 40 e resposta com dado inventado). Aqui o
    valor antigo sobe para o padrao atual uma vez e o arquivo ganha carimbo; ajuste
    manual depois do carimbo (inclusive `teto: 0`, que significa SEM parede) e
    sempre respeitado. Devolve True se o config precisa ser regravado.
    """
    if gravado is None or gravado.get(TOOL_ROUNDS_MIGRADA):
        return False
    padrao = int(DEFAULTS["max_tool_rounds"])
    teto_padrao = int(DEFAULTS["max_tool_rounds_teto"])
    try:
        etapas = int(gravado.get("max_tool_rounds", padrao))
    except (TypeError, ValueError):
        etapas = padrao
    try:
        teto = int(gravado.get("max_tool_rounds_teto", teto_padrao))
    except (TypeError, ValueError):
        teto = teto_padrao
    if etapas < padrao:
        cfg["max_tool_rounds"] = padrao
    if 0 < teto < teto_padrao:
        cfg["max_tool_rounds_teto"] = teto_padrao
    cfg[TOOL_ROUNDS_MIGRADA] = True
    return True


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    gravado: dict | None = None
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                gravado = data
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
    migrou = _migra_max_tokens(cfg, gravado)
    if _migra_cap_contexto(cfg, gravado):
        migrou = True
    if _migra_tool_rounds(cfg, gravado):
        migrou = True
    if migrou:
        save_config(cfg)
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

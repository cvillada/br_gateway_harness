"""Cliente OpenAI-compativel: llama.cpp, LM Studio, DeepSeek e afins.

Extras:
- Captura de "pensamento": aceita reasoning_content ou reasoning na resposta.
- Toggle de thinking: cfg["thinking"] = auto|on|off. on/off manda
  chat_template_kwargs {"thinking": bool}; se o servidor rejeitar, o cliente
  desliga o recurso sozinho e segue funcionando.
"""

import re
import time
from typing import Callable

import requests
from openai import OpenAI

from bgh.config import load_config

# Niveis de pensamento que a interface oferece.
THINKING_LEVELS = ("auto", "off", "on", "minimum", "low", "medium", "high",
                   "xhigh", "max", "ultra")
# nome enviado como reasoning_effort (padrao OpenAI/llama.cpp/OpenRouter)
_EFFORT = {"minimum": "minimal", "low": "low", "medium": "medium", "high": "high",
           "xhigh": "xhigh", "max": "max", "ultra": "ultra"}
# orcamento de tokens de raciocinio (chat_template_kwargs thinking_budget, qwen3 e afins)
_BUDGET = {"minimum": 128, "low": 512, "medium": 2048, "high": 4096,
           "xhigh": 8192, "max": 16384, "ultra": 32768}


class LLMError(Exception):
    """Erro de conexao/resposta do modelo, ja traduzido para mensagem legivel."""


class ContextOverflowError(LLMError):
    """O servidor recusou o pedido porque o contexto passou do limite dele.

    Caso especial: o agente compacta a conversa e tenta de novo sozinho, em vez
    de derrubar o turno (era assim que a tela 'parava' quando o contexto enchia).
    """


class LLMRateLimitError(LLMError):
    """O provedor pediu para esperar: limite de uso do momento ou cota esgotada.

    Tratado como caso proprio porque a resposta certa NAO e tentar de novo na
    mesma hora (cada tentativa gasta cota e a espera cresce): a tela avisa em
    frase simples que e so esperar um pouco ou trocar de provedor.
    """


# Marcadores de erro de contexto dos servidores que falam OpenAI (llama.cpp,
# DeepSeek, vLLM e afins). Comparados em minusculo contra o texto da excecao.
CONTEXT_MARKERS = (
    "context length", "context size", "n_ctx", "exceeds the available context",
    "too many tokens", "maximum context", "prompt is too long", "context window",
)

# Marcadores de limite de uso/cota (429 e derivados dos provedores hospedados).
RATE_LIMIT_MARKERS = (
    "429", "rate limit", "rate_limit", "ratelimit", "too many requests",
    "quota", "resource_exhausted", "overloaded", "requests per",
)


def _rate_limited(exc: BaseException) -> bool:
    """True quando a falha e limite de uso/cota, nao defeito de codigo ou rede."""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        try:
            if int(status) == 429:
                return True
        except (TypeError, ValueError):
            pass
    text = str(exc).lower()
    return any(marker in text for marker in RATE_LIMIT_MARKERS)


def _wait_hint(exc: BaseException) -> str:
    """'O servidor pediu Ns' quando a resposta traz Retry-After; senao, vazio."""
    headers = getattr(getattr(exc, "response", None), "headers", None)
    busca = getattr(headers, "get", None)
    if busca is None:
        return ""
    bruto = busca("retry-after") or busca("Retry-After")
    if bruto is None:
        return ""
    try:
        segundos = int(float(bruto))
    except (TypeError, ValueError):
        return ""
    if 0 < segundos <= 600:
        return f" O proprio servidor pediu {segundos} segundos de espera."
    return ""

# Catalog publico de modelos (mesma fonte de metadados que o Hermes usa quando o
# servidor nao publica nada: DeepSeek, Anthropic, OpenAI e afins). Cacheado uma
# vez por execucao para nao repetir a baixa.
MODELS_DEV_URL = "https://models.dev/api.json"
_models_dev_cache: dict | None = None


def _models_dev_catalog() -> dict | None:
    global _models_dev_cache
    if _models_dev_cache is None:
        try:
            r = requests.get(MODELS_DEV_URL, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    _models_dev_cache = data
        except Exception:  # noqa: BLE001 - sem catalogo, segue sem ele
            pass
    return _models_dev_cache


def _provider_hint(base_url: str) -> str:
    """api.deepseek.com -> 'deepseek'; openrouter.ai -> 'openrouter'; etc."""
    import urllib.parse

    host = urllib.parse.urlparse(str(base_url)).netloc.lower().split(":")[0]
    for prefix in ("api.", "inference-api.", "www."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    for suffix in (".com", ".ai", ".io", ".dev", ".net", ".org"):
        if host.endswith(suffix):
            host = host[: -len(suffix)]
    return host.split(".")[0]


def _timeout_for(cfg: dict) -> float:
    """Segundos que o cliente espera pelo modelo antes de desistir.

    Modelo na propria maquina responde em segundos -> 120 s chegam.
    Servidor remoto (API hospedada) pode levar mais de um minuto apenas para ler
    um contexto grande -> 300 s, senao a pessoa ve 'travou' e depois um erro.
    request_timeout_s no config.json manda em qualquer valor acima de zero.
    """
    try:
        explicito = int(cfg.get("request_timeout_s") or 0)
    except (TypeError, ValueError):
        explicito = 0
    if explicito > 0:
        return float(max(10, min(explicito, 900)))
    url = str(cfg.get("base_url", "")).lower()
    if "127.0.0.1" in url or "localhost" in url or "::1" in url:
        return 120.0
    return 300.0


class LLM:
    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config()
        self.timeout_s = _timeout_for(self.cfg)
        # Uma pergunta do usuario nao pode virar uma fila de pedidos atrasados no
        # servidor: cada nova tentativa paga a leitura do contexto de novo.
        raw_retries = self.cfg.get("max_retries")
        self.retries = max(0, min(1 if raw_retries is None else int(raw_retries), 4))
        self.client = OpenAI(
            base_url=self.cfg["base_url"],
            api_key=self.cfg.get("api" + "_key") or "none",
            timeout=self.timeout_s,
            max_retries=self.retries,
        )
        # Aviso para a tela (ex.: "o servidor demorou; tentei sem streaming").
        self.on_note: Callable[[str], None] | None = None
        # Tokens que o servidor informou no ULTIMO pedido (entrada/saida/cache).
        # None enquanto nenhum pedido voltou com contagem.
        self.last_usage: dict | None = None
        # Por que o pedido terminou ("stop", "length" quando o pensamento comeu o
        # max_tokens, "tool_calls"...). A tela usa isso para avisar em vez de silencio.
        self.last_finish: str | None = None
        # vao para False quando o servidor rejeita cada recurso (queda em escada)
        self._template_ok = True   # chat_template_kwargs (thinking / thinking_budget)
        self._effort_ok = True     # reasoning_effort

    def _record_usage(self, usage) -> None:
        """Guarda a contagem de tokens do pedido (o servidor manda no fim)."""
        if usage is None:
            return
        entrada = getattr(usage, "prompt_tokens", None)
        saida = getattr(usage, "completion_tokens", None)
        if entrada is None and saida is None:
            return
        cache = 0
        detalhes = getattr(usage, "prompt_tokens_details", None)
        if detalhes is not None:
            try:
                cache = int(getattr(detalhes, "cached_tokens", 0) or 0)
            except (TypeError, ValueError):
                cache = 0
        try:
            self.last_usage = {"entrada": int(entrada or 0), "saida": int(saida or 0),
                               "cache": cache}
        except (TypeError, ValueError):
            pass


    def _create_stream(self, kwargs: dict):
        """Cria o stream pedindo tambem a contagem de tokens.

        Servidor que recusa o campo 'stream_options' perde SO o contador: o
        pedido segue sem ele (nunca derruba a resposta por causa disso).
        """
        try:
            return self.client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            if "stream_options" in kwargs and "stream_options" in str(exc).lower():
                kwargs.pop("stream_options", None)
                return self.client.chat.completions.create(**kwargs)
            raise

    def _note(self, text: str) -> None:
        if self.on_note is not None:
            try:
                self.on_note(text)
            except Exception:  # noqa: BLE001 - aviso nunca derruba o turno
                pass

    def _rate_limit_error(self, exc: BaseException) -> LLMRateLimitError:
        """Frase simples para leigo: o que aconteceu e o que fazer agora."""
        return LLMRateLimitError(
            "O provedor pediu para esperar: o limite de uso deste momento foi atingido "
            "(ou a cota da conta acabou)."
            + _wait_hint(exc)
            + " Espere um pouco e mande a pergunta de novo. Se acontecer sempre, "
            "troque de provedor digitando /provedor."
        )

    def _apply_thinking(self, kwargs: dict) -> None:
        """Traduz o nivel de pensamento para os campos que os servidores entendem."""
        level = str(self.cfg.get("thinking") or "auto").lower()
        if level not in THINKING_LEVELS or level == "auto":
            return
        body: dict = {}
        if level == "off":
            if self._template_ok:
                body["chat_template_kwargs"] = {"thinking": False}
        elif level == "on":
            if self._template_ok:
                body["chat_template_kwargs"] = {"thinking": True}
        else:
            tpl: dict = {"thinking": True}
            if self._template_ok and level in _BUDGET:
                tpl["thinking_budget"] = _BUDGET[level]
            body["chat_template_kwargs"] = tpl
            if self._effort_ok and level in _EFFORT:
                body["reasoning_effort"] = _EFFORT[level]
        if body:
            kwargs["extra_body"] = body

    def _create(self, kwargs: dict):
        # Queda em escada: primeiro tenta com tudo; se o servidor reclamar de um
        # campo de pensamento, tira o reasoning_effort, depois o chat_template_kwargs.
        for _ in range(3):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as exc:  # noqa: BLE001
                eb = kwargs.get("extra_body") or {}
                text = str(exc).lower()
                if _rate_limited(exc):
                    # Limite de uso/cota: tentar de novo na mesma hora so gasta cota
                    # e a espera cresce - e isso que a pessoa precisa ouvir.
                    raise self._rate_limit_error(exc) from exc
                if eb and any(k in text for k in ("reasoning_effort", "thinking_budget",
                                                  "chat_template_kwargs")):
                    if "reasoning_effort" in eb:
                        self._effort_ok = False
                        eb.pop("reasoning_effort", None)
                        continue
                    self._template_ok = False
                    kwargs.pop("extra_body", None)
                    continue
                if "timeout" in text:
                    raise LLMError(
                        f"O modelo nao respondeu em {int(self.timeout_s)}s de espera. "
                        "Em servidor remoto isso costuma ser contexto grande demais: "
                        "baixe o orcamento de contexto ou ajuste request_timeout_s no config.json."
                    ) from exc
                if any(marker in text for marker in CONTEXT_MARKERS):
                    # Contexto estourou o teto do servidor: caso tratavel (o agente
                    # compacta e tenta de novo), nao morte do turno.
                    raise ContextOverflowError(
                        "O contexto passou do limite que o servidor aceita."
                    ) from exc
                raise LLMError(f"Falha ao falar com o modelo ({type(exc).__name__}): {exc}") from exc
        raise LLMError("Falha ao falar com o modelo (fallback esgotado).")

    def chat(self, messages: list, tools: list | None = None) -> dict:
        """Devolve a mensagem do assistente como dict pronto para o historico.

        Formato: {"role":"assistant","content":str,"reasoning":str?,"tool_calls":[...]?}
        """
        kwargs = {
            "model": self.cfg["model"],
            "messages": messages,
            "temperature": float(self.cfg.get("temperature", 0.3)),
            "max_tokens": int(self.cfg.get("max_tokens", 2048)),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        self._apply_thinking(kwargs)
        resp = self._create(kwargs)
        if not resp.choices:
            raise LLMError("O modelo respondeu vazio (sem choices).")
        self._record_usage(getattr(resp, "usage", None))
        self.last_finish = getattr(resp.choices[0], "finish_reason", None)
        msg = resp.choices[0].message
        out = {"role": "assistant", "content": msg.content or ""}
        reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
        if reasoning:
            out["reasoning"] = reasoning
        if getattr(msg, "tool_calls", None):
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return out

    def list_models(self) -> list[str]:
        """Modelos publicados pelo endpoint (/v1/models); abstrai data[] ou models[]."""
        try:
            listing = self.client.models.list()
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"Nao consegui listar modelos em {self.cfg['base_url']}: {exc}") from exc
        items = getattr(listing, "data", None)
        if not items:
            items = getattr(listing, "models", None) or []
        return [item.id for item in items]

    def discover_context(self) -> int | None:
        """Teto de TOKENS que o proprio servidor publica para o modelo dele.

        Devolve None quando o servidor nao publica nada (portal que esconde isso).
        Ordem tentada:
        1) 'props' da raiz do servidor (llama.cpp / motor igual): n_ctx, total_tokens;
        2) lista de modelos (/v1/models): campos tipo context_length (estilo
           OpenRouter), preferindo o modelo em uso.
        Nunca derruba a configuracao: pesquisa e, se nao acha, fica em silencio.
        """
        base = str(self.cfg.get("base_url", "")).rstrip("/")
        if not base:
            return None
        headers = {}
        key = self.cfg.get("api" + "_key")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        root = re.sub(r"/v\d+/?$", "", base) or base
        try:
            r = requests.get(root + "/props", headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    for field in ("n_ctx", "total_tokens"):
                        val = data.get(field)
                        if isinstance(val, (int, float)) and val > 0:
                            return int(val)
        except Exception:  # noqa: BLE001 - sondagem nunca quebra o assistente
            pass
        alvo = str(self.cfg.get("model", ""))
        melhor_outro = 0
        try:
            listing = self.client.models.list()
            items = getattr(listing, "data", None) or getattr(listing, "models", None) or []
            for item in items:
                info: dict = {}
                try:
                    info = item.model_dump()
                except Exception:  # noqa: BLE001 - itens de API variam muito
                    info = dict(getattr(item, "__dict__", {}) or {})
                if not isinstance(info, dict):
                    continue
                tokens = 0
                for field in ("context_length", "max_context_length", "max_context", "n_ctx"):
                    val = info.get(field)
                    if isinstance(val, (int, float)) and val > 0:
                        tokens = int(val)
                        break
                if tokens <= 0:
                    continue
                if str(getattr(item, "id", "")) == alvo:
                    return tokens
                melhor_outro = max(melhor_outro, tokens)
            if melhor_outro:
                return melhor_outro
        except Exception:  # noqa: BLE001 - sem lista nao ha o que descobrir
            pass
        # 3) Catalogo models.dev (mesma fonte do Hermes): APIs fechadas como
        # DeepSeek/Anthropic/OpenAI nao publicam contexto na API; o catalogo publica.
        hint = _provider_hint(base)
        catalog = _models_dev_catalog()
        if hint and catalog:
            models = (catalog.get(hint) or {}).get("models") or {}
            if isinstance(models, dict) and models:
                alvo_local = alvo.split("/")[-1].split(":")[0]
                for cand in (alvo, alvo_local):
                    info = models.get(cand)
                    if isinstance(info, dict):
                        lim: object = (info.get("limit") or {}).get("context")
                        if isinstance(lim, (int, float)) and lim > 0:
                            return int(lim)
                for mid, info in models.items():  # variantes ':free', '/model' etc.
                    if str(mid).split("/")[-1].split(":")[0] == alvo_local and isinstance(info, dict):
                        lim = (info.get("limit") or {}).get("context")
                        if isinstance(lim, (int, float)) and lim > 0:
                            return int(lim)
        return None

    def chat_stream(self, messages: list, tools: list | None = None,
                    on_text=None, on_reasoning=None, should_stop=None) -> dict:
        """Versao em streaming: entrega o texto em pedacos (callbacks) e monta a mensagem final.

        Se o servidor nao suportar streaming, cai automaticamente para chat() normal.
        should_stop: funcao sem argumentos; quando devolve True (usuario mandou
        parar), o streaming fecha e a mensagem volta parcial com 'stopped': True.
        """
        kwargs = {
            "model": self.cfg["model"],
            "messages": messages,
            "temperature": float(self.cfg.get("temperature", 0.3)),
            "max_tokens": int(self.cfg.get("max_tokens", 2048)),
            "stream": True,
            # Contador de tokens no fim do stream (o palco mostra por etapa).
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        self._apply_thinking(kwargs)
        t0 = time.time()
        try:
            resp = self._create_stream(kwargs)
        except Exception as exc:  # noqa: BLE001
            if _rate_limited(exc):
                # Nao adianta cair para o modo sem streaming: o pedido seguinte
                # bateria no mesmo limite e gastaria mais cota.
                raise self._rate_limit_error(exc) from exc
            # Servidor sem streaming (ou sem o campo de nivel): segue pelo caminho normal,
            # mas avisando na tela - espera dupla nao pode ser lida como trava.
            self._note("O servidor nao aceitou a resposta em pedacos "
                       f"({type(exc).__name__}); vou responder de uma vez (mais uma espera).")
            kwargs.pop("stream", None)
            kwargs.pop("extra_body", None)
            return self.chat(messages, tools)

        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_acc: dict[int, dict] = {}
        stopped = False
        try:
            for chunk in resp:
                if should_stop is not None and should_stop():
                    stopped = True  # usuario apertou o botao de parar
                    break
                if chunk.choices:
                    self.last_finish = (getattr(chunk.choices[0], "finish_reason", None)
                                        or self.last_finish)
                uso = getattr(chunk, "usage", None)
                if uso is not None:
                    # O stream manda a contagem no ultimo pedaco (choices vazio).
                    self._record_usage(uso)
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                rc = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
                if rc:
                    reasoning_parts.append(rc)
                    if on_reasoning:
                        on_reasoning(rc)
                if delta.content:
                    content_parts.append(delta.content)
                    if on_text:
                        on_text(delta.content)
                for tc in getattr(delta, "tool_calls", None) or []:
                    slot = tool_acc.setdefault(
                        tc.index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                    )
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            slot["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            slot["function"]["arguments"] += tc.function.arguments
        except Exception as exc:  # noqa: BLE001
            if _rate_limited(exc) and not (content_parts or reasoning_parts):
                # Nada chegou ainda e o servidor pediu espera: repetir sem streaming
                # seria outro pedido na mesma janela de limite.
                raise self._rate_limit_error(exc) from exc
            esperado = int(time.time() - t0)
            if content_parts or reasoning_parts:
                raise LLMError(
                    f"A resposta caiu no meio depois de {esperado}s de espera "
                    f"({type(exc).__name__}: {exc}). O texto que apareceu ficou guardado; "
                    "pergunte de novo ou use um orcamento de contexto menor."
                ) from exc
            self._note(f"Nada chegou do servidor em {esperado}s; vou tentar sem streaming "
                       "(uma espera a mais, e o pedido vai de novo para a fila).")
            kwargs.pop("stream", None)
            return self.chat(messages, tools)

        if stopped:
            try:
                resp.close()
            except Exception:  # noqa: BLE001 - fechar stream ja parado nao e erro
                pass
            out = {"role": "assistant", "content": "".join(content_parts), "stopped": True}
            if reasoning_parts:
                out["reasoning"] = "".join(reasoning_parts)
            return out

        out = {"role": "assistant", "content": "".join(content_parts)}
        if reasoning_parts:
            out["reasoning"] = "".join(reasoning_parts)
        if tool_acc:
            out["tool_calls"] = [tool_acc[i] for i in sorted(tool_acc)]
        return out

    def summarize(self, text: str) -> str:
        """Resumo sem ferramentas, usado na compressao de contexto."""
        prompt = [
            {
                "role": "system",
                "content": (
                    "Resuma a conversa abaixo em no maximo 15 pontos curtos. "
                    "Preserve: decisoes tomadas, caminhos de arquivo citados, "
                    "erros encontrados e pedidos ainda abertos. Responda so com o resumo."
                ),
            },
            {"role": "user", "content": text},
        ]
        try:
            return self.chat(prompt).get("content", "")
        except LLMError:
            # Sem resumo automatico, mantem-se o corte simples.
            return ""

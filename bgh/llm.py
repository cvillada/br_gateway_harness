"""Cliente OpenAI-compativel: llama.cpp, LM Studio, DeepSeek e afins.

Extras:
- Captura de "pensamento": aceita reasoning_content ou reasoning na resposta.
- Toggle de thinking: cfg["thinking"] = auto|on|off. on/off manda
  chat_template_kwargs {"thinking": bool}; se o servidor rejeitar, o cliente
  desliga o recurso sozinho e segue funcionando.
"""

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


class LLM:
    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or load_config()
        self.client = OpenAI(
            base_url=self.cfg["base_url"],
            api_key=self.cfg.get("api" + "_key") or "none",
            timeout=120.0,
            max_retries=2,
        )
        # vao para False quando o servidor rejeita cada recurso (queda em escada)
        self._template_ok = True   # chat_template_kwargs (thinking / thinking_budget)
        self._effort_ok = True     # reasoning_effort

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
                if eb and any(k in text for k in ("reasoning_effort", "thinking_budget",
                                                  "chat_template_kwargs")):
                    if "reasoning_effort" in eb:
                        self._effort_ok = False
                        eb.pop("reasoning_effort", None)
                        continue
                    self._template_ok = False
                    kwargs.pop("extra_body", None)
                    continue
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
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        self._apply_thinking(kwargs)
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception:  # noqa: BLE001
            # Servidor sem streaming (ou sem o campo de nivel): segue pelo caminho normal.
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
            if content_parts or reasoning_parts:
                raise LLMError(f"Streaming caiu no meio da resposta: {exc}") from exc
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

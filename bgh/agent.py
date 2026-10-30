"""Loop do agente: mensagens -> chamadas de ferramenta -> resultados -> resposta final.

Inclui compressao de contexto (resumo automatico quando passa do orcamento) e
persistencia da conversa em ~/.bgh/session.json (retoma de onde parou).
"""

import json
import threading

from .approvals import Gate
from .config import SESSION_FILE
from .llm import LLM, LLMError
from .prompts import build_system_prompt
from .tools import ToolBox
from .tools.memory import load_lines
from .tools.skills import discover, index_lines

# Mensagem mostrada/quando o usuario manda parar (botao CTRL+C / ESC na UI).
STOPPED_NOTE = "(parei a resposta, como voce pediu)"


class Agent:
    def __init__(self, cfg: dict, llm: LLM, gate: Gate, on_event=None):
        self.cfg = cfg
        self.llm = llm
        self.gate = gate
        self.on_event = on_event  # callback(nome_ferramenta, resumo) para exibir atividade
        self.last_reasoning: list[str] = []
        self.last_compressed = False
        self.last_streamed = False
        self.on_text_delta = None      # callback(pedaco_de_texto) para streaming na UI
        self.on_reasoning_delta = None # callback(pedaco_de_pensamento)
        # Botao de parar: a UI seta este evento e o agente interrompe streaming,
        # ferramentas e rodadas na hora (igual ao CTRL+C do Hermes).
        self.stop_event = threading.Event()
        self.tools = ToolBox(cfg, gate, stop_event=self.stop_event)
        skills = discover()
        self.messages = [
            {
                "role": "system",
                "content": build_system_prompt(
                    load_lines("user"), load_lines("note"), index_lines(skills)
                ),
            }
        ]
        self._load_session()

    # ----- sessao -------------------------------------------------------------
    def _load_session(self) -> None:
        if not SESSION_FILE.exists():
            return
        try:
            history = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            if isinstance(history, list):
                self.messages.extend(history)
        except (json.JSONDecodeError, OSError):
            pass  # sessao corrompida: comeca limpa, sem quebrar o chat

    def _save_session(self) -> None:
        try:
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            SESSION_FILE.write_text(
                json.dumps(self.messages[1:], ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def new_session(self) -> None:
        skills = discover()
        self.messages = [
            {
                "role": "system",
                "content": build_system_prompt(
                    load_lines("user"), load_lines("note"), index_lines(discover())
                ),
            }
        ]
        self.gate.session_rules.clear()
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    # ----- turno --------------------------------------------------------------
    def run_turn(self, user_text: str) -> str:
        self.last_reasoning = []
        self.last_compressed = False
        self.stop_event.clear()
        self.messages.append({"role": "user", "content": user_text})
        max_rounds = int(self.cfg.get("max_tool_rounds", 12))
        rounds = 0
        sig_count: dict[str, int] = {}   # anti-loop: chamadas identicas sao contadas
        fail_streak = 0                  # anti-loop: erros em sequencia fecham a janela
        while rounds < max_rounds:
            if self.stop_event.is_set():
                self._save_session()
                return STOPPED_NOTE
            use_stream = bool(self.cfg.get("stream", True)) and hasattr(self.llm, "chat_stream")
            if use_stream:
                msg = self.llm.chat_stream(
                    self.messages,
                    self.tools.specs,
                    on_text=self.on_text_delta,
                    on_reasoning=self.on_reasoning_delta,
                    should_stop=self.stop_event.is_set,
                )
            else:
                msg = self.llm.chat(self.messages, self.tools.specs)
            self.last_streamed = use_stream
            self.messages.append(msg)
            if msg.get("stopped"):
                # Usuario parou no meio do streaming; o parcial fica guardado.
                self._save_session()
                return STOPPED_NOTE
            if msg.get("reasoning"):
                self.last_reasoning.append(str(msg["reasoning"]))
            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                self._save_session()
                return msg.get("content", "")
            user_stopped = False
            for tc in tool_calls:
                fn = tc["function"]
                if self.stop_event.is_set():
                    # Historico continua valido: toda tool_call precisa de resposta.
                    user_stopped = True
                    self.messages.append(
                        {"role": "tool", "tool_call_id": tc["id"],
                         "content": "BLOQUEADO: o usuario mandou parar esta resposta."}
                    )
                    continue
                sig = self._call_signature(fn)
                sig_count[sig] = sig_count.get(sig, 0) + 1
                if sig_count[sig] >= 3:
                    # Circuit breaker: mesmissima chamada pela 3a vez nao executa.
                    result = (
                        f"LOOP DETECTADO: a chamada IDENTICA a '{fn['name']}' ja foi repetida "
                        f"{sig_count[sig]} vezes e nao vai executar de novo. Mude argumentos, "
                        "caminho ou estrategia; se nao houver saida, explique o obstaculo ao usuario."
                    )
                else:
                    if self.on_event:
                        self.on_event(fn["name"], fn.get("arguments", "")[:120])
                    result = self.tools.dispatch(fn["name"], fn.get("arguments", ""))
                fail_streak = (
                    fail_streak + 1
                    if result.startswith(("ERRO", "BLOQUEADO", "FALHOU", "LOOP"))
                    else 0
                )
                self.messages.append(
                    {"role": "tool", "tool_call_id": tc["id"], "content": result}
                )
            if user_stopped:
                self._save_session()
                return STOPPED_NOTE
            rounds += 1
            if self._maybe_compress():
                self.last_compressed = True
            if fail_streak >= 5:
                return self._close_window(
                    "(5 ferramentas falharam em sequencia; pare de tentar variantes do mesmo "
                    "caminho e responda ao usuario: o que foi tentado, o que travou e a saida)"
                )
        # Estourou o limite de rodadas: fecha a janela pedindo resposta com o que tem.
        return self._close_window(
            "(limite de ferramentas atingido neste turno; responda com o que ja foi coletado)"
        )

    # ----- janela final -------------------------------------------------------
    def _close_window(self, note: str) -> str:
        self.messages.append({"role": "user", "content": note})
        final = self.llm.chat(self.messages)
        self.messages.append(final)
        self._save_session()
        return final.get("content", "")

    @staticmethod
    def _call_signature(fn: dict) -> str:
        """Assinatura canonica da chamada (nome + argumentos normalizados) para detectar repeticao."""
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except (json.JSONDecodeError, TypeError):
            args = str(fn.get("arguments", "")).strip()
        return fn["name"] + "|" + json.dumps(args, sort_keys=True, ensure_ascii=False)

    # ----- contexto -----------------------------------------------------------
    def _estimate_chars(self) -> int:
        return sum(len(json.dumps(m, ensure_ascii=False)) for m in self.messages)

    def ctx_usage(self) -> dict:
        """Medidor para a UI: quantos chars do orcamento ja foram usados."""
        chars = self._estimate_chars()
        budget = int(self.cfg.get("context_budget_chars", 60000))
        pct = min(int(100 * chars / max(budget, 1)), 999)
        return {"chars": chars, "budget": budget, "pct": pct, "messages": len(self.messages)}

    def _maybe_compress(self) -> bool:
        budget = int(self.cfg.get("context_budget_chars", 60000))
        if self._estimate_chars() <= budget:
            return False
        keep_tail = 8
        if len(self.messages) <= keep_tail + 2:
            return False
        head, tail = self.messages[1:-keep_tail], self.messages[-keep_tail:]
        transcript = "\n".join(
            f"{m.get('role')}: {str(m.get('content', ''))[:500]}" for m in head
        )
        summary = self.llm.summarize(transcript)
        if not summary:
            # Sem resumo possivel, corta o meio (falha aberta mas visivel ao modelo).
            summary = "(partes antigas da conversa foram removidas por limite de contexto)"
        self.messages = [self.messages[0]] + [
            {"role": "system", "content": "RESUMO DA CONVERSA ANTERIOR:\n" + summary}
        ] + tail
        self._save_session()
        return True

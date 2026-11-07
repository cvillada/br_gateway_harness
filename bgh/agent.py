"""Loop do agente: mensagens -> chamadas de ferramenta -> resultados -> resposta final.

Inclui compressao de contexto (resumo automatico quando passa do orcamento) e
persistencia da conversa em ~/.bgh/session.json (retoma de onde parou).
"""

import json
import threading
from typing import Callable

from .approvals import Gate
from .config import SESSION_FILE
from .llm import ContextOverflowError, LLM, LLMError
from .prompts import build_system_prompt
from .tools import ToolBox
from .tools.memory import load_lines
from .tools.skills import discover, index_lines

# Mensagem mostrada/quando o usuario manda parar (botao CTRL+C / ESC na UI).
STOPPED_NOTE = "(parei a resposta, como voce pediu)"

# Sinais de que o provedor recusou a IMAGEM (modelo sem visao).
VISION_MARKERS = ("image", "vision", "multimodal", "image_url", "media type",
                  "content type")


def _parece_falta_de_visao(exc: BaseException) -> bool:
    texto = str(exc).lower()
    return any(marcador in texto for marcador in VISION_MARKERS)


class Agent:
    def __init__(self, cfg: dict, llm: LLM, gate: Gate, on_event=None):
        self.cfg = cfg
        self.llm = llm
        self.gate = gate
        self.on_event = on_event  # callback(nome_ferramenta, resumo) para exibir atividade
        self.last_reasoning: list[str] = []
        self.last_compressed = False
        self.last_streamed = False
        # Tokens que o servidor informou no ultimo pedido (o palco mostra por etapa).
        self.last_usage: dict | None = None
        self.on_usage: Callable[[dict | None], None] | None = None
        self.on_text_delta = None      # callback(pedaco_de_texto) para streaming na UI
        self.on_reasoning_delta = None # callback(pedaco_de_pensamento)
        # Avisos do proprio agente (compactando, estouro de contexto) viram linha na tela.
        self.on_note: Callable[[str], None] | None = None
        # Cada chamada do modelo comeca um bloco novo na UI (reset de cabecalhos).
        self.on_round_start: Callable[[], None] | None = None
        # Mensagem do usuario digitada NO MEIO do processamento (estilo Hermes):
        # chega agora, sera entregue ao modelo na proxima fronteira de rodada.
        self.steer_queue: list[str] = []
        self._steer_lock = threading.Lock()
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

    # ----- mensagens com imagem (visao) ---------------------------------------
    @staticmethod
    def _texto_de(mensagem: dict) -> str:
        """Texto puro da mensagem (ignora pedacos de imagem)."""
        conteudo = mensagem.get("content")
        if isinstance(conteudo, str):
            return conteudo
        partes = []
        for parte in conteudo or []:
            if isinstance(parte, dict) and parte.get("type") == "text":
                partes.append(str(parte.get("text", "")))
        return "\n".join(partes)

    @staticmethod
    def _sem_imagem(mensagem: dict) -> dict:
        """Copia da mensagem com as imagens trocadas por marcador de texto.

        Usado ao salvar a sessao e ao medir o contexto: base64 de foto nao pode
        entrar no session.json (ficaria com megabytes) nem inflar o medidor.
        """
        conteudo = mensagem.get("content")
        if not isinstance(conteudo, list):
            return mensagem
        partes = []
        for parte in conteudo:
            if isinstance(parte, dict) and parte.get("type") == "image_url":
                partes.append({"type": "text", "text": "[imagem anexada nesta conversa]"})
            else:
                partes.append(parte)
        if all(isinstance(p, dict) and p.get("type") == "text" for p in partes):
            # so texto: volta a ser string (todo servidor aceita; e o session.json fica limpo)
            return {**mensagem, "content": "\n".join(str(p.get("text", "")) for p in partes)}
        return {**mensagem, "content": partes}

    def _anexar_imagem(self, user_text: str, caminho: str) -> None:
        """Mensagem do usuario com a foto (parte de imagem para a visao)."""
        from .tools.files import image_data_url

        url, _tamanho, erro = image_data_url(caminho)
        if not url:
            self._note(erro or "nao consegui preparar a imagem; seguindo so com o texto.")
            self.messages.append({"role": "user", "content": user_text})
            return
        self.messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        })

    def _tem_imagem(self) -> bool:
        for m in self.messages:
            c = m.get("content")
            if isinstance(c, list) and any(
                    isinstance(p, dict) and p.get("type") == "image_url" for p in c):
                return True
        return False

    def _tirar_imagem(self) -> bool:
        """Remove a imagem da mensagem (provedor sem visao): mantem o texto."""
        for m in reversed(self.messages):
            if m.get("role") == "user" and isinstance(m.get("content"), list):
                m["content"] = self._texto_de(m)
                return True
        return False

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
            historico = [self._sem_imagem(m) for m in self.messages[1:]]
            SESSION_FILE.write_text(
                json.dumps(historico, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass

    def new_session(self) -> None:
        skills = discover()
        self.messages = [
            {
                "role": "system",
                "content": build_system_prompt(
                    load_lines("user"), load_lines("note"), index_lines(skills)
                ),
            }
        ]
        self.gate.session_rules.clear()
        self.last_compressed = False   # aviso 'compactado' nao pode sobreviver ao zerar a conversa
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    # ----- turno --------------------------------------------------------------
    def run_turn(self, user_text: str, imagem: str | None = None) -> str:
        self.last_reasoning = []
        self.last_compressed = False
        self.stop_event.clear()
        if imagem:
            self._anexar_imagem(user_text, imagem)
        else:
            self.messages.append({"role": "user", "content": user_text})
        max_rounds = max(1, int(self.cfg.get("max_tool_rounds", 20)))   # tamanho da etapa
        teto = max(max_rounds,
                   int(self.cfg.get("max_tool_rounds_teto", max_rounds * 2)))
        limite = max_rounds
        rounds = 0
        sig_count: dict[str, int] = {}   # anti-loop: chamadas identicas sao contadas
        fail_streak = 0                  # anti-loop: erros em sequencia fecham a janela
        while rounds < limite:
            if self.stop_event.is_set():
                self._save_session()
                return STOPPED_NOTE
            use_stream = bool(self.cfg.get("stream", True)) and hasattr(self.llm, "chat_stream")
            if self._compress_if_needed():
                self.last_compressed = True
            try:
                self._round_start()
                msg = self._call_model(use_stream)
            except ContextOverflowError as exc:
                # O servidor recusou o tamanho: compactar e tentar na hora.
                # Antes isso era onde a tela "parava" quando o contexto enchia.
                self._note("O servidor recusou o tamanho do contexto; vou compactar a conversa e tentar de novo.")
                self._force_compress()
                self.last_compressed = True
                try:
                    self._round_start()
                    msg = self._call_model(use_stream)
                except ContextOverflowError:
                    raise LLMError(
                        str(exc) + " Mesmo depois de compactar, o pedido nao coube no servidor. "
                        "Reduza o limite aqui na tela: /ctx 60000"
                    ) from exc
            except LLMError as exc:
                # Modelo sem visao: segue sem a foto (nunca deixa a pessoa sem resposta).
                if not (self._tem_imagem() and _parece_falta_de_visao(exc)):
                    raise
                self._tirar_imagem()
                self._note("O modelo deste provedor nao le imagem; vou seguir sem a foto. "
                           "Para ler imagens, escolha um modelo com visao (/modelo).")
                self._round_start()
                msg = self._call_model(use_stream)
            self.last_streamed = use_stream
            self._usage_note()
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
                if result.startswith("PARADO"):
                    # A ferramenta obedeceu ao 'parar': o turno fecha agora, sem
                    # emendar outra rodada de ferramentas atrasada.
                    user_stopped = True
            if user_stopped:
                self._save_session()
                return STOPPED_NOTE
            self._drain_steers()  # steering do meio do turno chega entre as rodadas
            rounds += 1
            if self._compress_if_needed():
                self.last_compressed = True
            if fail_streak >= 5:
                self._note("5 ferramentas falharam em sequencia; vou fechar este turno com o que ja tenho.")
                return self._close_window(
                    "(5 ferramentas falharam em sequencia. Pare de tentar variantes do mesmo "
                    "caminho e responda em portugues ao usuario: o que foi tentado, o que travou "
                    "e o que ele pode fazer.)"
                )
            if rounds >= limite:
                # Limite da etapa: se o turno esta PROGREDINDO, prorroga sozinho ate o
                # teto (nao e parede, mas tambem nao vira loop infinito). Sem progresso
                # (falha/loop na ultima rodada), fecha como antes.
                if fail_streak == 0 and limite < teto:
                    novo = min(limite + max_rounds, teto)
                    self._note(
                        f"Ja usei {limite} ferramentas neste pedido; vou continuar por "
                        f"mais {novo - limite} (CTRL+C ou ESC para parar)."
                    )
                    limite = novo
                else:
                    break
        if limite >= teto:
            self._note(f"Parei em {limite} ferramentas para nao gastar demais; "
                       "vou responder com o que ja coletei.")
            return self._close_window(
                f"(voce chegou ao teto de {limite} ferramentas deste turno. Responda em "
                "portugues com o que ja coletou, sem prometer acao futura, e termine a "
                "resposta dizendo ao usuario que ele pode escrever 'continue' para voce "
                "seguir de onde parou.)"
            )
        # Estourou o limite de rodadas: fecha a janela pedindo resposta com o que tem.
        self._note("Limite de ferramentas deste turno atingido; vou responder com o que ja coletei.")
        return self._close_window(
            "(limite de ferramentas deste turno atingido. Responda em portugues usando apenas "
            "o que ja foi coletado; nao prometa acao futura, feche o assunto agora.)"
        )

    # ----- janela final -------------------------------------------------------
    def _close_window(self, note: str) -> str:
        self.messages.append({"role": "user", "content": note})
        self._round_start()  # fechamento e bloco novo: cabecalho 'resposta' garantido
        # Fechamento em streaming (estilo Hermes): o texto aparece ao vivo, sem
        # silencio morto no ultimo modelo quando o contexto ja esta cheio.
        use_stream = bool(self.cfg.get("stream", True)) and hasattr(self.llm, "chat_stream")
        try:
            if use_stream:
                final = self.llm.chat_stream(
                    self.messages, None,
                    on_text=self.on_text_delta,
                    on_reasoning=self.on_reasoning_delta,
                    should_stop=self.stop_event.is_set,
                )
            else:
                final = self.llm.chat(self.messages)
        except ContextOverflowError:
            # O fechamento tambem pode esbarrar no tamanho: compacta e fecha no modo normal.
            self._force_compress()
            final = self.llm.chat(self.messages)
        self._usage_note()
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
        return sum(len(json.dumps(self._sem_imagem(m), ensure_ascii=False))
                   for m in self.messages)

    def ctx_usage(self) -> dict:
        """Medidor para a UI: quantos chars do orcamento ja foram usados.

        Traz tambem a equivalencia em tokens: o numero REAL que o servidor contou
        no ultimo pedido; antes do primeiro pedido, a estimativa de 3,5 caracteres
        por token (a tela marca a estimativa com '~').
        """
        chars = self._estimate_chars()
        budget = int(self.cfg.get("context_budget_chars", 156000))
        pct = min(int(100 * chars / max(budget, 1)), 999)
        uso = self.last_usage or {}
        reais = uso.get("entrada") if isinstance(uso, dict) else None
        from .setup_wizard import CHARS_POR_TOKEN

        if reais:
            tokens, tokens_reais = int(reais), True
        else:
            tokens, tokens_reais = int(chars / CHARS_POR_TOKEN), False
        return {"chars": chars, "budget": budget, "pct": pct,
                "messages": len(self.messages), "tokens": tokens,
                "tokens_reais": tokens_reais,
                "tokens_teto": int(budget / CHARS_POR_TOKEN)}

    def _compress_pct(self) -> int:
        """A partir de quanto do orcamento comeca a compactar (padrao 85%)."""
        try:
            pct = int(self.cfg.get("context_compress_pct", 85))
        except (TypeError, ValueError):
            pct = 85
        return max(50, min(pct, 100))

    def _note(self, text: str) -> None:
        if self.on_note is not None:
            try:
                self.on_note(text)
            except Exception:  # noqa: BLE001 - aviso nunca derruba o turno
                pass

    def _usage_note(self) -> None:
        """Repassa a contagem de tokens do ultimo pedido para a tela."""
        uso = getattr(self.llm, "last_usage", None)
        self.last_usage = uso
        if self.on_usage is not None:
            try:
                self.on_usage(uso)
            except Exception:  # noqa: BLE001 - contador nunca derruba o turno
                pass

    def steer(self, text: str) -> None:
        """Mensagem do meio do turno: entra na fila, o modelo recebe apos os
        resultados de ferramenta, sem derrubar o trabalho em andamento."""
        text = str(text).strip()
        if text:
            with self._steer_lock:
                self.steer_queue.append(text)

    def pop_steer(self) -> str | None:
        """Steer que chegou tarde (turno ja fechando): vira o proximo turno."""
        with self._steer_lock:
            return self.steer_queue.pop(0) if self.steer_queue else None

    def _drain_steers(self) -> int:
        with self._steer_lock:
            pending, self.steer_queue = self.steer_queue, []
        for t in pending:
            self.messages.append({
                "role": "user",
                "content": f"(mensagem do usuario durante o processamento): {t}",
            })
        if pending:
            self._note(f"{len(pending)} mensagem(s) recebida(s) no meio do turno; "
                       "entregue(s) ao modelo agora.")
        return len(pending)

    def _round_start(self) -> None:
        if self.on_round_start is not None:
            try:
                self.on_round_start()
            except Exception:  # noqa: BLE001 - reset de cabecalho nunca derruba o turno
                pass

    def _call_model(self, use_stream: bool) -> dict:
        if use_stream:
            return self.llm.chat_stream(
                self.messages,
                self.tools.specs,
                on_text=self.on_text_delta,
                on_reasoning=self.on_reasoning_delta,
                should_stop=self.stop_event.is_set,
            )
        return self.llm.chat(self.messages, self.tools.specs)

    def _compress_once(self) -> bool:
        """Uma rodada de compactacao: o comeco da conversa vira um resumo."""
        keep_tail = 8
        if len(self.messages) <= keep_tail + 2:
            return False
        head, tail = self.messages[1:-keep_tail], self.messages[-keep_tail:]
        # Ferramenta no comeco da cauda perde o par 'assistant' quando este e
        # cortado; servidores rejeitam a mensagem orfa: ela vai para o resumo.
        while tail and tail[0].get("role") == "tool":
            head.append(tail.pop(0))
        if not head:
            return False
        transcript = "\n".join(
            f"{m.get('role')}: {self._texto_de(m)[:500]}" for m in head
        )
        self._note("Compactando a conversa em resumo (o resumo custa uma espera extra)...")
        summary = self.llm.summarize(transcript)
        if not summary:
            # Sem resumo possivel, corta o meio (falha aberta mas visivel ao modelo).
            summary = "(partes antigas da conversa foram removidas por limite de contexto)"
        self.messages = [self.messages[0]] + [
            {"role": "system", "content": "RESUMO DA CONVERSA ANTERIOR:\n" + summary}
        ] + tail
        self._save_session()
        return True

    def _compress_if_needed(self) -> bool:
        """Compacta ANTES de esbarrar no teto: comeca no % configurado (85%)."""
        budget = int(self.cfg.get("context_budget_chars", 156000))
        threshold = int(budget * self._compress_pct() / 100)
        if self._estimate_chars() <= threshold:
            return False
        did = False
        for _ in range(3):
            if not self._compress_once():
                break
            did = True
            if self._estimate_chars() <= threshold:
                break
        return did

    def _force_compress(self) -> bool:
        """Compactacao depois que o servidor ja recusou: baixa ate 70% do orcamento."""
        budget = int(self.cfg.get("context_budget_chars", 156000))
        target = int(budget * 0.70)
        did = False
        for _ in range(4):
            if self._estimate_chars() <= target:
                break
            if not self._compress_once():
                break
            did = True
        return did

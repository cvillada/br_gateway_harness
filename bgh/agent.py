"""Loop do agente: mensagens -> chamadas de ferramenta -> resultados -> resposta final.

Inclui compressao de contexto (resumo automatico quando passa do orcamento) e
persistencia da conversa em ~/.bgh/session.json (retoma de onde parou).
"""

import json
import threading
from pathlib import Path
from typing import Callable

from . import i18n
from .approvals import Gate
from .config import SESSION_FILE
from .llm import ContextOverflowError, LLM, LLMError
from .i18n import t
from .prompts import build_system_prompt
from .tools import ToolBox
from .tools.memory import load_lines
from .tools.skills import discover, index_lines

# Mensagem mostrada/quando o usuario manda parar (botao CTRL+C / ESC na UI).
STOPPED_NOTE = "(parei a resposta, como voce pediu)"

# Sinais de que o provedor recusou a IMAGEM (modelo sem visao).
VISION_MARKERS = ("image", "vision", "multimodal", "image_url", "media type",
                  "content type")

# Teto de fotos por turno: cada uma vira base64 no pedido (33% maior) e o
# contexto do modelo local e curto. Acima disso a tela avisa que ficaram de fora.
MAX_IMAGENS = 4

# Linha que uma FERRAMENTA usa para dizer "olhei e tirei este print". O resultado
# de ferramenta nao carrega imagem (servidor local recusa): o agent le esta marca
# e manda o print como mensagem do usuario, que e o unico jeito que funciona em
# qualquer provedor. Usada pelo ver_pagina (bgh/tools/pagina.py).
MARCA_IMAGEM = "IMAGEM: "
# Prints por rodada: dois bastam para "gerou, abriu, olhou" e nao incham o contexto.
MAX_PRINTS_RODADA = 2


def _imagens_do_resultado(resultado: str) -> list[str]:
    """Caminhos de print que uma ferramenta devolveu, na ordem."""
    achados: list[str] = []
    for linha in str(resultado or "").splitlines():
        if not linha.startswith(MARCA_IMAGEM):
            continue
        caminho = linha[len(MARCA_IMAGEM):].strip()
        try:
            if caminho and Path(caminho).is_file():
                achados.append(caminho)
        except OSError:
            continue
    return achados


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
        # Compactacao que ja tentou e nao baixou o suficiente neste turno: repetir
        # seria uma chamada de modelo por rodada sem ganho (ver _compress_if_needed).
        self._compactacao_travada = False
        # Aviso ao modelo no % do teto: sai uma vez por turno (ver _aviso_orcamento).
        self._aviso_teto_dado = False
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
        self.messages = [self._system_message()]
        self._load_session()

    @staticmethod
    def _system_message() -> dict:
        """Prompt do sistema no idioma atual (tambem e o que /lingua refaz)."""
        skills = discover()
        return {
            "role": "system",
            "content": build_system_prompt(
                load_lines("user"), load_lines("note"), index_lines(skills)
            ),
        }

    def refresh_prompt(self) -> None:
        """Refaz o pedido ao modelo depois de trocar o idioma (comando /lingua)."""
        if self.messages and self.messages[0].get("role") == "system":
            self.messages[0]["content"] = self._system_message()["content"]
        else:
            self.messages.insert(0, self._system_message())

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

    def _chave_visao(self) -> str:
        return f"{self.cfg.get('base_url', '')}|{self.cfg.get('model', '')}"

    def _anexar_imagem(self, user_text: str, caminho: str) -> None:
        """Mensagem do usuario com UMA foto (chamada antiga, mantida)."""
        self._anexar_imagens(user_text, [caminho])

    def _anexar_imagens(self, user_text: str, caminhos: list) -> None:
        """Mensagem do usuario com as fotos anexadas (clipe da tela ou '@').

        Cada foto e uma parte 'image_url' na MESMA mensagem: assim o modelo ve
        todas juntas e o historico continua com um turno so. O que nao puder ir
        (arquivo grande, formato estranho) vira aviso na tela - nunca some calado.
        """
        from .tools.files import image_data_url

        caminhos = [c for c in (caminhos or []) if c]
        bloqueados = self.cfg.get("vision_blocklist") or []
        if isinstance(bloqueados, list) and self._chave_visao() in bloqueados:
            # Este modelo ja recusou imagem antes: decide ANTES e avisa, em vez de
            # mandar de novo e tomar outro 400.
            self._note(t("agent.vision_blocked", model=i18n.cmd("model")))
            self.messages.append({"role": "user", "content": user_text})
            return
        partes: list[dict] = [{"type": "text", "text": user_text}]
        for caminho in caminhos[:MAX_IMAGENS]:
            url, _tamanho, erro = image_data_url(caminho)
            if not url:
                self._note(erro or t("agent.image_fail"))
                continue
            partes.append({"type": "image_url", "image_url": {"url": url}})
        if len(caminhos) > MAX_IMAGENS:
            self._note(t("agent.image_more", n=len(caminhos) - MAX_IMAGENS))
        if len(partes) == 1:
            self.messages.append({"role": "user", "content": user_text})
            return
        self.messages.append({"role": "user", "content": partes})

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
        self.messages = [self._system_message()]
        self.gate.session_rules.clear()
        self.last_compressed = False   # aviso 'compactado' nao pode sobreviver ao zerar a conversa
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    # ----- turno --------------------------------------------------------------
    def run_turn(self, user_text: str, imagem: str | None = None,
                 imagens: list | None = None) -> str:
        self.last_reasoning = []
        self.last_compressed = False
        self._compactacao_travada = False   # cada turno tenta compactar de novo
        self._aviso_teto_dado = False       # aviso de orcamento ao modelo (uma vez)
        self.stop_event.clear()
        fotos = [c for c in (imagens or []) if c]
        if imagem:
            fotos.insert(0, imagem)
        if fotos:
            # Conversa longa + foto = o servidor local pode DESCARTAR a imagem em
            # silencio (o modelo entao responde "nao chegou imagem"). Abrir espaco
            # antes de enviar e o que evita esse susto.
            self._abrir_espaco_para_imagem()
            self._anexar_imagens(user_text, fotos)
        else:
            self.messages.append({"role": "user", "content": user_text})
        max_rounds = max(1, int(self.cfg.get("max_tool_rounds", 20)))   # tamanho da etapa
        teto_cfg = int(self.cfg.get("max_tool_rounds_teto", max_rounds * 6))
        # teto 0 = SEM parede: projeto/tarefa longa prorroga enquanto o turno progride
        # (os anti-loop de chamada repetida e de 5 falhas continuam valendo).
        teto = 0 if teto_cfg <= 0 else max(max_rounds, teto_cfg)
        limite = max_rounds
        rounds = 0
        sig_count: dict[str, int] = {}   # anti-loop: chamadas identicas sao contadas
        ok_sigs: set[str] = set()        # chamadas DISTINTAS que deram certo (progresso)
        feitos_antes = 0                 # progresso no comeco da etapa atual
        prorrogou = False                # a nota de prorrogacao sai UMA vez por turno
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
                self._note(t("agent.overflow"))
                self._force_compress()
                self.last_compressed = True
                try:
                    self._round_start()
                    msg = self._call_model(use_stream)
                except ContextOverflowError:
                    raise LLMError(str(exc) + t("agent.overflow_still",
                                                ctx=i18n.cmd("ctx"))) from exc
            except LLMError as exc:
                # Modelo sem visao: segue sem a foto (nunca deixa a pessoa sem resposta).
                if not (self._tem_imagem() and _parece_falta_de_visao(exc)):
                    raise
                self._tirar_imagem()
                try:
                    marca = self._chave_visao()
                    lista = self.cfg.setdefault("vision_blocklist", [])
                    if marca not in lista:
                        lista.append(marca)
                        from .config import save_config
                        save_config(self.cfg)
                except Exception:  # noqa: BLE001 - memoria de recurso nunca derruba o turno
                    pass
                self._note(t("agent.vision_refused", model=i18n.cmd("model")))
                self._round_start()
                msg = self._call_model(use_stream)
            if (not msg.get("tool_calls") and not msg.get("stopped")
                    and not str(msg.get("content") or "").strip()):
                # Resposta SEM texto (o modelo gastou a saida pensando, tipico logo
                # depois de compactar): antes o turno morria aqui e a pessoa tinha de
                # digitar 'continue'. Uma segunda tentativa, sem mexer no historico.
                nova = self._retry_sem_texto(use_stream)
                if (str(nova.get("content") or "").strip() or nova.get("tool_calls")
                        or nova.get("stopped")):
                    msg = nova
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
            prints: list[str] = []
            for tc in tool_calls:
                fn = tc["function"]
                if self.stop_event.is_set():
                    # Historico continua valido: toda tool_call precisa de resposta.
                    user_stopped = True
                    self.messages.append(
                        {"role": "tool", "tool_call_id": tc["id"],
                         "content": t("agent.tool_stopped")}
                    )
                    continue
                sig = self._call_signature(fn)
                sig_count[sig] = sig_count.get(sig, 0) + 1
                if sig_count[sig] >= 3:
                    # Circuit breaker: mesmissima chamada pela 3a vez nao executa.
                    result = t("agent.loop", nome=fn["name"], n=sig_count[sig])
                else:
                    if self.on_event:
                        self.on_event(fn["name"], fn.get("arguments", "")[:120])
                    result = self.tools.dispatch(fn["name"], fn.get("arguments", ""))
                    prints.extend(_imagens_do_resultado(result))
                falhou = result.startswith(("ERRO", "BLOQUEADO", "FALHOU", "LOOP"))
                fail_streak = fail_streak + 1 if falhou else 0
                if not falhou:
                    ok_sigs.add(sig)   # chamada distinta que deu certo = progresso
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
            if prints:
                # Ferramenta que OLHOU uma tela: o print entra como imagem para o
                # modelo (resultado de ferramenta nao carrega imagem). Sem visao do
                # modelo, _anexar_imagens avisa e segue so com o texto.
                self._anexar_imagens(t("agent.tool_image", n=len(prints)),
                                     prints[:MAX_PRINTS_RODADA])
            self._drain_steers()  # steering do meio do turno chega entre as rodadas
            self._aviso_orcamento(rounds + 1, teto)
            rounds += 1
            if self._compress_if_needed():
                self.last_compressed = True
            if fail_streak >= 5:
                self._note(t("agent.fail_note"))
                return self._close_window(t("agent.close_fail",
                                            lang=t("agent.in_lang")))
            if rounds >= limite:
                # Limite da ETAPA: se o turno esta PROGREDINDO (chamada distinta que deu
                # certo nesta etapa e nada falhando), prorroga sozinho ate o teto. Sem
                # progresso, fecha como antes. teto 0 = sem parede (projeto/tarefa longa).
                progrediu = fail_streak == 0 and len(ok_sigs) > feitos_antes
                if progrediu and (teto == 0 or limite < teto):
                    novo = (limite + max_rounds if teto == 0
                            else min(limite + max_rounds, teto))
                    if not prorrogou:
                        # A nota sai UMA vez: a tela nao vira contador de ferramentas.
                        self._note(t("agent.extend_note", limite=limite,
                                     extra=novo - limite))
                        prorrogou = True
                    limite = novo
                    feitos_antes = len(ok_sigs)
                else:
                    break
        if rounds >= limite and teto > 0 and limite >= teto:
            # Tarefa NAO terminou: o harness marca a entrega como PARCIAL (cabecalho na
            # frente do texto, montado aqui - instrucao a modelo pequeno nao garante
            # aviso) e a conversa fica salva para o 'continue' seguir de onde parou.
            self._note(t("agent.max_note", limite=limite))
            return self._close_window(
                t("agent.close_teto", limite=limite, lang=t("agent.in_lang")),
                marca=t("agent.partial_banner", limite=limite))
        # Estourou o limite de rodadas: fecha a janela pedindo resposta com o que tem.
        self._note(t("agent.round_note"))
        return self._close_window(t("agent.close_round", lang=t("agent.in_lang")))

    # ----- janela final -------------------------------------------------------
    def _close_window(self, note: str, marca: str | None = None) -> str:
        self.messages.append({"role": "user", "content": note})
        indice_nota = len(self.messages) - 1
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
        if marca:
            # Fechamento com a tarefa EM ANDAMENTO: o aviso e do HARNESS (linha na tela
            # + primeira linha do texto guardado), nao do modelo. Assim um relatorio
            # pela metade nunca sai com cara de entrega concluida.
            self._note(marca)
            final = {**final, "content": marca + "\n\n" + str(final.get("content") or "")}
        self.messages.append(final)
        # A nota de fechamento e instrucao de GESTAO do turno, nao fala do usuario: sai
        # do historico depois de usada (antes ela ficava e puxava o turno seguinte para
        # "encerrar o assunto"). A compactacao pode ter reescrito a lista: confere antes.
        if (indice_nota < len(self.messages)
                and self.messages[indice_nota].get("role") == "user"
                and self.messages[indice_nota].get("content") == note):
            del self.messages[indice_nota]
        self._save_session()
        return final.get("content", "")

    def _aviso_orcamento(self, usadas: int, teto: int) -> None:
        """Aviso ao MODELO em % do teto do turno (padrao copiado do Hermes).

        O Hermes injeta `budget_warning_ratio` no ultimo resultado de ferramenta uma
        unica vez: "checkpoint the progress now, then continue; do not stop solely
        because of this warning". Aqui o mesmo: o modelo anota o progresso e segue, em
        vez de ser surpreendido pelo teto e entregar o trabalho pela metade.
        """
        if self._aviso_teto_dado or teto <= 0:
            return
        try:
            ratio = float(self.cfg.get("tool_warning_ratio", 0.8))
        except (TypeError, ValueError):
            return
        if not 0 < ratio < 1:
            return
        if usadas < min(ratio * teto, teto - 1):
            return
        ultimo = self.messages[-1] if self.messages else None
        if not isinstance(ultimo, dict) or ultimo.get("role") != "tool":
            return
        ultimo["content"] = (str(ultimo.get("content") or "") + "\n\n"
                             + t("agent.budget_notice", usadas=usadas, teto=teto))
        self._aviso_teto_dado = True

    def _retry_sem_texto(self, use_stream: bool) -> dict:
        """Segunda tentativa quando o modelo devolve resposta sem texto nenhum.

        Caso real: modelo local com thinking, logo depois de compactar, gasta o
        `max_tokens` inteiro pensando e devolve vazio. O turno fechava sozinho e a
        pessoa tinha de digitar 'continue'. Aqui o pedido vai de novo com pensamento
        'low' (no maximo UMA vez) e o historico NAO ganha mensagem nova.
        """
        self._note(t("agent.retry_empty"))
        llm_cfg = getattr(self.llm, "cfg", None)
        alternativo = dict(llm_cfg) if isinstance(llm_cfg, dict) else None
        if alternativo is not None and isinstance(llm_cfg, dict):
            alternativo["thinking"] = "low"
            self.llm.cfg = alternativo
        try:
            if use_stream and hasattr(self.llm, "chat_stream"):
                return self.llm.chat_stream(
                    self.messages, self.tools.specs,
                    on_text=self.on_text_delta,
                    on_reasoning=self.on_reasoning_delta,
                    should_stop=self.stop_event.is_set,
                )
            return self.llm.chat(self.messages, self.tools.specs)
        except ContextOverflowError:
            return {}
        except LLMError:
            return {}
        except Exception:  # noqa: BLE001 - a segunda tentativa NAO pode derrubar o turno
            return {}
        finally:
            if alternativo is not None and isinstance(llm_cfg, dict):
                self.llm.cfg = llm_cfg

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
        budget = int(self.cfg.get("context_budget_chars", 250000))
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
        for pedaco in pending:
            self.messages.append({
                "role": "user",
                "content": t("agent.steer_wrap", texto=pedaco),
            })
        if pending:
            self._note(t("agent.steer_note", n=len(pending)))
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

    # ----- compactacao --------------------------------------------------------
    # O que cada mensagem antiga leva para o resumo. 500 cortava no meio o resultado
    # de ferramenta (pagina, laudo, planilha): o resumo nao via o dado e o modelo
    # completava o buraco depois.
    RESUMO_POR_MENSAGEM = 4000
    # Quanto do orcamento o bloco de dados LITERAIS pode ocupar depois do resumo.
    FRACAO_DADOS = 0.25
    MAX_DADOS_CHARS = 40000

    def _guardar_pre_compactacao(self) -> None:
        """Copia a conversa ANTES de resumir (uma vez por compactacao).

        O session.json e sobrescrito pela compactacao; sem esta copia o 'continue'
        nao tinha de onde voltar e o modelo reconstruia de memoria.
        """
        try:
            alvo = SESSION_FILE.with_name("session.pre-compact.json")
            alvo.write_text(
                json.dumps([self._sem_imagem(m) for m in self.messages[1:]],
                           ensure_ascii=False),
                encoding="utf-8")
        except OSError:
            pass

    def _dados_verbatim(self, head: list) -> str:
        """Trechos LITERAIS dos resultados de ferramenta que saem da conversa.

        O resumo do modelo perde numero/medida mesmo quando bem instruido. Este bloco
        e montado pelo codigo (sem modelo), do mais RECENTE para o mais antigo, para o
        que estava em uso continuar visivel depois de compactar.
        """
        budget = int(self.cfg.get("context_budget_chars", 250000))
        teto = min(int(budget * self.FRACAO_DADOS), self.MAX_DADOS_CHARS)
        partes: list[str] = []
        total = 0
        cortados = 0
        anteriores = ""
        # Compactacao em cima de compactacao: o bloco de dados do resumo anterior volta
        # LITERAL (era exatamente ele que o "resumo do resumo" apagava).
        for mensagem in head:
            if mensagem.get("role") != "system":
                continue
            texto = self._texto_de(mensagem)
            marca = t("agent.data_header")
            if marca not in texto:
                continue
            pedaco = texto.split(marca, 1)[1]
            pedaco = pedaco.split(t("agent.summary_guard"), 1)[0].strip()
            if pedaco:
                anteriores = pedaco[: min(teto, 20000)]
                total += len(anteriores)
            break
        for mensagem in reversed(head):
            if mensagem.get("role") != "tool":
                continue
            texto = self._texto_de(mensagem).strip()
            if not texto:
                continue
            pedaco = (texto if len(texto) <= 2000
                      else texto[:1400] + "\n[...]\n" + texto[-600:])
            if total + len(pedaco) > teto:
                cortados += 1
                continue
            partes.append(pedaco)
            total += len(pedaco)
        if not partes and not anteriores:
            return ""
        partes.reverse()   # volta para a ordem em que foi coletado
        corpo = "\n---\n".join(partes)
        if anteriores:
            corpo = anteriores + ("\n---\n" + corpo if corpo else "")
        if cortados:
            corpo += "\n" + t("agent.data_cut", n=cortados)
        return corpo

    def _compress_once(self) -> bool:
        """Uma rodada de compactacao: o comeco da conversa vira resumo + dados.

        Uma chamada ao modelo no maximo (o resumo). O que nao couber e resolvido
        cortando resultado de ferramenta velho (_descartar_troca_antiga), nunca
        resumindo o resumo - resumo de resumo perde mais e custa outra espera.
        """
        if len(self.messages) <= 3:
            return False
        # Conversa curta com resultado gigante (poucas mensagens e ja acima do
        # orcamento): a cauda encolhe em vez de recusar a compactacao.
        keep_tail = min(8, max(2, len(self.messages) - 2))
        head, tail = self.messages[1:-keep_tail], self.messages[-keep_tail:]
        # Ferramenta no comeco da cauda perde o par 'assistant' quando este e
        # cortado; servidores rejeitam a mensagem orfa: ela vai para o resumo.
        while tail and tail[0].get("role") == "tool":
            head.append(tail.pop(0))
        if not head:
            return False
        self._guardar_pre_compactacao()
        transcript = "\n".join(
            f"{m.get('role')}: {self._texto_de(m)[:self.RESUMO_POR_MENSAGEM]}"
            for m in head
        )
        self._note(t("agent.compacting"))
        summary = self.llm.summarize(transcript)
        corpo = summary or t("agent.summary_fallback")
        dados = self._dados_verbatim(head)
        if dados:
            corpo += "\n\n" + t("agent.data_header") + "\n" + dados
        self.messages = [self.messages[0]] + [
            {"role": "system",
             "content": t("agent.summary_header") + corpo + "\n\n"
                        + t("agent.summary_guard")}
        ] + tail
        self._save_session()
        return True

    def _descartar_troca_antiga(self, manter: int = 2) -> bool:
        """Tira a troca de ferramenta MAIS ANTIGA (assistant + resultados).

        Usado quando o resumo nao baixou o suficiente. Mantem as ultimas trocas
        (`manter`), que sao as que o turno esta usando agora.
        """
        trocas = [i for i, m in enumerate(self.messages)
                  if m.get("role") == "assistant" and m.get("tool_calls")]
        if len(trocas) <= manter:
            return False
        inicio = trocas[0]
        fim = inicio + 1
        while fim < len(self.messages) and self.messages[fim].get("role") == "tool":
            fim += 1
        del self.messages[inicio:fim]
        return True

    def _compress_if_needed(self) -> bool:
        """Compacta ANTES de esbarrar no teto: comeca no % configurado (85%)."""
        if self._compactacao_travada:
            # Ja compactou e nao baixou (a cauda sozinha passa do limiar): repetir e
            # uma chamada de modelo por rodada sem ganho nenhum. A barra do rodape
            # mostra o numero real; se o servidor recusar, _force_compress age.
            return False
        budget = int(self.cfg.get("context_budget_chars", 250000))
        threshold = int(budget * self._compress_pct() / 100)
        if self._estimate_chars() <= threshold:
            return False
        did = self._compress_once()
        if not did:
            return False
        for _ in range(6):
            if self._estimate_chars() <= threshold:
                break
            if not self._descartar_troca_antiga():
                break
            did = True
        if self._estimate_chars() > threshold:
            self._compactacao_travada = True
            self._note(t("agent.ctx_stuck", ctx=i18n.cmd("ctx"), new=i18n.cmd("new")))
        return did

    def _abrir_espaco_para_imagem(self, pct: float = 0.55) -> bool:
        """Compacta ANTES de mandar foto quando a conversa ja encheu o contexto.

        Caso real medido (17/11): conversa com 150+ mensagens e uma foto. A foto foi
        enviada (o session.json guarda o marcador), mas o servidor local cortou a
        imagem para caber no contexto e o modelo respondeu "nao chegou imagem".
        Com 55% do orcamento livre a foto (que consome muitos tokens) cabe.
        """
        budget = int(self.cfg.get("context_budget_chars", 250000))
        if self._estimate_chars() <= int(budget * pct):
            return False
        did = self._force_compress(pct)
        if did:
            self.last_compressed = True
            self._note(t("agent.compressed_for_image"))
        return did

    def _force_compress(self, pct: float = 0.70) -> bool:
        """Compactacao depois que o servidor ja recusou: baixa ate pct do orcamento."""
        budget = int(self.cfg.get("context_budget_chars", 250000))
        target = int(budget * pct)
        if self._estimate_chars() <= target:
            return False
        did = self._compress_once()
        for _ in range(8):
            if self._estimate_chars() <= target:
                break
            if not self._descartar_troca_antiga():
                break
            did = True
        return did

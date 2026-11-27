"""Tela do TEO no navegador: a mesma cabeca, uma segunda tampa.

O coracao (chat_core.py, agent.py, tools/) NAO muda e nao sabe que esta tela
existe. Ele ja recebe a tela pelo construtor:

    self.gate = Gate(cfg, sink.ask_approval)          # bgh/chat_core.py:377
    self.agent = Agent(cfg, self.llm, self.gate, on_event=sink.tool_event)

Entao aqui so existe o que a tela do terminal tambem tem: um objeto com os
mesmos metodos (line, thinking, answer, tool_event, ask_approval...) que
transforma cada chamada em um evento para o navegador.

Tres decisoes que sustentam este arquivo:

1. SEM DEPENDENCIA NOVA. Servidor HTTP da biblioteca padrao
   (ThreadingHTTPServer) e SSE (Server-Sent Events) para o servidor falar com
   a pagina. WebSocket nao existe na stdlib e uma dependencia nova teria que
   ser instalada nos tres sistemas - o wheel e instalado com --no-deps a partir
   do requirements proprio, e o app nao pode quebrar isso.

2. A LICENCA CONTINUA SENDO A PAREDE. Toda ferramenta de risco passa pelo
   Gate de sempre; o modal do navegador so transporta os mesmos quatro codigos
   ("o"/"s"/"a"/"d"). Se ninguem responder (aba fechada, computador desligado),
   o padrao e NEGAR, igual ao Enter-sozinho do terminal.

3. O TEO EXECUTA COMANDO NESTA MAQUINA. Uma tela que escuta em porta e um
   agente com shell e execucao remota de codigo se ninguem cuidar disso. Daí:
   bind so em 127.0.0.1 por padrao, token sorteado por execucao, cookie
   HttpOnly em vez de token na URL, Host conferido (DNS rebinding), Origin
   conferido nos POST, nenhum CORS, CSP fechada. O modo --rede e explicito,
   confirmado no terminal e avisado na tela o tempo todo.

Ciclo de vida (diferente do terminal): no terminal, fechar a janela mata o
processo. Aqui a aba e descartavel - o processo e o servidor. Por isso:

- /sair no meio do turno emite "encerrando" e fecha a porta DEPOIS que a
  resposta chegou na tela (senao a pessoa ve "conexao caiu" em vez de "saiu");
- sem nenhum cliente conectado por MORRER_SEM_CLIENTE_S, o servidor morre
  sozinho (senao cada abertura deixa um processo esquecido escutando).
"""

from __future__ import annotations

import json
import os
import queue
import secrets
import shutil
import socket
import sys
import tempfile
import threading
import time
import webbrowser
from collections import deque
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FuturoTimeout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from . import __version__, i18n, tela
from . import anexos as anexos_mod
from .chat_core import ChatCore, build_approval_options, ctx_parts, log_error
from .i18n import t

# --- tempos (segundos) ------------------------------------------------------
# Quanto o agente espera uma licenca antes de negar sozinho. Generoso: o
# publico do TEO le devagar e as vezes levanta da cadeira.
ESPERA_LICENCA_S = 180
# Cliente caiu no meio de uma pergunta: nao faz sentido segurar o agente 3 min.
AUSENTE_NEGA_S = 45
# Ninguem voltou para a tela: o processo morre (aba esquecida nao deixa shell aberto).
MORRER_SEM_CLIENTE_S = 900
PING_S = 15

COOKIE = "teo_app"
BUFFER_EVENTOS = 4000
CORPO_MAX = 1_000_000
# Quantas linhas ditas antes da pergunta viajam DENTRO do cartao (o cartao cobre
# o historico). 14 cobre a lista de provedores + os avisos do assistente sem
# transformar o cartao numa parede de texto.
CONTEXTO_PERGUNTA = 14

# Anexo (clipe da tela) tem corpo BINARIO e limite proprio: CORPO_MAX acima e do
# JSON curto do turno. Base64 no JSON incharia 33% e estouraria o teto.
ANEXO_MAX = anexos_mod.MAX_BYTES

ASSETS = Path(__file__).resolve().parent / "assets"
TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}
# Arquivos da tela que podem ser servidos sem token: sao estaticos e nao dizem
# nada sobre a conversa nem sobre as ferramentas. O HTML continua exigindo.
ASSET_ROTAS = {
    "/app.css": "app.css",
    "/app.js": "app.js",
    "/teo.svg": "teo.svg",
    "/teo.png": "teo.png",
    "/favicon.ico": "teo.ico",
}

# --- documentos citados na resposta (link clicavel) -------------------------
# A tela do TEO roda em 127.0.0.1 com um token: um endereco que serve QUALQUER
# arquivo do computador nao pode existir aqui. Por isso: lista FECHADA de tipos
# e so arquivo dentro das pastas da pessoa.
# HTML ENTRA (v0.2.36) porque o TEO escreve cartilha/relatorio em .html e o dono
# quer clicar e abrir. Quem protege e o cabecalho `Content-Security-Policy:
# sandbox` que TODO documento servido leva (_arquivo): a pagina abre em origem
# opaca - sem script, sem formulario, sem cookie da sessao, sem tocar no TEO.
# SVG e JS continuam FORA: SVG pode carregar script e JS nunca e documento.
DOC_TIPOS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".log": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".tsv": "text/tab-separated-values; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": ("application/vnd.openxmlformats-officedocument."
              "presentationml.presentation"),
    ".ppt": "application/vnd.ms-powerpoint",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".rtf": "application/rtf",
    ".epub": "application/epub+zip",
    ".zip": "application/zip",
}
# Teto de tamanho do documento servido (acima disso o aviso manda abrir pela pasta).
DOC_MAX = 200 * 1024 * 1024
# Chaves de bgh/i18n.py que o JavaScript usa (o catalogo inteiro nao vai junto).
CHAVES_APP = (
    "app.enviar", "app.parar", "app.placeholder", "app.dica", "app.trabalhando",
    "app.abrir_arquivo",
    "app.anexar", "app.anexar_dica", "app.anexo_remover", "app.anexo_falhou",
    "app.anexo_grande", "app.anexo_limite", "app.anexos", "app.anexo_so",
    "app.anexo_subindo",
    "app.trabalhando_curto",
    "app.ligando", "app.caiu", "app.pensamento", "app.ferramentas", "app.contexto",
    "app.licenca_titulo", "app.licenca_dica", "app.sem_resposta", "app.encerrando",
    "app.erro", "app.modo_rede", "app.vazio", "app.voce", "app.passo",
    "app.escreva_aqui", "app.fechar", "app.modelo", "app.sessao",
    "app.ver_rascunho", "app.esconder", "app.sair_confirmar", "app.nada_feito",
    "app.sair_ok",
    "app.ajuda", "app.opcoes", "app.fechar_menu",
    "app.terminal", "app.terminal.aviso", "app.abrindo_terminal",
)


# Ajuda da tela do navegador: so o que existe AQUI, em secoes curtas. O manual
# do terminal fala de teclas (Ctrl+J, Alt+Enter, "voce>") que no navegador nao
# existem; o /ajuda do modo terminal continua mostrando o manual completo.
HELP_APP = (
    ("sec", "dia"),
    ("item", "escrever"),
    ("item", "anexar"),
    ("item", "parar"),
    ("item", "novo"),
    ("item", "sessoes"),
    ("item", "buscar"),
    ("item", "exportar"),
    ("sec", "ajustes"),
    ("item", "modelo"),
    ("item", "provedor"),
    ("item", "reserva"),
    ("item", "handoff"),
    ("item", "configurar"),
    ("item", "lingua"),
    ("item", "fundo"),
    ("item", "ctx"),
    ("item", "teto"),
    ("item", "pensamento"),
    ("sec", "quando"),
    ("item", "skills"),
    ("item", "zoom"),
    ("item", "site"),
    ("item", "doctor"),
    ("item", "atualizar"),
    ("item", "limpar"),
    ("item", "sobre"),
    ("sec", "tela"),
    ("item", "terminal"),
    ("item", "sair"),
    ("sec", "terminal"),
    ("item", "so_terminal"),
)


def ajuda_do_app() -> list[list[str]]:
    """Linhas [coluna 1, coluna 2] ja no idioma da tela.

    Secao vem com a segunda coluna vazia: a tela desenha como cabecalho.
    """
    saida: list[list[str]] = []
    for tipo, chave in HELP_APP:
        if tipo == "sec":
            saida.append([t("app.help.secao." + chave), ""])
        else:
            saida.append([t("app.cmd." + chave), t("app.help." + chave)])
    return saida


# ---------------------------------------------------------------------------
# Canal de eventos: o TUI repinta a janela; aqui existe uma fila por cliente.
# ---------------------------------------------------------------------------
class Canal:
    """Ponte entre as threads do agente e as conexoes SSE abertas.

    Guarda um buffer dos eventos recentes para o caso de a pagina recarregar no
    meio de um turno: o cliente volta pedindo os eventos depois do ultimo que
    ja viu (Last-Event-ID) e a tela se refaz sozinha.
    """

    def __init__(self, limite: int = BUFFER_EVENTOS):
        self._lock = threading.Lock()
        self._seq = 0
        self._buffer: deque = deque(maxlen=limite)
        self._filas: set[queue.Queue] = set()
        self.ultimo_cliente = 0.0
        self.teve_cliente = False

    def emitir(self, tipo: str, **dados):
        with self._lock:
            self._seq += 1
            evento = {"seq": self._seq, "tipo": tipo}
            evento.update(dados)
            self._buffer.append(evento)
            for fila in list(self._filas):
                fila.put(evento)
        return evento

    def assinar(self, desde: int = 0) -> queue.Queue:
        fila: queue.Queue = queue.Queue()
        with self._lock:
            # desde=-1: cliente novo sem historico (nao quer replay nenhum).
            # desde=0: quer tudo o que existe no buffer (primeira abertura).
            if desde >= 0:
                for evento in self._buffer:
                    if evento["seq"] > desde:
                        fila.put(evento)
            self._filas.add(fila)
            self.teve_cliente = True
            self.ultimo_cliente = time.time()
        return fila

    def desassinar(self, fila: queue.Queue) -> None:
        with self._lock:
            self._filas.discard(fila)
            self.ultimo_cliente = time.time()

    @property
    def clientes(self) -> int:
        with self._lock:
            return len(self._filas)


# ---------------------------------------------------------------------------
# A "tampa": os mesmos metodos do TuiSink, saindo como evento para o navegador.
# ---------------------------------------------------------------------------
class AppSink:
    """Implementa o contrato de tela que o chat_core chama (ver ConsoleSink).

    Nada aqui decide comportamento do agente: so desenha. Quem pergunta,
    aprova e nega continua sendo o Gate (bgh/approvals.py).
    """

    # O menu numerado de pastas do terminal nao existe aqui: com False o core
    # cai na listagem em texto, que ja funciona e nao precisa de codigo novo.
    menu_arquivos = False
    # Tabela aqui e desenhada em HTML pelo app.js (montarTabela). Se o core
    # convertesse a tabela em caixa ASCII antes de mandar, a pagina receberia
    # linhas com "|" e "----" e remontaria a tabela em cima da caixa.
    tabela_ascii = False
    # Esta tela ENTENDE o /zoom (o terminal nao: la o tamanho da letra e /fonte).
    tela_navegador = True

    def __init__(self, app: "App"):
        self.app = app
        self.cfg = app.cfg
        self.canal = app.canal
        # callbacks que o chat_core troca ao vivo (mesmos nomes do TuiSink)
        self.tema_fn = None
        self.preencher_fn = None
        self.bipar_fn = None
        # Linhas ditas desde que o assistente do /configurar comecou. O cartao
        # de pergunta cobre o historico, entao as explicacoes que o terminal
        # imprime acima da pergunta (a lista de provedores, o valor padrao)
        # chegavam invisiveis: a pessoa via so "Opcao" e o campo vazio
        # (reclamacao do dono, 21/11). Estas linhas vao DENTRO do cartao.
        self._contexto: list[str] = []

    # ----- texto no historico ------------------------------------------------
    def line(self, text: str, style: str | None = None) -> None:
        self.canal.emitir("linha", texto=str(text), estilo=style or "")
        # Regua/separador nao e explicacao: fica no historico, nao no cartao.
        if str(text).strip().strip("-").strip():
            self._contexto.append(str(text))
            del self._contexto[:-CONTEXTO_PERGUNTA]

    def contexto_novo(self) -> None:
        """Zera o texto que acompanha a proxima pergunta (/configurar chama)."""
        self._contexto.clear()

    def parts(self, segments: list) -> None:
        self.canal.emitir("partes",
                          partes=[[str(txt), sty or ""] for txt, sty in segments])

    def sep(self, title: str | None = None) -> None:
        self.canal.emitir("sep", titulo=str(title) if title else "")

    def border(self) -> None:
        self.canal.emitir("borda")

    def thinking(self, text: str) -> None:
        # Streaming: o navegador vai colando os pedacos no cartao de rascunho.
        self.canal.emitir("delta", canal="pensamento", texto=str(text))

    def answer(self, text: str) -> None:
        self.canal.emitir("delta", canal="resposta", texto=str(text))

    def tool_event(self, name: str, preview: str) -> None:
        self.canal.emitir("ferramenta", nome=str(name), preview=str(preview),
                          quando=time.time())

    def status(self, text: str) -> None:
        self.canal.emitir("status", texto=str(text))

    # ----- opcionais (o core pergunta hasattr antes de chamar) ---------------
    def on_usage(self, uso) -> None:
        self.canal.emitir("uso", uso=dict(uso) if uso else None)

    def rodada_nova(self) -> None:
        self.canal.emitir("rodada")

    def set_ctx(self, text: str, pct: int | None = None, hot_pct: int | None = None,
                extra: str = "") -> None:
        self.canal.emitir("ctx", texto=str(text), pct=pct, hot=hot_pct,
                          extra=str(extra or ""))

    def modelo_agora(self, modelo: str, base_url: str) -> None:
        """Troca de modelo/provedor: a linha de cima da tela mostra o modelo e
        ficava com o nome antigo ate a pessoa recarregar a pagina."""
        self.canal.emitir("modelo", modelo=str(modelo or ""),
                          base_url=str(base_url or ""))

    # ----- aparencia e avisos ------------------------------------------------
    def aplicar_tema(self) -> None:
        if self.tema_fn is not None:
            try:
                self.tema_fn()
            except Exception:  # noqa: BLE001 - repintar nunca derruba a conversa
                pass
        self.canal.emitir("tema", cores=tela.paleta(tela.cor(self.cfg)))

    def preencher(self, texto: str) -> None:
        if self.preencher_fn is not None:
            try:
                self.preencher_fn(str(texto))
            except Exception:  # noqa: BLE001
                pass
        self.canal.emitir("preencher", texto=str(texto))

    def bipar(self) -> None:
        if self.bipar_fn is not None:
            try:
                self.bipar_fn()
            except Exception:  # noqa: BLE001
                pass
        self.canal.emitir("bip")

    # ----- perguntas ---------------------------------------------------------
    def read_prompt(self) -> str:
        """O app nao tem esse laco: quem manda o turno e o POST /api/turno.

        Levantar EOFError e o mesmo que o fim de entrada faz no terminal (o
        cli.chat trata como saida), entao um chamador antigo nao fica girando.
        """
        raise EOFError

    def ask_line(self, prompt: str, default: str = "", secret: bool = False) -> str:
        """Pergunta de texto livre (assistente do /configurar) no cartao.

        O que o assistente explicou DESDE a pergunta anterior (a lista de
        provedores, o aviso de orcamento) vai junto no corpo do cartao: no
        navegador o cartao cobre o historico e a pessoa ficava so com "Opcao" e
        um campo vazio. O valor padrao aparece como dica DENTRO do campo
        (Enter devolve o padrao, igual ao Enter do terminal).
        """
        titulo_setup = t("setup.title")
        detalhe = "\n".join(
            ln for ln in self._contexto
            if ln.strip() and ln.strip() != titulo_setup
        )
        self._contexto.clear()      # a proxima pergunta leva so o que vier depois
        resposta = self._perguntar(
            {"modo": "texto", "titulo": titulo_setup, "label": str(prompt),
             "detalhe": detalhe, "secret": bool(secret), "valor": str(default),
             "placeholder": "" if secret else str(default)},
            default=str(default),
        )
        # Enter/campo vazio = valor padrao, como na janela de comando.
        return str(resposta).strip() or str(default)

    def ask_approval(self, label: str, detail: str, allow_always: bool) -> str:
        opcoes, codigos = build_approval_options(allow_always)
        tons = {"o": "bom", "s": "bom", "a": "cuidado", "d": "nao"}
        return self._perguntar(
            {"modo": "opcoes", "titulo": t("app.licenca_titulo"), "label": str(label),
             "detalhe": str(detail or "")[:1500],
             "opcoes": [{"texto": txt, "codigo": cod, "tom": tons.get(cod, "")}
                        for txt, cod in zip(opcoes, codigos)]},
            default="d",          # igual ao Enter sozinho do terminal: nega
        )

    def ask_choice(self, title: str, label: str, options: list) -> str:
        # Sem resposta no app a escolha e NENHUMA (""), e nao a primeira da lista
        # como no terminal: num menu de "apagar rascunhos?" a primeira opcao e
        # "sim", e negar por omissao e o padrao seguro. O core entende "".
        return self._perguntar(
            {"modo": "opcoes", "titulo": str(title), "label": str(label), "detalhe": "",
             "opcoes": [{"texto": str(o), "codigo": str(o), "tom": ""} for o in options]},
            default="",
        )

    def _perguntar(self, dados: dict, default: str) -> str:
        pedido = self.app.abrir_pergunta(dados, default)
        try:
            return pedido["future"].result(timeout=ESPERA_LICENCA_S)
        except FuturoTimeout:
            self.app.fechar_pergunta(pedido["id"], default)
            self.canal.emitir("linha", texto=t("app.sem_resposta"), estilo="yellow")
            return default


# ---------------------------------------------------------------------------
# O app: dono do canal, do sink, do core e do servidor.
# ---------------------------------------------------------------------------
class App:
    def __init__(self, cfg: dict, rede: bool = False, token: str | None = None):
        self.cfg = cfg
        self.rede = bool(rede)
        self.token = token or secrets.token_urlsafe(24)
        self.canal = Canal()
        self.sink = AppSink(self)
        self.core: ChatCore | None = None
        self.servidor: ThreadingHTTPServer | None = None
        self.porta = 0
        self.hosts = _hosts_locais()
        self._lock_busy = threading.Lock()
        self.busy = False
        self.fechado = False
        self._lock_ped = threading.Lock()
        self._pedidos: dict[int, dict] = {}
        self._pid = 0
        self._fim = threading.Event()
        self.inicio = time.time()
        self.motivo = ""
        # Anexos recebidos pela tela nesta sessao: id -> {nome, caminho, tipo,
        # tamanho}. Vive na memoria (a pagina so manda o id no turno) e os
        # arquivos vao para BGH_HOME/anexos, apagados no fim da sessao.
        self.anexos: dict[str, dict] = {}
        self._lock_anexos = threading.Lock()
        # Quando o cliente falou com o servidor pela ultima vez. E isto que
        # distingue "a pessoa esta olhando a tela" de "a aba foi fechada":
        # detectar queda de socket TCP nao e confiavel (FIN/RST podem demorar
        # minutos atras de proxy), entao a pagina manda um sinal de vida curto.
        self.ultimo_contato = time.time()

    def tocar(self) -> None:
        """Marca que o cliente esta vivo (qualquer requisicao autenticada)."""
        self.ultimo_contato = time.time()

    # ----- perguntas (o navegador responde por POST) -------------------------
    def abrir_pergunta(self, dados: dict, default: str) -> dict:
        with self._lock_ped:
            self._pid += 1
            pedido = {"id": self._pid, "future": Future(), "default": default}
            self._pedidos[pedido["id"]] = pedido
        self.canal.emitir("pergunta", id=pedido["id"], **dados)
        return pedido

    def fechar_pergunta(self, pid: int, valor: str) -> None:
        with self._lock_ped:
            self._pedidos.pop(pid, None)
        self.canal.emitir("pergunta_fechada", id=pid)

    def responder(self, pid: int, valor: str) -> bool:
        with self._lock_ped:
            pedido = self._pedidos.pop(pid, None)
        if pedido is None:
            return False
        if not pedido["future"].done():
            pedido["future"].set_result(str(valor))
        self.canal.emitir("pergunta_fechada", id=pid)
        return True

    def _negar_pendentes(self, motivo: str) -> None:
        with self._lock_ped:
            pendentes = list(self._pedidos.values())
        for pedido in pendentes:
            self.responder(pedido["id"], pedido["default"])
        if pendentes:
            self.canal.emitir("linha", texto=motivo, estilo="yellow")

    # ----- anexos (clipe da tela) --------------------------------------------
    def guardar_anexo(self, nome: str, dados: bytes) -> tuple[int, dict]:
        """Guarda um anexo recebido e devolve (codigo HTTP, corpo JSON)."""
        with self._lock_anexos:
            if len(self.anexos) >= anexos_mod.MAX_ANEXOS:
                return 400, {"erro": t("anexo.limite", n=anexos_mod.MAX_ANEXOS)}
            ident, caminho, erro = anexos_mod.salvar(nome, dados)
            if erro or caminho is None:
                return 400, {"erro": erro or t("anexo.falhou", nome=nome)}
            limpo = anexos_mod.nome_seguro(nome)
            self.anexos[ident] = {
                "nome": limpo,
                "caminho": str(caminho),
                "tipo": anexos_mod.classificar(caminho),
                "tamanho": len(dados),
            }
            return 200, {"ok": True, "id": ident, "nome": limpo,
                         "tipo": self.anexos[ident]["tipo"],
                         "tamanho": len(dados)}

    def resolver_anexos(self, ids) -> tuple[list[str], bool]:
        """Ids da pagina -> caminhos no disco. (caminhos, algum_perdido)."""
        caminhos: list[str] = []
        perdido = False
        with self._lock_anexos:
            for ident in ids or []:
                meta = self.anexos.get(str(ident))
                if meta is None or not Path(meta["caminho"]).is_file():
                    perdido = True
                    continue
                if meta["caminho"] not in caminhos:
                    caminhos.append(meta["caminho"])
        return caminhos, perdido

    def limpar_anexos(self) -> int:
        """Apaga os anexos desta sessao (o arquivo do usuario nao fica para tras)."""
        with self._lock_anexos:
            metas = list(self.anexos.values())
            self.anexos.clear()
        removidos = 0
        for meta in metas:
            try:
                Path(meta["caminho"]).unlink()
                removidos += 1
            except OSError:
                continue
        return removidos

    # ----- o turno -----------------------------------------------------------
    def turno(self, texto: str, anexos_ids=None) -> None:
        texto = (texto or "").strip()
        core = self.core
        caminhos: list[str] = []
        if anexos_ids:
            caminhos, perdido = self.resolver_anexos(anexos_ids)
            if perdido:
                self.canal.emitir("linha", texto=t("anexo.perdido"), estilo="yellow")
        if not texto and not caminhos:
            return
        if core is None:
            return
        if anexos_ids and not caminhos:
            # O anexo foi escolhido, mas nao esta mais aqui (outra janela, sessao
            # reiniciada). Chamar o modelo so com o texto faria ele responder "nao
            # recebi imagem" - confuso e falso. Melhor parar e pedir de novo.
            self.canal.emitir("linha", texto=t("anexo.perdido"), estilo="yellow")
            return
        ocupado = self.pegar_busy()
        if not ocupado:
            # Aviso no meio do turno: mesmo caminho do terminal (core.steer).
            # Anexo NAO entra agora: o turno em curso ja foi montado; o arquivo
            # esperaria calado, entao a tela diz a verdade.
            if caminhos:
                self.canal.emitir("linha", texto=t("anexo.ocupado"), estilo="yellow")
            if texto:
                core.steer(texto)
                self.canal.emitir("linha", texto=t("tui.steer_hint"), estilo="dim")
            return
        self.canal.emitir("estado", ocupado=True)

        def _roda():
            resultado = "continue"
            try:
                if caminhos:
                    resultado = core.submit(texto, anexos=caminhos)
                else:
                    resultado = core.submit(texto)
            except Exception as exc:  # noqa: BLE001 - turno nunca derruba o servidor
                log_error(exc, "turno no app")
                self.canal.emitir("linha",
                                  texto=t("app.erro", erro=str(exc)[:300]), estilo="red")
            finally:
                self.soltar_busy()
                self.canal.emitir("estado", ocupado=False)
                self.canal.emitir("fim_turno")
            if resultado == "exit":
                self.encerrar("sair")

        threading.Thread(target=_roda, daemon=True).start()

    def pegar_busy(self) -> bool:
        """True se este chamador pegou o turno; False se ja havia um rodando."""
        with self._lock_busy:
            if self.busy:
                return False
            self.busy = True
            return True

    def soltar_busy(self) -> None:
        with self._lock_busy:
            self.busy = False

    def parar(self) -> None:
        """/api/parar: para o modelo E fecha qualquer pergunta pendente (nega)."""
        if self.core is not None:
            self.core.stop()
        self._negar_pendentes(t("app.sem_resposta"))

    # ----- ciclo de vida -----------------------------------------------------
    def subir(self, porta: int = 0) -> None:
        # O titulo de janela e comando de TERMINAL (ESC ]2;...): no app nao ha
        # janela para batizar, e a sequencia sujaria a saida de quem rodou o
        # comando. Trocar a funcao no modulo e mais barato que mudar o core.
        from . import chat_core

        chat_core.set_window_title = lambda *a, **k: None

        i18n.set_lang(self.cfg.get("lang"))
        # Anexos de sessoes antigas (aba fechada sem /sair) nao podem ficar no disco.
        try:
            anexos_mod.limpar(horas=24)
        except OSError:
            pass
        self.core = ChatCore(self.cfg, self.sink)
        self.sink.aplicar_tema()
        self.abertura()
        try:
            self.core.check_update_on_start()
            self.core.aviso_scratch_on_start()
        except Exception as exc:  # noqa: BLE001 - aviso de versao nunca impede o app
            log_error(exc, "aviso de versao no app")

        self.subir_servidor(porta)

    def abertura(self) -> None:
        """Abertura da tela do navegador.

        Nao chama core.banner(): aquela abertura foi desenhada para o terminal,
        com a arte em ASCII e a LISTA DE COMANDOS inteira (que aqui empurraria a
        conversa para fora da tela e fala de teclas que nao existem no navegador).
        A mesma informacao continua a um /ajuda de distancia.
        """
        self.canal.emitir("linha", texto=t("banner.title"), estilo="bold")
        self.canal.emitir("linha", estilo="cyan", texto=t(
            "banner.model",
            model=self.cfg.get("model", ""),
            base_url=self.cfg.get("base_url", ""),
            thinking=self.cfg.get("thinking", "auto"),
        ))
        try:
            from .chat_core import SESSION_FILE

            if SESSION_FILE.exists():
                self.canal.emitir("linha", estilo="dim",
                                  texto=t("banner.resumed", new=i18n.cmd("new")))
        except Exception:  # noqa: BLE001 - aviso e enfeite, nao pode impedir a abertura
            pass

    def subir_servidor(self, porta: int = 0) -> None:
        """Sobe o HTTP + as threads de trabalho. Separado do core para o teste
        offline poder exercitar o transporte sem modelo nem rede."""
        host = "0.0.0.0" if self.rede else "127.0.0.1"
        self.servidor = _Servidor((host, int(porta or 0)), self)
        self.porta = self.servidor.server_address[1]
        threading.Thread(target=self._vigia, daemon=True).start()
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def servir(self) -> None:
        """Segura o processo enquanto o servidor estiver de pe."""
        while not self.fechado:
            time.sleep(0.3)
            if self.servidor is None:
                break

    def encerrar(self, motivo: str = "") -> None:
        """Fecha com a tela sabendo: o evento chega antes de a porta cair.

        CTRL+C apertado de novo DURANTE o encerramento nao pode virar traceback:
        o dono do projeto viu exatamente isso no macOS (tres ^C seguidos). Tudo
        que espera aqui dentro e a prova de KeyboardInterrupt.
        """
        if self.fechado:
            return
        self.fechado = True
        self.motivo = motivo
        try:
            self.canal.emitir("encerrando", motivo=motivo)
        except Exception:  # noqa: BLE001
            pass
        if self.core is not None:
            try:
                self.core.stop()
            except KeyboardInterrupt:
                pass
        try:
            self._negar_pendentes(t("app.sem_resposta"))
        except KeyboardInterrupt:
            pass
        try:
            self.limpar_anexos()
        except OSError:
            pass
        try:
            time.sleep(1.2)   # a resposta do SSE sai antes da porta fechar
        except KeyboardInterrupt:
            pass
        servidor = self.servidor
        if servidor is not None:
            try:
                servidor.shutdown()      # para de aceitar conexao
            except (Exception, KeyboardInterrupt):  # noqa: BLE001 - ja desligado
                pass
            try:
                servidor.server_close()  # fecha o socket: a porta deixa de existir
            except (OSError, KeyboardInterrupt):
                pass
        self._fim.set()

    def esperar_fim(self, timeout: float = 6.0) -> None:
        try:
            self._fim.wait(timeout)
        except KeyboardInterrupt:
            # CTRL+C enquanto esperava o servidor desligar: o app ja esta fechado.
            pass

    def _vigia(self) -> None:
        """Duas mortes por inatividade: pergunta sem ninguem e servidor sem gente."""
        while not self.fechado:
            time.sleep(2.0)
            agora = time.time()
            ausente = agora - self.ultimo_contato
            with self._lock_ped:
                tem_pergunta = bool(self._pedidos)
            # Ausente = a pagina parou de dar sinal de vida (aba fechada,
            # computador suspenso). Tela aberta e parada NAO e ausencia: negar a
            # licenca de quem esta olhando seria negar por padrao. O relogio
            # comeca a contar na abertura do app, entao uma janela esquecida
            # fechada tambem nao fica presa esperando licenca para sempre.
            if tem_pergunta and ausente > AUSENTE_NEGA_S:
                self._negar_pendentes(t("app.sem_resposta"))
            if ausente > MORRER_SEM_CLIENTE_S:
                self.encerrar("sem_cliente")

    # ----- URLs e estado -----------------------------------------------------
    def url(self, interno: bool = False) -> str:
        if interno or not self.rede:
            host = "127.0.0.1"
        else:
            host = ip_lan() or "127.0.0.1"
        return f"http://{host}:{self.porta}/?t={self.token}"

    def estado_json(self) -> dict:
        estado = {
            "ocupado": bool(self.busy),
            "modelo": self.cfg.get("model", ""),
            "base_url": self.cfg.get("base_url", ""),
            "lingua": i18n.get_lang(),
            "versao": __version__,
            "rede": self.rede,
            "cores": tela.paleta(tela.cor(self.cfg)),
            "nome_tema": tela.cor(self.cfg),
            "strings": {chave: t(chave) for chave in CHAVES_APP},
            "dica": t("app.dica", cmd=i18n.cmd("help")),
            "ajuda": ajuda_do_app(),
            # O clipe da tela precisa saber os limites e o accept ANTES de mandar
            # arquivo: o servidor continua sendo quem manda (valida de novo).
            "zoom": zoom_da_tela(self.cfg),
            "anexo": {"max_mb": round(ANEXO_MAX / (1024 * 1024)),
                      "max": anexos_mod.MAX_ANEXOS,
                      "aceita": ",".join(anexos_mod.aceitos())},
        }
        # Medidor de contexto ja na abertura (antes do primeiro turno ele mostra
        # a estimativa do orcamento; sem isso a barra ficava vazia e parecia quebrada).
        try:
            uso = self.core.agent.ctx_usage() if self.core is not None else None
            if uso:
                core_txt, extra = ctx_parts(self.cfg, uso)
                estado["ctx"] = {"texto": core_txt + extra, "pct": uso.get("pct")}
        except Exception:  # noqa: BLE001 - medidor e enfeite: nunca impede a tela
            pass
        return estado


def ip_lan() -> str | None:
    """IP desta maquina na rede local, sem depender de pacote externo."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))     # nao envia nada: so descobre a rota
            return s.getsockname()[0]
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


def zoom_da_tela(cfg: dict):
    """Zoom guardado: numero (75/90/100/110/125) ou "auto" (a tela decide)."""
    valor = cfg.get("zoom_web", 75)
    if isinstance(valor, (int, float)) and valor > 0:
        return int(valor)
    if str(valor).strip().isdigit():
        return int(str(valor).strip())
    return "auto"


def _hosts_locais() -> set[str]:
    """Nomes pelos quais ESTA maquina pode ser chamada (checagem do header Host)."""
    hosts = {"127.0.0.1", "localhost"}
    try:
        hosts.add(socket.gethostname().lower())
    except OSError:
        pass
    lan = ip_lan()
    if lan:
        hosts.add(lan)
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            hosts.add(ip)
    except OSError:
        pass
    return hosts


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
class _Servidor(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 32   # o padrao (5) derruba requisicao em rajada

    def __init__(self, endereco, app: App):
        self.app = app
        super().__init__(endereco, _Handler)


class _Handler(BaseHTTPRequestHandler):
    server_version = "TEO"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # ----- utilidades --------------------------------------------------------
    @property
    def app(self) -> App:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format, *args):  # noqa: A002 - assinatura da stdlib
        return

    def _host_ok(self) -> bool:
        """Header Host tem que ser um nome desta maquina (barra DNS rebinding)."""
        host = (self.headers.get("Host") or "").split(":")[0].strip().lower()
        if not host:
            return False
        if host in self.app.hosts:
            return True
        # modo rede: aceitar IP literal que seja desta maquina
        return self.app.rede and host == (ip_lan() or "")

    def _origin_ok(self) -> bool:
        origem = self.headers.get("Origin")
        if not origem:
            return True      # curl/navegador antigo: a parede e o token
        host = (urlsplit(origem).hostname or "").lower()
        return host in self.app.hosts

    def _token_ok(self) -> bool:
        tok = (self.query.get("t") or [""])[0] or self._cookie()
        return bool(tok) and secrets.compare_digest(str(tok), self.app.token)

    def _cookie(self) -> str:
        bruto = self.headers.get("Cookie") or ""
        for parte in bruto.split(";"):
            nome, _, valor = parte.strip().partition("=")
            if nome == COOKIE:
                return valor
        return ""

    def _cabecalhos(self, tipo: str, tamanho: int | None = None,
                    extra: dict | None = None) -> None:
        self.send_header("Content-Type", tipo)
        if tamanho is not None:
            self.send_header("Content-Length", str(tamanho))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        for chave, valor in (extra or {}).items():
            self.send_header(chave, valor)

    def _json(self, codigo: int, obj, extra: dict | None = None) -> None:
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self._cabecalhos("application/json; charset=utf-8", len(corpo), extra)
        self.end_headers()
        try:
            self.wfile.write(corpo)
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

    def _texto(self, codigo: int, texto: str) -> None:
        corpo = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>TEO</title>"
            "<div style='font:20px/1.6 system-ui,sans-serif;padding:8vh 6vw;"
            "max-width:40em;margin:auto;color:#222'>"
            f"<h1 style='font-size:1.4em'>TEO</h1><p>{_escapar(texto)}</p></div>"
        ).encode("utf-8")
        self.send_response(codigo)
        self._cabecalhos("text/html; charset=utf-8", len(corpo),
                         {"Content-Security-Policy":
                          "default-src 'none'; style-src 'unsafe-inline'"})
        self.end_headers()
        try:
            self.wfile.write(corpo)
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

    # ----- GET ---------------------------------------------------------------
    def do_GET(self) -> None:
        partes = urlsplit(self.path)
        caminho = partes.path
        self.query = parse_qs(partes.query)
        if not self._host_ok():
            return self._texto(421, "endereco nao reconhecido (Host)")
        if caminho in ASSET_ROTAS:
            return self._asset(ASSET_ROTAS[caminho])
        if caminho not in ("/", "/api/inicio", "/api/eventos", "/api/arquivo"):
            return self._texto(404, "nao existe")
        if not self._token_ok():
            return self._texto(401, t("app.sessao"))
        self.app.tocar()
        if caminho == "/api/arquivo":
            return self._arquivo()
        if caminho == "/":
            if (self.query.get("t") or [""])[0]:
                # Token saiu da URL e virou cookie: nao fica no historico/log.
                return self._redirecionar()
            return self._pagina()
        if caminho == "/api/inicio":
            return self._json(200, self.app.estado_json())
        return self._eventos()

    def _redirecionar(self) -> None:
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie",
                         f"{COOKIE}={self.app.token}; Path=/; HttpOnly; SameSite=Strict")
        self.send_header("Content-Length", "0")
        self.end_headers()
        self.close_connection = True

    def _arquivo(self) -> None:
        """Serve um documento citado na resposta, para o clique abrir em outra aba.

        Regras: arquivo comum, de tipo da lista fechada (DOC_TIPOS) e dentro das
        pastas da pessoa (home, pasta do TEO e temporaria). Qualquer outra coisa
        e 404 - a tela escuta em porta e nao pode ser uma janela para o disco
        inteiro.
        """
        bruto = (self.query.get("c") or [""])[0].strip()
        alvo = Path(os.path.expanduser(bruto)) if bruto else None
        try:
            alvo = alvo.resolve(strict=True) if alvo is not None else None
        except (OSError, RuntimeError):
            alvo = None
        tipo = DOC_TIPOS.get(alvo.suffix.lower()) if alvo is not None else None
        if alvo is None or not alvo.is_file() or tipo is None or not _pasta_da_pessoa(alvo):
            return self._texto(404, t("app.arquivo.nao"))
        try:
            tamanho = alvo.stat().st_size
        except OSError:
            return self._texto(404, t("app.arquivo.nao"))
        if tamanho > DOC_MAX:
            return self._texto(413, t("app.arquivo.grande",
                                      mb=str(tamanho // (1024 * 1024))))
        # Checagem rapida (`checar=1`): a tela pergunta se o caminho EXISTE antes
        # de transformar em link. Assim nada de link morto na conversa de uma
        # crianca ou de um idoso - e caminho com ESPACO no nome tambem funciona,
        # porque quem confirma e o disco, nao um palpite do navegador.
        if (self.query.get("checar") or [""])[0] in ("1", "sim", "true"):
            self.send_response(204)
            self._cabecalhos("text/plain; charset=utf-8", 0)
            self.end_headers()
            self.close_connection = True
            return
        nome = alvo.name.replace('"', "").replace("\\", "").replace("\n", " ")
        ascii_nome = nome.encode("ascii", "replace").decode("ascii")
        self.send_response(200)
        self._cabecalhos(tipo, tamanho, {
            "Content-Disposition":
                f'inline; filename="{ascii_nome}"; filename*=UTF-8\'\'{quote(nome)}',
            # Sem scripts, sem acesso a nada: o arquivo e um documento, nao uma pagina.
            "Content-Security-Policy": "sandbox",
        })
        self.end_headers()
        try:
            with open(alvo, "rb") as fonte:
                shutil.copyfileobj(fonte, self.wfile, 256 * 1024)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        self.close_connection = True

    def _asset(self, nome: str) -> None:
        caminho = ASSETS / nome
        try:
            corpo = caminho.read_bytes()
        except OSError:
            return self._texto(404, "arquivo da tela nao encontrado")
        self.send_response(200)
        self._cabecalhos(TIPOS.get(caminho.suffix, "application/octet-stream"),
                         len(corpo))
        self.end_headers()
        try:
            self.wfile.write(corpo)
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

    def _pagina(self) -> None:
        try:
            corpo = (ASSETS / "app.html").read_bytes()
        except OSError:
            return self._texto(500, "arquivo da tela nao encontrado")
        self.send_response(200)
        self._cabecalhos("text/html; charset=utf-8", len(corpo), {
            "Content-Security-Policy":
                "default-src 'none'; style-src 'self'; script-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; base-uri 'none'; "
                "form-action 'none'; frame-ancestors 'none'",
            "Set-Cookie":
                f"{COOKIE}={self.app.token}; Path=/; HttpOnly; SameSite=Strict",
        })
        self.end_headers()
        try:
            self.wfile.write(corpo)
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

    def _eventos(self) -> None:
        """SSE: o servidor fala, a pagina escuta. Reconexao com replay."""
        desde = -1
        ultimo = self.headers.get("Last-Event-ID") or ""
        if ultimo.strip().isdigit():
            desde = int(ultimo.strip())
        elif (self.query.get("desde") or [""])[0].isdigit():
            desde = int((self.query.get("desde") or ["0"])[0])
        fila = self.app.canal.assinar(desde)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        self.close_connection = True
        ultimo_ping = time.time()
        try:
            self.wfile.write(b"retry: 1500\n\n")
            self.wfile.flush()
            # Sem condicao de "app.fechado" aqui: o evento encerrando precisa
            # SAIR por esta conexao antes de a porta cair. Quem fecha o laco e o
            # proprio evento (ou a conexao morrendo no shutdown).
            while True:
                try:
                    evento = fila.get(timeout=1.0)
                except queue.Empty:
                    if time.time() - ultimo_ping >= PING_S:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        ultimo_ping = time.time()
                    continue
                dados = json.dumps(evento, ensure_ascii=False)
                self.wfile.write(f"id: {evento['seq']}\ndata: {dados}\n\n".encode("utf-8"))
                self.wfile.flush()
                ultimo_ping = time.time()
                if evento.get("tipo") == "encerrando":
                    break
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.app.canal.desassinar(fila)

    # ----- POST --------------------------------------------------------------
    def do_POST(self) -> None:
        partes = urlsplit(self.path)
        caminho = partes.path
        self.query = parse_qs(partes.query)
        if not self._host_ok():
            return self._json(421, {"erro": "host"})
        if not self._origin_ok():
            return self._json(403, {"erro": "origem"})
        if not self._token_ok():
            return self._json(401, {"erro": "sessao"})
        self.app.tocar()
        # Anexo vai primeiro: corpo BINARIO e limite proprio (o JSON curto do
        # turno tem outro teto). Ler como JSON aqui daria 400 mudo para a tela.
        if caminho == "/api/anexo":
            return self._receber_anexo()
        # POST sem corpo e legitimo (/api/parar, /api/sair): so le JSON quando
        # o cliente mandou tamanho. Sem isso o botao Parar voltava 400 mudo.
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"erro": "corpo"})
        dados: dict = {}
        if tamanho > 0:
            lido = self._corpo(tamanho)
            if lido is None:
                return self._json(400, {"erro": "corpo"})
            dados = lido
        if caminho == "/api/turno":
            ids = dados.get("anexos")
            self.app.turno(str(dados.get("texto") or ""),
                           anexos_ids=ids if isinstance(ids, list) else None)
            return self._json(202, {"ok": True})
        if caminho == "/api/responder":
            try:
                pid = int(str(dados.get("id") or ""))
            except (TypeError, ValueError):
                return self._json(400, {"erro": "id"})
            ok = self.app.responder(pid, str(dados.get("valor") or ""))
            return self._json(200 if ok else 410, {"ok": ok})
        if caminho == "/api/parar":
            self.app.parar()
            return self._json(200, {"ok": True})
        if caminho == "/api/vivo":
            # Sinal de vida da pagina (a cada 12s): e o que separa "a pessoa
            # esta na frente da tela" de "a aba foi fechada". Vai tambem o idioma
            # atual: se a pessoa trocou no /lingua, a tela se reescreve sozinha.
            return self._json(200, {"ok": True, "ocupado": bool(self.app.busy),
                                    "lingua": i18n.get_lang(),
                                    # /zoom muda ao vivo: a pagina se ajusta no
                                    # proximo sinal de vida (12s), sem recarregar.
                                    "zoom": zoom_da_tela(self.app.cfg)})
        if caminho == "/api/sair":
            self.app.encerrar("sair")
            return self._json(200, {"ok": True})
        if caminho == "/api/terminal":
            # Botao Terminal: fecha esta tela e o cli abre o TEO no terminal.
            self.app.encerrar("terminal")
            return self._json(200, {"ok": True})
        return self._json(404, {"erro": "rota"})

    def _receber_anexo(self) -> None:
        """POST /api/anexo?nome=...: corpo BINARIO do arquivo escolhido no clipe.

        Nao vai em JSON de proposito: base64 incharia 33% e o teto do corpo JSON
        (CORPO_MAX) e de 1 MB - foto de celular nunca passaria. O nome vem na
        query porque o binario tem que ir cru.
        """
        nome = (self.query.get("nome") or [""])[0]
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"erro": t("anexo.falhou", nome=nome or "?")})
        if tamanho <= 0:
            return self._json(400, {"erro": t("anexo.vazio", nome=nome or "?")})
        if tamanho > ANEXO_MAX:
            return self._json(413, {
                "erro": t("anexo.grande", nome=nome or "?",
                          size=f"{tamanho / (1024 * 1024):.1f}".replace(".", ","),
                          max=f"{ANEXO_MAX / (1024 * 1024):.0f}")})
        try:
            dados = self.rfile.read(tamanho)
        except (OSError, ValueError):
            return self._json(400, {"erro": t("anexo.falhou", nome=nome or "?")})
        if len(dados) != tamanho:
            return self._json(400, {"erro": t("anexo.falhou", nome=nome or "?")})
        codigo, corpo = self.app.guardar_anexo(nome, dados)
        return self._json(codigo, corpo)

    def _corpo(self, tamanho: int):
        if tamanho <= 0 or tamanho > CORPO_MAX:
            return None
        bruto = self.rfile.read(tamanho)
        try:
            dados = json.loads(bruto.decode("utf-8", "replace"))
        except (ValueError, UnicodeError):
            return None
        return dados if isinstance(dados, dict) else None


def _pasta_da_pessoa(alvo: Path) -> bool:
    """True se o documento esta numa pasta que a pessoa usa de verdade.

    A tela nunca vira uma janela para o disco inteiro: home, pasta do TEO
    (BGH_HOME) e temporaria. /etc, /usr, a pasta de outro usuario ficam de fora.
    """
    raizes = [Path.home(), Path(tempfile.gettempdir())]
    casa = os.environ.get("BGH_HOME")
    if casa:
        raizes.append(Path(casa))
    for raiz in raizes:
        try:
            alvo.relative_to(raiz.resolve())
            return True
        except (ValueError, OSError):
            continue
    return False


def _escapar(texto: str) -> str:
    return (str(texto).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# Entrada: bgh app
# ---------------------------------------------------------------------------
def rede_efetiva(cfg: dict, flag_rede: bool = False, flag_local: bool = False) -> bool:
    """Abrir para a rede? A flag da linha manda mais que o configurado no menu.

    --local existe para quem quer fechar a rede numa execucao sem mexer no
    config (ex.: testar algo em publico).
    """
    if flag_local:
        return False
    if flag_rede:
        return True
    return bool(cfg.get("rede", False))


def run_app(cfg: dict, rede: bool | None = None, porta: int = 0, abrir: bool = True,
            token: str | None = None, confirmar: bool = True) -> int:
    ligado_agora = bool(rede)          # veio --rede: e pedido desta execucao
    if rede is None:
        rede = bool(cfg.get("rede", False))
    if rede and confirmar and ligado_agora:
        for linha in t("cfg.rede.aviso").splitlines():
            print(f"  {linha}")
        print("")
        if not sys.stdin.isatty():
            print("  Sem terminal interativo: rode sem --rede, ou confirme no terminal.")
            return 2
        resposta = input(f"  {t('cfg.rede.prompt')}").strip().upper()
        if resposta not in ("SIM", "S", "SI", "YES", "Y"):
            print(f"  {t('cfg.rede.cancelou')}")
            return 2

    app = App(cfg, rede=rede, token=token)
    try:
        app.subir(porta=porta)
    except OSError as exc:
        print(t("app.erro", erro=exc))
        return 1

    print("", flush=True)
    print(f"  TEO aberto no navegador: {app.url(interno=True)}", flush=True)
    if rede:
        print(f"  Para quem esta na rede:  {app.url()}", flush=True)
    print(f"  modelo: {cfg.get('model', '')}   versao: {__version__}", flush=True)
    print("  Para fechar: o botao Sair na tela, ou CTRL+C aqui.", flush=True)
    print("", flush=True)
    if abrir:
        try:
            webbrowser.open(app.url(interno=True))
        except Exception:  # noqa: BLE001 - sem navegador padrao: a URL esta na tela
            pass
    try:
        app.servir()
    except KeyboardInterrupt:
        app.encerrar("ctrl+c")
    finally:
        app.esperar_fim()
        if app.servidor is not None:
            try:
                app.servidor.server_close()
            except (OSError, KeyboardInterrupt):
                pass
    print(t("app.encerrando"))
    if app.motivo == "terminal":
        return tela.TROCA_CHAT
    return 0

"""Testes da tela do navegador (offline: sem modelo, sem internet).

Roda: .venv/bin/python tests/test_app.py
Mesmo estilo do test_smoke.py: sem pytest, um 'ok - ...' por verificacao.

O que este arquivo prova, e por que cada coisa importa:

1. ASSINATURA: o AppSink tem os mesmos metodos e as mesmas assinaturas que o
   ConsoleSink (a tampa de referencia). Se o coracao mudar um argumento, o app
   quebra aqui e nao na maquina do cliente.
2. LICENCA: o Gate de verdade (bgh/approvals.py) pede licenca pelo modal, e o
   caminho de "ninguem respondeu" NEGA - nao deixa o agente rodando solto.
3. PORTA: sem token nao entra (401), Host estranho nao entra (421), Origin
   estranho nao entra (403). Um agente com shell nao pode aceitar qualquer aba.
4. TURNO E EVENTOS: o POST /api/turno responde 202 na hora e o resultado chega
   pelo SSE; /api/responder fecha a pergunta pendente.
"""

import http.client
import inspect
import json
import os
import re
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="bgh_app_test_"))
os.environ["BGH_HOME"] = str(TMP)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PASS = 0


def ok(label: str, cond: bool):
    global PASS
    if not cond:
        raise AssertionError(f"FALHOU: {label}")
    PASS += 1
    print(f"ok - {label}")


# ---------- 1. contrato da tela ----------------------------------------------
from bgh.app_servidor import App, AppSink, rede_efetiva
from bgh.chat_core import ConsoleSink
from bgh.cli import _opcao_do_menu, escolher_tela
from bgh.i18n import t
from bgh.tela import eh_troca_para_app
from bgh.tui import TuiSink

COMO_CONSOLE = ("line", "parts", "sep", "border", "thinking", "answer", "tool_event",
                "status", "aplicar_tema", "preencher", "bipar", "read_prompt",
                "ask_line", "ask_approval", "ask_choice")
COMO_TUI = ("set_ctx", "on_usage", "rodada_nova")

for nome in COMO_CONSOLE:
    ref = getattr(ConsoleSink, nome, None)
    novo = getattr(AppSink, nome, None)
    ok(f"AppSink tem {nome}", ref is not None and novo is not None)
    if ref is not None and novo is not None:
        ok(f"assinatura de {nome} igual a do ConsoleSink",
           list(inspect.signature(ref).parameters) == list(inspect.signature(novo).parameters))

for nome in COMO_TUI:
    ref = getattr(TuiSink, nome, None)
    novo = getattr(AppSink, nome, None)
    ok(f"AppSink tem o opcional {nome}", ref is not None and novo is not None)
    if ref is not None and novo is not None:
        ok(f"assinatura de {nome} igual a do TuiSink",
           list(inspect.signature(ref).parameters) == list(inspect.signature(novo).parameters))

ok("menu_arquivos desligado (usa a listagem em texto que ja existe)",
   AppSink.menu_arquivos is False)


class _SemTTY:
    def isatty(self):
        return False


_stdin_antes = sys.stdin
try:
    sys.stdin = _SemTTY()  # type: ignore[assignment]
    ok("menu de entrada nao pergunta nada sem terminal (nao trava automacao)",
       escolher_tela() == "chat")
finally:
    sys.stdin = _stdin_antes

# ---------- menu: numero digitado vira acao --------------------------------
ok("menu: Enter vai para a tela bonita", _opcao_do_menu("") == "app")
ok("menu: 2 e o terminal", _opcao_do_menu("2") == "chat")
ok("menu: 3 sao as configuracoes", _opcao_do_menu("3") == "config")
ok("menu: 4 sai", _opcao_do_menu("4") == "sair")
ok("menu: palavra tambem vale", _opcao_do_menu("configuracoes") == "config")
ok("menu: lixo nao escolhe por conta", _opcao_do_menu("xyz") == "")

# ---------- /tela: comando e da TELA, nao do cerebro ------------------------
ok("/tela pede a tela do navegador", eh_troca_para_app("/tela"))
ok("/app tambem", eh_troca_para_app("/app"))
ok("/navegador tambem", eh_troca_para_app("  /navegador "))
# A ajuda em ingles/espanhol escreve /screen e /pantalla: os tres nomes tem que
# abrir a tela (antes so /tela funcionava e /screen caia em "comando desconhecido").
ok("/screen tambem (nome do comando em ingles)", eh_troca_para_app("/screen"))
ok("/pantalla tambem (nome do comando em espanhol)", eh_troca_para_app("/pantalla"))
ok("maiuscula e espaco nao atrapalham", eh_troca_para_app(" /SCREEN "))
ok("texto comum nao troca de tela", not eh_troca_para_app("abre a tela pra mim"))
ok("/telapronta nao e /tela", not eh_troca_para_app("/telapronta"))
ok("/screenshots nao e /screen", not eh_troca_para_app("/screenshots"))

# ---------- rede: flag manda mais que config -------------------------------
ok("rede desligada por padrao", rede_efetiva({}) is False)
ok("config ligado abre a rede", rede_efetiva({"rede": True}) is True)
ok("--rede liga mesmo com config desligado",
   rede_efetiva({"rede": False}, flag_rede=True) is True)
ok("--local fecha mesmo com config ligado",
   rede_efetiva({"rede": True}, flag_local=True) is False)

# ---------- 2. app sem modelo: core de mentira, servidor de verdade -----------
CFG = {
    "model": "teste",
    "base_url": "http://127.0.0.1:1/v1",
    "max_tokens": 128,
    "temperature": 0.0,
    "thinking": "auto",
    "context_budget_chars": 4000,
    "lang": "pt",
    "command_allowlist": [],
    "palco": False,
}


class CoreFalso:
    """Faz o papel do ChatCore: recebe o turno e devolve 'continue'."""

    def __init__(self, app):
        self.app = app
        self.textos = []
        self.parado = False
        self.steers = []

    def submit(self, texto):
        self.textos.append(texto)
        self.app.canal.emitir("linha", texto="turno:" + texto, estilo="")
        return "continue"

    def stop(self):
        self.parado = True

    def steer(self, texto):
        self.steers.append(texto)


TOKEN = "token-de-teste-1234567890"
app = App(CFG, token=TOKEN)
app.core = CoreFalso(app)   # type: ignore[assignment]
app.canal.emitir("linha", texto="banner de teste", estilo="")
app.subir_servidor(porta=0)
time.sleep(0.05)


def pedir(metodo, caminho, corpo=None, cookie=True, host=None, origem=None):
    conn = http.client.HTTPConnection("127.0.0.1", app.porta, timeout=6)
    cabecalhos = {}
    if cookie:
        cabecalhos["Cookie"] = f"teo_app={TOKEN}"
    if host:
        cabecalhos["Host"] = host
    if origem:
        cabecalhos["Origin"] = origem
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode("utf-8")
        cabecalhos["Content-Type"] = "application/json"
    conn.request(metodo, caminho, body=dados, headers=cabecalhos)
    resp = conn.getresponse()
    bruto = resp.read()
    cabeçalhos = dict(resp.getheaders())
    conn.close()
    return resp.status, bruto, cabeçalhos


# ---------- 3. porta fechada --------------------------------------------------
status, _, _ = pedir("GET", "/", cookie=False)
ok("GET / sem token = 401", status == 401)

status, _, _ = pedir("GET", "/api/inicio", cookie=False)
ok("GET /api/inicio sem token = 401", status == 401)

status, _, _ = pedir("POST", "/api/turno", corpo={"texto": "oi"}, cookie=False)
ok("POST /api/turno sem token = 401", status == 401)

status, _, _ = pedir("GET", "/", host="evil.example.com")
ok("Host estranho = 421 (DNS rebinding)", status == 421)

status, _, _ = pedir("POST", "/api/turno", corpo={"texto": "oi"},
                     origem="http://evil.example.com")
ok("Origin estranho = 403 (pagina de fora nao manda recado)", status == 403)

status, bruto, cab = pedir("GET", f"/?t={TOKEN}", cookie=False)
ok("GET com token = 303 e cookie HttpOnly",
   status == 303 and "HttpOnly" in cab.get("Set-Cookie", "")
   and "SameSite=Strict" in cab.get("Set-Cookie", ""))

status, bruto, _ = pedir("GET", "/", cookie=True)
ok("GET / com cookie = 200", status == 200)
ok("pagina tem o gato e o botao de enviar",
   b"teo.svg" in bruto and b'id="enviar"' in bruto)

status, bruto, _ = pedir("GET", "/app.css", cookie=False)
ok("CSS da tela e servido (estatico, sem token)", status == 200 and b"--accent" in bruto)

status, bruto, _ = pedir("GET", "/teo.svg", cookie=False)
ok("desenho do gato e servido", status == 200 and b"<svg" in bruto)

# ---------- 4. estado e strings ----------------------------------------------
status, bruto, _ = pedir("GET", "/api/inicio")
dados = json.loads(bruto.decode("utf-8"))
ok("/api/inicio = 200", status == 200)
ok("strings vem do i18n", dados["strings"]["app.enviar"] == t("app.enviar"))
ok("nao expoe chave de API no estado", not any("key" in k for k in dados))
ok("modo rede desligado por padrao", dados["rede"] is False)
ok("a ajuda propria do app vem pronta", len(dados.get("ajuda") or []) >= 20)
_cmds = [cmd for cmd, _desc in dados.get("ajuda") or []]
ok("a ajuda lista os comandos importantes que existem no app",
   all(x in _cmds for x in ("/provedor", "/configurar", "/modelo", "/doctor",
                            "/lingua", "/ctx", "/skills", "/atualizar")))
ok("a ajuda tem secoes (linha sem explicacao)",
   any(not desc for _cmd, desc in dados.get("ajuda") or []))
ok("a ajuda do app nao cita tecla de terminal",
   all("Ctrl+J" not in desc and "Alt+Enter" not in desc
       for _cmd, desc in dados.get("ajuda") or []))

# ---------- 5. SSE: replay do que ja aconteceu -------------------------------
# A conexao e feita com socket cru, de proposito: o http.client guarda parte do
# corpo num buffer proprio e, no macOS, os bytes que ja chegaram junto com o
# cabecalho se perdiam (o teste lia zero eventos). Aqui tudo o que chega e lido.
import select

_sock = socket.create_connection(("127.0.0.1", app.porta), timeout=10)
_sock.sendall(
    (f"GET /api/eventos?desde=0 HTTP/1.1\r\n"
     f"Host: 127.0.0.1:{app.porta}\r\n"
     f"Cookie: teo_app={TOKEN}\r\n"
     f"\r\n").encode("ascii")
)
_resto = ""


def _ler_cabecalho() -> str:
    global _resto
    while "\r\n\r\n" not in _resto:
        dados = _sock.recv(65536)
        if not dados:
            raise AssertionError("o stream fechou antes do cabecalho")
        _resto += dados.decode("utf-8", "replace")
    cabecalho, _, _resto = _resto.partition("\r\n\r\n")
    return cabecalho


_cab = _ler_cabecalho()
ok("SSE responde 200", _cab.splitlines()[0].endswith("200 OK"))
ok("SSE e event-stream", "text/event-stream" in _cab)


def ler_eventos(quantos=6, limite=4.0):
    """Le o SSE do socket cru (select antes de cada recv; nunca trava)."""
    global _resto
    eventos = []
    fim = time.time() + limite
    while time.time() < fim and len(eventos) < quantos:
        while "\n" in _resto:
            linha, _, _resto = _resto.partition("\n")
            linha = linha.strip()
            if linha.startswith("data: "):
                eventos.append(json.loads(linha[6:]))
                if len(eventos) >= quantos:
                    return eventos
        pronto, _, _ = select.select([_sock], [], [], max(0.05, fim - time.time()))
        if not pronto:
            break
        try:
            dados = _sock.recv(65536)
        except OSError:
            break
        if not dados:
            break
        _resto += dados.decode("utf-8", "replace")
    return eventos


eventos = ler_eventos(quantos=3)
ok("SSE reenviou o que ja estava no buffer",
   any(e.get("texto") == "banner de teste" for e in eventos))

# ---------- 6. turno pelo POST + evento no SSE ------------------------------
status, _, _ = pedir("POST", "/api/turno", corpo={"texto": "manda oi"})
ok("POST /api/turno = 202", status == 202)
time.sleep(0.3)
eventos = ler_eventos(quantos=3)
ok("o turno chegou no core", app.core.textos == ["manda oi"])
ok("a resposta do turno saiu pelo SSE",
   any(e.get("texto") == "turno:manda oi" for e in eventos))

# ---------- 7. licenca: pergunta, resposta e negacao ------------------------
from bgh.approvals import Gate

gate = Gate(CFG, app.sink.ask_approval)
resultado = {}


def pede_licenca():
    resultado["ok"] = gate.command_ok("chmod 777 /tmp/teste.txt")[0]


fio = threading.Thread(target=pede_licenca, daemon=True)
fio.start()
time.sleep(0.3)
eventos = ler_eventos(quantos=4)
pedido = next((e for e in eventos if e.get("tipo") == "pergunta"), None)
ok("o Gate pediu licenca pelo modal", pedido is not None)
ok("o modal tem os quatro caminhos (o/s/a/d)",
   pedido is not None and len(pedido.get("opcoes") or []) == 4)
ok("a ultima opcao e 'nao'", pedido["opcoes"][-1]["tom"] == "nao")

status, _, _ = pedir("POST", "/api/responder", corpo={"id": pedido["id"], "valor": "o"})
ok("POST /api/responder = 200", status == 200)
fio.join(3)
ok("licenca respondida destravou o agente", resultado.get("ok") is True and not fio.is_alive())

status, _, _ = pedir("POST", "/api/responder", corpo={"id": pedido["id"], "valor": "o"})
ok("responder duas vezes a mesma pergunta = 410", status == 410)

# Agora o caso que mais importa: ninguem responde. parar() nega e destrava.
resultado = {}


def pede_licenca_2():
    resultado["ok"] = gate.command_ok("systemctl restart teo-teste")[0]


fio = threading.Thread(target=pede_licenca_2, daemon=True)
fio.start()
time.sleep(0.3)
pedir("POST", "/api/parar")
fio.join(3)
ok("sem resposta a licenca = NEGADO (falha fechada)",
   resultado.get("ok") is False and not fio.is_alive())
ok("/api/parar tambem chega no core", app.core.parado is True)

# ---------- 8. sair: a tela e avisada antes da porta cair -------------------
def ler_ate(tipo, limite=6.0):
    """Le o SSE ate encontrar o evento pedido (ha outros na fila antes dele)."""
    achados = []
    fim = time.time() + limite
    while time.time() < fim:
        novos = ler_eventos(quantos=8, limite=max(0.15, fim - time.time()))
        achados.extend(novos)
        if any(e.get("tipo") == tipo for e in achados):
            break
        if not novos:
            break
    return achados


status, _, _ = pedir("POST", "/api/sair")
ok("POST /api/sair = 200", status == 200)
eventos = ler_ate("encerrando")
ok("o evento 'encerrando' saiu antes de fechar",
   any(e.get("tipo") == "encerrando" for e in eventos))
try:
    _sock.close()
except OSError:
    pass
app.esperar_fim(5)

# ---------- 9. nada escutando fora de 127.0.0.1 -----------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(1.0)
try:
    s.connect(("127.0.0.1", app.porta))
    aberto = True
except OSError:
    aberto = False
s.close()
ok("porta nao aceita conexao depois de sair", aberto is False)


# ---------- 10. o vigia: tela que da sinal de vida NAO e tela ausente --------
# Regressao do bug que negava a licenca sozinho: quem esta com a pagina aberta,
# parado, continua sendo quem pode responder. O sinal e o POST /api/vivo que a
# pagina manda a cada 12s.
import bgh.app_servidor as _srv

_antes = _srv.AUSENTE_NEGA_S
_srv.AUSENTE_NEGA_S = 5.0
try:
    app2 = App(CFG, token="tok2")
    app2.core = CoreFalso(app2)   # type: ignore[assignment]
    app2.subir_servidor(porta=0)
    time.sleep(0.1)

    def vivo():
        conn = http.client.HTTPConnection("127.0.0.1", app2.porta, timeout=6)
        conn.request("POST", "/api/vivo", headers={"Cookie": "teo_app=tok2"})
        r = conn.getresponse()
        r.read()
        conn.close()
        return r.status

    ok("POST /api/vivo responde 200", vivo() == 200)

    pedido2 = app2.abrir_pergunta(
        {"modo": "opcoes", "titulo": "t", "label": "l", "detalhe": "",
         "opcoes": [{"texto": "sim", "codigo": "s", "tom": "bom"},
                    {"texto": "nao", "codigo": "d", "tom": "nao"}]}, "d")
    time.sleep(2.0)
    ok("com sinal de vida a licenca continua esperando", not pedido2["future"].done())
    ok("o sinal de vida manteve o app acordado", app2.fechado is False)

    # a pessoa fechou a aba (parou de mandar sinal): o vigia nega em AUSENTE+2s
    time.sleep(8.0)
    ok("sem sinal de vida a licenca e NEGADA pelo vigia",
       pedido2["future"].done() and pedido2["future"].result() == "d")

    # Botao Terminal: a tela avisa e o processo devolve o codigo que abre o TUI.
    conn = http.client.HTTPConnection("127.0.0.1", app2.porta, timeout=8)
    conn.request("POST", "/api/terminal", headers={"Cookie": "teo_app=tok2"})
    resp2 = conn.getresponse()
    resp2.read()
    conn.close()
    ok("POST /api/terminal = 200", resp2.status == 200)
    ok("o app registra que vai para o terminal", app2.motivo == "terminal")
    app2.esperar_fim(5)
finally:
    _srv.AUSENTE_NEGA_S = _antes

# ---------- 11. CTRL+C durante o encerramento nao vira traceback ------------
# Regressao do macOS: tres ^C seguidos interrompiam o sleep do encerramento e o
# TEO terminava com um traceback na cara do usuario.
app3 = App(CFG, token="tok3")
app3.core = None
app3.subir_servidor(porta=0)
time.sleep(0.1)
_sono = _srv.time.sleep


def _sono_interrompido(_segundos):
    raise KeyboardInterrupt


_srv.time.sleep = _sono_interrompido     # type: ignore[assignment]
try:
    app3.encerrar("ctrl+c")
    ok("encerrar sobrevive a CTRL+C no meio da espera", True)
except KeyboardInterrupt:
    ok("encerrar sobrevive a CTRL+C no meio da espera", False)
finally:
    _srv.time.sleep = _sono                    # type: ignore[assignment]
    app3.esperar_fim(5)
ok("sem CTRL+C o app ainda fecha normal", app3.fechado is True)

# ---------- 12. aviso de "TEO trabalhando" bem visivel ----------------------
# Antes so a frase pequena do rodape mudava: quem olhava a conversa nao sabia
# distinguir "pensando" de "travado". Agora existe uma faixa ACIMA da linha de
# digitar, com rodinha, texto, contador de segundos e barra em movimento.
_raiz12 = Path(__file__).resolve().parents[1]
_html12 = (_raiz12 / "bgh" / "assets" / "app.html").read_text(encoding="utf-8")
_css12 = (_raiz12 / "bgh" / "assets" / "app.css").read_text(encoding="utf-8")
_js12 = (_raiz12 / "bgh" / "assets" / "app.js").read_text(encoding="utf-8")
ok("a faixa de 'TEO trabalhando' existe acima da linha de digitar",
   'id="trabalhando"' in _html12
   and _html12.index('id="trabalhando"') < _html12.index('class="linha-digitar"'))
ok("a faixa tem rodinha, texto e contador de segundos",
   'class="rodinha"' in _html12 and 'id="trabalhando-texto"' in _html12
   and 'id="trabalhando-tempo"' in _html12)
ok("a faixa nasce escondida e e anunciada por leitor de tela",
   'id="trabalhando" class="trabalhando" role="status" aria-live="polite" hidden' in _html12)
ok("o CSS anima rodinha e barra, sem nada piscando",
   "@keyframes girar" in _css12 and "@keyframes correr" in _css12
   and "infinite" in _css12)
ok("a faixa aparece e some junto com o estado ocupado",
   'faixa.hidden = !ocupado' in _js12
   and 'document.body.classList.toggle("ocupado", ocupado)' in _js12)
ok("o contador do turno mostra segundos e minutos",
   "function comecarRelogio" in _js12 and "Math.floor(segundos / 60)" in _js12)
ok("a frase da faixa vem do i18n (tres idiomas)",
   dados["strings"].get("app.trabalhando_curto") == t("app.trabalhando_curto")
   and t("app.trabalhando_curto").strip() != "")
ok("a dica do turno nao repete a frase da faixa (aviso, nao eco)",
   not t("app.trabalhando").startswith(t("app.trabalhando_curto")))
# A faixa muda a ALTURA do rodape: a conversa encolhe e, sem devolver a rolagem,
# a ultima linha da mensagem da pessoa ficava cortada no meio pela borda (visto
# na tela real, com lista de marcadores na propria mensagem).
ok("a faixa nao corta a ultima linha da mensagem (volta para o fim)",
   "var estavaNoFim = pertoDoFim();" in _js12
   and _js12.count("rolar(estavaNoFim);") >= 2)
ok("rolar e salto instantaneo (a animacao era cortada pelo reflow)",
   'c.style.scrollBehavior = "auto";' in _js12
   and "c.scrollTop = c.scrollHeight;" in _js12)
ok("a caixa de digitar crescendo tambem preserva o fim da conversa",
   "var estavaNoFim = pertoDoFim();" in
   _js12[_js12.index("function ajustarAltura()"):_js12.index("function enviar(")])

# ---------- 13. a barra sozinha abre a lista de opcoes ----------------------
# No terminal o "/" abre o menu da pasta. No navegador nao existe pasta: a barra
# sozinha abre a lista de comandos da tela (mesmo cartao do botao Opcoes).
ok("digitar so a barra abre a lista de opcoes da tela",
   'if (texto === "/")' in _js12
   and _js12.index('if (texto === "/")') < _js12.index('if (!silencioso) { bolha('))
ok("a dica do rodape continua ensinando o comando de ajuda",
   t("app.dica", cmd="/ajuda").startswith("ENTER envia"))
ok("na ajuda, os comandos do terminal aparecem com a barra",
   "/ditar, /voz, /fonte, /palco" in _cmds)

# ---------- 14. instalacao nova nasce com a voz DESLIGADA -------------------
# Pedido do dono: instalacao padrao sem voz. O padrao mora em DEFAULTS e vale
# para quem instala hoje; quem ja ligou no /voz mantem a escolha gravada.
from bgh import config as _cfg14
from bgh.config import DEFAULTS as _DEF14

ok("voz desligada de fabrica (DEFAULTS)", _DEF14.get("voz") is False)
_path14 = _cfg14.CONFIG_PATH
_dir14 = Path(tempfile.mkdtemp(prefix="bgh_voz_"))
try:
    _cfg14.CONFIG_PATH = _dir14 / "config.json"
    _cfg14.CONFIG_PATH.write_text(
        json.dumps({"model": "m", "base_url": "http://127.0.0.1:1/v1"}), encoding="utf-8")
    _novo14 = _cfg14.load_config()
    ok("config recem-criado nao liga a voz sozinho", _novo14.get("voz") is False)
finally:
    _cfg14.CONFIG_PATH = _path14

# ---------- 15. /modelo e /provedor atualizam a linha de cima ---------------
# A linha de cima da tela (nome do modelo + versao) era escrita UMA vez, na
# abertura: depois de trocar de modelo/provedor o nome antigo continuava la ate
# a pessoa recarregar a pagina (bug visto pelo dono do projeto no navegador).
from bgh.chat_core import ChatCore as _Core15


class _LLM15:
    """Modelo de mentira: aqui so a troca de nome importa."""

    def __init__(self):
        self.cfg = {}

    def complete(self, *a, **k):
        return iter(())


app4 = App(dict(CFG), token="tok4")
app4.core = _Core15(dict(CFG), app4.sink, llm=_LLM15())  # type: ignore[arg-type]
# O menu de "nivel de pensamento" abriria um modal e a thread ficaria esperando
# resposta do navegador: aqui a escolha e nenhuma, o que ele ja sabe entender.
app4.sink.ask_choice = lambda *a, **k: ""
app4.subir_servidor(porta=0)
time.sleep(0.05)
_fila15 = app4.canal.assinar(0)
app4.core.submit("/modelo modelo-trocado")
_eventos15 = []
while not _fila15.empty():
    _eventos15.append(_fila15.get_nowait())
app4.canal.desassinar(_fila15)
_modelo15 = [e for e in _eventos15 if e.get("tipo") == "modelo"]
ok("trocar de modelo avisa a tela na hora (evento 'modelo')",
   bool(_modelo15) and _modelo15[-1].get("modelo") == "modelo-trocado")
ok("o aviso leva o servidor junto",
   bool(_modelo15) and "base_url" in _modelo15[-1])
ok("a tela desenha o aviso (o nome de cima e escrito em UM lugar)",
   'case "modelo": mostrarModelo(e.modelo); break;' in _js12
   and _js12.count('$("sub").textContent') == 1)
ok("idioma antigo nao fica: o nome vem do evento, nao de /api/inicio",
   "function mostrarModelo" in _js12)
app4.encerrar("teste")
app4.esperar_fim(5)

# ---------- 16. documento citado na resposta vira link que abre --------------
# Pedido do dono: quando o TEO cria um documento, o caminho na resposta tem que
# ser clicavel e abrir em OUTRA janela. Aqui se prova o lado do servidor: o que
# ele serve, o que ele RECUSA e que sem sessao nao sai nada.
_css16 = (_raiz12 / "bgh" / "assets" / "app.css").read_text(encoding="utf-8")
_pasta16 = Path(tempfile.mkdtemp(prefix="bgh_doc_", dir=TMP))
_doc16 = _pasta16 / "relatorio.txt"
_doc16.write_text("conteudo do relatorio", encoding="utf-8")
_pagina16 = _pasta16 / "cartilha.html"     # HTML do TEO: abre, mas sem script
_pagina16.write_text("<h1>oi</h1><script>document.title='x'</script>",
                     encoding="utf-8")
_script16 = _pasta16 / "solto.js"          # JS nunca e documento: fora
_script16.write_text("alert(1)", encoding="utf-8")
_sem_ext16 = _pasta16 / "binario"          # sem extensao: tambem nao
_sem_ext16.write_bytes(b"\x00\x01")

app5 = App(dict(CFG), token="tok5")
app5.core = CoreFalso(app5)  # type: ignore[assignment]
app5.subir_servidor(porta=0)
time.sleep(0.05)


def pedir16(caminho, cookie=True):
    conn = http.client.HTTPConnection("127.0.0.1", app5.porta, timeout=6)
    cab = {"Cookie": "teo_app=tok5"} if cookie else {}
    conn.request("GET", caminho, headers=cab)
    resp = conn.getresponse()
    corpo = resp.read()
    cabecalhos = dict(resp.getheaders())
    conn.close()
    return resp.status, corpo, cabecalhos


from urllib.parse import quote as _quote16

_url_doc16 = "/api/arquivo?c=" + _quote16(str(_doc16))
_status16, _corpo16, _cab16 = pedir16(_url_doc16, cookie=False)
ok("documento sem sessao = 401", _status16 == 401)

_status16, _corpo16, _cab16 = pedir16(_url_doc16)
ok("documento da pessoa abre (200) com o conteudo certo",
   _status16 == 200 and _corpo16 == b"conteudo do relatorio")
ok("o documento abre DENTRO da janela (inline) e sem rodar script",
   "inline" in _cab16.get("Content-Disposition", "")
   and _cab16.get("Content-Security-Policy") == "sandbox")
ok("tipo do documento vem certo (texto)", "text/plain" in _cab16.get("Content-Type", ""))

_status16, _corpo16h, _cab16h = pedir16("/api/arquivo?c=" + _quote16(str(_pagina16)))
ok("cartilha .html do TEO abre no navegador (0.2.36)",
   _status16 == 200 and b"<h1>oi</h1>" in _corpo16h)
ok("...e abre SEM rodar script e SEM a sessao do TEO (CSP sandbox)",
   _cab16h.get("Content-Security-Policy") == "sandbox")
_status16, _, _ = pedir16("/api/arquivo?c=" + _quote16(str(_script16)))
ok("arquivo .js NAO e servido (nunca e documento)", _status16 == 404)
_status16, _, _ = pedir16("/api/arquivo?c=" + _quote16(str(_sem_ext16)))
ok("arquivo sem extensao conhecida nao e servido", _status16 == 404)
_status16, _, _ = pedir16("/api/arquivo?c=" + _quote16(str(_pasta16 / "nao_existe.txt")))
ok("documento que nao existe = 404", _status16 == 404)
_status16, _, _ = pedir16("/api/arquivo?c=" + _quote16("/etc/passwd"))
ok("fora das pastas da pessoa = 404 (nada de /etc, /usr)", _status16 == 404)
_status16, _, _ = pedir16("/api/arquivo?c=" + _quote16(str(_pasta16)))
ok("pasta (nao arquivo) = 404", _status16 == 404)
_status16, _, _ = pedir16("/api/arquivo?c=")
ok("sem caminho = 404", _status16 == 404)

_status16, _, _ = pedir16(_url_doc16 + "&checar=1")
ok("a tela pergunta se o documento existe (204, sem baixar nada)", _status16 == 204)
_status16, _corpo16b, _ = pedir16("/api/arquivo?checar=1&c=" + _quote16(str(_script16)))
ok("a checagem tambem recusa tipo fora da lista", _status16 == 404 and bool(_corpo16b))
_status16, _, _ = pedir16("/api/arquivo?checar=1&c="
                          + _quote16(str(_pasta16 / "nao_existe.txt")))
ok("checagem de arquivo inexistente = 404 (nao vira link morto)", _status16 == 404)

from bgh.app_servidor import DOC_TIPOS as _TIPOS16

_exts_js16 = re.findall(r'"([a-z0-9]{2,5})"',
                        _js12[_js12.index("var DOC_EXTS"):
                              _js12.index("var DOC_RE")])
ok("a tela conhece exatamente os tipos que o servidor serve",
   sorted(set("." + e for e in _exts_js16)) == sorted(_TIPOS16.keys()))
_regex16 = _js12[_js12.index("var DOC_RE"):_js12.index("function candidatosDeDocumento")]
_alvo16 = re.search(r"\.\(\?:([a-z0-9|]+)\)\)", _regex16)
ok("o regex do link cobre os mesmos tipos da lista",
   _alvo16 is not None and sorted(_alvo16.group(1).split("|")) == sorted(_exts_js16))
ok("caminho com espaco no nome e aceito (o candidato vai ate a extensao)",
   "<>|]*?" in _regex16 and "checar=1" in _js12)

ok("a tela transforma o caminho em link que abre em outra janela",
   'a.target = "_blank";' in _js12 and "function ligarCaminhos" in _js12
   and '"/api/arquivo?c="' in _js12)
ok("a varredura roda quando a resposta termina",
   "ligarCaminhos();" in _js12[_js12.index("function fimTurno"):
                               _js12.index("function fimTurno") + 800])
ok("o link de documento tem estilo proprio (da para ver que e clicavel)",
   "a.arquivo" in _css16)
app5.encerrar("teste")
app5.esperar_fim(5)

# ---------- 17. clipe de anexo: arquivo recebido, recusado e lido -----------
# Pedido do dono: clipe embaixo da caixa de digitar para anexar foto, PDF,
# Word, Excel e texto. Aqui se prova o lado do SERVIDOR: o que entra, o que e
# RECUSADO (tipo e tamanho), como o anexo chega ao core e o que a tela mostra.
import zipfile as _zip17

import bgh.app_servidor as _srv17
from bgh import anexos as _anx17
from bgh.anexos import ler_texto as _ler17


class CoreFalso17(CoreFalso):
    """Core de mentira que GUARDA os anexos recebidos do servidor."""

    def __init__(self, app):
        super().__init__(app)
        self.chamadas: list[tuple[str, list]] = []

    def submit(self, texto, anexos=None):
        self.chamadas.append((texto, list(anexos or [])))
        self.textos.append(texto)
        self.app.canal.emitir("linha", texto="turno:" + texto, estilo="")
        return "continue"


app6 = App(dict(CFG), token="tok17")
app6.core = CoreFalso17(app6)  # type: ignore[assignment]
app6.subir_servidor(porta=0)
time.sleep(0.05)


def pedir_binario17(caminho, dados, cookie=True):
    conn = http.client.HTTPConnection("127.0.0.1", app6.porta, timeout=10)
    cab = {"Content-Type": "application/octet-stream"}
    if cookie:
        cab["Cookie"] = "teo_app=tok17"
    conn.request("POST", caminho, body=dados, headers=cab)
    resp = conn.getresponse()
    corpo = resp.read()
    conn.close()
    return resp.status, corpo


def pedir_json17(caminho, corpo):
    conn = http.client.HTTPConnection("127.0.0.1", app6.porta, timeout=10)
    cab = {"Cookie": "teo_app=tok17", "Content-Type": "application/json"}
    conn.request("POST", caminho, body=json.dumps(corpo).encode("utf-8"), headers=cab)
    resp = conn.getresponse()
    resp.read()
    conn.close()
    return resp.status


_AB17 = b"2 ovos e 1 copo de leite"
_st17, _cp17 = pedir_binario17("/api/anexo?nome=receita.txt", _AB17)
_dd17 = json.loads(_cp17.decode("utf-8"))
ok("anexo de texto entra pela tela (200)", _st17 == 200)
ok("o anexo devolve id, nome, tipo e tamanho",
   _dd17.get("ok") is True and bool(_dd17.get("id"))
   and _dd17.get("nome") == "receita.txt" and _dd17.get("tipo") == "texto"
   and _dd17.get("tamanho") == len(_AB17))
ok("o anexo fica na pasta do TEO (nada espalhado pelo disco)",
   bool(app6.anexos)
   and all(str(_anx17.pasta()) in m["caminho"] for m in app6.anexos.values()))

_st17, _cp17 = pedir_binario17("/api/anexo?nome=programa.exe", b"MZ")
ok("executavel NAO entra (lista de tipos e fechada)",
   _st17 == 400 and "exe" in _cp17.decode("utf-8"))
_st17, _cp17 = pedir_binario17("/api/anexo?nome=vazio.txt", b"")
ok("arquivo vazio e recusado", _st17 == 400)
_st17, _cp17 = pedir_binario17("/api/anexo?nome=segredo.txt", b"oi", cookie=False)
ok("anexo sem sessao = 401 (a porta nao recebe arquivo de fora)", _st17 == 401)

_antes_max17 = _srv17.ANEXO_MAX
_srv17.ANEXO_MAX = 1024
try:
    _st17, _cp17 = pedir_binario17("/api/anexo?nome=grande.txt", b"x" * 2000)
    ok("arquivo acima do limite = 413 com frase para a pessoa",
       _st17 == 413 and "MB" in _cp17.decode("utf-8"))
finally:
    _srv17.ANEXO_MAX = _antes_max17

# --- o turno leva o anexo ao core ---
_id17 = _dd17["id"]
_st17 = pedir_json17("/api/turno", {"texto": "leia isso", "anexos": [_id17]})
time.sleep(0.3)
ok("o turno com anexo chega no core com o caminho do arquivo",
   bool(app6.core.chamadas) and app6.core.chamadas[-1][1]
   and app6.core.chamadas[-1][1][0].endswith(".txt"))
ok("o texto digitado continua sendo o pedido", app6.core.chamadas[-1][0] == "leia isso")

_st17 = pedir_json17("/api/turno", {"texto": "", "anexos": [_id17]})
time.sleep(0.3)
ok("anexo sozinho, sem texto, tambem vira turno",
   len(app6.core.chamadas) == 2 and app6.core.chamadas[-1][0] == "")

_st17 = pedir_json17("/api/turno", {"texto": "oi", "anexos": ["naoexiste1"]})
time.sleep(0.3)
ok("id de anexo que nao existe: NAO chama o modelo so com o texto (0.2.35)",
   len(app6.core.chamadas) == 2)

# --- leitura de cada tipo (o que o MODELO recebe) ---
_p17 = Path(tempfile.mkdtemp(prefix="bgh_anx_", dir=TMP))

_nota17 = _p17 / "nota.md"
_nota17.write_text("# Contas\n\npagar luz", encoding="utf-8")
_conteudo17, _erro17, _cortado17 = _ler17(_nota17)
ok("texto puro entra inteiro", _erro17 is None and "pagar luz" in _conteudo17
   and _cortado17 is False)

_docx17 = _p17 / "carta.docx"
with _zip17.ZipFile(_docx17, "w") as _z17:
    _z17.writestr(
        "word/document.xml",
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
        '2006/main"><w:body><w:p><w:r><w:t>Prezado cliente</w:t></w:r></w:p>'
        "<w:p><w:r><w:t>segunda linha</w:t></w:r></w:p></w:body></w:document>")
_conteudo17, _erro17, _ = _ler17(_docx17)
ok("Word (.docx) vira texto, paragrafo por linha",
   _erro17 is None and "Prezado cliente" in _conteudo17
   and "segunda linha" in _conteudo17)

_xlsx17 = _p17 / "contas.xlsx"
with _zip17.ZipFile(_xlsx17, "w") as _z17:
    _z17.writestr(
        "xl/sharedStrings.xml",
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<si><t>Aluguel</t></si><si><t>1200</t></si></sst>")
    _z17.writestr(
        "xl/worksheets/sheet1.xml",
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/'
        'main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c>'
        '<c r="B1" t="s"><v>1</v></c></row></sheetData></worksheet>')
_conteudo17, _erro17, _ = _ler17(_xlsx17)
ok("Excel (.xlsx) vira texto com as celulas",
   _erro17 is None and "Aluguel" in _conteudo17 and "1200" in _conteudo17)

_pptx17 = _p17 / "aula.pptx"
with _zip17.ZipFile(_pptx17, "w") as _z17:
    _z17.writestr(
        "ppt/slides/slide1.xml",
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/'
        'main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        "<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Titulo do slide</a:t>"
        "</a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>")
_conteudo17, _erro17, _ = _ler17(_pptx17)
ok("PowerPoint (.pptx) vira texto com o slide",
   _erro17 is None and "Titulo do slide" in _conteudo17)


def _pdf_minimo17(caminho: Path, texto: str) -> None:
    """PDF de uma pagina com texto (xref calculado): prova a leitura de PDF."""
    corpo = b"BT /F1 12 Tf 20 100 Td (" + texto.encode("latin-1") + b") Tj ET"
    objetos = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(corpo)).encode() + b">>stream\n" + corpo
        + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    saida = bytearray(b"%PDF-1.4\n")
    posicoes = []
    for indice, objeto in enumerate(objetos, start=1):
        posicoes.append(len(saida))
        saida += str(indice).encode() + b" 0 obj\n" + objeto + b"\nendobj\n"
    inicio_xref = len(saida)
    saida += b"xref\n0 " + str(len(objetos) + 1).encode() + b"\n0000000000 65535 f \n"
    for posicao in posicoes:
        saida += f"{posicao:010d} 00000 n \n".encode()
    saida += (b"trailer\n<</Size " + str(len(objetos) + 1).encode()
              + b"/Root 1 0 R>>\nstartxref\n" + str(inicio_xref).encode()
              + b"\n%%EOF\n")
    caminho.write_bytes(bytes(saida))


try:
    import pypdf as _pypdf17  # noqa: F401
    _tem_pypdf17 = True
except ImportError:
    _tem_pypdf17 = False

_pdf17 = _p17 / "contrato.pdf"
_pdf_minimo17(_pdf17, "Contrato de aluguel")
_conteudo17, _erro17, _ = _ler17(_pdf17)
if _tem_pypdf17:
    ok("PDF vira texto (leitura pelo pypdf)",
       _erro17 is None and "Contrato" in _conteudo17)
else:
    ok("sem pypdf o PDF tem frase propria (nao quebra a tela)",
       _conteudo17 == "" and _erro17 == t("anexo.pdf_lib", atualizar="/atualizar"))
ok("a frase da falta de pypdf ensina o caminho de saida",
   t("anexo.pdf_lib").startswith("Para ler PDF"))

_exe17 = _p17 / "programa.exe"
_exe17.write_bytes(b"MZ")
_conteudo17, _erro17, _ = _ler17(_exe17)
ok("tipo fora da lista nao e lido como texto", _conteudo17 == "" and bool(_erro17))

_grande17 = _p17 / "grande.txt"
_grande17.write_text("a" * 50, encoding="utf-8")
_conteudo17, _erro17, _cortado17 = _ler17(_grande17, limite=10)
ok("arquivo grande e cortado, com aviso", _cortado17 is True
   and len(_conteudo17) == 10 and _erro17 is None)

_imagem17 = _p17 / "foto.png"
_imagem17.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 40)
_conteudo17, _erro17, _ = _ler17(_imagem17)
ok("imagem nao e lida como texto (ela vai pela visao)", _conteudo17 == ""
   and bool(_erro17) and _anx17.classificar(_imagem17) == "imagem")

# --- o anexo sai do disco no fim da sessao ---
_caminho17 = Path(next(iter(app6.anexos.values()))["caminho"])
ok("o anexo fica no disco enquanto a sessao esta aberta", _caminho17.is_file())
app6.limpar_anexos()
ok("o fim da sessao apaga o anexo do usuario", not _caminho17.exists())
app6.encerrar("teste")
app6.esperar_fim(5)

# --- o que a TELA mostra (sem navegador: HTML/JS/CSS conferidos) ---
_html17 = (_raiz12 / "bgh" / "assets" / "app.html").read_text(encoding="utf-8")
ok("a tela tem o clipe EMBAIXO da linha de digitar",
   'id="clipe"' in _html17
   and _html17.index('id="clipe"') > _html17.index('class="linha-digitar"'))
ok("o clipe abre o seletor com varios arquivos", 'id="arquivo" type="file"' in _html17
   and "multiple" in _html17[_html17.index('id="arquivo"'):][:60])
ok("a tela sobe o anexo antes do turno e manda os ids",
   '"/api/anexo?nome="' in _js12 and "anexos: ids" in _js12
   and "function anexarArquivos" in _js12)
ok("cola (CTRL+V) e arrastar arquivo tambem anexam",
   'addEventListener("paste"' in _js12 and '"drop"' in _js12)
ok("o limite e o tipo vem do servidor (a tela nao inventa)",
   "dados.anexo.accept" in _js12 or "dados.anexo.aceita" in _js12)
ok("o clipe tem estilo proprio e gira com o tema",
   ".botao-clipe" in _css16 and ".anexo-item" in _css16)
ok("o link de documento aceita caminho do Windows (bug da 0.2.33)",
   "A-Za-z" in _regex16 and "\\\\" in _regex16)
ok("a dica divide a linha do clipe (o rodape nao gasta linha extra)",
   _html17.index('id="dica"') > _html17.index('class="linha-anexo"')
   and _html17.index('id="dica"') < _html17.index("</footer>"))
ok("tela baixa esconde a dica e encolhe o campo (conversa ganha altura)",
   "@media (max-height: 720px)" in _css16 and ".dica { display: none; }" in _css16)
# v0.2.36: o modelo manda tabela com "|" e a tela desenhava os pipes crus.
ok("a resposta desenha tabela de verdade (linhas com | viram <table>)",
   "function montarTabela" in _js12 and "function blocosDaResposta" in _js12
   and 'tabela.className = "tabela"' in _js12)
ok("a tabela e desenhada no fim do turno, junto com os links",
   "renderizarRespostas();" in _js12[_js12.index("function fimTurno"):
                                     _js12.index("function fimTurno") + 900])
ok("tabela larga rola dentro do cartao (nao empurra a conversa)",
   ".tabela-caixa" in _css16 and "overflow-x: auto" in _css16)


class _Consulta17:
    """Acesso a /api/inicio de uma instancia so para ler o bloco do anexo."""

    def __init__(self, porta: int, token: str):
        self.porta = porta
        self.token = token

    def inicio(self) -> dict:
        conn = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=6)
        conn.request("GET", "/api/inicio", headers={"Cookie": f"teo_app={self.token}"})
        resp = conn.getresponse()
        corpo = resp.read()
        conn.close()
        return json.loads(corpo.decode("utf-8"))


app7 = App(dict(CFG), token="tok17b")
app7.core = CoreFalso17(app7)  # type: ignore[assignment]
app7.subir_servidor(porta=0)
time.sleep(0.05)
_inicio17 = _Consulta17(app7.porta, "tok17b").inicio()
ok("/api/inicio leva o limite e os tipos do clipe",
   _inicio17.get("anexo", {}).get("max_mb") == 15
   and _inicio17.get("anexo", {}).get("max") == _anx17.MAX_ANEXOS
   and ".pdf" in (_inicio17.get("anexo", {}).get("aceita") or ""))
_aceitas17 = {x for x in _inicio17["anexo"]["aceita"].split(",") if x}
ok("a lista que a tela oferece e a MESMA que o servidor aceita",
   _aceitas17 == set(_anx17.TIPOS))
app7.encerrar("teste")
app7.esperar_fim(5)

print()
print(f"TODOS OS TESTES DA TELA PASSARAM ({PASS} verificacoes)")

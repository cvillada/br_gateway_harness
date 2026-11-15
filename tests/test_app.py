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
ok("texto comum nao troca de tela", not eh_troca_para_app("abre a tela pra mim"))
ok("/telapronta nao e /tela", not eh_troca_para_app("/telapronta"))

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

print()
print(f"TODOS OS TESTES DA TELA PASSARAM ({PASS} verificacoes)")

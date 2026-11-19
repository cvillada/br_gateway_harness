"""Conversa minima com o protocolo de depuracao do Chrome (CDP).

Por que isto existe: o /site abre uma janela do navegador do TEO para a PESSOA
fazer login e o TEO le a pagina depois. Fechar a janela e reler num processo
novo nao funciona direito por dois motivos medidos:

1. enquanto a janela esta aberta, o perfil fica em uso (o segundo processo sai
   com "Failed to create a ProcessSingleton") - ou seja, nao dava para ler com
   ela aberta;
2. o Chrome grava cookie em LOTE, com atraso (medido: 10-20 s para cookie com
   validade e ate ~40 s para cookie de sessao). Quem fecha a janela antes disso
   perde o login, e a leitura seguinte cai na tela de login.

Com o CDP o TEO le a ABA ABERTA: a janela continua aberta, o login mora na
memoria do navegador e nao depende do disco.

So stdlib: socket + base64 + struct + urllib. O WebSocket do CDP e simples
(texto, sem extensoes): handshake com Sec-WebSocket-Key, frames do cliente
sempre mascarados, frames do servidor nunca. Fragmentacao e ping sao tratados.

Seguranca: o Chrome escuta o CDP so em 127.0.0.1, numa porta aleatoria (0), e o
caminho do WebSocket tem um id aleatorio. O arquivo DevToolsActivePort do perfil
(que ja e do dono, 700) e a unica pista - nada fica exposto na rede.
"""

import base64
import json
import os
import socket
import struct
import time
import urllib.parse
import urllib.request
from pathlib import Path


def _sem_proxy() -> urllib.request.OpenerDirector:
    """HTTP local nunca vai por proxy (o ambiente pode ter http_proxy setado)."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _get_json(url: str, timeout: float = 2.0, metodo: str = "GET"):
    pedido = urllib.request.Request(url, method=metodo)
    with _sem_proxy().open(pedido, timeout=timeout) as resposta:
        return json.loads(resposta.read().decode("utf-8", "replace"))


def porta_ativa(perfil) -> int | None:
    """Porta do CDP publicada pelo navegador no arquivo DevToolsActivePort."""
    caminho = Path(perfil) / "DevToolsActivePort"
    try:
        primeira = caminho.read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, IndexError):
        return None
    for linha in primeira[:1]:
        if linha.strip().isdigit():
            return int(linha.strip())
    return None


def versao(porta: int, timeout: float = 1.5) -> dict | None:
    """{'Browser': ..., 'webSocketDebuggerUrl': ...} ou None se ninguem atende."""
    if not porta:
        return None
    try:
        dado = _get_json(f"http://127.0.0.1:{int(porta)}/json/version", timeout)
    except Exception:  # noqa: BLE001 - navegador fechando, porta estranha, proxy
        return None
    return dado if isinstance(dado, dict) else None


def vivo(porta) -> bool:
    return bool(versao(porta) if porta else None)


def abas(porta: int, timeout: float = 2.0) -> list:
    """Abas de pagina abertas: [{'url', 'title', 'webSocketDebuggerUrl'}, ...]."""
    try:
        lista = _get_json(f"http://127.0.0.1:{int(porta)}/json/list", timeout)
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(lista, list):
        return []
    return [item for item in lista
            if isinstance(item, dict) and item.get("type") == "page"
            and item.get("webSocketDebuggerUrl")]


def nova_aba(porta: int, url: str, timeout: float = 4.0) -> dict | None:
    """Abre uma aba nova. O Chrome novo exige PUT; o antigo aceita GET."""
    alvo = f"http://127.0.0.1:{int(porta)}/json/new?{urllib.parse.quote(url, safe='')}"
    for metodo in ("PUT", "GET"):
        try:
            dado = _get_json(alvo, timeout, metodo=metodo)
        except Exception:  # noqa: BLE001 - tenta o outro metodo
            continue
        if isinstance(dado, dict) and dado.get("webSocketDebuggerUrl"):
            return dado
    return None


def escolher(lista: list, url: str) -> dict | None:
    """A aba que corresponde ao endereco pedido.

    Ordem: endereco exato -> mesma pagina (query ignorada) -> quando o pedido e a
    RAIZ do site ("https://site.com/"), qualquer aba daquele site serve (a pessoa
    pediu "o site", nao uma pagina especifica).
    """
    alvo = urllib.parse.urlsplit(url or "")
    host = (alvo.netloc or "").lower()
    caminho = alvo.path or "/"
    if not host:
        return None
    exatos, mesma_pagina, mesmo_site = [], [], []
    for aba in lista:
        partes = urllib.parse.urlsplit(str(aba.get("url") or ""))
        if (partes.netloc or "").lower() != host:
            continue
        if str(aba.get("url")) == url:
            exatos.append(aba)
        elif (partes.path or "/") == caminho:
            mesma_pagina.append(aba)
        else:
            mesmo_site.append(aba)
    # Pagina especifica fora da janela: NUNCA ler outra do mesmo site (o modelo
    # concluiria que o site redirecionou) - quem chama abre uma aba nova.
    for grupo in (exatos, mesma_pagina):
        if grupo:
            return grupo[0]
    if caminho in ("/", ""):
        return mesmo_site[0] if mesmo_site else None
    return None


# ----- WebSocket (o minimo que o CDP usa) ------------------------------------
def _endereco(ws_url: str) -> tuple:
    partes = urllib.parse.urlsplit(ws_url or "")
    if partes.scheme not in ("ws", "wss") or not partes.hostname:
        raise OSError(f"endereco de depuracao invalido: {ws_url!r}")
    return partes.hostname, int(partes.port or 80), (partes.path or "/") + (
        "?" + partes.query if partes.query else "")


class _Ligacao:
    """Socket do WebSocket com o buffer que o handshake ja tiver consumido."""

    def __init__(self, sock: socket.socket, resto: bytes = b"") -> None:
        self.sock = sock
        self.buf = bytearray(resto)

    def _ler(self, quantos: int) -> bytes:
        while len(self.buf) < quantos:
            pedaco = self.sock.recv(max(4096, quantos - len(self.buf)))
            if not pedaco:
                raise OSError("a conexao com o navegador caiu")
            self.buf.extend(pedaco)
        dados = bytes(self.buf[:quantos])
        del self.buf[:quantos]
        return dados

    def _frame(self) -> tuple:
        b1, b2 = self._ler(2)
        fin = bool(b1 & 0x80)
        op = b1 & 0x0F
        mascarado = bool(b2 & 0x80)
        tamanho = b2 & 0x7F
        if tamanho == 126:
            tamanho = struct.unpack(">H", self._ler(2))[0]
        elif tamanho == 127:
            tamanho = struct.unpack(">Q", self._ler(8))[0]
        chave = self._ler(4) if mascarado else b""
        dados = self._ler(tamanho)
        if mascarado:
            dados = bytes(b ^ chave[i % 4] for i, b in enumerate(dados))
        return fin, op, dados

    def _envia(self, op: int, dados: bytes) -> None:
        cab = bytearray([0x80 | op])
        tamanho = len(dados)
        if tamanho < 126:
            cab.append(0x80 | tamanho)
        elif tamanho < 65536:
            cab.append(0x80 | 126)
            cab += struct.pack(">H", tamanho)
        else:
            cab.append(0x80 | 127)
            cab += struct.pack(">Q", tamanho)
        chave = os.urandom(4)
        cab += chave
        cab += bytes(b ^ chave[i % 4] for i, b in enumerate(dados))
        self.sock.sendall(bytes(cab))

    def envia_texto(self, texto: str) -> None:
        self._envia(0x1, texto.encode("utf-8"))

    def mensagem(self, timeout: float) -> str:
        self.sock.settimeout(max(0.2, timeout))
        pedacos: list = []
        while True:
            fin, op, dados = self._frame()
            if op == 0x9:            # ping: responde e segue
                self._envia(0xA, dados)
                continue
            if op == 0xA:            # pong: ignora
                continue
            if op == 0x8:            # close
                raise OSError("o navegador fechou a conexao de depuracao")
            pedacos.append(dados)
            if fin:
                return b"".join(pedacos).decode("utf-8", "replace")


def _conecta(ws_url: str, timeout: float) -> _Ligacao:
    host, porta, caminho = _endereco(ws_url)
    sock = socket.create_connection((host, porta), timeout=timeout)
    chave = base64.b64encode(os.urandom(16)).decode("ascii")
    pedido = (f"GET {caminho} HTTP/1.1\r\nHost: {host}:{porta}\r\n"
              "Upgrade: websocket\r\nConnection: Upgrade\r\n"
              f"Sec-WebSocket-Key: {chave}\r\nSec-WebSocket-Version: 13\r\n"
              "\r\n")
    sock.sendall(pedido.encode("ascii"))
    cabecalho = b""
    while b"\r\n\r\n" not in cabecalho:
        pedaco = sock.recv(4096)
        if not pedaco:
            raise OSError("o navegador nao respondeu ao handshake")
        cabecalho += pedaco
        if len(cabecalho) > 65536:
            raise OSError("resposta grande demais do navegador")
    cabeca, resto = cabecalho.split(b"\r\n\r\n", 1)
    primeira = cabeca.split(b"\r\n", 1)[0].decode("latin-1", "replace")
    if " 101" not in primeira:
        raise OSError(f"o navegador recusou o WebSocket ({primeira[:80]})")
    return _Ligacao(sock, resto)


def executar(ws_url: str, metodo: str, params: dict | None = None,
             timeout: float = 8.0) -> dict:
    """Chama um metodo do CDP e devolve o 'result'. Levanta OSError se nao der."""
    ligacao = _conecta(ws_url, min(8.0, max(1.0, timeout)))
    sock = ligacao.sock
    try:
        ligacao.envia_texto(json.dumps({"id": 1, "method": metodo,
                                        "params": params or {}}))
        limite = time.time() + max(1.0, timeout)
        while True:
            restante = limite - time.time()
            if restante <= 0:
                raise OSError(f"o navegador nao respondeu a {metodo} a tempo")
            mensagem = json.loads(ligacao.mensagem(restante))
            if mensagem.get("id") != 1:
                continue        # evento do navegador: so ignora
            erro = mensagem.get("error")
            if erro:
                raise OSError(str(erro.get("message") or erro))
            resultado = mensagem.get("result")
            return resultado if isinstance(resultado, dict) else {}
    finally:
        try:
            sock.close()
        except OSError:
            pass


def pronta(ws_url: str, timeout: float = 10.0, graca: float = 2.5) -> bool:
    """Espera a pagina terminar de carregar (aba nova comeca em 'loading').

    ABA RECEM-ABERTA: pedir o texto no mesmo instante devolve vazio, porque o
    documento ainda nao foi montado. Aqui olhamos o readyState; se ele parar em
    'interactive' por mais que `graca` segundos, seguimos com o que houver.
    """
    inicio = time.time()
    interativo = 0.0
    while time.time() - inicio < max(0.5, timeout):
        try:
            resultado = executar(ws_url, "Runtime.evaluate", {
                "expression": "document.readyState",
                "returnByValue": True,
            }, timeout=4.0)
        except OSError:
            return False
        estado = str(((resultado.get("result") or {}).get("value")) or "")
        if estado == "complete":
            return True
        if estado == "interactive":
            interativo = interativo or time.time()
            if time.time() - interativo > graca:
                return True
        time.sleep(0.2)
    return False


def texto_da_aba(ws_url: str, timeout: float = 8.0) -> str:
    """Texto visivel da aba, do jeito que a pessoa ve (JS ja executado)."""
    resultado = executar(ws_url, "Runtime.evaluate", {
        "expression": "document.body ? document.body.innerText : ''",
        "returnByValue": True,
    }, timeout)
    valor = (resultado.get("result") or {}).get("value")
    return str(valor or "")


def print_da_aba(ws_url: str, timeout: float = 15.0) -> bytes | None:
    """PNG da aba (vai para o modelo como imagem, igual ao print do headless)."""
    resultado = executar(ws_url, "Page.captureScreenshot", {"format": "png"}, timeout)
    dado = resultado.get("data")
    if not dado:
        return None
    try:
        return base64.b64decode(dado)
    except (ValueError, TypeError):
        return None


def fechar(porta: int, timeout: float = 4.0) -> bool:
    """Fecha o navegador inteiro (Browser.close). True quando ele sai."""
    info = versao(porta) or {}
    ws_url = info.get("webSocketDebuggerUrl")
    if ws_url:
        try:
            executar(ws_url, "Browser.close", timeout=timeout)
        except OSError:
            pass  # o navegador fecha a conexao antes de responder: e o esperado
    limite = time.time() + 5.0
    while time.time() < limite:
        if not vivo(porta):
            return True
        time.sleep(0.2)
    return False

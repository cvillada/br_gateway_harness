"""ver_pagina: o TEO ABRE a pagina (arquivo ou URL) e OLHA o que apareceu.

Por que isso nao e o web_extract de sempre: o web_extract faz um pedido HTTP e le
o HTML cru. Em pagina que monta o conteudo por JavaScript (painel, X, aplicacao
local), o HTML cru nao tem o conteudo - e o modelo acaba improvisando script de
scraping, que quebra na proxima mudanca do site. Aqui quem renderiza e um
NAVEGADOR DE VERDADE: o DOM vem depois do JavaScript, os erros do console vem
junto e o desenho da tela vem como print (que o agent manda para a visao do
modelo, ver a linha "IMAGEM: ..." no resultado).

Serve para as duas coisas que o dono pediu, que sao a MESMA ferramenta:
- conferir o que o proprio TEO construiu (TDD de tela: gerou o HTML, abre, olha,
  conserta);
- ler uma pagina qualquer que a pessoa apontou.

Navegador, por sistema (sem dependencia Python nova):
- Linux/Windows: Chrome/Chromium/Edge/Brave (headless).
- macOS: os mesmos se existirem; senao SAFARI - e ai ele abre uma janela visivel
  e o print vem da tela (o Safari nao tem modo headless). Sem console nesse caso.
"""

from __future__ import annotations

import html as htmllib
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ..config import BGH_HOME
from .guard import STOPPED_NOTE, stopped
from .websearch import html_para_texto

SPEC = {
    "type": "function",
    "function": {
        "name": "ver_pagina",
        "description": (
            "Abre uma pagina num navegador de verdade (arquivo .html local ou endereco "
            "http/https) e devolve o texto que aparece DEPOIS do JavaScript rodar, os "
            "erros do console e um print da tela. Use para conferir o que voce mesmo "
            "construiu ou para ler pagina que monta o conteudo por JavaScript."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origem": {
                    "type": "string",
                    "description": ("Caminho completo de um arquivo .html (ex.: "
                                    "/home/ana/site/index.html) ou endereco http(s). "
                                    "No macOS, use \"aba\" para ler a aba ABERTA do "
                                    "Safari (pagina que a pessoa ja logou e deixou "
                                    "aberta)"),
                },
                "largura": {"type": "integer",
                            "description": "Largura da janela em pixels (padrao 1280)"},
                "altura": {"type": "integer",
                           "description": "Altura da janela em pixels (padrao 800)"},
                "espera": {"type": "integer",
                           "description": ("Segundos para o JavaScript rodar antes de "
                                           "olhar (padrao 3, maximo 15)")},
            },
            "required": ["origem"],
        },
    },
}

SPEC_ABRIR = {
    "type": "function",
    "function": {
        "name": "abrir_navegador",
        "description": (
            "Abre uma janela do navegador DO TEO para a PESSOA fazer login num site "
            "(so quando ela pede para o TEO ler uma pagina que exige conta). O TEO nao "
            "digita senha e nao clica em entrar: quem entra e a pessoa. Depois de "
            "entrar ela FECHA a janela e o ver_pagina le o site logado pelo texto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string",
                        "description": "Endereco http(s) do site onde a pessoa vai entrar"},
            },
            "required": ["url"],
        },
    },
}

MAX_TEXTO = 8000
TIMEOUT_S = 60          # navegador travado nao pode segurar o turno para sempre
MAX_ESPERA_S = 15
MAX_ERROS = 8
# Mensagens do PROPRIO Chrome no canal de console (nao sao erro da pagina).
RUIDO_CONSOLE = (
    "Automatic fallback to software WebGL",
    "No available adapters",
    "Not signed in with the identity provider",
    "GroupMarkerNotSet",
    "GPU stall due to ReadPixels",
    "Third-party cookie will be blocked",
)

# Nomes no PATH (Linux e macOS).
_CANDIDATOS_PATH = (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "microsoft-edge", "microsoft-edge-stable", "brave-browser",
)
# Caminhos fixos do Windows (o Edge esta em qualquer Windows 10/11).
_CAMINHOS_WIN = (
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)

# Formato do log do Chrome: [pid:pid:data:INFO:CONSOLE:11] "mensagem", source: ...
_CONSOLE = re.compile(r":(?:INFO|WARNING|ERROR):CONSOLE:(\d+)\] (.*)$", re.M)
# Falha de rede/carga do navegador ("Page load failed: net::ERR_...").
_FALHA = re.compile(r"(?:Page load failed|net::ERR_[A-Z_]+)[^\n]*")

# Cache do User-Agent por navegador: o UA do headless tem a palavra "HeadlessChrome"
# e site grande recusa (x.com devolvia erro de HTTP e a pagina vinha vazia).
_UA_CACHE: dict[str, str] = {}


def pasta() -> Path:
    """Prints das paginas (dentro de BGH_HOME, nunca no sistema)."""
    alvo = BGH_HOME / "paginas"
    alvo.mkdir(parents=True, exist_ok=True)
    return alvo


def perfil() -> Path:
    """Perfil PROPRIO do navegador do TEO (cookies de login ficam aqui).

    Fica separado do navegador da pessoa de proposito: o TEO nunca entra no perfil
    pessoal (que tem banco, e-mail, tudo). A pessoa loga UMA vez numa janela do
    TEO (`abrir_navegador`) e a partir dali o `ver_pagina` le a pagina logada como
    TEXTO, sem imagem e sem depender de a tela estar na frente.
    """
    alvo = BGH_HOME / "navegador" / "perfil"
    alvo.mkdir(parents=True, exist_ok=True)
    return alvo


def esquecer_logins() -> int:
    """Apaga o perfil (cookies, sessoes). Devolve quantos arquivos saiu.

    Usado pelo comando /site esquecer: quem decide apagar e a PESSOA, nunca o
    modelo - por isso e comando, nao ferramenta.
    """
    import shutil

    alvo = BGH_HOME / "navegador"
    if not alvo.exists():
        return 0
    total = sum(1 for item in alvo.rglob("*") if item.is_file())
    try:
        shutil.rmtree(alvo)
    except OSError:
        return 0
    return total


def perfil_em_uso(erro: str) -> bool:
    """True quando o Chrome recusou por ja existir outra janela com o perfil."""
    texto = (erro or "").lower()
    return ("processsingleton" in texto or "profile appears to be in use" in texto
            or "singletonlock" in texto)


def _url_usa_perfil(url: str) -> bool:
    """Perfil so vale para site (http/https). Arquivo local (TDD) fica de fora:
    nao precisa de cookie e nao corre risco de travar com a janela de login aberta.
    """
    return url.lower().startswith(("http://", "https://"))


def abrir_janela(url: str) -> tuple[bool, str]:
    """Abre uma janela VISIVEL do navegador do TEO para a pessoa fazer login.

    Nao espera nada: o turno continua. Quem digita a senha e a pessoa, na janela
    do TEO - o agente nao ve, nao digita e nao automatiza login.
    """
    exe, nome = achar_navegador()
    if not exe:
        if nome == "safari":
            try:
                subprocess.Popen(["open", "-a", "Safari", url], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, ("safari: janela aberta no Safari (sem perfil proprio do "
                              "TEO neste sistema - o login NAO fica guardado).")
            except OSError as exc:
                return False, f"nao consegui abrir o Safari: {exc}"
        return False, "nao achei navegador nesta maquina (Chrome, Chromium, Edge ou Brave)"
    comando = [
        exe,
        f"--user-data-dir={perfil()}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--window-size=1280,900",
        url,
    ]
    try:
        subprocess.Popen(comando, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                            if os.name == "nt" else {}))
    except OSError as exc:
        return False, f"nao consegui abrir o navegador: {exc}"
    return True, nome


def limpar(horas: float = 24.0) -> int:
    """Apaga prints velhos (aba fechada sem sair nao deixa arquivo para tras)."""
    removidos = 0
    limite = time.time() - max(0.0, horas) * 3600
    try:
        for item in pasta().iterdir():
            if not item.is_file():
                continue
            try:
                if item.stat().st_mtime >= limite:
                    continue
                item.unlink()
                removidos += 1
            except OSError:
                continue
    except OSError:
        return removidos
    return removidos


def achar_navegador() -> tuple[str, str]:
    """(comando, nome). ('', 'safari') no macOS sem Chrome/Edge; ('', '') sem nada."""
    for nome in _CANDIDATOS_PATH:
        achado = shutil.which(nome)
        if achado:
            return achado, nome
    if os.name == "nt":
        for caminho in _CAMINHOS_WIN:
            if Path(caminho).is_file():
                return caminho, Path(caminho).stem
    if sys.platform == "darwin":
        # Safari nao tem headless: abre janela e o print vem da tela.
        if Path("/Applications/Safari.app").is_dir():
            return "", "safari"
    return "", ""


def _user_agent(exe: str) -> str:
    """UA de Chrome normal (o headless se identifica e muitos sites bloqueiam)."""
    chave = f"{sys.platform}|{exe}"
    if chave in _UA_CACHE:
        return _UA_CACHE[chave]
    versao = "131.0.0.0"
    try:
        saida = subprocess.run([exe, "--version"], capture_output=True, text=True,
                               timeout=10)
        achado = re.search(r"(\d+\.\d+\.\d+\.\d+)", saida.stdout or "")
        if achado:
            versao = achado.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    if os.name == "nt":
        plataforma = "Windows NT 10.0; Win64; x64"
    elif sys.platform == "darwin":
        plataforma = "Macintosh; Intel Mac OS X 10_15_7"
    else:
        plataforma = "X11; Linux x86_64"
    ua = (f"Mozilla/5.0 ({plataforma}) AppleWebKit/537.36 (KHTML, like Gecko) "
          f"Chrome/{versao} Safari/537.36")
    _UA_CACHE[chave] = ua
    return ua


def _falha_carga(stderr: str) -> str | None:
    """Codigo do erro de carga (ex.: net::ERR_HTTP_RESPONSE_CODE_FAILURE)."""
    achado = _FALHA.search(stderr or "")
    if not achado:
        return None
    codigo = re.search(r"net::[A-Z_]+", achado.group(0))
    return codigo.group(0) if codigo else achado.group(0).strip()


def _clamp(valor: int, minimo: int, maximo: int) -> int:
    return max(minimo, min(int(valor), maximo))


def run_abrir(args: dict, ctx) -> str:
    """Ferramenta abrir_navegador: janela visivel para a pessoa entrar no site."""
    if stopped(ctx):
        return STOPPED_NOTE
    url = str(args.get("url") or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return "ERRO: informe o endereco do site comecando com http:// ou https://."
    ok, detalhe = abrir_janela(url)
    if not ok:
        return f"ERRO: {detalhe}"
    linhas = [
        f"JANELA ABERTA: {url}",
        f"NAVEGADOR: {detalhe}",
        "",
        "PASSOS PARA A PESSOA (repita isso em palavras simples):",
        "1. Na janela que abriu, entre no site com a conta dela. A senha e dela - "
        "eu nao vejo, nao digito e nao guardo. Se o site oferecer \"manter "
        "conectado\", ela deve marcar (cookie de sessao sozinho nao fica guardado).",
        "2. Quando aparecer a pagina que ela quer mostrar, FECHAR a janela.",
        "3. Depois pedir de novo para eu ler a pagina, que eu leio o texto ja logado.",
        "   (No macOS, com Safari: nao precisa fechar nada - eu leio a ABA aberta, "
        "com ver_pagina origem=aba.)",
        "",
        "Enquanto a janela estiver aberta eu NAO consigo ler o site (o perfil fica "
        "em uso) - o passo 2 e obrigatorio.",
    ]
    if detalhe.startswith("safari"):
        linhas.append("ATENCAO: neste Mac o login NAO fica guardado no perfil do TEO.")
    return "\n".join(linhas)


def _alvo(origem: str) -> tuple[str, Path | None, str | None]:
    """(url para o navegador, arquivo local ou None, erro em texto)."""
    bruto = (origem or "").strip()
    if not bruto:
        return "", None, "ERRO: informe o caminho do arquivo ou o endereco http(s)."
    if bruto.lower().startswith(("http://", "https://", "file://")):
        return bruto, None, None
    alvo = Path(os.path.expanduser(bruto))
    if not alvo.is_absolute():
        return "", None, (f"ERRO: caminho incompleto ({bruto}). Use o caminho inteiro, "
                          f"por exemplo /home/ana/pagina.html.")
    if not alvo.is_file():
        return "", None, f"ERRO: nao achei o arquivo {alvo}."
    return alvo.resolve().as_uri(), alvo, None


def _matar(proc: subprocess.Popen) -> None:
    """Mata o navegador E os filhos (Chrome cria processos auxiliares)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        else:
            os.killpg(os.getpgid(proc.pid), 9)
    except (OSError, subprocess.SubprocessError):
        try:
            proc.kill()
        except OSError:
            pass


def _chromium(exe: str, url: str, png: Path, largura: int, altura: int,
              espera_ms: int) -> tuple[str, str, str | None]:
    """Roda o navegador headless. Devolve (html, stderr, erro)."""
    comando = [
        exe,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-scrollbars",
        "--no-pdf-header-footer",
        # Sem isso o console da pagina nao aparece no stderr.
        "--enable-logging=stderr",
        "--v=1",
        # Site grande recusa o UA padrao do headless ("HeadlessChrome").
        f"--user-agent={_user_agent(exe)}",
        "--disable-blink-features=AutomationControlled",
        f"--window-size={largura},{altura}",
        # Deixa o JavaScript rodar (timers/await) antes de fotografar.
        f"--virtual-time-budget={espera_ms}",
        "--dump-dom",
        f"--screenshot={png}",
    ]
    if _url_usa_perfil(url):
        # Perfil proprio do TEO: site que a pessoa logou em abrir_navegador abre
        # aqui JA logado (cookie guardado no disco). Arquivo local nao usa perfil.
        comando.append(f"--user-data-dir={perfil()}")
    comando.append(url)
    try:
        proc = subprocess.Popen(
            comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,
            **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
               if os.name == "nt" else {}),
        )
    except OSError as exc:
        return "", "", f"ERRO ao abrir o navegador ({exe}): {exc}"
    try:
        saida, erro = proc.communicate(timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        _matar(proc)
        try:
            saida, erro = proc.communicate(timeout=10)
        except (subprocess.TimeoutExpired, ValueError):
            saida, erro = "", ""
        return saida or "", erro or "", (f"ERRO: a pagina passou de {TIMEOUT_S}s "
                                         f"para carregar; fechei o navegador.")
    return saida or "", erro or "", None


def _erros_console(stderr: str) -> list[str]:
    """Mensagens do console da pagina, ja em forma de linha para o modelo."""
    saida: list[str] = []
    for achado in _CONSOLE.finditer(stderr or ""):
        texto = achado.group(2)
        texto = re.sub(r'", source: .*$', "", texto).strip().strip('"').strip()
        if not texto:
            continue
        # "in" e nao startswith: o Chrome as vezes prefixa a mensagem ("[]...").
        if any(ruido in texto for ruido in RUIDO_CONSOLE):
            continue
        linha = f"- linha {achado.group(1)}: {texto}"
        if linha not in saida:
            saida.append(linha)
        if len(saida) >= MAX_ERROS:
            break
    return saida


def _titulo(html: str) -> str:
    achado = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    return htmllib.unescape(achado.group(1)).strip() if achado else ""


def _montar_texto(origem: str, navegador: str, titulo: str, texto: str,
                  erros: list[str], png: Path | None, nota: str = "") -> str:
    """Resultado em texto: o modelo le isso e o print vai como imagem."""
    linhas = [f"PAGINA ABERTA: {origem}", f"NAVEGADOR: {navegador}"]
    if titulo:
        linhas.append(f"TITULO: {titulo}")
    if nota:
        linhas.append(f"OBSERVACAO: {nota}")
    if erros:
        linhas.append(f"ERROS DO CONSOLE ({len(erros)}):")
        linhas.extend(erros)
    else:
        linhas.append("ERROS DO CONSOLE: nenhum")
    if not (texto or "").strip():
        linhas.append("TEXTO: a pagina ficou VAZIA depois do JavaScript "
                      "(nenhum texto visivel para ler).")
    else:
        cortado = len(texto) > MAX_TEXTO
        linhas.append("TEXTO DA PAGINA" + (" (comeco)" if cortado else "") + ":")
        linhas.append(texto[:MAX_TEXTO])
    if png is not None and Path(png).is_file():
        linhas.append(f"IMAGEM: {png}")
    return "\n".join(linhas)


def _montar(origem: str, navegador: str, html: str, erros: list[str],
            png: Path | None, nota: str = "") -> str:
    """Versao do navegador headless: entra HTML, sai texto."""
    return _montar_texto(origem, navegador, _titulo(html), html_para_texto(html),
                         erros, png, nota=nota)


# --- macOS: Safari (o navegador que a pessoa JA usa, ja logada) --------------
def _e_mac() -> bool:
    return sys.platform == "darwin"


# "current tab of front window" = a aba que esta na frente, em qualquer janela.
ABA_URL = ["-e", 'tell application "Safari" to get URL of current tab of front window']
ABA_TITULO = ["-e", 'tell application "Safari" to get name of current tab of front window']
# Sem "Permitir JavaScript de eventos da Apple" (menu Desenvolvedor) isto falha.
ABA_TEXTO = ["-e", ('tell application "Safari" to do JavaScript '
                    '"document.body.innerText" in current tab of front window')]


def _osascript(partes: list[str], timeout: int = 20) -> tuple[str, str]:
    """(stdout, stderr) do osascript. Nunca levanta: vazio quando nao deu."""
    try:
        saida = subprocess.run(["osascript", *partes], capture_output=True,
                               text=True, timeout=timeout)
        return (saida.stdout or "").strip(), (saida.stderr or "").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return "", str(exc)


def _safari_sem_js(erro: str) -> bool:
    """O erro de 'JavaScript de eventos da Apple' desligado."""
    texto = (erro or "").lower()
    return "javascript" in texto or "not allowed" in texto


def _safari_abrir(url: str) -> None:
    _osascript(["-e", 'tell application "Safari" to activate',
                "-e", "on run argv", "-e", 'tell application "Safari"',
                "-e", "open location (item 1 of argv)", "-e", "end tell",
                "-e", "end run", "--", url])


def _safari_print(png: Path) -> None:
    """Print da REGIAO da janela do Safari (sem capturar o resto da tela)."""
    medidas, _ = _osascript(
        ["-e", 'tell application "Safari" to get bounds of front window'])
    numeros = [int(n) for n in re.findall(r"-?\d+", medidas)[:4]]
    if len(numeros) != 4:
        return
    x1, y1, x2, y2 = numeros
    largura, altura = max(1, x2 - x1), max(1, y2 - y1)
    try:
        subprocess.run(["screencapture", "-x", "-o", "-R",
                        f"{x1},{y1},{largura},{altura}", str(png)],
                       capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        pass


def _safari(origem: str, url: str, png: Path, espera_s: int, alvo: Path | None,
            ler_aba: bool = False) -> str:
    """macOS: le a PAGINA RENDERIZADA da aba do Safari (a sessao da pessoa).

    O Safari nao tem headless - e nao precisa: a aba esta aberta no navegador em
    que a pessoa JA ESTA LOGADA. Pedindo `document.body.innerText` por AppleScript,
    o TEO le o texto montado pelo JavaScript e o conteudo de site com login, sem
    copiar cookie nenhum e sem perfil separado.

    Requisito unico: Safari > Preferencias > Avancado > "Mostrar recursos de
    desenvolvimento" e, no menu Desenvolvedor, "Permitir JavaScript de eventos da
    Apple". Sem isso, o texto cai para o HTML servido e o resultado DIZ o porque.
    """
    if not ler_aba:
        _safari_abrir(url)
        time.sleep(max(1, espera_s))

    aba_url, _ = _osascript(ABA_URL)
    titulo, _ = _osascript(ABA_TITULO)
    texto, erro_js = _osascript(ABA_TEXTO)
    nota = ("Safari do Mac: o texto vem da aba ABERTA (do jeito que a pessoa ve, "
            "inclusive site logado). O console do Safari nao e lido.")
    if erro_js or not (texto or "").strip():
        texto = ""
        if alvo is not None:
            try:
                texto = html_para_texto(alvo.read_text(encoding="utf-8",
                                                      errors="replace"))
            except OSError:
                texto = ""
        elif url:
            try:
                import requests

                resp = requests.get(url, timeout=20,
                                    headers={"User-Agent":
                                             "Mozilla/5.0 (Macintosh) TEO"})
                if "html" in resp.headers.get("content-type", ""):
                    texto = html_para_texto(resp.text)
            except Exception:  # noqa: BLE001 - sem rede o print ainda vale
                texto = ""
        if _safari_sem_js(erro_js):
            nota = ("Para eu ler a PAGINA montada (e nao o HTML cru), ligue no "
                    "Safari: Preferencias > Avancado > 'Mostrar recursos de "
                    "desenvolvimento' e depois, no menu Desenvolvedor, 'Permitir "
                    "JavaScript de eventos da Apple'. Sem isso o texto vem do HTML "
                    "servido.")
        elif aba_url and not ler_aba:
            nota = f"Safari leu a aba aberta ({aba_url})."
    _safari_print(png)
    return _montar_texto(origem, "Safari (aba aberta)", titulo, texto, [],
                         png if Path(png).is_file() else None, nota=nota)


def run(args: dict, ctx) -> str:
    origem = str(args.get("origem") or "").strip()
    if not origem:
        return "ERRO: informe o caminho do arquivo ou o endereco http(s)."
    if stopped(ctx):
        return STOPPED_NOTE
    if origem.lower() in ("aba", "aba aberta", "aba do safari"):
        if not _e_mac():
            return ("ERRO: 'aba' e do macOS com Safari (le a aba que a pessoa deixou "
                    "aberta, ja logada). No Linux/Windows use ver_tela, ou informe o "
                    "caminho/URL.")
        try:
            limpar(horas=24)
        except OSError:
            pass
        png = pasta() / f"pagina-{secrets.token_hex(4)}.png"
        espera = _clamp(int(args.get("espera") or 1), 0, MAX_ESPERA_S)
        return _safari(origem, "", png, espera, None, ler_aba=True)
    url, alvo, erro = _alvo(origem)
    if erro:
        return erro
    if alvo is not None:
        # Mesmo guarda dos arquivos: caminho sensivel pede licenca antes de abrir.
        ok, bloqueado = ctx.gate.path_ok(str(alvo))
        if not ok:
            return bloqueado or "BLOQUEADO: o usuario nao autorizou abrir esse arquivo."

    largura = _clamp(int(args.get("largura") or 1280), 320, 2400)
    altura = _clamp(int(args.get("altura") or 800), 240, 1600)
    espera = _clamp(int(args.get("espera") or 3), 0, MAX_ESPERA_S)

    try:
        limpar(horas=24)
    except OSError:
        pass
    png = pasta() / f"pagina-{secrets.token_hex(4)}.png"

    exe, nome = achar_navegador()
    if exe:
        html, stderr, erro_exec = _chromium(exe, url, png, largura, altura,
                                           espera * 1000)
        if erro_exec:
            return erro_exec
        if perfil_em_uso(stderr) and not (html or "").strip():
            return ("ERRO: a janela do navegador do TEO esta aberta com o login. "
                    "Peca para a pessoa FECHAR essa janela e depois abrir a pagina de "
                    "novo - enquanto ela estiver aberta eu nao consigo ler o site.")
        falha = _falha_carga(stderr)
        if falha and not (html or "").strip():
            return (f"ERRO: o navegador nao conseguiu carregar {origem} ({falha}). "
                    "Site que exige login/sessao nao abre assim - nesse caso mande um "
                    "print da tela ou use o web_extract para o texto publico.")
        return _montar(origem, nome, html, _erros_console(stderr), png)
    if nome == "safari":
        return _safari(origem, url, png, espera, alvo)
    return ("ERRO: nao achei navegador nesta maquina (Chrome, Chromium, Edge ou "
            "Brave). Sem navegador eu nao consigo abrir a pagina desenhada - o "
            "web_extract continua servindo para pagina simples.")

"""Atualizacao do TEO: compara a versao em uso com a release 'latest' do GitHub.

Fluxo (chamado pelo comando /atualizar no chat):
1. fetch_latest() le https://api.github.com/repos/<repo>/releases/latest (publico, sem chave).
2. update_needed() compara por numeros (v0.2.7 > v0.2.6).
3. apply_update() instala o .whl da propria release com a receita oficial dos
   instaladores: pip install --no-deps --force-reinstall <url>.
Nada roda sem a licenca dada na tela (o comando pergunta antes).
"""

import re
import shutil
import subprocess
import sys

REPO = "cvillada/br_gateway_harness"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"

import requests  # modulo do projeto; testes trocam este atributo por um fake


def version_tuple(ver: str) -> tuple:
    """'v0.2.7' -> (0, 2, 7); qualquer texto vira numeros comparaveis."""
    nums = re.findall(r"\d+", str(ver or ""))
    return tuple(int(x) for x in nums[:3]) or (0,)


def update_needed(current: str, latest: str) -> bool:
    return version_tuple(latest) > version_tuple(current)


def fetch_latest(timeout_s: int = 15) -> tuple[dict | None, str]:
    """(info, erro). info = {'version': tag, 'wheel_url': url_do_whl}."""
    try:
        resp = requests.get(API_LATEST, timeout=timeout_s,
                            headers={"User-Agent": "TEO-agent"})
    except Exception as exc:  # noqa: BLE001 - rede fora e caso comum
        return None, f"nao consegui falar com o GitHub ({type(exc).__name__})"
    if resp.status_code != 200:
        return None, f"o GitHub respondeu {resp.status_code} (limite de consulta? tente mais tarde)"
    try:
        data = resp.json()
    except ValueError:
        return None, "a pagina de releases do GitHub veio em formato inesperado"
    tag = str(data.get("tag_name") or "")
    wheel_url = ""
    for asset in data.get("assets", []) or []:
        if str(asset.get("name") or "").endswith(".whl"):
            wheel_url = str(asset.get("browser_download_url") or "")
            break
    if not tag:
        return None, "a release mais recente nao informou o numero da versao"
    if not wheel_url:
        return None, "a release mais recente nao traz o pacote .whl para instalar"
    return {"version": tag, "wheel_url": wheel_url}, ""


def python_bin() -> str:
    """Interpretador que recebe o pip (em build congelado/PyInstaller, cai no python3 do sistema)."""
    if getattr(sys, "frozen", False):
        found = shutil.which("python3") or shutil.which("python")
        return found or ""
    return sys.executable


def apply_update(wheel_url: str, timeout_s: int = 900) -> tuple[bool, str]:
    """Instala o wheel novo. Devolve (ok, mensagem para a tela)."""
    py = python_bin()
    if not py:
        return False, ("esta instalacao roda como arquivo unico (executavel) e nao tem um "
                       "Python para receber a atualizacao - use o INSTALAR_TEO.bat novament")
    cmd = [py, "-m", "pip", "install", "--no-deps", "--force-reinstall", wheel_url]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return False, "a baixada parou no meio (demorou demais); tente de novo ou rode o INSTALAR_TEO.bat"
    except OSError as exc:
        return False, f"nao consegui rodar o instalador interno: {exc}"
    if proc.returncode == 0:
        return True, "instalacao concluida"
    tail = ((proc.stderr or proc.stdout or "").strip().splitlines() or ["sem detalhe"])[-1]
    return False, f"o pip nao completou (codigo {proc.returncode}): {tail[:160]}"

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

from bgh import i18n
from bgh.i18n import t


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
        return None, t("upd.net", tipo=type(exc).__name__)
    if resp.status_code != 200:
        return None, t("upd.status", code=resp.status_code)
    try:
        data = resp.json()
    except ValueError:
        return None, t("upd.bad_json")
    tag = str(data.get("tag_name") or "")
    wheel_url = ""
    for asset in data.get("assets", []) or []:
        if str(asset.get("name") or "").endswith(".whl"):
            wheel_url = str(asset.get("browser_download_url") or "")
            break
    if not tag:
        return None, t("upd.no_tag")
    if not wheel_url:
        return None, t("upd.no_wheel")
    return {"version": tag, "wheel_url": wheel_url}, ""


def startup_check(current_version: str, timeout_s: int = 8) -> tuple[str, str | None]:
    """Checagem unica da ABERTURA: (texto para a tela, versao nova ou None).

    Regras (pedido do dono do projeto):
    - so fala quando ha o que dizer: versao nova -> avisa e ensina o /atualizar;
      sem internet -> avisa que nao deu para conferir (o TEO segue funcionando);
      GitHub fora/limite -> avisa em uma linha, sem assustar;
      ja atualizado -> silencio total.
    - timeout curto: abertura nao pode esperar rede (o trabalho real comeca em
      segundo plano, na linha da tela ja desenhada).
    """
    try:
        resp = requests.get(API_LATEST, timeout=timeout_s,
                            headers={"User-Agent": "TEO-agent"})
    except Exception:  # noqa: BLE001 - rede fora e caso comum, nao defeito
        return t("upd.start_offline"), None
    if resp.status_code != 200:
        return t("upd.start_unavailable", code=resp.status_code), None
    try:
        data = resp.json()
    except ValueError:
        return t("upd.start_unavailable", code=resp.status_code), None
    tag = str(data.get("tag_name") or "")
    if not tag or not update_needed(current_version, tag):
        return "", None
    return t("upd.start_new", version=tag, update=i18n.cmd("update")), tag


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
        return False, t("upd.frozen")
    # --ignore-installed: instalacao antiga sem RECORD nao pode travar a atualizacao
    # (o pip responde "uninstall-no-record-file"; aqui ele so sobrescreve).
    cmd = [py, "-m", "pip", "install", "--no-deps", "--ignore-installed",
           "--force-reinstall", wheel_url]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return False, t("upd.timeout")
    except OSError as exc:
        return False, t("upd.oserr", erro=exc)
    if proc.returncode == 0:
        return True, t("upd.done")
    tail = ((proc.stderr or proc.stdout or "").strip().splitlines()
            or [t("upd.no_detail")])[-1]
    return False, t("upd.pip_fail", code=proc.returncode, tail=tail[:160])

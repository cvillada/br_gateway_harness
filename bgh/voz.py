"""Fala do sistema operacional: o TEO le a resposta em voz alta.

Acessibilidade pedida pelo usuario (publico do TEO e crianca, idoso e pessoa com
deficiencia visual): quem nao consegue ler a tela ouve a resposta.

Regra de ouro: NADA de dependencia nova. Quem fala e o proprio sistema:

  Linux    spd-say (speech-dispatcher) -> reserva espeak-ng / espeak
  Windows  PowerShell + System.Speech (SAPI, offline, sem instalar nada;
           voz pt-BR se o pacote de idioma estiver na maquina)
  macOS    say (com a voz pt_BR instalada, se houver)

Como funciona no dia a dia:
  - `/voz` liga e desliga (fica gravado no config.json);
  - ligado, cada resposta do modelo e lida em voz alta;
  - CTRL+C/ESC (a mesma tecla que para o modelo) cala a voz na hora;
  - mandar uma pergunta nova tambem cala a leitura anterior;
  - a fala roda em processo separado, numa thread: a tela nunca espera a voz.

O texto passa por limpar_para_fala() antes: markdown, cercas de codigo, ANSI e
linhas de tabela sairiam como chiado no ouvido. Resposta gigante e cortada em
MAX_CHARS (ler 20 mil caracteres em voz alta e castigo, nao ajuda).
"""

import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading

from . import i18n

MAX_CHARS = 1400          # ~1 minuto e meio de fala; o resto fica na tela
_RATE_ESPEAK = "150"      # palavras por minuto (padrao 175; mais devagar p/ idoso)
_RATE_SAY = "160"
_RATE_SPD = "-10"         # spd-say usa -100..100

# idioma da tela -> (spd-say, espeak, locale do say)
_LOCALES = {
    "pt": ("pt-BR", "pt-br", "pt_BR"),
    "en": ("en-US", "en-us", "en_US"),
    "es": ("es-ES", "es", "es_ES"),
}

_LOCK = threading.Lock()
_PROC = None          # fala em andamento (para cortar)
_TMP = None           # arquivo temporario da fala em andamento
_BACKEND = None       # None = ainda nao descoberto; "" = nenhum nesta maquina
_CAIU = False         # spd-say ja falhou uma vez (nao repetir a queda)

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_FENCE = re.compile(r"```.*?```", re.S)
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MARCA = re.compile(r"^[#>\-\*\+]+\s*")


def limpar_para_fala(texto: str) -> str:
    """Texto da tela -> texto que se pode ouvir.

    Tira cerca de codigo, marca de markdown, ANSI, barra de tabela e linha de
    separador (====, ----); junta tudo numa frase so. Corta em MAX_CHARS para a
    leitura nao virar castigo.
    """
    bruto = _FENCE.sub(" ", str(texto or ""))
    bruto = _ANSI.sub("", bruto)
    bruto = _LINK.sub(r"\1", bruto)
    bruto = bruto.replace("`", " ").replace("**", "").replace("__", "")
    pedacos = []
    for linha in bruto.splitlines():
        limpa = linha.strip()
        if not limpa:
            continue
        if set(limpa) <= set("=-_*#|~+ "):     # separador/tabela vazia
            continue
        limpa = _MARCA.sub("", limpa).replace("|", " ")
        if limpa.strip():
            pedacos.append(limpa.strip())
    fala = re.sub(r"\s+", " ", " ".join(pedacos)).strip()
    if len(fala) > MAX_CHARS:
        corte = fala[:MAX_CHARS]
        espaco = corte.rfind(" ")
        if espaco > 0:
            corte = corte[:espaco]
        fala = corte.rstrip(" ,.;:") + " " + i18n.t("voz.truncada")
    return fala


def _escolhe_backend(sistema: str) -> str:
    """Qual programa do sistema fala nesta maquina ('' quando nao ha nenhum)."""
    nome = (sistema or "").lower()
    if nome.startswith("win"):
        if shutil.which("powershell") or shutil.which("pwsh"):
            return "powershell"
        return ""
    if nome.startswith("darwin") or nome.startswith("mac"):
        return "say" if shutil.which("say") else ""
    for candidato in ("spd-say", "espeak-ng", "espeak"):
        if shutil.which(candidato):
            return candidato
    return ""


def backend(sistema: str | None = None) -> str:
    """Backend desta execucao (descoberto uma vez e guardado)."""
    global _BACKEND
    if sistema is not None:            # caminho dos testes: sem cache
        return _escolhe_backend(sistema)
    if _BACKEND is None:
        _BACKEND = _escolhe_backend(platform.system())
    return _BACKEND


def disponivel() -> bool:
    return bool(backend())


def _locale(lang: str | None) -> tuple[str, str, str]:
    return _LOCALES.get((lang or "pt").lower()[:2], _LOCALES["pt"])


def _voz_mac(lang: str) -> list[str]:
    """Voz do `say` no idioma da tela; sem voz do idioma, usa a padrao."""
    try:
        lista = subprocess.run(["say", "-v", "?"], capture_output=True, text=True,
                               timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    alvo = _locale(lang)[2].lower()
    for linha in lista.splitlines():
        # "Luciana              pt_BR    # Most people recognize me by my voice."
        achado = re.match(r"^(.*?)\s{2,}([a-zA-Z]{2}_[a-zA-Z]{2})\s{2,}#", linha)
        if achado and achado.group(2).lower() == alvo:
            return ["-v", achado.group(1).strip()]
    return []


def _argv(texto: str, lang: str, nome: str, tmp: str | None) -> list[str]:
    """Programa + argumentos de uma fala (sem shell: nada de aspas quebradas)."""
    spd, esp, _mac = _locale(lang)
    if nome == "powershell":
        exe = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
        # O texto vai por ARQUIVO (variavel de ambiente): acento, aspas e quebra
        # de linha sobrevivem sem escapar nada dentro do PowerShell.
        script = ("Add-Type -AssemblyName System.Speech; "
                  "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  "$s.Rate = -1; "
                  "$s.Speak([IO.File]::ReadAllText($env:TEO_FALA, "
                  "[Text.Encoding]::UTF8))")
        return [exe, "-NoProfile", "-Command", script]
    if nome == "say":
        if not tmp:
            return []
        return ["say", "-r", _RATE_SAY] + _voz_mac(lang) + ["-f", tmp]
    if nome == "spd-say":
        # -w: o cliente ESPERA a fala terminar. Sem isso ele entrega o texto ao
        # speech-dispatcher e morre na hora - e nao haveria processo para cortar.
        return ["spd-say", "-l", spd, "-r", _RATE_SPD, "-w", "--", texto]
    if nome in ("espeak-ng", "espeak"):
        return [nome, "-v", esp, "-s", _RATE_ESPEAK, "--", texto]
    return []


def _arquivo_temporario(texto: str) -> str | None:
    """Grava a fala em disco (UTF-8) para os backends que leem arquivo."""
    try:
        from .config import SCRATCH_DIR

        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        fd, caminho = tempfile.mkstemp(prefix="fala_", suffix=".txt", dir=str(SCRATCH_DIR))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
        return caminho
    except OSError:
        return None


def _cancela_spd() -> None:
    """Cancela a fala e a fila do speech-dispatcher (-C), sem tocar em erro."""
    try:
        subprocess.run(["spd-say", "-C"], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=3)
    except (OSError, subprocess.SubprocessError):
        pass


def _apaga(caminho: str | None) -> None:
    if not caminho:
        return
    try:
        os.unlink(caminho)
    except OSError:
        pass


def _vigia(proc, tmp: str | None, texto: str, lang: str) -> None:
    """Espera a fala terminar, limpa o arquivo e, se o Linux recusou, troca a voz."""
    global _PROC, _TMP, _BACKEND, _CAIU
    try:
        codigo = proc.wait()
    except (OSError, subprocess.SubprocessError):
        codigo = 0
    finally:
        _apaga(tmp)
    with _LOCK:
        if _PROC is proc:
            _PROC, _TMP = None, None
    if codigo and not getattr(proc, "teo_calada", False) and _BACKEND == "spd-say" and not _CAIU:
        # spd-say existe mas o servico de fala nao responde: na proxima vai direto
        # no espeak-ng, que e autonomo. Uma tentativa so, para nao repetir em loop.
        _CAIU = True
        reserva = shutil.which("espeak-ng") or shutil.which("espeak")
        if reserva:
            with _LOCK:
                _BACKEND = "espeak-ng" if reserva.endswith("espeak-ng") else "espeak"
            falar(texto, lang)


def falar(texto: str, lang: str | None = None) -> bool:
    """Le o texto em voz alta. Devolve False quando nao ha voz no sistema.

    Nunca levanta excecao: fala e enfeite, a conversa e o que importa.
    """
    limpo = limpar_para_fala(texto)
    if not limpo:
        return False
    nome = backend()
    if not nome:
        return False
    idioma = (lang or i18n.get_lang() or "pt")[:2]
    parar()                              # uma voz por vez: a nova cala a anterior
    tmp = None
    env = None
    if nome in ("powershell", "say"):
        tmp = _arquivo_temporario(limpo)
        if tmp is None:
            return False
        if nome == "powershell":
            env = dict(os.environ, TEO_FALA=tmp)
    argv = _argv(limpo, idioma, nome, tmp)
    if not argv:
        _apaga(tmp)
        return False
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, env=env)
    except OSError:
        _apaga(tmp)
        return False
    global _PROC, _TMP
    with _LOCK:
        _PROC, _TMP = proc, tmp
    threading.Thread(target=_vigia, args=(proc, tmp, limpo, idioma), daemon=True).start()
    return True


def falando() -> bool:
    """Tem voz saindo agora? Usado pelo ESC, que cala sem apagar o que foi digitado."""
    with _LOCK:
        proc = _PROC
    return proc is not None and proc.poll() is None


def parar() -> None:
    """Cala a fala em andamento (CTRL+C/ESC, pergunta nova, saida do TEO)."""
    global _PROC, _TMP
    with _LOCK:
        proc, _PROC, _TMP = _PROC, None, None
    if proc is not None and proc.poll() is None and backend() == "spd-say":
        # Quem fala e o speech-dispatcher, nao o cliente: matar o cliente nao
        # calaria nada. O comando de cancelar e do proprio spd-say (-C).
        _cancela_spd()
    if proc is None or proc.poll() is not None:
        return
    try:
        # Marca a calada como PROPOSITAL: senao a saida com erro do processo
        # pareceria defeito do spd-say e trocaria a voz sem motivo.
        setattr(proc, "teo_calada", True)   # pyright: atributo dinamico ok aqui
        proc.terminate()
        try:
            proc.wait(timeout=0.6)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.kill()          # spd-say as vezes ignora o terminate
        try:
            proc.wait(timeout=0.6)
        except subprocess.TimeoutExpired:
            pass
    except OSError:
        pass


def nome_do_backend() -> str:
    """Nome amigavel da voz em uso (para a mensagem do /voz)."""
    nome = backend()
    return {"spd-say": "speech-dispatcher", "espeak-ng": "espeak-ng",
            "espeak": "espeak", "powershell": "Windows (System.Speech)",
            "say": "macOS (say)"}.get(nome, "")

"""Ditado: escrever falando - reconhecimento de fala LOCAL, sem internet.

Acessibilidade: quem tem dificuldade para digitar escreve falando,
nos MESMOS tres idiomas do `/lingua` (pt, en, es), e o ditado segue o idioma da
tela - trocou com `/lingua`, o reconhecedor troca junto.

Decisoes que sustentam isso:
- MOTOR: vosk (Kaldi). Roda offline na CPU, sem chave, sem nuvem, sem conta. O som
  nao sai do computador - importa para crianca e idoso.
- MODELO por idioma (pequeno, ~40-50 MB), baixado UMA vez na primeira vez que a
  pessoa dita e guardado em `~/.bgh/models/vosk/`. A wheel do TEO nao carrega
  modelo junto (o pacote de instalacao nao pode engordar 150 MB).
- AUDIO: `sounddevice` (wheels nos tres sistemas) e, no Linux, `arecord` como
  reserva quando a lib PortAudio nao esta na maquina.
- FORMATO: 16 kHz, mono, 16 bits - o que o vosk espera e o que o microfone
  entrega. Sem conversao no caminho, sem dependencia de ffmpeg para ditar.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import wave
import zipfile
from pathlib import Path
from urllib.request import urlopen

from .config import BGH_HOME

TAXA = 16000                 # Hz do modelo (nao mudar sem trocar de modelo)
MAX_SEGUNDOS = 25            # teto de uma fala (evita travar com microfone aberto)
BLOCO = 4000                 # ~0,25s por leitura do microfone

MODELOS_DIR = BGH_HOME / "models" / "vosk"

# idioma da tela -> (nome do modelo, endereco oficial)
IDIOMAS = {
    "pt": ("vosk-model-small-pt-0.3",
           "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"),
    "en": ("vosk-model-small-en-us-0.15",
           "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"),
    "es": ("vosk-model-small-es-0.42",
           "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"),
}


# tamanho aproximado do download, por idioma (para avisar antes de baixar)
TAMANHO_MB = {"pt": 46, "en": 41, "es": 40}


def tamanho_mb(lang: str | None) -> int:
    return TAMANHO_MB.get((lang or "pt").lower()[:2], TAMANHO_MB["pt"])


def idiomas() -> tuple[str, ...]:
    """Os tres idiomas que o ditado entende (os mesmos da tela)."""
    return tuple(IDIOMAS)


def modelo_do_idioma(lang: str | None) -> tuple[str, str]:
    """(nome, url) do modelo do idioma; idioma desconhecido cai no portugues."""
    return IDIOMAS.get((lang or "pt").lower()[:2], IDIOMAS["pt"])


def modelo_dir(lang: str | None) -> Path:
    return MODELOS_DIR / modelo_do_idioma(lang)[0]


def tem_modelo(lang: str | None) -> bool:
    pasta = modelo_dir(lang)
    return pasta.is_dir() and any(pasta.iterdir())


def tem_motor() -> bool:
    """O pacote de reconhecimento esta instalado nesta maquina?"""
    try:
        import vosk  # noqa: F401
    except ImportError:
        return False
    return True


def _baixar_arquivo(url: str, destino: Path, ao_progresso=None) -> bool:
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(url, timeout=60) as resposta, open(destino, "wb") as fh:
            total = int(resposta.headers.get("Content-Length") or 0)
            baixado = 0
            while True:
                pedaco = resposta.read(262144)
                if not pedaco:
                    break
                fh.write(pedaco)
                baixado += len(pedaco)
                if ao_progresso and total:
                    ao_progresso(min(99, int(baixado * 100 / total)))
        return True
    except Exception:  # noqa: BLE001 - rede pode faltar; quem chama avisa na tela
        return False


def baixar_modelo(lang: str | None, ao_progresso=None) -> tuple[bool, str]:
    """Baixa e descompacta o modelo do idioma. Devolve (ok, detalhe)."""
    nome, url = modelo_do_idioma(lang)
    if tem_modelo(lang):
        return (True, str(modelo_dir(lang)))
    zip_path = MODELOS_DIR / f"{nome}.zip"
    if not _baixar_arquivo(url, zip_path, ao_progresso):
        return (False, "sem_conexao")
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(MODELOS_DIR)
    except Exception:  # noqa: BLE001 - zip corrompido/parcial: apaga e tenta depois
        try:
            zip_path.unlink()
        except OSError:
            pass
        return (False, "zip_ruim")
    try:
        zip_path.unlink()
    except OSError:
        pass
    if not tem_modelo(lang):
        return (False, "zip_ruim")
    return (True, str(modelo_dir(lang)))


_RECONHECEDORES: dict = {}


def _reconhecedor(lang: str | None):
    """KaldiRecognizer pronto (fica em cache: carregar o modelo leva ~1s)."""
    chave = (lang or "pt")[:2]
    if chave in _RECONHECEDORES:
        return _RECONHECEDORES[chave]
    from vosk import KaldiRecognizer, Model

    try:
        # O Kaldi escreve LOG direto no terminal (stderr do processo) ao carregar o
        # modelo: num app para crianca/idoso isso vira lixo no meio da conversa.
        import vosk

        vosk.SetLogLevel(-1)
    except Exception:  # noqa: BLE001 - versao sem SetLogLevel: segue com log
        pass
    modelo = Model(str(modelo_dir(chave)))
    rec = KaldiRecognizer(modelo, TAXA)
    rec.SetWords(False)
    _RECONHECEDORES[chave] = rec
    return rec


def transcrever(pcm: bytes, lang: str | None = None) -> str:
    """PCM 16 kHz mono 16 bits -> texto. Devolve '' quando nao entendeu nada."""
    try:
        rec = _reconhecedor(lang)
        rec.Reset()
    except Exception:  # noqa: BLE001 - modelo ausente/pacote faltando
        return ""
    texto = []
    for inicio in range(0, len(pcm), BLOCO):
        pedaco = pcm[inicio:inicio + BLOCO]
        if rec.AcceptWaveform(pedaco):
            import json

            falado = json.loads(rec.Result()).get("text", "").strip()
            if falado:
                texto.append(falado)
    import json

    final = json.loads(rec.FinalResult()).get("text", "").strip()
    if final:
        texto.append(final)
    return " ".join(texto).strip()


# ---------------------------------------------------------------------------
# Audio do microfone
# ---------------------------------------------------------------------------
def _ler_microfone(max_segundos: int = MAX_SEGUNDOS, rec=None, parar=None) -> bytes:
    """Grava do microfone ate a pessoa parar de falar (silencio) ou estourar o teto.

    'rec' e o reconhecedor do idioma, usado so para saber QUANDO a fala acabou
    (o Kaldi marca o fim da frase); o texto sai por transcrever().
    """
    limite = int(TAXA * max_segundos)
    coletado = bytearray()
    try:
        import sounddevice as sd
    except Exception:  # noqa: BLE001 - sem PortAudio: tenta o arecord do Linux
        return _ler_arecord(max_segundos)

    try:
        with sd.RawInputStream(samplerate=TAXA, blocksize=BLOCO, dtype="int16",
                               channels=1) as entrada:
            while len(coletado) < limite * 2:
                if parar is not None and parar():
                    break      # CTRL+C/ESC durante a escuta: para na hora
                dados, _overflow = entrada.read(BLOCO)
                pedaco = bytes(dados)
                coletado.extend(pedaco)
                if rec is not None and rec.AcceptWaveform(pedaco):
                    break      # a pessoa parou: o Kaldi marcou o fim da fala
    except Exception:  # noqa: BLE001 - microfone ocupado/negado
        return b""
    return bytes(coletado)


def _ler_arecord(max_segundos: int, ao_vivo=None) -> bytes:
    """Reserva do Linux: arecord cru (16 kHz mono 16 bits) por tempo fixo."""
    binario = shutil.which("arecord")
    if not binario:
        return b""
    pasta = BGH_HOME / "scratch"
    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError:
        pasta = Path(tempfile.gettempdir())
    tmp = Path(tempfile.mkdtemp(prefix="ditar_", dir=str(pasta)))
    destino = tmp / "fala.raw"
    try:
        subprocess.run([binario, "-q", "-f", "S16_LE", "-r", str(TAXA), "-c", "1",
                        "-t", "raw", "-d", str(max_segundos), str(destino)],
                       timeout=max_segundos + 10, check=False,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return destino.read_bytes() if destino.exists() else b""
    except (OSError, subprocess.SubprocessError):
        return b""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def escutar(lang: str | None = None, max_segundos: int = MAX_SEGUNDOS,
            fonte: bytes | None = None, parar=None) -> str:
    """Escuta o microfone (ou usa 'fonte', nos testes) e devolve o texto.

    'parar' e um callable: quando devolve True (CTRL+C/ESC), a escuta termina na
    hora em vez de esperar o silencio ou o teto de segundos.
    """
    if fonte is not None:
        return transcrever(fonte, lang)
    try:
        rec = _reconhecedor(lang)
    except Exception:  # noqa: BLE001 - modelo ausente: grava sem detectar o fim
        rec = None
    pcm = _ler_microfone(max_segundos, rec, parar)
    if not pcm:
        return ""
    return transcrever(pcm, lang)


def wav_para_pcm(caminho: str) -> bytes:
    """WAV do disco -> PCM cru de 16 kHz mono (usado nos testes e por anexo .wav)."""
    try:
        with wave.open(str(caminho), "rb") as fh:
            if fh.getframerate() != TAXA or fh.getnchannels() != 1:
                return b""     # fora do formato: quem chamou converte antes
            return fh.readframes(fh.getnframes())
    except (OSError, wave.Error):
        return b""

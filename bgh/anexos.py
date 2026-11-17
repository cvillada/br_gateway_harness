"""Anexos: o arquivo que a pessoa entrega ao TEO (clipe da tela ou '@' no terminal).

Duas coisas moram aqui, e so elas:

1. TIPOS e limites. A tela do navegador recebe arquivo de fora: a lista de
   extensoes aceitas e FECHADA (como a dos documentos citados) e o tamanho tem
   teto. Tipo fora da lista nao entra, nem no disco.

2. LEITURA. Texto, PDF, Word, Excel e PowerPoint viram texto puro para o modelo
   ler. Imagem NAO passa por aqui: ela vai como imagem (visao) pelo agent.py.

Sem dependencia nova para Office: .docx/.xlsx/.pptx sao ZIP com XML dentro, e
zipfile + ElementTree da biblioteca padrao bastam. PDF e o unico que precisa de
pypdf - e quando ele nao esta instalado a resposta e uma frase clara, nunca um
traceback na tela de uma crianca.
"""

from __future__ import annotations

import os
import re
import secrets
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .config import BGH_HOME
from .i18n import cmd, t

# Extensao -> categoria. A lista e FECHADA de proposito: e a mesma que o
# navegador oferece no clipe (accept) e a mesma que o servidor aceita.
TIPOS = {
    ".png": "imagem",
    ".jpg": "imagem",
    ".jpeg": "imagem",
    ".webp": "imagem",
    ".gif": "imagem",
    ".bmp": "imagem",
    ".pdf": "pdf",
    ".docx": "office",
    ".xlsx": "office",
    ".pptx": "office",
    ".doc": "office",
    ".xls": "office",
    ".ppt": "office",
    ".odt": "office",
    ".ods": "office",
    ".odp": "office",
    ".rtf": "office",
    ".txt": "texto",
    ".md": "texto",
    ".csv": "texto",
    ".tsv": "texto",
    ".json": "texto",
    ".log": "texto",
    ".xml": "texto",
    ".yaml": "texto",
    ".yml": "texto",
    ".ini": "texto",
    ".py": "texto",
    ".js": "texto",
    ".ts": "texto",
    ".html": "texto",
    ".css": "texto",
    ".sql": "texto",
    ".sh": "texto",
}

# Teto por arquivo. 15 MB cobre foto de celular e contrato em PDF; acima disso o
# pedido ao modelo cresce mais do que o contexto aguenta.
MAX_BYTES = 15 * 1024 * 1024
# Teto de anexos por turno (a tela tambem limita, mas quem manda no limite e aqui).
MAX_ANEXOS = 5
# Texto por arquivo e texto somado no turno: o modelo precisa caber no contexto
# que sobra depois do system prompt e das ferramentas.
MAX_TEXTO = 20000
MAX_TEXTO_TOTAL = 40000

NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def categoria(ext: str) -> str | None:
    """'imagem', 'texto', 'pdf', 'office' - ou None se o tipo nao e aceito."""
    ext = (ext or "").strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    return TIPOS.get(ext)


def classificar(caminho) -> str | None:
    return categoria(Path(str(caminho)).suffix)


def pasta() -> Path:
    """Pasta dos anexos desta sessao (dentro de BGH_HOME, nunca no sistema)."""
    alvo = BGH_HOME / "anexos"
    alvo.mkdir(parents=True, exist_ok=True)
    return alvo


def nome_seguro(nome: str) -> str:
    """So o nome do arquivo, sem caminho, sem controle e sem tamanho absurdo."""
    base = os.path.basename(str(nome or "").replace("\\", "/")).strip()
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)
    base = base.replace("/", "-").replace("\\", "-")
    if len(base) > 120:
        raiz = Path(base)
        base = raiz.stem[:100] + raiz.suffix[:15]
    return base or "arquivo"


def aceitos() -> list[str]:
    """Extensoes aceitas, na ordem da lista (a tela usa no accept do clipe)."""
    return list(TIPOS)


def salvar(nome: str, dados: bytes) -> tuple[str, Path | None, str | None]:
    """Grava o anexo recebido da tela. Devolve (id, caminho, erro em texto)."""
    nome = nome_seguro(nome)
    cat = categoria(Path(nome).suffix)
    if cat is None:
        return "", None, t("anexo.tipo", ext=Path(nome).suffix or "?")
    if not dados:
        return "", None, t("anexo.vazio", nome=nome)
    if len(dados) > MAX_BYTES:
        return "", None, t("anexo.grande", nome=nome, size=_mb(len(dados)),
                           max=_mb(MAX_BYTES))
    ident = secrets.token_hex(8)
    alvo = pasta() / f"{ident}{Path(nome).suffix.lower()}"
    try:
        alvo.write_bytes(dados)
    except OSError:
        return "", None, t("anexo.falhou", nome=nome)
    return ident, alvo, None


def caminho_de(ident: str, ext: str = "") -> Path | None:
    """Caminho do anexo pelo id (so dentro da pasta de anexos: id vem da tela)."""
    if not re.fullmatch(r"[0-9a-f]{6,32}", str(ident or "")):
        return None
    casa = pasta()
    if ext:
        alvo = casa / f"{ident}{ext.lower()}"
        return alvo if alvo.is_file() else None
    for item in casa.glob(ident + ".*"):
        if item.is_file():
            return item
    return None


def _mb(n: int) -> str:
    return f"{max(0, int(n)) / (1024 * 1024):.1f}".replace(".", ",")


def ler_texto(caminho, limite: int = MAX_TEXTO) -> tuple[str, str | None, bool]:
    """Texto do anexo para o modelo. (texto, erro, cortado)."""
    alvo = Path(str(caminho))
    if not alvo.is_file():
        return "", t("anexo.nao_achei", nome=alvo.name), False
    cat = categoria(alvo.suffix)
    if cat is None:
        return "", t("anexo.tipo", ext=alvo.suffix or "?"), False
    if cat == "imagem":
        return "", t("anexo.imagem", nome=alvo.name), False
    try:
        if cat == "texto":
            texto = _texto_puro(alvo)
        elif cat == "pdf":
            falta = pdf_sem_biblioteca(alvo)
            if falta:
                return "", falta, False
            texto = _pdf(alvo)
        elif alvo.suffix.lower() in (".docx", ".xlsx", ".pptx"):
            texto = {".docx": _docx, ".xlsx": _xlsx, ".pptx": _pptx}[
                alvo.suffix.lower()](alvo)
        else:
            # .doc/.xls/.ppt/.odt antigos sao OLE, nao ZIP: sem extrator aqui.
            return "", t("anexo.antigo", ext=alvo.suffix), False
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError, ValueError):
        return "", t("anexo.falhou", nome=alvo.name), False
    texto = (texto or "").strip()
    if not texto:
        return "", t("anexo.sem_texto", nome=alvo.name), False
    cortado = len(texto) > limite
    return (texto[:limite], None, cortado)


def _texto_puro(alvo: Path) -> str:
    return alvo.read_text(encoding="utf-8", errors="replace")


def _docx(alvo: Path) -> str:
    with zipfile.ZipFile(alvo) as z:
        xml = z.read("word/document.xml")
    raiz = ElementTree.fromstring(xml)
    linhas: list[str] = []
    for par in raiz.iter(NS_W + "p"):
        pedacos: list[str] = []
        for no in par.iter():
            if no.tag == NS_W + "t" and no.text:
                pedacos.append(no.text)
            elif no.tag == NS_W + "tab":
                pedacos.append("\t")
            elif no.tag == NS_W + "br":
                pedacos.append("\n")
        linha = "".join(pedacos).strip()
        if linha:
            linhas.append(linha)
    return "\n".join(linhas)


def _xlsx(alvo: Path) -> str:
    with zipfile.ZipFile(alvo) as z:
        nomes = z.namelist()
        compartilhados: list[str] = []
        if "xl/sharedStrings.xml" in nomes:
            raiz = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            for si in raiz.iter(NS_S + "si"):
                compartilhados.append("".join(n.text or "" for n in si.iter(NS_S + "t")))
        folhas = sorted(n for n in nomes
                        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        saida: list[str] = []
        for i, folha in enumerate(folhas, start=1):
            raiz = ElementTree.fromstring(z.read(folha))
            saida.append(f"[planilha {i}]")
            for linha in raiz.iter(NS_S + "row"):
                celulas: list[str] = []
                for celula in linha.iter(NS_S + "c"):
                    valor = celula.find(NS_S + "v")
                    if valor is not None and valor.text is not None:
                        texto = valor.text
                        if celula.get("t") == "s":
                            try:
                                texto = compartilhados[int(texto)]
                            except (ValueError, IndexError):
                                pass
                    else:
                        dentro = celula.find(NS_S + "is")
                        texto = ("".join(n.text or "" for n in dentro.iter(NS_S + "t"))
                                 if dentro is not None else "")
                    celulas.append((texto or "").strip())
                linha_txt = "\t".join(celulas).rstrip()
                if linha_txt.strip():
                    saida.append(linha_txt)
                if len(saida) > 500:      # planilha gigante: o comeco ja responde
                    saida.append("...")
                    return "\n".join(saida)
    return "\n".join(saida)


def _pptx(alvo: Path) -> str:
    with zipfile.ZipFile(alvo) as z:
        slides = [n for n in z.namelist()
                  if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        slides.sort(key=lambda n: int(re.sub(r"\D", "", Path(n).stem) or 0))
        saida: list[str] = []
        for i, slide in enumerate(slides, start=1):
            raiz = ElementTree.fromstring(z.read(slide))
            textos = [no.text.strip() for no in raiz.iter(NS_A + "t") if no.text]
            if textos:
                saida.append(f"[slide {i}]")
                saida.extend(textos)
    return "\n".join(saida)


def _pdf(alvo: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:      # sem a biblioteca: frase clara e caminho de saida
        return ""
    leitor = PdfReader(str(alvo))
    if getattr(leitor, "is_encrypted", False):
        return ""
    partes: list[str] = []
    for pagina in leitor.pages:
        texto = pagina.extract_text() or ""
        if texto.strip():
            partes.append(texto.strip())
        if sum(len(p) for p in partes) > MAX_TEXTO:
            break
    return "\n\n".join(partes)


def pdf_sem_biblioteca(caminho) -> str | None:
    """Frase de erro quando o PDF nao pode ser lido por falta de pypdf."""
    if categoria(Path(str(caminho)).suffix) != "pdf":
        return None
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return t("anexo.pdf_lib", atualizar=cmd("update"))
    return None


def limpar(horas: float = 24.0, manter: tuple[str, ...] = ()) -> int:
    """Apaga anexos velhos (fim da sessao nao pode deixar arquivo do usuario)."""
    removidos = 0
    limite = time.time() - max(0.0, horas) * 3600
    try:
        for item in pasta().iterdir():
            if not item.is_file() or str(item) in manter:
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

"""Documentos do usuario: gera .md ou .html em ~/Documentos."""

import html as htmllib
import os
import re
from pathlib import Path
from typing import Any

from bgh.config import ensure_dirs

SPEC = {
    "type": "function",
    "function": {
        "name": "make_document",
        "description": (
            "Cria um documento para o usuario (relatorio, carta, guia, planilha) e "
            "salva na pasta de Documentos. Formatos: md e html saem prontos; docx, "
            "xlsx e pdf precisam da biblioteca instalada - se faltar, a resposta diz "
            "qual instalar (instalar_pacote) e pede para chamar de novo. Devolve o "
            "caminho completo do arquivo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo do documento"},
                "content_markdown": {"type": "string", "description": "Conteudo em markdown simples"},
                "fmt": {"type": "string", "enum": ["md", "html", "docx", "xlsx", "pdf"],
                        "description": ("Formato (padrao md). Para xlsx escreva o "
                                        "conteudo como tabela markdown (| item | valor |)")},
                "path": {"type": "string", "description": "Opcional: caminho explicito de saida"},
            },
            "required": ["title", "content_markdown"],
        },
    },
}


def documents_dir() -> Path:
    """Pasta de documentos no padrao pt-BR (XDG); nunca na raiz do home."""
    env = os.environ.get("XDG_DOCUMENTS_DIR")
    docs = Path(env) if env else Path.home() / "Documentos"
    docs.mkdir(parents=True, exist_ok=True)
    return docs


def _slug(title: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9 -]+", "", title).strip()
    clean = re.sub(r"\s+", "-", clean.lower())
    return clean or "documento"


def md_to_html(title: str, md: str) -> str:
    """Conversor minimo markdown -> html (titulos, listas, negrito, code blocks)."""
    out: list[str] = []
    in_code = False
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw_line in md.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre>")
                in_code = True
            continue
        if in_code:
            out.append(htmllib.escape(raw_line))
            continue
        stripped = line.strip()
        if not stripped:
            close_list()
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{htmllib.escape(m.group(2))}</h{level}>")
            continue
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue
        close_list()
        out.append(f"<p>{_inline(stripped)}</p>")
    close_list()
    if in_code:
        out.append("</pre>")
    body = "\n".join(out)
    return (
        "<!DOCTYPE html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{htmllib.escape(title)}</title>\n"
        "<style>body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "pre{background:#f4f4f4;padding:0.8rem;overflow-x:auto}</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>\n"
    )


def _inline(text: str) -> str:
    escaped = htmllib.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<i>\1</i>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


# Formatos: md/html saem do proprio TEO; docx/xlsx/pdf dependem de biblioteca
# instalada NA HORA (instalar_pacote, com licenca) - decisao do dono: o pacote do
# TEO nao engorda por causa de tres bibliotecas que muita gente nunca usa.
FORMATOS = ("md", "html", "docx", "xlsx", "pdf")
_DEPENDENCIAS = {
    "docx": ("docx", "python-docx", "criar documento .docx"),
    "xlsx": ("openpyxl", "openpyxl", "criar planilha .xlsx"),
    "pdf": ("reportlab", "reportlab", "criar arquivo PDF"),
}


def _falta_dependencia(fmt: str) -> str | None:
    """Mensagem que ensina o CAMINHO quando a biblioteca do formato nao esta.

    O texto vai para o modelo, nao para a tela: ele tem a ferramenta
    `instalar_pacote` (que pede licenca a pessoa) e depois chama make_document de
    novo. Nada e' instalado sozinho por aqui.
    """
    dep = _DEPENDENCIAS.get(fmt)
    if dep is None:
        return None
    modulo, pacote, motivo = dep
    try:
        __import__(modulo)
    except ImportError:
        return (f"ERRO: para gerar {fmt} falta a biblioteca {pacote}. Instale com "
                f'instalar_pacote(pacote="{pacote}", motivo="{motivo}") e chame '
                f"make_document de novo.")
    return None


def _blocos(md: str) -> list[tuple[str, Any]]:
    """Markdown simples -> blocos: ('h1'..'h4'|'li'|'p'|'code', texto) ou ('tabela', linhas).

    Tabela e' uma sequencia de linhas com '|'; as linhas de tracos do markdown
    (|---|) saem. Serve para docx (tabela de verdade) e para pdf (linha a linha).
    """
    saida: list[tuple[str, Any]] = []
    tabela: list[list[str]] = []
    in_code = False

    def fecha_tabela() -> None:
        nonlocal tabela
        if tabela:
            saida.append(("tabela", tabela))
            tabela = []

    for bruta in str(md or "").splitlines():
        linha = bruta.rstrip()
        if linha.strip().startswith("```"):
            fecha_tabela()
            in_code = not in_code
            continue
        if in_code:
            saida.append(("code", linha))
            continue
        texto = linha.strip()
        if texto.startswith("|"):
            celulas = [c.strip() for c in texto.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in celulas if c):
                continue
            tabela.append(celulas)
            continue
        fecha_tabela()
        if not texto:
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", texto)
        if m:
            saida.append(("h" + str(len(m.group(1))), m.group(2)))
            continue
        m = re.match(r"^[-*]\s+(.*)$", texto)
        if m:
            saida.append(("li", m.group(1)))
            continue
        saida.append(("p", texto))
    fecha_tabela()
    return saida


def _linhas_tabela(md: str) -> list[list[str]]:
    """Todas as linhas de tabela do markdown, na ordem (para a planilha)."""
    linhas: list[list[str]] = []
    for tipo, dado in _blocos(md):
        if tipo == "tabela":
            linhas.extend(dado)   # type: ignore[arg-type]
    return linhas


def _escrever_docx(alvo: Path, titulo: str, md: str) -> None:
    from docx import Document  # type: ignore[import-not-found]

    doc = Document()
    doc.add_heading(titulo or "Documento", level=0)
    for tipo, dado in _blocos(md):
        if tipo == "tabela":
            linhas = dado  # type: ignore[assignment]
            largura = max(len(linha) for linha in linhas)
            tabela = doc.add_table(rows=len(linhas), cols=largura)
            tabela.style = "Table Grid"
            for i, linha in enumerate(linhas):
                for j, celula in enumerate(linha):
                    tabela.cell(i, j).text = celula
            continue
        if tipo.startswith("h"):
            doc.add_heading(str(dado), level=int(tipo[1]))
        elif tipo == "li":
            doc.add_paragraph(str(dado), style="List Bullet")
        elif tipo == "code":
            doc.add_paragraph(str(dado), style="No Spacing")
        else:
            doc.add_paragraph(str(dado))
    doc.save(str(alvo))


def _escrever_xlsx(alvo: Path, titulo: str, md: str) -> None:
    from openpyxl import Workbook  # type: ignore[import-not-found]
    from openpyxl.styles import Font

    linhas = _linhas_tabela(md)
    wb = Workbook()
    ws = wb.active
    ws.title = (re.sub(r"[\\/*?:\[\]]", "", titulo).strip() or "Planilha")[:31]
    if not linhas:
        ws.append([titulo or "Planilha"])
    else:
        for linha in linhas:
            ws.append([c if c != "" else None for c in linha])
        for celula in ws[1]:          # primeira linha = cabecalho
            celula.font = Font(bold=True)
        for coluna in ws.columns:      # largura util (planilha legivel)
            largura = max(len(str(c.value or "")) for c in coluna)
            ws.column_dimensions[coluna[0].column_letter].width = min(60, largura + 2)
    wb.save(str(alvo))


def _escrever_pdf(alvo: Path, titulo: str, md: str) -> None:
    from reportlab.lib.pagesizes import A4  # type: ignore[import-not-found]
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    estilos = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(alvo), pagesize=A4, title=titulo or "Documento",
                            author="TEO")
    fluxo = [Paragraph(htmllib.escape(titulo or "Documento"), estilos["Title"]),
             Spacer(1, 10)]
    for tipo, dado in _blocos(md):
        if tipo == "tabela":
            for linha in dado:   # type: ignore[union-attr]
                fluxo.append(Paragraph(htmllib.escape(" | ".join(linha)),
                                       estilos["BodyText"]))
            continue
        if tipo.startswith("h"):
            chave = "Heading" + (tipo[1] if tipo[1] in "123" else "3")
            fluxo.append(Paragraph(htmllib.escape(str(dado)), estilos[chave]))
        elif tipo == "li":
            fluxo.append(Paragraph("&bull; " + htmllib.escape(str(dado)),
                                   estilos["BodyText"]))
        elif tipo == "code":
            fluxo.append(Paragraph(
                "<font face='Courier'>" + htmllib.escape(str(dado)) + "</font>",
                estilos["BodyText"]))
        else:
            fluxo.append(Paragraph(htmllib.escape(str(dado)), estilos["BodyText"]))
    doc.build(fluxo)


def make_document(args: dict, ctx) -> str:
    """Cria o documento no formato pedido (md/html sempre; docx/xlsx/pdf sob demanda)."""
    title = str(args.get("title", "")).strip()
    content = str(args.get("content_markdown", ""))
    fmt = str(args.get("fmt") or "md").lower()
    if fmt not in FORMATOS:
        return "ERRO: formato deve ser " + ", ".join(FORMATOS)
    falta = _falta_dependencia(fmt)
    if falta:
        return falta
    if args.get("path"):
        target = Path(os.path.expanduser(str(args["path"]))).resolve()
    else:
        ensure_dirs()
        target = documents_dir() / f"{_slug(title)}.{fmt}"
    ok, blocked = ctx.gate.path_ok(str(target))
    if not ok:
        return blocked
    if target.exists():
        approved_ok, blocked = ctx.gate.overwrite_ok(str(target))
        if not approved_ok:
            return blocked
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "html":
            target.write_text(md_to_html(title, content), encoding="utf-8")
        elif fmt == "docx":
            _escrever_docx(target, title, content)
        elif fmt == "xlsx":
            _escrever_xlsx(target, title, content)
        elif fmt == "pdf":
            _escrever_pdf(target, title, content)
        else:
            header = f"# {title}\n\n" if not content.lstrip().startswith("#") else ""
            target.write_text(header + content, encoding="utf-8")
    except OSError as exc:
        return f"ERRO ao criar documento: {exc}"
    return f"OK: documento salvo em {target}"



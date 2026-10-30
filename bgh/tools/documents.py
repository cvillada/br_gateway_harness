"""Documentos do usuario: gera .md ou .html em ~/Documentos."""

import html as htmllib
import os
import re
from pathlib import Path

from bgh.config import ensure_dirs

SPEC = {
    "type": "function",
    "function": {
        "name": "make_document",
        "description": (
            "Cria um documento para o usuario (relatorio, carta, guia) em Markdown ou HTML "
            "e salva na pasta de Documentos. Devolve o caminho completo do arquivo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titulo do documento"},
                "content_markdown": {"type": "string", "description": "Conteudo em markdown simples"},
                "fmt": {"type": "string", "enum": ["md", "html"], "description": "Formato (padrao md)"},
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


def make_document(args: dict, ctx) -> str:
    title = str(args.get("title", "")).strip()
    content = str(args.get("content_markdown", ""))
    fmt = (args.get("fmt") or "md").lower()
    if fmt not in ("md", "html"):
        return "ERRO: formato deve ser md ou html"
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
        else:
            header = f"# {title}\n\n" if not content.lstrip().startswith("#") else ""
            target.write_text(header + content, encoding="utf-8")
    except OSError as exc:
        return f"ERRO ao criar documento: {exc}"
    return f"OK: documento salvo em {target}"

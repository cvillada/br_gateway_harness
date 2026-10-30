"""Ferramentas de arquivo: leitura com numero de linha, escrita e busca de conteudo."""

import os
import re
from pathlib import Path

READ_SPEC = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Le um arquivo de texto e devolve linhas numeradas (NUM|conteudo).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do arquivo"},
                "offset": {"type": "integer", "description": "Linha inicial (1-indexado, padrao 1)"},
                "limit": {"type": "integer", "description": "Maximo de linhas (padrao 200)"},
            },
            "required": ["path"],
        },
    },
}

WRITE_SPEC = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Escreve conteudo em um arquivo (cria diretorios pai). Sobrescreve: se o arquivo ja existe, "
            "pede confirmacao ao usuario antes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do arquivo"},
                "content": {"type": "string", "description": "Conteudo completo a gravar"},
            },
            "required": ["path", "content"],
        },
    },
}

SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Busca expressao regular dentro dos arquivos de uma pasta (como rg).",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Expressao regular"},
                "path": {"type": "string", "description": "Pasta onde buscar (padrao: diretorio atual)"},
                "glob": {"type": "string", "description": "Filtro de nome, ex.: *.py"},
            },
            "required": ["pattern"],
        },
    },
}

SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".cache", "scratch"}


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def human_size(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    if n >= 1000:
        return f"{n / 1000:.1f} KB"
    return f"{n} B"


def list_dir(path: str, files_only: bool = False) -> str:
    """Listagem amigavel para os atalhos '/' e '@' do chat (pastas primeiro, ocultos de fora)."""
    root = _expand(path)
    if not root.is_dir():
        return f"Nao encontrei a pasta: {root}"
    try:
        entries = sorted(
            (e for e in os.scandir(root) if not e.name.startswith(".")),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        )
    except OSError as exc:
        return f"ERRO ao ler a pasta {root}: {exc}"
    lines: list[str] = []
    for e in entries:
        if e.is_dir():
            if files_only:
                continue
            lines.append(f"[DIR] {e.name}/")
        else:
            try:
                size = human_size(e.stat().st_size)
            except OSError:
                size = "?"
            lines.append(f"[ARQ] {e.name} ({size})")
        if len(lines) >= 60:
            lines.append("... (ainda tem mais; abra uma pasta mais especifica)")
            break
    body = "\n".join(lines) if lines else "(vazia)"
    modo = "so arquivos" if files_only else "pastas e arquivos"
    return f"pasta: {root}  [{modo}]\n{body}"


def read_file(args: dict, ctx) -> str:
    target = _expand(str(args.get("path", "")))
    if not target.is_file():
        return f"ERRO: arquivo nao encontrado: {target}"
    offset = max(int(args.get("offset") or 1), 1)
    limit = min(int(args.get("limit") or 200), 1000)
    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"ERRO ao ler {target}: {exc}"
    total = len(lines)
    chunk = lines[offset - 1 : offset - 1 + limit]
    out = [f"{i}|{line}" for i, line in enumerate(chunk, start=offset)]
    header = f"{target} ({total} linhas; mostrando {offset}-{offset + len(chunk) - 1})"
    body = "\n".join(out) if out else "(vazio)"
    result = header + "\n" + body
    if len(result) > 6000:
        return result[:6000] + "\n[truncado; continue com offset maior]"
    return result


def write_file(args: dict, ctx) -> str:
    target = _expand(str(args.get("path", "")))
    content = args.get("content")
    if content is None:
        return "ERRO: falta o conteudo"
    if target.exists() and target.is_dir():
        return f"ERRO: {target} e um diretorio"
    ok, blocked = ctx.gate.path_ok(str(target))
    if not ok:
        return blocked
    if target.exists():
        ok2, blocked2 = ctx.gate.overwrite_ok(str(target))
        if not ok2:
            return blocked2
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")
    except OSError as exc:
        return f"ERRO ao escrever {target}: {exc}"
    return f"OK: gravado {target} ({len(str(content))} chars)"


def search_files(args: dict, ctx) -> str:
    pattern = str(args.get("pattern", ""))
    if not pattern:
        return "ERRO: padrao vazio"
    root = _expand(str(args.get("path") or "."))
    glob_pat = args.get("glob")
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return f"ERRO: expressao regular invalida: {exc}"
    import fnmatch

    matches: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            if glob_pat and not fnmatch.fnmatch(fname, glob_pat):
                continue
            fpath = Path(dirpath) / fname
            try:
                if fpath.stat().st_size > 2_000_000:
                    continue
                for lineno, line in enumerate(
                    fpath.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
                ):
                    if rx.search(line):
                        matches.append(f"{fpath}:{lineno}:{line.strip()[:180]}")
                        if len(matches) >= 50:
                            return "\n".join(matches) + "\n(atingiu 50 resultados; refine a busca)"
            except (OSError, UnicodeDecodeError):
                continue
    if not matches:
        return f"Nenhum resultado para '{pattern}' em {root}"
    return "\n".join(matches)

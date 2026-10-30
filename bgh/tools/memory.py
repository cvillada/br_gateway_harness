"""Memoria persistente: SQLite em ~/.bgh/memory.db, com dois alvos como no Hermes.

- target=user : quem o usuario e' (nome, preferencias, nivel tecnico, como gosta de resposta)
- target=note : notas do Motor (hardware da maquina, caminhos, peculiaridades locais)

Fatos duraveis sobrevivem entre sessoes e entram no system prompt no inicio de
cada conversa (limite curto, alta sinalizacao). Senhas/cartoes NUNCA.
"""

import sqlite3
from datetime import datetime, timezone

from bgh.config import MEMORY_DB, ensure_dirs

SPEC = {
    "type": "function",
    "function": {
        "name": "memory",
        "description": (
            "Memoria permanente do Motor sobre este usuario/maquina. "
            "action=add grava um fato curto; action=search procura por palavra; action=list mostra as ultimas. "
            "target=user para preferencias e caracteristicas do usuario (ex.: 'prefere respostas curtas', "
            "'nao sabe usar terminal'); target=note para fatos da maquina. "
            "NUNCA guarde senhas, cartoes ou codigos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "search", "list"]},
                "target": {"type": "string", "enum": ["user", "note"], "description": "Padrao: note"},
                "text": {"type": "string", "description": "O fato a gravar (para add)"},
                "query": {"type": "string", "description": "Palavra-chave (para search)"},
            },
            "required": ["action"],
        },
    },
}


def _connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(str(MEMORY_DB))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memories ("
        "id INTEGER PRIMARY KEY, target TEXT NOT NULL DEFAULT 'note', "
        "text TEXT UNIQUE NOT NULL, created TEXT NOT NULL)"
    )
    cols = [row[1] for row in conn.execute("PRAGMA table_info(memories)")]
    if "target" not in cols:  # migracao de base antiga
        conn.execute("ALTER TABLE memories ADD COLUMN target TEXT NOT NULL DEFAULT 'note'")
    return conn


def add(text: str, target: str = "note") -> str:
    text = text.strip()
    if not text:
        return "ERRO: memoria vazia"
    if target not in ("user", "note"):
        target = "note"
    if len(text) > 500:
        text = text[:500]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO memories (target, text, created) VALUES (?, ?, ?)",
            (target, text, now),
        )
        if cur.rowcount == 0:
            return "Ja existia essa memoria (nothing added)."
    return f"Memoria gravada [{target}]: {text}"


def search(query: str) -> str:
    query = query.strip()
    if not query:
        return "ERRO: informe a palavra-chave"
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, target, text FROM memories WHERE text LIKE ? ORDER BY id DESC LIMIT 20",
            (f"%{query}%",),
        ).fetchall()
    if not rows:
        return f"Nenhuma memoria contendo '{query}'."
    return "\n".join(f"[{t}] {txt}" for _, t, txt in rows)


def list_recent(limit: int = 30) -> str:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT target, text FROM memories ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    if not rows:
        return "A memoria esta vazia."
    return "\n".join(f"- [{t}] {txt}" for t, txt in rows)


def load_lines(target: str, limit: int = 40, max_chars: int = 2500) -> list[str]:
    """Linhas para injetar no system prompt (mais recentes primeiro, ate o teto)."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT text FROM memories WHERE target = ? ORDER BY id DESC LIMIT ?",
                (target, limit),
            ).fetchall()
    except sqlite3.Error:
        return []
    out: list[str] = []
    total = 0
    for (text,) in rows:
        if total + len(text) > max_chars:
            break
        out.append(text)
        total += len(text)
    return out


def run(args: dict, ctx) -> str:
    action = args.get("action")
    if action == "add":
        return add(str(args.get("text", "")), str(args.get("target") or "note"))
    if action == "search":
        return search(str(args.get("query", "")))
    if action == "list":
        return list_recent()
    return "ERRO: action invalida (use add, search ou list)"

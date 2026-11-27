"""Memoria persistente: SQLite em ~/.bgh/memory.db, com dois alvos como no Hermes.

- target=user : quem o usuario e' (nome, preferencias, nivel tecnico, como gosta de resposta)
- target=note : notas do Motor (hardware da maquina, caminhos, peculiaridades locais)

Fatos duraveis sobrevivem entre sessoes e entram no system prompt no inicio de
cada conversa (limite curto, alta sinalizacao). Senhas/cartoes NUNCA.

Busca: indice FTS5 (bm25) quando o SQLite da maquina tem FTS5; sem ele, o LIKE de
sempre. `relevant()` alimenta o bloco que viaja junto da mensagem do usuario em
cada turno - e' assim que uma preferencia ANTIGA volta quando o assunto aparece,
mesmo depois de sair das 40 linhas do prompt.
"""

import re
import sqlite3
import time
from datetime import datetime, timezone

from bgh.config import MEMORY_DB, ensure_dirs
from bgh.i18n import t

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

# Indice de busca: None = ainda nao tentou; True/False = o SQLite desta maquina
# tem (ou nao) o modulo FTS5. Sem FTS5 tudo continua funcionando pelo LIKE.
_FTS: dict = {"ok": None}

# Momento do ultimo 'add': a captura automatica nao repete o que o modelo ja gravou.
_ULTIMO_ADD = {"quando": 0.0}

# Frases que denunciam um pedido PERMANENTE ("meu nome e...", "prefiro...").
# De proposito nao entram "sempre"/"nunca" soltos: aparecem em pedido de uma vez
# so' e virariam memoria falsa.
PADROES_CAPTURA = (
    r"\bmeu nome (?:e|eh)\b", r"\bme chame de\b", r"\bme chama de\b",
    r"\bde agora em diante\b", r"\bprefiro\b", r"\bpreferiria\b",
    r"\bnao gosto de\b", r"\bnao gosto quando\b",
    r"\btenho \d{1,3} anos\b", r"\bmoro (?:em|no|na)\b",
    r"\bsou alergic[oa]\b", r"\bmeu aniversario\b",
    r"\bsempre que (?:eu|voce|vc)\b", r"\bnunca (?:faca|use|mostre|apague)\b",
)

# Palavras que nao ajudam a achar nada na memoria (pedido comum, nao assunto).
_PARADAS = frozenset((
    "para", "pelo", "pela", "como", "qual", "quais", "onde", "quando", "porque",
    "quero", "queria", "preciso", "pode", "poderia", "faca", "fazer", "faz",
    "voce", "voces", "esta", "estao", "isso", "aquilo", "esse", "essa", "este",
    "com", "sem", "mais", "menos", "muito", "pouco", "agora", "depois", "antes",
    "the", "and", "that", "this", "with", "what", "when", "where", "your",
    "please", "could", "would", "should", "make", "need", "want",
))


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
    _garantir_indice(conn)
    return conn


def _garantir_indice(conn: sqlite3.Connection) -> bool:
    """Cria o indice FTS5 e mantem em dia com gatilhos (uma vez por base).

    Base antiga ja tem linhas: o 'rebuild' popula o indice na primeira vez. Se o
    SQLite da maquina nao tem FTS5, devolve False e a busca segue no LIKE.
    """
    if _FTS["ok"] is False:
        return False
    try:
        if _FTS["ok"] is None:
            ja_existe = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'memories_fts'"
            ).fetchone()
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5("
                "text, content='memories', content_rowid='id')"
            )
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN "
                "INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text); END")
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN "
                "INSERT INTO memories_fts(memories_fts, rowid, text) "
                "VALUES ('delete', old.id, old.text); END")
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN "
                "INSERT INTO memories_fts(memories_fts, rowid, text) "
                "VALUES ('delete', old.id, old.text); "
                "INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text); END")
            if not ja_existe:
                conn.execute("INSERT INTO memories_fts(memories_fts) VALUES ('rebuild')")
            _FTS["ok"] = True
        return True
    except sqlite3.Error:
        _FTS["ok"] = False
        return False


def _consulta_fts(texto: str) -> str:
    """Pedido em linguagem natural -> consulta FTS ('"a" OR "b" ...').

    Palavras curtas e de ligacao saem (senao tudo combina com tudo); as demais
    entram com OR para achar mesmo quando o pedido tem palavras a mais, e o
    ranking (bm25) poe o que interessa no topo.
    """
    palavras: list[str] = []
    for bruta in re.findall(r"[0-9a-zA-Z]{4,}", str(texto).lower()):
        if bruta in _PARADAS or bruta in palavras:
            continue
        palavras.append(bruta)
        if len(palavras) >= 6:
            break
    return " OR ".join(f'"{p}"' for p in palavras)


def _consulta_prefixos(texto: str) -> str:
    """Consulta FTS frouxa: 4 letras de cada palavra (para RECALL).

    O FTS5 nao tem radical em portugues: 'imprimir' e 'impressora' nunca se
    encontram por palavra exata. Com 4 letras as duas viram 'impr*' e a memoria
    volta. So' entra quando a busca exata nao achou nada, e com palavra de 6+
    letras - senao qualquer 'para' puxaria meia base.
    """
    palavras: list[str] = []
    for bruta in re.findall(r"[0-9a-zA-Z]{6,}", str(texto).lower()):
        if bruta in _PARADAS:
            continue
        prefixo = bruta[:4]
        if prefixo not in palavras:
            palavras.append(prefixo)
        if len(palavras) >= 6:
            break
    return " OR ".join(f'"{p}"*' for p in palavras)


def _buscar(query: str, limite: int = 20) -> list[tuple[str, str]]:
    """[(alvo, texto)] por assunto, do mais parecido para o menos.

    FTS5+bm25 quando existe; LIKE (mais recente primeiro) quando nao existe ou a
    consulta nao faz sentido para o FTS. Sem nenhum resultado exato, tenta uma
    vez com prefixo de 4 letras (recall), antes de desistir.
    """
    with _connect() as conn:
        consulta = _consulta_fts(query) or _consulta_fts(f'"{query}"')
        if _FTS["ok"] and consulta:
            try:
                rows = conn.execute(
                    "SELECT m.target, m.text FROM memories_fts "
                    "JOIN memories m ON m.id = memories_fts.rowid "
                    "WHERE memories_fts MATCH ? ORDER BY bm25(memories_fts) LIMIT ?",
                    (consulta, limite),
                ).fetchall()
                if rows:
                    return [(str(alvo), str(txt)) for alvo, txt in rows]
            except sqlite3.Error:
                pass   # consulta estranha: cai no LIKE (nunca fica sem busca)
        rows = conn.execute(
            "SELECT target, text FROM memories WHERE text LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limite),
        ).fetchall()
        if rows:
            return [(str(alvo), str(txt)) for alvo, txt in rows]
        # Ultimo recurso: prefixo (imprimir -> impressora).
        frouxa = _consulta_prefixos(query)
        if _FTS["ok"] and frouxa:
            try:
                rows = conn.execute(
                    "SELECT m.target, m.text FROM memories_fts "
                    "JOIN memories m ON m.id = memories_fts.rowid "
                    "WHERE memories_fts MATCH ? ORDER BY bm25(memories_fts) LIMIT ?",
                    (frouxa, limite),
                ).fetchall()
            except sqlite3.Error:
                rows = []
            return [(str(alvo), str(txt)) for alvo, txt in rows]
        return []


def add(text: str, target: str = "note") -> str:
    text = text.strip()
    if not text:
        return t("mem.empty_text")
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
            return t("mem.exists")
    _ULTIMO_ADD["quando"] = time.time()
    return t("mem.saved", target=target, texto=text)


def search(query: str) -> str:
    query = query.strip()
    if not query:
        return t("mem.no_query")
    achados = _buscar(query, limite=20)
    if not achados:
        return t("mem.none", query=query)
    return "\n".join(f"[{alvo}] {txt}" for alvo, txt in achados)


def relevant(query: str, limite: int = 5, max_chars: int = 600,
             ja_no_prompt: set | None = None) -> list[str]:
    """Memorias que COMBINAM com o pedido atual, para irem junto da mensagem.

    O bloco fixo do prompt mostra as mais recentes; por isso uma preferencia
    antiga ("nao gosto de jargao") sumia para sempre depois de 40 gravacoes.
    Aqui a busca e' por assunto e com ranking - e sem repetir o que a pessoa ja
    recebe no prompt (ja_no_prompt).
    """
    if not str(query or "").strip():
        return []
    try:
        achados = _buscar(query, limite=max(limite * 3, limite))
    except sqlite3.Error:
        return []
    repetidas = ja_no_prompt or set()
    saida: list[str] = []
    total = 0
    for _alvo, texto in achados:
        if texto in repetidas or texto in saida:
            continue
        if total + len(texto) > max_chars:
            break
        saida.append(texto)
        total += len(texto)
        if len(saida) >= limite:
            break
    return saida


def capturar(texto: str, depois_de: float | None = None) -> str | None:
    """Guarda uma frase do usuario que e' pedido PERMANENTE (rede de seguranca).

    O modelo ja recebe a ordem de gravar preferencias, mas modelo pequeno esquece.
    Aqui o codigo cobre o caso obvio ("meu nome e...", "prefiro...", "de agora em
    diante...") com frase curta - e devolve o que guardou, para a tela mostrar
    (a pessoa pode corrigir na hora).

    depois_de: instante em que o turno comecou. Se o modelo ja gravou algo DEPOIS
    disso, a captura nao repete (ele ja cuidou do caso neste turno).
    """
    frase = " ".join(str(texto or "").split())
    if not frase or len(frase) > 300:
        return None
    if depois_de is not None and float(_ULTIMO_ADD["quando"]) >= float(depois_de):
        return None   # o modelo ja gravou algo neste turno: nao duplica
    baixo = frase.lower()
    if not any(re.search(padrao, baixo) for padrao in PADROES_CAPTURA):
        return None
    # Frase inteira (com pontuacao final removida): e' ela que a pessoa vai reler.
    frase = frase.rstrip(".!? ").strip()
    if not frase:
        return None
    with _connect() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO memories (target, text, created) VALUES (?, ?, ?)",
            ("user", frase,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        if cur.rowcount == 0:
            return None   # ja estava na memoria
    _ULTIMO_ADD["quando"] = time.time()
    return frase


def list_recent(limit: int = 30) -> str:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT target, text FROM memories ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    if not rows:
        return t("mem.empty_base")
    return "\n".join(f"- [{alvo}] {txt}" for alvo, txt in rows)


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
    return t("mem.bad_action")

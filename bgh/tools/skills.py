"""Skills em SKILL.md: descoberta, indice no prompt e APRENDIZADO.

Duas origens:
- ~/.bgh/skills/<nome>/SKILL.md  -> skills da maquina do usuario (criadas pelo Motor ao aprender)
- <repo>/skills/<nome>/SKILL.md  -> skills de fabrica embutidas no pacote

A ferramenta `skill` fecha o ciclo de adaptacao, igual ao Hermes:
- load   : le a skill inteira antes de executar o assunto
- create : grava uma skill nova quando o Motor descobre um procedimento que funcionou
- append : acrescenta licao/correcao do usuario a uma skill existente
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from bgh.config import SKILLS_DIR, ensure_dirs

BUNDLED_SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills_default"

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

SPEC = {
    "type": "function",
    "function": {
        "name": "skill",
        "description": (
            "Skills = procedimentos aprendidos para esta maquina/usuario. "
            "action=load le uma skill inteira (SEMPRE antes de tarefa do dominio dela); "
            "action=create grava uma skill nova quando voce descobriu um procedimento que funcionou; "
            "action=append acrescenta uma licao ou correcao do usuario a uma skill existente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["load", "create", "append"]},
                "name": {"type": "string", "description": "Nome da skill (minusculo, com -)"},
                "content": {"type": "string", "description": "Conteudo completo (create)"},
                "section": {"type": "string", "description": "Trecho a acrescentar (append)"},
            },
            "required": ["action", "name"],
        },
    },
}


def _parse_frontmatter(text: str, fallback_name: str) -> tuple[str, str]:
    """Retorna (name, description) do bloco YAML simples; sem parser externo."""
    name, description = fallback_name, ""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:30]:
            stripped = line.strip()
            if stripped == "---":
                break
            if stripped.startswith("name:"):
                name = stripped.split(":", 1)[1].strip().strip("\"'") or name
            elif stripped.startswith("description:"):
                description = stripped.split(":", 1)[1].strip().strip("\"'")
    if not description:
        for line in lines:
            if line.strip() and not line.startswith(("#", "---")):
                description = line.strip()[:120]
                break
    return name, description


def discover() -> list[dict]:
    """Todas as skills visiveis: [{name, description, path, source}]."""
    found: dict[str, dict] = {}
    for base, source in ((SKILLS_DIR, "usuario"), (BUNDLED_SKILLS_DIR, "fabrica")):
        if not base.is_dir():
            continue
        for sub in sorted(base.iterdir()):
            md = sub / "SKILL.md"
            if sub.is_dir() and md.is_file():
                try:
                    text = md.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                name, description = _parse_frontmatter(text, sub.name)
                # Skill do usuario tem prioridade sobre a de fabrica com mesmo nome.
                if name not in found or source == "usuario":
                    found[name] = {
                        "name": name,
                        "description": description,
                        "path": md,
                        "source": source,
                    }
    return sorted(found.values(), key=lambda s: s["name"])


def index_lines(skills: list[dict]) -> list[str]:
    return [f"{s['name']}: {s['description'][:110]}" for s in skills]


def _find(name: str) -> dict | None:
    for s in discover():
        if s["name"] == name:
            return s
    return None


def load_skill_tool(args: dict, ctx) -> str:
    action = args.get("action")
    name = str(args.get("name", "")).strip().lower()
    if not name:
        return "ERRO: informe o nome da skill"
    if action == "load":
        skill = _find(name)
        if skill is None:
            available = ", ".join(s["name"] for s in discover()) or "(nenhuma)"
            return f"Skill '{name}' nao encontrada. Disponiveis: {available}"
        text = skill["path"].read_text(encoding="utf-8", errors="replace")
        if len(text) > 12000:
            text = text[:12000] + "\n[skill truncada]"
        return text
    if action == "create":
        if not NAME_RE.match(name):
            return "ERRO: nome invalido (use minusculas, digitos e '-', ex.: impressora-hp-laserjet)"
        if _find(name):
            return f"ERRO: skill '{name}' ja existe; use action=append para acrescentar licoes."
        content = str(args.get("content", "")).strip()
        if not content:
            return "ERRO: falta o conteudo da skill"
        ensure_dirs()
        skill_dir = SKILLS_DIR / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        md = skill_dir / "SKILL.md"
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        md.write_text(content + f"\n\n<!-- criada pelo Motor em {stamp} -->\n", encoding="utf-8")
        return f"OK: skill '{name}' criada em {md}. Ela entrara no indice das proximas conversas."
    if action == "append":
        skill = _find(name)
        if skill is None:
            return f"ERRO: skill '{name}' nao existe; crie com action=create."
        section = str(args.get("section", "")).strip()
        if not section:
            return "ERRO: falta a secao a acrescentar"
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        existing = skill["path"].read_text(encoding="utf-8", errors="replace")
        skill["path"].write_text(
            existing.rstrip() + f"\n\n## Licao ({stamp})\n{section}\n", encoding="utf-8"
        )
        return f"OK: licao acrescentada a skill '{name}'."
    return "ERRO: action invalida (use load, create ou append)"

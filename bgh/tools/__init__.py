"""Registro central de ferramentas: specs no formato OpenAI + dispatch tolerante."""

import json
import re
from dataclasses import dataclass
from typing import Callable

from . import documents, files, memory, packages, python_exec, skills, terminal, websearch


def truncate(text: str, limit: int = 6000) -> str:
    text = text if isinstance(text, str) else str(text)
    if len(text) <= limit:
        return text
    keep = limit // 2
    return text[:keep] + f"\n...[cortado, {len(text)} chars no total]...\n" + text[-keep:]


@dataclass
class Ctx:
    """Contexto compartilhado pelas ferramentas."""

    cfg: dict
    gate: object  # bgh.approvals.Gate
    stop_event: object | None = None  # threading.Event: usuario mandou parar


class ToolBox:
    def __init__(self, cfg: dict, gate, stop_event=None):
        self.ctx = Ctx(cfg=cfg, gate=gate, stop_event=stop_event)
        self.handlers = {
            "run_command": terminal.run,
            "run_python": python_exec.run,
            "read_file": files.read_file,
            "write_file": files.write_file,
            "search_files": files.search_files,
            "web_search": websearch.web_search,
            "web_extract": websearch.web_extract,
            "memory": memory.run,
            "skill": skills.load_skill_tool,
            "make_document": documents.make_document,
            "instalar_pacote": packages.run,
        }
        self.specs = [
            terminal.SPEC,
            python_exec.SPEC,
            files.READ_SPEC,
            files.WRITE_SPEC,
            files.SEARCH_SPEC,
            websearch.SEARCH_SPEC,
            websearch.EXTRACT_SPEC,
            memory.SPEC,
            skills.SPEC,
            documents.SPEC,
            packages.SPEC,
        ]

    def dispatch(self, name: str, arguments_json: str) -> str:
        handler = self.handlers.get(name)
        if handler is None:
            return f"ERRO: ferramenta desconhecida '{name}'. Disponiveis: {', '.join(self.handlers)}"
        try:
            args = _tolerant_json(arguments_json)
        except ValueError as exc:
            return f"ERRO: argumentos invalidos para {name}: {exc}. Reenvie JSON valido."
        try:
            result = handler(args, self.ctx)
        except Exception as exc:  # noqa: BLE001 - falha de ferramenta vira texto para o modelo
            result = f"ERRO na ferramenta {name} ({type(exc).__name__}): {exc}"
        return truncate(result)


def _tolerant_json(raw) -> dict:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return {}
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Consertos comuns de modelo pequeno: virgula antes de fechar }/] e aspas simples.
        fixed = re.sub(r",\s*([}\]])", r"\1", text)
        if fixed.count("'") > fixed.count('"'):
            fixed = fixed.replace("'", '"')
        try:
            parsed = json.loads(fixed)
        except json.JSONDecodeError as exc:
            raise ValueError(f"nao e JSON ({exc}). Recebido: {text[:200]}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("esperava um objeto JSON com os argumentos")
    return parsed

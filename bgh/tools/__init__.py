"""Registro central de ferramentas: specs no formato OpenAI + dispatch tolerante."""

import copy
import json
import re
from dataclasses import dataclass
from typing import Callable

from ..i18n import t
from . import documents, files, memory, packages, python_exec, skills, terminal, websearch


def localize_specs(specs: list) -> list:
    """Descricoes das ferramentas no idioma da tela (chave ausente: fica a original).

    O modelo le a descricao da ferramenta junto com o pedido: em ingles ou
    espanhol ele descobre o que a ferramenta faz no mesmo idioma da conversa, e o
    campo 'motivo' (que o usuario le no menu de licenca) pede o texto no idioma da
    tela em vez de portugues.
    """
    for spec in specs:
        fn = spec.get("function") or spec
        nome = str(fn.get("name") or "")
        texto = t("tool." + nome + ".desc")
        if not texto.startswith("tool."):
            fn["description"] = texto
        props = (fn.get("parameters") or {}).get("properties") or {}
        for argumento, campo in props.items():
            if not isinstance(campo, dict):
                continue
            texto_arg = t("tool." + nome + ".arg." + argumento)
            if not texto_arg.startswith("tool."):
                campo["description"] = texto_arg
    return specs


def truncate(text: str, limit: int = 6000) -> str:
    text = text if isinstance(text, str) else str(text)
    if len(text) <= limit:
        return text
    keep = limit // 2
    return text[:keep] + t("tool.truncated", n=len(text)) + text[-keep:]


@dataclass
class Ctx:
    """Contexto compartilhado pelas ferramentas."""

    cfg: dict
    gate: object  # bgh.approvals.Gate
    stop_event: object | None = None  # threading.Event: usuario mandou parar
    # Arquivos que o TEO criou nesta sessao (write_file). Serve para limpar o
    # apoio sem risco de apagar arquivo do usuario.
    criados: list | None = None


class ToolBox:
    def __init__(self, cfg: dict, gate, stop_event=None):
        self.ctx = Ctx(cfg=cfg, gate=gate, stop_event=stop_event, criados=[])
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
            "limpar_apoio": files.limpar_apoio,
        }
        # Copia da definicao original (portugues) + versao no idioma da tela: a
        # copia evita que um ToolBox novo herde o idioma de outro (testes e /lingua).
        self._specs_base = copy.deepcopy([
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
            files.LIMPAR_SPEC,
        ])
        self.specs = localize_specs(copy.deepcopy(self._specs_base))

    def relocalize(self) -> None:
        """Troca o idioma das descricoes das ferramentas (chamado pelo /lingua)."""
        self.specs = localize_specs(copy.deepcopy(self._specs_base))

    def dispatch(self, name: str, arguments_json: str) -> str:
        handler = self.handlers.get(name)
        if handler is None:
            return t("tool.unknown", name=name, lista=", ".join(self.handlers))
        try:
            args = _tolerant_json(arguments_json)
        except ValueError as exc:
            return t("tool.bad_args", name=name, erro=exc)
        try:
            result = handler(args, self.ctx)
        except Exception as exc:  # noqa: BLE001 - falha de ferramenta vira texto para o modelo
            result = t("tool.crash", name=name, tipo=type(exc).__name__, erro=exc)
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

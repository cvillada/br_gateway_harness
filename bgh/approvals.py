"""Politica de aprovacao espelhada no modelo do Hermes Agent.

Camadas:
1. Hardline blocklist: piso que nenhuma aprovacao cruza (rm -rf /, fork bomb, dd em disco).
2. Dangerous patterns: regras conhecidas que exigem licenca humana.
3. Allowlist permanente: padroes aprovados com 'sempre' voltam para config.json
   (campo command_allowlist; texto exato ou glob estilo shell).
4. Resto: executa sem perguntar.

Menu para o usuario (pensado para pessoa idosa):
  [1] Sim, fazer desta vez
  [2] Sim, e nao perguntar de novo nesta conversa
  [3] Sim, e sempre permitir isso depois   (quando faz sentido)
  [4] Nao / cancelar                        (padrao)
Por dentro continua o fluxo do Hermes: o/s/a/d, deny falha fechada.
"""

import fnmatch
import re

from bgh import config as cfg_mod

# --- Piso duro (nunca executa, nem com allowlist) -----------------------------
HARD_PATTERNS = [
    (r"\brm\b[^\n]*\s-[a-z]*r[a-z]*f[a-z]*\s+/(\s|$)", "apagar o sistema inteiro (rm -rf /)"),
    (r"\brm\b.*--no-preserve-root", "apagar o disco todo sem protecao"),
    (r":\s*\(\s*\)\s*\{[^}]*:\|:&.*\}", "travar o computador com bomba de processos"),
    (r"\bdd\b[^\n]*of=/dev/(sd|nvme|disk)", "zerar um disco fisico"),
]

HARD_TOKENS = ["rm -rf /", "--no-preserve-root", ":(){ :|:& };:", "of=/dev/sd", "of=/dev/nvme"]

# --- Regras perigosas: (rule_key, regex, texto simples para o usuario) --------
DANGEROUS_RULES = [
    ("recursive delete", r"\brm\b[^\n]*\s-[a-zA-Z]*r", "apagar uma pasta e tudo dentro dela"),
    ("delete in root path", r"\brm\b[^\n]*\s(/|~/?)", "apagar arquivos de pasta do sistema"),
    ("delete file", r"\brm\s", "apagar um arquivo"),
    ("unsafe permissions", r"\bchmod\b[^\n]*\b(777|666|o\+w|a\+w)\b", "deixar arquivos abertos para qualquer pessoa mexer"),
    ("recursive chown to root", r"\bchown\b[^\n]*-[a-zA-Z]*r[^\n]*\broot\b", "passar a posse de arquivos para o sistema"),
    ("format filesystem", r"\bmkfs(\.|\s)", "formatar (apagar tudo de) um disco"),
    ("disk copy", r"\bdd\s+if=", "copiar dados direto em disco fisico"),
    ("write to block device", r">\s*/dev/(sd|nvme|disk)", "gravar direto em disco fisico"),
    ("SQL drop", r"\bDROP\s+(TABLE|DATABASE)\b", "apagar uma tabela ou banco de dados inteiro"),
    ("SQL delete without WHERE", r"\bDELETE\s+FROM\b(?![^\n]*\bWHERE\b)", "apagar linhas de uma tabela sem filtro"),
    ("SQL truncate", r"\bTRUNCATE\s+TABLE\b", "esvaziar uma tabela inteira"),
    ("overwrite system config", r"(>>?|tee\s+/)\s*/etc/", "mudar arquivo de configuracao do sistema"),
    ("service control", r"\bsystemctl\b[^\n]*\b(stop|restart|disable|mask|poweroff|reboot)\b", "parar ou reiniciar um servico do sistema"),
    ("process kill", r"\b(pkill|killall)\b|\bkill\s+-9\s+-1\b", "fechar programas a forca"),
    ("pipe remote content to shell", r"\b(curl|wget)\b[^|\n]*\|\s*(ba|z|k)?sh\b", "baixar algo da internet e executar sem ver o que faz"),
    ("remote script via process substitution", r"\b(ba|z)?sh\s+<\s*\(\s*\(?\s*(curl|wget)", "executar um script baixado da internet"),
    ("find with delete action", r"\bfind\b[^\n]*(-exec\s+rm\b|-delete\b)", "procurar e apagar varios arquivos de uma vez"),
    ("xargs rm", r"\bxargs\b[^\n]*\brm\b", "apagar varios arquivos de uma vez"),
    ("copy into system config", r"\b(cp|mv|install)\b[^\n]*\s/etc/", "colocar um arquivo nas pastas do sistema"),
    ("in-place edit of system config", r"\bsed\b[^\n]*-i[^\n]*/etc/", "editar configuracao do sistema"),
    ("sudo (pede senha de administrador)", r"(^|\s)sudo\s", "usar poder de administrador (pede senha)"),
    ("instalar pacote", r"\b(pip3?|uv|pipx)\b[^\n|]*\binstall\b", "baixar e instalar programa da internet"),
]

RULE_LABELS = {key: label for key, _, label in DANGEROUS_RULES}

# Codigo Python que apaga arquivos tambem precisa de licenca.
DELETION_TOKENS = ["shutil.rmtree", "os.remove", "os.unlink", ".unlink(", 'system("rm', "system('rm"]

# --- Caminhos sensiveis para escrita ------------------------------------------
SENSITIVE_PATH_RE = [
    r"^/etc/", r"^/boot/", r"^/usr/", r"^/bin/", r"^/sbin/", r"^/lib/",
    r"/\.ssh/", r"/\.gnupg/", r"\.env$", r"\.netrc$", r"id_rsa", r"/\.password-store/",
]


def _hard_match(text: str) -> str | None:
    for rx, why in HARD_PATTERNS:
        if re.search(rx, text, re.IGNORECASE):
            return why
    for token in HARD_TOKENS:
        if token in text:
            return "padrao catastrofico no texto"
    return None


def dangerous_rules(command: str) -> list[tuple[str, str]]:
    """Retorna [(rule_key, trecho)] das regras que o comando toca."""
    hits = []
    for key, rx, _label in DANGEROUS_RULES:
        m = re.search(rx, command, re.IGNORECASE)
        if m:
            hits.append((key, m.group(0)[:60]))
    return hits


# --- Allowlist permanente (compartilhado com `bgh approvals`) -----------------
def list_allowlist(cfg: dict) -> list[str]:
    entries = cfg.get("command_allowlist") or []
    return [e for e in entries if isinstance(e, str)]


def remove_allowlist(cfg: dict, index: int) -> str | None:
    entries = list_allowlist(cfg)
    if not 1 <= index <= len(entries):
        return None
    removed = entries[index - 1]
    cfg["command_allowlist"] = [e for e in entries if e != removed]
    cfg_mod.save_config(cfg)
    return removed


def clear_allowlist(cfg: dict) -> int:
    count = len(list_allowlist(cfg))
    cfg["command_allowlist"] = []
    cfg_mod.save_config(cfg)
    return count


class Gate:
    """Decide se comando/codigo/caminho pode rodar; pergunta quando preciso (falha fechada)."""

    def __init__(self, cfg: dict, ask):
        # ask(label, detail, allow_always: bool) -> "o" | "s" | "a" | "d"
        self.cfg = cfg
        self.ask = ask
        self.session_rules: set[str] = set()

    @property
    def allowlist(self) -> list[str]:
        return list_allowlist(self.cfg)

    def _remember_always(self, rule_or_glob: str) -> None:
        self.cfg.setdefault("command_allowlist", []).append(rule_or_glob)
        cfg_mod.save_config(self.cfg)

    def _ask_rule(self, key: str, detail: str, allow_always: bool = True) -> bool:
        """True se o usuario aprovou; aplica 'nesta conversa'/'sempre' quando escolhido."""
        choice = self.ask(RULE_LABELS.get(key, key), detail, allow_always=allow_always)
        if choice == "o":
            return True
        if choice == "s":
            self.session_rules.add(key)
            return True
        if choice == "a" and allow_always:
            self._remember_always(key)
            self.session_rules.add(key)
            return True
        return False

    def _ask_rule_many(self, keys: list[str], detail: str) -> bool:
        """Uma unica licenca para um comando que toca varias regras (menos confusao)."""
        labels = "; ".join(RULE_LABELS.get(k, k) for k in keys)
        choice = self.ask(labels, detail, allow_always=True)
        if choice == "o":
            return True
        if choice == "s":
            self.session_rules.update(keys)
            return True
        if choice == "a":
            self.session_rules.update(keys)
            for k in keys:
                self._remember_always(k)
            return True
        return False

    def command_ok(self, command: str) -> tuple[bool, str | None]:
        """(pode_rodar, mensagem_de_bloqueio_para_o_modelo)."""
        command = command.strip()
        why = _hard_match(command)
        if why:
            return False, (
                f"BLOQUEADO PERMANENTE: {why}. Este comando nao roda em nenhuma circunstancia; "
                "rode fora do TEO se for realmente necessario. Procure um caminho alternativo."
            )
        hits = dangerous_rules(command)
        if not hits:
            return True, None  # comando seguro: executa sem perguntar
        pending: list[tuple[str, str]] = []
        for key, trecho in hits:
            if key in self.session_rules:
                continue
            if any(fnmatch.fnmatch(command, entry) or command == entry for entry in self.allowlist):
                continue
            if key in self.allowlist:
                continue
            pending.append((key, trecho))
        if pending:
            # Uma unica pergunta por comando, mesmo tocando varias regras.
            keys = [k for k, _ in pending]
            trechos = "\n".join(f"(preocupacao: {t})" for _, t in pending[:4])
            if not self._ask_rule_many(keys, f"Comando: {command}\n{trechos}"):
                labels = "; ".join(RULE_LABELS.get(k, k) for k in keys)
                return False, (
                    f"BLOQUEADO: o usuario negou ({labels}). "
                    "Proponha uma alternativa segura em vez de repetir."
                )
        return True, None

    def install_ok(self, pacote: str, motivo: str) -> tuple[bool, str | None]:
        """Licenca para baixar e instalar uma biblioteca Python do PyPI."""
        key = "instalar pacote"
        entry = f"pip install {pacote}"
        if key in self.session_rules or key in self.allowlist:
            return True, None
        if any(fnmatch.fnmatch(entry, e) or entry == e for e in self.allowlist):
            return True, None
        choice = self.ask(
            RULE_LABELS[key],
            f"Vou baixar e instalar a biblioteca '{pacote}' (loja oficial do Python, PyPI).\n"
            f"Motivo: {motivo}",
            allow_always=True,
        )
        if choice == "o":
            return True, None
        if choice == "s":
            self.session_rules.add(key)
            return True, None
        if choice == "a":
            self._remember_always(entry)  # 'pip install <pacote>' fica permanente
            self.session_rules.add(key)
            return True, None
        return False, (
            f"BLOQUEADO: o usuario nao quis instalar '{pacote}'. Continue sem essa biblioteca "
            "ou explique em linguagem simples por que ela e indispensavel."
        )

    def python_code_ok(self, code: str) -> tuple[bool, str | None]:
        """Codigo Python roda direto, exceto quando apaga arquivos - ai pede licenca."""
        why = _hard_match(code)
        if why:
            return False, f"BLOQUEADO PERMANENTE: {why} presente no codigo."
        hit = next((t for t in DELETION_TOKENS if t in code), None)
        if hit and "python delete" not in self.session_rules:
            preview = "\n".join(code.splitlines()[:6])
            if not self._ask_rule(
                "python delete",
                f"O programa Python vai apagar arquivos (usa '{hit}').\nCodigo:\n{preview}",
                allow_always=False,
            ):
                return False, "BLOQUEADO: o usuario negou o codigo que apaga arquivos."
        return True, None

    def overwrite_ok(self, path: str) -> tuple[bool, str | None]:
        """Sobrescrever arquivo existente sempre pede licenca (sem opcao 'sempre')."""
        if "overwrite" in self.session_rules:
            return True, None
        choice = self.ask(
            "Ja existe um arquivo com esse nome; sobrescrever?",
            path,
            allow_always=False,
        )
        if choice == "s":
            self.session_rules.add("overwrite")
            return True, None
        if choice != "o":
            return False, f"BLOQUEADO: o usuario nao quis sobrescrever {path}. Salve com outro nome."
        return True, None

    def path_ok(self, path: str) -> tuple[bool, str | None]:
        norm = str(path)
        if not norm.startswith("/"):
            return True, None  # caminhos relativos/home sao do usuario
        for rx in SENSITIVE_PATH_RE:
            if re.search(rx, norm):
                choice = self.ask(
                    "Vou escrever numa pasta protegida do sistema",
                    norm,
                    allow_always=False,
                )
                if choice != "o":
                    return False, f"BLOQUEADO: o usuario negou escrita em {norm}."
                return True, None
        return True, None

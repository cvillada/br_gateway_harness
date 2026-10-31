"""Testes offline do Motor (nao precisa de modelo nem internet).

Roda: .venv/bin/python tests/test_smoke.py
BGH_HOME aponta para uma pasta temporaria ANTES de importar o pacote.
"""

import json
import os
import sys
import tempfile
import types
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="bgh_test_"))
os.environ["BGH_HOME"] = str(TMP)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PASS = 0


def ok(label: str, cond: bool):
    global PASS
    if not cond:
        raise AssertionError(f"FALHOU: {label}")
    PASS += 1
    print(f"ok - {label}")


# ---------- approvals ---------------------------------------------------------
from bgh.approvals import Gate

calls: list[str] = []


def ask_o(label, detail, allow_always):
    calls.append(label)
    return "o"


def ask_d(label, detail, allow_always):
    calls.append(label)
    return "d"


cfg = {"command_allowlist": []}

# comando seguro nao pergunta nada
gate = Gate(cfg, ask_o)
allowed, msg = gate.command_ok("ls -la ~/Documentos")
ok("comando seguro roda sem prompt", allowed and not calls)

# piso duro: nem perguntando passa
allowed, msg = gate.command_ok("rm -rf / --no-preserve-root")
ok("piso duro bloqueia sem chance", not allowed and "PERMANENTE" in msg and not calls)

# perigoso com negar -> bloqueado
gate = Gate(cfg, ask_d)
allowed, msg = gate.command_ok("rm -rf ~/velho")
ok("deny bloqueia e orienta alternativa", not allowed and "BLOQUEADO" in msg)

# perigoso com 'o' aprova uma vez
gate = Gate(cfg, ask_o)
allowed, _ = gate.command_ok("sudo apt install --reinstall vim")
ok("'o' aprova sudo", allowed)

# 'a' persiste no allowlist e o proximo Gate silencia
chosen: list[str] = []


def ask_a(label, detail, allow_always):
    chosen.append(label)
    return "a"


gate = Gate(cfg, ask_a)
allowed, _ = gate.command_ok("systemctl restart nginx")
ok("'a' persiste a regra no allowlist", allowed and "service control" in cfg["command_allowlist"])
asked2: list[str] = []


def ask_d2(label, detail, allow_always):
    asked2.append(label)
    return "d"


gate2 = Gate(cfg, ask_d2)  # allowlist carregado: nao pergunta mais
allowed, _ = gate2.command_ok("systemctl restart postgres")
ok("allowlist permanente silencia a regra", allowed and not asked2)

# glob no allowlist
cfg["command_allowlist"].append("git push *")
gate3 = Gate(cfg, ask_d)
ok("glob do allowlist bate", gate3.command_ok("git push origin main")[0])

# texto de python catastrofico
ok("python_code_ok bloqueia fork bomb", not gate3.python_code_ok("import os\n:(){ :|:& };:")[0])

# caminho sensivel
ok("escrita em /etc bloqueada na recusa", not gate3.path_ok("/etc/nginx/site")[0])
ok("escrita na home livre", gate3.path_ok(str(TMP / "qualquer.txt"))[0])

# ---------- tolerant json -----------------------------------------------------
from bgh.tools import _tolerant_json

ok("json valido", _tolerant_json('{"a": 1}') == {"a": 1})
ok("virgula sobrando consertada", _tolerant_json('{"a": 1,}') == {"a": 1})
ok("string vazia vira {}", _tolerant_json("") == {})
try:
    _tolerant_json("isso nem e json")
    ok("lixo gera erro claro", False)
except ValueError:
    ok("lixo gera erro claro", True)

# ---------- memoria ------------------------------------------------------------
from bgh.tools import memory

memory.add("usuario prefere respostas curtas", "user")
memory.add("maquina tem 2 GPUs", "note")
memory.add("usuario prefere respostas curtas", "user")  # duplicada ignorada
ok("search acha fato", "curtas" in memory.search("curtas"))
lines_user = memory.load_lines("user")
lines_note = memory.load_lines("note")
ok("alvo user separado de note", lines_user == ["usuario prefere respostas curtas"]
   and lines_note == ["maquina tem 2 GPUs"])

# ---------- skills --------------------------------------------------------------
from bgh.tools.skills import discover, index_lines

skills = discover()
names = {s["name"] for s in skills}
ok("skills de fabrica descobertas", {"python-best-practices", "hardware-troubleshooting"} <= names)
ok("indice gerado", any("python" in line for line in index_lines(skills)))


class FakeCtx:
    gate = gate3


ctx = FakeCtx()
res = memory.run({"action": "add", "target": "user", "text": "nome do usuario: Jose"}, ctx)
ok("memory via ferramenta", "Memoria gravada [user]" in res)

from bgh.tools import skills as skills_mod

res = skills_mod.load_skill_tool({"action": "create", "name": "impressora-hp", "content": "# Impressora HP\nFunciona com lp"}, ctx)
ok("skill create", "criada" in res)
res = skills_mod.load_skill_tool({"action": "append", "name": "impressora-hp", "section": "Ligar antes do envio."}, ctx)
ok("skill append", "licao acrescentada" in res.lower())
res = skills_mod.load_skill_tool({"action": "load", "name": "impressora-hp"}, ctx)
ok("skill load devolve conteudo", "Ligar antes" in res)
res = skills_mod.load_skill_tool({"action": "create", "name": "impressora-hp", "content": "x"}, ctx)
ok("create duplicado recusa", "ja existe" in res)
ok("skill do usuario entra no discover", "impressora-hp" in {s["name"] for s in discover()})

# ---------- web parser (offline com html ensaiado) -----------------------------
from bgh.tools.websearch import _real_url, parse_lite, parse_html_page

lite_html = """
<table><tr><td><a rel="nofollow" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&amp;rut=abc">Example Page</a></td></tr>
<tr><td class='result-snippet'>Um <b>exemplo</b> de snippet.</td></tr></table>
"""
results = parse_lite(lite_html, 6)
ok("parse_lite link+titulo+snippet",
   results and results[0]["url"] == "https://example.com/page"
   and results[0]["title"] == "Example Page" and "exemplo" in results[0]["snippet"])

html_ddg = '<a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Foutro.com">Outro</a><a class="result__snippet" href="#">snip</a>'
ok("parse_html_page", parse_html_page(html_ddg, 6)[0]["url"] == "https://outro.com")
ok("_real_url passa URL normal", _real_url("https://direto.com/x") == "https://direto.com/x")

# ---------- documentos ----------------------------------------------------------
from bgh.tools.documents import make_document, md_to_html

html = md_to_html("Teste", "# Ola\n\n- item **negrito**\n\n`codigo`\n\n```\nx = 1\n```")
ok("md_to_html basico", "<h1>Ola</h1>" in html and "<b>negrito</b>" in html and "<pre>" in html)
out_path = str(TMP / "docs" / "teste.md")
res = make_document({"title": "Teste", "content_markdown": "oi", "path": out_path}, ctx)
ok("make_document salva", "OK" in res and Path(out_path).is_file())

# ---------- arquivos ------------------------------------------------------------
from bgh.tools import files

w = files.write_file({"path": str(TMP / "proj" / "a.py"), "content": "x = 1\nprint(x)\n"}, ctx)
ok("write_file cria dirs pai", "OK" in w)
r = files.read_file({"path": str(TMP / "proj" / "a.py")}, ctx)
ok("read_file com numero de linha", "1|x = 1" in r)
s = files.search_files({"pattern": "print", "path": str(TMP / "proj")}, ctx)
ok("search_files acha", "a.py:2" in s)

# ---------- run_python -----------------------------------------------------------
from bgh.tools import python_exec

r = python_exec.run({"code": "print(40 + 2)"}, ctx)
ok("run_python executa", "exit_code=0" in r and "42" in r)

# ---------- agente loop com FakeLLM ----------------------------------------------
from bgh.agent import Agent


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def chat(self, messages, tools=None):
        reply = self.replies[self.calls]
        self.calls += 1
        return json.loads(json.dumps(reply))  # copia profunda

    def summarize(self, text):
        return "resumo fake"


fake_llm = FakeLLM([
    {"role": "assistant", "content": "", "reasoning": "vou listar os arquivos primeiro",
     "tool_calls": [
        {"id": "c1", "type": "function", "function": {
            "name": "run_command", "arguments": '{"command": "echo ola_mundo"}'}}]},
    {"role": "assistant", "content": "Esta tudo certo, ola_mundo apareceu."},
])
cfg_agent = dict(cfg)
agent = Agent(cfg_agent, fake_llm, Gate(cfg_agent, ask_d))
answer = agent.run_turn("rode um echo ai")
ok("loop ferramenta->resposta", "ola_mundo" in answer or "certo" in answer)
ok("reasoning do modelo capturado", agent.last_reasoning and "listar" in agent.last_reasoning[0])
usage = agent.ctx_usage()
ok("medidor de contexto funciona", usage["pct"] >= 0 and usage["budget"] == 156000 and usage["messages"] > 2)
tool_msgs = [m for m in agent.messages if m.get("role") == "tool"]
ok("resultado da ferramenta voltou ao modelo", tool_msgs and "ola_mundo" in tool_msgs[0]["content"])
ok("sessao persistida", Path(os.environ["BGH_HOME"], "session.json").is_file())

# chamada com JSON quebrado -> erro amigavel volta como tool msg
fake_llm2 = FakeLLM([
    {"role": "assistant", "content": "", "tool_calls": [
        {"id": "c2", "type": "function", "function": {"name": "run_command", "arguments": "comando solto sem json"}}]},
    {"role": "assistant", "content": "ok"},
])
agent2 = Agent(cfg_agent, fake_llm2, Gate(cfg_agent, ask_d))
agent2.new_session()  # isola da conversa anterior (retomacao automatica e' por design)
agent2.run_turn("tenta ai")
bad = [m for m in agent2.messages if m.get("role") == "tool"][0]["content"]
ok("argumento malformado vira erro legivel", "ERRO" in bad and "JSON" in bad)

# prompt do sistema carrega memoria e skills
sysmsg = agent.messages[0]["content"]
ok("system prompt traz memoria user", "SOBRE O USUARIO" in sysmsg and "Jose" in sysmsg)
ok("system prompt traz indice de skills", "SKILLS DISPONIVEIS" in sysmsg and "impressora-hp" in sysmsg)

# ---------- aprovacoes ---------------------------------------------------------
gate_rm = Gate(cfg, ask_d)
allowed, msg = gate_rm.command_ok("rm nota.txt")
ok("rm de arquivo simples pede licenca", not allowed and "arquivo" in msg)
allowed, _ = Gate(cfg, ask_o).command_ok("rm nota.txt")
ok("rm aprovado com 'desta vez' roda", allowed)

asked_py: list[str] = []


def ask_py_d(label, detail, allow_always):
    asked_py.append(label)
    return "d"


gate_py = Gate(cfg, ask_py_d)
allowed, msg = gate_py.python_code_ok("import shutil\nshutil.rmtree('/home/x/velho')")
ok("python que apaga arquivos e bloqueado na recusa", not allowed and asked_py)
allowed, _ = Gate(cfg, lambda l, d, allow_always=True: "o").python_code_ok("import shutil\nshutil.rmtree('/home/x/velho')")
ok("python que apaga passa se usuario aprovar", allowed)
allowed, _ = Gate(cfg, ask_py_d).python_code_ok("print('nada perigoso')")
ok("python inocente nao pergunta", allowed and len(asked_py) == 1)

allowed, _ = Gate(cfg, ask_d).overwrite_ok("/home/x/nota.txt")
ok("sobrescrever negado bloqueia", not allowed)
gate_ows = Gate(cfg, lambda l, d, allow_always=True: "s")
o1, _ = gate_ows.overwrite_ok("/home/x/a.txt")
o2, _ = gate_ows.overwrite_ok("/home/x/b.txt")
ok("overwrite 'nesta conversa' silencia depois", o1 and o2)

cfg2 = {"command_allowlist": ["service control", "git push *"]}
from bgh.approvals import clear_allowlist, list_allowlist, remove_allowlist

ok("list_allowlist", list_allowlist(cfg2) == ["service control", "git push *"])
ok("remove_allowlist", remove_allowlist(cfg2, 1) == "service control" and list_allowlist(cfg2) == ["git push *"])
ok("clear_allowlist", clear_allowlist(cfg2) == 1 and list_allowlist(cfg2) == [])

# menu numerico de licenca do nucleo (input mockado)
import bgh.chat_core as core_mod

sink_menu = core_mod.ConsoleSink()
core_mod.input = lambda prompt: "1"
ok("menu 1 = desta vez", sink_menu.ask_approval("x", "y", True) == "o")
core_mod.input = lambda prompt: "2"
ok("menu 2 = nesta conversa", sink_menu.ask_approval("x", "y", True) == "s")
core_mod.input = lambda prompt: "3"
ok("menu 3 = sempre", sink_menu.ask_approval("x", "y", True) == "a")
core_mod.input = lambda prompt: ""
ok("Enter sozinho = nao (padrao)", sink_menu.ask_approval("x", "y", True) == "d")
core_mod.input = lambda prompt: "9"
ok("numero invalido = nao", sink_menu.ask_approval("x", "y", True) == "d")
del core_mod.input

# atalhos / e @ (list_dir)
from bgh.tools.files import list_dir

out = list_dir(str(TMP / "proj"))
out2 = list_dir(str(TMP / "proj"), files_only=True)
ok("list_dir mostra arquivos", "[ARQ] a.py" in out)
ok("list_dir files_only ignora pastas", "[ARQ] a.py" in out2 and "[DIR]" not in out2)

# streaming no agente
class StreamFake:
    def chat(self, messages, tools=None):
        raise AssertionError("com stream ligado nao deveria chamar chat()")

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None, should_stop=None):
        if on_reasoning:
            on_reasoning("pen")
        if on_text:
            on_text("sando certo")
        return {"role": "assistant", "content": "pensando certo", "reasoning": "pen"}

agent_s = Agent(dict(cfg), StreamFake(), Gate(dict(cfg), ask_d))
got: list[str] = []
agent_s.on_text_delta = lambda c: got.append(c)
ans_s = agent_s.run_turn("oi")
ok("streaming entregue por callback", got == ["sando certo"] and ans_s == "pensando certo" and agent_s.last_streamed)

# ---------- autonomia ------------------------------------------------------------
from bgh.tools import packages as pkg_mod
from bgh.tools import Ctx

ok("nome valido aceito", bool(pkg_mod.PKG_RE.match("rich")) and bool(pkg_mod.PKG_RE.match("pandas==2.2.0")))
ok("nome malicioso rejeitado", not pkg_mod.PKG_RE.match("x; rm -rf /") and not pkg_mod.PKG_RE.match("-evil") and not pkg_mod.PKG_RE.match(""))

# pip via run_command passa a pedir licenca
ok("pip install via run_command pede licenca", not Gate(cfg, ask_d).command_ok("pip install requests")[0])
ok("pip install aprovado roda", Gate(cfg, ask_o).command_ok("pip install requests")[0])

# licenca do instalar_pacote (negado / sempre)
install_asks: list[str] = []


def ask_install(label, detail, allow_always):
    install_asks.append(label)
    return "a"


cfg_pkg = dict(cfg)
gate_i = Gate(cfg_pkg, ask_install)
allowed, _ = gate_i.install_ok("rich", "montar tabelas")
ok("instalacao com 'sempre' persiste regra", allowed and cfg_pkg["command_allowlist"][-1] == "pip install rich")
before = len(install_asks)
allowed, _ = gate_i.install_ok("rich", "montar tabelas")
ok("mesmo pacote aprovado nao pergunta de novo", allowed and len(install_asks) == before)
gate_n = Gate(cfg, ask_d)
allowed, msg = gate_n.install_ok("openpyxl", "editar planilha")
ok("instalacao negada bloqueia", not allowed and "BLOQUEADO" in msg)

# ferramenta instalar_pacote com pip simulado
captured_cmds: list[list[str]] = []
orig_subprocess = pkg_mod.subprocess


def fake_subprocess_run(cmd, **kw):
    captured_cmds.append(cmd)
    return types.SimpleNamespace(returncode=0, stdout="Successfully installed rich-13.7", stderr="")


pkg_mod.subprocess = types.SimpleNamespace(
    run=fake_subprocess_run, TimeoutExpired=__import__("subprocess").TimeoutExpired
)
try:
    gate_ok = Gate(cfg, lambda l, d, allow_always=True: "o")
    res = pkg_mod.run({"pacote": "rich", "motivo": "tabelas"}, Ctx(cfg=cfg, gate=gate_ok))
    ok("instalar_pacote roda pip correto", "INSTALADO: rich" in res and captured_cmds[0][1:4] == ["-m", "pip", "install"])
    res_bad = pkg_mod.run({"pacote": "x; rm -rf /", "motivo": "teste"}, Ctx(cfg=cfg, gate=gate_ok))
    ok("instalar_pacote recusa nome invalido", "ERRO" in res_bad and not captured_cmds[1:])
finally:
    pkg_mod.subprocess = orig_subprocess

# circuit breaker: chamada identica 3 vezes nao executa
class RepeatLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        joined = " ".join(str(m.get("content", "")) for m in messages if m.get("role") == "tool")
        if "LOOP DETECTADO" in joined:
            return {"role": "assistant", "content": "entendi, mudei de estrategia"}
        return {"role": "assistant", "content": "", "tool_calls": [
            {"id": f"c{self.calls}", "type": "function", "function": {
                "name": "run_python", "arguments": '{"code": "print(1)"}'}}]}

    def summarize(self, text):
        return ""


agent_r = Agent(dict(cfg), RepeatLLM(), Gate(dict(cfg), ask_d))
ans_r = agent_r.run_turn("rode esse print ai")
tool_msgs = [str(m.get("content", "")) for m in agent_r.messages if m.get("role") == "tool"]
ok("loop cortado na 3a chamada identica", any("LOOP DETECTADO" in t for t in tool_msgs) and agent_r.last_compressed is False)
ok("turno fecha com resposta apos corte do loop", ans_r == "entendi, mudei de estrategia" and agent_r.llm.calls <= 5)

# 5 falhas em sequencia fecham a janela (sem virar infinito)
class FailLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        joined = " ".join(str(m.get("content", "")) for m in messages)
        if "falharam em sequencia" in joined:
            return {"role": "assistant", "content": "expliquei o obstaculo ao usuario"}
        return {"role": "assistant", "content": "", "tool_calls": [
            {"id": f"f{self.calls}", "type": "function", "function": {
                "name": f"ferramenta_inexistente_{self.calls}", "arguments": "{}"}}]}

    def summarize(self, text):
        return ""


agent_f = Agent(dict(cfg), FailLLM(), Gate(dict(cfg), ask_d))
ans_f = agent_f.run_turn("tenta ai")
ok("sequencia de falhas encerra turno com explicacao", ans_f == "expliquei o obstaculo ao usuario" and agent_f.llm.calls == 6)

# ---------- perfis de provedor ---------------------------------------------------
from bgh.config import ensure_profiles, list_profiles, load_config, set_active_profile, save_profile

cfg_old = {"provider": "local", "base_url": "http://x/v1", "model": "m1", "api" + "_key": ""}
ensure_profiles(cfg_old)
ok("migra cria perfil do provedor atual", list_profiles(cfg_old) == ["local"] and cfg_old["active_profile"] == "local")
cfg_old.update({"provider": "deepseek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"})
save_profile(cfg_old, "deepseek")
ok("novo provedor nao apaga o local",
   set(list_profiles(cfg_old)) == {"local", "deepseek"} and cfg_old["profiles"]["local"]["model"] == "m1")
ok("trocar perfil ativo muda top-level", set_active_profile(cfg_old, "local") and cfg_old["model"] == "m1")

# wizard duas vezes (2a simulada interativa) acumula perfis no config.json
import bgh.setup_wizard as wiz_mod

answers = iter(["n", "1", "", "", "s", "n"])  # manter? | opcao | url | modelo | atualizar deepseek? sim | testar? nao (orcamento nao pergunta mais)
orig_getpass = wiz_mod.getpass
orig_probe = wiz_mod._probe_context_tokens
wiz_mod.input = lambda prompt="": next(answers)
wiz_mod.getpass = types.SimpleNamespace(getpass=lambda prompt: "")
wiz_mod._probe_context_tokens = lambda probe_cfg: None  # teste hermetico: sem rede
try:
    wiz_mod.run(non_interactive=True, provider="local", api_key="")
    wiz_mod.run()
finally:
    del wiz_mod.input
    wiz_mod.getpass = orig_getpass
    wiz_mod._probe_context_tokens = orig_probe
saved = json.loads((TMP / "config.json").read_text(encoding="utf-8"))
ok("wizard acumula provedores", set(saved["profiles"]) == {"local", "deepseek"} and saved["active_profile"] == "deepseek")
ok("load ativa o ultimo salvo", load_config()["model"] == "deepseek-v4-flash")
ok("wizard define o orcamento sem perguntar numero ao usuario",
   saved["context_budget_chars"] == 60000)

# ---------- parada do usuario + nucleo compartilhado -----------------------------
import threading
import time

from bgh.agent import STOPPED_NOTE as _STOPPED
from bgh.tools import ToolBox


class FakeLLMStream:
    """LLM fake que fala em pedacos e obedece ao pedido de parar no meio."""

    def __init__(self, chunks, chunk_sleep=0.12):
        self.chunks = list(chunks)
        self.chunk_sleep = chunk_sleep

    def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "sem streaming"}

    def summarize(self, text):
        return "resumo fake"

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None, should_stop=None):
        parts = []
        for c in self.chunks:
            if should_stop is not None and should_stop():
                return {"role": "assistant", "content": "".join(parts), "stopped": True}
            parts.append(c)
            if on_text:
                on_text(c)
            time.sleep(self.chunk_sleep)
        return {"role": "assistant", "content": "".join(parts)}


cfg_s = dict(cfg)
cfg_s["stream"] = True
llm_s = FakeLLMStream(["um ", "dois ", "tres ", "quatro ", "cinco "])
agent_s = Agent(cfg_s, llm_s, Gate(cfg_s, ask_d))
agent_s.new_session()
seen_chunks = []
agent_s.on_text_delta = lambda c: seen_chunks.append(c)
threading.Timer(0.30, agent_s.stop_event.set).start()
ans_s = agent_s.run_turn("fale devagar")
ok("parada no meio do streaming fecha o turno", ans_s == _STOPPED)
ok("parada chegou antes do fim das partes", 0 < len(seen_chunks) < 5)
ok("pedaco parcial fica guardado na historia",
   any(m.get("role") == "assistant" and m.get("content") for m in agent_s.messages))


class FakeLLMToolStop:
    """Modelo pede uma ferramenta e o usuario aperta 'parar' antes dela rodar."""

    def __init__(self, ev=None):
        self.ev = ev

    def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "sem streaming"}

    def summarize(self, text):
        return ""

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None, should_stop=None):
        msg = {"role": "assistant", "content": "", "tool_calls": [
            {"id": "z1", "type": "function", "function": {
                "name": "run_command", "arguments": '{"command": "touch ' + str(TMP) + '/marca_parada.txt"}'}}]}
        if self.ev is not None:
            self.ev.set()
        return msg


llm_ts = FakeLLMToolStop()
agent_ts = Agent(cfg_s, llm_ts, Gate(cfg_s, ask_d))
agent_ts.new_session()
llm_ts.ev = agent_ts.stop_event
ans_ts = agent_ts.run_turn("rode isso")
ok("parada cancela a ferramenta antes de ela rodar",
   ans_ts == _STOPPED and not (TMP / "marca_parada.txt").exists())
tool_msgs_ts = [m for m in agent_ts.messages if m.get("role") == "tool"]
ok("tool_call parada ganha resposta valida no historico",
   tool_msgs_ts and "mandou parar" in tool_msgs_ts[0]["content"])

ev3 = threading.Event()
tb3 = ToolBox(dict(cfg), Gate(dict(cfg), ask_d), stop_event=ev3)
threading.Timer(0.4, ev3.set).start()
t0 = time.time()
res3 = tb3.dispatch("run_command", '{"command": "sleep 5"}')
dt = time.time() - t0
ok("run_command e interrompido quando o usuario manda parar",
   res3.startswith("PARADO") and dt < 3.0)
tb_ok = ToolBox(dict(cfg), Gate(dict(cfg), ask_d))  # sem evento de parada
res3b = tb_ok.dispatch("run_command", '{"command": "echo roda_normal"}')
ok("comando normal continua funcionando igual", "exit_code=0" in res3b and "roda_normal" in res3b)


class RecSink:
    """Affiche de teste: so coleta as linhas que o nucleo escreve."""

    def __init__(self):
        self.lines: list[str] = []

    def line(self, text, style=None):
        self.lines.append(str(text))

    def parts(self, segments):
        self.lines.append("".join(str(t) for t, _style in segments))

    def ask_choice(self, title, label, options):
        self.lines.append(f"{title} :: {options[0]}")
        return options[0]

    def sep(self, title=None):
        self.lines.append("-" * 46)
        if title:
            self.lines.append(title)
            self.lines.append("-" * 46)

    def border(self):
        self.lines.append("=" * 46)

    def thinking(self, text):
        self.lines.append(text)

    def answer(self, text):
        self.lines.append(text)

    def tool_event(self, name, preview):
        self.lines.append(f"> {name}")

    def status(self, text):
        pass

    def ask_approval(self, label, detail, allow_always):
        return "d"


from bgh.chat_core import ChatCore, build_approval_options, parse_approval_choice

core_cfg = dict(cfg)
core_cfg.update({"stream": False, "model": "fake-model", "base_url": "http://fake/v1"})
sink_rec = RecSink()
fake_core_llm = FakeLLM([{"role": "assistant", "content": "ola_resposta_core"}])
core_obj = ChatCore(core_cfg, sink_rec, llm=fake_core_llm)
core_obj.banner()
_i_eq = next(i for i,l in enumerate(sink_rec.lines) if l.startswith("===="))
ok("abertura traz o gatinho TEO antes do divisor '='",
   any("TEO" in l for l in sink_rec.lines[:_i_eq])
   and any(l.strip() == "/" + chr(92) + "_/" + chr(92) for l in sink_rec.lines[:_i_eq]))
ok("banner termina com divisor '='",
   any(l.startswith("====") for l in sink_rec.lines[-2:]))
n_ajuda = len(sink_rec.lines)
core_obj.submit("/ajuda")
seg = sink_rec.lines[n_ajuda:]
ok("/ajuda vem entre dois divisores '='",
   seg[0].startswith("====") and seg[-1].startswith("===="))
act = core_obj.submit("oi")
ok("ChatCore roda turno com affiche injetada",
   act == "continue" and any("ola_resposta_core" in l for l in sink_rec.lines))
act = core_obj.submit("/ctx")
ok("/ctx pelo ChatCore mostra o medidor", act == "continue" and any("contexto:" in l for l in sink_rec.lines))
act = core_obj.submit("/sair")
ok("/sair pelo ChatCore encerra", act == "exit")

opts_ap, codes_ap = build_approval_options(True)
ok("menu de licenca tem 4 opcoes o/s/a/d", len(opts_ap) == 4 and codes_ap == ["o", "s", "a", "d"])
ok("Enter sozinho ou invalido = nao (falha fechada)",
   parse_approval_choice("", codes_ap) == "d" and parse_approval_choice("x", codes_ap) == "d")
ok("numero valido escolhe a opcao certa",
   parse_approval_choice("1", codes_ap) == "o" and parse_approval_choice("4", codes_ap) == "d")

try:
    from bgh.tui import run_tui  # noqa: F401
    ok("tela fixa importa (prompt_toolkit presente)", True)
except ImportError:
    ok("tela fixa importa (prompt_toolkit presente)", False)

from bgh.config import DEFAULTS
ok("config traz tela fixa ligada por padrao", DEFAULTS.get("tui") is True)

# uma unica licenca por comando mesmo tocando varias regras
asks_multi: list[str] = []


def ask_multi(label, detail, allow_always):
    asks_multi.append(label)
    return "s"


gate_m = Gate({"command_allowlist": []}, ask_multi)
allowed, _ = gate_m.command_ok('rm /tmp/a.txt && ls -la /')
ok("comando de varias regras pede licenca UMA vez", allowed and len(asks_multi) == 1)
allowed, _ = gate_m.command_ok('rm /tmp/b.txt && ls -la /')
ok("'nesta conversa' silencia as duas regras depois", allowed and len(asks_multi) == 1)
allowed, msg = Gate({"command_allowlist": []}, ask_d).command_ok('rm /tmp/c.txt && ls -la /')
ok("negar numa licenca unica bloqueia o comando todo", not allowed and "BLOQUEADO" in msg)


# --- impressao no historico natural do terminal (v0.2.0) ---
from bgh.tui import LineBoard, flush_plan
ok("motor agora imprime no rolamento do terminal (sem tela alternativa)",
   "full_screen=False" in open("bgh/tui.py").read())

_b = LineBoard()
_b.add("oi", "an", True)
_b.add("par", "th", False)          # streaming: ultimo bloco aberto
_rows = _b.rows(80)
_n, _out = flush_plan(_rows, True, 0, 78)
ok("linha aberta nao sai antes de fechar", len(_out) == 1 and _n == 1)
_b.add("te", "th", False)
_b.close_last()
_rows = _b.rows(80)
_n2, _out2 = flush_plan(_rows, False, _n, 78)
ok("linha fechada vai para o historico sem repetir a anterior",
   len(_out2) == 1 and _out2[0][0][1] == "parte" and _n2 == 2)
_full = [[("an", "x" * 78)]]
_n3, _out3 = flush_plan(_full, True, 0, 78)
ok("linha aberta ja cheia aparece aos poucos (streaming de paragrafo)",
   len(_out3) == 1 and _n3 == 1)
_n4, _out4 = flush_plan(_full, True, 1, 78)
ok("nada reimpresso quando nao ha linha nova", _out4 == [] and _n4 == 1)

# --- divisores '=' do banner e da ajuda ---
from bgh.tui import TuiSink as _TSink
_seen = []
def _emit2(text="", newline=True, style=None):
    _seen.append((str(text), style))
_ts = _TSink(_emit2, lambda: None, {}, width_fn=lambda: 90)
_ts.border()
ok("divisor da tela usa a largura da janela (com folga)",
   _seen[-1][0] == "=" * 88 and _seen[-1][1] == "class:rule")

# ---------- v0.2.5: espera do servidor, parada dentro de ferramenta, busca com teto ----------
import threading as _th
import time as _t

from bgh.llm import LLM as LLM25
from bgh.llm import _timeout_for as _timeout_for25
from bgh.tools import Ctx as Ctx25
from bgh.tools import files as files25
from bgh.tools.guard import STOPPED_NOTE as NOTE_PARADO
from bgh.tools.guard import limit_n as _limit_n, limit_s as _limit_s

ok("modelo local tem teto de espera de 120s",
   _timeout_for25({"base_url": "http://127.0.0.1:30000/v1"}) == 120.0)
ok("servidor remoto tem teto de espera de 300s (contexto grande demora a ser lido)",
   _timeout_for25({"base_url": "https://ia.nubesbr.com/v1/"}) == 300.0)
ok("request_timeout_s do config manda no teto",
   _timeout_for25({"base_url": "https://x/v1/", "request_timeout_s": 45}) == 45.0)
_llm_remote = LLM25({"base_url": "https://ia.nubesbr.com/v1/", "model": "m"})
ok("o cliente OpenAI recebe o teto calculado", float(_llm_remote.client.timeout) == 300.0)
ok("uma pergunta nao vira fila de pedidos: retries padrao = 1",
   _llm_remote.retries == 1 and int(_llm_remote.client.max_retries) == 1)
ok("LLM tem canal de aviso para a tela (espera nunca e silencio)", _llm_remote.on_note is None)
ok("tetos de busca vem do config e tem piso/teto proprios",
   _limit_s({"search_time_limit_s": 9999}, "search_time_limit_s", 20) == 600
   and _limit_n({}, "search_max_files", 20000) == 20000)

# arvore de teste: 400 arquivos sem nenhum match (pior caso da busca)
_arvore = TMP / "arvore_busca"
for _i in range(400):
    _d = _arvore / f"pasta{_i % 20}"
    _d.mkdir(parents=True, exist_ok=True)
    (_d / f"arquivo{_i}.txt").write_text("conteudo sem o padrao procurado\n", encoding="utf-8")
_ctx_lim = Ctx25(cfg={"search_max_files": 100, "search_time_limit_s": 5}, gate=None, stop_event=None)
_res_lim = files25.search_files({"pattern": "zzqx_inexistente", "path": str(_arvore)}, _ctx_lim)
ok("busca para no teto de arquivos e explica em vez de caminhar a arvore inteira",
   "parei depois de" in _res_lim and "pasta mais especifica" in _res_lim)
(_arvore / "alvo.txt").write_text("linha_procurada_aqui\n", encoding="utf-8")
_ctx_sem_limite = Ctx25(cfg={}, gate=None, stop_event=None)
_res_ok = files25.search_files({"pattern": "linha_procurada_aqui", "path": str(_arvore)},
                               _ctx_sem_limite)
ok("busca normal (sem teto apertado) continua achando e sem aviso de limite",
   "alvo.txt" in _res_ok and "parei depois de" not in _res_ok)

_ev_ja_parado = _th.Event()
_ev_ja_parado.set()
_ctx_parado = Ctx25(cfg={}, gate=None, stop_event=_ev_ja_parado)
ok("search_files obedece o 'parar' antes de comecar",
   files25.search_files({"pattern": "qualquer", "path": str(_arvore)}, _ctx_parado)
   .startswith("PARADO"))
ok("read_file obedece o 'parar'",
   files25.read_file({"path": str(_arvore / "alvo.txt")}, _ctx_parado).startswith("PARADO"))
ok("nota de parada e a mesma em toda ferramenta", NOTE_PARADO.startswith("PARADO"))


class FakeLLMParado:
    """Modelo pede uma ferramenta; a ferramenta obedece o 'parar' e devolve PARADO."""

    def __init__(self):
        self.rodadas = 0

    def chat(self, messages, tools=None):
        self.rodadas += 1
        if self.rodadas == 1:
            return {"role": "assistant", "content": "",
                    "tool_calls": [{"id": "p1", "type": "function",
                                    "function": {"name": "search_files",
                                                 "arguments": '{"pattern": "abc"}'}}]}
        return {"role": "assistant", "content": "resposta final"}

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None, should_stop=None):
        return self.chat(messages, tools)

    def summarize(self, text):
        return ""


_llm_par = FakeLLMParado()
_ag_par = Agent(dict(cfg_s), _llm_par, Gate(dict(cfg_s), ask_d))
_ag_par.new_session()
_ag_par.tools.handlers["search_files"] = lambda args, ctx: NOTE_PARADO
_ans_par = _ag_par.run_turn("procure isso")
ok("ferramenta que obedece o 'parar' fecha o turno na hora", _ans_par == _STOPPED)
ok("turno parado nao emenda nova rodada de pergunta ao modelo", _llm_par.rodadas == 1)

_tb_par = ToolBox(dict(cfg), Gate(dict(cfg), ask_o), stop_event=None)
_ev_py = _th.Event()
_th.Timer(0.4, _ev_py.set).start()
_tb_par.ctx.stop_event = _ev_py
_t0_py = _t.time()
_res_py = _tb_par.dispatch("run_python", '{"code": "import time\\nprint(1)\\ntime.sleep(12)"}')
_dt_py = _t.time() - _t0_py
ok("run_python e derrubado quando o usuario manda parar (antes era esperar o script)",
   _res_py.startswith("PARADO") and _dt_py < 3.0)
_ev_py.clear()  # parada anterior so vale para o comando de antes
_res_py_ok = _tb_par.dispatch("run_python", '{"code": "print(2+2)"}')
ok("run_python normal continua funcionando", "exit_code=0" in _res_py_ok and "4" in _res_py_ok)

from bgh.tui import _status_text as _status_text25

_st_busy = {"busy": True, "approval": None, "spin": 0, "ctx": None, "stop_hits": 0,
            "busy_since": _t.time() - 47, "tool": "search_files", "tool_since": _t.time() - 12}
_barra = "".join(seg for _style, seg in _status_text25(_st_busy))
ok("barra de baixo conta os segundos da espera", "rodando... 47s" in _barra)
ok("barra mostra a ferramenta em andamento e ha quanto tempo", "search_files 12s" in _barra)

from bgh.setup_wizard import BUDGET_SUGESTAO, MAX_TOKENS_PRESET

ok("assistente sugere budget maior para o servidor hospedado (cabem 45 mil tokens)",
   BUDGET_SUGESTAO["nubesbr"] == "156000")
ok("perfil remoto vem com saida maior que o pensamento do modelo",
   MAX_TOKENS_PRESET["nubesbr"] == 3072)
ok("config novo traz teto de busca e timeout automatico",
   DEFAULTS.get("search_time_limit_s") == 20 and DEFAULTS.get("request_timeout_s") == 0)

_sink_vazio = RecSink()
_core_vazio = ChatCore(dict(core_cfg), _sink_vazio, llm=FakeLLM([{"role": "assistant", "content": ""}]))
_n_vazio = len(_sink_vazio.lines)
_core_vazio.submit("pergunta sem resposta")
ok("modelo que so pensa e devolve texto vazio ganha aviso na tela",
   any("sem texto de resposta" in l for l in _sink_vazio.lines[_n_vazio:]))
ok("canal de aviso do cliente esta ligado na tela", _core_vazio.llm.on_note is not None)

# ---------- v0.2.5: /ctx com numero define o limite -----------------------------
from bgh.chat_core import help_lines as _help_lines
from bgh.chat_core import parse_budget as _parse_budget

ok("aceita numero puro", _parse_budget("65000") == 65000)
ok("aceita 65k", _parse_budget("65k") == 65000)
ok("aceita milhar com ponto (65.000)", _parse_budget("65.000") == 65000)
ok("aceita '65 mil'", _parse_budget("65 mil") == 65000)
ok("letra nao e numero", _parse_budget("abc") is None)
ok("numero pequeno demais e recusado", _parse_budget("100") is None)
ok("numero absurdo e recusado", _parse_budget("2000000") is None)

_sink_ctx = RecSink()
_core_ctx = ChatCore(dict(core_cfg), _sink_ctx,
                     llm=FakeLLM([{"role": "assistant", "content": "ok"}]))
_orcamento_antes = _core_ctx.agent.ctx_usage()["budget"]
_core_ctx.submit("/ctx 65000")
ok("/ctx 65000 muda o limite que o medidor mostra",
   _orcamento_antes != 65000 and _core_ctx.agent.ctx_usage()["budget"] == 65000)
ok("mudanca e anunciada na tela", any("ajustado para 65000" in l for l in _sink_ctx.lines))
ok("limite novo vai para o config.json (sobrevive ao reabrir o TEO)",
   load_config()["context_budget_chars"] == 65000)

_sink_reaberto = RecSink()
_core_reaberto = ChatCore(dict(load_config()), _sink_reaberto,
                          llm=FakeLLM([{"role": "assistant", "content": "ok"}]))
ok("reabrir o chat ja vem com o limite salvo",
   _core_reaberto.cfg["context_budget_chars"] == 65000)
_linhas_antes = len(_sink_reaberto.lines)
_core_reaberto.submit("/ctx abc")
ok("numero invalido ganha aviso em vez de silencio",
   any("Esse numero nao vale" in l for l in _sink_reaberto.lines[_linhas_antes:]))
ok("numero invalido nao altera o limite guardado",
   _core_reaberto.cfg["context_budget_chars"] == 65000)
_linhas_ctx = len(_sink_reaberto.lines)
_ok_ctx_sozinho = _core_reaberto.submit("/ctx")
ok("/ctx sozinho continua sendo so o medidor (sem numero nao muda nada)",
   _ok_ctx_sozinho == "continue" and _core_reaberto.cfg["context_budget_chars"] == 65000
   and not any("Esse numero nao vale" in l for l in _sink_reaberto.lines[_linhas_ctx:]))
ok("ajuda menciona o /ctx com numero",
   any("/ctx <numero>" in "".join(seg for seg, _ in row) for row in _help_lines()))

# ---------- v0.2.6: /configurar e /doctor na tela, contexto do servidor ---------
from bgh.agent import Agent as _Agent26
from bgh.config import ConfigError as _CE26
from bgh.llm import ContextOverflowError as _COE26
from bgh.llm import LLM as _LLM26

ok("config novo ja nasce com orcamento grande e compactacao antecipada",
   DEFAULTS.get("context_budget_chars") == 156000
   and DEFAULTS.get("context_compress_pct") == 85
   and DEFAULTS.get("context_auto_cap_chars") == 160000)


class _OkLLM26:
    def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "ok_normal"}

    def summarize(self, text):
        return "resumo X"


class _OverLLM26:
    """1o pedido estoura o limite do servidor; depois de compactar responde normal."""

    def __init__(self):
        self.calls = 0
        self.summarizes = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls == 1:
            raise _COE26("O contexto passou do limite que o servidor aceita.")
        return {"role": "assistant", "content": "resposta depois de compactar"}

    def summarize(self, text):
        self.summarizes += 1
        return "resumo curto"

_cfg_soft = dict(core_cfg)
_cfg_soft.update({"context_budget_chars": 12000, "context_compress_pct": 85})
_ag_soft = _Agent26(_cfg_soft, _OkLLM26(), Gate(dict(_cfg_soft), ask_d))
_notas_soft: list[str] = []
_ag_soft.on_note = _notas_soft.append
for _i26 in range(12):
    _ag_soft.messages.append({"role": "user", "content": "x" * 1500})
_ans_soft = _ag_soft.run_turn("pergunta final")
ok("contexto comecando a encher compacta ANTES de esbarrar no teto",
   _ans_soft == "ok_normal" and _ag_soft.last_compressed
   and any("Compactando a conversa em resumo" in n for n in _notas_soft))

# abaixo do ponto de compactacao (85%) nao se mexe na conversa
_cfg_calmo = dict(core_cfg)
_cfg_calmo.update({"context_compress_pct": 85})
_ag_calmo = _Agent26(_cfg_calmo, _OkLLM26(), Gate(dict(_cfg_calmo), ask_d))
_notas_calmo: list[str] = []
_ag_calmo.on_note = _notas_calmo.append
for _i26 in range(12):
    _ag_calmo.messages.append({"role": "user", "content": "z" * 1500})
# orçamento = 125% do tamanho real medido -> medidor em 80%, um pouco antes dos 85%
_est_calmo = _ag_calmo._estimate_chars()
_cfg_calmo["context_budget_chars"] = int(_est_calmo * 1.25)
_msgs_antes = len(_ag_calmo.messages)
_usage_calmo = _ag_calmo.ctx_usage()
ok("antes dos 85% a conversa fica intacta (compactar tarde demais e raro, cedo demais irrita)",
   75 <= _usage_calmo["pct"] < 85 and _ag_calmo._compress_if_needed() is False
   and not _notas_calmo and _ag_calmo.last_compressed is False
   and len(_ag_calmo.messages) == _msgs_antes)

_cfg_over = dict(core_cfg)
_cfg_over.update({"context_budget_chars": 12000, "context_compress_pct": 85})
_ag_over = _Agent26(_cfg_over, _OverLLM26(), Gate(dict(_cfg_over), ask_d))
_notas_over: list[str] = []
_ag_over.on_note = _notas_over.append
for _i26 in range(12):
    _ag_over.messages.append({"role": "user", "content": "y" * 1500})
_ans_over = _ag_over.run_turn("pergunta final")
ok("servidor recusando o tamanho: compacta e tenta de novo sem derrubar o turno",
   _ans_over == "resposta depois de compactar"
   and any("recusou o tamanho do contexto" in n for n in _notas_over))


class _BoomClient26:
    class _Completions:
        def __init__(self, msg):
            self._msg = msg

        def create(self, **kwargs):
            raise Exception(self._msg)

    class _Chat:
        def __init__(self, comp):
            self.completions = comp

    def __init__(self, msg):
        self.chat = self._Chat(self._Completions(msg))


_llm_boom = _LLM26({"base_url": "http://fake/v1", "model": "m", "max_retries": 0})
_llm_boom.client = _BoomClient26("This exceeds the available context size, try increasing it")
try:
    _llm_boom.chat([{"role": "user", "content": "oi"}])
    _detectou = False
except _COE26:
    _detectou = True
ok("erro de contexto do servidor vira caso tratavel (ContextOverflowError)", _detectou)

# API fechada que nao publica contexto na propria API (DeepSeek): vem do catalogo
# models.dev, a mesma fonte de metadados que o Hermes usa.
from bgh import llm as _llmmod26
from bgh.config import PRESETS as _PRESETS26

_orig_requests26 = _llmmod26.requests
_orig_cache26 = _llmmod26._models_dev_cache


class _RespSemAchado26:
    status_code = 404


def _boom_lista26():
    raise RuntimeError("teste hermetico: sem rede")


_llmmod26.requests = types.SimpleNamespace(get=lambda *a, **k: _RespSemAchado26())
_llmmod26._models_dev_cache = {
    "deepseek": {"models": {"deepseek-v4-flash": {"limit": {"context": 1048576}}}},
}
try:
    _llm_md26 = _LLM26({"base_url": "https://api.deepseek.com/v1",
                        "model": "deepseek-v4-flash", "max_retries": 0})
    _llm_md26.client = types.SimpleNamespace(
        models=types.SimpleNamespace(list=_boom_lista26))
    _achado26 = _llm_md26.discover_context()
finally:
    _llmmod26.requests = _orig_requests26
    _llmmod26._models_dev_cache = _orig_cache26
ok("API fechada sem publicacao (DeepSeek): contexto sai do catalogo models.dev",
   _achado26 == 1048576
   and _llmmod26._provider_hint("https://api.deepseek.com/v1") == "deepseek")
ok("preset deepseek veio do nome aposentado para o modelo atual do provedor",
   _PRESETS26["deepseek"]["model"] == "deepseek-v4-flash")
ok("teto de saida por resposta subiu para caber documento HTML numa rodada",
   DEFAULTS["max_tokens"] == 8192)

# Rodape diz quando o numero exibido e teto do TEO, nao o limite do servidor.
from bgh.chat_core import ChatCore as _ChatCore26

_usage26 = {"pct": 3, "budget": 160000, "messages": 3}
_teto_txt = _ChatCore26._ctx_footer_text(
    types.SimpleNamespace(cfg={"server_context_tokens": 1048576}), _usage26)
ok("rodape avisa 'teto' quando o servidor entrega mais que o orcamento",
   "teto" in _teto_txt and "1.048.576 tokens" in _teto_txt)
_normal_txt = _ChatCore26._ctx_footer_text(
    types.SimpleNamespace(cfg={}), _usage26)
ok("rodape segue limpo quando nao ha prova do servidor", "teto" not in _normal_txt)
_cabivel_txt = _ChatCore26._ctx_footer_text(
    types.SimpleNamespace(cfg={"server_context_tokens": 40000}),
    {"pct": 3, "budget": 130000, "messages": 3})
ok("sem 'teto' quando o orcamento ja cabe no que o servidor entrega",
   "teto" not in _cabivel_txt)

# Fechamento de turno estilo Hermes: nota visivel antes de fechar, resposta em
# streaming, instrucao interna em portugues (modelo local nao desvia para ingles).
class _CloseLLM26:
    def __init__(self):
        self.chamadas: list[tuple] = []

    def chat(self, messages, tools=None):
        self.chamadas.append(("chat", tools is not None))
        return {"role": "assistant", "content": "fechamento sem streaming"}

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None,
                    should_stop=None):
        self.chamadas.append(("stream", tools is not None))
        if tools is not None:
            return {"role": "assistant", "content": "", "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "fantasma", "arguments": "{}"}}]}
        return {"role": "assistant", "content": "fechamento streamed em portugues"}

    def summarize(self, transcript):
        return "resumo"


_cfg_close = dict(core_cfg)
_cfg_close.update({"max_tool_rounds": 2, "stream": True, "context_budget_chars": 150000})
_llm_close = _CloseLLM26()
_ag_close = _Agent26(_cfg_close, _llm_close, Gate(dict(_cfg_close), ask_d))
_notas_close: list[str] = []
_ag_close.on_note = _notas_close.append
_ans_close = _ag_close.run_turn("probe")
ok("limite de rodadas fecha o turno com nota visivel na tela",
   any("Limite de ferramentas" in n for n in _notas_close))
ok("fechamento usa streaming quando o servidor suporta (sem silencio morto)",
   _ans_close == "fechamento streamed em portugues"
   and _llm_close.chamadas[-1] == ("stream", False))
ok("instrucao de fechamento em portugues",
   any("Responda em portugues" in str(m.get("content", ""))
       for m in _ag_close.messages if m.get("role") == "user"))
_cfg_fail = dict(_cfg_close)
_cfg_fail["max_tool_rounds"] = 8
_llm_fail = _CloseLLM26()
_ag_fail = _Agent26(_cfg_fail, _llm_fail, Gate(dict(_cfg_fail), ask_d))
_notas_fail: list[str] = []
_ag_fail.on_note = _notas_fail.append
_ag_fail.run_turn("probe")
ok("5 falhas em sequencia fecham o turno com aviso na tela",
   any("falharam em sequencia" in n for n in _notas_fail))
ok("teto de rodadas do config subiu para pesquisa/redacao longa",
   DEFAULTS["max_tool_rounds"] == 20)

# Cabecalho de resposta por chamada do modelo (a resposta final nao sai mais
# colada no bloco de pensamento quando o turno teve varias rodadas de ferramenta).
class _SinkCab26:
    def __init__(self):
        self.seps: list[str] = []

    def ask_approval(self, *a, **k):
        return "n"

    def tool_event(self, *a, **k):
        pass

    def line(self, *a, **k):
        pass

    def sep(self, title=None, *a, **k):
        self.seps.append(str(title))

    def thinking(self, *a, **k):
        pass

    def answer(self, *a, **k):
        pass


_sink_cab26 = _SinkCab26()
_core_cab26 = _ChatCore26(dict(core_cfg), _sink_cab26, llm=_CloseLLM26())
ok("callback de novo bloco ligado no agente",
   _core_cab26.agent.on_round_start is not None)
_core_cab26.agent.on_round_start()
_core_cab26._on_reasoning("pens A")
_core_cab26._on_text("resp A")
_core_cab26._on_reasoning("pens A2")
_core_cab26._on_text("resp A2")
ok("uma mesma chamada do modelo tem um unico bloco de resposta",
   sum(1 for s in _sink_cab26.seps if s == "resposta") == 1)
_core_cab26.agent.on_round_start()
_core_cab26._on_reasoning("pens B")
_core_cab26._on_text("resp B")
ok("chamada nova do modelo ganha cabecalho 'resposta' de novo",
   sum(1 for s in _sink_cab26.seps if s == "resposta") == 2)

# assistente pergunta ao servidor quanto ele entrega e sugere o valor dele (com teto)
_orig_probe26 = wiz_mod._probe_context_tokens
wiz_mod._probe_context_tokens = lambda probe_cfg: 262144  # motor publicando 262144 tokens
_ditos26: list[str] = []
_perguntas26: list[str] = []


def _ask_dinamico26(prompt, default="", secret=False):
    _perguntas26.append(prompt)
    if prompt.startswith("Manter"):
        return "n"
    if prompt.startswith("Opcao"):
        return "3"  # local: base 127.0.0.1 passa no guarda de sondagem sem chave
    if prompt.startswith("Testar"):
        return "n"
    return default


try:
    wiz_mod.run(ask=_ask_dinamico26, say=lambda *a: _ditos26.append(" ".join(str(x) for x in a)))
finally:
    wiz_mod._probe_context_tokens = _orig_probe26
_salvo26 = json.loads((TMP / "config.json").read_text(encoding="utf-8"))
ok("orcamento herdado do servidor sem pergunta de numero (com teto de leitura)",
   _salvo26["context_budget_chars"] == 160000
   and _salvo26.get("server_context_tokens") == 262144
   and any("herdado do servidor" in d and "262144" in d for d in _ditos26)
   and not any("Orcamento de contexto em caracteres" in p for p in _perguntas26))

# /configurar dentro do chat: assistente roda na tela e a conexao nova vale na hora
_orig_run26 = wiz_mod.run
_pedidos26: list[bool] = []


def _fake_setup26(ask=None, say=None, from_chat=False, **kw):
    _pedidos26.append(ask is not None and say is not None and from_chat is True)
    _cfg_novo26 = load_config()
    _cfg_novo26["model"] = "modelo-novo"
    _cfg_novo26["base_url"] = "http://novo/v1"
    from bgh.config import save_config as _save26

    _save26(_cfg_novo26)
    return 0


wiz_mod.run = _fake_setup26
try:
    _sink26 = RecSink()
    _sink26.ask_line = lambda prompt, default="", secret=False: default
    _core26 = ChatCore(dict(load_config()), _sink26,
                       llm=FakeLLM([{"role": "assistant", "content": "ok"}]))
    _core26.submit("/configurar")
    ok("/configurar roda o assistente com perguntas da tela", _pedidos26 == [True])
    ok("conexao nova entra no core, no agente e e anunciada na tela",
       _core26.cfg["model"] == "modelo-novo" and _core26.agent.llm is _core26.llm
       and any("Conexao agora: modelo-novo" in l for l in _sink26.lines))
finally:
    wiz_mod.run = _orig_run26

ok("ajuda menciona /configurar e /doctor",
   any("/configurar" in "".join(seg for seg, _ in row) for row in _help_lines())
   and any("/doctor" in "".join(seg for seg, _ in row) for row in _help_lines()))
ok("affiches conhecem a pergunta de texto livre (ask_line)",
   hasattr(core_mod.ConsoleSink(), "ask_line") and hasattr(_TSink, "ask_line"))

_st_hot26 = {"busy": False, "approval": None, "spin": 0, "stop_hits": 0,
             "ctx": "contexto: 91% de 156000 chars (20 mensagens)", "ctx_pct": 91,
             "busy_since": 0.0, "tool": None, "tool_since": 0.0}
ok("barra de baixo fica na cor de alerta quando o contexto passa do ponto de compactacao",
   _status_text25(_st_hot26)[0][0] == "class:footer.hot")
ok("barra continua normal logo abaixo dos 85%",
   _status_text25({**_st_hot26, "ctx_pct": 80})[0][0] == "class:footer")

from bgh import config as _cfg_mod26
from bgh.cli import doctor_report as _doctor_report26

_orig_load26 = _cfg_mod26.load_config


def _sem_conexao26():
    raise _CE26("TEO ainda nao configurado (sondagem dos testes)")


_cfg_mod26.load_config = _sem_conexao26
try:
    _linhas_doc26: list[str] = []
    _doctor_report26(lambda t: _linhas_doc26.append(str(t)))
finally:
    _cfg_mod26.load_config = _orig_load26
ok("/doctor mostra maquina, GPU e conexao na propria tela",
   any("Diagnostico do TEO" in l for l in _linhas_doc26)
   and any("Conexao com o modelo" in l for l in _linhas_doc26)
   and any("sem conexao ainda" in l for l in _linhas_doc26))

print(f"\nTODOS OS {PASS} TESTES PASSARAM")

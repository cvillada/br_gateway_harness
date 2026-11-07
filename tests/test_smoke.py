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


class _ListLLM26:
    """LLM fake que publica lista de modelos (para os comandos unificados)."""

    def __init__(self):
        self.cfg = {}

    def list_models(self):
        return ["alpha-model", "beta-model"]

    def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "n/a"}


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
                     llm=_ListLLM26())
_orcamento_antes = _core_ctx.agent.ctx_usage()["budget"]
_core_ctx.submit("/ctx 65000")
ok("/ctx 65000 muda o limite que o medidor mostra",
   _orcamento_antes != 65000 and _core_ctx.agent.ctx_usage()["budget"] == 65000)
ok("mudanca e anunciada na tela", any("ajustado para 65000" in l for l in _sink_ctx.lines))
ok("limite novo vai para o config.json (sobrevive ao reabrir o TEO)",
   load_config()["context_budget_chars"] == 65000)

_sink_reaberto = RecSink()
_core_reaberto = ChatCore(dict(load_config()), _sink_reaberto,
                          llm=_ListLLM26())
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
# orcamento = 125% do tamanho real medido -> medidor em 80%, um pouco antes dos 85%
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

# Steering estilo Hermes: mensagem digitada no meio do processamento chega ao
# modelo na proxima fronteira de rodada, sem derrubar o turno.
class _SteerLLM26:
    def __init__(self, agent_ref):
        self.agent_ref = agent_ref
        self.chamadas = 0
        self.msgs_vistas: list[int] = []

    def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "sem streaming"}

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None,
                    should_stop=None):
        self.chamadas += 1
        self.msgs_vistas.append(len(messages))
        if self.chamadas == 1:
            # o usuario "digita" enquanto o modelo ainda esta respondendo
            self.agent_ref[0].steer("muda de plano: foca no log")
            return {"role": "assistant", "content": "", "tool_calls": [
                {"id": "st1", "type": "function",
                 "function": {"name": "fantasma", "arguments": "{}"}}]}
        return {"role": "assistant", "content": "entendido, ajustei o plano"}

    def summarize(self, transcript):
        return "resumo"


_holder26: list = []
_llm_steer26 = _SteerLLM26(_holder26)
_cfg_steer26 = dict(core_cfg)
_cfg_steer26["stream"] = True  # steering via streaming, como na tela real
_ag_steer26 = _Agent26(_cfg_steer26, _llm_steer26, Gate(dict(_cfg_steer26), ask_d))
_holder26.append(_ag_steer26)
_notas_steer26: list[str] = []
_ag_steer26.on_note = _notas_steer26.append
_ans_steer26 = _ag_steer26.run_turn("trabalho longo")
ok("steering do meio do turno e injetado entre ferramentas e a proxima chamada do modelo",
   _ans_steer26 == "entendido, ajustei o plano"
   and any("durante o processamento" in str(m.get("content", ""))
           and "foca no log" in str(m.get("content", ""))
           for m in _ag_steer26.messages if m.get("role") == "user")
   and _llm_steer26.msgs_vistas[1] >= _llm_steer26.msgs_vistas[0] + 2
   and any("no meio do turno" in n for n in _notas_steer26))

# Steer que chegou tarde (turno ja fechando) vira o proximo turno sozinho.
class _LateLLM26:
    def __init__(self):
        self.chamadas = 0
        self.agent_ref: list = []

    def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "sem streaming"}

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None,
                    should_stop=None):
        self.chamadas += 1
        if self.chamadas == 1:
            self.agent_ref[0].steer("qual a sua versao?")
            if on_text:
                on_text("primeira resposta")
            return {"role": "assistant", "content": "primeira resposta"}
        if on_text:
            on_text("versao 0.2.6")
        return {"role": "assistant", "content": "versao 0.2.6"}

    def summarize(self, transcript):
        return "resumo"


class _SinkLate26(_SinkCab26):
    def __init__(self):
        super().__init__()
        self.textos: list[str] = []

    def line(self, *a, **k):
        self.textos.append(str(a[0] if a else ""))

    def answer(self, *a, **k):
        self.textos.append(str(a[0] if a else ""))


_sink_late26 = _SinkLate26()
_llm_late26 = _LateLLM26()
_cfg_late26 = dict(core_cfg)
_cfg_late26["stream"] = True
_core_late26 = _ChatCore26(_cfg_late26, _sink_late26, llm=_llm_late26)
_llm_late26.agent_ref.append(_core_late26.agent)
_core_late26.submit("pergunta original")
ok("steering tardio vira o proximo turno automaticamente (nada se perde)",
   _llm_late26.chamadas == 2
   and any("voce> qual a sua versao?" in ln for ln in _sink_late26.textos)
   and any("versao 0.2.6" in ln for ln in _sink_late26.textos))

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
                       llm=_ListLLM26())
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

# ---- emenda 3 da 0.2.6: erros amigaveis, comandos unificados, /pensamento, titulo da janela ----
from bgh.chat_core import help_lines as _help_lines26
from bgh.chat_core import set_window_title as _swt26
from bgh import prompts as _prompts26

_cmds26 = [seg[0][0].strip() for seg in _help_lines26() if seg and seg[0][0].strip().startswith("/")]
ok("ajuda unificada: /modelo faz lista e escolha (sem /modelos na lista)",
   any(c == "/modelo" for c in _cmds26) and not any(c.startswith("/modelos") for c in _cmds26))
ok("ajuda unificada: /provedor faz lista e troca (sem /provedores na lista)",
   any(c == "/provedor" for c in _cmds26) and not any(c.startswith("/provedores") for c in _cmds26))
ok("ajuda traz /pensamento com liga/desliga no lugar de /thinking",
   any(c.startswith("/pensamento") for c in _cmds26) and not any(c.startswith("/thinking") for c in _cmds26))
ok("ajuda tem UMA linha so para /ctx (medidor e limite na mesma linha)",
   sum(1 for c in _cmds26 if c == "/ctx" or c.startswith("/ctx ")) == 1)


_sink_m26 = RecSink()
_cfg_m26 = dict(core_cfg)
_cfg_m26["model"] = "alpha-model"  # para a lista marcar o que esta em uso
_core_m26 = ChatCore(_cfg_m26, _sink_m26, llm=_ListLLM26())
_core_m26.submit("/modelo")
ok("/modelo sozinho lista os modelos do servidor",
   any("1. alpha-model" in l for l in _sink_m26.lines))
ok("modelo em uso aparece marcado '(em uso)' na lista, igual ao provedor",
   any("1. alpha-model (em uso)" in l for l in _sink_m26.lines)
   and not any("(atual)" in l for l in _sink_m26.lines))
_core_m26.submit("/modelo 2")
ok("/modelo 2 escolhe da lista que acabou de ser mostrada",
   _core_m26.cfg["model"] == "beta-model")
_sink_alias26 = RecSink()
_core_alias26 = ChatCore(dict(core_cfg), _sink_alias26, llm=_ListLLM26())
_core_alias26.submit("/modelos")
ok("apelido antigo /modelos continua aceito (so saiu da ajuda)",
   any("1. alpha-model" in l for l in _sink_alias26.lines))
ok("sem igual exato: lista mostra o modelo em uso em linha propria (ID renomeado pelo provedor)",
   any("modelo em uso: fake-model" in l for l in _sink_alias26.lines))

_cfg_p26 = dict(core_cfg)
_cfg_p26["profiles"] = {
    "um": {"provider": "local", "base_url": "http://a/v1", "api_key": "k1", "model": "m1"},
    "dois": {"provider": "local", "base_url": "http://b/v1", "api_key": "k2", "model": "m2"},
}
_cfg_p26["active_profile"] = "um"
_sink_p26 = RecSink()
_core_p26 = ChatCore(_cfg_p26, _sink_p26, llm=_ListLLM26())
_core_p26.submit("/provedor")
ok("/provedor sozinho lista os provedores cadastrados",
   any("1. um" in l and "m1" in l for l in _sink_p26.lines))
_core_p26.submit("/provedor dois")
ok("/provedor dois troca o provedor em uso",
   _cfg_p26.get("active_profile") == "dois")

_sink_pen26 = RecSink()
_core_pen26 = ChatCore(dict(core_cfg), _sink_pen26,
                       llm=_ListLLM26())
_core_pen26.submit("/pensamento desliga")
ok("/pensamento desliga so esconde a tela (show_thinking=False) e nao muda o envio ao servidor",
   _core_pen26.cfg["show_thinking"] is False and load_config()["show_thinking"] is False
   and _core_pen26.cfg.get("thinking") in (None, "auto"))
_core_pen26.submit("/pensamento liga")
ok("/pensamento liga volta a mostrar o bloco cinza", _core_pen26.cfg["show_thinking"] is True)
_core_pen26.submit("/pensamento high")
ok("nivel avancado continua sendo o nivel enviado ao servidor", _core_pen26.cfg["thinking"] == "high")
_antes_bad26 = len(_sink_pen26.lines)
_core_pen26.submit("/pensamento xyz")
ok("nivel invalido ganha aviso claro apontando liga/desliga",
   any("Use /pensamento liga" in l for l in _sink_pen26.lines[_antes_bad26:]))
_core_pen26.submit("/thinking low")
ok("apelido antigo /thinking continua aceito", _core_pen26.cfg["thinking"] == "low")

# Renderizacao: com a tela desligada o bloco cinza nao aparece; com ela ligada, aparece.
_cfg_cinza_off26 = dict(core_cfg)
_cfg_cinza_off26["show_thinking"] = False
_sink_cinza_off26 = RecSink()
_core_cinza_off26 = ChatCore(_cfg_cinza_off26, _sink_cinza_off26, llm=_ListLLM26())
_core_cinza_off26._on_reasoning("raciocinio que nao deve aparecer")
ok("tela desligada: nenhum caractere do pensamento chega ao usuario",
   not any("raciocinio que nao deve aparecer" in l for l in _sink_cinza_off26.lines)
   and not any("pensamento do modelo" in l for l in _sink_cinza_off26.lines))
_sink_cinza_on26 = RecSink()
_core_cinza_on26 = ChatCore(dict(core_cfg), _sink_cinza_on26, llm=_ListLLM26())
_core_cinza_on26._on_reasoning("raciocinio visivel")
ok("tela ligada (padrao): cabecalho e texto do pensamento aparecem",
   any("pensamento do modelo" in l for l in _sink_cinza_on26.lines)
   and any("raciocinio visivel" in l for l in _sink_cinza_on26.lines))

# /atualizar: comparacao de versao hermetica (GitHub e pip simulados).
from bgh import updater as _upd26
from bgh import __version__ as _ver_instalada26

ok("comparacao de versao funciona por numeros",
   _upd26.update_needed("0.2.6", "v0.2.7")
   and not _upd26.update_needed("0.2.6", "v0.2.6")
   and not _upd26.update_needed("0.2.6", "v0.2.5")
   and _upd26.version_tuple("v0.10.2") > _upd26.version_tuple("v0.9.9"))


class _RespFake26:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _payload_novo26(tag):
    return {"tag_name": tag,
            "assets": [{"name": f"bgh_motor-{tag.lstrip('v')}-py3-none-any.whl",
                        "browser_download_url": "https://github.com/fake/x.whl"}]}


_orig_get26 = _upd26.requests.get
_orig_run26 = _upd26.subprocess.run
_cmds_upd26: list[list] = []
try:
    # Cenario A: existe versao nova -> pede licenca (RecSink responde opcao 1) e roda o pip certo.
    _upd26.requests = types.SimpleNamespace(
        get=lambda *a, **k: _RespFake26(_payload_novo26("v9.9.9")))
    _upd26.subprocess.run = lambda cmd, **k: (
        _cmds_upd26.append(cmd),
        types.SimpleNamespace(returncode=0, stdout="", stderr=""))[1]
    _sink_upd26 = RecSink()
    _core_upd26 = ChatCore(dict(core_cfg), _sink_upd26, llm=_ListLLM26())
    _core_upd26.submit("/atualizar")
    ok("/atualizar encontra versao nova e pede licenca antes de instalar",
       any("ATUALIZAR O TEO" in l for l in _sink_upd26.lines)
       and any("Baixando e instalando a versao v9.9.9" in l for l in _sink_upd26.lines))
    ok("instala com a receita oficial (pip --no-deps --force-reinstall no wheel da release)",
       len(_cmds_upd26) == 1 and "--force-reinstall" in _cmds_upd26[0]
       and "--ignore-installed" in _cmds_upd26[0]
       and "--no-deps" in _cmds_upd26[0] and _cmds_upd26[0][-1].endswith(".whl"))
    ok("sucesso manda fechar e reabrir para o codigo novo valer",
       any("Atualizado para v9.9.9" in l and "abra o TEO de novo" in l for l in _sink_upd26.lines))

    # Cenario B: mesma versao -> avisa que esta atualizado e pronto, sem perguntar nada.
    _upd26.requests = types.SimpleNamespace(
        get=lambda *a, **k: _RespFake26(_payload_novo26("v" + _ver_instalada26)))
    _sink_upd_b26 = RecSink()
    _core_upd_b26 = ChatCore(dict(core_cfg), _sink_upd_b26, llm=_ListLLM26())
    _core_upd_b26.submit("/atualizar")
    ok("mesma versao: avisa 'ja esta atualizado' e nao oferece instalacao",
       any("ja esta atualizado" in l for l in _sink_upd_b26.lines)
       and not any("ATUALIZAR O TEO" in l for l in _sink_upd_b26.lines)
       and len(_cmds_upd26) == 1)  # nenhum pip novo foi rodado

    # Cenario C: usuario recusa -> nada muda.
    _upd26.requests = types.SimpleNamespace(
        get=lambda *a, **k: _RespFake26(_payload_novo26("v9.9.9")))
    _sink_upd_c26 = RecSink()
    _sink_upd_c26.ask_choice = lambda title, label, options: options[1]
    _core_upd_c26 = ChatCore(dict(core_cfg), _sink_upd_c26, llm=_ListLLM26())
    _core_upd_c26.submit("/atualizar")
    ok("licenca negada: cancela sem tocar em nada",
       any("cancelada" in l for l in _sink_upd_c26.lines) and len(_cmds_upd26) == 1)

    # Cenario D: GitHub inacessivel -> frase amigavel, nunca traceback.
    def _boom26(*a, **k):
        raise ConnectionError("sem internet")

    _upd26.requests = types.SimpleNamespace(get=_boom26)
    _sink_upd_d26 = RecSink()
    _core_upd_d26 = ChatCore(dict(core_cfg), _sink_upd_d26, llm=_ListLLM26())
    _core_upd_d26.submit("/atualizar")
    ok("sem conexao: aviso simples na tela, nada de pilha python",
       any("Nao consegui verificar" in l for l in _sink_upd_d26.lines)
       and not any("Traceback" in l for l in _sink_upd_d26.lines))
finally:
    _upd26.requests = _orig_get26
    _upd26.subprocess.run = _orig_run26
ok("ajuda anuncia o /atualizar",
   any(c.startswith("/atualizar") for c in _cmds26))

# /nov redesenha o medidor na hora: a barra nao pode continuar mostrando a leitura velha.
_sink_nov27 = RecSink()
_core_nov27 = ChatCore(dict(core_cfg), _sink_nov27, llm=_OkLLM26())
_core_nov27.submit("falar um")
_core_nov27.submit("falar dois")
_core_nov27.agent.last_compressed = True   # simula compactacao que aconteceu na conversa antiga
_core_nov27.submit("/nov")
_idx_zer27 = max(i for i, l in enumerate(_sink_nov27.lines) if "zerada" in l)
_depois27 = _sink_nov27.lines[_idx_zer27 + 1:]
_ctx_apos27 = [l for l in _depois27 if l.startswith("contexto:")]
ok("/nov redesenha o medidor logo apos zerar (rodape mostra a leitura nova)",
   len(_ctx_apos27) >= 1 and "(1 mensagens)" in _ctx_apos27[-1])
ok("/nov derruba o aviso 'Contexto compactado' herdado da conversa zerada",
   _core_nov27.agent.last_compressed is False
   and not any("compactado" in l for l in _depois27))

# Barra de contexto segue o servidor (emenda da 0.2.7): troca de modelo/provedor
# e reabertura nunca deixam numero de servidor anterior na tela.
from bgh.setup_wizard import CHARS_POR_TOKEN as _CPT28, FOLGA_LEITURA as _FL28


class _CtxLLM28(_ListLLM26):
    """Servidor fake que publica (ou nao) seu teto de tokens; conta as sondas."""

    def __init__(self, tokens_pub):
        super().__init__()
        self.tokens_pub = tokens_pub
        self.probe_calls = 0

    def discover_context(self):
        self.probe_calls += 1
        return self.tokens_pub


def _cfg_ctx28(**extra):
    c28 = dict(core_cfg)
    c28["profiles"] = {
        "servidor_a": {"base_url": "http://a/v1", "api_" + "key": "k", "model": "alpha-model"},
        "servidor_b": {"base_url": "http://b/v1", "api_" + "key": "k", "model": "beta-model"},
    }
    c28["active_profile"] = "servidor_a"
    c28.update(extra)
    return c28


# Cenario relatado pelo dono do projeto: config guarda 1M de outro provedor; servidor atual entrega 262144.
_cfg_sw28 = _cfg_ctx28(server_context_tokens=1048576,
                       server_context_key="https://api.deepseek.com/v1|deepseek-flash")
_llm_sw28 = _CtxLLM28(262144)
_sink_sw28 = RecSink()
_core_sw28 = ChatCore(_cfg_sw28, _sink_sw28, llm=_llm_sw28)
_core_sw28.submit("/modelo")   # popula a lista como o usuario faz antes de escolher numero
_core_sw28.submit("/modelo 1")
_ok_linhas28 = [l for l in _sink_sw28.lines if l.startswith("contexto:")]
ok("troca de modelo re-sonda o servidor e a barra passa a mostrar o teto dele (262.144)",
   _cfg_sw28["server_context_tokens"] == 262144
   and _cfg_sw28.get("server_context_key") == "http://fake/v1|alpha-model"
   and any("servidor entrega 262.144 tokens" in l for l in _ok_linhas28))
ok("numero de servidor anterior nao sobrevive: a chave grava a procedencia",
   "deepseek" not in str(_cfg_sw28.get("server_context_key")))

# Troca para servidor que NAO publica nada: numero velho sai da barra (nao mente).
_cfg_off28 = _cfg_ctx28(server_context_tokens=1048576,
                        server_context_key="http://fake/v1|fake-model")  # pertence ao servidor em uso
_llm_off28 = _CtxLLM28(None)
_sink_off28 = RecSink()
_core_off28 = ChatCore(_cfg_off28, _sink_off28, llm=_llm_off28)
ok("reabertura com numero do proprio servidor/modelo nao paga rede de novo",
   _llm_off28.probe_calls == 0 and _cfg_off28["server_context_tokens"] == 1048576)
_core_off28.submit("/provedor 2")
ok("provedor novo que nao publica teto: valor antigo desaparece da barra",
   "server_context_tokens" not in _cfg_off28
   and not any("servidor entrega" in l for l in _sink_off28.lines))

# Servidor pequeno: orcamento se ajusta para baixo para comprimir antes de quebrar.
_cfg_small28 = _cfg_ctx28(context_budget_chars=156000)
_llm_small28 = _CtxLLM28(8192)
_sink_small28 = RecSink()
_core_small28 = ChatCore(_cfg_small28, _sink_small28, llm=_llm_small28)
_core_small28.submit("/modelo")   # popula a lista antes de escolher o numero
_core_small28.submit("/modelo 2")
_esperado28 = max(8000, int(8192 * _CPT28 * _FL28))
ok("servidor com teto menor reduz o orcamento na hora (compressao acontece antes do estouro)",
   _cfg_small28["context_budget_chars"] == _esperado28
   and _core_small28.agent.cfg.get("context_budget_chars") == _esperado28)

# Reabertura com numero de OUTRO servidor e servidor mudo: barra nao mostra numero emprestado.
_cfg_stale28 = _cfg_ctx28(server_context_tokens=1048576,
                          server_context_key="http://outro/v1|modelo-antigo")
_sink_stale28 = RecSink()
_core_stale28 = ChatCore(_cfg_stale28, _sink_stale28, llm=_CtxLLM28(None))
ok("procedencia batida + servidor sem publicacao: numero velho e retirado na abertura",
   "server_context_tokens" not in _cfg_stale28)

_sink_err26 = RecSink()
_core_err26 = ChatCore(dict(core_cfg), _sink_err26,
                       llm=_ListLLM26())


def _explode26(texto, imagem=None):
    raise ValueError("boom simulado dos testes")


_core_err26.agent.run_turn = _explode26
_ret_err26 = _core_err26.submit("oi")
ok("falha tecnica inesperada nunca vira traceback na tela",
   _ret_err26 == "continue"
   and any("Algo deu errado no TEO" in l for l in _sink_err26.lines)
   and not any("Traceback" in l or "ValueError" in l for l in _sink_err26.lines))
_log_err26 = Path(os.environ["BGH_HOME"], "erro.log")
ok("detalhe tecnico fica guardado no erro.log com a pilha completa",
   _log_err26.is_file() and "boom simulado" in _log_err26.read_text(encoding="utf-8")
   and "Traceback" in _log_err26.read_text(encoding="utf-8"))

_orig_system26 = _prompts26.platform.system
_prompts26.platform.system = lambda: "Windows"
try:
    _bloco_win26 = _prompts26.environment_block()
finally:
    _prompts26.platform.system = _orig_system26
ok("no Windows o prompt exige cmd.exe desde a primeira tentativa e veta bash",
   "cmd.exe" in _bloco_win26 and "findstr" in _bloco_win26 and "2>/dev/null" in _bloco_win26)

# Este teste perguntava o sistema REAL: rodando no CI do Windows ele reprovava
# (o bloco do cmd.exe aparecia, como devia). Simular os dois lados deixa a suite
# igual em qualquer maquina.
_prompts26.platform.system = lambda: "Linux"
try:
    _bloco_lin26 = _prompts26.environment_block()
finally:
    _prompts26.platform.system = _orig_system26
ok("em Linux o prompt nao fala de cmd (so aparece na maquina certa)",
   "cmd.exe" not in _bloco_lin26)

import contextlib as _ctxlib26
import io as _io26
import shutil as _shutil26

_st_extra26 = {**_st_hot26, "ctx": "contexto: 3% de 160000 chars (1 mensagens)",
               "ctx_pct": 3, "ctx_extra": " | teto; o servidor entrega 1.048.576 tokens"}
_orig_gts26 = _shutil26.get_terminal_size
try:
    _shutil26.get_terminal_size = lambda *a: os.terminal_size((80, 24))
    _fr80_26 = _status_text25(dict(_st_extra26))[0][1]
    _shutil26.get_terminal_size = lambda *a: os.terminal_size((140, 24))
    _fr140_26 = _status_text25(dict(_st_extra26))[0][1]
finally:
    _shutil26.get_terminal_size = _orig_gts26
ok("janela estreita: o medidor encolhe, as teclas ficam inteiras e nada e cortado no meio",
   len(_fr80_26) <= 78 and _fr80_26.endswith("/ajuda") and "ENTER = falar" in _fr80_26
   and "ctx 3%" in _fr80_26 and "1.048.576" not in _fr80_26)
ok("janela larga: medidor + teto + explicacao cabem juntos numa linha",
   "1.048.576 tokens" in _fr140_26 and "ENTER = falar" in _fr140_26
   and "\n" not in _fr140_26)

from bgh.tools.skills import BUNDLED_SKILLS_DIR as _BUNDLED26
from bgh.tools.skills import discover as _discover26, index_lines as _index_lines26

_nomes_fab26 = sorted(p.name for p in _BUNDLED26.iterdir() if (p / "SKILL.md").is_file())
ok("fabrica do pacote traz as skills spec, dev, dev-web e tdd",
   all(s in _nomes_fab26 for s in ("spec", "dev", "dev-web", "tdd")))
_idx26 = "\n".join(_index_lines26(_discover26()))
ok("indice do system prompt anuncia as skills novas ao modelo (descoberta direto no pacote)",
   all(f"/{s}" in _idx26 or f"- {s}" in _idx26 or s in _idx26
       for s in ("spec", "dev", "dev-web", "tdd")))

_buf_tit26 = _io26.StringIO()
# Mesma razao do teste do prompt: no Windows o titulo vai por API da janela, entao
# o caminho de terminal (OSC) e simulado para a suite valer nos tres sistemas.
_orig_osname26 = os.name
os.name = "posix"
try:
    with _ctxlib26.redirect_stdout(_buf_tit26):
        _core_tit26 = ChatCore(dict(core_cfg), RecSink(),
                               llm=_ListLLM26())
        _core_tit26.banner()
finally:
    os.name = _orig_osname26
ok("abertura batiza a janela do terminal como 'TEO Agent' (no Windows e via API da janela)",
   "\x1b]0;TEO Agent\x07" in _buf_tit26.getvalue())

# ---------- 0.2.8: limite de uso/cota do provedor (429) -----------------------
from bgh.llm import LLM as _LLM27
from bgh.llm import LLMError as _LLMErr27
from bgh.llm import LLMRateLimitError as _RateErr27


class _StatusErr27(Exception):
    """Falha no formato dos SDKs: status HTTP e, as vezes, cabecalhos."""

    def __init__(self, msg, status=429, headers=None):
        super().__init__(msg)
        self.status_code = status
        if headers is not None:
            self.response = types.SimpleNamespace(headers=headers)


class _ClientErr27:
    """Cliente que sempre falha (sem rede): anota cada pedido feito."""

    class _Comp:
        def __init__(self, exc, box):
            self._exc = exc
            self._box = box

        def create(self, **kwargs):
            self._box.append(bool(kwargs.get("stream")))
            raise self._exc

    class _Chat:
        def __init__(self, comp):
            self.completions = comp

    def __init__(self, exc):
        self.pedidos: list[bool] = []
        self.chat = self._Chat(self._Comp(exc, self.pedidos))


def _llm_falha27(exc):
    llm = _LLM27({"base_url": "http://fake/v1", "model": "m", "max_retries": 0})
    llm.client = _ClientErr27(exc)
    return llm


def _captura27(fn):
    try:
        fn()
        return None
    except Exception as exc:  # noqa: BLE001 - o proprio tipo do erro e a prova
        return exc


_llm_429 = _llm_falha27(_StatusErr27("Error code: 429 - rate limit reached"))
_err_429 = _captura27(lambda: _llm_429.chat([{"role": "user", "content": "oi"}]))
ok("limite de uso do provedor (429) vira aviso tratavel, nao 'falha ao falar com o modelo'",
   isinstance(_err_429, _RateErr27) and isinstance(_err_429, _LLMErr27))
ok("aviso do 429 diz em palavra simples o que fazer (esperar ou trocar de provedor)",
   "pediu para esperar" in str(_err_429) and "Espere um pouco" in str(_err_429)
   and "/provedor" in str(_err_429))
ok("429 nao vira fila de pedidos: uma tentativa, nao tres",
   len(_llm_429.client.pedidos) == 1)

# Cota esgotada sem status HTTP: o texto do provedor basta para classificar.
_llm_quota = _llm_falha27(Exception("You exceeded your current quota, please check your plan"))
_err_quota = _captura27(lambda: _llm_quota.chat([{"role": "user", "content": "oi"}]))
ok("cota esgotada tambem e reconhecida pelo texto do provedor",
   isinstance(_err_quota, _RateErr27))

# Retry-After: quando o servidor diz quanto esperar, a tela repete o numero.
_llm_espera = _llm_falha27(_StatusErr27("429 too many requests", headers={"retry-after": "30"}))
_err_espera = _captura27(lambda: _llm_espera.chat([{"role": "user", "content": "oi"}]))
ok("quando o servidor diz quanto esperar, a mensagem mostra o numero",
   "30 segundos" in str(_err_espera))

# Falha comum de servidor continua sendo erro generico (sem confundir com limite).
_llm_500 = _llm_falha27(_StatusErr27("Internal server error", status=500))
_err_500 = _captura27(lambda: _llm_500.chat([{"role": "user", "content": "oi"}]))
ok("erro comum de servidor (500) nao e confundido com limite de uso",
   isinstance(_err_500, _LLMErr27) and not isinstance(_err_500, _RateErr27))

# Em streaming, o 429 nao pode cair para 'responder de uma vez' (outro pedido).
_llm_stream429 = _llm_falha27(_StatusErr27("429 rate limit reached"))
_err_stream429 = _captura27(lambda: _llm_stream429.chat_stream([{"role": "user", "content": "oi"}]))
ok("429 no streaming nao dispara um segundo pedido sem streaming",
   isinstance(_err_stream429, _RateErr27) and len(_llm_stream429.client.pedidos) == 1)


class _SinkStyle27(RecSink):
    """Sink que guarda tambem a cor de cada linha (aviso x erro)."""

    def __init__(self):
        super().__init__()
        self.pares: list[tuple[str, object]] = []

    def line(self, text, style=None):
        self.pares.append((str(text), style))
        super().line(text, style)


class _RateLLM27(_ListLLM26):
    def __init__(self, exc):
        self.exc = exc

    def chat(self, messages, tools=None):
        raise self.exc

    def summarize(self, text):
        return ""


_sink_rate27 = _SinkStyle27()
_core_rate27 = ChatCore(dict(core_cfg), _sink_rate27, llm=_RateLLM27(_err_429))
_core_rate27.submit("oi")
ok("na tela o limite de uso aparece como aviso amarelo, nao como erro vermelho",
   any("pediu para esperar" in texto and style == "yellow"
       for texto, style in _sink_rate27.pares))
_texto_rate27 = " ".join(texto for texto, _style in _sink_rate27.pares)
ok("dica do 429 manda ver /provedor em vez de reconferir URL e chave",
   "/provedor" in _texto_rate27 and "/configurar" not in _texto_rate27)

# ---------- 0.2.8 (emenda): chave no perfil, rodape, janela, onde ficam as coisas
import io as _io28
import time as _time28

from bgh.chat_core import maximize_window as _max28
from bgh.config import set_active_profile as _ativa28
from bgh.config import sync_profile as _sync28
from bgh.tui import compact_ctx as _compact28
from bgh import setup_wizard as _wiz28

_cfg_perfil28 = {
    "provider": "custom", "base_url": "https://openrouter.ai/api/v1",
    "model": "openai/gpt-4o-mini", "api" + "_key": "chave-certa",
    "active_profile": "outro",
    "profiles": {"outro": {"provider": "custom",
                           "base_url": "https://openrouter.ai/api/v1",
                           "model": "openai/gpt-4o-mini", "api" + "_key": ""}},
}
ok("sync_profile leva a chave EM USO para o perfil salvo",
   _sync28(_cfg_perfil28)
   and _cfg_perfil28["profiles"]["outro"]["api" + "_key"] == "chave-certa")
_ativa28(_cfg_perfil28, "outro")
ok("depois disso, trocar de provedor NAO devolve a chave velha (401 medido no cliente)",
   _cfg_perfil28["api" + "_key"] == "chave-certa")

# O mesmo cenario, agora pelo assistente inteiro: chave vazia -> 401 -> chave certa.
_orig_llm28 = _llmmod26.LLM


class _LLMAuth28:
    def __init__(self, cfg=None):
        self.cfg = cfg or {}

    def chat(self, messages, tools=None):
        if str(self.cfg.get("api" + "_key") or "") == "chave-certa":
            return {"role": "assistant", "content": "pronto"}
        raise _LLMErr27("Falha ao falar com o modelo (AuthenticationError): Error code: 401")

    def discover_context(self):
        return None


def _ask28(prompt, default="", secret=False):
    texto = prompt.lower()
    if "manter o provedor" in texto:
        return "n"                      # segue para o cadastro
    if "opcao" in texto:
        return "4"                      # Outro (OpenRouter)
    if "url do servidor" in texto:
        return "https://openrouter.ai/api/v1"
    if "nome do modelo" in texto:
        return "openai/gpt-4o-mini"
    if "cole a chave" in texto:
        return "chave-certa"            # auto-correcao depois do 401
    if "chave de acesso" in texto:
        return ""                       # primeira tentativa: chave vazia
    if "testar a conexao" in texto:
        return "s"
    if "ja esta cadastrado" in texto or "atualizar os dados" in texto:
        return "s"
    return default


try:
    _llmmod26.LLM = _LLMAuth28
    _wiz28.run(ask=_ask28, say=lambda *a: None)
finally:
    _llmmod26.LLM = _orig_llm28
_cfg_disco28 = json.loads(Path(os.environ["BGH_HOME"], "config.json").read_text(encoding="utf-8"))
ok("assistente: a chave testada com sucesso fica TAMBEM no perfil salvo",
   _cfg_disco28.get("api" + "_key") == "chave-certa"
   and _cfg_disco28["profiles"]["outro"].get("api" + "_key") == "chave-certa")

# /modelo tambem tem que atualizar o perfil, senao trocar de provedor desfaz a troca.
_cfg_mod28 = {
    "provider": "p1", "base_url": "http://fake/v1", "model": "alpha-model",
    "api" + "_key": "k", "active_profile": "p1",
    "profiles": {"p1": {"provider": "p1", "base_url": "http://fake/v1",
                        "model": "alpha-model", "api" + "_key": "k"}},
    "context_budget_chars": 60000, "stream": False,
}
_sink_mod28 = RecSink()
_core_mod28 = ChatCore(_cfg_mod28, _sink_mod28, llm=_ListLLM26())
_core_mod28.submit("/modelo")       # popula a lista (o numero so resolve depois dela)
_core_mod28.submit("/modelo 2")
ok("/modelo troca o modelo E o perfil salvo (trocar de provedor nao desfaz mais)",
   _cfg_mod28["model"] == "beta-model"
   and _cfg_mod28["profiles"]["p1"]["model"] == "beta-model")

# --- barra de baixo: aviso manda, medidor cede espaco -------------------------
ok("medidor compacto: 500000 vira 500k e 'mensagens' vira 'msg'",
   _compact28("contexto: 29% de 500000 chars (88 mensagens)", 40)
   == "ctx 29% de 500k (88 msg)")
ok("sem espaco, o medidor sai da barra (o aviso vale mais)",
   _compact28("contexto: 29% de 500000 chars (88 mensagens)", 5) == "")

_st_grande28 = {"busy": False, "approval": None, "stop_hits": 0, "spin": 0,
                "ctx": "contexto: 29% de 500000 chars (88 mensagens)", "ctx_pct": 29,
                "ctx_extra": "", "busy_since": 0.0, "tool": None, "tool_since": 0.0}
_fr_idle28 = _status_text25(dict(_st_grande28), 100)[0][1]
ok("parado, janela de 100: medidor + teclas cabem INTEIROS (nada cortado no meio)",
   len(_fr_idle28) <= 98 and _fr_idle28.endswith("/ajuda")
   and "ENTER = falar" in _fr_idle28 and "29%" in _fr_idle28)

_st_busy28 = {**_st_grande28, "busy": True, "busy_since": _time28.time() - 12,
              "tool": "run_python", "tool_since": _time28.time() - 3}
_estilo_busy28, _fr_busy28 = _status_text25(dict(_st_busy28), 100)[0]
ok("rodando: 'PARA PARAR' e a ferramenta SEMPRE na barra, medidor so se couber",
   _estilo_busy28 == "class:footer.hot" and "rodando" in _fr_busy28
   and "run_python" in _fr_busy28 and "PARA PARAR" in _fr_busy28
   and len(_fr_busy28) <= 98)

_fr_estreito28 = _status_text25(dict(_st_busy28), 54)[0][1]
ok("janela muito estreita: o aviso de parar continua inteiro (o medidor sai)",
   "PARA PARAR" in _fr_estreito28 and len(_fr_estreito28) <= 52)

# --- janela maximizada na abertura -------------------------------------------
_buf_max28 = _io28.StringIO()
_orig_osname28 = os.name
try:
    os.name = "posix"
    with _ctxlib26.redirect_stdout(_buf_max28):
        _max28()
finally:
    os.name = _orig_osname28
ok("abertura pede janela maximizada (sequencia do xterm no Linux/macOS)",
   _buf_max28.getvalue() == "\x1b[9;0t")

_orig_osname28b = os.name
os.name = "nt"
try:
    _max28()            # sem ctypes.windll aqui: falha silenciosa, nunca derruba
    _nt_ok28 = True
except Exception:       # noqa: BLE001
    _nt_ok28 = False
finally:
    os.name = _orig_osname28b
ok("no Windows a maximizacao usa a API do console e nunca derruba a abertura", _nt_ok28)

# --- onde ficam as coisas (o modelo inventou 'registro do Windows') ----------
_prompt28 = _prompts26.build_system_prompt([], [], [])
ok("prompt diz onde ficam as coisas e proibe inventar registro do Windows",
   "ONDE FICAM AS COISAS" in _prompt28 and ".bgh/config.json" in _prompt28
   and "registro do Windows" in _prompt28 and "CONFIRA" in _prompt28)

# ---------- dev: palco do pedido (trilha durante o processamento) -------------
from bgh import palco as _palco29

_st_palco29 = {"busy": True, "fase": "ferramenta", "tool": "run_python",
               "tool_since": 1000.0, "busy_since": 990.0}
_linhas29 = _palco29.stage_rows(_st_palco29, 100, 1004.0, 0)


def _txt29(linha) -> str:
    return linha[1] if isinstance(linha, tuple) else "".join(t for _s, t in linha)


ok("palco largo: 5 linhas com a trilha completa (start ate tela)",
   len(_linhas29) == 5 and "[START]" in _txt29(_linhas29[0])
   and "[TELA]" in _txt29(_linhas29[0]))
_coluna29 = _txt29(_linhas29[1]).find("^")
ok("marcador fica exatamente sob a etapa em que o pedido esta",
   _coluna29 > 0
   and _txt29(_linhas29[0])[_coluna29:_coluna29 + len("[FERRAMENTA]")] == "[FERRAMENTA]")
ok("palco mostra o tempo real da ferramenta e do turno",
   "run_python 4s" in _txt29(_linhas29[3]) and "turno 14s" in _txt29(_linhas29[3]))

_estreito29 = _palco29.stage_rows(_st_palco29, 60, 1004.0, 0)
ok("janela estreita: palco vira UMA linha (nao rouba 4 linhas da conversa)",
   len(_estreito29) == 1 and "run_python" in _txt29(_estreito29[0])
   and "[START]" not in _txt29(_estreito29[0]) and len(_txt29(_estreito29[0])) <= 58)

ok("etapa atual vai como item de menu selecionado; o resto da trilha normal",
   any(e == "class:palco.sel" and x == "[FERRAMENTA]" for e, x in _linhas29[0])
   and any(e == "class:palco" and x == "[START]" for e, x in _linhas29[0]))

_frags29 = _palco29.stage_lines(_st_palco29, 100, 1004.0, 0)
ok("palco entrega as 5 linhas separadas por quebra dentro do texto",
   sum(x.count("\n") for _e, x in _frags29) == 4)

ok("palco e ASCII puro (terminal de Windows e fonte raster)",
   all(ord(c) < 128 for linha in _linhas29 for c in _txt29(linha)))

# fase sem ferramenta (modelo escrevendo) nao inventa ferramenta
_st_mod29 = {"busy": True, "fase": "modelo", "tool": None,
             "busy_since": 1000.0, "tool_since": 0.0}
_res29 = _txt29(_palco29.stage_rows(_st_mod29, 100, 1003.0, 0)[3])
ok("palco na fase do modelo nao mostra ferramenta nenhuma",
   "o modelo esta escrevendo" in _res29 and "None" not in _res29)

# comando /palco
_cfg_p29: dict = dict(core_cfg)
_cfg_p29["palco"] = True
_sink_p29 = RecSink()
_core_p29 = ChatCore(_cfg_p29, _sink_p29, llm=_ListLLM26())
_core_p29.submit("/palco desliga")
ok("/palco desliga tira o palco e salva (tela como antes)",
   _cfg_p29["palco"] is False and any("DESLIGADO" in l for l in _sink_p29.lines))
_core_p29.submit("/palco liga")
ok("/palco liga devolve o palco", _cfg_p29["palco"] is True)
ok("ajuda anuncia o comando /palco",
   any("/palco" in "".join(t for t, _s in seg) for seg in _help_lines26()))

# ---------- emenda da 0.2.9: tokens por etapa no palco ------------------------
from bgh.llm import LLM as _LLM29
ok("tokens abreviados no formato pedido (800, 2.00k, 1.20M)",
   _palco29.abrevia(800) == "800" and _palco29.abrevia(2000) == "2.00k"
   and _palco29.abrevia(1200000) == "1.20M")

_st_tk29 = {**_st_palco29, "tokens": {"entrada": 12400, "saida": 980, "cache": 0}}
_lin_tk29 = _txt29(_palco29.stage_rows(_st_tk29, 100, 1004.0, 0)[2])
ok("tokens embaixo das etapas: entrada no AGENTE, saida no MODELO, total na TELA",
   "12.40k" in _lin_tk29 and "980" in _lin_tk29 and "13.38k" in _lin_tk29
   and _lin_tk29.index("12.40k") < _lin_tk29.index("980") < _lin_tk29.index("13.38k"))
ok("FERRAMENTA nao ganha numero de token inventado (fica vazio)",
   _lin_tk29[27:39].strip() == "")

_est_tk29 = _txt29(_palco29.stage_rows(_st_tk29, 60, 1004.0, 0)[0])
ok("janela estreita mostra os tokens abreviados na linha unica",
   "12.40k/980 tk" in _est_tk29 and len(_est_tk29) <= 58)

ok("sem contagem do servidor, a linha de tokens fica vazia (nada inventado)",
   _txt29(_palco29.stage_rows(_st_palco29, 100, 1004.0, 0)[2]).strip() == "")

# O cliente tem que GUARDAR o que o servidor informou (entrada/saida/cache).
_uso29 = types.SimpleNamespace(
    prompt_tokens=1200, completion_tokens=300,
    prompt_tokens_details=types.SimpleNamespace(cached_tokens=800))
_msg29 = types.SimpleNamespace(content="ok", reasoning_content=None, tool_calls=None)
_resp29 = types.SimpleNamespace(choices=[types.SimpleNamespace(message=_msg29)], usage=_uso29)
_llm_u29 = _LLM29({"base_url": "http://fake/v1", "model": "m", "max_retries": 0})
_llm_u29.client = types.SimpleNamespace(chat=types.SimpleNamespace(
    completions=types.SimpleNamespace(create=lambda **k: _resp29)))
_llm_u29.chat([{"role": "user", "content": "oi"}])
ok("cliente guarda a contagem de tokens do pedido (entrada/saida/cache)",
   _llm_u29.last_usage == {"entrada": 1200, "saida": 300, "cache": 800})

# Streaming: pede include_usage e le o ultimo pedaco (choices vazio).
_pedidos29: list[dict] = []
_delta29 = types.SimpleNamespace(content="oi", reasoning_content=None, tool_calls=None)
_chunks29 = [types.SimpleNamespace(choices=[types.SimpleNamespace(delta=_delta29)], usage=None),
             types.SimpleNamespace(choices=[], usage=_uso29)]


def _cria_stream29(**kwargs):
    _pedidos29.append(dict(kwargs))
    return iter(_chunks29)


_llm_s29 = _LLM29({"base_url": "http://fake/v1", "model": "m", "max_retries": 0})
_llm_s29.client = types.SimpleNamespace(chat=types.SimpleNamespace(
    completions=types.SimpleNamespace(create=_cria_stream29)))
_msg_s29 = _llm_s29.chat_stream([{"role": "user", "content": "oi"}])
ok("streaming pede include_usage e conta os tokens do pedaco final",
   _msg_s29["content"] == "oi" and _pedidos29[0].get("stream_options") == {"include_usage": True}
   and _llm_s29.last_usage["entrada"] == 1200)

# Servidor que recusa o campo: perde SO o contador, resposta continua.
_rejeitados29: list[dict] = []


def _cria_rejeita29(**kwargs):
    _rejeitados29.append(dict(kwargs))
    if "stream_options" in kwargs:
        raise Exception("unsupported parameter: stream_options")
    return iter(_chunks29)


_llm_r29 = _LLM29({"base_url": "http://fake/v1", "model": "m", "max_retries": 0})
_llm_r29.client = types.SimpleNamespace(chat=types.SimpleNamespace(
    completions=types.SimpleNamespace(create=_cria_rejeita29)))
_msg_r29 = _llm_r29.chat_stream([{"role": "user", "content": "oi"}])
ok("servidor sem stream_options: responde igual, so perde o contador",
   _msg_r29["content"] == "oi" and "stream_options" not in _rejeitados29[-1]
   and len(_rejeitados29) == 2)


class _UsoLLM29:
    def __init__(self):
        self.last_usage = {"entrada": 10, "saida": 5, "cache": 0}

    def chat(self, messages, tools=None):
        return {"role": "assistant", "content": "ok"}

    def summarize(self, text):
        return ""


_ag_u29 = _Agent26(dict(core_cfg), _UsoLLM29(), Gate(dict(core_cfg), ask_d))
_recebido29: list = []
_ag_u29.on_usage = _recebido29.append
_ag_u29.run_turn("oi")
ok("o turno repassa a contagem de tokens para a tela",
   bool(_recebido29) and _recebido29[-1]["entrada"] == 10)

# ---------- emenda da 0.2.9: tokens no medidor de contexto (rodape) -----------
from bgh.chat_core import ctx_parts as _ctx_parts26
_uso_ctx29 = {"pct": 27, "budget": 250000, "messages": 102,
              "tokens": 19340, "tokens_reais": True, "tokens_teto": 71428}
_medidor29, _ = _ctx_parts26({}, _uso_ctx29)
ok("medidor do rodape mostra usado E teto em tokens (nao da para ler errado)",
   _medidor29 == "contexto: 27% de 250000 chars (19.34k de 71.43k toks) (102 mensagens)")

_uso_est29 = {"pct": 27, "budget": 250000, "messages": 102,
              "tokens": 19340, "tokens_reais": False, "tokens_teto": 71428}
_medidor_est29, _ = _ctx_parts26({}, _uso_est29)
ok("sem contagem do servidor, o rodape marca o '~' (estimativa, nao contagem)",
   "(~19.34k de 71.43k toks)" in _medidor_est29)

_compacto29 = _compact28(
    "contexto: 27% de 250000 chars (19.34k de 71.43k toks) (102 mensagens)", 60)
ok("janela apertada: medidor compacto mantem tokens e teto, e cabe",
   _compacto29 == "ctx 27% de 250k (19.34k/71.43k toks) (102 msg)"
   and len(_compacto29) <= 60)

_ag_med29 = _Agent26(dict(core_cfg), _OkLLM26(), Gate(dict(core_cfg), ask_d))
_uso_sem29 = _ag_med29.ctx_usage()
ok("sem pedido ainda, o medidor usa a estimativa de 3,5 chars por token",
   _uso_sem29["tokens_reais"] is False
   and _uso_sem29["tokens"] == int(_uso_sem29["chars"] / 3.5)
   and _uso_sem29["tokens_teto"] == int(_uso_sem29["budget"] / 3.5))
_ag_med29.last_usage = {"entrada": 1234, "saida": 10, "cache": 0}
_uso_com29 = _ag_med29.ctx_usage()
ok("depois de um pedido, o medidor passa a usar o numero real",
   _uso_com29["tokens_reais"] is True and _uso_com29["tokens"] == 1234)

# ---------- emenda 3 da 0.2.9: menu numerado de pasta/arquivo ---------------
import tempfile as _tmp29

class _SinkMenu29(RecSink):
    """Sink de tela fixa: sabe abrir menu e devolve as escolhas do roteiro."""

    menu_arquivos = True

    def __init__(self, escolhas):
        super().__init__()
        self.escolhas = list(escolhas)
        self.menus: list[list[str]] = []

    def ask_choice(self, title, label, options):
        self.menus.append([str(o) for o in options])
        return self.escolhas.pop(0) if self.escolhas else options[-1]


_base29 = Path(_tmp29.mkdtemp(prefix="menu29_"))
(_base29 / "pasta_a").mkdir()
(_base29 / "pasta_b").mkdir()
(_base29 / "nota.txt").write_text("conteudo de teste", encoding="utf-8")

_sink_m29 = _SinkMenu29(["anexar: nota.txt"])
_cfg_m29: dict = dict(core_cfg)
_cfg_m29["stream"] = False
_core_m29 = ChatCore(_cfg_m29, _sink_m29, llm=_ListLLM26())
_orig_cwd29 = os.getcwd()
os.chdir(_base29)
try:
    _core_m29.submit("@")
finally:
    os.chdir(_orig_cwd29)
ok("'@' abre menu com a ACAO escrita em cada linha ('anexar: arquivo')",
   bool(_sink_m29.menus) and "anexar: nota.txt" in _sink_m29.menus[0])

ok("menu tambem deixa ENTRAR em pasta no modo anexar (arquivo em subpasta)",
   "entrar em: pasta_a" in _sink_m29.menus[0])
ok("escolher o arquivo no menu ANEXA (o conteudo vai para a proxima pergunta)",
   _core_m29.pending_attach is not None and "conteudo de teste" in _core_m29.pending_attach)

_sink_m29b = _SinkMenu29(["entrar em: pasta_a", "cancelar (voltar para a conversa)"])
_core_m29b = ChatCore(dict(_cfg_m29), _sink_m29b, llm=_ListLLM26())
os.chdir(_base29)
try:
    _core_m29b.submit("/")
finally:
    os.chdir(_orig_cwd29)
ok("'/' abre menu com pastas ('entrar em') e arquivos ('ver')",
   bool(_sink_m29b.menus) and "entrar em: pasta_a" in _sink_m29b.menus[0]
   and "entrar em: pasta_b" in _sink_m29b.menus[0]
   and "ver: nota.txt" in _sink_m29b.menus[0])
ok("escolher uma pasta ENTRA nela (menu seguinte mostra o conteudo dela)",
   len(_sink_m29b.menus) > 1
   and ".. (voltar uma pasta)" in _sink_m29b.menus[1]
   and "cancelar (voltar para a conversa)" in _sink_m29b.menus[1])
ok("menu de arquivos: opcao 1 e CANCELAR (Enter/ESC nunca escolhem por engano)",
   _sink_m29.menus[0][0] == "cancelar (voltar para a conversa)"
   and _sink_m29b.menus[0][0] == "cancelar (voltar para a conversa)")

# Modo simples (sem menu) continua listando: nada de menu em script/pipe.
_sink_lista29 = RecSink()
_core_lista29 = ChatCore(dict(_cfg_m29), _sink_lista29, llm=_ListLLM26())
os.chdir(_base29)
try:
    _core_lista29.submit("/")
finally:
    os.chdir(_orig_cwd29)
ok("sem tela fixa, '/' continua so listando (script e pipe nao param em menu)",
   any("pasta:" in linha for linha in _sink_lista29.lines))

# ---------- emenda 6 da 0.2.9: palco so quando ha pedido de verdade ----------
ok("palco aparece durante um pedido ao agente",
   _palco29.visivel(True, "pedido", True, 0.0, 100.0) is True)
ok("palco NAO aparece em /ajuda, /modelo ou menu de arquivo (busy sem pedido)",
   _palco29.visivel(True, None, True, 0.0, 100.0) is False)
ok("palco mostra a entrega por 1,6s depois do turno e depois some",
   _palco29.visivel(True, "pronto", False, 101.0, 100.0) is True
   and _palco29.visivel(True, "pronto", False, 99.0, 100.0) is False)
ok("palco desligado no /palco desliga nao aparece nem com pedido em curso",
   _palco29.visivel(False, "pedido", True, 0.0, 100.0) is False)

# ---------- v0.2.10: limite de ferramentas prorroga sozinho ate o teto ----------
class _SempreFerramenta210:
    """Modelo que sempre pede uma ferramenta DIFERENTE (nunca repete chamada)."""

    def __init__(self):
        self.n = 0
        self.com_ferramenta = 0

    def chat(self, messages, tools=None):
        if tools is None:
            return {"role": "assistant", "content": "resposta final"}
        self.n += 1
        self.com_ferramenta += 1
        return {"role": "assistant", "content": "", "tool_calls": [{
            "id": f"c{self.n}", "type": "function",
            "function": {"name": "run_command",
                         "arguments": json.dumps({"command": f"echo passo {self.n}"})}}]}

    def summarize(self, text):
        return ""


class _FerramentaQuebrada210(_SempreFerramenta210):
    """Sempre pede uma ferramenta que NAO existe: todo resultado vira ERRO."""

    def chat(self, messages, tools=None):
        if tools is None:
            return {"role": "assistant", "content": "resposta final"}
        self.n += 1
        self.com_ferramenta += 1
        return {"role": "assistant", "content": "", "tool_calls": [{
            "id": f"c{self.n}", "type": "function",
            "function": {"name": "ferramenta_que_nao_existe",
                         "arguments": json.dumps({"tentativa": self.n})}}]}


_cfg_l210: dict = dict(core_cfg)
_cfg_l210.update({"max_tool_rounds": 2, "max_tool_rounds_teto": 4, "stream": False})
_llm_l210 = _SempreFerramenta210()
_ag_l210 = _Agent26(_cfg_l210, _llm_l210, Gate(dict(_cfg_l210), ask_d))
_notas_l210: list[str] = []
_ag_l210.on_note = _notas_l210.append
_resp_l210 = _ag_l210.run_turn("faca varias coisas")
ok("limite de 2 ferramentas RENOVA sozinho quando o turno esta progredindo",
   any("vou continuar por mais 2" in n for n in _notas_l210))
ok("prorrogacao para no teto (2 -> 4) e nao vira loop infinito",
   _llm_l210.com_ferramenta == 4 and _resp_l210 == "resposta final")
ok("ao bater o teto a tela avisa e a instrucao ensina a continuar",
   any("Parei em 4 ferramentas" in n for n in _notas_l210)
   and any("continue" in str(m.get("content", "")) for m in _ag_l210.messages))

# Sem progresso (tudo falhando) NAO prorroga: fecha na primeira etapa.
_cfg_r210: dict = dict(core_cfg)
_cfg_r210.update({"max_tool_rounds": 2, "max_tool_rounds_teto": 10, "stream": False})
_llm_r210 = _FerramentaQuebrada210()
_ag_r210 = _Agent26(_cfg_r210, _llm_r210, Gate(dict(_cfg_r210), ask_d))
_notas_r210: list[str] = []
_ag_r210.on_note = _notas_r210.append
_resp_r210 = _ag_r210.run_turn("quebre tudo")
ok("turno que so falha NAO prorroga (fecha na etapa, sem gastar mais)",
   _llm_r210.com_ferramenta == 2
   and not any("vou continuar" in n for n in _notas_r210)
   and _resp_r210 == "resposta final")

# Teto menor que o dobro: a prorrogacao respeita o numero exato do config.
_cfg_t210: dict = dict(core_cfg)
_cfg_t210.update({"max_tool_rounds": 2, "max_tool_rounds_teto": 3, "stream": False})
_llm_t210 = _SempreFerramenta210()
_ag_t210 = _Agent26(_cfg_t210, _llm_t210, Gate(dict(_cfg_t210), ask_d))
_notas_t210: list[str] = []
_ag_t210.on_note = _notas_t210.append
_ag_t210.run_turn("tres passos")
ok("teto de 3 com etapa de 2: prorroga so 1 rodada ('mais 1')",
   any("mais 1" in n for n in _notas_t210) and _llm_t210.com_ferramenta == 3)

# ---------- v0.2.10 (emenda): resposta vazia/cortada nao pode ficar muda ------
class _FimLLM210:
    """Modelo fake que termina com o finish_reason pedido (length = max_tokens)."""

    def __init__(self, conteudo="", finish="length"):
        self.conteudo = conteudo
        self.finish = finish
        self.last_finish = finish
        self.last_usage = None

    def chat_stream(self, messages, tools=None, on_text=None, on_reasoning=None,
                    should_stop=None):
        if self.conteudo and on_text:
            on_text(self.conteudo)
        self.last_finish = self.finish
        return {"role": "assistant", "content": self.conteudo}

    def chat(self, messages, tools=None):
        self.last_finish = self.finish
        return {"role": "assistant", "content": self.conteudo}

    def summarize(self, text):
        return ""


_cfg_f210: dict = dict(core_cfg)
_cfg_f210["stream"] = True
_sink_f210 = RecSink()
_core_f210 = ChatCore(_cfg_f210, _sink_f210, llm=_FimLLM210("", "length"))
_core_f210.submit("meca a velocidade")
ok("resposta vazia COM streaming agora avisa na tela (era o caso do Windows)",
   any("gastou o limite de saida pensando" in l for l in _sink_f210.lines))

_sink_c210 = RecSink()
_core_c210 = ChatCore(dict(_cfg_f210), _sink_c210, llm=_FimLLM210("texto cortado", "length"))
_core_c210.submit("fale bastante")
ok("resposta cortada pelo limite de saida avisa e ensina o 'continue'",
   any("cortada pelo limite de saida" in l for l in _sink_c210.lines))

_sink_n210 = RecSink()
_core_n210 = ChatCore(dict(_cfg_f210), _sink_n210, llm=_FimLLM210("resposta normal", "stop"))
_core_n210.submit("oi")
ok("resposta normal nao ganha aviso nenhum (nada de alarme falso)",
   not any("limite de saida" in l for l in _sink_n210.lines))

# --- gateway que recusa campo extra (nubesbr) nao pode derrubar o STREAMING ----
_delta_g210 = types.SimpleNamespace(content="oi", reasoning_content=None, tool_calls=None)
_chunks_g210 = [types.SimpleNamespace(
    choices=[types.SimpleNamespace(delta=_delta_g210, finish_reason="stop")], usage=None)]


class _GatewayChato210:
    """Recusa campo extra com mensagem generica (nao cita o nome do campo)."""

    def __init__(self):
        self.chamadas: list[dict] = []

    def create(self, **kwargs):
        self.chamadas.append(dict(kwargs))
        if "stream_options" in kwargs:
            raise Exception("Error code: 400 - parametros nao suportados por este node")
        return iter(_chunks_g210)


_cli_g210 = _GatewayChato210()
_llm_g210 = _LLM29({"base_url": "https://ia.nubesbr.com/v1/", "model": "m", "max_retries": 0})
_llm_g210.client = types.SimpleNamespace(chat=types.SimpleNamespace(
    completions=types.SimpleNamespace(create=_cli_g210.create)))
_msg_g210 = _llm_g210.chat_stream([{"role": "user", "content": "oi"}])
ok("gateway que recusa campo extra perde so o CONTADOR (streaming continua)",
   _msg_g210["content"] == "oi" and len(_cli_g210.chamadas) == 2
   and "stream_options" in _cli_g210.chamadas[0]
   and "stream_options" not in _cli_g210.chamadas[1])
_llm_g210.chat_stream([{"role": "user", "content": "de novo"}])
ok("depois da recusa, o campo nao e mais enviado (nao paga pedido extra por turno)",
   len(_cli_g210.chamadas) == 3 and "stream_options" not in _cli_g210.chamadas[2])

# Limite de uso NAO tenta de novo (cada tentativa gasta cota).
class _CliCota210:
    def __init__(self):
        self.chamadas = 0

    def create(self, **kwargs):
        self.chamadas += 1
        raise Exception("Error code: 429 - rate limit reached")


_cli_c210 = _CliCota210()
_llm_c210 = _LLM29({"base_url": "https://api.deepseek.com/v1", "model": "m", "max_retries": 0})
_llm_c210.client = types.SimpleNamespace(chat=types.SimpleNamespace(
    completions=types.SimpleNamespace(create=_cli_c210.create)))
try:
    _llm_c210.chat_stream([{"role": "user", "content": "oi"}])
    _tipo_c210 = None
except Exception as exc:  # noqa: BLE001
    _tipo_c210 = exc
ok("429 nao ganha retentativa extra por causa do campo de contagem",
   isinstance(_tipo_c210, _RateErr27) and _cli_c210.chamadas == 1)

# ---------- v0.2.12: tela nao trava mais com conversa grande (cache de linhas) --
import bgh.tui as _tui212

_contador212 = {"n": 0}
_orig_wrap212 = _tui212.textwrap.wrap


def _conta_wrap212(*a, **k):
    _contador212["n"] += 1
    return _orig_wrap212(*a, **k)


_board212 = _tui212.LineBoard()
for _i212 in range(600):
    _board212.add(f"linha fechada {_i212} com texto suficiente para embrulhar" * 2, "an", True)
_linhas212 = _board212.rows(100)
_tui212.textwrap.wrap = _conta_wrap212
try:
    _board212.rows(100)
    _depois_da_1a = _contador212["n"]
    for _i212 in range(50):
        _board212.add("pedaco ", "an", False)
        _board212.rows(100)
    _extras = _contador212["n"] - _depois_da_1a
finally:
    _tui212.textwrap.wrap = _orig_wrap212
ok("conversa grande: linhas fechadas ficam em cache (nao re-quebram a cada pedaco)",
   len(_linhas212) >= 600 and _extras <= 60)
ok("a cauda aberta continua sendo quebrada (texto novo nao perde)",
   _extras > 0)

# Turno que prorroga mostra a rodada no palco (nao um numero parado).
_st_rod212 = {"busy": True, "fase": "ferramenta", "tool": "run_command",
              "tool_since": 1000.0, "busy_since": 990.0, "rodada": 7}
ok("palco mostra a rodada quando o turno prorroga (rodada 7)",
   "rodada 7" in _palco29.resumo(_st_rod212, 1004.0))
_st_rod1 = dict(_st_rod212)
_st_rod1["rodada"] = 1
ok("na primeira rodada a palavra 'rodada' nao aparece (menos ruido)",
   "rodada" not in _palco29.resumo(_st_rod1, 1004.0))

# Largura diferente refaz o cache (senao texto ficaria com quebra errada).
_board212.rows(60)
ok("janela muda de largura: o cache e refeito na largura nova",
   _board212._rows_width == 58 and _board212._rows_consumidas >= 600)

# ---------- v0.2.12 (emenda): escrever em varias linhas no voce> --------------
from bgh.tui import quer_continuar as _cont212
from bgh.tui import tira_barra_final as _sem_barra212

ok("barra invertida no fim do texto = pular linha (regra de shell)",
   _cont212("linha 1 " + chr(92)) is True and _cont212("linha 1") is False)
ok("a barra de continuacao sai do texto que vai para o modelo",
   _sem_barra212("linha 1 " + chr(92)) == "linha 1")
ok("ajuda ensina a pular linha (Ctrl+J e a barra invertida)",
   any("Ctrl+J" in "".join(t for t, _s in seg) for seg in _help_lines26())
   and any("terminar a linha" in "".join(t for t, _s in seg) for seg in _help_lines26()))

# ---------- v0.2.13: instalador sobrevive a instalacao quebrada (RECORD) ------
_raiz213 = Path(__file__).resolve().parents[1]
_ps213 = (_raiz213 / "scripts" / "install_te_win.ps1").read_text(encoding="utf-8")
_sh213 = (_raiz213 / "scripts" / "install_te.sh").read_text(encoding="utf-8")
ok("instalador do Windows instala com --ignore-installed (bgh antigo sem RECORD nao trava)",
   "--ignore-installed" in _ps213 and "python.exe" in _ps213)
ok("instalador do Windows usa python -m pip (nao o pip.exe que reclama de si mesmo)",
   '-m pip install --upgrade pip' in _ps213 and 'Scripts\pip.exe" install --upgrade' not in _ps213)
ok("instalador do Linux/macOS tambem usa --ignore-installed e python -m pip",
   "--ignore-installed" in _sh213 and '.venv/bin/python"' in _sh213)
ok("os dois instaladores mostram a versao lida do proprio pacote (prova de que instalou)",
   "import bgh; print(bgh.__version__)" in _ps213
   and "import bgh; print(bgh.__version__)" in _sh213)

# ---------- v0.2.14: TEO limpa o proprio apoio (nao deixa lixo na pasta) ------
import tempfile as _tmp214
from bgh.tools import ToolBox as _ToolBox214

_pasta214 = Path(_tmp214.mkdtemp(prefix="apoio214_"))
(_pasta214 / "relatorio.html").write_text("<html>final</html>", encoding="utf-8")
(_pasta214 / "do_usuario.txt").write_text("arquivo que ja era dele", encoding="utf-8")
_cfg214: dict = dict(core_cfg)
_box214 = _ToolBox214(_cfg214, Gate(dict(_cfg214), ask_o))
_ctx214 = _box214.ctx
_box214.dispatch("write_file", json.dumps({"path": str(_pasta214 / "script.py"),
                                           "content": "print(1)"}))
_box214.dispatch("write_file", json.dumps({"path": str(_pasta214 / "copia.txt"),
                                           "content": "lixo"}))
_box214.dispatch("write_file", json.dumps({"path": str(_pasta214 / "relatorio.html"),
                                           "content": "<html>final</html>"}))
ok("write_file registra o que o TEO criou (para poder limpar depois)",
   len(_ctx214.criados) == 3)
ok("limpar_apoio existe no registro de ferramentas",
   "limpar_apoio" in _box214.handlers)
_saida214 = _box214.dispatch("limpar_apoio",
                             json.dumps({"pasta": str(_pasta214),
                                         "manter": str(_pasta214 / "relatorio.html")}))
ok("limpar_apoio apaga o apoio e MANTEM o entregavel pedido",
   "Removi 2" in _saida214 and (_pasta214 / "relatorio.html").is_file()
   and not (_pasta214 / "script.py").exists()
   and not (_pasta214 / "copia.txt").exists())
ok("limpar_apoio NUNCA apaga arquivo que o usuario ja tinha",
   (_pasta214 / "do_usuario.txt").is_file())

# O prompt tem que mandar rascunho para o scratch e limpar a pasta do usuario.
_prompt214 = _prompts26.build_system_prompt([], [], [])
ok("prompt separa RASCUNHO de ENTREGA e manda limpar a pasta do usuario",
   "RASCUNHO x ENTREGA" in _prompt214 and "limpar_apoio" in _prompt214
   and "pasta de rascunho" in _prompt214)

# ---------- v0.2.14: ler imagem (visao) em vez de OCR caseiro ------------------
import tempfile as _tmp299
from bgh.tools.files import image_data_url as _img_url299
from bgh.tools.files import is_image as _is_img299

_dir299 = Path(_tmp299.mkdtemp(prefix="visao299_"))
_foto299 = _dir299 / "foto.png"
_foto299.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 200)
_txt299 = _dir299 / "nota.txt"
_txt299.write_text("nao sou imagem", encoding="utf-8")
_grande299 = _dir299 / "grande.png"
_grande299.write_bytes(b"0" * (6 * 1024 * 1024))

_url299, _n299, _err299 = _img_url299(str(_foto299))
ok("imagem vira data URL para a visao do modelo",
   _url299.startswith("data:image/png;base64,") and _n299 == 208 and _err299 is None)
ok("arquivo de texto nao e aceito como imagem",
   "nao e uma imagem" in (_img_url299(str(_txt299))[2] or ""))
ok("foto grande demais e recusada com frase clara",
   "Diminua a foto" in (_img_url299(str(_grande299))[2] or ""))
ok("helper reconhece extensoes de imagem", _is_img299("a.JPG") and not _is_img299("a.py"))

_cfg299: dict = dict(core_cfg)
_cfg299["stream"] = False
_llm299 = _OkLLM26()
_ag299 = _Agent26(_cfg299, _llm299, Gate(dict(_cfg299), ask_d))
_ag299.run_turn("o que tem nesta foto?", imagem=str(_foto299))
_msg_user299 = [m for m in _ag299.messages if m.get("role") == "user"
                and isinstance(m.get("content"), list)]
ok("o pedido com foto leva texto + imagem (duas partes)",
   bool(_msg_user299) and len(_msg_user299[-1]["content"]) == 2
   and _msg_user299[-1]["content"][0]["type"] == "text"
   and _msg_user299[-1]["content"][1]["type"] == "image_url")
ok("o medidor de contexto nao conta o base64 da foto",
   len(json.dumps(_ag299._sem_imagem(_msg_user299[-1]), ensure_ascii=False)) < 600)
_sessao299 = Path(os.environ["BGH_HOME"], "session.json").read_text(encoding="utf-8")
ok("a sessao salva NAO guarda o base64 (troca por marcador)",
   "base64" not in _sessao299 and "[imagem anexada" in _sessao299)


class _SemVisao299:
    """Provedor que recusa imagem (modelo sem visao)."""

    def __init__(self):
        self.chamadas = 0

    def chat(self, messages, tools=None):
        self.chamadas += 1
        tem_foto = any(
            isinstance(m.get("content"), list)
            and any(isinstance(p, dict) and p.get("type") == "image_url"
                    for p in m["content"])
            for m in messages)
        if tem_foto:
            raise _LLMErr27("Error code: 400 - Invalid content type: image_url")
        return {"role": "assistant", "content": "segui sem a imagem"}

    def summarize(self, text):
        return ""


_ag_sv299 = _Agent26(dict(_cfg299), _SemVisao299(), Gate(dict(_cfg299), ask_d))
_notas_sv299: list[str] = []
_ag_sv299.on_note = _notas_sv299.append
_resp_sv299 = _ag_sv299.run_turn("leia a foto", imagem=str(_foto299))
ok("provedor sem visao: TEO tira a foto, avisa e responde assim mesmo",
   _resp_sv299 == "segui sem a imagem"
   and any("nao le imagem" in n for n in _notas_sv299))

print(f"\nTODOS OS {PASS} TESTES PASSARAM")

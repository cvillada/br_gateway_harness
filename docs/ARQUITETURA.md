# Arquitetura do Motor (bgh)

Python puro, sem servidor: o agente roda na maquina do usuario e fala com qualquer
endpoint OpenAI-compativel (llama.cpp/LM Studio local ou API na nuvem).

## Mapa dos modulos

```
bgh/
  cli.py            entrada dos comandos: chat / setup / doctor / approvals
  tui.py            TELA FIXA (prompt_toolkit): entrada sempre embaixo, area de
                    mensagens rolavel, barra de ajuda, botao de parar, menu de
                    licenca na tela
  chat_core.py      nucleo compartilhado pelas duas telas: comandos com barra,
                    atalhos @ e /, turnos do modelo, menu de licenca numerico
  agent.py          loop de tool-calling, anti-loop, compressao de contexto,
                    sessao persistida, stop_event (botao de parar)
  llm.py            cliente OpenAI-compativel: chat, chat_stream (com should_stop),
                    reasoning_content, toggle de thinking, list_models
  approvals.py      gate de seguranca em camadas (ver Seguranca abaixo)
  prompts.py        system prompt (identidade + memoria + indice de skills + regras)
  config.py         ~/.bgh/config.json (600), presets, perfis de provedor
  setup_wizard.py   assistente de 1 minuto com teste de conexao e auto-correcao
  tools/            run_command (interrumpivel), run_python, read/write/search_files,
                    web_search/web_extract (DDG, sem API), memory, skill,
                    make_document, instalar_pacote
  skills_default/   skills de fabrica (viajam no pacote; copiadas para ~/.bgh/skills)
```

## Fluxo de um turno

1. UI (tui ou classico) entrega a linha digitada ao `ChatCore.submit`.
2. Comandos com barra/atalhos sao resolvidos localmente; senao, `Agent.run_turn`.
3. `run_turn` roda ate `max_tool_rounds`: modelo -> tool_calls -> `ToolBox.dispatch`
   (cada ferramenta passa pelo `Gate`) -> resultados -> modelo ate a resposta final.
4. Streaming: `llm.chat_stream` empurra pedacos de texto/pensamento para a UI ao vivo.
5. Contexto acima do orcamento: `Agent._maybe_compress` resume a parte antiga.
6. Historico salvo em `~/.bgh/session.json` (retoma na proxima abertura).

## Botao de parar (CTRL+C / ESC na tela fixa)

- `Agent.stop_event` (threading.Event) e setado pela UI.
- No streaming: `chat_stream(should_stop=...)` fecha o stream e devolve a mensagem
  parcial com `stopped: True`; o turno devolve "(parei a resposta, como voce pediu)".
- Antes de cada ferramenta: chamada cancelada ganha resultado "BLOQUEADO: o usuario
  mandou parar" (historico OpenAI continua valido).
- Comando em andamento: `run_command` roda o shell em grupo proprio
  (`start_new_session`) e mata o grupo com SIGTERM->SIGKILL quando o evento dispara.
- Segunda pressao enquanto ainda ocupado = saida de seguranca da UI.

## Seguranca (aprovacoes)

Camadas do gate (`approvals.py`):
1. Piso duro: rm -rf /, fork bomb, dd em disco - nao passa NUNCA, nem com allowlist.
2. Regras perigosas (rm, chmod 777, systemctl stop, sudo, pip install, SQL destrutivo...):
   pedem licenca numerica em portugues; comando multi-regra pede UMA unica vez.
3. Allowlist permanente ("sempre") em `command_allowlist` no config (aceita glob);
   revisavel com `bgh approvals`.
4. Escrita em caminho sensivel (/etc, ~/.ssh, .env) e sobrescritura de arquivo
   existente sempre perguntam. Enter sozinho ou numero invalido = NAO (falha fechada).

## Memoria e skills

- `~/.bgh/memory.db` (SQLite): target user (quem e o usuario) e note (fatos da maquina);
  volta para o system prompt das proximas conversas.
- `~/.bgh/skills/<nome>/SKILL.md`: o Motor cria/atualiza ao aprender um procedimento
  que funcionou. Skills de fabrica em `bgh/skills_default/` viajam no pacote e sao
  escritas sob medida para as ferramentas do Motor (nao copiadas de outros agentes).

## Testes

- Suite offline: `.venv/bin/python tests/test_smoke.py` (FakeLLM, BGH_HOME temporario;
  nao precisa de modelo nem internet).
- Comportamento interativo so e provado em pseudo-terminal de verdade (pty real):
  tela fixa, parada no meio de comando longo, licenca respondida por numero, `/sair`.

## Empacotamento

- `bash build.sh` gera `dist/*.whl` (pip install cria o comando `bgh`) e binario unico
  PyInstaller `motor` (copiar e rodar; gerado NA maquina alvo).
- REGRADO o dist a cada mudanca em `bgh/` (o binario congela o codigo da build).
- Versao declarada em DOIS lugares: `bgh/__init__.py` e `pyproject.toml` (mude os dois).

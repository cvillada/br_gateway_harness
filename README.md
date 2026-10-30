# TEO (bgh) - agente CLI local para a maquina do usuario

TEO e o apelido deste harness (br_gateway_harness): o nome do gato preto do autor.

Harness enxuto em Python: loop de agente + endpoint OpenAI-compativel (local ou
API), ferramentas reais (shell, arquivos, Python, web, documentos), memoria
persistente e skills que o proprio TEO cria ao aprender. Modelo de aprovacao
espelhado no Hermes Agent: seguro roda direto, perigoso pede aprovacao humana.

## Instalacao por sistema operacional (pasta TEO + ambiente virtual)

O padrao e igual nos tres sistemas: criar uma pasta chamada TEO, criar um ambiente
virtual dentro dela e instalar o wheel baixado na pagina de Releases do repo.

### Windows (rota dos dois cliques - para criancas e idosos)

1. Instale antes o Python 3.11 ou mais novo: abra https://python.org, clique em
   "Download", abra o arquivo baixado e marque a caixinha "Add python.exe to PATH"
   (isso e uma vez so, na vida toda).
2. Abra esta pagina no navegador e baixe o arquivo `INSTALAR_TEO.bat`:
   https://github.com/cvillada/br_gateway_harness/releases/latest
3. De DOIS CLIQUES no arquivo `INSTALAR_TEO.bat` que esta na pasta Downloads.
   Pronto: ele baixa o TEO, cria a pasta TEO, instala, cria um icone **TEO** na area
   de trabalho e abre o programa sozinho. Da proxima vez em diante e so dar dois
   cliques no icone TEO da area de trabalho - nao precisa mexer em Prompt de Comando
   nunca mais. (Fechar a janela do TEO fecha so aquela conversa; o icone reabre tudo.)

Se o Windows mostrar o aviso azul "O Windows protegeu seu computador", clique em
"Mais informacoes" e depois no botao "Executar assim mesmo" (e porque o arquivo
ainda nao tem assinatura digital; o codigo esta neste proprio repo).

Para conversar de novo depois: dois cliques no icone **TEO** da area de trabalho.
(Se o icone nao aparecer, o atalho tambem esta em `C:\Users\SEU_USUARIO\TEO\abrir-teo.bat`.)

#### Windows (rota tecnica: 2 linhas no Prompt de Comando)

Requisito: Python 3.11 ou mais novo (https://python.org; marque "Add python.exe to PATH").
Abra o Prompt de Comando (cmd) e cole, uma linha de cada vez:

```batch
curl -L -o %USERPROFILE%\install_te.ps1 https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te_win.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\install_te.ps1
```

O script faz tudo sozinho: baixa o wheel do Release mais novo, cria a pasta
`%USERPROFILE%\TEO`, cria o ambiente virtual, copia o wheel para dentro dela, roda o
pip install e abre o TEO (na primeira vez, o assistente de configuracao comeca sozinho).

Para conversar outra vez: `cd %USERPROFILE%\TEO`, `.venv\Scripts\activate`, `bgh`.
Configuracoes e historico ficam em `C:\Users\SEU_USUARIO\.bgh`. Use o Windows
Terminal (ja vem no Windows 11); o Prompt de Comando antigo funciona, mas com menos
recursos visuais.

#### Windows (metodo manual, se preferir fazer passo a passo)

1. Baixe `bgh_motor-0.2.3-py3-none-any.whl` na pagina Releases (vai para a pasta
   Downloads do seu usuario).
3. Abra o Prompt de Comando (cmd) e rode, linha por linha:

```batch
mkdir TEO
cd TEO
python -m venv .venv
.venv\Scripts\activate
pip install %USERPROFILE%\Downloads\bgh_motor-0.2.3-py3-none-any.whl
bgh
```

Se o pip disser que o arquivo nao existe, descubra onde ele caiu:

```batch
dir /s /b %USERPROFILE%\Downloads\bgh_motor*
```

e use o caminho completo que aparecer (ou mova o .whl para a pasta TEO e faca
`pip install bgh_motor-0.2.3-py3-none-any.whl`). No PowerShell, troque
`%USERPROFILE%` por `$env:USERPROFILE`.

4. Para usar de novo em outra sessao: `cd TEO`, `.venv\Scripts\activate`, `bgh`.

Configuracoes e historico ficam em `C:\Users\SEU_USUARIO\.bgh`. Use o Windows
Terminal (ja vem no Windows 11); o Prompt de Comando antigo funciona, mas com menos
recursos visuais.

### macOS (instalacao pratica: 2 linhas)

Requisito: Python 3.11 ou mais novo (se falta: `brew install python@3.12`).
Abra o Terminal e cole, uma linha de cada vez:

```bash
curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
bash install_te.sh
```

O script faz tudo sozinho: baixa o wheel do Release mais novo, cria a pasta `~/TEO`,
cria o ambiente virtual, copia o wheel para dentro dela, roda o pip install, cria um
atalho para abrir o TEO sem terminal: um icone chamado **TEO** na Area de
trabalho (no macOS, `TEO.command` no Finder; no Linux, lancador `TEO`) e abre o programa
(na primeira vez, o assistente de configuracao comeca sozinho).

#### macOS (metodo manual, se preferir fazer passo a passo)

```bash
mkdir TEO && cd TEO
python3 -m venv .venv
source .venv/bin/activate
pip install /caminho/para/bgh_motor-0.2.4-py3-none-any.whl
bgh
```

Para usar de novo: `cd TEO`, `source .venv/bin/activate`, `bgh`. Configuracoes e
historico ficam em `~/.bgh`.

### Linux (instalacao pratica: 2 linhas)

Requisito: Python 3.11+ com venv (Ubuntu/Debian: `sudo apt install python3 python3-venv`).
No terminal, uma linha de cada vez:

```bash
curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
bash install_te.sh
```

Funciona exatamente como no macOS (mesmo script): cria `~/TEO` + venv, baixa o wheel
do Release mais novo, instala e abre o TEO.

#### Linux (alternativas)

Direto do repo clonado:

```bash
cd br_gateway_harness
bash install.sh   # instala e ja emenda o assistente de configuracao (fluxo unico)
bgh               # conversou, acabou
```

Ou o metodo manual com venv (copiando o wheel para `~/TEO`), igual ao do macOS acima.

### Sem Python (qualquer sistema)

Cada Release traz o binario pronto do seu sistema: `motor.exe` (Windows),
`motor-macos` (macOS) e `motor` (Linux). E baixar e rodar.

O assistente pode ser refeito a qualquer momento com `bgh setup`. Se o cliente abrir
o TEO sem nunca ter configurado, o assistente comeca sozinho na hora (nao precisa
decorar comando). No assistente ele escolhe o provedor (1-4), confirma URL e nome do
modelo (Enter aceita o padrao), cola a chave se o servidor pedir - e ha teste de
conexao com auto-correcao: se der "pede chave", ele pergunta a chave na hora e testa
de novo. Tudo fica em `~/.bgh/config.json` com permissao so do usuario (600); a chave
so e enviada para a URL que o proprio usuario cadastrou.

`bgh doctor` Diagnostico a maquina do usuario e a conexao com o modelo.

## Provedores suportados (setup presets)

| Preset | O que e | base_url |
|--------|---------|----------|
| deepseek | API DeepSeek (nuvem, mais facil) | https://api.deepseek.com/v1 |
| nubesbr  | servidor de IA hospedado (publico) | https://ia.nubesbr.com/v1/ (ajustavel) |
| local    | llama.cpp / LM Studio na propria maquina | http://127.0.0.1:30000/v1 |
| outro    | qualquer endpoint OpenAI-compativel | (voce digita) |

Preparado para modelos de 27B para cima: orcamento de contexto configuravel
(`context_budget_chars`, padrao 60000), compressao automatica da conversa e
dispatch tolerante a JSON malformado de modelo quantizado.

## Conversando

O chat abre igual ao Hermes: a linha `voce>` fica sempre embaixo e as mensagens
entram no rolamento natural do proprio terminal - a rodinha e a barra lateral do SEU
terminal rolam a conversa, e ao sair o texto continua visivel para reler. Sem
terminal interativo (pipe/script), cai no modo classico sozinho. Para desligar a
tela interativa: `"tui": false` no `~/.bgh/config.json`.

Parar e reler (pensado para idoso e crianca - um toque so):

| Tecla | O que faz |
|-------|-----------|
| CTRL+C ou ESC durante a resposta | PARA de responder e do comando na hora |
| CTRL+C duas vezes seguidas | saida de seguranca se algo travar |
| Roda do mouse ou barra lateral do seu terminal | reler o texto que subiu |
| CTRL+C com a linha vazia | fecha o TEO (ESC nunca fecha sozinho) |

Barra fixa embaixo sempre diz o que apertar; durante a resposta ela mostra
"respondendo... PARA PARAR: CTRL+C ou ESC".

Atalhos rapidos (nao perguntam licenca, s6 mostram):

| Atalho | O que faz |
|--------|-----------|
| `/` ou `/ls <pasta>` | lista pastas e arquivos |
| `@` | lista so os arquivos da pasta atual |
| `@<arquivo>` | anexa o arquivo; depois e so perguntar sobre ele |

Comandos:

| Comando | O que faz |
|---------|-----------|
| `/modelos` | lista os modelos publicados pelo servidor |
| `/modelo <nome ou numero>` | troca o modelo (fica salvo no config) |
| `/provedores` | lista os provedores cadastrados (ex.: 1 deepseek, 2 local) |
| `/provedor <nome ou numero>` | troca o provedor em uso na hora (fica salvo) |
| `/thinking on\|off\|auto` | liga/desliga o pensamento enviado ao servidor |
| `/ctx` | medidor do contexto atual |
| `/mem <texto>` | grava uma preferencia sua na memoria |
| `/nov` `/skills` `/ajuda` `/sair` | conversa nova, skills, ajuda, sair |

- Pensamento do modelo: se o servidor devolve `reasoning_content`/`reasoning`
  (llama.cpp com Qwen thinking, DeepSeek-R1 etc.), aparece como
  `pensamento> ...` antes da resposta.
- Contexto: apos cada resposta sai `contexto: NN% de 60000 chars` (verde/amarelo/
  vermelho); avisa quando esta enchendo e anuncia quando compacta em resumo.

## Seguranca (modelo Hermes, menu simples para o usuario)

- Comando seguro: executa sem perguntar.
- Apagar arquivo (ate um so), sobrescrever existente, codigo Python que apaga, disco,
  servico, sudo, pip install: sempre pedem licenca numa tela clara em portugues com menu numerico:
  `[1] Sim, desta vez  [2] Sim, e nao perguntar de novo nesta conversa  [3] Sim, sempre
  (quando faz sentido)  [4] Nao / cancelar` - Enter sozinho ou numero errado = NAO.
- "Sempre" vira regra permanente em `command_allowlist` no config.json; revise com
  `bgh approvals` (ou `bgh approvals remove <n>` / `bgh approvals clear`).
- Piso duro que nenhuma aprovacao cruza: rm -rf /, fork bomb, dd em disco fisico.
- Escrita em caminho sensivel (/etc, ~/.ssh, .env) pede aprovacao.
- Um comando que toca varias regras perigosas pede licenca UMA UNICA VEZ,
  listando as preocupacoes juntas - antes eram varias perguntas seguidas.
- Licenca pendente na tela fixa: o menu aparece na area de mensagens e o rodape muda
  para "LICENCA PENDENTE"; a pessoa responde o numero + ENTER (ou ESC = nao).

## Autonomia (resolver sozinho, sem loop infinito)

- Faltou biblioteca Python? O TEO confirma que falta, procura o nome certo se preciso,
  chama `instalar_pacote(pacote, motivo)` - a licenca aparece para o usuario com o motivo
  em linguagem simples - instala via pip e continua a tarefa. `pip install` por
  `run_command` passa pela mesma licenca (sem saida pelo lado).
- Anti-loop (regra dura): chamada IDENTICA repetida 3 vezes e cortada antes de executar
  ("LOOP DETECTADO"); 5 falhas em sequencia fecham o turno com uma explicacao ao usuario,
  em vez de insistir para sempre. Limite de rodadas por turno continua como teto final.

## Como ele aprende

- `memory` (SQLite em ~/.bgh/memory.db): target=user guarda quem o usuario e e
  como ele gosta de resposta; target=note guarda fatos da maquina. Tudo volta
  para o system prompt das proximas conversas.
- `skill` (SKILL.md em ~/.bgh/skills): ao descobrir um procedimento que
  funcionou, o TEO cria/atualiza a skill dela. Skills de fabrica em
  `skills/` do repo sao copiadas no setup e servem de base.

## Layout

```
bgh/                pacote do agente
  cli.py            entrada dos comandos (chat / setup / doctor / approvals)
  tui.py            TELA FIXA (prompt_toolkit): entrada embaixo, rolagem, botao parar
  chat_core.py      nucleo do chat compartilhado pelas duas telas (comandos, turnos)
  agent.py          loop + streaming + compressao + sessao + botao de parar
  llm.py            cliente OpenAI-compativel (stream + reasoning + thinking toggle)
  approvals.py      gate de licencas (modelo Hermes, regras em portugues)
  prompts.py        system prompt (identidade + memoria + skills)
  tools/            run_command (interrumpivel), run_python, read/write/search, web, memory, skill, documento
  skills_default/   skills de fabrica (copiadas para ~/.bgh/skills no setup)
tests/test_smoke.py testes offline (sem modelo)
pyproject.toml      empacotamento (wheel)
build.sh            gera wheel + binario unico
```

Estado do usuario fica todo em `~/.bgh/` (config.json 600, memory.db, skills/, session.json).

## Testes

```bash
.venv/bin/python tests/test_smoke.py
```

## Distribuir sem clone de repo

```bash
bash build.sh
```

Gera em dist/:
- `bgh_motor-<versao>-py3-none-any.whl` (vale para Windows, macOS e Linux) - na
  maquina do cliente: `pip install bgh_motor-*.whl` e o comando `bgh` passa a existir.
- `motor` - binario unico para Linux (mesma maquina/arquitetura): copiar para o
  cliente e rodar `./motor`. Os binarios `motor.exe` (Windows) e `motor-macos`
  (macOS) sao gerados pelo GitHub Actions em cada tag e anexados ao Release.

## Documentacao

- `docs/ARQUITETURA.md` - como o TEO funciona por dentro (modulos, seguranca, botao de parar, testes, empacotamento).
- `docs/CHANGELOG.md` - o que cada versao entrega.

## Roadmap proximo round

- Menu de permissoes tambem no modo nao-interativo (cron/-q) com `--yes`.
- Empacotar para outras distribuicoes (o binario `motor` e gerado na maquina alvo).

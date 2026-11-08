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

1. Baixe na pagina Releases o arquivo `bgh_motor-...-py3-none-any.whl` (vai para a
   pasta Downloads do seu usuario; o numero da versao aparece no meio do nome do
   arquivo).
2. Abra o Prompt de Comando (cmd) e rode, linha por linha. No comando do `pip`,
   troque `numero-da-versao` pelo numero que aparece no nome do arquivo baixado
   (ex.: 0.2.8):

```batch
mkdir TEO
cd TEO
python -m venv .venv
.venv\Scripts\activate
pip install "%USERPROFILE%\Downloads\bgh_motor-numero-da-versao-py3-none-any.whl"
bgh
```

Se o pip disser que o arquivo nao existe, descubra onde ele caiu:

```batch
dir /s /b %USERPROFILE%\Downloads\bgh_motor*
```

e use o caminho completo que aparecer na linha do comando acima (ou mova o `.whl`
para dentro da pasta TEO e instale pelo nome dele estando dentro dela).
No PowerShell, troque `%USERPROFILE%` por `$env:USERPROFILE`.

3. Para usar de novo em outra sessao: `cd TEO`, `.venv\Scripts\activate`, `bgh`.

Configuracoes e historico ficam em `C:\Users\SEU_USUARIO\.bgh`. Use o Windows
Terminal (ja vem no Windows 11); o Prompt de Comando antigo funciona, mas com menos
recursos visuais.

### macOS (instalacao pratica: 2 linhas)

Requisito: Python 3.11 ou mais novo (se falta: instale de https://python.org/downloads ou,
se tiver o brew, `brew install python@3.12`).
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
pip install ~/Downloads/bgh_motor-*.whl
bgh
```

Se o pip reclamar que achou mais de um arquivo, apague os `.whl` velhos da pasta
Downloads e rode o comando de novo. Para usar de novo: `cd TEO`,
`source .venv/bin/activate`, `bgh`. Configuracoes e historico ficam em `~/.bgh`.

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
`motor-macos` (macOS, para Macs com chip Apple - M1, M2, M3, M4) e `motor` (Linux).
E baixar e rodar. Mac com chip Intel: use o passo a passo com Python acima (funciona
em qualquer Mac). No Linux, rode o `motor` na mesma distribuicao em que ele foi gerado
(ou use o passo a passo com Python, que funciona em qualquer uma).

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
(`context_budget_chars`, padrao 156000), compressao automatica da conversa e
dispatch tolerante a JSON malformado de modelo quantizado. O assistente de setup
herda o limite do servidor em tres caminhos: motor llama.cpp publica `n_ctx`
(`props`), APIs estilo OpenRouter publicam `context_length`, e APIs que nada
publicam (DeepSeek, Anthropic...) saem do catalog publico models.dev. O valor e
definido sozinho - nao pergunta numero ao usuario; sem nenhuma fonte, vale o
padrao do provedor. Quando o provedor entrega mais que o teto de leitura, o
rodape avisa ("teto; o servidor entrega N tokens"). Saida por resposta ate 8192
tokens (`max_tokens`), o suficiente para escrever um documento HTML de ~28 mil
caracteres numa rodada; sessoes de redacao pesadas podem usar `/ctx 300000`.
Ajuste fino: `/ctx` na tela.

## Conversando

O chat abre igual ao Hermes: a linha `voce>` fica sempre embaixo e as mensagens
entram no rolamento natural do proprio terminal - a rodinha e a barra lateral do SEU
terminal rolam a conversa, e ao sair o texto continua visivel para reler. Sem
terminal interativo (pipe/script), cai no modo classico sozinho. Para desligar a
tela interativa: `"tui": false` no `~/.bgh/config.json`.

A janela ja abre maximizada e com o nome **TEO Agent**: em janela pequena a barra
de baixo (medidor, teclas, aviso de "rodando") nao caberia inteira. No Windows a
maximizacao e feita pela API do console; no Linux e no macOS o pedido e enviado ao
terminal, e terminal que nao aceita simplesmente mantem o tamanho que estava.

Ao mandar uma pergunta, aparece por alguns instantes a trilha do pedido acima da
linha de digitar: START -> AGENTE -> FERRAMENTA -> MODELO -> TELA. A etapa acesa e a
que esta com o pedido naquele momento, com o tempo real ao lado, e a trilha recolhe
quando a resposta chega (a trilha so aparece para pedido ao agente: comando de
barra e menu de arquivo nao a desenham). Abaixo das etapas ficam os tokens de cada pedaco
(entrada sob AGENTE, saida sob MODELO, total sob TELA), abreviados: 800, 2.00k,
1.20M. Para desligar: `/palco desliga`.

Parar e reler (pensado para idoso e crianca - um toque so):

| Tecla | O que faz |
|-------|-----------|
| CTRL+C ou ESC durante a resposta | PARA de responder e do comando na hora |
| ENTER com texto durante a resposta | avisa o turno em andamento; o modelo le na proxima rodada |
| CTRL+C duas vezes seguidas | saida de seguranca se algo travar |
| Roda do mouse ou barra lateral do seu terminal | reler o texto que subiu |
| CTRL+C com a linha vazia | fecha o TEO (ESC nunca fecha sozinho) |
| Ctrl+J, ou terminar a linha com `\` e ENTER | pula linha no `voce>` (escrever em varias linhas; no cmd do Windows Alt+Enter e tela cheia) |

Barra fixa embaixo sempre diz o que apertar; durante a resposta ela mostra
"respondendo... PARA PARAR: CTRL+C ou ESC".

Atalhos rapidos (nao perguntam licenca, so mostram):

| Atalho | O que faz |
|--------|-----------|
| `/` | na tela fixa abre o menu da pasta atual (escolhe por numero); no modo simples, lista |
| `@` | na tela fixa abre o menu de arquivos para anexar; no modo simples, lista os arquivos |
| `@<arquivo>` | anexa o arquivo; depois e so perguntar sobre ele. PNG/JPG/WEBP/GIF/BMP vao como IMAGEM para a visao do modelo (ate 5 MB); escrever o caminho da imagem na mensagem tambem anexa |
| `/ls <pasta>` | lista uma pasta especifica (sem menu) |

Comandos:

| Comando | O que faz |
|---------|-----------|
| `/modelo` | lista os modelos publicados pelo servidor |
| `/modelo <nome ou numero>` | troca o modelo (fica salvo no config) |
| `/provedor` | lista os provedores cadastrados (ex.: 1 deepseek, 2 local) |
| `/provedor <nome ou numero>` | troca o provedor em uso na hora (fica salvo) |
| `/pensamento liga\|desliga` | mostra ou esconde o bloco cinza na tela (o modelo segue pensando); avancado: nivel enviado ao servidor auto off minimum low medium high xhigh max ultra |
| `/palco liga\|desliga` | mostra ou esconde a trilha do pedido durante a resposta (so na tela fixa) |
| `/ctx` | medidor do contexto; `/ctx <numero>` define o limite e salva (ex.: `/ctx 65000`; aceita 65k, 65.000, 65 mil) |
| `/configurar` | conserta ou cadastra provedor sem sair do TEO (mesmo assistente do `bgh setup`) |
| `/doctor` | diagnostico da conexao e da maquina na propria tela |
| `/atualizar` | confere se ha versao nova no GitHub; se houver, pede licenca e instala (mesma versao: avisa que esta tudo certo) |
| `/mem <texto>` | grava uma preferencia sua na memoria |
| `/lingua` | troca o idioma da tela: 1) Portugues  2) English  3) Espanol (fica salvo). Atalhos: `/language`, `/idioma` |
| `/nov` `/skills` `/ajuda` `/sair` | conversa nova, skills, ajuda, sair |

Idioma: o TEO fala portugues (de fabrica), ingles e espanhol. O instalador pergunta
o idioma no inicio e o `/lingua` troca a qualquer momento, na hora - banner, ajuda,
menus, licenca, avisos e barra de baixo. Os comandos funcionam nos tres idiomas em
qualquer idioma de tela (`/help`, `/new`, `/model`, `/thinking`, `/exit`...), e o
modelo passa a responder no idioma escolhido (se a pessoa escrever em outro idioma,
ele responde no idioma da mensagem).

Versao nova: ao abrir, o TEO confere sozinho (uma vez, sem travar a tela) se ha
versao nova e avisa "existe versao nova do TEO (vX.Y.Z). Para atualizar, digite
`/atualizar`". Sem internet ele avisa que nao conseguiu conferir e segue
funcionando; o `update_check` no `~/.bgh/config.json` desliga a consulta.

Icone: o atalho do desktop sai com o gato do TEO - Linux (`.desktop` com `Icon=`),
Windows (atalho com `teo.ico` e o exe com icone) e macOS (app `TEO.app`). Os icones
vivem em `bgh/assets/` e sao gerados por `scripts/make_icons.py` (sem dependencias).

- Pensamento do modelo: se o servidor devolve `reasoning_content`/`reasoning`
  (llama.cpp com Qwen thinking, DeepSeek-R1 etc.), aparece como
  `pensamento> ...` antes da resposta.
- Contexto: apos cada resposta sai `contexto: NN% de 156000 chars` (verde/amarelo/
  vermelho); aos 85% a barra de baixo entra na cor de alerta e a proxima rodada
  compacta sozinha em resumo (o TEO avisa na tela enquanto compacta). Se o servidor
  recusar o tamanho, ele compacta e tenta de novo em vez de parar. O ponto de
  compactacao e ajustavel: `context_compress_pct` no `~/.bgh/config.json`.

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

===============================================================================
>>>>  LE ISTO ANTES DE FECHAR A PAGINA  <<<<
===============================================================================

O TEO nasceu das maos de um desenvolvedor brasileiro, feito do zero, e
continua dele pra voce: o programa e aberto, o codigo e seu, para sempre.

Mas existe um custo invisivel atras da tela: o cerebro que faz o TEO
pensar quando o servidor local do usuario nao da conta. Se o TEO ja te
ajudou a escrever um e-mail, arrumar uma pasta, tirar nota fiscal de
uma foto ou resolver o que quer que seja na sua maquina, ha um jeito
simples e direto de retribuir:

              >>>>  ASSINE IA.NUBESBR.COM  <<<<

              https://ia.nubesbr.com

Sua assinatura paga o servidor que faz o TEO pensar e mantem este
projeto vivo - sem propaganda, sem venda dos seus dados, sem pegadinha.
Quem assina usa o modelo do servidor lado a lado com o TEO: e so
cadastrar o provedor (o TEO pergunta a chave uma vez) e conversar.

Cada assinatura financia a proxima versao. Obrigado por chegar ate o fim
do README - quem le tudo merece saber quem mantem a luz acesa.

===============================================================================

## Licenca

MIT (arquivo `LICENSE` na raiz): use, estude, modifique e distribua.

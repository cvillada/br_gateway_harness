# Changelog

## 0.2.5

Silencio deixou de parecer trava, e "parar" passou a valer dentro das ferramentas.

- Espera do modelo virou numero na tela: a barra de baixo mostra "rodando... 47s"
  e a ferramenta em andamento ha quantos segundos ("search_files 12s").
- Teto de espera por perfil: 120 s para modelo na propria maquina, 300 s para
  servidor remoto (contexto grande demora ate 1 minuto so para ser lido). Ajustavel
  com `request_timeout_s` no config.json.
- Uma pergunta nao vira fila no servidor: `max_retries` caiu de 2 para 1 (antes, um
  timeout injetava 4 pedidos identicos na fila de quem divide o mesmo motor).
- Queda sem streaming agora avisa na tela em vez de repetir escondido.
- Modelo que gasta tudo no pensamento e devolve texto vazio ganha aviso ("apenas
  pensou; pergunte de novo ou suba max_tokens") em vez de tela muda.
- "Parar" (CTRL+C / ESC) agora derruba a ferramenta no meio: leitura de arquivo,
  busca, comando e run_python param na hora e o turno fecha sem nova rodada.
- Busca em arquivos ganhou teto (`search_time_limit_s` 20 s, `search_max_files`
  20000) e ignora pastas gigantes (AppData, Library, snap, venv, caches); ao bater
  o teto ela diz onde parou e pede uma pasta mais especifica.
- Assistente de configuracao sugere orçamento de contexto por provedor (45000 para
  servidor remoto NubesBR) e sobe `max_tokens` para 3072 nesse perfil.

## 0.2.4

- Preset NubesBR (opcao 2 do assistente) passou a vir com a URL publica
  https://ia.nubesbr.com/v1/ no lugar do endereco interno de rede.
- Repo tornou-se publico; o instalador pratico de 2 linhas do Windows passou a
  funcionar para qualquer pessoa (baixa o wheel do Release mais novo sozinho).

## 0.2.3

- Compatibilidade com Windows: matar comando parado agora usa taskkill /T la
  (a API POSIX de grupos nao existe no Windows); o resto ja era portavel.
- README ganhou instalacao nos tres sistemas: pasta TEO + ambiente virtual
  (PowerShell no Windows; bash no Linux/macOS) e binarios por sistema.
- Workflow do GitHub Actions passou a gerar motor.exe (Windows) e motor-macos
  (macOS) em cada tag, anexados ao Release. TEO roda em Windows, macOS e Linux.

## 0.2.2

- O harness agora se chama TEO (nome do gato preto do autor). Todos os textos
  visiveis passaram a usar TEO (ajuda, licenca, diagnostico, assistant).
- A abertura comeca com uma linha em branco, o gatinho ASCII com o nome TEO
  embaixo da boquinha, outra linha em branco e ai sim o divisor "=" para o
  restante das frases.

## 0.2.1

- O bloco de boas-vindas da abertura agora comeca e termina com uma linha
  de "=" ate perto da borda da tela (igual ao divisor "-").
- O /ajuda tambem vem entre dois divisores "=".
- Os divisores se ajustam a largura da janela (com folga de 2 colunas).

## 0.2.0

- A tela passou a usar o historico natural do proprio terminal (igual aos
  programas de sempre (pedido dos usuarios): as mensagens sobem para o
  rolamento DE VERDADE do terminal. A rodinha do mouse e a barra lateral
  que rolam a conversa sao as DO PROPRIO TERMINAL - sem tela isolada,
  sem rolagem interna, sem pedir nada ao terminal.
- Ao sair, a conversa continua visivel na janela (da para reler depois).
- Barra de baixo nunca mais embrulha: ela se corta sozinha na largura da
  janela (com o medidor de contexto ela encurta a explicacao).
- Removida a barra '#' interna e os controles de rolagem antigos (ja nao
  ha area fechada para rolar por dentro).

## 0.1.8

- Corrigido de vez a roda na linha do "voce>": alguns terminais mandam a
  roda como tecla especial sem posicao (ESC[62~ / ESC[63~) e a biblioteca
  transformava isso em setinha, andanto o historico digitado. Agora essas
  teclas tambem rolam o texto da tela e nunca mexem na linha de digitacao.

## 0.1.7

- A roda do mouse sobre a linha do "voce>" nao rola mais a conversa
  (ali sao so as setas para cima/baixo, que recuperam o que foi
  digitado). Rolagem com a roda e no centro da tela, na area de
  mensagens, e na barra lateral da direita.

## 0.1.6

- Barra lateral na area de mensagens: um pegador '#' na borda direita.
  Clique ou arraste para subir e rever as mensagens que sairam da tela.
  Nada e apagado: a conversa inteira fica guardada; barra, roda do mouse
  e PageUp/PageDown mostram o que ja passou. Roda tambem funciona sobre
  a barra.

## 0.1.5

- A roda do mouse voltou a rolar a tela. O app estava com o suporte a
  mouse desligado, entao a roda era tratada pelo proprio terminal (por
  isso so a barra de rolagem funcionava). Agora a roda rola em qualquer
  lugar da area de mensagens e tambem sobre a linha do "voce>".
- As setas para cima/baixo recuperam o que foi digitado ate em sessoes
  novas (historico salvo em ~/.bgh/input_history.txt). A carga do
  historico agora comeca junto com a abertura da tela, entao a primeira
  seta ja acha as entradas anteriores.

## 0.1.4

- Niveis de pensamento: auto, off, minimum, low, medium, high, xhigh, max, ultra
  (o antigo "on" continua aceito).
- Ao trocar de modelo (/modelo) ou de provedor (/provedor), abre menu na tela:
  [1] manter atual [2] off [3] minimum ... [10] auto. Enter sozinho ou ESC =
  manter atual (nunca escolhe por engano).
- /thinking <nivel> define na hora; /thinking sozinho mostra o nivel atual e a lista.
- No envio ao servidor o nivel vira reasoning_effort e/ou thinking_budget
  (OpenAI/llama.cpp/OpenRouter/qwen3). Queda em escada: se o servidor rejeitar um
  campo, ele e removido e o chat continua funcionando normalmente.

## 0.1.3

- Eco imediato: ao dar ENTER a fala da pessoa aparece na hora na tela (azul-claro),
  antes mesmo do modelo comecar a pensar - a tela nunca fica muda.
- Fim do texto "corrido": as quebras de linha do modelo viram linhas reais; listas
  aparecem um item por linha com "- ". Simbolos de markdown (**, #, ```) saem da
  resposta.
- System prompt agora exige legibilidade para idoso/crianca: uma ideia por linha,
  lista com "- " por item, sem markdown, frases curtas.
- Margem estilo Hermes: o texto para 2 colunas antes da borda da tela e pula linha
  quando necessario (nunca encosta na borda).
- Streaming ja era vivo (medido: conteudo novo a cada 0.25s durante o turno); o que
  atrasava a sensacao era a tela sem o seu proprio texto nos primeiros segundos.

## 0.1.2

- Ajuda: SO os comandos ficam em roxo suave; a explicacao continua branca e tudo
  cabe numa linha unica com colunas alinhadas.
- Medidor de contexto passa para a ULTIMA linha da tela (barra de baixo), junto
  das instrucoes: "contexto: X% de N chars (M mensagens) | ENTER = falar | ...".
- Processando: barra mostra bonequinho girando "| / - \" + "rodando..." e o
  contexto, separados por " | ": "\ | rodando... | contexto: ... | PARA PARAR...".
- Linha "-" tambem abaixo do "voce>" (entrada entre duas linhas iguais).

## 0.1.1

- Tela fixa agora mostra TODAS as cores que o nucleo envia (antes
  saia tudo branco): itens da ajuda em roxo suave, avisos em ciano/amarelo,
  erros em vermelho, medidor de contexto verde.
- Pensamento do modelo em CINZA ESCURO e resposta em BRANCO CLARO, na tela fixa
  e no modo classico; eventos de ferramenta em azul suave.

## 0.1.0

Primeira versao publicada do Motor (agente CLI local para maquina do usuario).

Nucleo:
- Chat com TELA FIXA (estilo Hermes): entrada sempre embaixo, mensagens rolaveis
  (roda do mouse / PageUp/PageDown), barra de ajuda permanente no rodape.
- BOTAO DE PARAR: CTRL+C/ESC interrompe a resposta do modelo, cancela ferramenta
  antes de executar e mata comando em andamento; segunda pressao = saida de seguranca.
- Streaming da resposta e do "pensamento" do modelo em blocos separados.
- Modo classico de rolagem preservado para pipe/script (sem terminal interativo).

Ferramentas reais:
- run_command (interrumpivel), run_python, ler/escrever/procurar arquivos,
  pesquisa web sem API paga, documentos (md/html em ~/Documentos),
  instalacao de biblioteca Python com licenca e motivo em linguagem simples.

Seguranca (menu numerico em portugues, publico idoso/crianca):
- Seguro roda direto; perigoso pede licenca [1 desta vez / 2 nesta conversa /
  3 sempre / 4 nao]; Enter sozinho = nao.
- Uma unica licenca por comando que toca varias regras.
- Piso duro inegociavel (rm -rf /, fork bomb, dd em disco).
- `bgh approvals` revisa as permissoes "sempre".

Modelo e contexto:
- Perfis multiplos de provedor (deepseek/nubesbr/local/outro) com troca no chat
  (`/provedores`, `/provedor`) e migracao automatica de config antigo.
- Anti-loop: chamada identica cortada na 3a repeticao; 5 falhas em sequencia
  fecham o turno com explicacao.
- Compressao automatica de contexto + medidor visual por resposta.

Interface do usuario:
- Assistente de configuracao embutido na instalacao (fluxo unico, teste de conexao
  com auto-correcao de chave).
- Atalhos `/`, `/ls`, `@arquivo` (listar/anexar), `/ajuda`, `/nov`, `/mem`,
  `/modelos`, `/modelo`, `/thinking`, `/ctx`, `/skills`, `/sair`.
- `bgh doctor` (diagnostico da maquina + conexao).

Skills de fabrica (escritas para as ferramentas do Motor):
- document-writing, hardware-troubleshooting, software-troubleshooting,
  internet-research, python-best-practices, impressora, wifi, audio.

Distribuicao:
- Wheel (`pip install bgh_motor-*.whl` -> comando `bgh`) e binario unico `motor`.
- Instalador `install.sh` que emenda o assistente de configuracao.

# Changelog

## 0.2.23

Uma TECLA para falar em vez de digitar - o `/ditar` continua existindo.

- F2, na tela fixa, faz exatamente o que o `/ditar` faz: ouve o microfone,
  transcreve no idioma da tela e poe o texto na linha para conferir antes do
  ENTER. Com a linha VAZIA, a barra de ESPACO faz o mesmo - e a tecla mais facil
  de achar no teclado para quem nao enxerga a tela.
- Dois bips do terminal marcam o comeco e o fim da escuta (nao depende de audio
  do sistema). O TEO nunca fala por cima do microfone: a voz e calada antes de
  comecar a ouvir.
- A barra de baixo mostra "ouvindo Ns" durante a escuta. ESC (ou CTRL+C) corta na
  hora e a resposta e "Parei de ouvir" - e nao "nao entendi nada", que era o que
  aparecia antes.
- Segurar a tecla para falar NAO existe em terminal (nao ha evento de soltar
  tecla, so repeticao): por isso a parada e automatica, quando a pessoa cala.
- A ajuda ganhou a secao "Falar em vez de digitar" e ela aparece LOGO ACIMA de
  "Comandos:" (a tecla tem que estar a vista antes da lista grande). Ao ligar a
  voz (`/voz`), o TEO avisa em voz alta que a tecla existe.
- Suite local: 492 testes verdes nesta maquina; o CI (ubuntu, windows, macos)
  roda no push, junto do build.

## 0.2.22

Agora da para ESCREVER FALANDO: `/ditar`, nos tres idiomas, sem internet.

- `/ditar` (`/dictate`, `/dictar`): a pessoa fala e o TEO escreve. O texto entra
  na linha de digitar para conferir (e corrigir) antes do ENTER - nada e enviado
  so porque foi falado.
- Reconhecimento LOCAL (vosk/Kaldi, roda na CPU): o som NAO sai do computador e
  nao precisa de chave nem de conta. Importa quando o publico e crianca e idoso.
- Os tres idiomas da tela, de fabrica: portugues, ingles e espanhol. O ditado
  SEGUE o `/lingua`: trocou a lingua da tela, o reconhecedor troca junto, sem
  reiniciar (e os avisos tambem mudam de idioma).
- O modelo de cada idioma (~40-55 MB) e baixado UMA vez, na primeira vez que a
  pessoa dita naquele idioma, com aviso de tamanho e permissao; depois funciona
  offline. Fica em `~/.bgh/models/vosk/` e NAO e apagado pelo `/limpar` (o
  `/limpar` mexe so na pasta de rascunhos).
- Vem na instalacao: `vosk` e `sounddevice` entram no `requirements.txt` (o
  instalador ja roda `pip install -r`), e o `/atualizar` passou a conferir o
  `requirements.txt` depois de trocar o wheel - sem isso, quem ja tinha instalado
  nunca receberia a dependencia nova. Os binarios (`motor.exe`, `motor-macos`)
  levam o vosk e a PortAudio dentro.
- Se o pacote nao estiver instalado, o `/ditar` avisa em vez de falhar calado; se
  o microfone estiver ocupado ou negado, avisa e a conversa continua.
- O log tecnico do reconhecedor (Kaldi/Vosk) nao vaza mais para a tela: ele some
  do terminal (era texto de depuracao no meio da conversa).
- CTRL+C ou ESC durante a escuta corta a gravacao na hora, em vez de esperar o
  fim da fala ou o teto de 25 segundos.
- Correcao de usabilidade: quem cala a leitura e o **ESC**, nao o CTRL+C. Na
  tela fixa o CTRL+C com a linha vazia FECHA o TEO, entao a ajuda que mandava usar
  CTRL+C para calar a voz mandava a pessoa fechar o programa sem querer. O ESC
  cala a voz e, quando o que estava tocando era a voz, nao apaga o que ja foi
  digitado na linha; o CTRL+C continua com o papel dele (parar o modelo / sair).
- Suite local: 483 testes verdes nesta maquina; o CI (ubuntu, windows, macos)
  roda no push, junto do build.

## 0.2.21

Tres comandos novos: limpar os rascunhos, trocar a cor de fundo e aumentar a letra.

- `/limpar` (`/clean`, `/limpiar`): apaga os arquivos que o TEO cria na pasta
  `scratch` - os scripts da ferramenta `run_python` e os textos que a voz grava -
  e diz quantos arquivos e quanto espaco foram liberados. Pergunta antes num menu
  (1 apagar / 2 deixar), nunca apaga por conta propria e NAO toca em conversa,
  memoria, skills nem configuracao, que ficam um nivel acima em `~/.bgh`.
- `/fundo` (`/background`, `/fondo`): cor de fundo da tela - branco, amarelo,
  verde, azul, vermelho, preto e "padrao" (a cor do seu terminal). A letra muda
  sozinha para continuar legivel: fundo claro usa letra escura e fundo escuro usa
  letra clara, inclusive nas cores de aviso/erro e no rodape. O contraste de cada
  par e MEDIDO pela suite (regra WCAG AA), nao escolhido no olho.
- A cor e aplicada pelo padrao do proprio terminal (OSC 11 para o fundo, OSC 10
  para a letra): pinta a janela inteira, inclusive o que ja rolou. A tela do TEO
  tambem se pinta, entao terminal que nao aceita a sequencia continua legivel.
  Ao sair, o TEO devolve a cor do terminal - ele nao sequestra a janela.
- `/fonte` (`/font`, `/fuente`): tamanho da letra em quatro passos (normal,
  grande, maior, enorme). No Windows o console tem API e a letra muda na hora e
  fica guardada para as proximas aberturas. No Linux/macOS a letra pertence ao
  terminal: o TEO reabre uma janela nova com zoom (`gnome-terminal --zoom`,
  `xterm -fs`, `kitty`, `alacritty`, `xfce4-terminal`) e avisa que a conversa
  continua la; quando nao reconhece o terminal, ensina as teclas (CTRL e +).
- A ajuda (`/ajuda`) ganhou os tres comandos nos tres idiomas.
- Suite local: 457 testes verdes nesta maquina; o CI (ubuntu, windows, macos)
  roda no push, junto do build.

## 0.2.20

A linha de digitar nao some mais pela direita, o ENTER se chama "enviar" e o TEO
passou a LER as respostas em voz alta (`/voz`) - pensando em quem enxerga pouco.

- Frase longa no `voce>`: quando o texto chegava no canto direito da tela, a
  linha era empurrada para a esquerda e o comeco da frase desaparecia (a janela
  de digitar rolava na horizontal em vez de quebrar). Agora o texto desce para a
  linha de baixo, alinhado embaixo do `voce>`, e a janela cresce ate 8 linhas -
  sem nunca empurrar a barra de baixo para fora da tela.
- A correcao tem duas partes que so funcionam juntas: a janela de digitar passa
  a QUEBRAR a linha (`wrap_lines=True`) e a altura dela passa a contar linhas de
  TELA (uma frase de 103 colunas ocupa 4 linhas numa janela de 34), nao o numero
  de ENTERs que a pessoa deu.
- Barra de baixo: `ENTER = falar` virou `ENTER = enviar` (em ingles `ENTER =
  send`, em espanhol `ENTER = enviar`) - a tecla manda a mensagem.
- Ctrl+J e a barra invertida no fim da linha continuam quebrando linha como
  antes; as setas cima/baixo continuam chamando o que ja foi digitado.
- Acessibilidade: `/voz` liga e desliga a leitura em voz alta das respostas,
  usando a voz do PROPRIO sistema - nada de instalar nada. Linux: `spd-say`
  (speech-dispatcher) e, se ele nao responder, `espeak-ng`; Windows:
  PowerShell + `System.Speech` (funciona offline; voz pt-BR se o pacote de
  idioma estiver na maquina); macOS: `say` com a voz pt_BR instalada.
- A voz le so a RESPOSTA final: pensamento (cinza), trilha das ferramentas,
  avisos e mensagens de erro continuam calados - quem ouve quer a resposta, nao
  o rascunho. Antes de falar, o texto perde cerca de codigo, markdown, cores e
  linhas de separador, e resposta gigante e resumida em voz alta (o resto fica
  na tela).
- ESC cala a voz na hora (mesma tecla que para o modelo); mandar uma
  pergunta nova tambem cala a leitura anterior; sair do TEO cala. No Linux quem
  fala e o speech-dispatcher, entao o corte usa o comando de cancelar dele
  (`spd-say -C`) - matar o cliente nao calaria nada.
- O estado da voz fica gravado no `config.json`, comeca DESLIGADA (quem nao
  precisa nao ouve nada) e, se a maquina nao tiver voz do sistema, o `/voz`
  avisa em vez de fingir que ligou.
- Suite local: 405 testes verdes nesta maquina; o CI (ubuntu, windows, macos)
  roda no push, junto do build.

## 0.2.18

O aviso amarelo do "continue" acaba tambem para quem instalou antes.

- Limite de saida das instalacoes antigas: desde que o padrao subiu para 8192,
  so quem instalava do zero recebia o valor novo - o `config.json` do cliente
  antigo tinha 2048 gravado pelo assistente da epoca, e o valor gravado manda
  sobre o padrao. Resultado: resposta longa cortada no meio com o aviso
  "diga 'continue'" para sempre, ate reinstalar.
- Agora, na primeira execucao do TEO 0.2.18, o valor antigo (2048 ou 3072)
  sobe sozinho para o padrao atual e o arquivo ganha um carimbo
  (`max_tokens_migrado`). Uma vez so: ajuste manual depois da migracao no
  `config.json`, para baixo ou para cima, continua sendo respeitado.
- Quem ja tinha subido o teto a mao no `config.json` antes da migracao
  conserva o valor escolhido e so ganha o carimbo. Instalacao do zero ja
  vinha em 8192 e nao muda nada.
- CI: 377 testes verdes (ubuntu, windows e macos; Python 3.11 e 3.12).

## 0.2.17

O atalho do Mac agora sai com o gato do TEO - e o README fala as tres linguas.

- macOS: o atalho da Area de trabalho saia como um pergaminho branco (icone
  generico de applet) quando o sistema nao aceitava o icone copiado por cima.
  Agora o `TEO.app` e montado arquivo por arquivo, com o icone no nome que o
  proprio app aponta (`teo.icns`), e o instalador avisa na tela quando o icone
  NAO entrou (em vez de dizer que deu tudo certo).
- Quem ja instalou nao precisa reinstalar: `scripts/consertar_icone_mac.sh`
  conserta o atalho em dez segundos e mostra, antes de mexer, se o `TEO.app`
  existe e se o `TEO.command` (o pergaminho) esta na Area de trabalho.
- README em tres idiomas: `README.md` (portugues), `README.en.md` e
  `README.es.md`, com o seletor de idioma no topo dos tres. A suite confere que
  os tres continuam com a mesma estrutura (titulos, tabelas e exemplos).
- CI: 369 testes verdes (ubuntu, windows e macos; Python 3.11 e 3.12).

## 0.2.16

O TEO agora fala portugues, ingles e espanhol - e o atalho do desktop ganhou o gato.

- Idioma da tela: portugues (de fabrica), ingles e espanhol. O instalador pergunta
  o idioma antes de tudo e o assistente ja abre nele. A qualquer momento dentro do
  TEO o comando `/lingua` (ou `/language`, `/idioma`) troca o idioma na hora:
  banner, lista de ajuda, menus numericos, licenca, avisos e a barra de baixo -
  sem fechar e abrir o programa.
- Os comandos aceitam os tres idiomas em qualquer idioma de tela: `/ajuda`/`/help`/
  `/ayuda`, `/nov`/`/new`/`/nuevo`, `/modelo`/`/model`/`/modelo`, `/pensamento`/
  `/thinking`/`/pensamiento`, `/palco`/`/stage`/`/escenario`, `/configurar`/`/setup`,
  `/atualizar`/`/update`/`/actualizar`, `/skills`/`/habilidades`,
  `/sair`/`/exit`/`/salir`, `/lingua`/`/language`/`/idioma`. Quem ja decorou os
  comandos em portugues nao perde nada.
- O modelo tambem passa a responder no idioma escolhido (o pedido dele e as
  descricoes das ferramentas vao traduzidas); se a pessoa escrever em outro
  idioma, ele responde no idioma da mensagem.
- Aviso de versao nova na abertura: ao abrir o TEO ele confere (uma vez, em
  segundo plano, sem segurar a tela) se ha versao nova e avisa em uma linha
  "existe versao nova do TEO (vX.Y.Z). Para atualizar, digite /atualizar". Se nao
  houver internet, avisa que nao deu para conferir e que o TEO funciona
  normalmente; se o GitHub responder um codigo (limite/fora do ar), a frase cita
  o codigo em vez de culpar a conexao do usuario. Ja atualizado = silencio total.
- Icone do gato no atalho do desktop: Linux (atalho .desktop com Icon=), Windows
  (atalho com o .ico e o proprio motor.exe com icone) e macOS (app TEO com o gato
  no Finder, mantendo o atalho de terminal como reserva). O icone vem DENTRO do
  pacote instalado - nada extra para baixar - e o `scripts/make_icons.py` gera os
  tres formatos sem dependencias.
- Detalhe tecnico: catalogo unico em `bgh/i18n.py` (cada frase guarda as tres
  versoes na mesma entrada, e a suite confere isso), `cfg["lang"]` no config.json,
  `bgh/assets/` no wheel e nos binarios (PyInstaller `--add-data`/`--icon`).

## 0.2.15

O TEO reconhece sozinho quando a pessoa esta falando de uma imagem.

- Caso real (Mac): o usuario escreveu o caminho completo de uma captura de tela na
  mensagem ("nesse arquivo /Users/.../Captura de Tela ....png pode analisar?") e o
  TEO tentou ler como texto - chegou a instalar Pillow. So mandava a foto para o
  modelo quando o arquivo era anexado com `@`.
- Agora, caminho de imagem escrito na propria mensagem e reconhecido (inclusive com
  espaco no nome, como "Captura de Tela 2026-06-14 as 11.24.21.png") e a foto vai
  para o modelo ver; a tela avisa "vi uma imagem na sua mensagem".
- Memoria por modelo: se o provedor recusar a imagem, o TEO guarda que aquele
  modelo nao le imagem e, na proxima vez, avisa ANTES em vez de mandar de novo -
  decisao tomada antes, como deve ser. Trocar de modelo limpa essa memoria.
- Quando nao da para ver a imagem, a mensagem oferece o caminho alternativo (ler
  por OCR, com instalacao de biblioteca) em vez de so recusar.
- Menu de pasta pagina de verdade: pasta com muita coisa mostra 18 itens por vez e
  a opcao "mais itens (mais N)" mostra o resto (antes ela aparecia mas CANCELAVA a
  escolha - quem digitava o numero dela voltava para a conversa sem entender). Em
  qualquer pagina existe "voltar ao inicio da lista".

## 0.2.14


Duas coisas que faziam falta no dia a dia: o TEO le imagem de verdade e nao deixa lixo na pasta do usuario.

- Ler imagem (visao): `@foto.png` (ou escolher a foto no menu do `@`) manda a imagem
  para o modelo em vez de tentar adivinhar o conteudo. Antes ele instalava biblioteca
  e fazia OCR caseiro. Aceita png, jpg, jpeg, webp, gif e bmp ate 5 MB; foto maior
  recebe uma frase clara pedindo para diminuir.
- Modelo sem visao: se o provedor recusar a imagem, o TEO avisa em uma linha
  ("o modelo deste provedor nao le imagem; vou seguir sem a foto") e responde com o
  texto - nunca deixa a pessoa sem resposta nem mostra erro tecnico.
- A foto nao vai para o `session.json` (fica um marcador "[imagem anexada]") nem
  entra na conta do medidor de contexto: base64 no arquivo deixaria a sessao com
  megabytes e o medidor mentiria.
- Pasta do usuario limpa: secao nova no prompt separando RASCUNHO de ENTREGA -
  codigo de teste e arquivo de apoio vao para o `run_python`, que roda na pasta de
  rascunho do TEO; `write_file`/`make_document` ficam so para o arquivo final.
- Ferramenta nova `limpar_apoio(pasta, manter)`: apaga SOMENTE os arquivos que o
  proprio TEO criou nesta conversa (ele passa a registrar cada `write_file`),
  preservando o entregavel. Nunca toca em arquivo que ja era do usuario - para
  esses continua valendo a licenca.

## 0.2.13


O instalador nao trava mais em cima de uma instalacao anterior quebrada.

- Caso real (maquina do cliente): a reinstalacao parava com "Cannot uninstall
  bgh-motor None / uninstall-no-record-file" - o pacote antigo estava sem o arquivo
  RECORD, entao o pip nao conseguia desinstalar e o `--force-reinstall` falhava,
  deixando a pessoa sem o TEO.
- Os dois instaladores (Windows e Linux/macOS) passam a instalar com
  `--ignore-installed`: o pip sobrescreve os arquivos em vez de tentar desinstalar.
  Se ainda assim falhar, limpam os restos de metadados e tentam outra vez; a
  mensagem final mostra o comando exato para resolver na mao.
- Instaladores usam `python -m pip` (o pip.exe do ambiente reclamava "To modify pip,
  please run..." ao se atualizar) e mostram a versao lida do proprio pacote
  (`import bgh`), que e a prova de que a instalacao realmente aconteceu.
- `/atualizar` tambem instala com `--ignore-installed`, pelo mesmo motivo.

## 0.2.12

A tela nao trava mais em turno longo com muita saida.

- Causa (medida em maquina de cliente): a tela re-quebrava TODAS as linhas da
  conversa a cada pedaco de texto recebido (`textwrap` sobre o texto inteiro). Num
  turno de 600 segundos, com raciocinio e saida de ferramenta acumulados, cada
  quadro ficava mais caro ate congelar - e o CTRL+C caia dentro do `textwrap`,
  virando traceback na tela. O turno longo em si era a prorrogacao funcionando.
- Agora as linhas ja fechadas ficam em cache (sao quebradas uma vez) e so a cauda
  que ainda esta chegando e refeita. Medido: 6000 linhas + 300 quadros de
  streaming fizeram 300 quebras em vez de 1,8 milhao.
- CTRL+C durante o desenho fecha limpo, sem traceback.
- Desenho a prova de falha: erro de quebra de linha vai para o `erro.log` e a tela
  continua, em vez de derrubar o programa.
- O palco mostra "rodada N" quando o turno prorroga alem da primeira etapa, para
  a espera longa ter progresso visivel.
- Escrever em varias linhas no `voce>`: **Ctrl+J** pula linha, e terminar a linha
  com `\` + ENTER continua na linha de baixo (regra de shell, funciona ate no cmd do
  Windows). **Alt+Enter** tambem pula linha onde o terminal entrega a tecla (Linux;
  no macOS so com "Use Option as Meta"; no cmd do Windows Alt+Enter e tela cheia,
  entao fica de fora). A caixa de entrada cresce ate 8 linhas e volta a uma depois
  de enviar. Tudo isso aparece no `/ajuda`, na secao "Escrever em varias linhas".

## 0.2.11

O streaming voltou ao normal em provedores cujo gateway recusa campos extras.

- Causa: para contar tokens o TEO passou a enviar `stream_options` (0.2.9). O gateway
  do nubesbr recusa qualquer campo fora da lista dele com 400 generico, sem citar o
  nome do campo - e o fallback so removia o campo quando a mensagem citava
  "stream_options". Resultado: cada rodada anunciava "o servidor nao aceitou a
  resposta em pedacos" e caia para responder de uma vez, perdendo o streaming.
- Correcao: se o pedido de streaming falhar, o TEO repete na hora SEM o campo (sem
  perder o streaming) e memoriza a recusa - nas proximas rodadas o campo nem e
  enviado. Em provedor que aceita, a contagem de tokens continua funcionando.
- Limite de uso (429) continua sem retentativa, para nao gastar cota repetindo.

## 0.2.10

O limite de ferramentas deixou de ser uma parede: se o trabalho esta rendendo, o
TEO continua sozinho ate um teto seguro.

- Ao chegar em 20 ferramentas num mesmo pedido, se o turno esta progredindo
  (nenhuma falha em sequencia), o TEO avisa na tela - "ja usei 20 ferramentas
  neste pedido; vou continuar por mais 20 (CTRL+C ou ESC para parar)" - e segue
  trabalhando sozinho.
- Teto de 40 por pedido. Ao chegar nele, responde com o que ja tem e avisa que a
  pessoa pode escrever "continue" para seguir de onde parou.
- Se o turno estiver falhando, NAO prorroga: fecha na etapa, como antes. As duas
  travas antigas continuam valendo (chamada identica 3 vezes e 5 falhas seguidas)
  e sao elas que impedem loop de verdade.
- Nada de loop infinito: o teto e sempre respeitado e CTRL+C/ESC interrompe em
  qualquer rodada.
- Ajustavel no config.json: `max_tool_rounds` (tamanho da etapa, padrao 20) e
  `max_tool_rounds_teto` (padrao 40).
- Resposta vazia ou cortada nao fica mais em silencio: quando o modelo gasta o
  limite de saida pensando (`finish_reason` = length) e volta sem texto, a tela
  avisa e ensina o caminho (/pensamento low ou max_tokens maior). O aviso antigo
  so valia para o modo SEM streaming - por isso, com streaming, a tela ficava
  muda depois da pergunta (visto em maquina Windows com o nubesbr). Resposta
  cortada no meio agora avisa e sugere "continue".

## 0.2.9

O TEO passa a mostrar, enquanto trabalha, o caminho do pedido - e o desenho segue
os eventos reais, nunca um relogio.

- Palco: durante o processamento aparece, acima da linha de digitar, a trilha
  START -> AGENTE -> FERRAMENTA -> MODELO -> TELA. A etapa acesa (fundo ciano,
  como item de menu selecionado) e a que esta com o pedido naquele momento, e o
  marcador azul embaixo aponta o ponto exato. Quando a resposta chega, a trilha
  recolhe e o historico continua onde estava (a rolagem do terminal nao muda).
- O numero de segundos e o tempo real do turno e da ferramenta: se uma ferramenta
  trava 30 segundos, a trilha fica parada nela em vez de fingir progresso.
- Liga por padrao; `/palco desliga` (ou `"palco": false` no config.json) devolve a
  tela exatamente como era antes.
- Janela estreita (menos de 70 colunas): a trilha vira uma unica linha no rodape
  do palco, para nao tomar 4 linhas da conversa.
- ASCII puro: terminal de Windows com fonte raster desenha igual, sem emoji.
- Tokens por etapa: embaixo de AGENTE aparece o que o modelo leu (entrada),
  embaixo de MODELO o que ele escreveu (saida) e embaixo de TELA o total, sempre
  abreviado (800, 2.00k, 1.20M). Sao os numeros que o proprio servidor informa;
  FERRAMENTA fica sem numero porque nao existe contagem propria de ferramenta.
  O palco ainda fica 1,6 segundo na tela depois da resposta para mostrar a
  entrega e os numeros finais (o servidor manda a contagem no fim do pedido).
- Palco so aparece quando existe PEDIDO ao agente/modelo: `/ajuda`, `/modelo`,
  `/doctor`, `/ctx` e o menu de arquivo nao desenham mais a trilha (antes ela
  ficava na tela durante comandos, poluindo a leitura).
- Rodape: o medidor de contexto mostra a equivalencia em tokens com usado E
  teto - "contexto: 27% de 250000 chars (19.34k de 71.43k toks) (102 mensagens)".
  O numero antes era ambiguo (parecia que o teto em chars valia os tokens).
  Depois do primeiro pedido o valor usado e o que o servidor contou; antes disso
  e a estimativa de 3,5 caracteres por token, marcada com "~". Em janela estreita
  vira "ctx 27% de 250k (19.34k/71.43k toks) (102 msg)".

- Menu numerado de pasta e arquivo: na tela fixa, `/` abre o menu da pasta atual
  (escolher uma pasta entra nela; escolher um arquivo mostra nome e tamanho) e
  `@` abre o menu de arquivos para anexar. Nada de digitar caminho - a pessoa
  escolhe pelo numero, como no menu de licenca. A opcao 1 e sempre "cancelar",
  entao Enter ou ESC nunca escolhem nada por engano. Em script/pipe continua
  listando como antes (menu so onde ha tela).

## 0.2.8

O TEO avisa em palavra simples quando o provedor pede para esperar, e a entrega
ficou mais confiavel por dentro: todo push roda a suite antes de virar release.

- Limite de uso ou cota esgotada no provedor (erro 429): a tela agora explica o
  que aconteceu e o que fazer - "o provedor pediu para esperar: espere um pouco e
  mande a pergunta de novo; se acontecer sempre, use /provedor". Antes esse caso
  chegava como "Falha ao falar com o modelo" e parecia programa quebrado.
- Quando o servidor informa quantos segundos esperar, a mensagem mostra o numero.
  O aviso sai em amarelo (aviso), nao em vermelho (erro), e a dica aponta para
  `/provedor` em vez de mandar reconferir URL e chave.
- O TEO nao insiste sozinho depois desse aviso: um pedido, sem repetir na fila.
  Cada repeticao gastaria mais cota e aumentaria a espera.
- Erro comum de servidor (500, queda de rede) continua como antes: o limite de
  uso nao e confundido com defeito.
- Todo push no GitHub roda a suite offline em Linux, Windows e macOS (Python 3.11
  e 3.12). Antes o unico CI era o empacotamento: o binario saia mesmo com teste
  vermelho.
- README: as instrucoes manuais de instalacao nao citam mais numero de versao
  fixo (o texto mandava baixar um arquivo que ja nao existia na pagina de
  Releases) e a numeracao dos passos do Windows foi corrigida.
- Chave de provedor corrigida no assistente agora fica TAMBEM no perfil salvo:
  antes so o topo do config recebia a chave nova e o `/provedor` restaurava a
  antiga, devolvendo 401 no mesmo provedor que tinha acabado de ser testado com
  sucesso (visto em maquina Windows com OpenRouter).
- `/modelo` tambem atualiza o perfil salvo: trocar de provedor nao desfaz mais a
  troca de modelo sem avisar.
- Barra de baixo: o aviso (rodando/parar, licenca pendente, teclas) nunca cai. O
  medidor de contexto e o primeiro a encolher ("ctx 29% de 500k (88 msg)") e sai
  da barra se ainda nao couber; a largura passa a vir da JANELA do app, nao do
  buffer do console (no Windows as duas medidas divergem e a linha quebrava).
- A janela abre maximizada e com o nome TEO Agent (no Windows pela API do
  console; Linux e macOS recebem a sequencia do xterm, que terminal sem suporte
  simplesmente ignora).
- O prompt do modelo ganhou a secao "onde ficam as coisas" (config.json com a
  chave, session.json, memory.db, skills, erro.log) e a proibicao de inventar
  lugar: perguntado onde a chave mora, o modelo respondia "registro do Windows".

## 0.2.7

O TEO aprende a se atualizar sozinho e a falar mais claro com quem nao e tecnico.

- `/atualizar` (apelido `/update`): confere a versao em uso com a release "latest"
  do GitHub oficial do TEO. Mesma versao: avisa "ja esta atualizado" e segue.
  Versao nova: pede sua licenca na tela e instala o `.whl` da propria release com
  `pip install --no-deps --force-reinstall`. Quem abriu pelo icone (arquivo
  executavel) e orientado a rodar o INSTALAR_TEO.bat de novo. Sem internet, aviso
  simples - nunca pilha de erro na tela.
- Erros tecnicos nunca mais aparecem crus: qualquer falha inesperada vira uma
  frase humana na tela e a pilha completa e gravada em `~/.bgh/erro.log` (para
  quem der suporte ler depois).
- `/pensamento liga|desliga` (substitui `/thinking`, apelido antigo continua
  valendo): liga/desliga controlam a TELA - o bloco cinza aparece ou nao, e o
  trabalho do modelo nao muda. Niveis avancados (auto off minimum low medium high
  xhigh max ultra) continuam sendo o nivel enviado ao servidor, com o aviso
  honesto de que provedores hospedados podem ignorar o pedido. Nova chave
  `show_thinking` no config.
- Ajuda unificada, um comando por linha: `/modelo` lista e escolhe, `/provedor`
  lista e troca, `/ctx` mede e define (apelidos antigos `/modelos` e
  `/provedores` seguem funcionando para quem ja os usava).
- Lista de modelos agora marca `(em uso)` igual a dos provedores; quando o
  provedor renomeia o ID do modelo, uma linha discreta explica qual esta em uso
  e que escolher um numero da lista alinha o nome.
- Rodape do contexto em janela estreita: a explicacao curta entra primeiro, o
  trecho "teto; o servidor entrega..." e descartado antes de qualquer corte, e o
  medidor nunca e cortado no meio de um numero.
- Janela do terminal ganha nome "TEO Agent" na abertura (no Windows pela API da
  propria janela), facilitando achar o TEO entre outras janelas.
- No Windows, o system prompt passa a exigir comandos no formato cmd.exe desde a
  primeira tentativa (dir, findstr, type, %VAR%) e veta sintaxe de bash - menos
  tentativa-e-erro visivel e tarefas mais rapidas na maquina do cliente.
- Skills de fabrica novas: `spec` (transformar ideia em especificacao pronta para
  desenvolvedor), `dev` (trabalho de codigo com backup e passos pequenos),
  `dev-web` (pagina/painel HTML comecando por arquivo unico, testado de verdade)
  e `tdd` (teste antes do codigo, ciclo vermelho-verde-refatorar).
- Corrigido no mesmo dia: depois do `/nov` o medidor do rodape mostrava a leitura
  velha (ex.: 40% com 20 mensagens) ate a proxima resposta. Agora o `/nov` redesenha
  a barra na hora (1 mensagem, so o prompt do sistema) e derruba o aviso
  'Contexto compactado' herdado da conversa zerada.
- A barra de contexto agora segue o servidor de verdade: troca de provedor ou de
  modelo re-sonda o teto publicado e assume o valor dele; servidor que nao publica
  nada retira o numero antigo (barra nunca mostra teto emprestado de outro
  servidor). O teto gravado passa a carregar a procedencia (servidor+modelo); na
  abertura, re-sonda so quando a procedencia nao bate. Servidor com teto menor
  reduz o orcamento na hora, para comprimir antes de quebrar o turno.
- README ganhou a sessao de apoio ao projeto antes da licenca: assinatura
  ia.nubesbr.com mantem o servidor que faz o TEO pensar.

## 0.2.6

A configuracao agora se conserta dentro do proprio TEO, e o contexto pega o limite
de quem entrega sem parar mais a tela.

- `/configurar` entrou na tela: quem instalou, esqueceu a chave e ficou no `voce>`
  pode consertar o provedor atual ou cadastrar um novo sem sair do TEO e sem
  aprender comando fora (e o mesmo assistente do `bgh setup`, perguntando uma
  linha de cada vez na tela fixa; os provedores antigos continuam salvos).
  Mensagem que falha por conexao agora aponta `/configurar`, nao `bgh doctor`.
- `/doctor` na tela tambem: maquina, GPU e conexao diagnostica sem fechar a conversa.
- Limite de contexto vem do que o SERVIDOR entrega (igual ao Hermes), em tres
  caminhos: o motor local publica (`props` com `n_ctx`), a API publica (lista de
  modelos com `context_length`, estilo OpenRouter) e, quando nenhuma API publica
  (DeepSeek, Anthropic...), o assistente consulta o catalog publico models.dev
  (mesma fonte de metadados que o Hermes usa). Converte para caracteres com folga
  de saida/ferramentas e define o orcamento sozinho - sem nunca perguntar numero
  ao usuario leigo (ajuste fino depois com `/ctx`). Teto de leitura de 160000 chars
  protege maquina simples (ler contexto grande custa tempo na GPU); `/ctx` passa
  desse teto por escolha.
- Preset DeepSeek atualizado: `deepseek-chat`/`deepseek-reasoner` foram aposentados
  pelo provedor em 24/07/2026; o preset agora vem com `deepseek-v4-flash` (mesma
  URL). Quem tinha o nome antigo no config deve rodar `/configurar` (ou editar o
  config.json) para voltar a funcionar.
- Teto de saida por resposta (`max_tokens`) subiu de 2048 para 8192: escrever
  documento (write_file/make_document leva o texto inteiro na resposta da
  ferramenta) parava em ~7 mil caracteres por rodada; agora comporta ~28 mil.
  Configs antigos sem a chave herdam o valor novo sozinhos.
- Rodape deixa explicito quando o numero exibido e teto do TEO, nao limite do
  servidor: "contexto: 3% de 160000 chars | teto; o servidor entrega 1.048.576
  tokens". O valor descoberto no setup fica salvo (`server_context_tokens`).
- Fechamento de turno visivel e ao vivo (estilo Hermes): ao bater o limite de
  rodadas de ferramenta ou 5 falhas em sequencia, agora aparece um aviso na tela
  explicando o motivo, a resposta final chega em streaming (sem silencio morto
  com contexto cheio) e a instrucao interna de fechamento passou a ser em
  portugues - o modelo local parou de responder em ingles no fim do turno. Se o
  servidor recusar o tamanho ate no fechamento, ele compacta e fecha mesmo assim.
- Limite de rodadas de ferramenta por turno subiu de 12 para 20 (pesquisa e
  redacao longa nao caem mais no fechamento no meio do trabalho; o anti-loop real
  continua sendo chamada identica 3x / 5 falhas em sequencia). Regra nova no
  system prompt: nunca encerrar turno prometendo acao futura ("depois eu faco").
- Cabecalho "resposta" agora vale por chamada do modelo, nao por turno: em turnos
  com varias rodadas de ferramenta a resposta final saia colada no bloco de
  pensamento porque o cabecalho da primeira rodada ficava preso na tela.
- Steering no meio do processamento (estilo Hermes): digitar texto e dar ENTER
  enquanto o TEO trabalha entrega a mensagem ao modelo na proxima rodada de
  ferramenta (eco na tela + aviso de entrega), sem derrubar o turno. Mensagem que
  chega tarde demais vira o proximo turno automaticamente; nada se perde. Comandos
  de barra continuam valendo somente quando o turno termina, e um turno que o usuario
  mandou parar nao emenda as mensagens guardadas. No modo classico sem tela o
  input bloqueia - steering e exclusivo da tela interativa.
- Sugestao do servidor hospedado subiu de 45000 para 156000 chars (~45 mil tokens;
  o motor la aceita 262144 tokens; leitura medida: 125 mil chars custam ~77 s).
  Config novo comeca em 156000 (antes 60000). Modelo local continua em 60000.
- Compactacao comecou ANTES do teto: dispara a 85% do orcamento e roda antes de
  mandar o pedido (antes so depois da rodada de ferramentas, entao o proximo
  pedido chegava ao servidor ja estourado -> tela parava). O aviso "contexto
  enchendo" e a barra amarela sairao exatamente nesse mesmo ponto (antes o aviso
  aparecia em 70% e a compactacao em outro lugar, o que parecia compactar cedo
  demais). O ponto fica em `context_compress_pct` no config.json.
- Servidor recusando o tamanho: o TEO compacta a conversa e tenta de novo sozinho;
  se ainda nao couber, a mensagem de erro ja ensina `/ctx 60000`. Durante a
  compactacao sai "Compactando a conversa em resumo..." na tela - espera longa nao
  e mais lida como programa travado.
- Barra de baixo fica na cor de alerta (amarelo) quando o contexto passa do ponto
  de compactacao (85%), mesmo com o TEO parado.
- Ferramenta cortada no comeco da cauda da compactacao (sem o `assistant` parceiro)
  vai para o resumo: alguns servidores rejeitam a mensagem orfa.

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
- Assistente de configuracao sugere orcamento de contexto por provedor (45000 para
  servidor remoto NubesBR) e sobe `max_tokens` para 3072 nesse perfil.
- `/ctx 65000` agora define o limite de contexto na hora e salva no config.json
  (aceita 65k, 65.000 e 65 mil). Antes o numero era ignorado em silencio, o que na
  maquina do cliente parecia comando quebrado. `/ctx` sozinho segue sendo so o
  medidor; numero invalido ganha aviso com o uso correto.

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

"""Textos da interface do TEO em tres idiomas: portugues, ingles e espanhol.

Regra do projeto (publico do TEO e leigo): toda frase que a PESSOA le sai daqui,
nunca escrita direto no codigo. Cada chave guarda as TRES versoes na mesma linha,
na ordem de LANGS - assim e impossivel traduzir so metade de uma frase e a
revisao fica lado a lado.

- Idioma atual: cfg["lang"] ("pt" padrao), aplicado por set_lang() na abertura.
- Comando /lingua troca na hora e grava no config.
- Chave sem traducao cai no portugues; chave inexistente devolve a propria chave
  (a tela nunca fica muda por causa de traducao).
- Texto e ASCII puro (regra do projeto): sem acento em portugues e espanhol.
"""

LANGS = ("pt", "en", "es")
LANG_NAMES = {"pt": "Portugues", "en": "English", "es": "Espanol"}
_LANG = "pt"


def set_lang(code: str | None) -> str:
    """Fixa o idioma da sessao (codigo desconhecido volta para portugues)."""
    global _LANG
    code = (code or "").strip().lower()[:2]
    _LANG = code if code in LANGS else "pt"
    return _LANG


def get_lang() -> str:
    return _LANG


def lang_index() -> int:
    return LANGS.index(_LANG)


def t(key: str, **valores) -> str:
    """Texto da chave no idioma atual, com os campos {nome} preenchidos."""
    entrada = TEXTS.get(key)
    if entrada is None:
        return key
    texto = entrada[lang_index()] or entrada[0]
    if valores:
        try:
            texto = texto.format(**valores)
        except (KeyError, IndexError, ValueError):
            pass  # texto sem campo correspondente sai como esta; nunca quebra a tela
    return texto


# ---------------------------------------------------------------------------
# Comandos: qualquer idioma e aceito em QUALQUER idioma de tela (quem troca de
# idioma nao perde os dedos). A chave canonica e a de baixo, em ingles curto.
# ---------------------------------------------------------------------------
ALIASES = {
    "exit": ("sair", "exit", "quit", "salir"),
    "help": ("ajuda", "help", "ayuda"),
    "new": ("nov", "new", "nuevo", "nova"),
    "mem": ("mem", "memory", "memoria"),
    "skills": ("skills", "habilidades"),
    "model": ("modelo", "modelos", "model", "models"),
    "provider": ("provedor", "provedores", "provider", "providers",
                 "proveedor", "proveedores"),
    "thinking": ("pensamento", "thinking", "pensamiento"),
    "stage": ("palco", "stage", "escenario"),
    "ctx": ("ctx", "contexto", "context"),
    "setup": ("configurar", "configure", "setup", "configuracion"),
    "doctor": ("doctor",),
    "update": ("atualizar", "update", "actualizar"),
    "lang": ("lingua", "language", "idioma", "lang"),
    "voice": ("voz", "voice", "voz"),
    "clean": ("limpar", "clean", "limpiar"),
    "background": ("fundo", "background", "fondo"),
    "font": ("fonte", "font", "fuente"),
    "dictate": ("ditar", "dictate", "dictar"),
}

# Como cada comando aparece ESCRITO na ajuda/avisos, por idioma.
CMD = {
    "exit": ("/sair", "/exit", "/salir"),
    "help": ("/ajuda", "/help", "/ayuda"),
    "new": ("/nov", "/new", "/nuevo"),
    "mem": ("/mem", "/mem", "/mem"),
    "skills": ("/skills", "/skills", "/habilidades"),
    "model": ("/modelo", "/model", "/modelo"),
    "provider": ("/provedor", "/provider", "/proveedor"),
    "thinking": ("/pensamento", "/thinking", "/pensamiento"),
    "stage": ("/palco", "/stage", "/escenario"),
    "ctx": ("/ctx", "/ctx", "/ctx"),
    "setup": ("/configurar", "/setup", "/configurar"),
    "doctor": ("/doctor", "/doctor", "/doctor"),
    "update": ("/atualizar", "/update", "/actualizar"),
    "lang": ("/lingua", "/language", "/idioma"),
    "voice": ("/voz", "/voice", "/voz"),
    "clean": ("/limpar", "/clean", "/limpiar"),
    "background": ("/fundo", "/background", "/fondo"),
    "font": ("/fonte", "/font", "/fuente"),
    "dictate": ("/ditar", "/dictate", "/dictar"),
}


def canon(nome: str) -> str:
    """Nome digitado (sem a barra) -> id canonico; desconhecido volta igual."""
    nome = (nome or "").strip().lower()
    for chave, apelidos in ALIASES.items():
        if nome in apelidos:
            return chave
    return nome


def cmd(nome: str) -> str:
    """Como escrever o comando na tela do idioma atual."""
    entrada = CMD.get(nome)
    return entrada[lang_index()] if entrada else nome


# ---------------------------------------------------------------------------
# Comum a varias telas
# ---------------------------------------------------------------------------
COMMON = {
    "common.cancel": ("Nao / cancelar", "No / cancel", "No / cancelar"),
    "common.approve_once": ("Sim, fazer desta vez", "Yes, do it this time",
                            "Si, hacerlo esta vez"),
    "common.approve_conv": ("Sim, e nao perguntar de novo nesta conversa",
                            "Yes, and do not ask again in this conversation",
                            "Si, y no preguntar de nuevo en esta conversacion"),
    "common.approve_always": ("Sim, e sempre permitir isso depois",
                              "Yes, and always allow this later",
                              "Si, y permitirlo siempre despues"),
    "common.nothing_chosen": ("(nada foi escolhido; a conversa continua)",
                              "(nothing was chosen; the conversation continues)",
                              "(no se eligio nada; la conversacion continua)"),
    "common.in_use": (" (em uso)", " (in use)", " (en uso)"),
    "common.keep_current": ("manter atual", "keep current", "mantener actual"),
    "common.yes": ("s", "y", "s"),
    "common.no": ("n", "n", "n"),
}

# ---------------------------------------------------------------------------
# Lista de ajuda (cabecalhos, linhas de comando e explicacoes)
# cada linha: (cmd_pt, cmd_en, cmd_es, desc_pt, desc_en, desc_es)
# ---------------------------------------------------------------------------
HELP_HEADERS = {
    "help.h.quick": ("Atalhos rapidos (nao precisam de permissao):",
                     "Quick shortcuts (no permission needed):",
                     "Atajos rapidos (no necesitan permiso):"),
    "help.h.multiline": ("Escrever em varias linhas (no voce>):",
                         "Writing on several lines (at the you> prompt):",
                         "Escribir en varias lineas (en el tu>):"),
    "help.h.stop": ("Parar e reler:", "Stopping and re-reading:",
                    "Parar y releer:"),
    "help.h.commands": ("Comandos:", "Commands:", "Comandos:"),
    "help.h.lang": ("Idioma / Language / Idioma:", "Idioma / Language / Idioma:",
                    "Idioma / Language / Idioma:"),
    "help.h.falar": ("Falar em vez de digitar (acessibilidade):",
                     "Speaking instead of typing (accessibility):",
                     "Hablar en vez de escribir (accesibilidad):"),
}

HELP_SECTIONS = [
    ("help.h.quick", [
        ("/", "/", "/",
         "tela fixa: menu da pasta atual (escolhe por numero); modo simples: lista",
         "fixed screen: menu of the current folder (pick by number); simple mode: lists",
         "pantalla fija: menu de la carpeta actual (elige por numero); modo simple: lista"),
        ("/ <pasta> ou /ls <pasta>", "/ <folder> or /ls <folder>",
         "/ <carpeta> o /ls <carpeta>",
         "lista uma pasta especifica", "lists a specific folder",
         "lista una carpeta especifica"),
        ("@", "@", "@",
         "tela fixa: menu de arquivos para anexar; modo simples: lista os arquivos",
         "fixed screen: file menu to attach; simple mode: lists the files",
         "pantalla fija: menu de archivos para adjuntar; modo simple: lista los archivos"),
        ("@<arquivo>", "@<file>", "@<archivo>",
         "anexa um arquivo ou uma FOTO (png, jpg...); escrever o caminho da "
         "imagem na mensagem tambem funciona",
         "attaches a file or a PHOTO (png, jpg...); writing the image path in "
         "the message also works",
         "adjunta un archivo o una FOTO (png, jpg...); escribir la ruta de la "
         "imagen en el mensaje tambien funciona"),
    ]),
    ("help.h.multiline", [
        ("Ctrl+J", "Ctrl+J", "Ctrl+J",
         "pula linha sem enviar a mensagem", "new line without sending the message",
         "salta de linea sin enviar el mensaje"),
        ("terminar a linha com \\ e ENTER", "end the line with \\ and ENTER",
         "terminar la linea con \\ y ENTER",
         "continua na linha de baixo (igual shell)",
         "continues on the next line (like a shell)",
         "continua en la linea de abajo (como el shell)"),
        ("Alt+Enter", "Alt+Enter", "Alt+Enter",
         "pula linha quando o terminal deixa (no cmd do Windows nao)",
         "new line when the terminal allows (not in Windows cmd)",
         "salta de linea cuando el terminal lo permite (no en cmd de Windows)"),
    ]),
    ("help.h.stop", [
        ("CTRL+C ou ESC durante a resposta", "CTRL+C or ESC while answering",
         "CTRL+C o ESC durante la respuesta",
         "para de responder na hora (igual ao Hermes)",
         "stops answering right away (like Hermes)",
         "deja de responder al instante (igual que Hermes)"),
        ("digitar ENTER durante a resposta", "press ENTER while answering",
         "presionar ENTER durante la respuesta",
         "avisa o turno em andamento; o modelo le na proxima rodada",
         "warns the current turn; the model reads it on the next round",
         "avisa al turno en curso; el modelo lo lee en la siguiente ronda"),
        ("Roda do mouse ou PageUp/PageDown", "Mouse wheel or PageUp/PageDown",
         "Rueda del raton o PageUp/PageDown",
         "reler o texto que subiu na tela", "re-read text that scrolled up",
         "releer el texto que subio en pantalla"),
        ("CTRL+C com a linha vazia", "CTRL+C with an empty line",
         "CTRL+C con la linea vacia",
         "fecha o TEO", "closes TEO", "cierra el TEO"),
        ("Seta para cima / para baixo", "Up / down arrow",
         "Flecha arriba / abajo",
         "repete o que voce ja digitou (historico guardado)",
         "repeats what you typed before (saved history)",
         "repite lo que ya escribiste (historial guardado)"),
    ]),
    ("help.h.falar", [
        ("F2", "F2", "F2",
         "comeca a ouvir o microfone e poe o texto na linha; para sozinho quando "
         "voce cala (um bip avisa que comecou e outro que parou)",
         "starts listening to the microphone and puts the text on the line; stops "
         "by itself when you go quiet (one beep when it starts, another when it stops)",
         "empieza a escuchar el microfono y pone el texto en la linea; para solo "
         "cuando callas (un bip avisa que empezo y otro que paro)"),
        ("espaco com a linha vazia", "space on an empty line",
         "espacio con la linea vacia",
         "a mesma coisa, na tecla mais facil de achar no teclado",
         "the same thing, on the easiest key to find on the keyboard",
         "lo mismo, en la tecla mas facil de encontrar en el teclado"),
        ("ESC durante a escuta", "ESC while listening", "ESC mientras escucha",
         "para de ouvir na hora, sem enviar nada",
         "stops listening right away, without sending anything",
         "deja de escuchar al instante, sin enviar nada"),
    ]),
    ("help.h.commands", [
        ("/ajuda", "/help", "/ayuda",
         "esta lista", "this list", "esta lista"),
        ("/nov", "/new", "/nuevo",
         "conversa nova (limpa contexto; memoria e skills continuam)",
         "new conversation (clears context; memory and skills stay)",
         "conversacion nueva (limpia el contexto; memoria y skills siguen)"),
        ("/mem <texto>", "/mem <text>", "/mem <texto>",
         "grava uma preferencia sua na memoria permanente",
         "saves a preference of yours in permanent memory",
         "guarda una preferencia tuya en la memoria permanente"),
        ("/modelo", "/model", "/modelo",
         "lista os modelos do servidor; /modelo <nome ou numero> troca (fica salvo)",
         "lists the server models; /model <name or number> switches (saved)",
         "lista los modelos del servidor; /modelo <nombre o numero> cambia (guardado)"),
        ("/provedor", "/provider", "/proveedor",
         "lista os provedores; /provedor <nome ou numero> troca na hora (fica salvo)",
         "lists providers; /provider <name or number> switches now (saved)",
         "lista los proveedores; /proveedor <nombre o numero> cambia ahora (guardado)"),
        ("/pensamento", "/thinking", "/pensamiento",
         "mostra ou esconde o pensamento na tela; avancado (nivel enviado ao "
         "servidor): auto off minimum low medium high xhigh max ultra",
         "shows or hides the thinking on screen; advanced (level sent to the "
         "server): auto off minimum low medium high xhigh max ultra",
         "muestra u oculta el pensamiento en pantalla; avanzado (nivel enviado "
         "al servidor): auto off minimum low medium high xhigh max ultra"),
        ("/palco", "/stage", "/escenario",
         "mostra ou esconde a trilha do pedido durante a resposta (so na tela fixa)",
         "shows or hides the request trail while answering (fixed screen only)",
         "muestra u oculta el recorrido del pedido durante la respuesta (solo pantalla fija)"),
        ("/ctx", "/ctx", "/ctx",
         "medidor do contexto; /ctx <numero> define o limite e fica salvo "
         "(ex.: /ctx 65000; aceita 65k, 65.000, 65 mil)",
         "context meter; /ctx <number> sets the limit and saves it "
         "(e.g. /ctx 65000; accepts 65k)",
         "medidor del contexto; /ctx <numero> fija el limite y lo guarda "
         "(ej.: /ctx 65000; acepta 65k)"),
        ("/configurar", "/setup", "/configurar",
         "conserta ou cria um provedor sem sair do TEO (o mesmo assistente do 'bgh setup')",
         "fixes or creates a provider without leaving TEO (same as 'bgh setup')",
         "arregla o crea un proveedor sin salir del TEO (igual a 'bgh setup')"),
        ("/doctor", "/doctor", "/doctor",
         "diagnostico da conexao e da maquina, na propria tela",
         "connection and machine diagnosis, on the screen itself",
         "diagnostico de la conexion y de la maquina, en la propia pantalla"),
        ("/atualizar", "/update", "/actualizar",
         "confere se ha versao nova no GitHub; se houver, pede sua licenca e instala",
         "checks for a new version on GitHub; if there is one, asks permission and installs",
         "revisa si hay version nueva en GitHub; si hay, pide permiso e instala"),
        ("/skills", "/skills", "/habilidades",
         "lista as skills conhecidas", "lists the known skills",
         "lista las skills conocidas"),
        ("/lingua", "/language", "/idioma",
         "troca o idioma da tela: Portugues, English ou Espanol",
         "switches the screen language: Portugues, English or Espanol",
         "cambia el idioma de la pantalla: Portugues, English o Espanol"),
        ("/voz", "/voice", "/voz",
         "acessibilidade: le as respostas em voz alta com a voz do sistema; "
         "digitar de novo desliga (ESC cala a voz)",
         "accessibility: reads the answers out loud with the system voice; "
         "type it again to turn off (ESC silences the voice)",
         "accesibilidad: lee las respuestas en voz alta con la voz del sistema; "
         "escribirlo otra vez apaga (ESC calla la voz)"),
        ("/limpar", "/clean", "/limpiar",
         "apaga os rascunhos que o TEO guarda na pasta scratch (scripts e textos "
         "da voz) e diz quanto espaco foi liberado",
         "deletes the drafts TEO keeps in the scratch folder (scripts and voice "
         "texts) and reports how much space was freed",
         "borra los borradores que el TEO guarda en la carpeta scratch (scripts y "
         "textos de la voz) y dice cuanto espacio se libero"),
        ("/fundo", "/background", "/fondo",
         "cor de fundo da tela: branco, azul, amarelo, verde, vermelho ou preto "
         "(as letras mudam para continuar legiveis)",
         "screen background color: white, blue, yellow, green, red or black "
         "(the letters change to stay readable)",
         "color de fondo de la pantalla: blanco, azul, amarillo, verde, rojo o "
         "negro (las letras cambian para seguir legibles)"),
        ("/fonte", "/font", "/fuente",
         "tamanho da letra: normal, grande, maior ou enorme",
         "letter size: normal, large, larger or huge",
         "tamano de la letra: normal, grande, mayor o enorme"),
        ("/ditar", "/dictate", "/dictar",
         "acessibilidade: escreva FALANDO - o TEO ouve o microfone, transcreve no "
         "idioma da tela e poe o texto na linha para voce conferir antes do ENTER",
         "accessibility: write by SPEAKING - TEO listens to the microphone, "
         "transcribes in the screen language and puts the text on the line for you "
         "to check before ENTER",
         "accesibilidad: escribe HABLANDO - el TEO escucha el microfono, transcribe "
         "en el idioma de la pantalla y pone el texto en la linea para que lo revises "
         "antes del ENTER"),
        ("/sair", "/exit", "/salir", "encerra", "quits", "cierra"),
    ]),
]

# ---------------------------------------------------------------------------
# Chat (chat_core.py)
# ---------------------------------------------------------------------------
CHAT = {
    "chat.window_title": ("TEO Agent", "TEO Agent", "TEO Agent"),

    "banner.title": (
        "TEO - agente local (comandos seguros rodam direto; perigosos pedem sua licenca)",
        "TEO - local agent (safe commands run directly; dangerous ones ask your permission)",
        "TEO - agente local (los comandos seguros corren directo; los peligrosos piden tu permiso)"),
    "banner.model": ("Modelo: {model} em {base_url} (thinking: {thinking})",
                     "Model: {model} at {base_url} (thinking: {thinking})",
                     "Modelo: {model} en {base_url} (thinking: {thinking})"),
    "banner.resumed": ("Conversa anterior retomada. {new} para comecar do zero.",
                       "Previous conversation resumed. {new} to start from scratch.",
                       "Conversacion anterior retomada. {new} para empezar de cero."),

    "ctx.meter": ("contexto: {pct}% de {budget} chars{tokens} ({messages} mensagens)",
                  "context: {pct}% of {budget} chars{tokens} ({messages} messages)",
                  "contexto: {pct}% de {budget} chars{tokens} ({messages} mensajes)"),
    "ctx.tokens_teto": (" ({marca}{tokens} de {teto} toks)",
                        " ({marca}{tokens} of {teto} toks)",
                        " ({marca}{tokens} de {teto} toks)"),
    "ctx.tokens": (" ({marca}{tokens} toks)", " ({marca}{tokens} toks)",
                   " ({marca}{tokens} toks)"),
    "ctx.extra": (" | teto; o servidor entrega {tokens} tokens",
                  " | cap; the server delivers {tokens} tokens",
                  " | tope; el servidor entrega {tokens} tokens"),
    "ctx.compacted": ("Contexto compactado: as partes antigas viraram um resumo.",
                      "Context compacted: the old parts became a summary.",
                      "Contexto compactado: las partes viejas se volvieron un resumen."),
    "ctx.filling": ("Contexto enchendo; sera compactado na proxima rodada pesada.",
                    "Context filling up; it will be compacted on the next heavy round.",
                    "Contexto llenandose; se compactara en la proxima ronda pesada."),

    "cmd.clean.title": ("Limpar rascunhos do TEO", "Clean TEO scratch files",
                        "Limpiar borradores del TEO"),
    "cmd.clean.ask": ("A pasta de rascunhos tem {n} arquivo(s) ({size}). Apagar tudo?",
                      "The scratch folder has {n} file(s) ({size}). Delete everything?",
                      "La carpeta de borradores tiene {n} archivo(s) ({size}). Borrar todo?"),
    "cmd.clean.yes": ("Sim, apagar", "Yes, delete", "Si, borrar"),
    "cmd.clean.no": ("Nao, deixar como esta", "No, leave it", "No, dejarlo"),
    "cmd.clean.ok": ("Pronto: {n} arquivo(s) apagados, {size} liberados.{nota}",
                     "Done: {n} file(s) deleted, {size} freed.{nota}",
                     "Listo: {n} archivo(s) borrados, {size} liberados.{nota}"),
    "cmd.clean.empty": ("A pasta de rascunhos ja esta vazia.",
                        "The scratch folder is already empty.",
                        "La carpeta de borradores ya esta vacia."),
    "cmd.clean.cancel": ("Nada foi apagado.", "Nothing was deleted.",
                         "No se borro nada."),
    "cmd.clean.nota": (" Ali ficam so rascunhos (scripts do run_python e textos da "
                       "voz): conversa, memoria, skills e configuracao ficam em "
                       "outro lugar e nao sao tocadas.",
                       " Only drafts live there (run_python scripts and voice texts): "
                       "conversation, memory, skills and settings live elsewhere and "
                       "are not touched.",
                       " Ahi quedan solo borradores (scripts de run_python y textos de "
                       "la voz): conversacion, memoria, skills y configuracion estan en "
                       "otro lugar y no se tocan."),

    "cmd.clean.confirm_hint": ("Para apagar de uma vez: {cmd} sim.",
                              "To delete in one go: {cmd} yes.",
                              "Para borrar de una vez: {cmd} si."),
    "cmd.fundo.ask": ("Qual cor? (Enter = {first})", "Which color? (Enter = {first})",
                      "Que color? (Enter = {first})"),
    "cmd.fundo.list": ("Fundo atual: {atual}. Opcoes: {cores}. Use {cmd} <cor>.",
                       "Current background: {atual}. Options: {cores}. Use {cmd} <color>.",
                       "Fondo actual: {atual}. Opciones: {cores}. Usa {cmd} <color>."),
    "cmd.fonte.ask": ("Qual tamanho? (Enter = {first})", "Which size? (Enter = {first})",
                      "Que tamano? (Enter = {first})"),
    "cmd.fonte.list": ("Letra atual: {atual}. Opcoes: {niveis}. Use {cmd} <numero>.",
                       "Current letter: {atual}. Options: {niveis}. Use {cmd} <number>.",
                       "Letra actual: {atual}. Opciones: {niveis}. Usa {cmd} <numero>."),

    "cmd.fundo.title": ("Cor de fundo da tela", "Screen background color",
                        "Color de fondo de la pantalla"),
    "cmd.fundo.now": ("Fundo {cor}. As letras mudaram de cor para continuar legiveis. "
                      "Para voltar ao padrao: {cmd} padrao.",
                      "Background {cor}. The letters changed color to stay readable. "
                      "To go back to normal: {cmd} default.",
                      "Fondo {cor}. Las letras cambiaron de color para seguir legibles. "
                      "Para volver al normal: {cmd} padrao."),
    "cmd.fundo.bad": ("Nao conheco essa cor. {cmd} mostra as opcoes.",
                      "I do not know that color. {cmd} shows the options.",
                      "No conozco ese color. {cmd} muestra las opciones."),
    "cmd.fundo.off": ("O fundo voltou a ser o do seu terminal.",
                      "The background is the terminal's own again.",
                      "El fondo volvio a ser el de tu terminal."),

    "cmd.fonte.title": ("Tamanho da letra", "Letter size", "Tamano de la letra"),
    "cmd.fonte.now_win": ("Letra {nivel} aplicada nesta janela e guardada para as "
                          "proximas aberturas (1 = normal).",
                          "Letter {nivel} applied to this window and saved for the next "
                          "openings (1 = normal).",
                          "Letra {nivel} aplicada en esta ventana y guardada para las "
                          "proximas aperturas (1 = normal)."),
    "cmd.fonte.now_linux": ("Abri uma janela nova do TEO com a letra {nivel}. Pode "
                            "fechar esta: a conversa continua la.",
                            "I opened a new TEO window with the letter {nivel}. You may "
                            "close this one: the conversation goes on there.",
                            "Abri una ventana nueva del TEO con la letra {nivel}. Puedes "
                            "cerrar esta: la conversacion sigue alla."),
    "cmd.fonte.teclas": ("O tamanho da letra e do seu terminal, o TEO nao consegue "
                         "mudar por dentro. No seu terminal: {teclas}.",
                         "The letter size belongs to your terminal; TEO cannot change "
                         "it from inside. In your terminal: {teclas}.",
                         "El tamano de la letra es de tu terminal; el TEO no puede "
                         "cambiarlo por dentro. En tu terminal: {teclas}."),
    "cmd.fonte.bad": ("Escolha 1 (normal), 2 (grande), 3 (maior) ou 4 (enorme). "
                      "{cmd} mostra as opcoes.",
                      "Choose 1 (normal), 2 (large), 3 (larger) or 4 (huge). "
                      "{cmd} shows the options.",
                      "Elige 1 (normal), 2 (grande), 3 (mayor) o 4 (enorme). "
                      "{cmd} muestra las opciones."),

    "cmd.ditar.title": ("Escrever falando", "Write by speaking", "Escribir hablando"),
    "cmd.ditar.ouvindo": ("Pode falar agora: eu paro sozinho quando voce terminar "
                          "(ate 25 segundos).",
                          "Speak now: I stop by myself when you finish (up to 25 "
                          "seconds).",
                          "Habla ahora: paro solo cuando termines (hasta 25 segundos)."),
    "cmd.ditar.entendi": ("Eu entendi: {texto}", "I heard: {texto}",
                          "Entendi: {texto}"),
    "cmd.ditar.revisar": ("O texto esta na linha de baixo: confira, corrija se quiser "
                          "e aperte ENTER para enviar.",
                          "The text is on the line below: check it, fix it if you "
                          "want and press ENTER to send.",
                          "El texto esta en la linea de abajo: revisalo, corregilo si "
                          "quieres y aprieta ENTER para enviar."),
    "cmd.ditar.revisar_simples": ("Se estiver certo, digite ENTER na proxima linha "
                                  "para enviar.",
                                  "If it is right, press ENTER on the next line to send.",
                                  "Si esta bien, presiona ENTER en la linea siguiente "
                                  "para enviar."),
    "cmd.ditar.dirigir": ("Diga o que voce quer e eu escrevo (ex.: 'pergunte ao "
                          "modelo...').",
                          "Say what you want and I write it (e.g. 'ask the model...').",
                          "Di lo que quieres y yo lo escribo (ej.: 'pregunta al modelo...')."),
    "cmd.ditar.parado": ("Parei de ouvir. Nada foi enviado.",
                        "I stopped listening. Nothing was sent.",
                        "Deje de escuchar. No se envio nada."),
    "cmd.ditar.vazio": ("Nao entendi nada. Fale mais perto do microfone, sem pressa, "
                        "e tente de novo com {cmd}.",
                        "I did not understand anything. Speak closer to the microphone, "
                        "slowly, and try again with {cmd}.",
                        "No entendi nada. Habla mas cerca del microfono, sin apuro, y "
                        "prueba otra vez con {cmd}."),
    "cmd.ditar.sem_motor": ("O motor de ditado nao esta instalado nesta maquina "
                            "(pacote 'vosk'). Rode 'bgh setup' ou "
                            "'pip install -r requirements.txt' e tente de novo.",
                            "The dictation engine is not installed on this machine "
                            "(package 'vosk'). Run 'bgh setup' or "
                            "'pip install -r requirements.txt' and try again.",
                            "El motor de dictado no esta instalado en esta maquina "
                            "(paquete 'vosk'). Corre 'bgh setup' o "
                            "'pip install -r requirements.txt' y prueba otra vez."),
    "cmd.ditar.baixar_ask": ("Para ditar em {idioma} eu preciso baixar o modelo do "
                             "idioma uma vez ({mb} MB). Depois funciona sem internet. "
                             "Baixar agora?",
                             "To dictate in {idioma} I need to download the language "
                             "model once ({mb} MB). After that it works offline. "
                             "Download now?",
                             "Para dictar en {idioma} necesito bajar el modelo del "
                             "idioma una vez ({mb} MB). Despues funciona sin internet. "
                             "Bajar ahora?"),
    "cmd.ditar.baixar_hint": ("Para baixar o modelo de {idioma} uma vez: {cmd} baixar.",
                              "To download the {idioma} model once: {cmd} baixar.",
                              "Para bajar el modelo de {idioma} una vez: {cmd} baixar."),
    "cmd.ditar.baixando": ("Baixando o modelo de {idioma}... {pct}%",
                           "Downloading the {idioma} model... {pct}%",
                           "Bajando el modelo de {idioma}... {pct}%"),
    "cmd.ditar.baixou": ("Modelo de {idioma} pronto ({tam}). O som nao sai do seu "
                         "computador: quem entende a fala e o proprio TEO.",
                         "{idioma} model ready ({tam}). The sound never leaves your "
                         "computer: TEO itself understands the speech.",
                         "Modelo de {idioma} listo ({tam}). El sonido no sale de tu "
                         "computadora: el propio TEO entiende la voz."),
    "cmd.ditar.baixou_falhou": ("Nao consegui baixar o modelo ({motivo}). Confira a "
                                "internet e tente de novo com {cmd}.",
                                "I could not download the model ({motivo}). Check your "
                                "internet and try again with {cmd}.",
                                "No pude bajar el modelo ({motivo}). Revisa internet y "
                                "prueba otra vez con {cmd}."),
    "cmd.ditar.confirmar": ("Enviar esse texto ao modelo?", "Send this text to the model?",
                            "Enviar ese texto al modelo?"),
    "cmd.ditar.nao": ("Deixei o texto so na tela.", "I left the text on the screen only.",
                      "Deje el texto solo en la pantalla."),

    "cor.padrao": ("do terminal", "of the terminal", "del terminal"),
    "cor.branco": ("branco", "white", "blanco"),
    "cor.amarelo": ("amarelo", "yellow", "amarillo"),
    "cor.verde": ("verde", "green", "verde"),
    "cor.azul": ("azul", "blue", "azul"),
    "cor.vermelho": ("vermelho", "red", "rojo"),
    "cor.preto": ("preto", "black", "negro"),

    "fonte.normal": ("normal", "normal", "normal"),
    "fonte.grande": ("grande", "large", "grande"),
    "fonte.maior": ("maior", "larger", "mayor"),
    "fonte.enorme": ("enorme", "huge", "enorme"),

    "cmd.voz.on": ("Voz LIGADA: leio cada resposta em voz alta com a voz do sistema "
                   "({voz}). Para calar a leitura: ESC. Para desligar de vez: {cmd}.",
                   "Voice ON: I read every answer out loud with the system voice "
                   "({voz}). To silence a reading: ESC. To turn it off: {cmd}.",
                   "Voz ACTIVADA: leo cada respuesta en voz alta con la voz del sistema "
                   "({voz}). Para callar la lectura: ESC. Para apagar: {cmd}."),
    "cmd.voz.off": ("Voz desligada: as respostas ficam so na tela.",
                    "Voice off: answers stay on the screen only.",
                    "Voz apagada: las respuestas quedan solo en la pantalla."),
    "cmd.voz.status": ("Voz {onoff}. {cmd} liga ou desliga.",
                       "Voice {onoff}. {cmd} turns it on or off.",
                       "Voz {onoff}. {cmd} la activa o la apaga."),
    "cmd.voz.bad": ("Use {cmd} para ligar/desligar a voz (ou {cmd} ligar / desligar).",
                    "Use {cmd} to turn the voice on/off (or {cmd} on / off).",
                    "Usa {cmd} para activar/apagar la voz (o {cmd} activar / apagar)."),
    "cmd.voz.no_backend": ("Nao encontrei a voz do sistema nesta maquina, entao nao "
                           "consigo ler em voz alta (Linux: spd-say ou espeak-ng; "
                           "Windows: PowerShell; Mac: say). A conversa continua normal.",
                           "I could not find the system voice on this machine, so I cannot "
                           "read out loud (Linux: spd-say or espeak-ng; Windows: "
                           "PowerShell; Mac: say). The conversation goes on normally.",
                           "No encontre la voz del sistema en esta maquina, asi que no puedo "
                           "leer en voz alta (Linux: spd-say o espeak-ng; Windows: "
                           "PowerShell; Mac: say). La conversacion sigue normal."),
    "cmd.voz.hello": ("Voz ligada. Eu vou ler as respostas em voz alta. Para "
                      "escrever falando em vez de digitar, aperte F2.",
                      "Voice on. I will read the answers out loud. To write by "
                      "speaking instead of typing, press F2.",
                      "Voz activada. Voy a leer las respuestas en voz alta. Para "
                      "escribir hablando en vez de teclear, presiona F2."),
    "voz.truncada": ("(resposta longa: a voz le so o comeco; o resto esta na tela)",
                     "(long answer: the voice reads only the beginning; the rest is on the screen)",
                     "(respuesta larga: la voz lee solo el comienzo; el resto esta en pantalla)"),

    "cmd.unknown": ("Comando desconhecido. {help} mostra a lista.",
                    "Unknown command. {help} shows the list.",
                    "Comando desconocido. {help} muestra la lista."),
    "cmd.new.done": ("Conversa zerada (memoria e skills preservadas).",
                     "Conversation cleared (memory and skills kept).",
                     "Conversacion reiniciada (memoria y skills conservadas)."),
    "cmd.skills.empty": ("(nenhuma skill ainda)", "(no skills yet)",
                         "(ninguna skill todavia)"),
    "cmd.model.no_list": ("O servidor nao publica lista de modelos.",
                          "The server does not publish a model list.",
                          "El servidor no publica lista de modelos."),
    "cmd.model.off_list": ("Numero fora da lista. Digite {model} para ver.",
                           "Number out of the list. Type {model} to see it.",
                           "Numero fuera de la lista. Escribe {model} para verla."),
    "cmd.model.now": ("Modelo agora: {model} (salvo no config)",
                      "Model now: {model} (saved in the config)",
                      "Modelo ahora: {model} (guardado en el config)"),
    "cmd.model.not_in_list": (
        "  (modelo em uso: {model}; nao apareceu na lista do servidor - escolher "
        "um numero acima alinhara o nome)",
        "  (model in use: {model}; it did not appear in the server list - picking "
        "a number above will align the name)",
        "  (modelo en uso: {model}; no aparecio en la lista del servidor - elegir "
        "un numero arriba alineara el nombre)"),
    "cmd.model.no_answer": (
        "O servidor nao respondeu a lista de modelos agora. Tente de novo em "
        "instantes (o detalhe tecnico foi guardado no erro.log).",
        "The server did not answer the model list now. Try again in a moment "
        "(the technical detail was saved in erro.log).",
        "El servidor no respondio la lista de modelos ahora. Intenta de nuevo en "
        "un momento (el detalle tecnico quedo en erro.log)."),
    "cmd.model.bad_answer": (
        "O servidor mandou uma lista que o TEO nao conseguiu ler. Rode {doctor} "
        "para ver a conexao (detalhe no erro.log).",
        "The server sent a list TEO could not read. Run {doctor} to check the "
        "connection (detail in erro.log).",
        "El servidor envio una lista que el TEO no pudo leer. Ejecuta {doctor} "
        "para ver la conexion (detalle en erro.log)."),
    "cmd.provider.none": ("(nenhum provedor cadastrado ainda)",
                          "(no provider registered yet)",
                          "(ningun proveedor registrado todavia)"),
    "cmd.provider.row": ("  {n}. {name}{marca} - {model} em {base_url}",
                         "  {n}. {name}{marca} - {model} at {base_url}",
                         "  {n}. {name}{marca} - {model} en {base_url}"),
    "cmd.provider.now": (
        "Provedor agora: {name} - {model} em {base_url} (salvo; a conversa continua)",
        "Provider now: {name} - {model} at {base_url} (saved; the conversation goes on)",
        "Proveedor ahora: {name} - {model} en {base_url} (guardado; la conversacion sigue)"),
    "cmd.provider.not_found": (
        "Provedor nao encontrado. Digite {provider} sozinho para ver a lista.",
        "Provider not found. Type {provider} alone to see the list.",
        "Proveedor no encontrado. Escribe {provider} solo para ver la lista."),

    "cmd.thinking.on": ("Pensamento na tela: LIGADO (salvo)",
                        "Thinking on screen: ON (saved)",
                        "Pensamiento en pantalla: ACTIVADO (guardado)"),
    "cmd.thinking.off": (
        "Pensamento na tela: DESLIGADO (salvo); o modelo segue trabalhando por "
        "dentro e a resposta chega igual",
        "Thinking on screen: OFF (saved); the model keeps working inside and the "
        "answer arrives the same",
        "Pensamiento en pantalla: DESACTIVADO (guardado); el modelo sigue "
        "trabajando por dentro y la respuesta llega igual"),
    "cmd.thinking.level": (
        "Nivel de raciocinio enviado ao servidor: {level} (salvo). Obs.: provedores "
        "hospedados podem ignorar o nivel pedido.",
        "Reasoning level sent to the server: {level} (saved). Note: hosted "
        "providers may ignore the requested level.",
        "Nivel de razonamiento enviado al servidor: {level} (guardado). Nota: los "
        "proveedores hospedados pueden ignorar el nivel pedido."),
    "cmd.thinking.status": (
        "Pensamento na tela: {onoff} | nivel enviado ao servidor: {level}. "
        "Uso: {cmd} liga | desliga | auto | off | minimum | low | medium | high | "
        "xhigh | max | ultra",
        "Thinking on screen: {onoff} | level sent to the server: {level}. "
        "Use: {cmd} on | off | auto | minimum | low | medium | high | "
        "xhigh | max | ultra",
        "Pensamiento en pantalla: {onoff} | nivel enviado al servidor: {level}. "
        "Uso: {cmd} activar | desactivar | auto | off | minimum | low | medium | "
        "high | xhigh | max | ultra"),
    "cmd.thinking.bad": (
        "Nao entendi. Use {cmd} liga ou {cmd} desliga (tela); avancado (servidor): "
        "auto off minimum low medium high xhigh max ultra",
        "Not understood. Use {cmd} on or {cmd} off (screen); advanced (server): "
        "auto off minimum low medium high xhigh max ultra",
        "No entendi. Usa {cmd} activar o {cmd} desactivar (pantalla); avanzado "
        "(servidor): auto off minimum low medium high xhigh max ultra"),
    "cmd.stage.on": ("Palco: LIGADO (a trilha do pedido aparece durante a resposta).",
                     "Stage: ON (the request trail appears while answering).",
                     "Escenario: ACTIVADO (el recorrido del pedido aparece durante la respuesta)."),
    "cmd.stage.off": ("Palco: DESLIGADO (tela como antes; salvo)",
                      "Stage: OFF (screen as before; saved)",
                      "Escenario: DESACTIVADO (pantalla como antes; guardado)"),
    "cmd.stage.status": ("Palco: {onoff}. Uso: {cmd} liga | {cmd} desliga",
                         "Stage: {onoff}. Use: {cmd} on | {cmd} off",
                         "Escenario: {onoff}. Uso: {cmd} activar | {cmd} desactivar"),
    "cmd.stage.bad": ("Nao entendi. Use {cmd} liga ou {cmd} desliga",
                      "Not understood. Use {cmd} on or {cmd} off",
                      "No entendi. Usa {cmd} activar o {cmd} desactivar"),
    "cmd.ctx.bad": (
        "Esse numero nao vale. Uso: {ctx} 65000 (aceita 65k, 65.000, 65 mil). "
        "Intervalo: 8000 a 1000000.",
        "That number is not valid. Use: {ctx} 65000 (accepts 65k). "
        "Range: 8000 to 1000000.",
        "Ese numero no vale. Uso: {ctx} 65000 (acepta 65k). "
        "Rango: 8000 a 1000000."),
    "cmd.ctx.set": (
        "Orcamento de contexto ajustado para {n} caracteres (salvo). Vale ja na "
        "proxima resposta.",
        "Context budget set to {n} characters (saved). It applies on the next answer.",
        "Presupuesto de contexto ajustado a {n} caracteres (guardado). Vale ya en "
        "la proxima respuesta."),
    "cmd.setup.no_menu": (
        "Este modo nao consegue perguntar na tela; rode 'bgh setup' na janela de comando.",
        "This mode cannot ask on the screen; run 'bgh setup' in the command window.",
        "Este modo no puede preguntar en pantalla; ejecuta 'bgh setup' en la ventana de comandos."),
    "cmd.setup.connected": (
        "Conexao agora: {model} @ {base_url}. Ja vale na proxima mensagem.",
        "Connection now: {model} @ {base_url}. It applies on the next message.",
        "Conexion ahora: {model} @ {base_url}. Vale ya en el proximo mensaje."),

    "cmd.update.check_fail": ("Nao consegui verificar a versao nova: {err}",
                              "I could not check for a new version: {err}",
                              "No pude verificar la version nueva: {err}"),
    "cmd.update.uptodate": (
        "O TEO ja esta atualizado (versao {version}). Pode continuar usando.",
        "TEO is already up to date (version {version}). Keep using it.",
        "El TEO ya esta actualizado (version {version}). Puedes seguir usandolo."),
    "cmd.update.no_pip": (
        "Existe versao nova ({version}). Como o TEO foi aberto pelo icone/arquivo "
        "executavel, baixe e rode o INSTALAR_TEO.bat outra vez (dois cliques) - ele "
        "faz a atualizacao inteira.",
        "A new version exists ({version}). Since TEO was opened from the icon/executable, "
        "download and run INSTALAR_TEO.bat again (two clicks) - it does the whole update.",
        "Existe version nueva ({version}). Como el TEO se abrio desde el icono/ejecutable, "
        "descarga y ejecuta INSTALAR_TEO.bat otra vez (dos clics) - hace toda la actualizacion."),
    "cmd.update.title": ("ATUALIZAR O TEO", "UPDATE TEO", "ACTUALIZAR EL TEO"),
    "cmd.update.ask": (
        "Encontrei a versao {new} (a sua e a {cur}). Atualizar agora?",
        "I found version {new} (yours is {cur}). Update now?",
        "Encontre la version {new} (la tuya es la {cur}). Actualizar ahora?"),
    "cmd.update.yes": ("Sim, atualizar", "Yes, update", "Si, actualizar"),
    "cmd.update.no": ("Nao, deixar como esta", "No, keep it as it is",
                      "No, dejarlo como esta"),
    "cmd.update.cancelled": ("Atualizacao cancelada (nada mudou).",
                             "Update cancelled (nothing changed).",
                             "Actualizacion cancelada (nada cambio)."),
    "cmd.update.downloading": ("Baixando e instalando a versao {version}...",
                               "Downloading and installing version {version}...",
                               "Descargando e instalando la version {version}..."),
    "cmd.update.done": (
        "Atualizado para {version}. Feche ({exit}) e abra o TEO de novo para o "
        "codigo novo comecar a valer.",
        "Updated to {version}. Close ({exit}) and open TEO again so the new code "
        "takes effect.",
        "Actualizado a {version}. Cierra ({exit}) y abre el TEO otra vez para que "
        "el codigo nuevo empiece a valer."),
    "cmd.update.failed": ("A atualizacao nao completou: {err}",
                          "The update did not complete: {err}",
                          "La actualizacion no se completo: {err}"),
    "cmd.update.fallback": (
        "Alternativa que funciona em qualquer maquina: baixar e rodar o "
        "INSTALAR_TEO.bat da pagina de downloads do TEO.",
        "Alternative that works on any machine: download and run INSTALAR_TEO.bat "
        "from the TEO downloads page.",
        "Alternativa que funciona en cualquier maquina: descargar y ejecutar "
        "INSTALAR_TEO.bat de la pagina de descargas del TEO."),

    "lang.title": ("IDIOMA DO TEO", "TEO LANGUAGE", "IDIOMA DEL TEO"),
    "lang.ask": ("Qual idioma voce quer na tela? (Enter = {first})",
                 "Which language do you want on screen? (Enter = {first})",
                 "Que idioma quieres en pantalla? (Enter = {first})"),
    "lang.status": ("Idioma: {name}. Uso: {cmd} 1 | 2 | 3 (ou {cmd} pt | en | es)",
                    "Language: {name}. Use: {cmd} 1 | 2 | 3 (or {cmd} pt | en | es)",
                    "Idioma: {name}. Uso: {cmd} 1 | 2 | 3 (o {cmd} pt | en | es)"),
    "lang.changed": (
        "Idioma agora: {name} (salvo). A tela toda passa a usar este idioma.",
        "Language now: {name} (saved). The whole screen uses this language.",
        "Idioma ahora: {name} (guardado). Toda la pantalla usa este idioma."),
    "lang.bad": (
        "Nao entendi esse idioma. Escolha 1 (Portugues), 2 (English) ou 3 (Espanol).",
        "I did not understand that language. Choose 1 (Portugues), 2 (English) or 3 (Espanol).",
        "No entendi ese idioma. Elige 1 (Portugues), 2 (English) o 3 (Espanol)."),

    "ask.thinking.title": ("NIVEL DE PENSAMENTO DO MODELO",
                           "MODEL THINKING LEVEL", "NIVEL DE PENSAMIENTO DEL MODELO"),
    "ask.thinking.label": (
        "O quanto o modelo deve 'pensar' antes de responder? (Enter = manter atual)",
        "How much should the model 'think' before answering? (Enter = keep current)",
        "Cuanto debe 'pensar' el modelo antes de responder? (Enter = mantener actual)"),
    "ask.thinking.done": ("Pensamento: {level} (salvo)",
                          "Thinking: {level} (saved)",
                          "Pensamiento: {level} (guardado)"),

    "menu.enter_folder": ("entrar em: {nome}", "enter: {nome}", "entrar en: {nome}"),
    "menu.attach": ("anexar: {nome}", "attach: {nome}", "adjuntar: {nome}"),
    "menu.view": ("ver: {nome}", "view: {nome}", "ver: {nome}"),
    "menu.cancel": ("cancelar (voltar para a conversa)",
                    "cancel (back to the conversation)",
                    "cancelar (volver a la conversacion)"),
    "menu.up": (".. (voltar uma pasta)", ".. (up one folder)", ".. (subir una carpeta)"),
    "menu.more": ("mais itens (mais {n})", "more items ({n} more)", "mas items ({n} mas)"),
    "menu.back_start": ("voltar ao inicio da lista", "back to the start of the list",
                        "volver al inicio de la lista"),
    "menu.title_attach": ("ESCOLHER ARQUIVO PARA ANEXAR", "CHOOSE A FILE TO ATTACH",
                          "ELEGIR ARCHIVO PARA ADJUNTAR"),
    "menu.title_open": ("ABRIR PASTA OU ARQUIVO", "OPEN A FOLDER OR FILE",
                        "ABRIR CARPETA O ARCHIVO"),
    "menu.label": ("Pasta atual: {atual}\nDigite o numero e ENTER. O numero 1 cancela.",
                   "Current folder: {atual}\nType the number and press ENTER. Number 1 cancels.",
                   "Carpeta actual: {atual}\nEscribe el numero y ENTER. El numero 1 cancela."),
    "menu.entering": ("entrando em: {alvo}", "entering: {alvo}", "entrando en: {alvo}"),

    "attach.image_ok": (
        "Imagem anexada: {target} ({size}). Agora faca sua pergunta sobre ela.",
        "Image attached: {target} ({size}). Now ask your question about it.",
        "Imagen adjuntada: {target} ({size}). Ahora haz tu pregunta sobre ella."),
    "attach.read_fail": (
        "Nao consegui ler {target} (o arquivo pode estar aberto em outro programa "
        "ou protegido). O detalhe tecnico ficou no erro.log.",
        "I could not read {target} (the file may be open in another program or "
        "protected). The technical detail is in erro.log.",
        "No pude leer {target} (el archivo puede estar abierto en otro programa o "
        "protegido). El detalle tecnico quedo en erro.log."),
    "attach.truncated": (" (mostrando o comeco do arquivo)", " (showing the start of the file)",
                         " (mostrando el comienzo del archivo)"),
    "attach.file_ok": (
        "Arquivo anexado: {target} ({size}){cortado}. Agora digite sua pergunta sobre ele.",
        "File attached: {target} ({size}){cortado}. Now type your question about it.",
        "Archivo adjuntado: {target} ({size}){cortado}. Ahora escribe tu pregunta sobre el."),
    "attach.not_found": ("Nao encontrei esse arquivo: {target}",
                         "I could not find that file: {target}",
                         "No encontre ese archivo: {target}"),
    "listing.file": ("arquivo: {path} ({size})", "file: {path} ({size})",
                     "archivo: {path} ({size})"),
    "listing.hint": ("(para mandar o conteudo ao TEO, digite @ e escolha o arquivo no menu)",
                     "(to send the content to TEO, type @ and choose the file in the menu)",
                     "(para enviar el contenido al TEO, escribe @ y elige el archivo en el menu)"),

    "turn.rate_hint": ("Dica: {provider} mostra os outros provedores cadastrados.",
                       "Tip: {provider} shows the other registered providers.",
                       "Consejo: {provider} muestra los otros proveedores registrados."),
    "turn.err_hint": (
        "Dica: digite {setup} aqui mesmo para conferir URL e chave (ou {doctor} para "
        "o diagnostico completo).",
        "Tip: type {setup} right here to check URL and key (or {doctor} for the full "
        "diagnosis).",
        "Consejo: escribe {setup} aqui mismo para revisar URL y clave (o {doctor} para "
        "el diagnostico completo)."),
    "turn.crash": (
        "Algo deu errado no TEO durante a resposta. A conversa continua; o detalhe "
        "tecnico foi guardado no arquivo erro.log da pasta .bgh.",
        "Something went wrong in TEO during the answer. The conversation continues; "
        "the technical detail was saved in erro.log inside the .bgh folder.",
        "Algo salio mal en el TEO durante la respuesta. La conversacion continua; el "
        "detalle tecnico quedo en el archivo erro.log de la carpeta .bgh."),
    "turn.sep.thinking": (
        "pensamento do modelo (raciocinio; pode ignorar e ir direto para a resposta)",
        "model thinking (reasoning; you may ignore it and go straight to the answer)",
        "pensamiento del modelo (razonamiento; puedes ignorarlo e ir directo a la respuesta)"),
    "turn.sep.answer": ("resposta", "answer", "respuesta"),
    "turn.length_thinking": (
        "O modelo gastou o limite de saida pensando e nao sobrou texto para a "
        "resposta. Mande a pergunta de novo, use {thinking} low ou aumente "
        "max_tokens no config.json.",
        "The model spent the output limit thinking and no text was left for the "
        "answer. Send the question again, use {thinking} low or raise max_tokens "
        "in config.json.",
        "El modelo gasto el limite de salida pensando y no quedo texto para la "
        "respuesta. Manda la pregunta otra vez, usa {thinking} low o aumenta "
        "max_tokens en config.json."),
    "turn.empty": (
        "O modelo terminou sem texto de resposta. Mande a pergunta de novo; se "
        "repetir, use {thinking} low.",
        "The model finished without answer text. Send the question again; if it "
        "repeats, use {thinking} low.",
        "El modelo termino sin texto de respuesta. Manda la pregunta otra vez; si "
        "se repite, usa {thinking} low."),
    "turn.cut": (
        "(a resposta foi cortada pelo limite de saida; diga 'continue' que eu sigo "
        "de onde parei)",
        "(the answer was cut by the output limit; say 'continue' and I go on from "
        "where I stopped)",
        "(la respuesta se corto por el limite de salida; di 'continua' y sigo "
        "desde donde pare)"),
    "turn.dropped": (
        "({n} mensagem(s) digitadas durante o turno parado nao foram enviadas; "
        "digite de novo quando quiser)",
        "({n} message(s) typed during the stopped turn were not sent; type them "
        "again when you want)",
        "({n} mensaje(s) escritos durante el turno detenido no se enviaron; "
        "escribelos otra vez cuando quieras)"),
    "turn.echo": ("voce> {texto}", "you> {texto}", "tu> {texto}"),
    "turn.image_seen": (
        "Vi uma imagem na sua mensagem: {nome}. Vou mandar para o modelo olhar{extra}.",
        "I saw an image in your message: {nome}. I will send it for the model to look{extra}.",
        "Vi una imagen en tu mensaje: {nome}. La voy a enviar para que el modelo la vea{extra}."),
    "turn.image_more": (
        " (voce citou {n} imagens; por enquanto eu olho a primeira)",
        " (you mentioned {n} images; for now I look at the first one)",
        " (mencionaste {n} imagenes; por ahora miro la primera)"),

    "approval.header": ("== O TEO precisa da sua licenca ==",
                        "== TEO needs your permission ==",
                        "== El TEO necesita tu permiso =="),
    "approval.question": ("O que voce quer fazer?", "What do you want to do?",
                          "Que quieres hacer?"),
    "approval.prompt_deny": ("  Digite o numero (se so Enter, vale {n}): ",
                             "  Type the number (Enter alone means {n}): ",
                             "  Escribe el numero (solo Enter vale {n}): "),
    "approval.prompt_choice": ("  Digite o numero (Enter = {first}): ",
                               "  Type the number (Enter = {first}): ",
                               "  Escribe el numero (Enter = {first}): "),
    "sink.prompt": ("voce> ", "you> ", "tu> "),

    "onoff.on": ("ligado", "on", "activado"),
    "onoff.off": ("desligado", "off", "desactivado"),

    "state.on": ("LIGADO", "ON", "ACTIVADO"),
    "state.off": ("DESLIGADO", "OFF", "DESACTIVADO"),
    "turn.stopped": ("(parei a resposta, como voce pediu)",
                     "(I stopped the answer, as you asked)",
                     "(pare la respuesta, como pediste)"),
}

# ---------------------------------------------------------------------------
# Agente (agent.py): avisos de tela e instrucoes que vao ao modelo
# ---------------------------------------------------------------------------
AGENT = {
    "agent.vision_blocked": (
        "Este modelo ja recusou imagem antes, entao nao vou mandar a foto. Para ver "
        "imagens, escolha um modelo com visao ({model}) - ou me peca para ler por OCR.",
        "This model already refused an image before, so I will not send the photo. To "
        "see images, pick a model with vision ({model}) - or ask me to read it by OCR.",
        "Este modelo ya rechazo una imagen antes, asi que no voy a enviar la foto. Para "
        "ver imagenes, elige un modelo con vision ({model}) - o pideme leer por OCR."),
    "agent.image_fail": ("nao consegui preparar a imagem; seguindo so com o texto.",
                         "I could not prepare the image; going on with text only.",
                         "no pude preparar la imagen; sigo solo con el texto."),
    "agent.overflow": (
        "O servidor recusou o tamanho do contexto; vou compactar a conversa e tentar de novo.",
        "The server refused the context size; I will compact the conversation and try again.",
        "El servidor rechazo el tamano del contexto; voy a compactar la conversacion e intentar de nuevo."),
    "agent.overflow_still": (
        " Mesmo depois de compactar, o pedido nao coube no servidor. Reduza o limite "
        "aqui na tela: {ctx} 60000",
        " Even after compacting, the request did not fit the server. Lower the limit "
        "here on screen: {ctx} 60000",
        " Incluso despues de compactar, el pedido no cupo en el servidor. Baja el limite "
        "aqui en pantalla: {ctx} 60000"),
    "agent.vision_refused": (
        "O modelo deste provedor nao le imagem; vou seguir sem a foto. Para ler imagens, "
        "escolha um modelo com visao ({model}) - ou me peca para ler por OCR, que eu "
        "instalo uma biblioteca.",
        "This provider's model does not read images; I will go on without the photo. To "
        "read images, pick a model with vision ({model}) - or ask me to read it by OCR "
        "and I will install a library.",
        "El modelo de este proveedor no lee imagenes; sigo sin la foto. Para leer "
        "imagenes, elige un modelo con vision ({model}) - o pideme leer por OCR y "
        "instalo una biblioteca."),
    "agent.tool_stopped": ("BLOQUEADO: o usuario mandou parar esta resposta.",
                           "BLOCKED: the user asked to stop this answer.",
                           "BLOQUEADO: el usuario pidio parar esta respuesta."),
    "agent.loop": (
        "LOOP DETECTADO: a chamada IDENTICA a '{nome}' ja foi repetida {n} vezes e nao "
        "vai executar de novo. Mude argumentos, caminho ou estrategia; se nao houver "
        "saida, explique o obstaculo ao usuario.",
        "LOOP DETECTED: the IDENTICAL call to '{nome}' was already repeated {n} times "
        "and will not run again. Change arguments, path or strategy; if there is no way "
        "out, explain the obstacle to the user.",
        "BUCLE DETECTADO: la llamada IDENTICA a '{nome}' ya se repitio {n} veces y no se "
        "ejecutara otra vez. Cambia argumentos, ruta o estrategia; si no hay salida, "
        "explica el obstaculo al usuario."),
    "agent.fail_note": ("5 ferramentas falharam em sequencia; vou fechar este turno com o "
                        "que ja tenho.",
                        "5 tools failed in a row; I will close this turn with what I have.",
                        "5 herramientas fallaron en secuencia; cierro este turno con lo que ya tengo."),
    "agent.close_fail": (
        "(5 ferramentas falharam em sequencia. Pare de tentar variantes do mesmo caminho "
        "e responda {lang} ao usuario: o que foi tentado, o que travou e o que ele pode "
        "fazer.)",
        "(5 tools failed in a row. Stop trying variants of the same path and answer "
        "{lang} to the user: what was tried, what got stuck and what he can do.)",
        "(5 herramientas fallaron en secuencia. Deja de probar variantes del mismo camino "
        "y responde {lang} al usuario: que se intento, que se trabo y que puede hacer.)"),
    "agent.extend_note": (
        "Ja usei {limite} ferramentas neste pedido; vou continuar por mais {extra} "
        "(CTRL+C ou ESC para parar).",
        "I already used {limite} tools in this request; I will go on for {extra} more "
        "(CTRL+C or ESC to stop).",
        "Ya use {limite} herramientas en este pedido; sigo por {extra} mas "
        "(CTRL+C o ESC para parar)."),
    "agent.max_note": ("Parei em {limite} ferramentas para nao gastar demais; vou "
                       "responder com o que ja coletei.",
                       "I stopped at {limite} tools to avoid overspending; I will answer "
                       "with what I already collected.",
                       "Pare en {limite} herramientas para no gastar de mas; respondo "
                       "con lo que ya recogi."),
    "agent.close_teto": (
        "(voce chegou ao teto de {limite} ferramentas deste turno. Responda {lang} com o "
        "que ja coletou, sem prometer acao futura, e termine a resposta dizendo ao "
        "usuario que ele pode escrever 'continue' para voce seguir de onde parou.)",
        "(you reached the cap of {limite} tools in this turn. Answer {lang} with what you "
        "already collected, do not promise future action, and end the answer telling the "
        "user he can write 'continue' for you to go on from where you stopped.)",
        "(llegaste al tope de {limite} herramientas de este turno. Responde {lang} con lo "
        "que ya recogiste, sin prometer accion futura, y termina la respuesta diciendo al "
        "usuario que puede escribir 'continua' para que sigas desde donde paraste.)"),
    "agent.round_note": ("Limite de ferramentas deste turno atingido; vou responder com o "
                         "que ja coletei.",
                         "Tool limit for this turn reached; I will answer with what I "
                         "already collected.",
                         "Limite de herramientas de este turno alcanzado; respondo con lo "
                         "que ya recogi."),
    "agent.close_round": (
        "(limite de ferramentas deste turno atingido. Responda {lang} usando apenas o que "
        "ja foi coletado; nao prometa acao futura, feche o assunto agora.)",
        "(tool limit for this turn reached. Answer {lang} using only what was already "
        "collected; do not promise future action, close the subject now.)",
        "(limite de herramientas de este turno alcanzado. Responde {lang} usando solo lo "
        "que ya se recogio; no prometas accion futura, cierra el asunto ahora.)"),
    "agent.steer_wrap": ("(mensagem do usuario durante o processamento): {texto}",
                         "(user message during processing): {texto}",
                         "(mensaje del usuario durante el procesamiento): {texto}"),
    "agent.steer_note": ("{n} mensagem(s) recebida(s) no meio do turno; entregue(s) ao "
                         "modelo agora.",
                         "{n} message(s) received in the middle of the turn; delivered to "
                         "the model now.",
                         "{n} mensaje(s) recibidos en medio del turno; entregados al "
                         "modelo ahora."),
    "agent.compacting": ("Compactando a conversa em resumo (o resumo custa uma espera "
                         "extra)...",
                         "Compacting the conversation into a summary (the summary costs an "
                         "extra wait)...",
                         "Compactando la conversacion en un resumen (el resumen cuesta una "
                         "espera extra)..."),
    "agent.summary_fallback": ("(partes antigas da conversa foram removidas por limite de "
                               "contexto)",
                               "(old parts of the conversation were removed by the context "
                               "limit)",
                               "(las partes viejas de la conversacion se quitaron por el "
                               "limite de contexto)"),
    "agent.summary_header": ("RESUMO DA CONVERSA ANTERIOR:\n",
                             "SUMMARY OF THE PREVIOUS CONVERSATION:\n",
                             "RESUMEN DE LA CONVERSACION ANTERIOR:\n"),
    "agent.in_lang": ("em portugues", "in English", "en espanol"),
}

# ---------------------------------------------------------------------------
# Portao de licenca (approvals.py): rotulo da regra e frase da pergunta
# ---------------------------------------------------------------------------
GATE = {
    "gate.hard.rm_root": ("apagar o sistema inteiro (rm -rf /)",
                          "erasing the whole system (rm -rf /)",
                          "borrar el sistema entero (rm -rf /)"),
    "gate.hard.no_preserve": ("apagar o disco todo sem protecao",
                              "erasing the whole disk without protection",
                              "borrar todo el disco sin proteccion"),
    "gate.hard.fork_bomb": ("travar o computador com bomba de processos",
                            "freezing the computer with a fork bomb",
                            "travar la computadora con una bomba de procesos"),
    "gate.hard.dd": ("zerar um disco fisico", "wiping a physical disk",
                     "borrar un disco fisico"),
    "gate.hard.token": ("padrao catastrofico no texto", "catastrophic pattern in the text",
                        "patron catastrofico en el texto"),
    "gate.rule.rm_recursive": ("apagar uma pasta e tudo dentro dela",
                               "deleting a folder and everything inside it",
                               "borrar una carpeta y todo lo que hay dentro"),
    "gate.rule.rm_root_path": ("apagar arquivos de pasta do sistema",
                               "deleting files from a system folder",
                               "borrar archivos de una carpeta del sistema"),
    "gate.rule.rm_file": ("apagar um arquivo", "deleting a file", "borrar un archivo"),
    "gate.rule.unsafe_perms": ("deixar arquivos abertos para qualquer pessoa mexer",
                               "leaving files open for anyone to touch",
                               "dejar archivos abiertos para que cualquiera los cambie"),
    "gate.rule.chown_root": ("passar a posse de arquivos para o sistema",
                             "handing file ownership to the system",
                             "pasar la propiedad de archivos al sistema"),
    "gate.rule.mkfs": ("formatar (apagar tudo de) um disco",
                       "formatting (erasing everything on) a disk",
                       "formatear (borrar todo de) un disco"),
    "gate.rule.dd_copy": ("copiar dados direto em disco fisico",
                          "copying data straight onto a physical disk",
                          "copiar datos directo a un disco fisico"),
    "gate.rule.write_block": ("gravar direto em disco fisico",
                              "writing straight onto a physical disk",
                              "escribir directo en un disco fisico"),
    "gate.rule.sql_drop": ("apagar uma tabela ou banco de dados inteiro",
                           "dropping a table or a whole database",
                           "borrar una tabla o una base de datos entera"),
    "gate.rule.sql_delete": ("apagar linhas de uma tabela sem filtro",
                             "deleting table rows without a filter",
                             "borrar filas de una tabla sin filtro"),
    "gate.rule.sql_truncate": ("esvaziar uma tabela inteira", "emptying a whole table",
                               "vaciar una tabla entera"),
    "gate.rule.system_config": ("mudar arquivo de configuracao do sistema",
                                "changing a system configuration file",
                                "cambiar un archivo de configuracion del sistema"),
    "gate.rule.service": ("parar ou reiniciar um servico do sistema",
                          "stopping or restarting a system service",
                          "parar o reiniciar un servicio del sistema"),
    "gate.rule.kill": ("fechar programas a forca", "force-closing programs",
                       "cerrar programas a la fuerza"),
    "gate.rule.pipe_shell": ("baixar algo da internet e executar sem ver o que faz",
                             "downloading something from the internet and running it blindly",
                             "descargar algo de internet y ejecutarlo sin ver que hace"),
    "gate.rule.remote_script": ("executar um script baixado da internet",
                                "running a script downloaded from the internet",
                                "ejecutar un script descargado de internet"),
    "gate.rule.find_delete": ("procurar e apagar varios arquivos de uma vez",
                              "finding and deleting many files at once",
                              "buscar y borrar varios archivos a la vez"),
    "gate.rule.xargs_rm": ("apagar varios arquivos de uma vez",
                           "deleting many files at once",
                           "borrar varios archivos a la vez"),
    "gate.rule.copy_system": ("colocar um arquivo nas pastas do sistema",
                              "putting a file into system folders",
                              "poner un archivo en las carpetas del sistema"),
    "gate.rule.edit_system": ("editar configuracao do sistema",
                              "editing system configuration",
                              "editar la configuracion del sistema"),
    "gate.rule.sudo": ("usar poder de administrador (pede senha)",
                       "using administrator power (asks for a password)",
                       "usar poder de administrador (pide contrasena)"),
    "gate.rule.install_pkg": ("baixar e instalar programa da internet",
                              "downloading and installing a program from the internet",
                              "descargar e instalar un programa de internet"),
    "gate.blocked_hard": (
        "BLOQUEADO PERMANENTE: {why}. Este comando nao roda em nenhuma circunstancia; "
        "rode fora do TEO se for realmente necessario. Procure um caminho alternativo.",
        "PERMANENTLY BLOCKED: {why}. This command does not run under any circumstance; "
        "run it outside TEO if it is really necessary. Look for an alternative path.",
        "BLOQUEADO PERMANENTE: {why}. Este comando no corre en ninguna circunstancia; "
        "ejecutalo fuera del TEO si es realmente necesario. Busca un camino alternativo."),
    "gate.detail_line": ("(preocupacao: {t})", "(concern: {t})", "(preocupacion: {t})"),
    "gate.detail": ("Comando: {command}\n{trechos}", "Command: {command}\n{trechos}",
                    "Comando: {command}\n{trechos}"),
    "gate.denied": (
        "BLOQUEADO: o usuario negou ({labels}). Proponha uma alternativa segura em vez de "
        "repetir.",
        "BLOCKED: the user denied it ({labels}). Propose a safe alternative instead of "
        "repeating it.",
        "BLOQUEADO: el usuario lo nego ({labels}). Propone una alternativa segura en vez "
        "de repetir."),
    "gate.install_detail": (
        "Vou baixar e instalar a biblioteca '{pacote}' (loja oficial do Python, PyPI).\n"
        "Motivo: {motivo}",
        "I will download and install the library '{pacote}' (official Python store, PyPI).\n"
        "Reason: {motivo}",
        "Voy a descargar e instalar la biblioteca '{pacote}' (tienda oficial de Python, PyPI).\n"
        "Motivo: {motivo}"),
    "gate.install_denied": (
        "BLOQUEADO: o usuario nao quis instalar '{pacote}'. Continue sem essa biblioteca "
        "ou explique em linguagem simples por que ela e indispensavel.",
        "BLOCKED: the user did not want to install '{pacote}'. Go on without that library "
        "or explain in simple words why it is indispensable.",
        "BLOQUEADO: el usuario no quiso instalar '{pacote}'. Sigue sin esa biblioteca o "
        "explica en palabras simples por que es indispensable."),
    "gate.py_delete_label": ("apagar arquivos com um programa Python",
                             "deleting files with a Python program",
                             "borrar archivos con un programa Python"),
    "gate.py_delete_detail": (
        "O programa Python vai apagar arquivos (usa '{hit}').\nCodigo:\n{preview}",
        "The Python program will delete files (uses '{hit}').\nCode:\n{preview}",
        "El programa Python va a borrar archivos (usa '{hit}').\nCodigo:\n{preview}"),
    "gate.py_delete_denied": ("BLOQUEADO: o usuario negou o codigo que apaga arquivos.",
                              "BLOCKED: the user denied the code that deletes files.",
                              "BLOQUEADO: el usuario nego el codigo que borra archivos."),
    "gate.overwrite_label": ("Ja existe um arquivo com esse nome; sobrescrever?",
                             "A file with that name already exists; overwrite it?",
                             "Ya existe un archivo con ese nombre; sobrescribir?"),
    "gate.overwrite_denied": (
        "BLOQUEADO: o usuario nao quis sobrescrever {path}. Salve com outro nome.",
        "BLOCKED: the user did not want to overwrite {path}. Save it under another name.",
        "BLOQUEADO: el usuario no quiso sobrescribir {path}. Guardalo con otro nombre."),
    "gate.sensitive_label": ("Vou escrever numa pasta protegida do sistema",
                             "I will write into a protected system folder",
                             "Voy a escribir en una carpeta protegida del sistema"),
    "gate.sensitive_denied": ("BLOQUEADO: o usuario negou escrita em {path}.",
                              "BLOCKED: the user denied writing to {path}.",
                              "BLOQUEADO: el usuario nego escribir en {path}."),
}

# ---------------------------------------------------------------------------
# Tela fixa (tui.py): barra de baixo, perguntas na tela e avisos do teclado
# ---------------------------------------------------------------------------
TUI = {
    "tui.default": (" (padrao: {default})", " (default: {default})",
                    " (predeterminado: {default})"),
    "tui.secret_hint": (
        "(se preferir digitar a chave sem ela aparecer na tela, cancele com ESC e "
        "rode 'bgh setup' na janela de comando)",
        "(to type the key without showing it on screen, cancel with ESC and run "
        "'bgh setup' in the command window)",
        "(para escribir la clave sin que aparezca en pantalla, cancela con ESC y "
        "ejecuta 'bgh setup' en la ventana de comandos)"),
    "tui.hot.config": ("CONFIGURANDO: digite a resposta e ENTER (Enter sozinho = padrao)",
                       "SETTING UP: type the answer and ENTER (Enter alone = default)",
                       "CONFIGURANDO: escribe la respuesta y ENTER (solo Enter = predeterminado)"),
    "tui.hot.license": ("LICENCA PENDENTE: digite o numero e ENTER (ESC = nao)",
                        "PERMISSION PENDING: type the number and ENTER (ESC = no)",
                        "PERMISO PENDIENTE: escribe el numero y ENTER (ESC = no)"),
    "tui.hot.choice": ("OPCAO PENDENTE: digite o numero e ENTER (ESC = [1])",
                       "OPTION PENDING: type the number and ENTER (ESC = [1])",
                       "OPCION PENDIENTE: escribe el numero y ENTER (ESC = [1])"),
    "tui.choice_hint": ("(Enter sozinho = [1]; ESC tambem escolhe [1])",
                        "(Enter alone = [1]; ESC also picks [1])",
                        "(solo Enter = [1]; ESC tambien elige [1])"),
    "tui.approval_question": ("O que voce quer fazer? Digite o numero e ENTER:",
                              "What do you want to do? Type the number and ENTER:",
                              "Que quieres hacer? Escribe el numero y ENTER:"),
    "tui.approval_hint": ("(Enter sozinho = [{n}] nao / cancelar; ESC tambem nega)",
                          "(Enter alone = [{n}] no / cancel; ESC also denies)",
                          "(solo Enter = [{n}] no / cancelar; ESC tambien niega)"),
    "tui.cancelled": ("(cancelado)", "(cancelled)", "(cancelado)"),
    "tui.stopping": ("(parando...)", "(stopping...)", "(parando...)"),
    "tui.steer_hint": ("(avisado no meio do turno; o modelo le na proxima rodada)",
                       "(noted in the middle of the turn; the model reads it on the next round)",
                       "(avisado en medio del turno; el modelo lo lee en la siguiente ronda)"),
    "tui.busy_cmd": ("(estou respondendo; comandos / funcionam quando o turno terminar)",
                     "(I am answering; / commands work when the turn ends)",
                     "(estoy respondiendo; los comandos / funcionan cuando termine el turno)"),
    "tui.busy_hint": ("(estou respondendo; para parar: CTRL+C ou ESC)",
                      "(I am answering; to stop: CTRL+C or ESC)",
                      "(estoy respondiendo; para parar: CTRL+C o ESC)"),
    "tui.crash": ("Algo deu errado na tela do TEO; a conversa continua normalmente. "
                  "O detalhe tecnico foi guardado no arquivo erro.log da pasta .bgh.",
                  "Something went wrong on the TEO screen; the conversation goes on "
                  "normally. The technical detail was saved in erro.log inside .bgh.",
                  "Algo salio mal en la pantalla del TEO; la conversacion sigue "
                  "normalmente. El detalle tecnico quedo en erro.log de la carpeta .bgh."),
    "tui.running": ("rodando... {s}s", "running... {s}s", "corriendo... {s}s"),
    "tui.listening": ("ouvindo", "listening", "escuchando"),
    "tui.stop_keys": ("PARA PARAR: CTRL+C ou ESC", "TO STOP: CTRL+C or ESC",
                      "PARA PARAR: CTRL+C o ESC"),
    "tui.footer_long": (
        "ENTER = enviar | CTRL+C com linha vazia = sair | {help} | reler: roda do mouse "
        "ou barra lateral do seu terminal",
        "ENTER = send | CTRL+C on an empty line = quit | {help} | re-read: mouse wheel "
        "or your terminal scrollbar",
        "ENTER = enviar | CTRL+C con linea vacia = salir | {help} | releer: rueda del "
        "raton o barra lateral de tu terminal"),
    "tui.footer_short": ("ENTER = enviar | CTRL+C vazio = sair | {help}",
                         "ENTER = send | CTRL+C empty = quit | {help}",
                         "ENTER = enviar | CTRL+C vacio = salir | {help}"),
    "tui.of": ("de", "of", "de"),
    "tui.msg": ("msg", "msg", "msg"),
    "tui.toks": ("toks", "toks", "toks"),
}

# ---------------------------------------------------------------------------
# Palco (palco.py): trilha do pedido desenhada durante a resposta
# ---------------------------------------------------------------------------
PALCO = {
    "palco.stage.start": ("START", "START", "START"),
    "palco.stage.agent": ("AGENTE", "AGENT", "AGENTE"),
    "palco.stage.tool": ("FERRAMENTA", "TOOL", "HERRAMIENTA"),
    "palco.stage.model": ("MODELO", "MODEL", "MODELO"),
    "palco.stage.screen": ("TELA", "SCREEN", "PANTALLA"),
    "palco.fase.pedido": ("pedido entregue ao agente", "request handed to the agent",
                          "pedido entregado al agente"),
    "palco.fase.agente": ("o agente esta trabalhando", "the agent is working",
                          "el agente esta trabajando"),
    "palco.fase.ferramenta": ("o pessoal esta executando a tarefa",
                              "the tools are running the task",
                              "las herramientas estan ejecutando la tarea"),
    "palco.fase.modelo": ("o modelo esta escrevendo a resposta",
                          "the model is writing the answer",
                          "el modelo esta escribiendo la respuesta"),
    "palco.fase.resposta": ("a resposta esta chegando na tela",
                            "the answer is arriving on screen",
                            "la respuesta esta llegando a la pantalla"),
    "palco.fase.pronto": ("resposta entregue", "answer delivered", "respuesta entregada"),
    "palco.fase.erro": ("voltou com erro", "came back with an error", "volvio con error"),
    "palco.fase.parado": ("voce mandou parar", "you asked to stop", "pediste parar"),
    "palco.round": ("rodada {n}", "round {n}", "ronda {n}"),
    "palco.turn": ("turno {s}s", "turn {s}s", "turno {s}s"),
    "palco.tk": ("{entrada}/{saida} tk", "{entrada}/{saida} tk", "{entrada}/{saida} tk"),
}

# ---------------------------------------------------------------------------
# Cliente do modelo (llm.py): erros e avisos que aparecem na tela
# ---------------------------------------------------------------------------
LLM = {
    "llm.wait_hint": (" O proprio servidor pediu {s} segundos de espera.",
                      " The server itself asked for a {s} second wait.",
                      " El propio servidor pidio {s} segundos de espera."),
    "llm.rate_limit": (
        "O provedor pediu para esperar: o limite de uso deste momento foi atingido "
        "(ou a cota da conta acabou).{hint} Espere um pouco e mande a pergunta de "
        "novo. Se acontecer sempre, troque de provedor digitando {provider}.",
        "The provider asked to wait: the usage limit for this moment was reached "
        "(or the account quota ran out).{hint} Wait a little and send the question "
        "again. If it keeps happening, switch providers by typing {provider}.",
        "El proveedor pidio esperar: se alcanzo el limite de uso de este momento "
        "(o se acabo la cuota de la cuenta).{hint} Espera un poco y manda la "
        "pregunta otra vez. Si pasa siempre, cambia de proveedor escribiendo {provider}."),
    "llm.timeout": (
        "O modelo nao respondeu em {s}s de espera. Em servidor remoto isso costuma "
        "ser contexto grande demais: baixe o orcamento de contexto ou ajuste "
        "request_timeout_s no config.json.",
        "The model did not answer within {s}s. On a remote server this is usually a "
        "context that is too large: lower the context budget or adjust "
        "request_timeout_s in config.json.",
        "El modelo no respondio en {s}s de espera. En servidor remoto eso suele ser "
        "contexto demasiado grande: baja el presupuesto de contexto o ajusta "
        "request_timeout_s en config.json."),
    "llm.context_overflow": ("O contexto passou do limite que o servidor aceita.",
                             "The context went over the limit the server accepts.",
                             "El contexto paso del limite que el servidor acepta."),
    "llm.fail": ("Falha ao falar com o modelo ({tipo}): {erro}",
                 "Failed to talk to the model ({tipo}): {erro}",
                 "Falla al hablar con el modelo ({tipo}): {erro}"),
    "llm.fail_fallback": ("Falha ao falar com o modelo (fallback esgotado).",
                          "Failed to talk to the model (fallback exhausted).",
                          "Falla al hablar con el modelo (sin mas intentos)."),
    "llm.empty": ("O modelo respondeu vazio (sem choices).",
                  "The model answered empty (no choices).",
                  "El modelo respondio vacio (sin choices)."),
    "llm.list_fail": ("Nao consegui listar modelos em {url}: {erro}",
                      "I could not list models at {url}: {erro}",
                      "No pude listar modelos en {url}: {erro}"),
    "llm.no_stream": (
        "O servidor nao aceitou a resposta em pedacos ({tipo}); vou responder de "
        "uma vez (mais uma espera).",
        "The server did not accept the piece-by-piece answer ({tipo}); I will answer "
        "all at once (one more wait).",
        "El servidor no acepto la respuesta por partes ({tipo}); voy a responder de "
        "una vez (una espera mas)."),
    "llm.broken": (
        "A resposta caiu no meio depois de {s}s de espera ({tipo}: {erro}). O texto "
        "que apareceu ficou guardado; pergunte de novo ou use um orcamento de "
        "contexto menor.",
        "The answer broke in the middle after {s}s ({tipo}: {erro}). The text that "
        "appeared was kept; ask again or use a smaller context budget.",
        "La respuesta se corto en el medio despues de {s}s ({tipo}: {erro}). El texto "
        "que aparecio quedo guardado; pregunta otra vez o usa un presupuesto de "
        "contexto menor."),
    "llm.silent": (
        "Nada chegou do servidor em {s}s; vou tentar sem streaming (uma espera a "
        "mais, e o pedido vai de novo para a fila).",
        "Nothing arrived from the server in {s}s; I will try without streaming (one "
        "more wait, and the request goes back in the queue).",
        "Nada llego del servidor en {s}s; voy a intentar sin streaming (una espera "
        "mas, y el pedido vuelve a la fila)."),
    "llm.summarize": (
        "Resuma a conversa abaixo em no maximo 15 pontos curtos. Preserve: decisoes "
        "tomadas, caminhos de arquivo citados, erros encontrados e pedidos ainda "
        "abertos. Responda so com o resumo.",
        "Summarize the conversation below in at most 15 short points. Keep: decisions "
        "taken, file paths mentioned, errors found and requests still open. Answer "
        "only with the summary.",
        "Resume la conversacion abajo en maximo 15 puntos cortos. Conserva: decisiones "
        "tomadas, rutas de archivo citadas, errores encontrados y pedidos aun "
        "abiertos. Responde solo con el resumen."),
}

# ---------------------------------------------------------------------------
# Assistente de configuracao (setup_wizard.py) e CLI (cli.py)
# ---------------------------------------------------------------------------
SETUP = {
    "setup.title": ("Configuracao do TEO", "TEO setup", "Configuracion del TEO"),
    "setup.current": ("Atual: {name} / {model} @ {base_url}",
                      "Current: {name} / {model} @ {base_url}",
                      "Actual: {name} / {model} @ {base_url}"),
    "setup.keep": ("Manter o provedor em uso?", "Keep the provider in use?",
                   "Mantener el proveedor en uso?"),
    "setup.nothing_changed": ("Nada mudado.", "Nothing changed.", "Nada cambiado."),
    "setup.where": ("Escolha onde o modelo vai rodar:", "Choose where the model will run:",
                    "Elige donde va a correr el modelo:"),
    "setup.opt.deepseek": (
        "  1) DeepSeek      - API na nuvem (mais facil; precisa de chave em api.deepseek.com)",
        "  1) DeepSeek      - cloud API (easiest; needs a key at api.deepseek.com)",
        "  1) DeepSeek      - API en la nube (mas facil; necesita clave en api.deepseek.com)"),
    "setup.opt.nubesbr": (
        "  2) NubesBR       - servidor de IA hospedado (exige rede/tunel liberado)",
        "  2) NubesBR       - hosted AI server (needs network/tunnel open)",
        "  2) NubesBR       - servidor de IA hospedado (necesita red/tunel liberado)"),
    "setup.opt.local": (
        "  3) Local         - modelo na propria maquina (llama.cpp / LM Studio)",
        "  3) Local         - model on this machine (llama.cpp / LM Studio)",
        "  3) Local         - modelo en la propia maquina (llama.cpp / LM Studio)"),
    "setup.opt.custom": (
        "  4) Outro         - qualquer endpoint OpenAI-compativel",
        "  4) Other         - any OpenAI-compatible endpoint",
        "  4) Otro          - cualquier endpoint compatible con OpenAI"),
    "setup.option": ("Opcao", "Option", "Opcion"),
    "setup.url": ("URL do servidor do modelo", "Model server URL", "URL del servidor del modelo"),
    "setup.model": ("Nome do modelo", "Model name", "Nombre del modelo"),
    "setup.key": ("Chave de acesso (Enter se nao precisar)",
                  "Access key (Enter if not needed)", "Clave de acceso (Enter si no hace falta)"),
    "setup.budget_inherited": (
        "Orcamento de contexto herdado do servidor: {n} caracteres (ele entrega ate "
        "{tokens} tokens).",
        "Context budget inherited from the server: {n} characters (it delivers up to "
        "{tokens} tokens).",
        "Presupuesto de contexto heredado del servidor: {n} caracteres (entrega hasta "
        "{tokens} tokens)."),
    "setup.budget_default": (
        "Orcamento de contexto: {n} caracteres (padrao deste provedor; o TEO nao "
        "perguntou ao servidor). Para ajustar: {ctx} 90000 na tela.",
        "Context budget: {n} characters (default for this provider; TEO did not ask "
        "the server). To adjust: {ctx} 90000 on screen.",
        "Presupuesto de contexto: {n} caracteres (predeterminado de este proveedor; el "
        "TEO no pregunto al servidor). Para ajustar: {ctx} 90000 en pantalla."),
    "setup.exists": ("'{name}' ja esta cadastrado. Atualizar os dados dessa opcao?",
                     "'{name}' is already registered. Update the data of that option?",
                     "'{name}' ya esta registrado. Actualizar los datos de esa opcion?"),
    "setup.new_name": ("Nome da nova opcao", "Name of the new option",
                       "Nombre de la nueva opcion"),
    "setup.skills": ("Skills instaladas em {dir}", "Skills installed in {dir}",
                     "Skills instaladas en {dir}"),
    "setup.saved": ("Salvo em {path} (permissao restrita ao seu usuario).",
                    "Saved in {path} (permission restricted to your user).",
                    "Guardado en {path} (permiso restricto a tu usuario)."),
    "setup.ping": ("Responda apenas com a palavra: pronto",
                   "Answer only with the word: ready",
                   "Responde solo con la palabra: listo"),
    "setup.conn_ok": ("Conexao OK. O modelo disse: {reply}",
                      "Connection OK. The model said: {reply}",
                      "Conexion OK. El modelo dijo: {reply}"),
    "setup.test": ("Testar a conexao agora?", "Test the connection now?",
                   "Probar la conexion ahora?"),
    "setup.failed": ("FALHOU: {msg}", "FAILED: {msg}", "FALLO: {msg}"),
    "setup.wants_key": ("O servidor parece exigir uma chave de acesso.",
                        "The server seems to require an access key.",
                        "El servidor parece exigir una clave de acceso."),
    "setup.paste_key": ("Cole a chave aqui (Enter se nao tiver uma)",
                        "Paste the key here (Enter if you do not have one)",
                        "Pega la clave aqui (Enter si no tienes una)"),
    "setup.failed_again": ("FALHOU de novo: {msg}", "FAILED again: {msg}",
                           "FALLO de nuevo: {msg}"),
    "setup.check": ("Confira URL e chave (digite {setup} de novo ou rode 'bgh doctor' "
                    "fora do TEO).",
                    "Check URL and key (type {setup} again or run 'bgh doctor' outside TEO).",
                    "Revisa URL y clave (escribe {setup} otra vez o ejecuta 'bgh doctor' "
                    "fuera del TEO)."),
    "setup.done": ("Pronto! Para conversar, digite apenas: bgh",
                   "Ready! To chat, type only: bgh",
                   "Listo! Para conversar, escribe solo: bgh"),
    "setup.lang_ask": (
        "Idioma / Language / Idioma - 1) Portugues  2) English  3) Espanol",
        "Idioma / Language / Idioma - 1) Portugues  2) English  3) Espanol",
        "Idioma / Language / Idioma - 1) Portugues  2) English  3) Espanol"),
}

CLI = {
    "cli.noninteractive": ("Em modo nao-interativo, configure antes com: bgh setup",
                           "In non-interactive mode, set it up first with: bgh setup",
                           "En modo no interactivo, configura antes con: bgh setup"),
    "cli.first_run": ("\nVamos configurar juntos agora, em poucas perguntas de uma linha cada.",
                      "\nLet us set it up together now, in a few one-line questions.",
                      "\nVamos a configurarlo juntos ahora, en pocas preguntas de una linea cada una."),
    "cli.no_always": ("Nenhuma permissao 'sempre' guardada.",
                      "No 'always' permission saved.",
                      "Ningun permiso 'siempre' guardado."),
    "cli.clear_ask": ("Apagar todas as permissoes 'sempre' guardadas?",
                      "Delete all saved 'always' permissions?",
                      "Borrar todos los permisos 'siempre' guardados?"),
    "cli.clear_done": ("Pronto: {n} permissao(oes) removida(s).",
                       "Done: {n} permission(s) removed.",
                       "Listo: {n} permiso(s) quitados."),
    "cli.nothing_removed": ("Nada removido.", "Nothing removed.", "Nada quitado."),
    "cli.removed": ("Removido: {item}", "Removed: {item}", "Quitado: {item}"),
    "cli.bad_index": ("Numero invalido (veja 'bgh approvals').",
                      "Invalid number (see 'bgh approvals').",
                      "Numero invalido (mira 'bgh approvals')."),
    "doctor.title": ("Diagnostico do TEO", "TEO diagnostics", "Diagnostico del TEO"),
    "doctor.machine": ("Maquina", "Machine", "Maquina"),
    "doctor.gpu": ("GPU", "GPU", "GPU"),
    "doctor.conn": ("Conexao com o modelo", "Connection to the model",
                    "Conexion con el modelo"),
    "doctor.no_output": ("(sem saida)", "(no output)", "(sin salida)"),
    "doctor.failed": ("(falhou: {erro})", "(failed: {erro})", "(fallo: {erro})"),
    "doctor.no_nvidia": ("(nvidia-smi nao encontrado; pode ser AMD/intel ou placa sem driver)",
                         "(nvidia-smi not found; may be AMD/intel or a card without driver)",
                         "(nvidia-smi no encontrado; puede ser AMD/intel o placa sin driver)"),
    "doctor.no_conn": ("(sem conexao ainda: {erro})", "(no connection yet: {erro})",
                       "(sin conexion todavia: {erro})"),
    "doctor.ok": ("OK - {url} responde. Modelos: {names}{extra}",
                  "OK - {url} answers. Models: {names}{extra}",
                  "OK - {url} responde. Modelos: {names}{extra}"),
    "doctor.empty_list": ("(lista vazia)", "(empty list)", "(lista vacia)"),
    "doctor.context": (" | contexto que o servidor entrega: {tokens} tokens",
                       " | context the server delivers: {tokens} tokens",
                       " | contexto que el servidor entrega: {tokens} tokens"),
    "doctor.fail": ("Falha - {erro}", "Failure - {erro}", "Falla - {erro}"),
    "doctor.hint": (
        "Confira: o servidor do modelo esta ligado? A URL e a chave estao certas? "
        "({setup} no chat ou bgh setup na janela de comando)",
        "Check: is the model server running? Are the URL and key right? "
        "({setup} in the chat or bgh setup in the command window)",
        "Revisa: el servidor del modelo esta encendido? La URL y la clave estan "
        "correctas? ({setup} en el chat o bgh setup en la ventana de comandos)"),
    "cli.help.prog": ("TEO - agente local simples", "TEO - simple local agent",
                      "TEO - agente local simple"),
    "cli.help.chat": ("conversa interativa (padrao)", "interactive chat (default)",
                      "conversacion interactiva (predeterminado)"),
    "cli.help.setup": ("configurar o modelo em 1 minuto", "set up the model in 1 minute",
                       "configurar el modelo en 1 minuto"),
    "cli.help.doctor": ("diagnostico da maquina e da conexao",
                        "machine and connection diagnostics",
                        "diagnostico de la maquina y de la conexion"),
    "cli.help.approvals": ("ver/limpar permissoes 'sempre' guardadas",
                           "view/clear saved 'always' permissions",
                           "ver/limpiar permisos 'siempre' guardados"),
}

# ---------------------------------------------------------------------------
# Ferramentas (tools/): descricoes que acompanham o pedido ao modelo
# ---------------------------------------------------------------------------
TOOLS = {
    "tool.run_command.desc": (
        "Executa um comando shell na maquina local (ls, df, journalctl, systemctl "
        "status, nvidia-smi, apt list, smartctl etc.). Comandos de leitura rodam sem "
        "perguntar; perigosos pedem aprovacao do usuario.",
        "Runs a shell command on the local machine (ls, df, journalctl, systemctl "
        "status, nvidia-smi, apt list, smartctl etc.). Read-only commands run without "
        "asking; dangerous ones ask the user for approval.",
        "Ejecuta un comando shell en la maquina local (ls, df, journalctl, systemctl "
        "status, nvidia-smi, apt list, smartctl etc.). Los comandos de lectura corren "
        "sin preguntar; los peligrosos piden aprobacion del usuario."),
    "tool.run_command.arg.command": ("O comando shell completo", "The full shell command",
                                     "El comando shell completo"),
    "tool.run_command.arg.timeout": ("Tempo limite em segundos (padrao 120)",
                                     "Time limit in seconds (default 120)",
                                     "Tiempo limite en segundos (predeterminado 120)"),
    "tool.run_python.desc": (
        "Executa um script Python na maquina local e devolve stdout/stderr. Use para "
        "calcular, validar dados, testar o codigo que voce escreveu e diagnosticar o "
        "sistema. O codigo roda no venv do Motor (tem requests/openai/rich) e na PASTA "
        "DE RASCUNHO do TEO: arquivos criados ali nao aparecem na pasta do usuario. Para "
        "experimentar, use esta ferramenta - write_file e so para o arquivo final que o "
        "usuario pediu.",
        "Runs a Python script on the local machine and returns stdout/stderr. Use it to "
        "calculate, validate data, test the code you wrote and diagnose the system. The "
        "code runs in the Motor venv (it has requests/openai/rich) and in the TEO DRAFT "
        "FOLDER: files created there do not show up in the user's folder. To experiment, "
        "use this tool - write_file is only for the final file the user asked for.",
        "Ejecuta un script Python en la maquina local y devuelve stdout/stderr. Usalo para "
        "calcular, validar datos, probar el codigo que escribiste y diagnosticar el "
        "sistema. El codigo corre en el venv del Motor (tiene requests/openai/rich) y en "
        "la CARPETA DE BORRADOR del TEO: los archivos creados ahi no aparecen en la "
        "carpeta del usuario. Para experimentar, usa esta herramienta - write_file es "
        "solo para el archivo final que el usuario pidio."),
    "tool.run_python.arg.code": ("Script Python completo", "Complete Python script",
                                 "Script Python completo"),
    "tool.run_python.arg.timeout": ("Tempo limite em segundos (padrao 60)",
                                    "Time limit in seconds (default 60)",
                                    "Tiempo limite en segundos (predeterminado 60)"),
    "tool.read_file.desc": (
        "Le um arquivo de texto e devolve linhas numeradas (NUM|conteudo).",
        "Reads a text file and returns numbered lines (NUM|content).",
        "Lee un archivo de texto y devuelve lineas numeradas (NUM|contenido)."),
    "tool.read_file.arg.path": ("Caminho do arquivo", "File path", "Ruta del archivo"),
    "tool.read_file.arg.offset": ("Linha inicial (1-indexado, padrao 1)",
                                  "Starting line (1-indexed, default 1)",
                                  "Linea inicial (1-indexado, predeterminado 1)"),
    "tool.read_file.arg.limit": ("Maximo de linhas (padrao 200)",
                                 "Maximum lines (default 200)",
                                 "Maximo de lineas (predeterminado 200)"),
    "tool.write_file.desc": (
        "Grava o ARQUIVO FINAL que o usuario pediu (relatorio, documento, pagina). Cria "
        "diretorios pai; se o arquivo ja existe, pede confirmacao antes. Para testar "
        "codigo ou gerar arquivos de apoio use run_python (ele roda no rascunho do TEO e "
        "nao suja a pasta do usuario).",
        "Writes the FINAL FILE the user asked for (report, document, page). Creates "
        "parent directories; if the file already exists, it asks for confirmation first. "
        "To test code or generate helper files use run_python (it runs in the TEO draft "
        "folder and does not dirty the user's folder).",
        "Graba el ARCHIVO FINAL que el usuario pidio (informe, documento, pagina). Crea "
        "los directorios padre; si el archivo ya existe, pide confirmacion antes. Para "
        "probar codigo o generar archivos de apoyo usa run_python (corre en el borrador "
        "del TEO y no ensucia la carpeta del usuario)."),
    "tool.write_file.arg.path": ("Caminho do arquivo", "File path", "Ruta del archivo"),
    "tool.write_file.arg.content": ("Conteudo completo a gravar", "Full content to write",
                                    "Contenido completo a grabar"),
    "tool.search_files.desc": (
        "Busca expressao regular dentro dos arquivos de uma pasta (como rg). Passe uma "
        "pasta especifica: a busca tem teto de tempo e de arquivos e para sozinha.",
        "Searches a regular expression inside the files of a folder (like rg). Pass a "
        "specific folder: the search has time and file caps and stops by itself.",
        "Busca una expresion regular dentro de los archivos de una carpeta (como rg). Pasa "
        "una carpeta especifica: la busqueda tiene tope de tiempo y de archivos y se "
        "detiene sola."),
    "tool.search_files.arg.pattern": ("Expressao regular", "Regular expression",
                                      "Expresion regular"),
    "tool.search_files.arg.path": ("Pasta onde buscar (padrao: diretorio atual)",
                                   "Folder to search (default: current directory)",
                                   "Carpeta donde buscar (predeterminado: directorio actual)"),
    "tool.search_files.arg.glob": ("Filtro de nome, ex.: *.py", "Name filter, e.g. *.py",
                                   "Filtro de nombre, ej.: *.py"),
    "tool.web_search.desc": (
        "Pesquisa na internet (DuckDuckGo, sem chave de API). Devolve titulo, URL e "
        "resumo dos resultados.",
        "Searches the internet (DuckDuckGo, no API key). Returns title, URL and a summary "
        "of the results.",
        "Busca en internet (DuckDuckGo, sin clave de API). Devuelve titulo, URL y resumen "
        "de los resultados."),
    "tool.web_search.arg.query": ("Termos da busca", "Search terms", "Terminos de la busqueda"),
    "tool.web_search.arg.top_k": ("Quantidade de resultados (padrao 6, max 10)",
                                  "Number of results (default 6, max 10)",
                                  "Cantidad de resultados (predeterminado 6, max 10)"),
    "tool.web_extract.desc": (
        "Baixa uma pagina web e devolve o texto do conteudo (para confirmar informacao da "
        "busca).",
        "Downloads a web page and returns the content text (to confirm information from "
        "the search).",
        "Descarga una pagina web y devuelve el texto del contenido (para confirmar "
        "informacion de la busqueda)."),
    "tool.web_extract.arg.url": ("URL http(s) completa", "Full http(s) URL",
                                 "URL http(s) completa"),
    "tool.memory.desc": (
        "Memoria permanente do Motor sobre este usuario/maquina. action=add grava um fato "
        "curto; action=search procura por palavra; action=list mostra as ultimas. "
        "target=user para preferencias e caracteristicas do usuario (ex.: 'prefere "
        "respostas curtas', 'nao sabe usar terminal'); target=note para fatos da maquina. "
        "NUNCA guarde senhas, cartoes ou codigos.",
        "Motor's permanent memory about this user/machine. action=add saves a short fact; "
        "action=search looks for a word; action=list shows the latest. target=user for the "
        "user's preferences and traits (e.g. 'prefers short answers', 'does not know how "
        "to use a terminal'); target=note for machine facts. NEVER store passwords, cards "
        "or codes.",
        "Memoria permanente del Motor sobre este usuario/maquina. action=add graba un dato "
        "corto; action=search busca por palabra; action=list muestra las ultimas. "
        "target=user para preferencias y caracteristicas del usuario (ej.: 'prefiere "
        "respuestas cortas', 'no sabe usar terminal'); target=note para datos de la "
        "maquina. NUNCA guardes contrasenas, tarjetas o codigos."),
    "tool.memory.arg.target": ("Padrao: note", "Default: note", "Predeterminado: note"),
    "tool.memory.arg.text": ("O fato a gravar (para add)", "The fact to save (for add)",
                             "El dato a grabar (para add)"),
    "tool.memory.arg.query": ("Palavra-chave (para search)", "Keyword (for search)",
                              "Palabra clave (para search)"),
    "tool.skill.desc": (
        "Skills = procedimentos aprendidos para esta maquina/usuario. action=load le uma "
        "skill inteira (SEMPRE antes de tarefa do dominio dela); action=create grava uma "
        "skill nova quando voce descobriu um procedimento que funcionou; action=append "
        "acrescenta uma licao ou correcao do usuario a uma skill existente.",
        "Skills = procedures learned for this machine/user. action=load reads a whole "
        "skill (ALWAYS before a task in its domain); action=create saves a new skill when "
        "you found a procedure that worked; action=append adds a lesson or the user's "
        "correction to an existing skill.",
        "Skills = procedimientos aprendidos para esta maquina/usuario. action=load lee una "
        "skill entera (SIEMPRE antes de una tarea de su dominio); action=create graba una "
        "skill nueva cuando descubriste un procedimiento que funciono; action=append "
        "agrega una leccion o correccion del usuario a una skill existente."),
    "tool.skill.arg.name": ("Nome da skill (minusculo, com -)",
                            "Skill name (lowercase, with -)",
                            "Nombre de la skill (minuscula, con -)"),
    "tool.skill.arg.content": ("Conteudo completo (create)", "Full content (create)",
                               "Contenido completo (create)"),
    "tool.skill.arg.section": ("Trecho a acrescentar (append)", "Piece to add (append)",
                               "Trecho a agregar (append)"),
    "tool.make_document.desc": (
        "Cria um documento para o usuario (relatorio, carta, guia) em Markdown ou HTML e "
        "salva na pasta de Documentos. Devolve o caminho completo do arquivo.",
        "Creates a document for the user (report, letter, guide) in Markdown or HTML and "
        "saves it in the Documents folder. Returns the full file path.",
        "Crea un documento para el usuario (informe, carta, guia) en Markdown o HTML y lo "
        "guarda en la carpeta de Documentos. Devuelve la ruta completa del archivo."),
    "tool.make_document.arg.title": ("Titulo do documento", "Document title",
                                     "Titulo del documento"),
    "tool.make_document.arg.content_markdown": ("Conteudo em markdown simples",
                                                "Content in simple markdown",
                                                "Contenido en markdown simple"),
    "tool.make_document.arg.fmt": ("Formato (padrao md)", "Format (default md)",
                                   "Formato (predeterminado md)"),
    "tool.make_document.arg.path": ("Opcional: caminho explicito de saida",
                                    "Optional: explicit output path",
                                    "Opcional: ruta explicita de salida"),
    "tool.instalar_pacote.desc": (
        "Instala uma biblioteca Python que esta faltando para a tarefa (PyPI oficial). Use "
        "quando um import falhar com ModuleNotFoundError. O usuario ve o motivo em "
        "linguagem simples e aprova ou nega. Instale so o que a tarefa precisa.",
        "Installs a Python library that is missing for the task (official PyPI). Use it "
        "when an import fails with ModuleNotFoundError. The user sees the reason in simple "
        "words and approves or denies. Install only what the task needs.",
        "Instala una biblioteca Python que falta para la tarea (PyPI oficial). Usalo "
        "cuando un import falle con ModuleNotFoundError. El usuario ve el motivo en "
        "lenguaje simple y aprueba o niega. Instala solo lo que la tarea necesita."),
    "tool.instalar_pacote.arg.pacote": (
        "Nome exato no PyPI, ex.: requests, openpyxl, pandas==2.2.0",
        "Exact PyPI name, e.g. requests, openpyxl, pandas==2.2.0",
        "Nombre exacto en PyPI, ej.: requests, openpyxl, pandas==2.2.0"),
    "tool.instalar_pacote.arg.motivo": (
        "Frase curta NO IDIOMA DA TELA explicando ao usuario por que precisa",
        "Short sentence IN THE SCREEN LANGUAGE telling the user why it is needed",
        "Frase corta EN EL IDIOMA DE LA PANTALLA explicando al usuario por que hace falta"),
    "tool.limpar_apoio.desc": (
        "Apaga os arquivos de APOIO que o proprio TEO criou nesta conversa (scripts, "
        "rascunhos, copias), deixando apenas o arquivo final pedido pelo usuario. Nunca "
        "apaga arquivo que o usuario ja tinha.",
        "Deletes the HELPER files that TEO itself created in this conversation (scripts, "
        "drafts, copies), keeping only the final file the user asked for. It never deletes "
        "a file the user already had.",
        "Borra los archivos de APOYO que el propio TEO creo en esta conversacion (scripts, "
        "borradores, copias), dejando solo el archivo final pedido por el usuario. Nunca "
        "borra un archivo que el usuario ya tenia."),
    "tool.limpar_apoio.arg.pasta": ("Limitar a esta pasta (padrao: todas)",
                                    "Limit to this folder (default: all)",
                                    "Limitar a esta carpeta (predeterminado: todas)"),
    "tool.limpar_apoio.arg.manter": ("Arquivo a PRESERVAR (ex.: o relatorio final)",
                                     "File to KEEP (e.g. the final report)",
                                     "Archivo a CONSERVAR (ej.: el informe final)"),
    "tool.unknown": ("ERRO: ferramenta desconhecida '{name}'. Disponiveis: {lista}",
                     "ERROR: unknown tool '{name}'. Available: {lista}",
                     "ERROR: herramienta desconocida '{name}'. Disponibles: {lista}"),
    "tool.bad_args": ("ERRO: argumentos invalidos para {name}: {erro}. Reenvie JSON valido.",
                      "ERROR: invalid arguments for {name}: {erro}. Send valid JSON again.",
                      "ERROR: argumentos invalidos para {name}: {erro}. Reenvia JSON valido."),
    "tool.crash": ("ERRO na ferramenta {name} ({tipo}): {erro}",
                   "ERROR in tool {name} ({tipo}): {erro}",
                   "ERROR en la herramienta {name} ({tipo}): {erro}"),
    "tool.truncated": ("\n...[cortado, {n} chars no total]...\n",
                       "\n...[truncated, {n} chars total]...\n",
                       "\n...[cortado, {n} chars en total]...\n"),
}

# ---------------------------------------------------------------------------
# Atualizacao (updater.py)
# ---------------------------------------------------------------------------
UPDATER = {
    "upd.net": ("nao consegui falar com o GitHub ({tipo})",
                "I could not reach GitHub ({tipo})",
                "no pude hablar con GitHub ({tipo})"),
    "upd.status": ("o GitHub respondeu {code} (limite de consulta? tente mais tarde)",
                   "GitHub answered {code} (query limit? try later)",
                   "GitHub respondio {code} (limite de consulta? intenta mas tarde)"),
    "upd.bad_json": ("a pagina de releases do GitHub veio em formato inesperado",
                     "the GitHub releases page came in an unexpected format",
                     "la pagina de releases de GitHub vino en un formato inesperado"),
    "upd.no_tag": ("a release mais recente nao informou o numero da versao",
                   "the latest release did not report the version number",
                   "la release mas reciente no informo el numero de version"),
    "upd.no_wheel": ("a release mais recente nao traz o pacote .whl para instalar",
                     "the latest release does not bring the .whl package to install",
                     "la release mas reciente no trae el paquete .whl para instalar"),
    "upd.deps_ok": ("Dependencias conferidas (nada novo para instalar).",
                    "Dependencies checked (nothing new to install).",
                    "Dependencias revisadas (nada nuevo para instalar)."),
    "upd.deps_fail": ("A versao nova ja esta instalada, mas nao consegui conferir as "
                      "dependencias ({erro}). Se algum recurso novo faltar, rode "
                      "'bgh setup'.",
                      "The new version is installed, but I could not check the "
                      "dependencies ({erro}). If a new feature is missing, run "
                      "'bgh setup'.",
                      "La version nueva ya esta instalada, pero no pude revisar las "
                      "dependencias ({erro}). Si falta algun recurso nuevo, corre "
                      "'bgh setup'."),
    "upd.deps_net": ("sem internet para conferir as dependencias ({tipo})",
                     "no internet to check the dependencies ({tipo})",
                     "sin internet para revisar las dependencias ({tipo})"),
    "upd.deps_status": ("o GitHub respondeu {code} no requirements.txt",
                        "GitHub answered {code} for requirements.txt",
                        "GitHub respondio {code} en requirements.txt"),
    "upd.frozen": (
        "esta instalacao roda como arquivo unico (executavel) e nao tem um Python para "
        "receber a atualizacao - use o INSTALAR_TEO.bat novamente",
        "this installation runs as a single file (executable) and has no Python to "
        "receive the update - run INSTALAR_TEO.bat again",
        "esta instalacion corre como archivo unico (ejecutable) y no tiene un Python "
        "para recibir la actualizacion - usa INSTALAR_TEO.bat otra vez"),
    "upd.timeout": ("a baixada parou no meio (demorou demais); tente de novo ou rode o INSTALAR_TEO.bat",
                    "the download stopped in the middle (it took too long); try again or run "
                    "INSTALAR_TEO.bat",
                    "la descarga se corto en el medio (tardo demasiado); intenta de nuevo o "
                    "ejecuta INSTALAR_TEO.bat"),
    "upd.oserr": ("nao consegui rodar o instalador interno: {erro}",
                  "I could not run the internal installer: {erro}",
                  "no pude ejecutar el instalador interno: {erro}"),
    "upd.done": ("instalacao concluida", "installation finished", "instalacion terminada"),
    "upd.pip_fail": ("o pip nao completou (codigo {code}): {tail}",
                     "pip did not finish (code {code}): {tail}",
                     "pip no termino (codigo {code}): {tail}"),
    "upd.no_detail": ("sem detalhe", "no detail", "sin detalle"),
    # Checagem da ABERTURA (uma vez, em segundo plano): so avisa quando ha o que dizer.
    "upd.start_new": (
        "Existe versao nova do TEO ({version}). Para atualizar, digite {update}.",
        "A new TEO version is available ({version}). To update, type {update}.",
        "Hay una version nueva del TEO ({version}). Para actualizar, escribe {update}."),
    "upd.start_offline": (
        "Sem acesso a internet agora: nao consegui conferir se ha versao nova do "
        "TEO. O TEO funciona normalmente; a checagem acontece na proxima abertura.",
        "No internet access right now: I could not check for a new TEO version. "
        "TEO works normally; the check happens on the next start.",
        "Sin acceso a internet ahora: no pude revisar si hay version nueva del TEO. "
        "El TEO funciona normalmente; la revision ocurre en la proxima apertura."),
    "upd.start_unavailable": (
        "Nao consegui conferir a versao nova agora (o GitHub respondeu {code}). "
        "O TEO funciona normalmente.",
        "I could not check for a new version now (GitHub answered {code}). "
        "TEO works normally.",
        "No pude revisar la version nueva ahora (GitHub respondio {code}). "
        "El TEO funciona normalmente."),
}

# ---------------------------------------------------------------------------
# Arquivos (tools/files.py): o que o usuario le na tela (listagem, menu, foto)
# ---------------------------------------------------------------------------
FILES = {
    "files.header": ("pasta: {root}  [{modo}]", "folder: {root}  [{modo}]",
                     "carpeta: {root}  [{modo}]"),
    "files.mode.files": ("so arquivos", "files only", "solo archivos"),
    "files.mode.all": ("pastas e arquivos", "folders and files", "carpetas y archivos"),
    "files.dir_row": ("[DIR] {nome}/", "[DIR] {nome}/", "[DIR] {nome}/"),
    "files.file_row": ("[ARQ] {nome} ({size})", "[FILE] {nome} ({size})",
                       "[ARCH] {nome} ({size})"),
    "files.more": ("... (ainda tem mais; abra uma pasta mais especifica)",
                   "... (there is more; open a more specific folder)",
                   "... (hay mas; abre una carpeta mas especifica)"),
    "files.empty": ("(vazia)", "(empty)", "(vacia)"),
    "files.no_folder": ("Nao encontrei a pasta: {root}", "I could not find the folder: {root}",
                        "No encontre la carpeta: {root}"),
    "files.read_error": ("ERRO ao ler a pasta {root}: {erro}", "ERROR reading the folder {root}: {erro}",
                         "ERROR al leer la carpeta {root}: {erro}"),
    "files.img_missing": ("nao encontrei a imagem: {alvo}", "I could not find the image: {alvo}",
                          "no encontre la imagen: {alvo}"),
    "files.img_ext": ("'{ext}' nao e uma imagem que eu saiba enviar (png, jpg, jpeg, webp, gif, bmp)",
                      "'{ext}' is not an image I know how to send (png, jpg, jpeg, webp, gif, bmp)",
                      "'{ext}' no es una imagen que yo sepa enviar (png, jpg, jpeg, webp, gif, bmp)"),
    "files.img_read": ("nao consegui ler a imagem: {erro}", "I could not read the image: {erro}",
                       "no pude leer la imagen: {erro}"),
    "files.img_big": (
        "a imagem tem {size} - acima de {max} eu nao envio. Diminua a foto ou recorte a "
        "parte que importa.",
        "the image has {size} - above {max} I do not send it. Make the photo smaller or "
        "crop the part that matters.",
        "la imagen tiene {size} - por encima de {max} no la envio. Achica la foto o "
        "recorta la parte que importa."),
}

# ---------------------------------------------------------------------------
# Memoria (tools/memory.py) - o que a pessoa le quando usa /mem
# ---------------------------------------------------------------------------
MEMORY = {
    "mem.empty_text": ("ERRO: memoria vazia", "ERROR: empty memory", "ERROR: memoria vacia"),
    "mem.exists": ("Ja existia essa memoria (nothing added).",
                   "That memory already existed (nothing added).",
                   "Esa memoria ya existia (nada agregado)."),
    "mem.saved": ("Memoria gravada [{target}]: {texto}",
                  "Memory saved [{target}]: {texto}",
                  "Memoria grabada [{target}]: {texto}"),
    "mem.no_query": ("ERRO: informe a palavra-chave", "ERROR: give the keyword",
                     "ERROR: informa la palabra clave"),
    "mem.none": ("Nenhuma memoria contendo '{query}'.",
                 "No memory containing '{query}'.", "Ninguna memoria con '{query}'."),
    "mem.empty_base": ("A memoria esta vazia.", "The memory is empty.",
                       "La memoria esta vacia."),
    "mem.bad_action": ("ERRO: action invalida (use add, search ou list)",
                       "ERROR: invalid action (use add, search or list)",
                       "ERROR: accion invalida (usa add, search o list)"),
}

TEXTS: dict[str, tuple[str, str, str]] = {}
for _bloco in (COMMON, HELP_HEADERS, CHAT, AGENT, GATE, TUI, PALCO, LLM, SETUP, CLI, TOOLS,
               UPDATER, FILES, MEMORY):
    TEXTS.update(_bloco)


def help_table() -> list[tuple[str, list[tuple[str, str]]]]:
    """Ajuda pronta para desenhar: [(cabecalho, [(comando, explicacao), ...]), ...]."""
    i = lang_index()
    saida = []
    for chave_cab, linhas in HELP_SECTIONS:
        saida.append((t(chave_cab), [(l[i], l[3 + i]) for l in linhas]))
    return saida


def lang_options() -> list[str]:
    """Opcoes do menu de idioma, na ordem 1/2/3 (sempre com os tres nomes)."""
    return [LANG_NAMES[c] for c in LANGS]


def lang_from_answer(raw: str) -> str | None:
    """Aceita '1'/'2'/'3', 'pt'/'en'/'es', o nome do idioma ou vazio (-> pt)."""
    texto = (raw or "").strip().lower()
    if not texto:
        return "pt"
    if texto in ("1", "2", "3"):
        return LANGS[int(texto) - 1]
    for codigo, nome in LANG_NAMES.items():
        if texto == codigo or texto.startswith(nome.lower()[:4]):
            return codigo
    for codigo in LANGS:
        if texto.startswith(codigo):
            return codigo
    return None

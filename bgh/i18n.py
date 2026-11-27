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

from datetime import datetime

LANGS = ("pt", "en", "es")
LANG_NAMES = {"pt": "Portugues", "en": "English", "es": "Espanol"}

# Nome do dia da semana por idioma (strftime("%A") depende do locale da maquina,
# que costuma estar em ingles - o modelo receberia "Friday" numa sessao em pt).
WEEKDAYS = {
    "pt": ("segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
           "sexta-feira", "sabado", "domingo"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
           "Sunday"),
    "es": ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
           "domingo"),
}

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
    "new": ("nova", "nov", "new", "nuevo"),
    "mem": ("mem", "memory", "memoria"),
    "skills": ("skills", "habilidades"),
    "site": ("site", "sites", "logins"),
    "zoom": ("zoom", "escala", "scale"),
    "model": ("modelo", "modelos", "model", "models"),
    "provider": ("provedor", "provedores", "provider", "providers",
                 "proveedor", "proveedores"),
    "thinking": ("pensamento", "thinking", "pensamiento"),
    "stage": ("palco", "stage", "escenario"),
    "ctx": ("ctx", "contexto", "context"),
    # Teto de ferramentas por pedido (0 = sem limite). "limite" NAO entra: e a
    # palavra que o pessoal usa para o contexto, e trocar um pelo outro confunde.
    "teto": ("teto", "cap", "tope"),
    "setup": ("configurar", "configure", "setup", "configuracion"),
    "doctor": ("doctor",),
    "update": ("atualizar", "update", "actualizar"),
    "lang": ("lingua", "language", "idioma", "lang"),
    "voice": ("voz", "voice", "voz"),
    "notify": ("aviso", "avisos", "notify", "notificacao", "notificacion"),
    # Buscar/exportar/erro/simples (0.2.52)
    "find": ("buscar", "find", "buscar", "procurar"),
    "export": ("exportar", "export", "exportar", "salvar"),
    "error": ("erro", "error", "erro", "errores"),
    "simple": ("simples", "simple", "sencillo", "facil"),
    "reserve": ("reserva", "reserve", "reserva", "respaldo"),
    "handoff": ("handoff", "passar", "passagem", "continuar-depois"),
    "clean": ("limpar", "clean", "limpiar"),
    "background": ("fundo", "background", "fondo"),
    "font": ("fonte", "font", "fuente"),
    "dictate": ("ditar", "dictate", "dictar"),
    "about": ("sobre", "about", "acerca"),
    # /tela nao e tratado pelo nucleo (quem troca de tela e o cli/tui), mas o id
    # canonico mora aqui: assim /tela, /screen e /pantalla valem nos tres idiomas
    # e a tela do navegador (que cai no nucleo) sabe responder em vez de "nao
    # entendi". "app"/"navegador"/"webapp" sao apelidos antigos, seguem valendo.
    "screen": ("tela", "screen", "pantalla", "app", "navegador", "webapp",
               "browser"),
    # Sessoes guardadas: /novo ARQUIVA em vez de apagar, /sessoes lista e /abrir
    # retoma. Apelidos curtos porque quem usa TEO digita pouco (idoso/crianca).
    "sessions": ("sessoes", "sessions", "sesiones", "historicos", "historico"),
    "open": ("abrir", "open", "abrir", "retomar", "resume"),
}

# Como cada comando aparece ESCRITO na ajuda/avisos, por idioma.
CMD = {
    "exit": ("/sair", "/exit", "/salir"),
    "help": ("/ajuda", "/help", "/ayuda"),
    "new": ("/nova", "/new", "/nuevo"),
    "mem": ("/mem", "/mem", "/mem"),
    "skills": ("/skills", "/skills", "/habilidades"),
    "model": ("/modelo", "/model", "/modelo"),
    "provider": ("/provedor", "/provider", "/proveedor"),
    "thinking": ("/pensamento", "/thinking", "/pensamiento"),
    "stage": ("/palco", "/stage", "/escenario"),
    "ctx": ("/ctx", "/ctx", "/ctx"),
    "teto": ("/teto", "/cap", "/tope"),
    "setup": ("/configurar", "/setup", "/configurar"),
    "doctor": ("/doctor", "/doctor", "/doctor"),
    "update": ("/atualizar", "/update", "/actualizar"),
    "lang": ("/lingua", "/language", "/idioma"),
    "voice": ("/voz", "/voice", "/voz"),
    "notify": ("/aviso", "/notify", "/aviso"),
    "find": ("/buscar", "/find", "/buscar"),
    "export": ("/exportar", "/export", "/exportar"),
    "error": ("/erro", "/error", "/erro"),
    "simple": ("/simples", "/simple", "/sencillo"),
    "reserve": ("/reserva", "/reserve", "/reserva"),
    "handoff": ("/handoff", "/handoff", "/handoff"),
    "clean": ("/limpar", "/clean", "/limpiar"),
    "background": ("/fundo", "/background", "/fondo"),
    "font": ("/fonte", "/font", "/fuente"),
    "dictate": ("/ditar", "/dictate", "/dictar"),
    "about": ("/sobre", "/about", "/acerca"),
    "screen": ("/tela", "/screen", "/pantalla"),
    "site": ("/site", "/site", "/site"),
    "zoom": ("/zoom", "/zoom", "/zoom"),
    "sessions": ("/sessoes", "/sessions", "/sesiones"),
    "open": ("/abrir", "/open", "/abrir"),
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
         "menu de comandos com as setas (digitar filtra); no modo simples, lista a pasta atual",
         "command menu with the arrow keys (type to filter); in simple mode, lists the current folder",
         "menu de comandos con las flechas (escribir filtra); en modo simple, lista la carpeta actual"),
        ("/ <pasta> ou /ls <pasta>", "/ <folder> or /ls <folder>",
         "/ <carpeta> o /ls <carpeta>",
         "lista uma pasta especifica", "lists a specific folder",
         "lista una carpeta especifica"),
        ("@", "@", "@",
         "menu de arquivos da pasta atual, com as setas (ENTER escolhe e ENTER de novo anexa)",
         "file menu of the current folder, with the arrow keys (ENTER picks, ENTER again attaches)",
         "menu de archivos de la carpeta actual, con las flechas (ENTER elige y ENTER otra vez adjunta)"),
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
         "para de responder na hora",
         "stops answering right away",
         "deja de responder al instante"),
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
        ("/nova", "/new", "/nuevo",
         "conversa nova (guarda a atual nas sessoes; memoria e skills continuam)",
         "new conversation (saves the current one in sessions; memory and skills stay)",
         "conversacion nueva (guarda la actual en sesiones; memoria y skills siguen)"),
        ("/sessoes", "/sessions", "/sesiones",
         "conversas guardadas: lista as ultimas com data e assunto",
         "saved conversations: lists the latest with date and subject",
         "conversaciones guardadas: lista las ultimas con fecha y asunto"),
        ("/abrir <numero>", "/open <number>", "/abrir <numero>",
         "volta numa conversa guardada (o numero sai da lista do /sessoes)",
         "goes back to a saved conversation (number comes from the /sessions list)",
         "vuelve a una conversacion guardada (el numero sale de la lista de /sesiones)"),
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
        ("/teto", "/cap", "/tope",
         "teto de ferramentas por pedido (padrao 120); /teto 0 = sem limite, "
         "prorroga enquanto o turno progride",
         "tool cap per request (default 120); /cap 0 = no limit, it extends "
         "while the turn progresses",
         "tope de herramientas por pedido (por defecto 120); /tope 0 = sin limite, "
         "sigue mientras el turno avanza"),
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
        ("/zoom [75|90|100|110|125|auto]", "/zoom [75|90|100|110|125|auto]",
         "/zoom [75|90|100|110|125|auto]",
         "tamanho da tela do navegador; abre a 75% (cabe no notebook) - use "
         "/zoom 100 em tela grande ou /zoom auto",
         "browser screen size; opens at 75% (fits a notebook) - use /zoom 100 "
         "on a large screen or /zoom auto",
         "tamano de la pantalla del navegador; abre al 75% (cabe en el portatil) - "
         "usa /zoom 100 en pantalla grande o /zoom auto"),
        ("/site", "/site", "/site",
         "sites com login: /site mostra o estado, /site abrir <endereco> abre uma "
         "janela do navegador do TEO para VOCE entrar, /site esquecer apaga as sessoes",
         "login sites: /site shows the state, /site open <address> opens a TEO "
         "browser window for YOU to log in, /site forget erases the sessions",
         "sitios con login: /site muestra el estado, /site abrir <direccion> abre "
         "una ventana del navegador del TEO para que TU entres, /site esquecer "
         "borra las sesiones"),
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
        ("/aviso", "/notify", "/aviso",
         "som e notificacao do sistema quando o TEO termina um turno demorado ou "
         "fica esperando sua resposta; digitar de novo desliga",
         "beep and system notification when TEO finishes a long turn or is "
         "waiting for your answer; type it again to turn off",
         "bip y notificacion del sistema cuando el TEO termina un turno largo o "
         "queda esperando tu respuesta; escribirlo otra vez apaga"),
        ("/buscar <palavra>", "/find <word>", "/buscar <palabra>",
         "procura uma palavra na conversa e mostra os trechos (ela mesma, "
         "resumida pelo /exportar)",
         "looks for a word in the conversation and shows the snippets (the "
         "conversation itself, summarized by /export)",
         "busca una palabra en la conversacion y muestra los trozos (la "
         "conversacion misma, resumida por /exportar)"),
        ("/exportar", "/export", "/exportar",
         "salva a conversa em ~/Documentos (texto simples) para mandar a alguem; "
         "aceita um nome: /exportar carta",
         "saves the conversation in ~/Documentos (plain text) to send to someone; "
         "takes a name: /export letter",
         "guarda la conversacion en ~/Documentos (texto simple) para mandarla a "
         "alguien; acepta un nombre: /exportar carta"),
        ("/erro", "/error", "/erro",
         "mostra o ultimo erro tecnico registrado, pronto para copiar e pedir ajuda",
         "shows the last recorded technical error, ready to copy and ask for help",
         "muestra el ultimo error tecnico registrado, listo para copiar y pedir ayuda"),
        ("/simples", "/simple", "/sencillo",
         "tela simples: esconde a trilha do pedido e o nome da ferramenta (para "
         "crianca ou para quem se distrai com muita informacao)",
         "simple screen: hides the request trail and the tool name (for a child or "
         "for anyone distracted by too much information)",
         "pantalla simple: esconde el recorrido del pedido y el nombre de la "
         "herramienta (para ninos o para quien se distrae con mucha informacion)"),
        ("/reserva <numero>", "/reserve <number>", "/reserva <numero>",
         "provedor de reserva: se o principal nao responder, o TEO tenta esse UMA "
         "vez no turno; /reserva off desliga",
         "backup provider: if the main one does not answer, TEO tries this one ONCE "
         "in the turn; /reserve off turns it off",
         "proveedor de reserva: si el principal no responde, el TEO intenta ese UNA "
         "vez en el turno; /reserva off lo apaga"),
        ("/handoff [pasta/nome]", "/handoff [folder/name]", "/handoff [carpeta/nombre]",
         "salva um .md com o que foi feito, onde paramos e os proximos passos, para "
         "continuar em outro dia; sem argumento vai na pasta atual, e voce pode "
         "escolher a pasta e o nome",
         "saves a .md with what was done, where we stopped and the next steps, to "
         "continue another day; with no argument it goes in the current folder, and you "
         "can choose the folder and the name",
         "guarda un .md con lo que se hizo, donde quedamos y los proximos pasos, para "
         "continuar otro dia; sin argumento va en la carpeta actual, y puedes elegir la "
         "carpeta y el nombre"),
        ("/limpar", "/clean", "/limpiar",
         "apaga os rascunhos que o TEO guarda na pasta scratch (scripts, textos "
         "da voz e temporarios) e diz quanto espaco foi liberado; com um tamanho "
         "(/limpar 5GB) muda o aviso de pasta cheia",
         "deletes the drafts TEO keeps in the scratch folder (scripts, voice "
         "texts and temporary files) and reports how much space was freed; with "
         "a size (/clean 5GB) it changes the full-folder warning",
         "borra los borradores que el TEO guarda en la carpeta scratch (scripts, "
         "textos de la voz y temporales) y dice cuanto espacio se libero; con un "
         "tamano (/limpiar 5GB) cambia el aviso de carpeta llena"),
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
        ("/sobre", "/about", "/acerca",
         "quem fez o TEO, por que esse nome e os agradecimentos",
         "who made TEO, why that name and the thanks",
         "quien hizo el TEO, por que ese nombre y los agradecimientos"),
        ("/tela", "/screen", "/pantalla",
         "abre a tela do navegador (no navegador, o botao Terminal traz de volta)",
         "opens the browser screen (inside it, the Terminal button comes back)",
         "abre la pantalla del navegador (dentro de ella, el boton Terminal vuelve)"),
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
    # `/limpar 5GB` nao apaga: muda o tamanho a partir do qual a ABERTURA avisa
    # que a pasta de rascunhos esta cheia (o aviso amarelo do comeco da tela).
    "cmd.clean.set": (
        "Pronto: quando a pasta de rascunhos passar de {gb}, o TEO avisa na "
        "abertura. Para apagar os rascunhos agora: {cmd}.",
        "Done: when the draft folder goes above {gb}, TEO warns at startup. "
        "To delete the drafts now: {cmd}.",
        "Listo: cuando la carpeta de borradores pase de {gb}, el TEO avisa al "
        "abrir. Para borrar los borradores ahora: {cmd}."),
    "cmd.clean.bad": (
        "Nao entendi esse tamanho. Use {cmd} 3GB (ou 5GB, 10GB) para mudar o "
        "aviso, ou {cmd} sozinho para apagar os rascunhos.",
        "I did not understand that size. Use {cmd} 3GB (or 5GB, 10GB) to change "
        "the warning, or {cmd} alone to delete the drafts.",
        "No entendi ese tamano. Usa {cmd} 3GB (o 5GB, 10GB) para cambiar el "
        "aviso, o {cmd} solo para borrar los borradores."),
    "cmd.scratch.aviso": (
        "A pasta de rascunhos do TEO ja tem {size} (o aviso comeca em {gb}). "
        "Use {cmd} para apagar: ali so ha rascunhos - conversa, memoria e skills "
        "ficam em outro lugar.",
        "TEO's draft folder already holds {size} (the warning starts at {gb}). "
        "Use {cmd} to delete them: only drafts live there - conversation, memory "
        "and skills are stored elsewhere.",
        "La carpeta de borradores del TEO ya tiene {size} (el aviso empieza en "
        "{gb}). Usa {cmd} para borrarlos: ahi solo hay borradores - conversacion, "
        "memoria y skills estan en otro lugar."),
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

    "cmd.sobre.title": ("Sobre o TEO", "About TEO", "Sobre el TEO"),
    "cmd.sobre.texto": (
        "Este harness foi criado por Claudinei Villada, inspirado no agente Hermes "
        "e construido para rodar com modelos locais. Recebeu o nome de TEO em "
        "homenagem ao gato dele.",
        "This harness was created by Claudinei Villada, inspired by the Hermes "
        "agent and built to run with local models. It was named TEO in honour of "
        "his cat.",
        "Este harness fue creado por Claudinei Villada, inspirado en el agente "
        "Hermes y hecho para correr con modelos locales. Recibio el nombre de TEO "
        "en homenaje a su gato."),
    "cmd.sobre.agradece": (
        "Agradecimentos a familia e aos amigos.",
        "Thanks to family and friends.",
        "Agradecimientos a la familia y a los amigos."),
    "cmd.sobre.rodape": ("Versao {version} - licenca MIT - {repo}",
                         "Version {version} - MIT license - {repo}",
                         "Version {version} - licencia MIT - {repo}"),

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

    # /aviso: som no terminal + notificacao do sistema quando o TEO para e espera
    # a pessoa (licenca) ou termina um turno demorado.
    "cmd.aviso.on": ("Aviso LIGADO: quando um turno demorar, eu bipo e mostro uma "
                     "notificacao ao terminar - e aviso na hora se ficar esperando "
                     "sua resposta (licenca).",
                     "Alert ON: when a turn takes long I beep and show a "
                     "notification at the end - and I warn you right away if I am "
                     "waiting for your answer (license).",
                     "Aviso ACTIVADO: cuando un turno demore, hago un bip y muestro "
                     "una notificacion al terminar - y aviso enseguida si quedo "
                     "esperando tu respuesta (licencia)."),
    "cmd.aviso.off": ("Aviso desligado: sem som e sem notificacao. As respostas "
                      "continuam na tela normalmente.",
                      "Alert off: no beep and no notification. Answers keep showing "
                      "on screen as usual.",
                      "Aviso desactivado: sin bip y sin notificacion. Las respuestas "
                      "siguen en la pantalla normalmente."),
    "cmd.aviso.bad": ("Use {cmd} para ligar/desligar o aviso (ou {cmd} ligar / "
                      "desligar).",
                      "Use {cmd} to turn the alert on/off (or {cmd} on / off).",
                      "Usa {cmd} para activar/desactivar el aviso (o {cmd} activar / "
                      "desactivar)."),
    # /buscar: achar um trecho na conversa atual (o historico da tela nao e'
    # pesquisavel pelo terminal; a conversa guardada, sim).
    "cmd.find.header": ("Achei {n} trecho(s) com \"{termo}\" (do mais antigo para o "
                        "mais novo):",
                        "Found {n} snippet(s) with \"{termo}\" (oldest first):",
                        "Encontre {n} trozo(s) con \"{termo}\" (del mas antiguo al "
                        "mas nuevo):"),
    "cmd.find.user": ("voce", "you", "tu"),
    "cmd.find.bot": ("TEO", "TEO", "TEO"),
    "cmd.find.tool": ("ferramenta", "tool", "herramienta"),
    "cmd.find.none": ("Nao achei \"{termo}\" nesta conversa.",
                      "I did not find \"{termo}\" in this conversation.",
                      "No encontre \"{termo}\" en esta conversacion."),
    "cmd.find.bad": ("Escreva o que procurar. Exemplo: {cmd} impressora",
                     "Write what to look for. Example: {cmd} printer",
                     "Escribe lo que buscar. Ejemplo: {cmd} impresora"),
    "cmd.find.more": ("(+{n} trechos anteriores nao mostrados)",
                      "(+{n} older snippets not shown)",
                      "(+{n} trozos anteriores no mostrados)"),
    # /exportar: a conversa vira um arquivo de texto para mandar a alguem.
    "cmd.export.header": ("Conversa com o TEO - {quando} - modelo: {modelo}",
                          "Conversation with TEO - {quando} - model: {modelo}",
                          "Conversacion con TEO - {quando} - modelo: {modelo}"),
    "cmd.export.user": ("Voce", "You", "Tu"),
    "cmd.export.bot": ("TEO", "TEO", "TEO"),
    "cmd.export.ok": ("Conversa salva em: {caminho}",
                      "Conversation saved at: {caminho}",
                      "Conversacion guardada en: {caminho}"),
    "cmd.export.empty": ("Nao ha conversa para salvar ainda.",
                         "There is no conversation to save yet.",
                         "No hay conversacion para guardar todavia."),
    "cmd.export.fail": ("Nao consegui escrever o arquivo em {caminho}.",
                        "I could not write the file at {caminho}.",
                        "No pude escribir el archivo en {caminho}."),
    # /erro: o bloco tecnico pronto para copiar e mandar para quem da suporte.
    "cmd.erro.title": ("Ultimo erro registrado ({caminho}):",
                       "Last recorded error ({caminho}):",
                       "Ultimo error registrado ({caminho}):"),
    "cmd.erro.none": ("Nenhum erro registrado ate agora (bom sinal).",
                      "No error recorded so far (good sign).",
                      "Ningun error registrado hasta ahora (buena senal)."),
    "cmd.erro.hint": ("Para pedir ajuda, copie o bloco acima e mande para quem da "
                      "suporte.",
                      "To ask for help, copy the block above and send it to whoever "
                      "supports you.",
                      "Para pedir ayuda, copia el bloque de arriba y mandalo a quien "
                      "te da soporte."),
    # /simples: tela para crianca/idoso - sem trilha do pedido e sem nome da
    # ferramenta; ficam o relogio da espera, o aviso de parar e o medidor.
    "cmd.simples.on": ("Tela simples LIGADA: sem a trilha do pedido e sem o nome da "
                       "ferramenta - so o essencial na tela.",
                       "Simple screen ON: no request trail and no tool name - only "
                       "the essentials.",
                       "Pantalla simple ACTIVADA: sin el recorrido del pedido y sin "
                       "el nombre de la herramienta - solo lo esencial."),
    "cmd.simples.off": ("Tela simples desligada: a trilha e a ferramenta voltam a "
                        "aparecer.",
                        "Simple screen off: the trail and the tool name are back.",
                        "Pantalla simple desactivada: el recorrido y la herramienta "
                        "vuelven a aparecer."),
    "cmd.simples.bad": ("Use {cmd} para ligar/desligar a tela simples (ou {cmd} "
                        "ligar / desligar).",
                        "Use {cmd} to turn the simple screen on/off (or {cmd} on / "
                        "off).",
                        "Usa {cmd} para activar/desactivar la pantalla simple (o "
                        "{cmd} activar / desactivar)."),
    # /reserva: provedor de reserva (troca sozinho quando o principal nao responde).
    "cmd.reserva.show": ("Reserva de provedor: {atual}. Use {cmd} <numero ou nome> "
                         "para escolher e {cmd} off para desligar.",
                         "Backup provider: {atual}. Use {cmd} <number or name> to "
                         "pick one and {cmd} off to turn it off.",
                         "Proveedor de reserva: {atual}. Usa {cmd} <numero o nombre> "
                         "para elegir y {cmd} off para apagar."),
    "cmd.reserva.set": ("Reserva definida: \"{perfil}\". Se o principal nao "
                        "responder, o TEO tenta ele UMA vez no turno e volta ao "
                        "principal no turno seguinte.",
                        "Backup set: \"{perfil}\". If the main one does not answer, "
                        "TEO tries it ONCE in the turn and goes back to the main one "
                        "next turn.",
                        "Reserva definida: \"{perfil}\". Si el principal no responde, "
                        "el TEO lo intenta UNA vez en el turno y vuelve al principal "
                        "en el turno siguiente."),
    "cmd.reserva.off": ("Reserva desligada: o TEO nao troca de provedor sozinho.",
                        "Backup off: TEO does not switch providers by itself.",
                        "Reserva apagada: el TEO no cambia de proveedor solo."),
    "cmd.reserva.bad": ("Nao achei esse perfil. Use {cmd} sozinho para ver a lista.",
                        "I did not find that profile. Use {cmd} alone to see the list.",
                        "No encontre ese perfil. Usa {cmd} solo para ver la lista."),
    "cmd.reserva.empty": ("Nenhum provedor salvo ainda. Configure um segundo com "
                          "{cmd_provedor}.",
                          "No provider saved yet. Set up a second one with "
                          "{cmd_provedor}.",
                          "Ningun proveedor guardado todavia. Configura un segundo "
                          "con {cmd_provedor}."),
    # /handoff: documento de passagem para o dia seguinte (na pasta atual).
    "handoff.pedido": (
        "Voce vai escrever um documento de PASSAGEM DE TURNO (handoff) para a proxima "
        "sessao do TEO, que nao lembra de nada desta conversa. Escreva em markdown, em "
        "portugues simples, com estas secoes e nada mais: '## O que foi feito' (bullets "
        "curtos com o resultado), '## Onde paramos' (o ponto exato em que ficou), "
        "'## Proximos passos' (numerados, um por linha), '## Arquivos e comandos "
        "importantes' (caminhos reais que apareceram), '## Cuidados' (o que NAO repetir, "
        "erros que apareceram e como foram resolvidos). Use so' o que esta na conversa; "
        "nao invente. Responda so' com o documento.",
        "You will write a HANDOFF document for the next TEO session, which remembers "
        "nothing from this conversation. Write in markdown, in plain language, with "
        "these sections and nothing else: '## What was done' (short bullets with the "
        "result), '## Where we stopped' (the exact point), '## Next steps' (numbered, one "
        "per line), '## Important files and commands' (real paths that appeared), "
        "'## Warnings' (what NOT to repeat, errors that showed up and how they were "
        "solved). Use only what is in the conversation; do not invent. Answer only with "
        "the document.",
        "Vas a escribir un documento de PASE DE TURNO para la proxima sesion del TEO, "
        "que no recuerda nada de esta conversacion. Escribe en markdown, en lenguaje "
        "simple, con estas secciones y nada mas: '## Que se hizo' (vinetas cortas con el "
        "resultado), '## Donde quedamos' (el punto exacto), '## Proximos pasos' "
        "(numerados, uno por linea), '## Archivos y comandos importantes' (rutas reales), "
        "'## Cuidados' (que NO repetir, errores que aparecieron y como se resolvieron). "
        "Usa solo lo que esta en la conversacion; no inventes. Responde solo con el "
        "documento."),
    "handoff.titulo": (
        "# Handoff do TEO - {quando}\n\nModelo: {modelo}\nPasta: {pasta}\n\n"
        "Este arquivo foi escrito para continuar o trabalho em outro dia. "
        "Abra o TEO nesta pasta e diga: \"leia {nome} e continue de onde paramos\".",
        "# TEO handoff - {quando}\n\nModel: {modelo}\nFolder: {pasta}\n\n"
        "This file was written to continue the work on another day. "
        "Open TEO in this folder and say: \"read {nome} and continue where we stopped\".",
        "# Handoff del TEO - {quando}\n\nModelo: {modelo}\nCarpeta: {pasta}\n\n"
        "Este archivo fue escrito para continuar el trabajo otro dia. "
        "Abre el TEO en esta carpeta y di: \"lee {nome} y continua donde quedamos\"."),
    "handoff.sem_resumo": (
        "_(O resumo automatico nao saiu; abaixo ficam as perguntas desta conversa.)_",
        "_(The automatic summary failed; below are the questions from this conversation.)_",
        "_(El resumen automatico no salio; abajo quedan las preguntas de esta conversacion.)_"),
    "cmd.handoff.ok": ("Handoff salvo em {caminho}. Amanha, abra o TEO nesta pasta e "
                       "diga: \"leia {nome} e continue de onde paramos\".",
                       "Handoff saved at {caminho}. Tomorrow, open TEO in this folder "
                       "and say: \"read {nome} and continue where we stopped\".",
                       "Handoff guardado en {caminho}. Manana, abre el TEO en esta "
                       "carpeta y di: \"lee {nome} y continua donde quedamos\"."),
    "cmd.handoff.empty": ("Nao ha conversa para passar adiante ainda.",
                          "There is no conversation to hand off yet.",
                          "No hay conversacion para pasar todavia."),
    "cmd.handoff.fail_llm": ("Nao consegui pedir o resumo ao modelo ({erro}). Salvei o "
                             "registro das perguntas da conversa.",
                             "I could not ask the model for the summary ({erro}). I "
                             "saved the record of the conversation questions.",
                             "No pude pedir el resumen al modelo ({erro}). Guarde el "
                             "registro de las preguntas de la conversacion."),
    "cmd.handoff.fail_write": ("Nao consegui escrever o handoff em {caminho} ({erro}).",
                               "I could not write the handoff at {caminho} ({erro}).",
                               "No pude escribir el handoff en {caminho} ({erro})."),

    "cmd.unknown": ("Comando desconhecido. {help} mostra a lista.",
                    "Unknown command. {help} shows the list.",
                    "Comando desconocido. {help} muestra la lista."),
    "cfg.janela": ("Janela maximizada", "Maximized window", "Ventana maximizada"),
    "cli.chat.maximizar": ("abre a janela do terminal maximizada nesta execucao",
                           "opens the terminal window maximized for this run",
                           "abre la ventana del terminal maximizada en esta ejecucion"),
    "cmd.screen.here": ("Voce ja esta na tela do navegador. O botao Terminal "
                        "(no topo) volta para o terminal.",
                        "You are already on the browser screen. The Terminal "
                        "button (top) goes back to the terminal.",
                        "Ya estas en la pantalla del navegador. El boton Terminal "
                        "(arriba) vuelve al terminal."),
    "app.arquivo.nao": ("Documento nao encontrado (ou o TEO nao abre esse tipo de arquivo).",
                        "Document not found (or TEO does not open this file type).",
                        "Documento no encontrado (o el TEO no abre este tipo de archivo)."),
    "app.arquivo.grande": ("Documento grande demais para abrir na tela ({mb} MB). "
                           "Abra pela pasta do computador.",
                           "Document too large to open on screen ({mb} MB). Open it "
                           "from the computer folder.",
                           "Documento demasiado grande para abrir en pantalla ({mb} MB). "
                           "Abrelo desde la carpeta del ordenador."),
    "app.abrir_arquivo": ("abrir o documento em outra janela",
                          "open the document in another window",
                          "abrir el documento en otra ventana"),
    # --- clipe de anexo da tela (v0.2.34) ---------------------------------
    "app.anexar": ("Anexar arquivo ou foto", "Attach file or photo",
                   "Adjuntar archivo o foto"),
    "app.anexar_dica": ("Anexar documento ou foto (PDF, Word, Excel, texto, imagem)",
                        "Attach a document or photo (PDF, Word, Excel, text, image)",
                        "Adjuntar documento o foto (PDF, Word, Excel, texto, imagen)"),
    "app.anexo_remover": ("Remover este anexo", "Remove this attachment",
                          "Quitar este adjunto"),
    "app.anexo_falhou": ("Nao consegui anexar {nome}", "I could not attach {nome}",
                         "No pude adjuntar {nome}"),
    "app.anexo_grande": ("{nome} e grande demais (o limite e {max} MB)",
                         "{nome} is too large (the limit is {max} MB)",
                         "{nome} es demasiado grande (el limite es {max} MB)"),
    "app.anexo_limite": ("No maximo {n} anexos por vez.",
                         "At most {n} attachments at a time.",
                         "Como maximo {n} adjuntos a la vez."),
    "app.anexos": ("anexos", "attachments", "adjuntos"),
    "app.anexo_so": ("(so o anexo, sem texto)", "(attachment only, no text)",
                     "(solo el adjunto, sin texto)"),
    "app.anexo_subindo": ("Espera o anexo terminar de subir.",
                          "Wait for the attachment to finish uploading.",
                          "Espera que el adjunto termine de subir."),
    "cmd.new.done": ("Conversa zerada (memoria e skills preservadas).",
                     "Conversation cleared (memory and skills kept).",
                     "Conversacion reiniciada (memoria y skills conservadas)."),
    # /novo nao apaga mais: ARQUIVA a conversa (v0.2.47). A pessoa pode voltar
    # nela depois - "aquela conversa de ontem" e' o pedido real.
    "cmd.new.saved": ("A conversa anterior ficou guardada. Use {listar} para ver a "
                      "lista e {abrir} <numero> para voltar nela.",
                      "The previous conversation was saved. Use {listar} to see "
                      "the list and {abrir} <number> to go back to it.",
                      "La conversacion anterior quedo guardada. Usa {listar} para "
                      "ver la lista y {abrir} <numero> para volver a ella."),
    "cmd.sessions.title": ("Sessoes guardadas (a mais recente primeiro):",
                           "Saved sessions (newest first):",
                           "Sesiones guardadas (la mas reciente primero):"),
    "cmd.sessions.line": ("[{n}] {data} - {titulo} ({msgs} mensagens)",
                          "[{n}] {data} - {titulo} ({msgs} messages)",
                          "[{n}] {data} - {titulo} ({msgs} mensajes)"),
    "cmd.sessions.none": ("(nenhuma sessao guardada ainda; {cmd} guarda a conversa atual)",
                          "(no session saved yet; {cmd} saves the current conversation)",
                          "(ninguna sesion guardada todavia; {cmd} guarda la conversacion actual)"),
    "cmd.sessions.hint": ("Para retomar uma: {cmd} <numero>.",
                          "To resume one: {cmd} <number>.",
                          "Para retomar una: {cmd} <numero>."),
    "cmd.sessions.untitled": ("(sem assunto)", "(no subject)", "(sin asunto)"),
    "cmd.open.done": ("Sessao de {data} retomada: {titulo} ({msgs} mensagens).",
                      "Session from {data} resumed: {titulo} ({msgs} messages).",
                      "Sesion del {data} retomada: {titulo} ({msgs} mensajes)."),
    "cmd.open.bad": ("Numero invalido. Use {cmd} para ver a lista.",
                     "Invalid number. Use {cmd} to see the list.",
                     "Numero invalido. Usa {cmd} para ver la lista."),
    "cmd.open.miss": ("Nao achei a sessao {n}. Use {cmd} para ver a lista.",
                      "Session {n} not found. Use {cmd} to see the list.",
                      "No encontre la sesion {n}. Usa {cmd} para ver la lista."),
    "cmd.skills.empty": ("(nenhuma skill ainda)", "(no skills yet)",
                         "(ninguna skill todavia)"),
    # /zoom: tamanho da TELA DO NAVEGADOR (v0.2.40). Notebook de 14" corta o
    # rodape em 100%; a 75% cabe inteiro. Fica guardado no config.
    "cmd.zoom.list": ("Tela do navegador em {atual}%. Opcoes: 75, 90, 100, 110 ou "
                      "125. Use {cmd} <numero> - fica guardado para as proximas "
                      "aberturas.",
                      "Browser screen at {atual}%. Options: 75, 90, 100, 110 or 125. "
                      "Use {cmd} <number> - it is saved for the next openings.",
                      "Pantalla del navegador al {atual}%. Opciones: 75, 90, 100, 110 o "
                      "125. Usa {cmd} <numero> - queda guardado para las proximas "
                      "aperturas."),
    "cmd.zoom.list_auto": ("Tela do navegador em AUTOMATICO: 75% em janela baixa "
                           "(notebook) e 100% em tela grande. Opcoes: {cmd} 75, 90, "
                           "100, 110, 125 - ou {cmd} auto para voltar ao automatico.",
                           "Browser screen on AUTOMATIC: 75% on a short window "
                           "(notebook) and 100% on a large screen. Options: {cmd} 75, "
                           "90, 100, 110, 125 - or {cmd} auto to go back to automatic.",
                           "Pantalla del navegador en AUTOMATICO: 75% en ventana baja "
                           "(portatil) y 100% en pantalla grande. Opciones: {cmd} 75, "
                           "90, 100, 110, 125 - o {cmd} auto para volver al automatico."),
    "cmd.zoom.auto_now": ("Tela do navegador de volta ao AUTOMATICO (75% em janela "
                          "baixa, 100% em tela grande).",
                          "Browser screen back to AUTOMATIC (75% on a short window, "
                          "100% on a large screen).",
                          "Pantalla del navegador de vuelta al AUTOMATICO (75% en "
                          "ventana baja, 100% en pantalla grande)."),
    "cmd.zoom.now": ("Tela do navegador agora em {atual}% (guardado). Se a tela ja "
                     "estiver aberta, ela se ajusta em ate 12 segundos.",
                     "Browser screen now at {atual}% (saved). If the screen is already "
                     "open it adjusts within 12 seconds.",
                     "Pantalla del navegador ahora al {atual}% (guardado). Si ya esta "
                     "abierta se ajusta en hasta 12 segundos."),
    "cmd.zoom.bad": ("Escolha 75, 90, 100, 110 ou 125. Exemplo: {cmd} 75.",
                     "Choose 75, 90, 100, 110 or 125. Example: {cmd} 75.",
                     "Elige 75, 90, 100, 110 o 125. Ejemplo: {cmd} 75."),
    "cmd.zoom.terminal": ("O {cmd} vale para a tela do navegador. No terminal, o "
                          "tamanho da letra e o {fonte}.",
                          "{cmd} applies to the browser screen. In the terminal the "
                          "letter size is {fonte}.",
                          "{cmd} vale para la pantalla del navegador. En el terminal el "
                          "tamano de la letra es {fonte}."),
    # /site: navegador proprio do TEO para site com login (v0.2.39).
    "cmd.site.status_vazio": (
        "Nenhum login guardado no navegador do TEO. Para entrar num site: {cmd} "
        "abrir <endereco> - a janela abre, VOCE entra com a sua conta e DEIXA a janela "
        "aberta; eu leio a aba ja logada.",
        "No login stored in the TEO browser. To log in to a site: {cmd} open "
        "<address> - the window opens, YOU sign in with your account and LEAVE it open; "
        "I read the logged-in tab.",
        "Ningun inicio de sesion guardado en el navegador del TEO. Para entrar en un "
        "sitio: {cmd} abrir <direccion> - la ventana se abre, TU entras con tu cuenta y "
        "DEJAS la ventana abierta; yo leo la pestana con sesion."),
    "cmd.site.status_janela": (
        "A janela do navegador do TEO esta ABERTA com {n} aba(s): {urls}. Eu leio a aba "
        "logada quando voce pedir. Para fechar: {cmd} fechar.",
        "The TEO browser window is OPEN with {n} tab(s): {urls}. I read the logged-in tab "
        "when you ask. To close it: {cmd} close.",
        "La ventana del navegador del TEO esta ABIERTA con {n} pestana(s): {urls}. Leo la "
        "pestana con sesion cuando lo pidas. Para cerrar: {cmd} cerrar."),
    "cmd.site.fechar_ok": (
        "Fechei a janela do navegador do TEO.",
        "I closed the TEO browser window.",
        "Cerre la ventana del navegador del TEO."),
    "cmd.site.fechar_nada": (
        "Nao havia janela do TEO aberta.",
        "There was no TEO window open.",
        "No habia ninguna ventana del TEO abierta."),
    "cmd.site.status": (
        "O navegador do TEO tem {n} arquivo(s) de sessao guardados. Isso permite ler "
        "os sites em que voce entrou, sem precisar da tela aberta. Para apagar tudo: "
        "{cmd} esquecer.",
        "The TEO browser has {n} session file(s) stored. That lets me read the sites "
        "you logged in to without the screen being open. To erase everything: "
        "{cmd} forget.",
        "El navegador del TEO tiene {n} archivo(s) de sesion guardados. Eso permite "
        "leer los sitios en los que entraste sin necesitar la pantalla abierta. Para "
        "borrar todo: {cmd} esquecer."),
    "cmd.site.esquecer_ok": (
        "Sessoes apagadas ({n} arquivo(s)). O TEO nao abre mais nenhum site logado "
        "ate voce entrar de novo.",
        "Sessions erased ({n} file(s)). TEO will not open any logged-in site until "
        "you sign in again.",
        "Sesiones borradas ({n} archivo(s)). El TEO no abre mas ningun sitio con "
        "sesion hasta que entres de nuevo."),
    "cmd.site.nada": ("Nao havia sessao guardada para apagar.",
                      "There was no stored session to erase.",
                      "No habia sesion guardada para borrar."),
    "cmd.site.abrir": (
        "Abri uma janela do navegador do TEO em {url}. Entre na sua conta (a senha e "
        "sua) e DEIXE A JANELA ABERTA - eu leio a aba ja logada, sem precisar fechar "
        "nada. Se o site oferecer \"manter conectado\", marque tambem.",
        "I opened a TEO browser window at {url}. Sign in with your account (the "
        "password is yours) and LEAVE THE WINDOW OPEN - I read the logged-in tab, no "
        "need to close anything. If the site offers \"keep me signed in\", tick it too.",
        "Abri una ventana del navegador del TEO en {url}. Entra con tu cuenta (la "
        "contrasena es tuya) y DEJA LA VENTANA ABIERTA - leo la pestana con sesion, sin "
        "cerrar nada. Si el sitio ofrece \"mantener la sesion\", marcalo tambien."),
    "cmd.site.abrir_falhou": (
        "Nao consegui abrir a janela do navegador: {erro}",
        "I could not open the browser window: {erro}",
        "No pude abrir la ventana del navegador: {erro}"),
    "cmd.site.safari": (
        "No Mac o TEO usa o SEU Safari, que ja esta logado: abra a pagina no Safari, "
        "entre na conta e me peca para ler a aba aberta (o ver_pagina com origem=aba). "
        "Nao precisa perfil separado nem fechar janela. Se eu disser que nao consegui "
        "ler a pagina, ligue em Safari > Preferencias > Avancado > 'Mostrar recursos "
        "de desenvolvimento' e, no menu Desenvolvedor, 'Permitir JavaScript de "
        "eventos da Apple'.",
        "On a Mac TEO uses YOUR Safari, already logged in: open the page in Safari, "
        "sign in and ask me to read the open tab (ver_pagina with origem=tab). No "
        "separate profile and no need to close anything. If I say I could not read "
        "the page, enable Safari > Preferences > Advanced > 'Show features for web "
        "developers' and then Develop menu > 'Allow JavaScript from Apple Events'.",
        "En Mac el TEO usa TU Safari, ya con sesion: abre la pagina en Safari, entra "
        "y pide que lea la pestana abierta (ver_pagina con origen=pestana). Sin perfil "
        "separado y sin cerrar nada. Si digo que no pude leer la pagina, activa Safari "
        "> Preferencias > Avanzado > 'Mostrar funciones para desarrolladores web' y en "
        "el menu Desarrollo, 'Permitir JavaScript de eventos de Apple'."),
    "cmd.site.uso": (
        "Use: {cmd} (estado do navegador), {cmd} abrir <endereco do site>, "
        "{cmd} fechar (fecha a janela do TEO), {cmd} esquecer (apaga as sessoes "
        "guardadas).",
        "Use: {cmd} (browser state), {cmd} open <site address>, {cmd} close (closes "
        "the TEO window), {cmd} forget (erases the stored sessions).",
        "Usa: {cmd} (estado del navegador), {cmd} abrir <direccion del sitio>, "
        "{cmd} cerrar (cierra la ventana del TEO), {cmd} esquecer (borra las sesiones "
        "guardadas)."),
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
    "cmd.teto.show": (
        "Limite por pedido: o TEO pode dar ate {teto} passos antes de pedir para "
        "voce continuar. 0 = sem limite. Para mudar, escreva {cmd} 60 (60 passos) "
        "ou {cmd} 0 (sem limite).",
        "Limit per request: TEO may take up to {teto} steps before asking you to "
        "continue. 0 = no limit. To change it, write {cmd} 60 (60 steps) or "
        "{cmd} 0 (no limit).",
        "Limite por pedido: el TEO puede dar hasta {teto} pasos antes de pedirte "
        "que sigas. 0 = sin limite. Para cambiar, escribe {cmd} 60 (60 pasos) "
        "o {cmd} 0 (sin limite)."),
    "cmd.teto.set": (
        "Pronto: agora o TEO pode dar ate {teto} passos por pedido. Vale no proximo "
        "pedido.",
        "Done: TEO may now take up to {teto} steps per request. It applies on the "
        "next request.",
        "Listo: ahora el TEO puede dar hasta {teto} pasos por pedido. Vale en el "
        "proximo pedido."),
    "cmd.teto.no_wall": (
        "Pronto: agora NAO tem limite de passos por pedido. Pode demorar bastante; "
        "se quiser parar, aperte ESC (ou CTRL+C). Vale no proximo pedido.",
        "Done: there is NO step limit per request now. It can take a long while; "
        "to stop, press ESC (or CTRL+C). It applies on the next request.",
        "Listo: ahora NO hay limite de pasos por pedido. Puede demorar bastante; "
        "si quieres parar, pulsa ESC (o CTRL+C). Vale en el proximo pedido."),
    "cmd.teto.bad": (
        "Nao entendi esse numero. Escreva {cmd} 60 para 60 passos, ou {cmd} 0 para "
        "nao ter limite.",
        "I did not understand that number. Write {cmd} 60 for 60 steps, or {cmd} 0 "
        "for no limit.",
        "No entendi ese numero. Escribe {cmd} 60 para 60 pasos, o {cmd} 0 para no "
        "tener limite."),
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
    # Menu com SETAS (@ e / enquanto se digita): cabecalho, vazio e a dica na barra.
    "menu.pasta": ("Pasta: {pasta}", "Folder: {pasta}", "Carpeta: {pasta}"),
    "menu.comandos": ("Comandos (setas e ENTER; digitar filtra):",
                      "Commands (arrows and ENTER; type to filter):",
                      "Comandos (flechas y ENTER; escribir filtra):"),
    "menu.pasta_vazia": ("(pasta vazia)", "(empty folder)", "(carpeta vacia)"),
    "menu.vazio": ("(nada aqui com \"{filtro}\")", "(nothing here matching \"{filtro}\")",
                   "(nada aqui con \"{filtro}\")"),
    "menu.sem_comando": ("(nenhum comando com \"{filtro}\"; ENTER envia a linha assim mesmo)",
                         "(no command with \"{filtro}\"; ENTER sends the line anyway)",
                         "(ningun comando con \"{filtro}\"; ENTER envia la linea igual)"),
    "menu.hint": ("setas: escolher | ENTER: pegar/entrar | ESC: fechar | digitar: filtrar",
                  "arrows: choose | ENTER: pick/enter | ESC: close | type: filter",
                  "flechas: elegir | ENTER: tomar/entrar | ESC: cerrar | escribir: filtrar"),

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
    # --- anexos que a pessoa entrega (v0.2.34) ----------------------------
    # Falam do ARQUIVO, nao da tela: servem para o clipe do navegador e para o
    # '@' do terminal, com a mesma frase nos dois.
    "anexo.tipo": ("Nao consigo ler arquivo {ext}. Aceito imagem, PDF, Word, "
                   "Excel, PowerPoint e texto.",
                   "I cannot read {ext} files. I accept image, PDF, Word, Excel, "
                   "PowerPoint and text.",
                   "No puedo leer archivos {ext}. Acepto imagen, PDF, Word, Excel, "
                   "PowerPoint y texto."),
    "anexo.grande": ("O arquivo {nome} tem {size} MB e o limite e {max} MB.",
                     "{nome} has {size} MB and the limit is {max} MB.",
                     "El archivo {nome} tiene {size} MB y el limite es {max} MB."),
    "anexo.vazio": ("O arquivo {nome} esta vazio.", "{nome} is empty.",
                    "El archivo {nome} esta vacio."),
    "anexo.falhou": ("Nao consegui ler {nome}.", "I could not read {nome}.",
                     "No pude leer {nome}."),
    "anexo.nao_achei": ("O anexo {nome} nao esta mais aqui. Mande de novo.",
                        "The attachment {nome} is no longer here. Send it again.",
                        "El adjunto {nome} ya no esta aqui. Mandalo de nuevo."),
    "anexo.cortado": (" (arquivo grande: mandei o comeco)",
                      " (large file: I sent the beginning)",
                      " (archivo grande: mande el comienzo)"),
    "anexo.sem_texto": ("Nao achei texto em {nome} (pode ser digitalizado ou "
                        "protegido por senha).",
                        "I found no text in {nome} (it may be scanned or "
                        "password protected).",
                        "No encontre texto en {nome} (puede estar escaneado o "
                        "protegido con contrasena)."),
    "anexo.pdf_lib": ("Para ler PDF falta uma biblioteca (pypdf). Rode {atualizar} "
                      "ou instale com pip install pypdf.",
                      "Reading PDF needs a library (pypdf). Run {atualizar} or "
                      "install it with pip install pypdf.",
                      "Para leer PDF falta una biblioteca (pypdf). Ejecuta "
                      "{atualizar} o instalala con pip install pypdf."),
    "anexo.imagem": ("{nome} e imagem: vai para a visao do modelo, nao como texto.",
                     "{nome} is an image: it goes to the model vision, not as text.",
                     "{nome} es imagen: va a la vision del modelo, no como texto."),
    "anexo.antigo": ("O formato {ext} e antigo e nao tem extrator aqui. Abra no "
                     "programa e salve como .docx, .xlsx ou .pptx.",
                     "The {ext} format is old and has no extractor here. Open it in "
                     "the program and save as .docx, .xlsx or .pptx.",
                     "El formato {ext} es antiguo y no tiene extractor aqui. Abrelo "
                     "en el programa y guardalo como .docx, .xlsx o .pptx."),
    "anexo.limite": ("Muitos anexos de uma vez: mandei os {n} primeiros.",
                     "Too many attachments at once: I sent the first {n}.",
                     "Demasiados adjuntos a la vez: mande los primeros {n}."),
    "anexo.perdido": ("Um dos anexos se perdeu (a tela recarregou?). Mande de novo.",
                      "One of the attachments was lost (page reloaded?). Send it "
                      "again.",
                      "Uno de los adjuntos se perdio (se recargo la pantalla?). "
                      "Mandalo de nuevo."),
    "anexo.ok": ("Anexo: {nome} ({size}).", "Attachment: {nome} ({size}).",
                 "Adjunto: {nome} ({size})."),
    "anexo.ocupado": ("O TEO esta trabalhando agora: mande o anexo junto com o "
                      "proximo pedido.",
                      "TEO is working right now: send the attachment with your next "
                      "request.",
                      "El TEO esta trabajando ahora: manda el adjunto con el proximo "
                      "pedido."),
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
    # Linha que vai JUNTO da mensagem da pessoa, em cada turno: e' assim que o
    # modelo sabe que dia e' hoje (o prompt do sistema e' montado uma vez so' na
    # sessao e envelhece). Fica curta de proposito: entra no texto do usuario,
    # que ja muda a cada turno, entao nao custa cache de contexto no servidor.
    "agent.now_line": ("(AGORA: {quando})", "(NOW: {quando})", "(AHORA: {quando})"),
    # Memorias antigas que combinam com o pedido atual: vao na mesma linha do
    # pedido, para uma preferencia de semanas atras voltar quando o assunto surge.
    "agent.mem_block": ("(MEMORIAS QUE JA SEI E QUE COMBINAM COM O PEDIDO: {itens})",
                        "(MEMORIES I ALREADY HAVE THAT MATCH THIS REQUEST: {itens})",
                        "(MEMORIAS QUE YA SE Y QUE ENCAJAN CON EL PEDIDO: {itens})"),
    # Cabecalho do pedido LITERAL que fica na frente do resumo da compactacao.
    "agent.pinned_header": ("PEDIDO ATUAL DA PESSOA (literal, continua valendo):",
                            "CURRENT REQUEST FROM THE PERSON (verbatim, still applies):",
                            "PEDIDO ACTUAL DE LA PERSONA (literal, sigue valiendo):"),
    # Reserva de provedor (/reserva): o TEO troca sozinho quando o principal nao
    # responde. A tela diz o que aconteceu - nunca troca calado.
    "agent.fallback_on": ("Nao consegui falar com {modelo} ({motivo}). Tentando pelo "
                          "perfil de reserva \"{perfil}\".",
                          "I could not talk to {modelo} ({motivo}). Trying the backup "
                          "profile \"{perfil}\".",
                          "No pude hablar con {modelo} ({motivo}). Intentando por el "
                          "perfil de reserva \"{perfil}\"."),
    "agent.fallback_back": ("De volta ao provedor principal: {modelo}.",
                            "Back to the main provider: {modelo}.",
                            "De vuelta al proveedor principal: {modelo}."),
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
    "agent.tool_image": ("Print da tela que a ferramenta acabou de tirar ({n}). "
                         "Olhe a imagem junto com o texto da pagina.",
                         "Screenshot just taken by the tool ({n}). Look at the image "
                         "together with the page text.",
                         "Captura que la herramienta acaba de hacer ({n}). Mira la "
                         "imagen junto con el texto de la pagina."),
    "agent.image_more": ("So {n} imagem(ns) vao para o modelo por turno; as outras "
                         "ficaram de fora.",
                         "Only {n} image(s) go to the model per turn; the others were "
                         "left out.",
                         "Solo {n} imagen(es) van al modelo por turno; las otras "
                         "quedaron fuera."),
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
        "Ja usei {limite} passos neste pedido; posso seguir por mais {extra} "
        "(CTRL+C ou ESC para parar).",
        "I already used {limite} steps in this request; I can go on for {extra} more "
        "(CTRL+C or ESC to stop).",
        "Ya use {limite} pasos en este pedido; puedo seguir por {extra} mas "
        "(CTRL+C o ESC para parar)."),
    # A tarefa NAO terminou: o texto nao pode soar como entrega pronta (era assim que
    # o modelo devolvia laudo/relatorio acabado com buraco preenchido por invencao).
    "agent.max_note": (
        "Parei em {limite} passos porque este pedido e grande e o trabalho NAO "
        "terminou. Nada se perdeu: escreva continuar que eu sigo de onde parei.",
        "I stopped at {limite} steps because this request is big and the work is NOT "
        "done. Nothing was lost: write continue and I go on from where I stopped.",
        "Pare en {limite} pasos porque este pedido es grande y el trabajo NO "
        "termino. No se perdio nada: escribe continuar y sigo desde donde pare."),
    "agent.close_teto": (
        "(voce chegou ao teto de {limite} ferramentas deste turno e a tarefa NAO "
        "terminou. Responda {lang}, em no maximo 12 linhas: 1) o que ja foi feito e "
        "provado; 2) o que falta e qual e o proximo passo. Nao escreva o documento final, "
        "nao preencha dado que voce nao "
        "coletou e nao prometa acao futura; termine dizendo que o usuario pode escrever "
        "'continuar' para voce seguir de onde parou.)",
        "(you reached the cap of {limite} tools in this turn and the task is NOT done. "
        "Answer {lang} in at most 12 lines: 1) what is already done and proven; 2) what "
        "is missing and the next step. Do not write the final document, do not fill in data "
        "you did not collect and do "
        "not promise future action; end by saying the user can write 'continue' so you go "
        "on from where you stopped.)",
        "(llegaste al tope de {limite} herramientas de este turno y la tarea NO termino. "
        "Responde {lang}, en no mas de 12 lineas: 1) lo que ya esta hecho y probado; 2) lo "
        "que falta y el proximo paso. No escribas el documento final, no rellenes dato que no "
        "recogiste y no prometas "
        "accion futura; termina diciendo que el usuario puede escribir 'continua' para que "
        "sigas desde donde paraste.)"),
    # Marcado pelo HARNESS, na frente do texto: instrucao a modelo pequeno nao garante
    # que o aviso apareca - e essa e a diferenca entre "relatorio" e "entrega parcial".
    "agent.partial_banner": (
        "AINDA NAO ESTA PRONTO: parei no limite de {limite} passos deste pedido. "
        "Escreva continuar que eu sigo de onde parei.",
        "NOT DONE YET: I stopped at the {limite} step limit of this request. Write "
        "continue and I go on from where I stopped.",
        "TODAVIA NO ESTA LISTO: pare en el limite de {limite} pasos de este pedido. "
        "Escribe continuar y sigo desde donde pare."),
    "agent.round_note": (
        "Cheguei no limite de passos deste pedido e o trabalho nao terminou; vou te "
        "contar onde parei.",
        "I reached this request step limit and the work is not done; I will tell you "
        "where I stopped.",
        "Llegue al limite de pasos de este pedido y el trabajo no termino; te cuento "
        "donde pare."),
    "agent.close_round": (
        "(limite de ferramentas deste turno atingido e o trabalho NAO terminou. Responda "
        "{lang} em no maximo 12 linhas usando apenas o que ja foi coletado: o que esta "
        "feito, o que falta e o proximo passo. Nao escreva documento final, nao preencha "
        "dado que voce nao coletou e nao prometa acao futura.)",
        "(tool limit for this turn reached and the work is NOT done. Answer {lang} in at "
        "most 12 lines using only what was already collected: what is done, what is "
        "missing and the next step. Do not write the final document, do not fill in data "
        "you did not collect and do not promise future action.)",
        "(limite de herramientas de este turno alcanzado y el trabajo NO termino. Responde "
        "{lang} en no mas de 12 lineas usando solo lo que ya se recogio: lo que esta "
        "hecho, lo que falta y el proximo paso. No escribas documento final, no rellenes "
        "dato que no recogiste y no prometas accion futura.)"),
    "agent.retry_empty": ("O modelo respondeu sem texto (gastou a saida pensando); "
                          "tentando de novo com menos pensamento...",
                          "The model answered without text (it spent the output "
                          "thinking); trying again with less thinking...",
                          "El modelo respondio sin texto (gasto la salida pensando); "
                          "intentando de nuevo con menos pensamiento..."),
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
    # Caso real medido (17/11): conversa com 150+ mensagens e uma foto. A foto FOI
    # enviada (o session.json prova), mas o servidor local descartou a imagem e o
    # modelo respondeu "nao chegou imagem". Duas medidas: compactar antes de mandar
    # foto (agent._abrir_espaco_para_imagem) e dizer a verdade quando isso escapar.
    "agent.compressed_for_image": ("Conversa longa: resumi o comeco para a imagem caber "
                                   "no contexto do modelo.",
                                   "Long conversation: I summarized the beginning so the "
                                   "image fits in the model context.",
                                   "Conversacion larga: resumi el comienzo para que la "
                                   "imagen quepa en el contexto del modelo."),
    "agent.image_lost": ("A imagem foi enviada junto do pedido; se o modelo disse que nao "
                         "viu, o servidor descartou a foto (contexto cheio). Tente {nova} e "
                         "mande a foto de novo.",
                         "The image was sent with your request; if the model said it did not "
                         "see it, the server dropped the photo (context full). Try {nova} and "
                         "send the photo again.",
                         "La imagen se envio con el pedido; si el modelo dijo que no la vio, "
                         "el servidor descarto la foto (contexto lleno). Prueba {nova} y "
                         "manda la foto de nuevo."),
    "agent.summary_fallback": ("(partes antigas da conversa foram removidas por limite de "
                               "contexto)",
                               "(old parts of the conversation were removed by the context "
                               "limit)",
                               "(las partes viejas de la conversacion se quitaron por el "
                               "limite de contexto)"),
    "agent.summary_header": ("RESUMO DA CONVERSA ANTERIOR:\n",
                             "SUMMARY OF THE PREVIOUS CONVERSATION:\n",
                             "RESUMEN DE LA CONVERSACION ANTERIOR:\n"),
    # O resumo pode perder numero/medida. Estes dois textos existem para o dado nao
    # sumir calado: trechos LITERAIS dos resultados de ferramenta voltam junto.
    "agent.data_header": ("DADOS COLETADOS ANTES DO RESUMO (trechos literais):",
                          "DATA COLLECTED BEFORE THE SUMMARY (verbatim excerpts):",
                          "DATOS RECOGIDOS ANTES DEL RESUMEN (trozos literales):"),
    "agent.data_cut": ("(+{n} resultado(s) de ferramenta nao couberam por tamanho)",
                       "(+{n} tool result(s) did not fit for size)",
                       "(+{n} resultado(s) de herramienta no cupieron por tamano)"),
    "agent.summary_guard": ("Dado coletado antes deste resumo pode ter ficado incompleto: "
                            "se faltar informacao, diga que faltou; NUNCA complete de "
                            "memoria.",
                            "Data collected before this summary may be incomplete: if "
                            "information is missing, say it is missing; NEVER fill it in "
                            "from memory.",
                            "Dato recogido antes de este resumen puede haber quedado "
                            "incompleto: si falta informacion, di que falto; NUNCA "
                            "completes de memoria."),
    "agent.ctx_stuck": ("A conversa ficou grande demais e nao deu para encurtar mais. "
                        "Segui com ela assim. Se aparecer erro de tamanho, use {ctx} "
                        "para diminuir ou {new} para comecar uma conversa nova.",
                        "The conversation got too big and could not be shortened any "
                        "further. I went on with it like this. If a size error shows up, "
                        "use {ctx} to make it smaller or {new} to start a new "
                        "conversation.",
                        "La conversacion se hizo demasiado grande y no se pudo acortar "
                        "mas. Segui con ella asi. Si aparece un error de tamano, usa {ctx} "
                        "para achicarla o {new} para empezar una conversacion nueva."),
    "agent.budget_notice": (
        "[AVISO DO SISTEMA - orcamento do turno] Voce ja usou {usadas} de {teto} "
        "ferramentas deste turno. Anote agora o progresso (o que esta feito, o que falta e "
        "o proximo passo) e CONTINUE a tarefa; nao pare so por causa deste aviso.",
        "[SYSTEM NOTICE - turn budget] You have used {usadas} of {teto} tools in this turn. "
        "Checkpoint the progress now (what is done, what is missing and the next step) and "
        "CONTINUE the task; do not stop solely because of this warning.",
        "[AVISO DEL SISTEMA - presupuesto del turno] Ya usaste {usadas} de {teto} "
        "herramientas de este turno. Anota ahora el progreso (lo que esta hecho, lo que "
        "falta y el proximo paso) y SIGUE la tarea; no pares solo por este aviso."),
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
    # Print da tela (ver_tela): a frase tem que dizer o risco em linguagem de gente.
    "gate.tela_label": ("Tirar um print da sua tela", "Take a screenshot of your screen",
                        "Tomar una captura de tu pantalla"),
    "gate.tela_detail": (
        "O TEO vai fotografar TUDO o que estiver aberto na sua tela agora - pode "
        "aparecer e-mail, conversa ou documento que voce nao quer mostrar. A imagem "
        "vai junto do seu pedido para o modelo ler.\n"
        "Mostre so o que quiser: feche o resto ou clique na janela certa e peca de novo.",
        "TEO will capture EVERYTHING open on your screen right now - email, chats or "
        "documents you may not want to show could appear. The image goes with your "
        "request for the model to read.\n"
        "Show only what you want: close the rest or click the right window and ask again.",
        "El TEO va a capturar TODO lo que este abierto en tu pantalla ahora - puede "
        "aparecer correo, conversacion o documento que no quieres mostrar. La imagen "
        "va con tu pedido para que el modelo la lea.\n"
        "Muestra solo lo que quieras: cierra el resto o haz clic en la ventana correcta "
        "y pide de nuevo."),
    "gate.tela_denied": (
        "BLOQUEADO: a pessoa nao autorizou o print da tela. Sem a imagem, peca para ela "
        "tirar um print e anexar no clipe, ou descrever o que aparece.",
        "BLOCKED: the person did not allow the screenshot. Without the image, ask them to "
        "take a screenshot and attach it, or describe what is on screen.",
        "BLOQUEADO: la persona no autorizo la captura. Sin la imagen, pide que haga una "
        "captura y la adjunte, o que describa lo que aparece."),
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
    # Aviso com som + notificacao do sistema: e' o unico sinal para quem saiu da
    # frente da tela (turno demorado / licenca esperando resposta).
    "tui.done_title": ("TEO terminou", "TEO finished", "TEO termino"),
    "tui.done_body": ("A resposta esta pronta (depois de {s}s). Volte para a tela "
                      "para ler.",
                      "The answer is ready (after {s}s). Come back to the screen "
                      "to read it.",
                      "La respuesta esta lista (despues de {s}s). Vuelve a la "
                      "pantalla para leerla."),
    "tui.need_you_title": ("TEO esta esperando voce", "TEO is waiting for you",
                           "TEO esta esperando por ti"),
    "tui.need_you_body": ("Preciso da sua resposta para continuar: {label}",
                          "I need your answer to continue: {label}",
                          "Necesito tu respuesta para continuar: {label}"),
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
    # Rede/servidor fora do ar: frase de gente (o tecnico vai para o erro.log).
    "llm.offline": (
        "Nao consegui falar com o servidor do modelo em {url}. Confira se ele esta "
        "ligado (no modelo local, o llama.cpp/LM Studio) ou se a internet esta "
        "funcionando, e mande a pergunta de novo.",
        "I could not reach the model server at {url}. Check that it is running (for "
        "a local model, llama.cpp/LM Studio) or that the internet works, then send "
        "the question again.",
        "No pude hablar con el servidor del modelo en {url}. Revisa que este "
        "encendido (en modelo local, llama.cpp/LM Studio) o que la internet "
        "funcione, y manda la pregunta otra vez."),
    # Repeticao automatica de uma falha passageira (ver LLM._pedido).
    "llm.retry": ("O servidor do modelo nao respondeu; tentando de novo "
                  "(tentativa {n} de {total}).",
                  "The model server did not answer; trying again (attempt {n} of "
                  "{total}).",
                  "El servidor del modelo no respondio; intentando otra vez "
                  "(intento {n} de {total})."),
    "llm.server_error": (
        "O servidor do modelo esta com problema agora (erro {code}). Costuma ser "
        "passageiro: mande a pergunta de novo em alguns segundos.",
        "The model server has a problem right now (error {code}). It is usually "
        "temporary: send the question again in a few seconds.",
        "El servidor del modelo tiene un problema ahora (error {code}). Suele ser "
        "pasajero: manda la pregunta otra vez en unos segundos."),
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
        "Resuma a conversa abaixo em no maximo 30 pontos curtos. Preserve "
        "LITERALMENTE: numeros, medidas, datas, nomes, trechos citados, caminhos de "
        "arquivo, decisoes tomadas, erros encontrados e pedidos ainda abertos. No fim, "
        "sob a linha 'DADOS:', liste cada dado coletado por ferramenta (valor medido, "
        "texto citado) sem arredondar e sem trocar numero por adjetivo. Responda so com "
        "o resumo.",
        "Summarize the conversation below in at most 30 short points. Keep VERBATIM: "
        "numbers, measurements, dates, names, quoted excerpts, file paths, decisions "
        "taken, errors found and requests still open. At the end, under the line 'DATA:', "
        "list every piece of data collected by a tool (measured value, quoted text) "
        "without rounding and without trading a number for an adjective. Answer only with "
        "the summary.",
        "Resume la conversacion abajo en maximo 30 puntos cortos. Conserva LITERALMENTE: "
        "numeros, medidas, fechas, nombres, trozos citados, caminos de archivo, decisiones "
        "tomadas, errores encontrados y pedidos aun abiertos. Al final, bajo la linea "
        "'DATOS:', lista cada dato recogido por herramienta (valor medido, texto citado) "
        "sin redondear y sin cambiar numero por adjetivo. Responde solo con el resumen."),
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
    "cli.tui_fail": ("Esta janela nao aceitou a tela fixa; sigo no modo simples "
                     "(rolagem), que funciona igual. Para voltar a tela fixa, abra o "
                     "TEO numa janela maior ou no Windows Terminal.",
                     "This window did not accept the fixed screen; I go on in the "
                     "simple (scrolling) mode, which works the same. To get the fixed "
                     "screen back, open TEO in a larger window or in Windows Terminal.",
                     "Esta ventana no acepto la pantalla fija; sigo en el modo simple "
                     "(desplazamiento), que funciona igual. Para volver a la pantalla "
                     "fija, abre el TEO en una ventana mas grande o en Windows Terminal."),
    "doctor.screen": ("Tela / console:", "Screen / console:", "Pantalla / consola:"),
    "doctor.size": ("janela: {cols} colunas x {rows} linhas",
                    "window: {cols} columns x {rows} rows",
                    "ventana: {cols} columnas x {rows} lineas"),
    "doctor.tui": ("tela fixa (tui): {onoff}", "fixed screen (tui): {onoff}",
                   "pantalla fija (tui): {onoff}"),
    "doctor.temp": ("pasta temporaria gravavel: {ok} ({path})",
                    "temporary folder writable: {ok} ({path})",
                    "carpeta temporal escribible: {ok} ({path})"),
    "doctor.admin": ("rodando como administrador: {onoff}",
                     "running as administrator: {onoff}",
                     "corriendo como administrador: {onoff}"),

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
        "perguntar; perigosos pedem aprovacao do usuario. O comando roda na PASTA DE "
        "RASCUNHO do TEO (o temporario do sistema tambem aponta para la): use caminho "
        "absoluto para tocar os arquivos do usuario.",
        "Runs a shell command on the local machine (ls, df, journalctl, systemctl "
        "status, nvidia-smi, apt list, smartctl etc.). Read-only commands run without "
        "asking; dangerous ones ask the user for approval. The command runs in the TEO "
        "DRAFT FOLDER (the system temp folder points there too): use an absolute path "
        "to touch the user's files.",
        "Ejecuta un comando shell en la maquina local (ls, df, journalctl, systemctl "
        "status, nvidia-smi, apt list, smartctl etc.). Los comandos de lectura corren "
        "sin preguntar; los peligrosos piden aprobacion del usuario. El comando corre "
        "en la CARPETA DE BORRADOR del TEO (el temporal del sistema tambien apunta "
        "ahi): usa ruta absoluta para tocar los archivos del usuario."),
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
    "tool.ver_tela.desc": (
        "Tira um print da TELA da pessoa (todas as janelas visiveis) e devolve a "
        "imagem para voce olhar. Use quando a pessoa pedir para ver algo que esta na "
        "tela dela e que exige login (caixa de e-mail, painel, conversa): ela loga, "
        "deixa aberto e pede. Pede licenca antes de fotografar.",
        "Takes a screenshot of the person's SCREEN (all visible windows) and returns "
        "the image for you to look at. Use it when the person asks you to see something "
        "on their screen that requires a login (mailbox, dashboard, chat): they log in, "
        "leave it open and ask. It asks permission before capturing.",
        "Toma una captura de la PANTALLA de la persona (todas las ventanas visibles) y "
        "devuelve la imagen para que la mires. Usalo cuando la persona pida ver algo que "
        "esta en su pantalla y que exige inicio de sesion (correo, panel, conversacion): "
        "ella entra, lo deja abierto y pide. Pide permiso antes de capturar."),
    "tool.ver_tela.arg.espera": (
        "Segundos antes de fotografar (padrao 1, maximo 10), para a pessoa clicar na "
        "janela que quer mostrar",
        "Seconds before capturing (default 1, max 10), so the person can click the "
        "window to show",
        "Segundos antes de capturar (predeterminado 1, max 10), para que la persona "
        "haga clic en la ventana que quiere mostrar"),
    "tool.web_search.arg.top_k": ("Quantidade de resultados (padrao 6, max 10)",
                                  "Number of results (default 6, max 10)",
                                  "Cantidad de resultados (predeterminado 6, max 10)"),
    "tool.ver_pagina.desc": (
        "Abre uma pagina num navegador de verdade (arquivo .html local ou endereco "
        "http/https) e devolve o texto que aparece DEPOIS do JavaScript rodar, os "
        "erros do console e um print da tela. Use para conferir o que voce mesmo "
        "construiu ou para ler pagina que monta o conteudo por JavaScript.",
        "Opens a page in a real browser (local .html file or http/https address) and "
        "returns the text that appears AFTER JavaScript runs, the console errors and a "
        "screenshot. Use it to check what you built or to read a page that builds its "
        "content with JavaScript.",
        "Abre una pagina en un navegador de verdad (archivo .html local o direccion "
        "http/https) y devuelve el texto que aparece DESPUES de que corre el "
        "JavaScript, los errores de consola y una captura de pantalla. Usalo para "
        "revisar lo que construiste o para leer pagina que arma el contenido con "
        "JavaScript."),
    "tool.ver_pagina.arg.origem": (
        "Caminho completo de um arquivo .html (ex.: /home/ana/site/index.html) ou "
        "endereco http(s). No macOS, use \"aba\" para ler a aba ABERTA do Safari "
        "(pagina que a pessoa ja logou e deixou aberta)",
        "Full path of an .html file (e.g. /home/ana/site/index.html) or an http(s) "
        "address. On macOS, use \"tab\" to read the OPEN Safari tab (a page the "
        "person already logged in to and left open)",
        "Ruta completa de un archivo .html (ej.: /home/ana/site/index.html) o "
        "direccion http(s). En macOS, usa \"pestana\" para leer la pestana ABIERTA "
        "de Safari (pagina en la que la persona ya entro y dejo abierta)"),
    "tool.ver_pagina.arg.largura": ("Largura da janela em pixels (padrao 1280)",
                                    "Window width in pixels (default 1280)",
                                    "Ancho de la ventana en pixels (predeterminado 1280)"),
    "tool.ver_pagina.arg.altura": ("Altura da janela em pixels (padrao 800)",
                                   "Window height in pixels (default 800)",
                                   "Alto de la ventana en pixels (predeterminado 800)"),
    "tool.ver_pagina.arg.espera": (
        "Segundos para o JavaScript rodar antes de olhar (padrao 3, maximo 15)",
        "Seconds for JavaScript to run before looking (default 3, max 15)",
        "Segundos para que corra el JavaScript antes de mirar (predeterminado 3, max 15)"),
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
        "Cria um documento para o usuario (relatorio, carta, guia, planilha) e salva na "
        "pasta de Documentos. md e html saem prontos; docx, xlsx e pdf precisam da "
        "biblioteca instalada - se faltar, a resposta diz qual instalar (instalar_pacote). "
        "Devolve o caminho completo do arquivo.",
        "Creates a document for the user (report, letter, guide, spreadsheet) and saves it "
        "in the Documents folder. md and html are ready to go; docx, xlsx and pdf need the "
        "library installed - if missing, the answer says which one to install "
        "(instalar_pacote). Returns the full file path.",
        "Crea un documento para el usuario (informe, carta, guia, planilla) y lo guarda en "
        "la carpeta de Documentos. md y html salen listos; docx, xlsx y pdf necesitan la "
        "biblioteca instalada - si falta, la respuesta dice cual instalar (instalar_pacote). "
        "Devuelve la ruta completa del archivo."),
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
    # ----- lembrete (tools/lembrete.py): vale enquanto o TEO estiver aberto ------
    "tool.lembrete.desc": (
        "Marca um lembrete para daqui a N minutos. O aviso aparece na tela do TEO e faz "
        "som quando a hora chega. SO' funciona enquanto o TEO estiver aberto: se a "
        "pessoa fechar, o lembrete se perde - diga isso a ela.",
        "Sets a reminder for N minutes from now. The notice shows on the TEO screen and "
        "beeps when the time comes. ONLY works while TEO is open: if the person closes "
        "it, the reminder is lost - tell them that.",
        "Marca un recordatorio para dentro de N minutos. El aviso aparece en la pantalla "
        "del TEO y hace un bip cuando llega la hora. SOLO funciona con el TEO abierto: si "
        "la persona lo cierra, el recordatorio se pierde - diselo."),
    "tool.lembrete.arg.minutos": (
        "Daqui a quantos minutos (aceita 0.5, 2, 90)",
        "In how many minutes (accepts 0.5, 2, 90)",
        "Dentro de cuantos minutos (acepta 0.5, 2, 90)"),
    "tool.lembrete.arg.texto": (
        "O que devo lembrar (frase curta)",
        "What should I remind (short sentence)",
        "Que debo recordar (frase corta)"),
    "lembrete.ok": ("Lembrete marcado: em {quando} eu aviso \"{texto}\". Vale enquanto o "
                    "TEO estiver aberto.",
                    "Reminder set: in {quando} I will warn \"{texto}\". Valid while TEO "
                    "is open.",
                    "Recordatorio marcado: en {quando} aviso \"{texto}\". Vale mientras "
                    "el TEO este abierto."),
    "lembrete.agora": ("LEMBRETE: {texto}", "REMINDER: {texto}", "RECORDATORIO: {texto}"),
    "lembrete.titulo": ("Lembrete do TEO", "TEO reminder", "Recordatorio del TEO"),
    "lembrete.segundos": ("{s} segundo(s)", "{s} second(s)", "{s} segundo(s)"),
    "lembrete.minutos": ("{m} minuto(s)", "{m} minute(s)", "{m} minuto(s)"),
    "lembrete.horas": ("{h} hora(s)", "{h} hour(s)", "{h} hora(s)"),
    "lembrete.bad_min": ("ERRO: informe em quantos minutos (numero, ex.: 20).",
                         "ERROR: say in how many minutes (number, e.g. 20).",
                         "ERROR: di en cuantos minutos (numero, ej.: 20)."),
    "lembrete.bad_text": ("ERRO: escreva o que devo lembrar.",
                          "ERROR: write what I should remind.",
                          "ERROR: escribe que debo recordar."),
    "lembrete.bad_range": ("ERRO: o lembrete vale de 0,01 a 1440 minutos (24 horas).",
                           "ERROR: the reminder ranges from 0.01 to 1440 minutes (24 hours).",
                           "ERROR: el recordatorio va de 0,01 a 1440 minutos (24 horas)."),
    "lembrete.cheio": ("ERRO: ja ha {n} lembretes marcados; espere um deles tocar.",
                       "ERROR: there are already {n} reminders set; wait for one to fire.",
                       "ERROR: ya hay {n} recordatorios marcados; espera que uno suene."),
    "lembrete.sem_canal": ("ERRO: esta tela nao tem como mostrar aviso de lembrete.",
                           "ERROR: this screen cannot show reminder notices.",
                           "ERROR: esta pantalla no puede mostrar avisos de recordatorio."),
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
    # Captura automatica (rede de seguranca do modelo): a tela diz o que ficou
    # guardado para a pessoa poder corrigir na hora.
    "mem.captured": ("Guardei na memoria para as proximas conversas: {texto}",
                     "Saved to memory for next conversations: {texto}",
                     "Guardado en la memoria para las proximas conversaciones: {texto}"),
    "mem.none": ("Nenhuma memoria contendo '{query}'.",
                 "No memory containing '{query}'.", "Ninguna memoria con '{query}'."),
    "mem.empty_base": ("A memoria esta vazia.", "The memory is empty.",
                       "La memoria esta vacia."),
    "mem.bad_action": ("ERRO: action invalida (use add, search ou list)",
                       "ERROR: invalid action (use add, search or list)",
                       "ERROR: accion invalida (usa add, search o list)"),
}

# ---------------------------------------------------------------------------
# Tela do navegador (bgh/app_servidor.py + bgh/assets/app.html)
# Mesmo principio: toda frase que a PESSOA le sai daqui, inclusive os botoes.
# O /api/inicio do app entrega so as chaves desta secao para o JavaScript.
# ---------------------------------------------------------------------------
APP = {
    "app.enviar": ("Enviar", "Send", "Enviar"),
    "app.parar": ("Parar", "Stop", "Parar"),
    "app.placeholder": ("Escreva aqui o que voce quer que o TEO faca",
                        "Write here what you want TEO to do",
                        "Escribe aqui lo que quieres que el TEO haga"),
    "app.dica": ("ENTER envia. Para escrever mais de uma linha, use SHIFT+ENTER. "
                 "{cmd} para listar as opcoes.",
                 "ENTER sends. To write more than one line, use SHIFT+ENTER. "
                 "{cmd} to list the options.",
                 "ENTER envia. Para escribir mas de una linea, usa SHIFT+ENTER. "
                 "{cmd} para listar las opciones."),
    # Aviso da dica (rodape) durante o turno: so a parte do RECADO, porque a
    # faixa acima da linha de digitar ja diz que o TEO esta trabalhando. Antes
    # as duas frases repetiam "O TEO esta trabalhando" uma embaixo da outra.
    "app.trabalhando": ("Se escrever agora, o recado chega no meio do caminho.",
                        "If you write now, the note arrives on the way.",
                        "Si escribes ahora, el aviso llega en el camino."),
    # Frase curta da faixa que fica ACIMA da linha de digitar (rodinha + barra).
    "app.trabalhando_curto": ("O TEO esta trabalhando", "TEO is working",
                              "El TEO esta trabajando"),
    "app.ligando": ("Ligando no TEO...", "Connecting to TEO...", "Conectando al TEO..."),
    "app.caiu": ("A ligacao caiu. Tentando de novo sozinho...",
                 "The connection dropped. Retrying by itself...",
                 "La conexion se corto. Reintentando solo..."),
    "app.pensamento": ("Rascunho do TEO (nao e a resposta)",
                       "TEO draft (not the answer)", "Borrador del TEO (no es la respuesta)"),
    "app.ferramentas": ("O que o TEO esta fazendo",
                        "What TEO is doing", "Lo que el TEO esta haciendo"),
    "app.contexto": ("Memoria da conversa", "Conversation memory", "Memoria de la conversacion"),
    "app.licenca_titulo": ("O TEO precisa da sua licenca",
                           "TEO needs your permission", "El TEO necesita tu permiso"),
    "app.licenca_dica": ("Escolha uma opcao. Se ninguem escolher, o TEO NAO faz.",
                         "Choose one option. If nobody chooses, TEO does NOT do it.",
                         "Elige una opcion. Si nadie elige, el TEO NO lo hace."),
    "app.sem_resposta": ("Ninguem respondeu a licenca; por seguranca, o TEO nao fez.",
                         "Nobody answered the permission; for safety, TEO did not do it.",
                         "Nadie respondio al permiso; por seguridad, el TEO no lo hizo."),
    "app.encerrando": ("O TEO foi encerrado. Pode fechar esta aba.",
                       "TEO is closed. You can close this tab.",
                       "El TEO se cerro. Puedes cerrar esta pestana."),
    "app.erro": ("Deu um problema: {erro}", "Something went wrong: {erro}",
                 "Hubo un problema: {erro}"),
    "app.modo_rede": ("MODO REDE: quem estiver na mesma rede pode abrir esta tela. "
                      "Feche quando terminar.",
                      "NETWORK MODE: anyone on this network can open this screen. "
                      "Close it when you finish.",
                      "MODO REDE: quien este en la misma red puede abrir esta pantalla. "
                      "Cierra cuando termines."),
    "app.vazio": ("Nada ainda. Escreva a primeira coisa que voce quer fazer.",
                  "Nothing yet. Write the first thing you want to do.",
                  "Nada todavia. Escribe la primera cosa que quieres hacer."),
    "app.voce": ("Voce", "You", "Tu"),
    "app.passo": ("passo {n}", "step {n}", "paso {n}"),
    "app.escreva_aqui": ("Escreva aqui e aperte ENTER",
                         "Write here and press ENTER", "Escribe aqui y pulsa ENTER"),
    "app.fechar": ("Fechar", "Close", "Cerrar"),
    "app.modelo": ("modelo", "model", "modelo"),
    "app.ver_rascunho": ("ver o rascunho", "show the draft", "ver el borrador"),
    "app.nada_feito": ("(nada ainda)", "(nothing yet)", "(nada todavia)"),
    "app.esconder": ("esconder", "hide", "ocultar"),
    "app.ajuda": ("Ajuda", "Help", "Ayuda"),
    "app.terminal": ("Terminal", "Terminal", "Terminal"),
    "app.terminal.aviso": ("Fechar esta tela e continuar no terminal?",
                           "Close this screen and continue in the terminal?",
                           "Cerrar esta pantalla y seguir en el terminal?"),
    "app.abrindo_terminal": ("Abrindo o TEO no terminal... pode fechar esta aba.",
                             "Opening TEO in the terminal... you can close this tab.",
                             "Abriendo el TEO en el terminal... puedes cerrar esta pestana."),
    "cli.menu.titulo": ("Como voce quer usar o TEO?", "How do you want to use TEO?",
                        "Como quieres usar el TEO?"),
    "cli.menu.app": ("Na tela do navegador (bonita, com botao)",
                     "On the browser screen (pretty, with buttons)",
                     "En la pantalla del navegador (bonita, con boton)"),
    "cli.menu.chat": ("No terminal (como sempre)", "In the terminal (as always)",
                      "En el terminal (como siempre)"),
    "cli.menu.config": ("Configuracoes", "Settings", "Configuracion"),
    "cli.menu.sair": ("Sair", "Quit", "Salir"),
    "cli.menu.prompt": ("Numero (Enter = 1): ", "Number (Enter = 1): ",
                        "Numero (Enter = 1): "),
    "cli.menu.bad": ("Nao entendi. Digite 1, 2, 3 ou 4.",
                     "I did not get it. Type 1, 2, 3 or 4.",
                     "No entendi. Escribe 1, 2, 3 o 4."),
    "cfg.titulo": ("Configuracoes do TEO", "TEO settings", "Configuracion del TEO"),
    "cfg.rede": ("Abrir para a rede", "Open to the network", "Abrir a la red"),
    "cfg.rede.on": ("SIM - quem estiver na mesma rede pode abrir a tela",
                    "YES - anyone on the same network can open the screen",
                    "SI - quien este en la misma red puede abrir la pantalla"),
    "cfg.rede.off": ("NAO - so nesta maquina", "NO - this computer only",
                     "NO - solo en esta maquina"),
    "cfg.idioma": ("Idioma", "Language", "Idioma"),
    "cfg.modelo": ("Modelo", "Model", "Modelo"),
    "cfg.voltar": ("Voltar", "Back", "Volver"),
    "cfg.prompt": ("Numero (Enter = {voltar}): ", "Number (Enter = {voltar}): ",
                   "Numero (Enter = {voltar}): "),
    "cfg.rede.aviso": (
        "ATENCAO: com a rede ligada, o TEO (que executa comandos NESTA maquina)\n"
        "pode ser aberto por qualquer pessoa que estiver na mesma rede e souber o\n"
        "endereco. Use so enquanto precisar e desligue depois.",
        "WARNING: with the network on, TEO (which runs commands on THIS machine)\n"
        "can be opened by anyone on the same network who knows the address.\n"
        "Use it only while you need it and turn it off afterwards.",
        "ATENCION: con la red activada, el TEO (que ejecuta comandos en ESTA maquina)\n"
        "puede abrirlo cualquiera que este en la misma red y sepa la direccion.\n"
        "Usalo solo mientras lo necesites y apagalo despues."),
    "cfg.rede.prompt": ("Digite SIM para abrir para a rede: ",
                        "Type YES to open to the network: ",
                        "Escribe SI para abrir a la red: "),
    "cfg.rede.ligou": ("Pronto: o TEO agora abre para a rede.",
                       "Done: TEO now opens to the network.",
                       "Listo: el TEO ahora abre a la red."),
    "cfg.rede.desligou": ("Pronto: o TEO volta a abrir so nesta maquina.",
                          "Done: TEO is back to this computer only.",
                          "Listo: el TEO vuelve a abrir solo en esta maquina."),
    "cfg.rede.cancelou": ("Cancelado: continua so nesta maquina.",
                          "Cancelled: it stays on this computer only.",
                          "Cancelado: sigue solo en esta maquina."),
    "cfg.lingua.prompt": ("Numero do idioma (Enter = {first}): ",
                          "Language number (Enter = {first}): ",
                          "Numero del idioma (Enter = {first}): "),
    "cfg.lingua.ok": ("Idioma gravado: {nome}.", "Language saved: {nome}.",
                      "Idioma guardado: {nome}."),
    "cfg.modelo.prompt": ("Nome do modelo (Enter = manter {atual}): ",
                          "Model name (Enter = keep {atual}): ",
                          "Nombre del modelo (Enter = mantener {atual}): "),
    "cfg.modelo.ok": ("Modelo gravado: {modelo}.", "Model saved: {modelo}.",
                      "Modelo guardado: {modelo}."),
    "app.opcoes": ("Opcoes do TEO", "TEO options", "Opciones del TEO"),
    # Ajuda PROPRIA da tela do navegador: so o que existe aqui. O manual completo
    # (com teclas do terminal) continua no /ajuda do modo terminal.
    "app.cmd.escrever": ("Escrever", "Writing", "Escribir"),
    "app.help.escrever": ("ENTER envia. SHIFT+ENTER escreve em outra linha.",
                          "ENTER sends. SHIFT+ENTER writes on another line.",
                          "ENTER envia. SHIFT+ENTER escribe en otra linea."),
    "app.cmd.anexar": ("Clipe", "Clip", "Clip"),
    "app.help.anexar": ("o clipe embaixo da caixa de digitar anexa foto, PDF, "
                        "Word, Excel ou texto para o TEO ler",
                        "the clip below the typing box attaches a photo, PDF, "
                        "Word, Excel or text for TEO to read",
                        "el clip debajo de la caja de escribir adjunta foto, PDF, "
                        "Word, Excel o texto para que el TEO lea"),
    "app.cmd.parar": ("Parar", "Stop", "Parar"),
    "app.help.parar": ("durante a resposta o botao Enviar vira Parar; ele para na hora",
                       "while answering, the Send button becomes Stop; it stops right away",
                       "mientras responde, el boton Enviar pasa a Parar; para al instante"),
    "app.cmd.novo": ("/nova", "/new", "/nuevo"),
    "app.help.novo": ("conversa nova; a atual fica guardada nas sessoes; a memoria "
                      "e as skills continuam",
                      "new conversation; the current one is saved in sessions; "
                      "memory and skills stay",
                      "conversacion nueva; la actual queda guardada en sesiones; "
                      "la memoria y las skills siguen"),
    "app.cmd.sessoes": ("/sessoes", "/sessions", "/sesiones"),
    "app.help.sessoes": ("conversas guardadas, com data e assunto; /abrir <numero> "
                         "volta numa delas",
                         "saved conversations with date and subject; /open <number> "
                         "goes back to one",
                         "conversaciones guardadas con fecha y asunto; /abrir <numero> "
                         "vuelve a una"),
    "app.cmd.buscar": ("/buscar <palavra>", "/find <word>", "/buscar <palabra>"),
    "app.help.buscar": ("procura uma palavra na conversa e mostra os trechos",
                        "looks for a word in the conversation and shows the snippets",
                        "busca una palabra en la conversacion y muestra los trozos"),
    "app.cmd.exportar": ("/exportar", "/export", "/exportar"),
    "app.help.exportar": ("salva a conversa em ~/Documentos (texto simples) para "
                          "mandar a alguem",
                          "saves the conversation in ~/Documentos (plain text) to "
                          "send to someone",
                          "guarda la conversacion en ~/Documentos (texto simple) "
                          "para mandarla a alguien"),
    "app.cmd.reserva": ("/reserva <numero>", "/reserve <number>", "/reserva <numero>"),
    "app.help.reserva": ("provedor de reserva para quando o principal nao responde",
                         "backup provider for when the main one does not answer",
                         "proveedor de reserva para cuando el principal no responde"),
    "app.cmd.handoff": ("/handoff", "/handoff", "/handoff"),
    "app.help.handoff": ("salva um .md com o que foi feito, para continuar outro dia",
                         "saves a .md with what was done, to continue another day",
                         "guarda un .md con lo que se hizo, para continuar otro dia"),
    "app.cmd.modelo": ("/modelo", "/model", "/modelo"),
    "app.help.modelo": ("lista e troca o modelo do servidor (fica salvo)",
                        "lists and switches the server model (saved)",
                        "lista y cambia el modelo del servidor (guardado)"),
    "app.cmd.lingua": ("/lingua", "/language", "/idioma"),
    "app.help.lingua": ("troca o idioma da tela", "switches the screen language",
                        "cambia el idioma de la pantalla"),
    "app.cmd.fundo": ("/fundo", "/background", "/fondo"),
    "app.help.fundo": ("cor de fundo da tela (as letras mudam para continuar legiveis)",
                       "screen background colour (letters change to stay readable)",
                       "color de fondo de la pantalla (las letras cambian para seguir legibles)"),
    "app.cmd.limpar": ("/limpar", "/clean", "/limpiar"),
    "app.help.limpar": ("apaga os rascunhos que o TEO guarda neste computador",
                        "erases the scratch files TEO keeps on this computer",
                        "borra los borradores que el TEO guarda en esta computadora"),
    "app.cmd.sobre": ("/sobre", "/about", "/acerca"),
    "app.help.sobre": ("quem fez o TEO, por que esse nome e os agradecimentos",
                       "who made TEO, why that name and the thanks",
                       "quien hizo el TEO, por que ese nombre y los agradecimientos"),
    "app.cmd.ditar": ("/ditar", "/dictate", "/dictar"),
    "app.help.ditar": ("falar em vez de digitar: por enquanto so no terminal",
                       "speaking instead of typing: for now only in the terminal",
                       "hablar en vez de escribir: por ahora solo en el terminal"),
    "app.help.secao.dia": ("Do dia a dia", "Every day", "Del dia a dia"),
    "app.help.secao.ajustes": ("Ajustes", "Adjustments", "Ajustes"),
    "app.help.secao.quando": ("Quando precisar", "When you need it", "Cuando lo necesites"),
    "app.help.secao.tela": ("Tela", "Screen", "Pantalla"),
    "app.help.secao.terminal": ("So no terminal", "Terminal only", "Solo en el terminal"),
    # comandos que existem aqui e ainda nao estavam na lista
    "app.cmd.provedor": ("/provedor", "/provider", "/proveedor"),
    "app.help.provedor": ("lista e troca o provedor (DeepSeek, NubesBR, modelo local)",
                          "lists and switches the provider (DeepSeek, NubesBR, local model)",
                          "lista y cambia el proveedor (DeepSeek, NubesBR, modelo local)"),
    "app.cmd.configurar": ("/configurar", "/setup", "/configurar"),
    "app.help.configurar": ("assistente que cria ou conserta o provedor, sem editar arquivo",
                            "wizard that creates or fixes the provider, no file editing",
                            "asistente que crea o arregla el proveedor, sin editar archivo"),
    "app.cmd.teto": ("/teto", "/cap", "/tope"),
    "app.help.teto": ("teto de ferramentas por pedido (padrao 120); /teto 0 = sem limite",
                      "tool cap per request (default 120); /cap 0 = no limit",
                      "tope de herramientas por pedido (por defecto 120); /tope 0 = sin limite"),
    "app.cmd.ctx": ("/ctx", "/ctx", "/ctx"),
    "app.help.ctx": ("medidor da memoria da conversa; /ctx 65000 define o limite",
                     "conversation memory meter; /ctx 65000 sets the limit",
                     "medidor de la memoria de la conversacion; /ctx 65000 fija el limite"),
    "app.cmd.pensamento": ("/pensamento", "/thinking", "/pensamiento"),
    "app.help.pensamento": ("mostra ou esconde o rascunho do modelo na resposta",
                            "shows or hides the model draft in the answer",
                            "muestra u oculta el borrador del modelo en la respuesta"),
    "app.cmd.zoom": ("/zoom", "/zoom", "/zoom"),
    "app.help.zoom": ("tamanho da tela: /zoom 75 para notebook de 14 polegadas "
                      "(fica guardado)",
                      "screen size: /zoom 75 for a 14 inch notebook (saved)",
                      "tamano de pantalla: /zoom 75 para portatil de 14 pulgadas "
                      "(guardado)"),
    "app.cmd.site": ("/site", "/site", "/site"),
    "app.help.site": ("sites com login: /site abrir <endereco> abre uma janela para "
                      "VOCE entrar; /site esquecer apaga as sessoes",
                      "login sites: /site open <address> opens a window for YOU to "
                      "sign in; /site forget erases the sessions",
                      "sitios con login: /site abrir <direccion> abre una ventana para "
                      "que TU entres; /site esquecer borra las sesiones"),
    "app.cmd.skills": ("/skills", "/skills", "/habilidades"),
    "app.help.skills": ("lista as habilidades que o TEO ja aprendeu",
                        "lists the skills TEO has already learned",
                        "lista las habilidades que el TEO ya aprendio"),
    "app.cmd.doctor": ("/doctor", "/doctor", "/doctor"),
    "app.help.doctor": ("diagnostico da conexao e da maquina",
                        "connection and machine diagnosis",
                        "diagnostico de la conexion y de la maquina"),
    "app.cmd.atualizar": ("/atualizar", "/update", "/actualizar"),
    "app.help.atualizar": ("confere versao nova e instala (pedindo sua licenca)",
                           "checks for a new version and installs it (asking permission)",
                           "revisa si hay version nueva e instala (pidiendo permiso)"),
    "app.cmd.so_terminal": ("/ditar, /voz, /fonte, /palco", "/dictate, /voice, /font, /stage",
                            "/dictar, /voz, /fuente, /escenario"),
    "app.help.so_terminal": ("esses quatro so funcionam na tela do terminal",
                             "those four only work on the terminal screen",
                             "esos cuatro solo funcionan en la pantalla del terminal"),
    "app.cmd.terminal": ("Terminal", "Terminal", "Terminal"),
    "app.help.terminal": ("botao no topo: continua no terminal onde voce abriu",
                          "top button: continues in the terminal you opened it from",
                          "boton arriba: sigue en el terminal donde lo abriste"),
    "app.cmd.sair": ("Fechar", "Close", "Cerrar"),
    "app.help.sair": ("botao no topo: encerra o TEO (a conversa fica guardada)",
                      "top button: closes TEO (the conversation is saved)",
                      "boton arriba: cierra el TEO (la conversacion queda guardada)"),
    "app.fechar_menu": ("fechar", "close", "cerrar"),
    "app.sair_ok": ("Fechar o TEO? A conversa fica guardada: quando voce abrir de "
                    "novo, ele continua do mesmo ponto.",
                    "Close TEO? The conversation is saved: when you open it again it "
                    "continues from the same point.",
                    "Cerrar el TEO? La conversacion queda guardada: cuando lo abras de "
                    "nuevo, sigue desde el mismo punto."),
    "app.sair_confirmar": ("O TEO ainda esta trabalhando. Sair agora mesmo?",
                           "TEO is still working. Leave right now?",
                           "El TEO todavia esta trabajando. Salir ahora mismo?"),
    "cli.help.app": ("tela do TEO no navegador (mesmo agente, mesma memoria)",
                     "TEO screen in the browser (same agent, same memory)",
                     "pantalla del TEO en el navegador (mismo agente, misma memoria)"),
    "cli.app.rede": ("abrir para a rede local (pede confirmacao e avisa na tela)",
                     "open to the local network (asks for confirmation and warns on screen)",
                     "abrir a la red local (pide confirmacion y avisa en pantalla)"),
    "cli.app.local": ("so nesta maquina, mesmo que o config diga rede",
                      "this computer only, even if the config says network",
                      "solo en esta maquina, aunque el config diga red"),
    "cli.app.porta": ("porta fixa (padrao: uma porta livre escolhida agora)",
                      "fixed port (default: a free port picked now)",
                      "puerto fijo (por defecto: un puerto libre elegido ahora)"),
    "cli.app.no_browser": ("nao abrir o navegador sozinho (o endereco aparece na tela)",
                           "do not open the browser by itself (the address shows up)",
                           "no abrir el navegador solo (la direccion aparece)"),
    "cli.app.menu": ("Como voce quer usar o TEO?\n  1. Na tela do navegador (bonita, com botao)\n"
                     "  2. No terminal (como sempre)\n"
                     "Numero (Enter = 1): ",
                     "How do you want to use TEO?\n  1. On the browser screen (pretty, with buttons)\n"
                     "  2. In the terminal (as always)\n"
                     "Number (Enter = 1): ",
                     "Como quieres usar el TEO?\n  1. En la pantalla del navegador (bonita, con boton)\n"
                     "  2. En el terminal (como siempre)\n"
                     "Numero (Enter = 1): "),
    "app.sessao": ("Esta janela do TEO nao esta liberada. Abra o endereco que "
                   "apareceu no terminal (aquele com o codigo depois de ?t=).",
                   "This TEO window is not unlocked. Open the address shown in the "
                   "terminal (the one with the code after ?t=).",
                   "Esta ventana del TEO no esta liberada. Abre la direccion que "
                   "aparecio en el terminal (aquella con el codigo despues de ?t=)."),
}

TEXTS: dict[str, tuple[str, str, str]] = {}
for _bloco in (COMMON, HELP_HEADERS, CHAT, AGENT, GATE, TUI, PALCO, LLM, SETUP, CLI, TOOLS,
               UPDATER, FILES, MEMORY, APP):
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


def when_now(agora: datetime | None = None) -> str:
    """Data e hora locais no formato que vai para o modelo: 'sexta-feira, 27/11/2026, 14:32 (-03)'.

    Fonte unica do "que dia e' hoje": o prompt do sistema e' montado uma vez por
    sessao e envelhece, entao a linha (AGORA: ...) viaja junto da mensagem da
    pessoa em cada turno (ver agent.py). Dia da semana vem de WEEKDAYS porque
    strftime depende do locale da maquina.
    """
    momento = agora or datetime.now().astimezone()
    dia = WEEKDAYS[get_lang()][momento.weekday()]
    fuso = momento.strftime("%z") or ""
    sufixo = f" ({fuso[:3]})" if fuso else ""
    return f"{dia}, {momento.strftime('%d/%m/%Y, %H:%M')}{sufixo}"


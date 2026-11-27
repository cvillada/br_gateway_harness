[Portugues](README.md) | [English](README.en.md) | **Espanol**

# TEO (bgh) - agente CLI local para la maquina del usuario

TEO es el apodo de este harness (br_gateway_harness): el nombre del gato negro del
autor.

Harness liviano en Python: bucle de agente + endpoint compatible con OpenAI (local o
API), herramientas reales (shell, archivos, Python, web, documentos), memoria
persistente y skills que el propio TEO crea al aprender. Modelo de aprobacion:
lo seguro corre directo, lo peligroso pide aprobacion
humana.

## Instalacion por sistema operativo (carpeta TEO + ambiente virtual)

El patron es igual en los tres sistemas: crear una carpeta llamada TEO, crear un
ambiente virtual dentro de ella e instalar el wheel bajado de la pagina de Releases
del repo.

### Windows (ruta de los dos clics - para ninos y mayores)

1. Instala antes Python 3.11 o mas nuevo: abre https://python.org, haz clic en
   "Download", abre el archivo bajado y marca la casilla "Add python.exe to PATH"
   (eso es una sola vez en la vida).
2. Abre esta pagina en el navegador y baja el archivo `INSTALAR_TEO.bat`:
   https://github.com/cvillada/br_gateway_harness/releases/latest
3. Haz DOBLE CLIC en el archivo `INSTALAR_TEO.bat` que esta en la carpeta Descargas.
   Listo: baja el TEO, crea la carpeta TEO, instala, crea un icono **TEO** en el
   escritorio y abre el programa solo. De ahi en adelante son solo dos clics en el
   icono TEO del escritorio - no hace falta tocar el Simbolo del sistema nunca mas.
   (Cerrar la ventana del TEO cierra solo esa conversacion; el icono reabre todo.)

Si Windows muestra el aviso azul "Windows protegio tu PC", haz clic en "Mas
informacion" y despues en el boton "Ejecutar de todas formas" (es porque el archivo
todavia no tiene firma digital; el codigo esta en este mismo repo).

Para conversar otra vez despues: dos clics en el icono **TEO** del escritorio.
(Si el icono no aparece, el atajo tambien esta en
`C:\Users\TU_USUARIO\TEO\abrir-teo.bat`.)

#### Windows (ruta tecnica: 2 lineas en el Simbolo del sistema)

Requisito: Python 3.11 o mas nuevo (https://python.org; marca "Add python.exe to PATH").
Abre el Simbolo del sistema (cmd) y pega, una linea por vez:

```batch
curl -L -o %USERPROFILE%\install_te.ps1 https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te_win.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\install_te.ps1
```

El script hace todo solo: baja el wheel del Release mas nuevo, crea la carpeta
`%USERPROFILE%\TEO`, crea el ambiente virtual, copia el wheel dentro de ella, corre
el pip install y abre el TEO (la primera vez, el asistente de configuracion empieza
solo). El instalador tambien pregunta el idioma (Portugues, English o Espanol) y
toda la pantalla arranca en el.

Para conversar otra vez: `cd %USERPROFILE%\TEO`, `.venv\Scripts\activate`, `bgh`.
La configuracion y el historial quedan en `C:\Users\TU_USUARIO\.bgh`. Usa Windows
Terminal (ya viene en Windows 11); el Simbolo del sistema viejo funciona, pero con
menos recursos visuales.

#### Windows (metodo manual, si prefieres paso a paso)

1. Baja en la pagina Releases el archivo `bgh_motor-...-py3-none-any.whl` (va a la
   carpeta Descargas de tu usuario; el numero de version aparece en el medio del
   nombre del archivo).
2. Abre el Simbolo del sistema (cmd) y ejecuta, linea por linea. En el comando del
   `pip`, cambia `numero-de-version` por el numero que aparece en el nombre del
   archivo bajado (ej.: 0.2.8):

```batch
mkdir TEO
cd TEO
python -m venv .venv
.venv\Scripts\activate
pip install "%USERPROFILE%\Downloads\bgh_motor-numero-de-version-py3-none-any.whl"
bgh
```

Si el pip dice que el archivo no existe, descubre donde cayo:

```batch
dir /s /b %USERPROFILE%\Downloads\bgh_motor*
```

y usa la ruta completa que aparezca en la linea del comando de arriba (o mueve el
`.whl` dentro de la carpeta TEO e instalalo por su nombre estando dentro de ella).
En PowerShell, cambia `%USERPROFILE%` por `$env:USERPROFILE`.

3. Para usarlo de nuevo en otra sesion: `cd TEO`, `.venv\Scripts\activate`, `bgh`.

La configuracion y el historial quedan en `C:\Users\TU_USUARIO\.bgh`.

### macOS (instalacion practica: 2 lineas)

Requisito: Python 3.11 o mas nuevo (si falta: instalalo de
https://python.org/downloads o, si tienes brew, `brew install python@3.12`).
Abre la Terminal y pega, una linea por vez:

```bash
curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
bash install_te.sh
```

El script hace todo solo: baja el wheel del Release mas nuevo, crea la carpeta
`~/TEO`, crea el ambiente virtual, copia el wheel dentro de ella, corre el pip
install, crea un atajo para abrir el TEO sin terminal - un icono llamado **TEO** en
el escritorio (en macOS, `TEO.app` en el Finder; en Linux, un lanzador `TEO`) - y
abre el programa (la primera vez, el asistente de configuracion empieza solo). El
instalador tambien pregunta el idioma (Portugues, English o Espanol) y toda la
pantalla arranca en el.

#### macOS (metodo manual, si prefieres paso a paso)

```bash
mkdir TEO && cd TEO
python3 -m venv .venv
source .venv/bin/activate
pip install ~/Downloads/bgh_motor-*.whl
bgh
```

Si el pip se queja de que encontro mas de un archivo, borra los `.whl` viejos de la
carpeta Descargas y corre el comando otra vez. Para usar de nuevo: `cd TEO`,
`source .venv/bin/activate`, `bgh`. La configuracion y el historial quedan en `~/.bgh`.

### Linux (instalacion practica: 2 lineas)

Requisito: Python 3.11+ con venv (Ubuntu/Debian:
`sudo apt install python3 python3-venv`). En la terminal, una linea por vez:

```bash
curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
bash install_te.sh
```

Funciona igual que en macOS (mismo script): crea `~/TEO` + venv, baja el wheel del
Release mas nuevo, instala, crea el atajo del escritorio con el icono del gato y
abre el TEO.

#### Linux (alternativas)

Directo del repo clonado:

```bash
cd br_gateway_harness
bash install.sh   # instala y ya entra al asistente de configuracion (flujo unico)
bgh               # conversaste, listo
```

O el metodo manual con venv (copiando el wheel a `~/TEO`), igual al de macOS de arriba.

### Sin Python (cualquier sistema)

Cada Release trae el binario listo de tu sistema: `motor.exe` (Windows),
`motor-macos` (macOS, para Macs con chip Apple - M1, M2, M3, M4) y `motor` (Linux).
Es bajar y ejecutar. Mac con chip Intel: usa el paso a paso con Python de arriba
(funciona en cualquier Mac). En Linux, ejecuta `motor` en la misma distribucion en
la que fue generado (o usa el paso a paso con Python, que funciona en cualquiera).

El asistente se puede rehacer en cualquier momento con `bgh setup`. Si la persona
abre el TEO sin haberlo configurado nunca, el asistente empieza solo en el acto (no
hace falta memorizar comandos). En el asistente elige el proveedor (1-4), confirma
URL y nombre del modelo (Enter acepta el predeterminado), pega la clave si el
servidor la pide - y hay prueba de conexion con autocorreccion: si dice "pide
clave", pregunta la clave en el acto y prueba otra vez. Todo queda en
`~/.bgh/config.json` con permiso solo del usuario (600); la clave solo se envia a la
URL que el propio usuario registro.

`bgh doctor` Diagnostica la maquina del usuario y la conexion con el modelo.

## Proveedores soportados (presets del setup)

| Preset | Que es | base_url |
|--------|--------|----------|
| deepseek | API DeepSeek (nube, mas facil) | https://api.deepseek.com/v1 |
| nubesbr  | servidor de IA hospedado (publico) | https://ia.nubesbr.com/v1/ (ajustable) |
| local    | llama.cpp / LM Studio en la propia maquina | http://127.0.0.1:30000/v1 |
| otro    | cualquier endpoint compatible con OpenAI | (lo escribes tu) |

Preparado para modelos de 27B para arriba: presupuesto de contexto configurable
(`context_budget_chars`, predeterminado 250000), compresion automatica de la
conversacion y dispatch tolerante a JSON malformado de modelo cuantizado. El
asistente de setup hereda el limite del servidor por tres caminos: el motor
llama.cpp publica `n_ctx` (`props`), las APIs estilo OpenRouter publican
`context_length`, y las APIs que no publican nada (DeepSeek, Anthropic...) salen del
catalogo publico models.dev. El valor se define solo - no le pregunta un numero al
usuario; sin ninguna fuente, vale el predeterminado del proveedor. Cuando el
proveedor entrega mas que el tope de lectura, el pie avisa ("tope; el servidor
entrega N tokens"). Salida por respuesta hasta 8192 tokens (`max_tokens`), suficiente
para escribir un documento HTML de ~28 mil caracteres en una ronda; sesiones de
redaccion pesadas pueden usar `/ctx 300000`. Ajuste fino: `/ctx` en pantalla.

Limite de pasos por pedido: un pedido puede dar mucho trabajo (abrir paginas, ejecutar
comandos, revisar archivos, escribir un documento). Para no pasar horas sin avisar, el TEO
tiene un limite de **120 pasos por pedido**. Si el trabajo no termina, NO inventa el resto:
para, muestra `TODAVIA NO ESTA LISTO`, guarda la conversacion y te pide escribir `continuar`
- retoma desde donde paro, con los datos que ya tenia. `/tope 60` cambia el limite,
`/tope 0` lo quita (ahi puede demorar bastante; ESC o CTRL+C paran) y `/tope` solo muestra
el valor que vale. El valor por defecto (120) queda guardado en el config.

## Conversando

El chat abre con la linea `tu>` siempre abajo y los mensajes
entran en el scroll natural de la propia terminal - la rueda y la barra lateral de TU
terminal mueven la conversacion, y al salir el texto sigue visible para releer. Sin
terminal interactiva (pipe/script), cae en el modo clasico solo. Para apagar la
pantalla interactiva: `"tui": false` en `~/.bgh/config.json`.

La ventana ya abre maximizada y con el nombre **TEO Agent**: en ventana pequena la
barra de abajo (medidor, teclas, aviso de "corriendo") no cabria entera. En Windows
la maximizacion la hace la API de la consola; en Linux y macOS el pedido se envia a
la terminal, y la terminal que no lo acepta simplemente mantiene el tamano que tenia.

Al mandar una pregunta, aparece por unos instantes el recorrido del pedido arriba de
la linea de escribir: START -> AGENTE -> HERRAMIENTA -> MODELO -> PANTALLA. El paso
encendido es el que tiene el pedido en ese momento, con el tiempo real al lado, y el
recorrido se recoge cuando llega la respuesta (el recorrido solo aparece para
pedidos al agente: comando con barra y menu de archivos no lo dibujan). Debajo de los
pasos quedan los tokens de cada pieza (entrada bajo AGENTE, salida bajo MODELO, total
bajo PANTALLA), abreviados: 800, 2.00k, 1.20M. Para apagarlo: `/escenario desactivar`.

Parar y releer (pensado para mayores y ninos - un solo toque):

| Tecla | Que hace |
|-------|----------|
| CTRL+C o ESC durante la respuesta | PARA de responder y devuelve el comando en el acto |
| ENTER con texto durante la respuesta | avisa al turno en curso; el modelo lo lee en la siguiente ronda |
| CTRL+C dos veces seguidas | salida de seguridad si algo se traba |
| Rueda del raton o barra lateral de tu terminal | releer el texto que subio |
| CTRL+C con la linea vacia | cierra el TEO (ESC nunca cierra solo) |
| Ctrl+J, o terminar la linea con `\` y ENTER | salta de linea en el `tu>` (escribir en varias lineas; en cmd de Windows Alt+Enter es pantalla completa) |

La barra fija de abajo siempre dice que apretar; durante la respuesta muestra
"corriendo... PARA PARAR: CTRL+C o ESC".

Atajos rapidos (no piden permiso, solo muestran):

| Atajo | Que hace |
|-------|----------|
| `/` | al COMIENZO de la linea abre la lista de comandos (flechas eligen, escribir filtra, ENTER ejecuta); despues de texto (ej.: `veja /`) abre el navegador de CARPETAS desde la raiz - flechas andan, ENTER entra, `..` sube; en modo simple, lista |
| `@` | con la linea vacia abre el menu de archivos de la carpeta actual para adjuntar (flechas eligen, ENTER toma y ENTER otra vez adjunta); en modo simple, lista los archivos |
| `@<archivo>` | adjunta el archivo; despues solo pregunta sobre el. PNG/JPG/WEBP/GIF/BMP van como IMAGEN a la vision del modelo (hasta 5 MB); escribir la ruta de la imagen en el mensaje tambien adjunta |
| `/ls <carpeta>` | lista una carpeta especifica (sin menu) |

Comandos:

| Comando | Que hace |
|---------|----------|
| `/modelo` | lista los modelos publicados por el servidor |
| `/modelo <nombre o numero>` | cambia el modelo (queda guardado en el config) |
| `/proveedor` | lista los proveedores registrados (ej.: 1 deepseek, 2 local) |
| `/proveedor <nombre o numero>` | cambia el proveedor en uso en el acto (queda guardado) |
| `/pensamiento activar\|desactivar` | muestra u oculta el bloque gris en pantalla (el modelo sigue pensando); avanzado: nivel enviado al servidor auto off minimum low medium high xhigh max ultra |
| `/escenario activar\|desactivar` | muestra u oculta el recorrido del pedido durante la respuesta (solo pantalla fija) |
| `/ctx` | medidor del contexto; `/ctx <numero>` fija el limite y lo guarda (ej.: `/ctx 65000`; acepta 65k) |
| `/tope` | cuantos pasos puede dar el TEO en un pedido (por defecto 120). `/tope 60` lo cambia, `/tope 0` quita el limite (puede demorar; ESC/CTRL+C paran), `/tope` solo muestra el valor. Acepta tambien `sin` e `ilimitado` |
| `/configurar` | arregla o registra proveedor sin salir del TEO (mismo asistente de `bgh setup`) |
| `/doctor` | diagnostico de la conexion y de la maquina en la propia pantalla |
| `/actualizar` | revisa si hay version nueva en GitHub; si hay, pide permiso e instala (misma version: avisa que todo esta bien) |
| `/mem <texto>` | guarda una preferencia tuya en la memoria |
| `/idioma` | cambia el idioma de la pantalla: 1) Portugues  2) English  3) Espanol (queda guardado). Atajos: `/lingua`, `/language` |
| `/voz` | accesibilidad: lee cada respuesta en voz alta con la voz del sistema (speech-dispatcher/espeak en Linux, System.Speech en Windows, `say` en Mac); escribirlo otra vez apaga; ESC calla. Atajo: `/voice` |
| `/fundo` | color de fondo de la pantalla: blanco, amarillo, verde, azul, rojo, negro o `padrao`; las letras cambian solas para seguir legibles (fondo claro = letras oscuras). Atajo: `/background` |
| `/fonte` | tamano de la letra: 1 normal, 2 grande, 3 mayor, 4 enorme. En Windows cambia en el acto; en Linux/Mac reabre la ventana con zoom (o ensena las teclas de tu terminal). Atajo: `/font` |
| `/ditar` | accesibilidad: escribe HABLANDO. El TEO escucha el microfono, transcribe en el idioma de la pantalla y pone el texto en la linea para que lo revises antes del ENTER. El modelo del idioma (pt/en/es, ~55 MB) se baja una vez, la primera vez; despues funciona sin internet y el sonido no sale de tu computadora. Atajos: `/dictate`, `/dictar`. En la pantalla fija la tecla F2 hace lo mismo, y con la linea VACIA DOS espacios seguidos tambien (un espacio solo es un espacio normal; un bip avisa que empezo a escuchar, otro que paro; ESC corta) |
| `/limpiar` | borra los borradores que el TEO crea en la carpeta `scratch` (scripts de `run_python`, textos de la voz y temporales de los comandos) y muestra el espacio liberado; pregunta antes y no toca conversacion, memoria ni skills. Con un tamano (`/limpiar 5GB`) cambia solo el aviso de carpeta llena de la apertura (por defecto 3 GB). Atajo: `/clean` |
| `/sessoes` | lista las conversaciones guardadas (fecha, asunto, mensajes). `/abrir <numero>` vuelve a una de ellas; la conversacion abierta tambien queda guardada. Atajos: `/sessions`, `/sesiones`; `/open` |
| `/handoff [carpeta/nombre]` | guarda un .md en la carpeta que elijas (o en esta) con lo que se hizo, donde quedamos y los proximos pasos, para continuar otro dia; el TEO busca y lee ese archivo cuando pidas continuar |
| `/buscar <palabra>` | busca una palabra en la conversacion y muestra los trozos (tu, TEO y herramienta). Atajo: `/find` |
| `/exportar [nombre]` | guarda la conversacion en `~/Documentos` como texto simple, para mandarla a alguien. Atajo: `/export` |
| `/erro` | muestra el ultimo error tecnico registrado, listo para copiar y pedir ayuda. Atajo: `/error` |
| `/aviso` | activa/desactiva el bip y la notificacion del sistema cuando termina un turno largo o cuando el TEO espera tu respuesta (licencia). Atajo: `/notify` |
| `/simples` | pantalla simple: esconde el recorrido del pedido y el nombre de la herramienta - para ninos o para quien se distrae con mucha informacion. Atajo: `/simple` |
| `/reserva <numero>` | proveedor de reserva: si el principal no responde, el TEO intenta ese UNA vez en el turno y vuelve al principal en el siguiente; `/reserva off` lo apaga. Atajo: `/reserve` |
| `/nuevo` `/habilidades` `/ayuda` `/salir` | conversacion nueva (la actual queda guardada en las sesiones), skills, ayuda, salir |

Idioma: el TEO habla portugues (de fabrica), ingles y espanol. El instalador pregunta
el idioma al inicio y el `/idioma` lo cambia en cualquier momento, en el acto -
banner, ayuda, menus, permiso, avisos y barra de abajo. Los comandos funcionan en los
tres idiomas en cualquier idioma de pantalla (`/ajuda`, `/nova`, `/modelo`,
`/pensamento`, `/sair`...), y el modelo pasa a responder en el idioma elegido (si la
persona escribe en otro idioma, responde en el idioma del mensaje).

Version nueva: al abrir, el TEO revisa solo (una vez, sin trabar la pantalla) si hay
version nueva y avisa "hay una version nueva del TEO (vX.Y.Z). Para actualizar,
escribe `/actualizar`". Sin internet avisa que no pudo revisar y sigue funcionando;
el `update_check` en `~/.bgh/config.json` apaga la consulta.

Icono: el atajo del escritorio sale con el gato del TEO - Linux (`.desktop` con
`Icon=`), Windows (atajo con `teo.ico` y el exe con icono) y macOS (`TEO.app` montado
con el `teo.icns`). Los iconos viven en `bgh/assets/` y los genera
`scripts/make_icons.py` (sin dependencias). Si en macOS el atajo aparece como un
pergamino blanco (instalacion vieja), ejecuta `scripts/consertar_icone_mac.sh`: lo
arregla sin reinstalar.

- Pensamiento del modelo: si el servidor devuelve `reasoning_content`/`reasoning`
  (llama.cpp con Qwen thinking, DeepSeek-R1 etc.), aparece como `pensamiento> ...`
  antes de la respuesta.
- Contexto: despues de cada respuesta sale `contexto: NN% de 250000 chars`
  (verde/amarillo/rojo); al 85% la barra de abajo entra en el color de alerta y la
  siguiente ronda pesada compacta sola en resumen (el TEO avisa en pantalla mientras
  compacta). Si el servidor rechaza el tamano, compacta e intenta de nuevo en vez de
  parar. El medidor anda en cada ronda (no solo al final) y, cuando la conversacion ya
  paso el umbral, la compactacion corre al FINAL de un turno largo - el siguiente empieza
  con espacio. El punto de compactacion es ajustable: `context_compress_pct` en
  `~/.bgh/config.json`; con `summary_model` un modelo menor puede hacer el resumen.

## Pantalla del navegador (el mismo TEO, con botones)

Quien abre el TEO - por el icono del escritorio o escribiendo `bgh` - elige como
usarlo:

      Como quieres usar el TEO?
        1. En la pantalla del navegador (bonita, con boton)
        2. En el terminal (como siempre)
        3. Configuracion
        4. Salir

- La opcion 1 abre la MISMA conversacion en una pantalla del navegador, en
  `127.0.0.1` en un puerto libre: letra grande, boton Enviar, borrador del modelo
  recogido, panel "Lo que el TEO esta haciendo" y medidor de contexto. Nada para
  instalar, sin internet: el navegador que la persona ya tiene.
- Permiso: los cuatro caminos se vuelven botones grandes. Si nadie responde
  (pestana cerrada, computadora suspendida), el TEO NO lo hace - falla cerrado,
  igual que el Enter solo del terminal.
- Cambiar de pantalla sin salir: `/tela` (o `/screen`, `/pantalla`, `/app`,
  `/navegador`) en el terminal abre el navegador; el boton **Terminal** en la
  pantalla del navegador vuelve.
- Un documento citado se vuelve enlace: la ruta que el TEO escribe (PDF, DOCX,
  XLSX, CSV, imagen, TXT...) se puede clicar y abre en otra ventana, sin perder la
  conversacion. Solo abre archivos dentro de tus carpetas y de tipo conocido.
- La opcion 3 (Configuracion) cambia lo que antes solo existia en el archivo:
  abrir a la red (con aviso y confirmacion escrita), idioma y modelo. Se guarda en
  `~/.bgh/config.json`; `bgh app --local` ignora la red solo en esa ejecucion.
- El nucleo es el mismo: memoria, conversacion, herramientas y permisos. Solo
  cambia la tapa.
- Para acceso desde fuera de casa usa tunel SSH o Tailscale - no abras puerto en
  el router.
- Atajos: `bgh app` (va directo al navegador), `bgh chat` (va directo al
  terminal).
- Tamano de pantalla: abre al 75% (cabe en una ventana de portatil, con el pie
  y la dica a la vista). `/zoom 100` (o 90/110/125) lo agranda; `/zoom auto` deja
  que la pantalla elija. En el terminal el tamano de la letra es `/fonte`.

## Ver la pantalla y leer sitios con login (0.2.37 a 0.2.39)

- `ver_pagina`: el TEO abre tu pagina (archivo .html o direccion) en un navegador
  de verdad y MIRA: el texto que solo aparece despues del JavaScript, los errores
  de consola y una captura de pantalla. Sirve para revisar lo que el TEO acaba de
  construir (ciclo de desarrollo) y para leer pagina que arma el contenido con
  JavaScript. No pide permiso - es lo mismo que abrir y mirar.
- `ver_tela`: captura de TU pantalla, para el caso de sitio con login: entras en
  tu navegador, dejas la pagina abierta y pides "mira mi pantalla". Pide permiso
  antes de capturar, porque la captura lleva todo lo que este abierto.
- Sitios con login, leyendo el TEXTO (mejor que imagen para lista de correos,
  informes y tablas): `/site abrir https://...` abre una ventana del navegador
  del TEO para que TU entres; cierras la ventana y pides la lectura. Si el sitio
  ofrece "mantener la sesion", marcalo - la cookie de sesion sola no se guarda.
- `/site` muestra si hay login guardado; `/site esquecer` borra todo (cookies y
  sesiones). El TEO nunca teclea contrasenas, nunca hace clic en "entrar" y no
  automatiza sesion: quien entra eres tu.
- El navegador del TEO usa un perfil propio (`~/.bgh/navegador`), separado de tu
  navegador personal - no toca tus contrasenas ni tus pestanas.
- Las tablas de la respuesta ahora salen como tabla de verdad en la pantalla del
  navegador, y la ruta de un documento (incluido .html) se vuelve un enlace que
  abre en otra ventana.

## Seguridad (menu simple para el usuario)

- Comando seguro: corre sin preguntar.
- Borrar archivo (aunque sea uno solo), sobrescribir existente, codigo Python que
  borra, disco, servicio, sudo, pip install: siempre piden permiso en una pantalla
  clara con menu numerico:
  `[1] Si, esta vez  [2] Si, y no preguntar de nuevo en esta conversacion  [3] Si,
  siempre (cuando tiene sentido)  [4] No / cancelar` - solo Enter o numero erroneo =
  NO.
- "Siempre" se vuelve regla permanente en `command_allowlist` en config.json;
  revisala con `bgh approvals` (o `bgh approvals remove <n>` / `bgh approvals clear`).
- Piso duro que ninguna aprobacion cruza: rm -rf /, bomba de procesos, dd en disco
  fisico.
- Escritura en ruta sensible (/etc, ~/.ssh, .env) pide aprobacion.
- Un comando que toca varias reglas peligrosas pide permiso UNA SOLA VEZ, listando
  las preocupaciones juntas - antes eran varias preguntas seguidas.
- Permiso pendiente en la pantalla fija: el menu aparece en el area de mensajes y el
  pie cambia a "PERMISO PENDIENTE"; la persona responde el numero + ENTER (o ESC =
  no).

## Autonomia (resolver solo, sin bucle infinito)

- Falto una biblioteca Python? El TEO confirma que falta, busca el nombre correcto si
  hace falta, llama `instalar_pacote(pacote, motivo)` - el permiso aparece para el
  usuario con el motivo en lenguaje simple - instala por pip y sigue la tarea.
  `pip install` por `run_command` pasa por el mismo permiso (sin salida lateral).
- Recordatorio: cuando la persona pide "avisame en 20 minutos", el TEO marca un aviso en
  su propia pantalla (con bip y notificacion, si el `/aviso` esta activado) - vale
  mientras el TEO este abierto, y el TEO lo dice en la respuesta.
- Documentos en `.docx`, `.xlsx` y `.pdf`: el `make_document` crea los tres. La
  biblioteca que falte (python-docx, openpyxl o reportlab) se instala EN EL MOMENTO con
  el mismo permiso - el paquete del TEO no crece por ellas.
- Anti-bucle (regla dura): una llamada IDENTICA repetida 3 veces se corta antes de
  ejecutar ("BUCLE DETECTADO"); 5 fallas en secuencia cierran el turno con una
  explicacion al usuario, en vez de insistir para siempre. El limite de rondas por
  turno sigue como tope final.

## Como aprende

- `memory` (SQLite en ~/.bgh/memory.db): target=user guarda quien es el usuario y
  como le gustan las respuestas; target=note guarda datos de la maquina. Todo vuelve
  al system prompt de las proximas conversaciones.
- La memoria se busca por ASUNTO (indice FTS5 del SQLite, con busqueda simple cuando la
  build no lo tiene): lo que encaja con el pedido viaja con el mensaje, asi una
  preferencia vieja vuelve cuando aparece el asunto. Pedido permanente ("me llamo...",
  "prefiero...", "de ahora en adelante...") queda guardado aunque el modelo lo olvide.
- `skill` (SKILL.md en ~/.bgh/skills): al descubrir un procedimiento que funciono,
  el TEO crea/actualiza su skill. Las skills de fabrica en `skills/` del repo se
  copian en el setup y sirven de base.

## Layout

```
bgh/                paquete del agente
  cli.py            entrada de los comandos (chat / setup / doctor / approvals)
  i18n.py           cada frase de pantalla en los 3 idiomas (pt/en/es)
  tui.py            PANTALLA FIJA (prompt_toolkit): entrada abajo, scroll, boton parar
  chat_core.py      nucleo del chat compartido por las dos pantallas (comandos, turnos)
  agent.py          bucle + streaming + compresion + sesion + boton de parar
  llm.py            cliente compatible con OpenAI (stream + reasoning + thinking toggle)
  approvals.py      gate de permisos (menu numerico)
  prompts.py        system prompt por idioma (identidad + memoria + skills)
  palco.py          recorrido del pedido dibujado mientras el TEO trabaja
  assets/           el icono del gato (png/ico/svg) usado por el atajo del escritorio
  tools/            run_command (interrumpible), run_python, read/write/search, web, memory, skill, documento, recordatorio
  skills_default/   skills de fabrica (copiadas a ~/.bgh/skills en el setup)
tests/test_smoke.py pruebas offline (sin modelo)
pyproject.toml      empaquetado (wheel)
build.sh            genera wheel + binario unico
scripts/            instaladores para Windows/macOS/Linux + make_icons.py
```

Todo el estado del usuario vive en `~/.bgh/` (config.json 600, memory.db, skills/,
session.json).

## Pruebas

```bash
.venv/bin/python tests/test_smoke.py
```

## Distribuir sin clonar el repo

```bash
bash build.sh
```

Genera en dist/:
- `bgh_motor-<version>-py3-none-any.whl` (vale para Windows, macOS y Linux) - en la
  maquina del cliente: `pip install bgh_motor-*.whl` y el comando `bgh` existe.
- `motor` - binario unico para Linux (misma maquina/arquitectura): copiar al cliente
  y ejecutar `./motor`. Los binarios `motor.exe` (Windows) y `motor-macos` (macOS)
  los genera GitHub Actions en cada tag y se adjuntan al Release.

## Documentacion

- `docs/ARQUITETURA.md` - como funciona el TEO por dentro (modulos, seguridad, boton de parar, pruebas, empaquetado).
- `docs/CHANGELOG.md` - lo que entrega cada version.

## Roadmap proxima ronda

- Menu de permisos tambien en el modo no interactivo (cron/-q) con `--yes`.
- Empaquetar para otras distribuciones (el binario `motor` se genera en la maquina destino).

===============================================================================
>>>>  LEE ESTO ANTES DE CERRAR LA PAGINA  <<<<
===============================================================================

El TEO nacio de las manos de un desarrollador brasileno, hecho desde cero, y sigue
siendo suyo y tuyo: el programa es abierto, el codigo es tuyo, para siempre.

Pero hay un costo invisible detras de la pantalla: el cerebro que hace pensar al TEO
cuando el servidor local del usuario no da abasto. Si el TEO ya te ayudo a escribir
un correo, arreglar una carpeta, sacar factura de una foto o resolver lo que sea en
tu maquina, hay una forma simple y directa de devolver:

              >>>>  SUSCRIBETE A IA.NUBESBR.COM  <<<<

              https://ia.nubesbr.com

Tu suscripcion paga el servidor que hace pensar al TEO y mantiene vivo este
proyecto - sin propaganda, sin vender tus datos, sin trampa. Quien se suscribe usa el
modelo del servidor al lado del TEO: solo registra el proveedor (el TEO pide la
clave una vez) y conversa.

Cada suscripcion financia la proxima version. Gracias por llegar hasta el final del
README - quien lee todo merece saber quien mantiene la luz encendida.

===============================================================================

## Licencia

MIT (archivo `LICENSE` en la raiz): usa, estudia, modifica y distribuye.

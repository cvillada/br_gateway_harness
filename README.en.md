[Portugues](README.md) | **English** | [Espanol](README.es.md)

# TEO (bgh) - local CLI agent for the user's machine

TEO is the nickname of this harness (br_gateway_harness): the name of the author's
black cat.

A lean harness in Python: agent loop + any OpenAI-compatible endpoint (local or
API), real tools (shell, files, Python, web, documents), persistent memory and
skills that TEO itself creates as it learns. Approval model mirroring Hermes
Agent: safe commands run directly, dangerous ones ask for human permission.

## Installation by operating system (TEO folder + virtual environment)

The pattern is the same on all three systems: create a folder called TEO, create a
virtual environment inside it and install the wheel downloaded from the repo's
Releases page.

### Windows (two-click route - for children and elders)

1. First install Python 3.11 or newer: open https://python.org, click "Download",
   open the downloaded file and tick the box "Add python.exe to PATH" (that is once
   in a lifetime).
2. Open this page in the browser and download the file `INSTALAR_TEO.bat`:
   https://github.com/cvillada/br_gateway_harness/releases/latest
3. DOUBLE-CLICK the `INSTALAR_TEO.bat` file in your Downloads folder.
   Done: it downloads TEO, creates the TEO folder, installs, creates a **TEO** icon
   on the desktop and opens the program by itself. From then on it is just two
   clicks on the TEO icon - no need to touch the Command Prompt ever again.
   (Closing the TEO window closes only that conversation; the icon reopens everything.)

If Windows shows the blue warning "Windows protected your PC", click "More info"
and then the "Run anyway" button (it is because the file has no digital signature
yet; the code is in this very repo).

To chat again later: two clicks on the **TEO** icon on the desktop.
(If the icon does not appear, the shortcut is also at
`C:\Users\YOUR_USER\TEO\abrir-teo.bat`.)

#### Windows (technical route: 2 lines in the Command Prompt)

Requirement: Python 3.11 or newer (https://python.org; tick "Add python.exe to PATH").
Open the Command Prompt (cmd) and paste, one line at a time:

```batch
curl -L -o %USERPROFILE%\install_te.ps1 https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te_win.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File %USERPROFILE%\install_te.ps1
```

The script does everything alone: downloads the wheel from the newest Release,
creates the folder `%USERPROFILE%\TEO`, creates the virtual environment, copies the
wheel into it, runs pip install and opens TEO (the first time, the setup assistant
starts by itself).

To chat again: `cd %USERPROFILE%\TEO`, `.venv\Scripts\activate`, `bgh`.
Settings and history live in `C:\Users\YOUR_USER\.bgh`. Use Windows Terminal (it
comes with Windows 11); the old Command Prompt works, but with fewer visual
resources.

#### Windows (manual method, if you prefer step by step)

1. On the Releases page download the file `bgh_motor-...-py3-none-any.whl` (it goes
   to your user's Downloads folder; the version number appears in the middle of the
   file name).
2. Open the Command Prompt (cmd) and run, line by line. In the `pip` command,
   replace `version-number` with the number in the downloaded file name
   (e.g. 0.2.8):

```batch
mkdir TEO
cd TEO
python -m venv .venv
.venv\Scripts\activate
pip install "%USERPROFILE%\Downloads\bgh_motor-version-number-py3-none-any.whl"
bgh
```

If pip says the file does not exist, find out where it landed:

```batch
dir /s /b %USERPROFILE%\Downloads\bgh_motor*
```

and use the full path that appears in the command line above (or move the `.whl`
into the TEO folder and install it by name from inside it).
In PowerShell, replace `%USERPROFILE%` with `$env:USERPROFILE`.

3. To use it again in another session: `cd TEO`, `.venv\Scripts\activate`, `bgh`.

Settings and history live in `C:\Users\YOUR_USER\.bgh`. Use Windows Terminal (it
comes with Windows 11); the old Command Prompt works, but with fewer visual
resources.

### macOS (practical install: 2 lines)

Requirement: Python 3.11 or newer (if missing: install from
https://python.org/downloads or, if you have brew, `brew install python@3.12`).
Open Terminal and paste, one line at a time:

```bash
curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
bash install_te.sh
```

The script does everything alone: downloads the wheel from the newest Release,
creates the folder `~/TEO`, creates the virtual environment, copies the wheel into
it, runs pip install, creates a shortcut to open TEO without a terminal - an icon
called **TEO** on the desktop (on macOS, `TEO.app` in the Finder; on Linux, a `TEO`
launcher) - and opens the program (the first time, the setup assistant starts by
itself). The installer also asks the language (Portuguese, English or Spanish) and
the whole screen starts in it.

#### macOS (manual method, if you prefer step by step)

```bash
mkdir TEO && cd TEO
python3 -m venv .venv
source .venv/bin/activate
pip install ~/Downloads/bgh_motor-*.whl
bgh
```

If pip complains that it found more than one file, delete the old `.whl` files from
the Downloads folder and run the command again. To use it again: `cd TEO`,
`source .venv/bin/activate`, `bgh`. Settings and history live in `~/.bgh`.

### Linux (practical install: 2 lines)

Requirement: Python 3.11+ with venv (Ubuntu/Debian:
`sudo apt install python3 python3-venv`). In the terminal, one line at a time:

```bash
curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
bash install_te.sh
```

It works exactly as on macOS (same script): creates `~/TEO` + venv, downloads the
wheel from the newest Release, installs, creates the desktop shortcut with the cat
icon and opens TEO.

#### Linux (alternatives)

Straight from the cloned repo:

```bash
cd br_gateway_harness
bash install.sh   # installs and goes straight into the setup assistant (single flow)
bgh               # chatted, done
```

Or the manual method with venv (copying the wheel to `~/TEO`), same as macOS above.

### Without Python (any system)

Each Release brings the ready binary for your system: `motor.exe` (Windows),
`motor-macos` (macOS, for Macs with Apple chip - M1, M2, M3, M4) and `motor`
(Linux). Just download and run. Intel Mac: use the step by step with Python above
(works on any Mac). On Linux, run `motor` on the same distribution where it was
built (or use the Python route, which works on any of them).

The assistant can be redone at any moment with `bgh setup`. If the person opens TEO
without ever having configured it, the assistant starts by itself right away (no
command to memorize). In the assistant they choose the provider (1-4), confirm URL
and model name (Enter accepts the default), paste the key if the server asks - and
there is a connection test with self-correction: if it says "asks for a key", it
asks for the key right there and tests again. Everything lives in
`~/.bgh/config.json` with permission only for the user (600); the key is only sent
to the URL the user registered.

`bgh doctor` Diagnoses the user's machine and the connection to the model.

## Supported providers (setup presets)

| Preset | What it is | base_url |
|--------|------------|----------|
| deepseek | DeepSeek API (cloud, easiest) | https://api.deepseek.com/v1 |
| nubesbr  | hosted AI server (public) | https://ia.nubesbr.com/v1/ (adjustable) |
| local    | llama.cpp / LM Studio on this machine | http://127.0.0.1:30000/v1 |
| other    | any OpenAI-compatible endpoint | (you type it) |

Ready for 27B and larger models: configurable context budget
(`context_budget_chars`, default 156000), automatic conversation compression and a
tolerant dispatch for malformed JSON from quantized models. The setup assistant
inherits the server limit in three ways: a llama.cpp engine publishes `n_ctx`
(`props`), OpenRouter-style APIs publish `context_length`, and APIs that publish
nothing (DeepSeek, Anthropic...) come from the public models.dev catalog. The value
is set by itself - it never asks the user for a number; with no source at all, the
provider default applies. When the provider delivers more than the reading cap, the
footer warns ("cap; the server delivers N tokens"). Output per answer up to 8192
tokens (`max_tokens`), enough to write a ~28 thousand character HTML document in one
round; heavy writing sessions can use `/ctx 300000`. Fine tuning: `/ctx` on screen.

## Chatting

The chat opens like Hermes: the `you>` line always stays at the bottom and the
messages go into the terminal's own natural scrollback - the mouse wheel and the
scrollbar of YOUR terminal scroll the conversation, and when you leave the text is
still there to re-read. Without an interactive terminal (pipe/script) it falls back
to classic mode by itself. To turn the interactive screen off: `"tui": false` in
`~/.bgh/config.json`.

The window opens maximized and titled **TEO Agent**: in a small window the bottom
bar (meter, keys, "running" sign) would not fit. On Windows the maximization uses
the console API; on Linux and macOS the request is sent to the terminal, and a
terminal that does not accept it simply keeps its current size.

When you send a question, the request trail appears for a moment above the input
line: START -> AGENT -> TOOL -> MODEL -> SCREEN. The lit step is the one holding the
request at that moment, with the real time beside it, and the trail folds away when
the answer arrives (the trail only appears for a request to the agent: slash
commands and the file menu do not draw it). Below the steps are the tokens of each
piece (input under AGENT, output under MODEL, total under SCREEN), abbreviated:
800, 2.00k, 1.20M. To turn it off: `/stage off`.

Stopping and re-reading (designed for elders and children - a single touch):

| Key | What it does |
|-----|--------------|
| CTRL+C or ESC while answering | STOPS answering and gives the prompt back at once |
| ENTER with text while answering | warns the current turn; the model reads it on the next round |
| CTRL+C twice in a row | safety exit if something gets stuck |
| Mouse wheel or your terminal scrollbar | re-read the text that scrolled up |
| CTRL+C with an empty line | closes TEO (ESC never closes by itself) |
| Ctrl+J, or ending the line with `\` and ENTER | new line at the `you>` prompt (write on several lines; in Windows cmd Alt+Enter is full screen) |

The fixed bottom bar always says what to press; while answering it shows
"answering... TO STOP: CTRL+C or ESC".

Quick shortcuts (they do not ask permission, they only show):

| Shortcut | What it does |
|----------|--------------|
| `/` | on the fixed screen opens the menu of the current folder (pick by number); in simple mode, lists |
| `@` | on the fixed screen opens the file menu to attach; in simple mode, lists the files |
| `@<file>` | attaches the file; then just ask about it. PNG/JPG/WEBP/GIF/BMP go as an IMAGE to the model's vision (up to 5 MB); writing the image path in the message also attaches it |
| `/ls <folder>` | lists a specific folder (no menu) |

Commands:

| Command | What it does |
|---------|--------------|
| `/model` | lists the models published by the server |
| `/model <name or number>` | switches the model (saved in the config) |
| `/provider` | lists the registered providers (e.g. 1 deepseek, 2 local) |
| `/provider <name or number>` | switches the provider in use right now (saved) |
| `/thinking on\|off` | shows or hides the gray block on screen (the model keeps thinking); advanced: level sent to the server auto off minimum low medium high xhigh max ultra |
| `/stage on\|off` | shows or hides the request trail while answering (fixed screen only) |
| `/ctx` | context meter; `/ctx <number>` sets the limit and saves it (e.g. `/ctx 65000`; accepts 65k) |
| `/setup` | fixes or registers a provider without leaving TEO (same assistant as `bgh setup`) |
| `/doctor` | connection and machine diagnosis on the screen itself |
| `/update` | checks for a new version on GitHub; if there is one, asks permission and installs (same version: says everything is fine) |
| `/mem <text>` | saves a preference of yours in the memory |
| `/language` | switches the screen language: 1) Portugues  2) English  3) Espanol (saved). Shortcuts: `/lingua`, `/idioma` |
| `/voz` | accessibility: reads every answer out loud with the system voice (speech-dispatcher/espeak on Linux, System.Speech on Windows, `say` on macOS); type it again to turn off; ESC silences. Shortcut: `/voice` |
| `/fundo` | screen background color: white, yellow, green, blue, red, black or `default`; the letters change on their own to stay readable (light background = dark letters). Shortcut: `/background` |
| `/fonte` | letter size: 1 normal, 2 large, 3 larger, 4 huge. On Windows it changes right away; on Linux/macOS it reopens the window with zoom (or teaches your terminal keys). Shortcut: `/font` |
| `/ditar` | accessibility: write by SPEAKING. TEO listens to the microphone, transcribes in the screen language and puts the text on the line for you to check before ENTER. The language model (pt/en/es, ~55 MB) is downloaded once on first use; after that it works offline and the sound never leaves your computer. Shortcuts: `/ditar`, `/dictar` |
| `/limpar` | deletes the drafts TEO creates in the `scratch` folder (run_python scripts and voice texts) and reports the space freed; it asks first and never touches conversation, memory or skills. Shortcut: `/clean` |
| `/new` `/skills` `/help` `/exit` | new conversation, skills, help, quit |

Language: TEO speaks Portuguese (factory default), English and Spanish. The installer
asks the language at the start and `/language` switches it at any moment, right away
- banner, help, menus, permission, warnings and the bottom bar. Commands work in the
three languages on any screen language (`/ajuda`, `/nov`, `/modelo`, `/pensamento`,
`/sair`...), and the model starts answering in the chosen language (if the person
writes in another language, it answers in the language of the message).

New version: on startup TEO checks by itself (once, without blocking the screen)
whether there is a new version and says "a new TEO version is available (vX.Y.Z). To
update, type `/update`". With no internet it says it could not check and keeps
working; `update_check` in `~/.bgh/config.json` turns the check off.

Icon: the desktop shortcut comes with the TEO cat - Linux (`.desktop` with `Icon=`),
Windows (shortcut with `teo.ico` and the exe with the icon) and macOS (`TEO.app` built
with `teo.icns`). The icons live in `bgh/assets/` and are generated by
`scripts/make_icons.py` (no dependencies). If on macOS the shortcut shows up as a
white scroll (older install), run `scripts/consertar_icone_mac.sh`: it fixes it
without reinstalling.

- Model thinking: if the server returns `reasoning_content`/`reasoning` (llama.cpp
  with Qwen thinking, DeepSeek-R1 etc.), it appears as `thinking> ...` before the
  answer.
- Context: after each answer comes `context: NN% of 156000 chars`
  (green/yellow/red); at 85% the bottom bar turns to the alert color and the next
  heavy round compacts the conversation into a summary by itself (TEO says so on
  screen while compacting). If the server refuses the size, it compacts and tries
  again instead of stopping. The compaction point is adjustable:
  `context_compress_pct` in `~/.bgh/config.json`.

## Security (Hermes model, simple menu for the user)

- Safe command: runs without asking.
- Deleting a file (even a single one), overwriting an existing one, Python code that
  deletes, disk, service, sudo, pip install: they always ask permission in a clear
  screen with a numeric menu:
  `[1] Yes, this time  [2] Yes, and do not ask again in this conversation  [3] Yes,
  always (when it makes sense)  [4] No / cancel` - Enter alone or a wrong number =
  NO.
- "Always" becomes a permanent rule in `command_allowlist` in config.json; review it
  with `bgh approvals` (or `bgh approvals remove <n>` / `bgh approvals clear`).
- Hard floor no approval can cross: rm -rf /, fork bomb, dd onto a physical disk.
- Writing to a sensitive path (/etc, ~/.ssh, .env) asks for permission.
- A command that touches several dangerous rules asks for permission ONCE, listing
  the concerns together - before it was several questions in a row.
- Permission pending on the fixed screen: the menu appears in the message area and
  the footer changes to "PERMISSION PENDING"; the person answers the number + ENTER
  (or ESC = no).

## Autonomy (solving alone, without infinite loops)

- Missing a Python library? TEO confirms it is missing, looks up the right name if
  needed, calls `instalar_pacote(pacote, motivo)` - the permission appears to the user
  with the reason in simple words - installs via pip and goes on with the task.
  `pip install` through `run_command` goes through the same permission (no side door).
- Anti-loop (hard rule): an IDENTICAL call repeated 3 times is cut before running
  ("LOOP DETECTED"); 5 failures in a row close the turn with an explanation to the
  user, instead of insisting forever. The round limit per turn stays as the final cap.

## How it learns

- `memory` (SQLite in ~/.bgh/memory.db): target=user keeps who the user is and how
  they like answers; target=note keeps machine facts. Everything comes back into the
  system prompt of the next conversations.
- `skill` (SKILL.md in ~/.bgh/skills): when it finds a procedure that worked, TEO
  creates/updates its skill. Factory skills in the repo's `skills/` are copied at
  setup and serve as a base.

## Layout

```
bgh/                agent package
  cli.py            command entry (chat / setup / doctor / approvals)
  i18n.py           every on-screen phrase in the 3 languages (pt/en/es)
  tui.py            FIXED SCREEN (prompt_toolkit): input at the bottom, scrolling, stop button
  chat_core.py      chat core shared by both screens (commands, turns)
  agent.py          loop + streaming + compression + session + stop button
  llm.py            OpenAI-compatible client (stream + reasoning + thinking toggle)
  approvals.py      permission gate (Hermes model)
  prompts.py        system prompt per language (identity + memory + skills)
  palco.py          request trail drawn while TEO works
  assets/           the cat icon (png/ico/svg) used by the desktop shortcut
  tools/            run_command (interruptible), run_python, read/write/search, web, memory, skill, document
  skills_default/   factory skills (copied to ~/.bgh/skills at setup)
tests/test_smoke.py offline tests (no model)
pyproject.toml      packaging (wheel)
build.sh            builds wheel + single binary
scripts/            installers for Windows/macOS/Linux + make_icons.py
```

All user state lives in `~/.bgh/` (config.json 600, memory.db, skills/, session.json).

## Tests

```bash
.venv/bin/python tests/test_smoke.py
```

## Distributing without cloning the repo

```bash
bash build.sh
```

It generates in dist/:
- `bgh_motor-<version>-py3-none-any.whl` (works on Windows, macOS and Linux) - on the
  client machine: `pip install bgh_motor-*.whl` and the `bgh` command exists.
- `motor` - single binary for Linux (same machine/architecture): copy it to the
  client and run `./motor`. The `motor.exe` (Windows) and `motor-macos` (macOS)
  binaries are built by GitHub Actions on each tag and attached to the Release.

## Documentation

- `docs/ARQUITETURA.md` - how TEO works inside (modules, security, stop button, tests, packaging).
- `docs/CHANGELOG.md` - what each version delivers.

## Next round roadmap

- Permission menu also in non-interactive mode (cron/-q) with `--yes`.
- Package for other distributions (the `motor` binary is built on the target machine).

===============================================================================
>>>>  READ THIS BEFORE CLOSING THE PAGE  <<<<
===============================================================================

TEO was born from the hands of a Brazilian developer, built from scratch, and it
stays his and yours: the program is open, the code is yours, forever.

But there is an invisible cost behind the screen: the brain that makes TEO think
when the user's local server cannot handle it. If TEO has already helped you write
an e-mail, fix a folder, turn a photo into an invoice or solve whatever on your
machine, there is a simple and direct way to give back:

              >>>>  SUBSCRIBE IA.NUBESBR.COM  <<<<

              https://ia.nubesbr.com

Your subscription pays for the server that makes TEO think and keeps this project
alive - no ads, no selling your data, no tricks. Subscribers use the server model
side by side with TEO: just register the provider (TEO asks for the key once) and
talk.

Each subscription funds the next version. Thank you for reaching the end of the
README - whoever reads everything deserves to know who keeps the light on.

===============================================================================

## License

MIT (file `LICENSE` at the root): use, study, modify and distribute.

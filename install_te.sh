#!/usr/bin/env bash
# Instala o TEO no macOS e no Linux do inicio ao fim:
#   pergunta o idioma, baixa o wheel do Release mais novo, cria a pasta ~/TEO, cria o
#   ambiente virtual, copia o wheel para la, roda o pip install, cria o atalho COM o
#   icone do gato e abre o programa.
# Uso (terminal):
#   curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
#   bash install_te.sh
set -e
REPO="cvillada/br_gateway_harness"
DIR="$HOME/TEO"

# --- Idioma da interface do TEO (as mensagens do instalador sao em portugues) ---
IDIOMA=pt
if [ -t 0 ]; then
    echo "Idioma / Language / Idioma: 1) Portugues  2) English  3) Espanol"
    printf "Opcao [1]: "
    read -r OPCAO_IDIOMA || true
    case "$OPCAO_IDIOMA" in
        2|en|EN|En|english|English) IDIOMA=en ;;
        3|es|ES|Es|espanol|Espanol) IDIOMA=es ;;
        *) IDIOMA=pt ;;
    esac
fi

echo "Procurando a versao mais recente do TEO..."
JSON=$(curl -s "https://api.github.com/repos/$REPO/releases/latest")
URL=$(echo "$JSON" | grep -oE '"browser_download_url": *"[^"]*\.whl"' | head -1 | sed -E 's/.*"(https[^"]*)".*/\1/')
if [ -z "$URL" ]; then echo "NAO encontrei arquivo .whl no Release mais novo."; exit 1; fi
NAME=$(basename "$URL")

mkdir -p "$DIR"
cd "$DIR"
echo "Pasta criada: $DIR"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
    echo "Python nao encontrado. Instale Python 3.11+ primeiro (no macOS: brew install python@3.12; no Ubuntu/Debian: sudo apt install python3 python3-venv)."
    exit 1
fi

echo "Criando ambiente virtual (.venv)..."
if [ "$(uname)" = "Darwin" ]; then
    echo "  (se o macOS oferecer 'Instalar ferramentas do desenvolvedor', clique em Instalar e aguarde)"
fi
"$PY" -m venv .venv

# Wheels de instalacoes anteriores sobram na pasta e confundem (a pessoa acha
# que o arquivo velho e o programa novo). Limpa antes de baixar o atual.
rm -f "$DIR"/bgh_motor-*.whl

echo "Baixando $NAME ..."
curl -L -o "$DIR/$NAME" "$URL"

echo "Instalando no ambiente virtual..."
PYBIN="$DIR/.venv/bin/python"
"$PYBIN" -m pip install --upgrade pip > /dev/null
curl -L -o "$DIR/requirements.txt" \
  "https://raw.githubusercontent.com/$REPO/main/requirements.txt"
"$PYBIN" -m pip install -r "$DIR/requirements.txt" > /dev/null
# --ignore-installed e o que salva instalacao quebrada: se o bgh antigo ficou SEM
# RECORD (o pip nao consegue desinstalar), --force-reinstall sozinho falha com
# "uninstall-no-record-file". Com ignore-installed o pip sobrescreve os arquivos.
if ! "$PYBIN" -m pip install --no-deps --ignore-installed --force-reinstall "$DIR/$NAME"; then
    echo "Tentando de novo com limpeza dos restos da instalacao anterior..."
    rm -rf "$DIR"/.venv/lib/python*/site-packages/bgh_motor* 2>/dev/null || true
    "$PYBIN" -m pip install --no-deps --ignore-installed "$DIR/$NAME"
fi
VER=$("$PYBIN" -c "import bgh; print(bgh.__version__)" 2>/dev/null || true)
echo "Versao instalada: ${VER:-desconhecida}"

# Icone do gato que vem DENTRO do pacote instalado (nada extra para baixar).
ICONE_DIR=$("$PYBIN" -c "import bgh, os; print(os.path.join(os.path.dirname(bgh.__file__), 'assets'))" 2>/dev/null || true)

echo "Criando atalho para abrir sem terminal..."
cat > "$DIR/abrir-teo.sh" <<EOF
#!/usr/bin/env bash
# Abre o TEO (liga o ambiente virtual sozinho).
cd "$DIR"
source .venv/bin/activate
exec bgh
EOF
chmod +x "$DIR/abrir-teo.sh"

if [ "$(uname)" = "Darwin" ]; then
    DESK="$HOME/Desktop"
    mkdir -p "$DESK"
    cat > "$DESK/TEO.command" <<EOF
#!/usr/bin/env bash
cd "$DIR"
source .venv/bin/activate
exec bgh
EOF
    chmod +x "$DESK/TEO.command"
    # --- atalho COM o gato: TEO.app montado a mao ---------------------------
    # Osacompile + applet.icns deixava a Area de trabalho com o TEO.command
    # (pergaminho branco) em parte dos Macs: aqui o bundle e montado arquivo por
    # arquivo, com o icone no nome que o proprio Info.plist aponta.
    APP="$DESK/TEO.app"
    ICNS="$DIR/teo.icns"
    if [ -n "$ICONE_DIR" ] && [ -f "$ICONE_DIR/teo.png" ] \
       && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
        ICONSET="${TMPDIR:-/tmp}/teo.iconset"
        rm -rf "$ICONSET"
        mkdir -p "$ICONSET"
        for TAM in 16 32 128 256 512; do
            sips -z "$TAM" "$TAM" "$ICONE_DIR/teo.png" --out "$ICONSET/icon_${TAM}x${TAM}.png" >/dev/null 2>&1 || true
            DOBRO=$((TAM * 2))
            sips -z "$DOBRO" "$DOBRO" "$ICONE_DIR/teo.png" --out "$ICONSET/icon_${TAM}x${TAM}@2x.png" >/dev/null 2>&1 || true
        done
        iconutil -c icns "$ICONSET" -o "$ICNS" >/dev/null 2>&1 || true
        rm -rf "$ICONSET"
    fi
    rm -rf "$APP"
    mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
    cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>TEO</string>
    <key>CFBundleDisplayName</key><string>TEO</string>
    <key>CFBundleIdentifier</key><string>com.nubesbr.teo</string>
    <key>CFBundleVersion</key><string>${VER:-1.0}</string>
    <key>CFBundleShortVersionString</key><string>${VER:-1.0}</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>teo</string>
    <key>CFBundleIconFile</key><string>teo.icns</string>
    <key>LSMinimumSystemVersion</key><string>10.13</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
    # `open -a Terminal arquivo.sh` = mesmo caminho do duplo clique no .command,
    # e aceita caminho com espaco (sem osascript de aspas aninhadas).
    cat > "$APP/Contents/MacOS/teo" <<SH
#!/bin/bash
exec /usr/bin/open -a Terminal "$DIR/abrir-teo.sh"
SH
    chmod +x "$APP/Contents/MacOS/teo"
    if [ -f "$ICNS" ]; then
        cp -f "$ICNS" "$APP/Contents/Resources/teo.icns"
    fi
    # mtime novo: e assim que o Finder percebe que o icone mudou
    touch "$APP/Contents/Info.plist" "$APP/Contents/Resources" "$APP" 2>/dev/null || true
    if [ -f "$APP/Contents/Resources/teo.icns" ]; then
        echo "Icone do gato criado na Area de trabalho: TEO.app (dois cliques)."
    else
        echo "Atalho TEO criado, mas SEM o icone do gato (faltou sips/iconutil no sistema)."
    fi
    echo "O TEO.command tambem fica na Area de trabalho (icone de pergaminho, so reserva)."
    echo "Se o sistema pedir uma permissao na primeira vez, aceite ('Abrir')."
else
    DESK=$(xdg-user-dir DESKTOP 2>/dev/null || true)
    if [ -z "$DESK" ]; then DESK="$HOME/Desktop"; fi
    mkdir -p "$DESK"
    ICONE_LINHA=""
    if [ -n "$ICONE_DIR" ] && [ -f "$ICONE_DIR/teo.png" ]; then
        cp -f "$ICONE_DIR/teo.png" "$DIR/teo.png" 2>/dev/null || true
        cp -f "$ICONE_DIR/teo.svg" "$DIR/teo.svg" 2>/dev/null || true
        # tema de icones do usuario (menus, lancadores) + caminho absoluto no atalho
        mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps" \
                 "$HOME/.local/share/icons/hicolor/scalable/apps" 2>/dev/null || true
        cp -f "$ICONE_DIR/teo.png" "$HOME/.local/share/icons/hicolor/256x256/apps/teo.png" 2>/dev/null || true
        cp -f "$ICONE_DIR/teo.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/teo.svg" 2>/dev/null || true
        ICONE_LINHA="Icon=$DIR/teo.png"
    fi
    cat > "$DESK/TEO.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TEO
Comment=Conversar com o TEO
Exec=bash "$DIR/abrir-teo.sh"
$ICONE_LINHA
Terminal=true
Categories=Utility;
EOF
    chmod +x "$DESK/TEO.desktop"
    gio set "$DESK/TEO.desktop" metadata::trusted true 2>/dev/null || true
    echo "Atalho 'TEO' criado na Area de trabalho. Se ele aparecer apagado, clique com o"
    echo "botao direito e escolha 'Permitir Lancamento' / 'Confiar' uma unica vez."
fi

echo ""
echo "TEO instalado em $DIR"
echo "Para conversar outra vez, abra o terminal e digite:"
echo "  cd ~/TEO"
echo "  source .venv/bin/activate"
echo "  bgh"
echo ""
if [ "${TEO_NO_RUN:-0}" = "1" ]; then
    echo "(TEO_NO_RUN=1: instalacao concluida, sem abrir o programa agora)"
else
    # Primeira execucao: o assistente ja abre no idioma escolhido (sem perguntar duas vezes).
    if [ ! -f "$DIR/config.json" ] && [ ! -f "$HOME/.bgh/config.json" ] \
       && [ ! -f "${BGH_HOME:-/nao-existe}/config.json" ]; then
        echo "Abrindo o assistente de configuracao do TEO (idioma: $IDIOMA)..."
        "$DIR/.venv/bin/bgh" setup --lang "$IDIOMA" || true
    fi
    echo "Abrindo o TEO agora..."
    exec "$DIR/.venv/bin/bgh"
fi

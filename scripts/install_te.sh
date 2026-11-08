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
    # App com o gato no Dock/Finder (o .command acima fica como reserva).
    if [ -n "$ICONE_DIR" ] && [ -f "$ICONE_DIR/teo.png" ] && command -v osacompile >/dev/null 2>&1; then
        ICONSET="${TMPDIR:-/tmp}/teo.iconset"
        rm -rf "$ICONSET"
        mkdir -p "$ICONSET"
        for TAM in 16 32 128 256 512; do
            sips -z "$TAM" "$TAM" "$ICONE_DIR/teo.png" --out "$ICONSET/icon_${TAM}x${TAM}.png" >/dev/null 2>&1 || true
            DOBRO=$((TAM * 2))
            sips -z "$DOBRO" "$DOBRO" "$ICONE_DIR/teo.png" --out "$ICONSET/icon_${TAM}x${TAM}@2x.png" >/dev/null 2>&1 || true
        done
        if iconutil -c icns "$ICONSET" -o "$DIR/teo.icns" >/dev/null 2>&1; then
            rm -rf "$DESK/TEO.app"
            if osacompile -o "$DESK/TEO.app" \
                -e "tell application \"Terminal\" to do script \"bash '$DIR/abrir-teo.sh'\"" >/dev/null 2>&1; then
                cp -f "$DIR/teo.icns" "$DESK/TEO.app/Contents/Resources/applet.icns" 2>/dev/null || true
                touch "$DESK/TEO.app" 2>/dev/null || true
                echo "Icone do gato criado na Area de trabalho do Finder: TEO (dois cliques)."
            fi
        fi
        rm -rf "$ICONSET"
    fi
    [ -d "$DESK/TEO.app" ] || echo "Icone criado na Area de trabalho do Finder: TEO (dois cliques)."
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

#!/usr/bin/env bash
# Conserta o icone do TEO no macOS (o gato no atalho da Area de trabalho).
#
# Por que existe: o instalador antigo montava o atalho com `osacompile` e copiava
# o .icns por cima do "applet.icns". Quando isso nao pega (cache do Finder, versao
# do macOS), a Area de trabalho fica com o TEO.command - e o macOS desenha o
# "pergaminho branco" (icone generico de arquivo/script) em vez do gato.
#
# O que este script faz, sem reinstalar nada:
#   1. acha a pasta do TEO (~/TEO por padrao) e o icone que veio DENTRO do pacote;
#   2. gera ~/TEO/teo.icns com sips + iconutil (ferramentas do proprio macOS);
#   3. MONTA o TEO.app a mao (Info.plist + executavel + Resources/teo.icns) -
#      sem osacompile, sem depender de cache de applet;
#   4. avisa no fim o que fez e o que fazer se o Finder insistir no icone velho.
#
# Uso (terminal):
#   curl -L -o ~/consertar_icone.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/consertar_icone_mac.sh
#   bash ~/consertar_icone.sh
#
# Opcoes: --teo-dir <pasta>  --destino <pasta>  --refrescar-finder
set -u

TEO_DIR="$HOME/TEO"
DESTINO="$HOME/Desktop"
REFRESCAR=0

while [ $# -gt 0 ]; do
    case "$1" in
        --teo-dir) TEO_DIR="${2:-}"; shift 2 ;;
        --destino) DESTINO="${2:-}"; shift 2 ;;
        --refrescar-finder) REFRESCAR=1; shift ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "Opcao desconhecida: $1"; exit 2 ;;
    esac
done

SISTEMA="$(uname)"
echo "== TEO: conserto do icone"
echo "Sistema: $SISTEMA"
echo "Pasta do TEO: $TEO_DIR"

if [ ! -d "$TEO_DIR" ]; then
    echo "NAO encontrei a pasta $TEO_DIR."
    echo "Se o TEO foi instalado em outro lugar, rode de novo com: --teo-dir <pasta>"
    exit 1
fi

# Diagnostico do que existe hoje na Area de trabalho (o "pergaminho branco" e o
# TEO.command; o app com o gato e o TEO.app).
echo "Antes de mexer, na Area de trabalho:"
if [ -d "$DESTINO/TEO.app" ]; then
    echo "  TEO.app  -> existe ($(du -sh "$DESTINO/TEO.app" 2>/dev/null | cut -f1))"
else
    echo "  TEO.app  -> NAO existe (por isso so apareceu o pergaminho)"
fi
if [ -f "$DESTINO/TEO.command" ]; then
    echo "  TEO.command -> existe (este e o icone de pergaminho branco)"
else
    echo "  TEO.command -> nao existe"
fi

# 1) icone que veio DENTRO do pacote instalado (fonte da verdade)
PYBIN="$TEO_DIR/.venv/bin/python"
ICONE_DIR=""
if [ -x "$PYBIN" ]; then
    ICONE_DIR="$("$PYBIN" -c "import bgh, os; print(os.path.join(os.path.dirname(bgh.__file__), 'assets'))" 2>/dev/null || true)"
fi
if [ -z "$ICONE_DIR" ] || [ ! -f "$ICONE_DIR/teo.png" ]; then
    echo "NAO achei o icone dentro do pacote instalado (bgh/assets/teo.png)."
    echo "Reinstale com o install_te.sh novo (ele traz o icone) e rode este script de novo."
    exit 1
fi
echo "Icone do pacote: $ICONE_DIR/teo.png"

# 2) .icns a partir do PNG (sips redimensiona, iconutil empacota)
ICNS="$TEO_DIR/teo.icns"
gerar_icns() {
    if [ "${TEO_ICONE_TESTE:-0}" = "1" ]; then
        # modo de teste (nao-macOS): usa o proprio PNG para exercitar a estrutura
        cp -f "$ICONE_DIR/teo.png" "$ICNS"
        return 0
    fi
    command -v sips >/dev/null 2>&1 || return 1
    command -v iconutil >/dev/null 2>&1 || return 1
    ICONSET="${TMPDIR:-/tmp}/teo.iconset"
    rm -rf "$ICONSET"
    mkdir -p "$ICONSET"
    for TAM in 16 32 128 256 512; do
        sips -z "$TAM" "$TAM" "$ICONE_DIR/teo.png" --out "$ICONSET/icon_${TAM}x${TAM}.png" >/dev/null 2>&1 || true
        DOBRO=$((TAM * 2))
        sips -z "$DOBRO" "$DOBRO" "$ICONE_DIR/teo.png" --out "$ICONSET/icon_${TAM}x${TAM}@2x.png" >/dev/null 2>&1 || true
    done
    iconutil -c icns "$ICONSET" -o "$ICNS" >/dev/null 2>&1 || { rm -rf "$ICONSET"; return 1; }
    rm -rf "$ICONSET"
    return 0
}

if gerar_icns && [ -f "$ICNS" ]; then
    echo "Icone .icns gerado: $ICNS ($(wc -c < "$ICNS" | tr -d ' ') bytes)"
else
    echo "NAO consegui gerar o .icns (faltou sips/iconutil?)."
    echo "O TEO.app abaixo fica com o icone padrao de aplicativo; o gato nao entra."
    ICNS=""
fi

# 3) TEO.app montado a mao (o Finder respeita melhor que o applet do osacompile)
APP="$DESTINO/TEO.app"
VER=""
if [ -x "$PYBIN" ]; then
    VER="$("$PYBIN" -c "import bgh; print(bgh.__version__)" 2>/dev/null || true)"
fi
mkdir -p "$DESTINO"
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

# Executavel do app: abre uma janela do Terminal rodando o abrir-teo.sh.
# `open -a Terminal arquivo.sh` e o mesmo caminho do duplo clique no .command e
# aceita caminho com espaco (por isso nao montamos osascript com aspas aninhadas).
cat > "$APP/Contents/MacOS/teo" <<SH
#!/bin/bash
exec /usr/bin/open -a Terminal "$TEO_DIR/abrir-teo.sh"
SH
chmod +x "$APP/Contents/MacOS/teo"

if [ -n "$ICNS" ]; then
    cp -f "$ICNS" "$APP/Contents/Resources/teo.icns"
fi
# mtime novo nos tres arquivos: e assim que o Finder percebe que o icone mudou
touch "$APP/Contents/Info.plist" "$APP/Contents/Resources" "$APP" 2>/dev/null || true

echo "TEO.app montado em: $APP"
echo "  executavel: Contents/MacOS/teo"
echo "  icone:      Contents/Resources/teo.icns ${ICNS:-(ausente)}"

# 4) o .command continua como reserva (mas ele E o pergaminho branco)
cat > "$DESTINO/TEO.command" <<EOF
#!/usr/bin/env bash
cd "$TEO_DIR"
source .venv/bin/activate
exec bgh
EOF
chmod +x "$DESTINO/TEO.command"
echo "Reserva: TEO.command (esse e o icone de pergaminho - use o TEO.app)."

if [ "$REFRESCAR" = "1" ]; then
    echo "Reiniciando o Finder para limpar o cache de icone..."
    killall Finder >/dev/null 2>&1 || true
fi

echo ""
echo "Pronto. Abra o TEO pelo TEO.app da Area de trabalho."
echo "Se o icone AINDA aparecer como pergaminho (cache do Finder):"
echo "  - arraste o TEO.app para fora da Area de trabalho e de volta, ou"
echo "  - rode de novo com: bash $0 --refrescar-finder"
echo "  - e confirme que voce esta clicando no TEO.app (icone de aplicativo),"
echo "    nao no TEO.command (pergaminho)."
if [ "$SISTEMA" != "Darwin" ] && [ "${TEO_ICONE_TESTE:-0}" != "1" ]; then
    echo ""
    echo "AVISO: este script e para macOS; aqui ele so conferiu a estrutura."
fi

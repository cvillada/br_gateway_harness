#!/usr/bin/env bash
# Instala o TEO no macOS e no Linux do inicio ao fim:
#   baixa o wheel do Release mais novo, cria a pasta ~/TEO, cria o ambiente virtual,
#   copia o wheel para la, roda o pip install e abre o programa.
# Uso (terminal):
#   curl -L -o install_te.sh https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te.sh
#   bash install_te.sh
set -e
REPO="cvillada/br_gateway_harness"
DIR="$HOME/TEO"

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
"$PY" -m venv .venv

echo "Baixando $NAME ..."
curl -L -o "$DIR/$NAME" "$URL"

echo "Instalando no ambiente virtual..."
"$DIR/.venv/bin/pip" install --upgrade pip > /dev/null
"$DIR/.venv/bin/pip" install "$DIR/$NAME"

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
    echo "Abrindo o TEO agora (na primeira vez ele pede a configuracao)..."
    exec "$DIR/.venv/bin/bgh"
fi

#!/usr/bin/env bash
# Instalacao de uma linha: bash install.sh
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

chmod +x bin/bgh
mkdir -p "$HOME/.local/bin"
ln -sf "$PWD/bin/bgh" "$HOME/.local/bin/bgh"

echo ""
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "Aviso: adicione ao PATH e reabra o terminal: export PATH=\"\$HOME/.local/bin:\$PATH\"";;
esac

# Deixa o cliente ja no chat configurando (fluxo unico, sem comando extra para decorar).
if [ -t 0 ]; then
    echo ""
    echo "Vamos configurar o modelo agora (1 minuto, perguntas de uma linha cada; Enter aceita o padrao)."
    "$PWD/bin/bgh" setup
    echo ""
    echo "Para conversar depois, um unico comando: bgh   (ou $PWD/bin/bgh)"
else
    echo "Instalado. Proximo passo (um unico comando):"
    echo "    bgh setup"
fi

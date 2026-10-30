#!/usr/bin/env bash
# Empacota o Motor: roda em qualquer maquina sem clonar o repo.
#   dist/*.whl          -> pip install dist/bgh_motor-*.whl  (cria o comando 'bgh')
#   dist/motor          -> binario unico, e so copiar e rodar
set -e
cd "$(dirname "$0")"

.venv/bin/pip install -q build pyinstaller
rm -rf build dist *.egg-info
.venv/bin/python -m build --wheel
.venv/bin/pyinstaller --onefile --clean --noconfirm --log-level=WARN \
    --name motor \
    --add-data "bgh/skills_default:bgh/skills_default" \
    motor_entry.py

echo ""
echo "Artefatos gerados:"
ls -lh dist/ | grep -E "whl|motor$" || ls -lh dist/

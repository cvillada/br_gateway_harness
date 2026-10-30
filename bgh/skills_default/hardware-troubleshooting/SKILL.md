---
name: hardware-troubleshooting
description: Use when o usuario relata problema de hardware: lentidao, calor, disco cheio, USB, tela, impressora.
version: 1.0.0
---

# Diagnostico de hardware (Linux)

## Metodo: medir antes de opinar
1. Coleta basica (todas seguras, rodam direto):
   - `uname -sr && lscpu | head -10` (SO e CPU)
   - `free -h` (RAM) e `df -h` (disco)
   - `top -bn1 | head -15` (o que esta comendo CPU agora)
   - `lsblk` e `df -h ~` (particoes e espaco)
2. GPU NVIDIA: `nvidia-smi --query-gpu=name,memory.total,temperature.gpu,utilization.gpu --format=csv,noheader`
   - temperatura acima de 85 C = suspeita de poeira/ventilacao; acima de 95 = risco real.
3. Saude de disco: `smartctl -H /dev/sda` (se smartmontools instalado; senao proponha instalar).
4. USB/perifericos: `lsusb`; impressora: `lpstat -t`; audio: `pactl info`.
5. Logs do kernel: `journalctl -p err -b --no-pager | tail -30` (erros desta inicializacao).

## Regras
- Sempre apresente: sintoma -> numero medido -> causa provavel -> acao (1 unico comando por vez).
- Nunca sugere formatar, apagar particao ou mexer em BIOS sem explicar o risco e pedir confirmacao.
- O que o Motor nao faz sozinho: abrir PC, trocar peca, mexer na BIOS. Instrua passo a passo simples.

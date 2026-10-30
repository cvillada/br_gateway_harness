---
name: software-troubleshooting
description: Use when o usuario relata problema de software: app que nao abre, update quebrado, internet, systemd, apt.
version: 1.0.0
---

# Diagnostico de software (Linux)

## Metodo: do sintoma ao log
1. O que falhou exatamente? Pergunte o erro na tela se o usuario nao souber descrever.
2. Servico: `systemctl status <nome>` e `journalctl -u <servico> -b --no-pager | tail -40`.
3. App de terminal: reproduza o comando e leia stderr. App grafico: procure log em ~/.local/share ou journalctl.
4. Dependencia: `dpkg -l | grep <pacote>`, `apt list --upgradable` (atualizacoes pendentes).
5. Internet: `ss -ltn | head`, `ip route`, `resolvectl status`; teste real: `curl -sI https://duckduckgo.com | head -3`.
6. Espaco: disco cheio quebra update e navegador; confira `df -h` antes de culpar o app.

## Reparos comuns (sempre com explicacao antes)
- Servico travado: restart (comando perigoso -> pede aprovacao do usuario).
- Pacote quebrado: `sudo apt install --reinstall <pacote>`.
- Config corrompida: faca backup do arquivo (`cp arquivo arquivo.bak`) ANTES de qualquer edicao.

## Regras
- Um diagnostico por vez; nao despeje dez possibilidades sobre o usuario leigo.
- Mudanca que afeta uso principal do sistema: explique o impacto primeiro, depois execute.

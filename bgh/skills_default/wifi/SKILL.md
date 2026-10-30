---
name: wifi
description: Use when o usuario relata internet caindo, Wi-Fi fraco ou nao conecta (Linux).
version: 1.0.0
---

# Wi-Fi e rede local (Linux)

## Medir antes de opinar (um teste por vez)
1. `nmcli device status` (o que aparece conectado: wifi, cabo, modem).
2. `ip -brief address` e `ip route` (tem IP valido? tem saida?).
3. Ate o roteador: `ping -c 3 <IP do gateway do passo 2>`.
4. Ate a internet: `ping -c 3 8.8.8.8` (se o 3 passou e o 4 nao, o corte e no roteador/provedor).
5. Forca do sinal: `nmcli -f SSID,SIGNAL,SECURITY device wifi list | head -15`.
6. Erros do servico: `journalctl -u NetworkManager -b --no-pager | tail -30`.

## Casos comuns
- IP 169.254.* (sem DHCP): reconectar a interface (`nmcli device disconnect/connect <nome>`) ou relogar no app de rede do desktop.
- Conectado ao Wi-Fi mas sem internet: confirmar no celular; se so neste PC, reiniciar NetworkManager (pede licenca).
- Sinal fraco/caindo: listar redes com forca e sugerir trocar o canal do roteador pelo painel dele (a pessoa faz; o Motor so instrui).
- Senha da rede salva que a pessoa esqueceu: `nmcli connection show "<nome>" | grep psk` mostra a senha guardada; mostrar APENAS se o dono da maquina pedir.

## Regras
- Primeiro provar ate onde chega (roteador), depois onde corta (internet); nunca culpar o provedor sem o ping 3.
- Trocar DNS ou mexer em configuracao de rede: explicar o impacto no uso principal e pedir licenca antes.
- Sem `nmcli` no sistema: propor instalar network-manager (com licenca) ou usar o app grafico de rede da pessoa.

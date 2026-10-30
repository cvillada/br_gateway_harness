---
name: audio
description: Use when o usuario relata sem som, volume baixo, microfone mudo ou bluetooth de audio (Linux).
version: 1.0.0
---

# Audio (PipeWire/PulseAudio nos sistemas atuais)

## Medir antes de opinar
1. `pactl list short sinks` (o sistema reconhece alguma saida de som?).
2. `pactl get-sink-mute @DEFAULT_SINK@` e `pactl get-sink-volume @DEFAULT_SINK@` (mutado? volume zero?).
3. `wpctl status` se existir (dispositivos e qual esta marcado como padrao); senao `pactl info`.
4. Placa vista pelo kernel: `aplay -l` (falta alsa-utils? propor instalar com licenca).
5. Erros: `journalctl -b --no-pager | grep -iE "pipewire|pulse|alsa" | tail -20`.

## Casos comuns
- Sai mutado ou mudo: `pactl set-sink-mute @DEFAULT_SINK@ 0` e `pactl set-sink-volume @DEFAULT_SINK@ 80%`.
- Som saiu pelo lugar errado (ex.: monitor HDMI virou padrao): listar sinks e escolher o certo com `pactl set-default-sink <nome do dispositivo>`.
- Fone Bluetooth caiu: ver pareamento (`bluetoothctl info` / app grafico) e reconectar; o Motor instrui, o pareamento a pessoa confirma no app.
- Microfone: `pactl list short sources` e checar mute/volume da source; em app de conversa (WhatsApp Web, Meet) conferir a entrada escolhida dentro do proprio app.
- So um aplicativo esta mudo: se os testes 1-2 estao ok, o problema e dentro do app; instruir a selecao de dispositivo nele.

## Regras
- Reiniciar servico de som (pipewire/pulseaudio) afeta o som inteiro da maquina: explicar e pedir licenca.
- Nunca baixar driver de som de forum; pacote oficial apenas (apt/instalar_pacote com licenca).
- Antes de falar em "placa de som queimada", provar que o kernel ve a placa (passo 4).

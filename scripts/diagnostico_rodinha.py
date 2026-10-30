#!/usr/bin/env python3
"""Diagnostico da rodinha do mouse.

Descobre o que o SEU terminal realmente manda para o programa quando voce
gira a rodinha. Rodar assim (no mesmo terminal onde o Motor esta estranho):

    cd ~/Projetos/br_gateway_harness
    .venv/bin/python scripts/diagnostico_rodinha.py

Depois: gire a rodinha umas 10 vezes sobre o texto e aperte CTRL+C.
O resultado aparece na tela e fica salvo em ~/.bgh/rodinha_diag.txt
(para outra pessoa ler depois sem precisar estar na sua frente).

Leitura rapida do resultado:
- "RODA SGR" ou "MOUSE" entao o terminal MANDA a roda como mouse (bom).
- "SETA PARA CIMA/BAIXO" entao o terminal disfarca a roda de setinhas
  (e por isso ela anda o historico do 'voce>').
"""
import os
import sys
import termios
import time
import tty


def classify(chunk: bytes) -> str:
    if b"\x1b[<" in chunk:
        return "RODA/MOUSE SGR (com posicao)"
    if b"\x1b[M" in chunk:
        return "MOUSE antigo (com posicao)"
    if b"\x1b[A" in chunk or b"\x1bOA" in chunk:
        return "SETA PARA CIMA"
    if b"\x1b[B" in chunk or b"\x1bOB" in chunk:
        return "SETA PARA BAIXO"
    if b"\x1b[62" in chunk:
        return "RODA SEM POSICAO (ESC[62~)"
    if b"\x1b[63" in chunk:
        return "RODA SEM POSICAO (ESC[63~)"
    if chunk.startswith(b"\x1b[") and chunk.endswith(b"~"):
        return "TECLA ESPECIAL"
    return "outro"


def main() -> int:
    print("DIAGNOSTICO DA RODINHA DO MOUSE")
    print("Gire a rodinha algumas vezes sobre o texto; depois CTRL+C para sair.")
    print("-" * 64)
    log_path = os.path.expanduser("~/.bgh/rodinha_diag.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    out = open(log_path, "w")
    out.write(
        "TERM=%s TERM_PROGRAM=%s TMUX=%s COLORTERM=%s\n" % (
            os.environ.get("TERM"), os.environ.get("TERM_PROGRAM"),
            os.environ.get("TMUX", ""), os.environ.get("COLORTERM", ""),
        )
    )
    out.flush()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    # Pede ao terminal para REPORTAR o mouse (alguns so mandam a rodinha
    # quando o programa solicita; sem isto ela pode ser engolida em silencio).
    sys.stdout.write("\x1b[?1000h\x1b[?1003h\x1b[?1006h")
    sys.stdout.flush()
    print("AGORA: gire a rodinha 10 vezes sobre estas linhas. Cada giro deve")
    print("aparecer como uma linha abaixo. Se NADA aparecer, o terminal nao esta")
    print("mandando o mouse ao programa. Quando terminar: CTRL+C.")
    print("-" * 64)
    try:
        tty.setraw(fd)
        events = 0
        while True:
            chunk = os.read(fd, 64)
            if not chunk:
                break
            kind = classify(chunk)
            events += 1
            line = "%.3f  %-34s %r" % (time.time(), kind, chunk)
            sys.stdout.write(line + "\r\n")  # modo raw: precisa do CR explicito
            sys.stdout.flush()
            out.write(line + "\n")
            out.flush()
            if b"\x03" in chunk:  # CTRL+C
                break
    finally:
        sys.stdout.write("\x1b[?1000l\x1b[?1003l\x1b[?1006l")
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        out.close()
    print("-" * 64)
    if events <= 1:
        print("ATENCAO: nenhum evento de mouse/teclado chegou durante o teste.")
    print("gravado em", log_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

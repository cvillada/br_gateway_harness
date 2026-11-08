"""Gera o icone do TEO (o gato preto) em PNG, ICO e SVG - sem dependencias.

Motivo de existir: o instalador precisa de um icone de verdade no atalho, e o
projeto nao instala Pillow por padrao. Aqui o PNG e escrito na mao (zlib +
struct), o ICO e um container com o PNG dentro (Windows Vista+ aceita) e o SVG e
o mesmo desenho em vetor (Linux/desktop moderno escala sem borrar).

Uso:
    .venv/bin/python scripts/make_icons.py

Os arquivos gerados (bgh/assets/teo.png, teo.ico, teo.svg) vao COMMITADOS: assim
instalar nao depende de rodar este script na maquina do usuario.
"""

import pathlib
import struct
import zlib

SAIDA = pathlib.Path(__file__).resolve().parent.parent / "bgh" / "assets"
LADO = 256          # tamanho final do PNG
SUPER = 4           # supersampling (desenha 4x e reduz: borda sem escada)

PRETO = (24, 24, 32, 255)      # corpo do gato (preto do TEO)
ORELHA = (58, 47, 74, 255)     # dentro da orelha
ROXO = (175, 135, 255, 255)    # olhos (mesmo roxo dos comandos na tela)
ROSA = (255, 158, 203, 255)    # nariz
BRANCO = (255, 255, 255, 255)  # brilho dos olhos


def _elipse(cx: float, cy: float, rx: float, ry: float):
    """Funcao de cobertura (x, y) -> True/False de uma elipse."""
    def dentro(x: float, y: float) -> bool:
        dx = (x - cx) / rx
        dy = (y - cy) / ry
        return dx * dx + dy * dy <= 1.0
    return dentro


def _triangulo(p1, p2, p3):
    """Cobertura de um triangulo (teste de sinal das areas)."""
    def dentro(x: float, y: float) -> bool:
        def lado(a, b) -> float:
            return (x - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (y - b[1])

        d1, d2, d3 = lado(p1, p2), lado(p2, p3), lado(p3, p1)
        neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (neg and pos)
    return dentro


def _traco(p1, p2, espessura: float):
    """Cobertura de um traco (segmento com espessura) - usado nos bigodes."""
    def dentro(x: float, y: float) -> bool:
        ax, ay = p1
        bx, by = p2
        dx, dy = bx - ax, by - ay
        comp = dx * dx + dy * dy
        if comp == 0:
            return False
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / comp))
        px, py = ax + t * dx, ay + t * dy
        return (x - px) ** 2 + (y - py) ** 2 <= espessura ** 2
    return dentro


def _desenha() -> list[list[tuple[int, int, int, int]]]:
    """Desenha o gato em SUPER*LADO e devolve a grade de pixels RGBA."""
    n = LADO * SUPER
    escala = n / 256.0
    grade = [[(0, 0, 0, 0) for _ in range(n)] for _ in range(n)]

    # Formas na escala de 256 (multiplicadas por SUPER)
    orelha_e = _triangulo((44, 96), (52, 22), (112, 62))
    orelha_d = _triangulo((212, 96), (204, 22), (144, 62))
    orelha_e_dentro = _triangulo((62, 84), (66, 42), (102, 64))
    orelha_d_dentro = _triangulo((194, 84), (190, 42), (154, 64))
    cabeca = _elipse(128, 144, 92, 84)
    focinho = _elipse(128, 172, 46, 34)
    olho_e = _elipse(98, 132, 17, 22)
    olho_d = _elipse(158, 132, 17, 22)
    brilho_e = _elipse(93, 124, 6, 8)
    brilho_d = _elipse(153, 124, 6, 8)
    nariz = _triangulo((118, 166), (138, 166), (128, 178))
    boca_e = _elipse(118, 190, 11, 5)
    boca_d = _elipse(138, 190, 11, 5)
    # bigodes: dois de cada lado, saindo do focinho e passando da borda da cabeca
    bigodes = (
        _traco((18, 172), (96, 179), 2.4),
        _traco((18, 194), (96, 188), 2.4),
        _traco((238, 172), (160, 179), 2.4),
        _traco((238, 194), (160, 188), 2.4),
    )

    for y in range(n):
        real_y = (y + 0.5) / escala
        linha = grade[y]
        for x in range(n):
            real_x = (x + 0.5) / escala
            cor = None
            if orelha_e(real_x, real_y) or orelha_d(real_x, real_y):
                cor = PRETO
            if orelha_e_dentro(real_x, real_y) or orelha_d_dentro(real_x, real_y):
                cor = ORELHA
            if cabeca(real_x, real_y):
                cor = PRETO
            if focinho(real_x, real_y):
                cor = PRETO
            if olho_e(real_x, real_y) or olho_d(real_x, real_y):
                cor = ROXO
            if brilho_e(real_x, real_y) or brilho_d(real_x, real_y):
                cor = BRANCO
            if nariz(real_x, real_y):
                cor = ROSA
            # bigodes por ultimo: aparecem por cima do pelo e passam da borda
            if any(bigode(real_x, real_y) for bigode in bigodes):
                cor = BRANCO
            if boca_e(real_x, real_y) or boca_d(real_x, real_y):
                cor = ROSA
            if cor is not None:
                linha[x] = cor
    return grade


def _reduz(grade):
    """Media dos blocos SUPER x SUPER -> imagem final LADO x LADO."""
    n = len(grade)
    final = []
    for y in range(0, n, SUPER):
        linha = []
        for x in range(0, n, SUPER):
            r = g = b = a = 0
            for dy in range(SUPER):
                for dx in range(SUPER):
                    px = grade[y + dy][x + dx]
                    r += px[0] * px[3]
                    g += px[1] * px[3]
                    b += px[2] * px[3]
                    a += px[3]
            total = SUPER * SUPER
            if a == 0:
                linha.append((0, 0, 0, 0))
            else:
                linha.append((r // a, g // a, b // a, a // total))
        final.append(linha)
    return final


def png_bytes(pixels) -> bytes:
    altura = len(pixels)
    largura = len(pixels[0])
    bruto = bytearray()
    for linha in pixels:
        bruto.append(0)  # filtro 'none' por linha
        for px in linha:
            bruto.extend(px)

    def chunk(tipo: bytes, dados: bytes) -> bytes:
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", largura, altura, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(bruto), 9))
            + chunk(b"IEND", b""))


def ico_bytes(png: bytes, lado: int = LADO) -> bytes:
    """ICO com um PNG dentro (formato aceito desde o Windows Vista)."""
    cabecalho = struct.pack("<HHH", 0, 1, 1)
    largura = 0 if lado >= 256 else lado          # 0 significa 256 no padrao ICO
    altura = 0 if lado >= 256 else lado
    entrada = struct.pack("<BBBBHHII", largura, altura, 0, 0, 1, 32,
                          len(png), 6 + 16)
    return cabecalho + entrada + png


def svg_texto() -> str:
    """Mesmo desenho em vetor (desktop Linux escala sem perder qualidade)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <title>TEO</title>
  <polygon points="44,96 52,22 112,62" fill="#181820"/>
  <polygon points="212,96 204,22 144,62" fill="#181820"/>
  <polygon points="62,84 66,42 102,64" fill="#3a2f4a"/>
  <polygon points="194,84 190,42 154,64" fill="#3a2f4a"/>
  <ellipse cx="128" cy="144" rx="92" ry="84" fill="#181820"/>
  <ellipse cx="98" cy="132" rx="17" ry="22" fill="#af87ff"/>
  <ellipse cx="158" cy="132" rx="17" ry="22" fill="#af87ff"/>
  <ellipse cx="93" cy="124" rx="6" ry="8" fill="#ffffff"/>
  <ellipse cx="153" cy="124" rx="6" ry="8" fill="#ffffff"/>
  <polygon points="118,166 138,166 128,178" fill="#ff9ecb"/>
  <ellipse cx="118" cy="190" rx="12" ry="5" fill="#ff9ecb"/>
  <ellipse cx="138" cy="190" rx="12" ry="5" fill="#ff9ecb"/>
  <g stroke="#f2f2f2" stroke-width="4" stroke-linecap="round">
    <line x1="18" y1="172" x2="96" y2="179"/>
    <line x1="18" y1="194" x2="96" y2="188"/>
    <line x1="238" y1="172" x2="160" y2="179"/>
    <line x1="238" y1="194" x2="160" y2="188"/>
  </g>
</svg>
"""


def main() -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    pixels = _reduz(_desenha())
    png = png_bytes(pixels)
    (SAIDA / "teo.png").write_bytes(png)
    (SAIDA / "teo.ico").write_bytes(ico_bytes(png))
    (SAIDA / "teo.svg").write_text(svg_texto(), encoding="utf-8")
    for nome in ("teo.png", "teo.ico", "teo.svg"):
        caminho = SAIDA / nome
        print(f"{caminho} ({caminho.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

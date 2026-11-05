"""Palco: o caminho do pedido desenhado enquanto o TEO trabalha.

Metafora: voce (START) entrega o pedido, o agente pega, a ferramenta roda, o
modelo escreve e a resposta volta para a tela. Cada etapa desenhada aqui e um
estado REAL do turno - nunca um progresso inventado: quem manda no desenho e o
evento (enter, ferramenta, primeiro texto), nao um relogio.

Aparece acima da linha de digitar SO durante o processamento e recolhe no fim.
ASCII puro: terminal de Windows e fonte raster nao lidam com desenho unicode.
"""

# Largura minima para o palco de 4 linhas; abaixo disso vira uma linha de texto
# (janela estreita nao pode perder 4 linhas para enfeite).
MIN_WIDTH = 70

# Etapas na ordem em que o pedido caminha. START = quem pediu (o usuario).
ETAPAS = (
    ("start", "START"),
    ("agente", "AGENTE"),
    ("ferramenta", "FERRAMENTA"),
    ("modelo", "MODELO"),
    ("tela", "TELA"),
)

# Fase do turno -> etapa acesa na trilha.
FASE_ETAPA = {
    "pedido": "agente",        # enter: o pedido acabou de sair da mao do usuario
    "agente": "agente",
    "ferramenta": "ferramenta",
    "modelo": "modelo",
    "resposta": "tela",
    "pronto": "tela",
    "erro": "tela",
    "parado": "tela",
}

# Texto curto e honesto de cada fase (o que a pessoa le embaixo da trilha).
FASE_TEXTO = {
    "pedido": "pedido entregue ao agente",
    "agente": "o agente esta trabalhando",
    "ferramenta": "o pessoal esta executando a tarefa",
    "modelo": "o modelo esta escrevendo a resposta",
    "resposta": "a resposta esta chegando na tela",
    "pronto": "resposta entregue",
    "erro": "voltou com erro",
    "parado": "voce mandou parar",
}


def _trilha_partes() -> tuple[list, dict]:
    """Trilha em pedacos (chave_ou_None, texto) e a coluna/largura de cada etapa.

    Separar por etapa e o que permite destacar SO a etapa atual (como item de
    menu selecionado), mantendo o resto da trilha em cor normal.
    """
    partes: list = [(None, "  ")]  # duas colunas de margem
    posicoes: dict[str, tuple[int, int]] = {}
    coluna = 2
    for i, (chave, nome) in enumerate(ETAPAS):
        if i:
            partes.append((None, " --> "))
            coluna += 5
        rotulo = "[" + nome + "]"
        posicoes[chave] = (coluna, len(rotulo))
        partes.append((chave, rotulo))
        coluna += len(rotulo)
    return partes, posicoes


PARTES_TRILHA, POSICOES = _trilha_partes()
TRILHA = "".join(texto for _chave, texto in PARTES_TRILHA)


def _corta(texto: str, limite: int) -> str:
    return texto if len(texto) <= limite else texto[:limite]


def _corta_frags(frags: list, limite: int) -> list:
    """Corta a lista de fragmentos no limite de colunas, sem quebrar o estilo."""
    saida: list = []
    total = 0
    for estilo, texto in frags:
        if total >= limite:
            break
        sobra = limite - total
        saida.append((estilo, texto[:sobra]))
        total += min(len(texto), sobra)
    return saida


def _segundos(desde, agora) -> int:
    try:
        return max(0, int(agora - float(desde or agora)))
    except (TypeError, ValueError):
        return 0


def resumo(state: dict, agora: float) -> str:
    """Uma linha com o estado real: fase, ferramenta (com tempo) e turno."""
    fase = state.get("fase") or "pedido"
    partes = [FASE_TEXTO.get(fase, fase)]
    ferramenta = state.get("tool")
    if ferramenta:
        partes.append(f"{ferramenta} {_segundos(state.get('tool_since'), agora)}s")
    partes.append(f"turno {_segundos(state.get('busy_since'), agora)}s")
    return " | ".join(partes)


def stage_rows(state: dict, width: int, agora: float, frame: int = 0) -> list:
    """Uma lista de fragmentos por LINHA do palco (formato facil de testar).

    Devolve 4 linhas em janela larga e 1 linha em janela estreita. Sempre cabe na
    largura pedida: linha que embrulha vira lixo visual.
    """
    fase = state.get("fase") or "pedido"
    limite = max(10, int(width) - 2)

    if int(width) < MIN_WIDTH:
        return [[("class:palco.dim", _corta("  > " + resumo(state, agora), limite))]]

    etapa = FASE_ETAPA.get(fase, "agente")
    coluna, largura_rotulo = POSICOES.get(etapa, (2, 6))
    # Marcador embaixo da etapa acesa; os quadros trocam sem piscar (2 em 2 ticks).
    marca = "^" * largura_rotulo if frame % 2 == 0 else "-" * largura_rotulo
    trilha = [
        ("class:palco.sel" if chave == etapa else "class:palco", texto)
        for chave, texto in PARTES_TRILHA
    ]
    return [
        _corta_frags(trilha, limite),
        [("class:palco.on", _corta(" " * coluna + marca, limite))],
        [("class:palco.dim", _corta("  " + resumo(state, agora), limite))],
        [("class:palco.dim", "")],
    ]


def stage_lines(state: dict, width: int, agora: float, frame: int = 0) -> list:
    """Fragmentos para a tela: lista de (estilo, texto), com '\\n' no fim de cada
    linha. (Uma lista de fragmentos e SEMPRE uma linha unica no prompt_toolkit;
    a quebra de linha tem que estar dentro do texto.)"""
    linhas = stage_rows(state, width, agora, frame)
    frags: list = []
    for i, linha in enumerate(linhas):
        pedacos = list(linha) or [("class:palco.dim", "")]
        if i < len(linhas) - 1:
            estilo, texto = pedacos[-1]
            pedacos[-1] = (estilo, texto + "\n")
        frags.extend(pedacos)
    return frags

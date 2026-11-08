"""Palco: o caminho do pedido desenhado enquanto o TEO trabalha.

Metafora: voce (START) entrega o pedido, o agente pega, a ferramenta roda, o
modelo escreve e a resposta volta para a tela. Cada etapa desenhada aqui e um
estado REAL do turno - nunca um progresso inventado: quem manda no desenho e o
evento (enter, ferramenta, primeiro texto), nao um relogio.

Aparece acima da linha de digitar SO durante o processamento e recolhe no fim.
ASCII puro: terminal de Windows e fonte raster nao lidam com desenho unicode.
Os rotulos vem de bgh/i18n.py (pt/en/es) e a trilha e remontada quando o idioma
muda (as colunas do marcador dependem do tamanho do rotulo).
"""

from .i18n import get_lang, t

# Largura minima para o palco de 4 linhas; abaixo disso vira uma linha de texto
# (janela estreita nao pode perder 4 linhas para enfeite).
MIN_WIDTH = 70

# Chaves das etapas na ordem em que o pedido caminha. START = quem pediu.
ETAPAS = ("start", "agente", "ferramenta", "modelo", "tela")

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

FASES = ("pedido", "agente", "ferramenta", "modelo", "resposta", "pronto",
         "erro", "parado")


def fase_texto(fase: str) -> str:
    """Texto curto e honesto da fase (o que a pessoa le embaixo da trilha)."""
    if fase in FASES:
        return t("palco.fase." + fase)
    return fase


def _etapas() -> tuple[tuple[str, str], ...]:
    """(chave, rotulo) de cada etapa no idioma da tela."""
    rotulos = {
        "start": t("palco.stage.start"),
        "agente": t("palco.stage.agent"),
        "ferramenta": t("palco.stage.tool"),
        "modelo": t("palco.stage.model"),
        "tela": t("palco.stage.screen"),
    }
    return tuple((chave, rotulos[chave]) for chave in ETAPAS)


def _trilha_partes() -> tuple[list, dict]:
    """Trilha em pedacos (chave_ou_None, texto) e a coluna/largura de cada etapa.

    Separar por etapa e o que permite destacar SO a etapa atual (como item de
    menu selecionado), mantendo o resto da trilha em cor normal.
    """
    partes: list = [(None, "  ")]  # duas colunas de margem
    posicoes: dict[str, tuple[int, int]] = {}
    coluna = 2
    for i, (chave, nome) in enumerate(_etapas()):
        if i:
            partes.append((None, " --> "))
            coluna += 5
        rotulo = "[" + nome + "]"
        posicoes[chave] = (coluna, len(rotulo))
        partes.append((chave, rotulo))
        coluna += len(rotulo)
    return partes, posicoes


_CACHE: dict = {"lang": None, "partes": [], "posicoes": {}}


def _trilha() -> tuple[list, dict]:
    """Trilha do idioma atual (remontada quando o /lingua troca o idioma)."""
    lang = get_lang()
    if _CACHE["lang"] != lang:
        partes, posicoes = _trilha_partes()
        _CACHE.update({"lang": lang, "partes": partes, "posicoes": posicoes})
    return _CACHE["partes"], _CACHE["posicoes"]


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


def visivel(ligado: bool, fase: str | None, busy: bool, hold: float, agora: float) -> bool:
    """O palco so existe quando ha PEDIDO de verdade em curso (ou a entrega).

    O 'busy' sozinho nao serve de criterio: comando de barra (/ajuda, /modelo),
    menu de arquivo e /doctor tambem deixam busy=True, e o desenho ficava na tela
    sem nenhum pedido indo para o agente - poluindo a leitura.
    """
    if not ligado or not fase:
        return False
    if busy:
        return True
    return agora < float(hold or 0)


def abrevia(valor) -> str:
    """Numero de tokens curto e padronizado: 800, 2.00k, 1.20M."""
    try:
        n = max(0, int(valor or 0))
    except (TypeError, ValueError):
        return "0"
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.2f}k"
    return f"{n / 1_000_000:.2f}M"


def linha_tokens(state: dict, limite: int) -> str:
    """Numeros de token centrados embaixo das etapas (o que o servidor informou).

    Entrada fica sob AGENTE, saida sob MODELO e o total sob TELA. A FERRAMENTA
    nao recebe numero: nao existe contagem propria de ferramenta - o resultado
    dela entra na proxima entrada. Melhor vazio do que um numero inventado.
    """
    uso = state.get("tokens") or {}
    entrada = int(uso.get("entrada") or 0)
    saida = int(uso.get("saida") or 0)
    if not entrada and not saida:
        return ""
    _partes, posicoes = _trilha()
    valores: list[tuple[str, str]] = []
    if entrada:
        valores.append(("agente", abrevia(entrada)))
    if saida:
        valores.append(("modelo", abrevia(saida)))
    if entrada and saida:
        valores.append(("tela", abrevia(entrada + saida)))
    grade = [" "] * max(int(limite), 1)
    for chave, texto in valores:
        coluna, largura = posicoes.get(chave, (0, len(texto)))
        inicio = coluna + max(0, (largura - len(texto)) // 2)
        if inicio + len(texto) > len(grade):
            inicio = max(0, len(grade) - len(texto))
        for i, caractere in enumerate(texto):
            if inicio + i < len(grade):
                grade[inicio + i] = caractere
    return "".join(grade).rstrip()


def resumo(state: dict, agora: float) -> str:
    """Uma linha com o estado real: fase, ferramenta (com tempo) e turno."""
    fase = state.get("fase") or "pedido"
    partes = [fase_texto(fase)]
    ferramenta = state.get("tool")
    if ferramenta:
        partes.append(f"{ferramenta} {_segundos(state.get('tool_since'), agora)}s")
    rodada = int(state.get("rodada") or 0)
    if rodada > 1:
        # turno que prorroga: a pessoa ve em que rodada esta (e nao um numero parado)
        partes.append(t("palco.round", n=rodada))
    partes.append(t("palco.turn", s=_segundos(state.get("busy_since"), agora)))
    return " | ".join(partes)


def stage_rows(state: dict, width: int, agora: float, frame: int = 0) -> list:
    """Uma lista de fragmentos por LINHA do palco (formato facil de testar).

    Devolve 5 linhas em janela larga (trilha, marcador, tokens, detalhes, folga) e
    1 linha em janela estreita. Sempre cabe na largura pedida: linha que embrulha
    vira lixo visual.
    """
    fase = state.get("fase") or "pedido"
    limite = max(10, int(width) - 2)

    if int(width) < MIN_WIDTH:
        partes_n: list[str] = [fase_texto(fase)]
        uso = state.get("tokens") or {}
        if uso:
            partes_n.append(t("palco.tk", entrada=abrevia(uso.get("entrada")),
                              saida=abrevia(uso.get("saida"))))
        ferramenta_n = state.get("tool")
        if ferramenta_n:
            partes_n.append(f"{ferramenta_n} {_segundos(state.get('tool_since'), agora)}s")
        return [[("class:palco.dim", _corta("  > " + " | ".join(partes_n), limite))]]

    partes_trilha, posicoes = _trilha()
    etapa = FASE_ETAPA.get(fase, "agente")
    coluna, largura_rotulo = posicoes.get(etapa, (2, 6))
    # Marcador embaixo da etapa acesa; os quadros trocam sem piscar (2 em 2 ticks).
    marca = "^" * largura_rotulo if frame % 2 == 0 else "-" * largura_rotulo
    trilha = [
        ("class:palco.sel" if chave == etapa else "class:palco", texto)
        for chave, texto in partes_trilha
    ]
    return [
        _corta_frags(trilha, limite),
        [("class:palco.on", _corta(" " * coluna + marca, limite))],
        [("class:palco.tk", linha_tokens(state, limite))],
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

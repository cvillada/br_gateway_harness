"""Tabela que o modelo escreve com "|" vira caixa ASCII na tela de texto.

A 0.2.36 passou a permitir tabela simples no pedido ("| a | b |" e a linha de
tracos) porque a tela do navegador desenha a grade. No terminal nao havia esse
desenho: o texto chegava em LineBoard, que quebra a linha na largura da janela
e corta no espaco - os "|" ficavam orfaos ("||" sozinho numa linha).

Aqui a tabela e reconhecida e desenhada como no DOS, com bordas ASCII puras
(+, - e |). O modelo continua mandando simples; quem desenha e o TEO.

Regras copiadas do app.js (mesmo comportamento nas duas telas):
- linha de tabela = comeca com "|" e tem outro "|" depois;
- separador tolera o "||||" torto que o modelo manda no lugar de |---|---|;
- uma linha so com "|" nao e tabela (volta como texto).
"""

SEP = "-"
BORDA = "+"
MIN_COLUNA = 6   # menos que isso a coluna nao se le: melhor o formato vertical


def linha_de_tabela(texto: str) -> bool:
    s = str(texto or "").strip()
    return len(s) > 1 and s[0] == "|" and "|" in s[1:]


def celulas(linha: str) -> list:
    s = str(linha or "").strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def eh_separador(cols: list) -> bool:
    """|---|---| e o separador certo; '||||' (caso real do dono) tambem conta."""
    if not cols:
        return False
    for c in cols:
        if not c:
            continue
        nucleo = c.strip(":")
        if len(nucleo) < 2 or set(nucleo) != {SEP}:
            return False
    return True


def _corta(txt: str, largura: int) -> str:
    if len(txt) <= largura:
        return txt
    if largura <= 1:
        return txt[:largura]
    return txt[:largura - 1] + "~"


def _caber(larguras: list, largura) -> list | None:
    """Encolhe as colunas para caber na janela; None = nao cabe de jeito nenhum.

    Encolhe SEMPRE a coluna mais larga primeiro (water-filling): assim a coluna
    curta continua inteira e o texto cortado e so o da coluna que nao cabia.
    """
    if not largura:
        return larguras
    n = len(larguras)
    if 1 + sum(w + 3 for w in larguras) <= largura:
        return larguras
    livre = int(largura) - 1 - 3 * n
    if livre < MIN_COLUNA * n:
        return None
    novas = list(larguras)
    while 1 + sum(w + 3 for w in novas) > largura:
        i = novas.index(max(novas))
        if novas[i] <= MIN_COLUNA:
            return None
        novas[i] -= 1
    return novas


def _borda(larguras: list) -> str:
    return BORDA + BORDA.join(SEP * (w + 2) for w in larguras) + BORDA


def _linha(cols: list, larguras: list) -> str:
    pedacos = []
    for i, w in enumerate(larguras):
        texto = cols[i] if i < len(cols) else ""
        pedacos.append(" " + _corta(texto, w).ljust(w) + " ")
    return "|" + "|".join(pedacos) + "|"


def _vertical(cabecalho, corpo: list) -> list:
    """Nao coube na largura: uma linha por campo, com o nome da coluna na frente."""
    saida: list = []
    for i, cols in enumerate(corpo):
        if i:
            saida.append("")
        for j, texto in enumerate(cols):
            if cabecalho and j < len(cabecalho) and cabecalho[j]:
                rotulo = cabecalho[j]
            else:
                rotulo = "coluna " + str(j + 1)
            saida.append(f"{rotulo}: {texto}")
    return saida


def montar(linhas: list, largura=None) -> list:
    """Linhas de tabela do modelo -> linhas da caixa ASCII (largura opcional)."""
    grade = [celulas(l) for l in linhas]
    cabecalho = None
    if len(grade) > 1 and eh_separador(grade[1]):
        cabecalho = grade[0]
        grade = grade[2:]
    colunas = max([len(c) for c in grade] + ([len(cabecalho)] if cabecalho else [1]))
    if colunas < 2:
        return list(linhas)   # uma coluna so nao e tabela: texto original
    larguras = [0] * colunas
    for cols in grade + ([cabecalho] if cabecalho else []):
        for i in range(colunas):
            texto = cols[i] if i < len(cols) else ""
            larguras[i] = max(larguras[i], len(texto))
    larguras = [max(3, w) for w in larguras]
    larguras = _caber(larguras, largura)
    if larguras is None:
        return _vertical(cabecalho, grade)
    saida = [_borda(larguras)]
    if cabecalho:
        saida.append(_linha(cabecalho, larguras))
        saida.append(_borda(larguras))
    for cols in grade:
        saida.append(_linha(cols, larguras))
    saida.append(_borda(larguras))
    return saida


class FiltroTabela:
    """Segura as linhas de tabela do streaming e devolve a caixa pronta.

    So a linha em construcao que COMECA com "|" fica retida; texto normal sai
    na hora, como sempre saiu. A tabela sai quando o bloco fecha (linha que nao
    e tabela) ou quando o chamador faz flush() - no fim do turno, no "parar" e
    no fechamento por limite. Sem esse flush a tabela do fim da resposta
    desaparecia.
    """

    def __init__(self) -> None:
        self.linha = ""
        self.rows: list = []

    def _fecha(self, largura, saida: list) -> None:
        if not self.rows:
            return
        linhas, self.rows = self.rows, []
        # Uma linha so com "|" nao e tabela: volta como veio.
        prontas = montar(linhas, largura) if len(linhas) >= 2 else list(linhas)
        for pronta in prontas:
            saida.append(pronta)
            saida.append("\n")

    def feed(self, texto: str, largura=None) -> str:
        saida: list = []
        partes = (self.linha + str(texto or "")).split("\n")
        self.linha = partes.pop()
        for p in partes:
            if linha_de_tabela(p):
                # Segura: a caixa so pode ser desenhada com a tabela inteira.
                self.rows.append(p)
                continue
            self._fecha(largura, saida)
            saida.append(p)
            saida.append("\n")
        retida = bool(self.rows) or linha_de_tabela(self.linha) \
            or self.linha.lstrip().startswith("|")
        if not retida:
            saida.append(self.linha)
            self.linha = ""
        return "".join(saida)

    def flush(self, largura=None) -> str:
        saida: list = []
        if self.linha:
            if linha_de_tabela(self.linha):
                self.rows.append(self.linha)
            else:
                self._fecha(largura, saida)
                saida.append(self.linha)
            self.linha = ""
        self._fecha(largura, saida)
        return "".join(saida)


def preparar(texto: str, largura=None) -> str:
    """Texto fechado (fora do streaming): tabelas viram caixa de uma vez."""
    filtro = FiltroTabela()
    return filtro.feed(texto, largura) + filtro.flush(largura)

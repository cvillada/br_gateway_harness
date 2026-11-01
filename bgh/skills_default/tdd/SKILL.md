---
name: tdd
description: Use quando o usuario quiser codigo novo com qualidade (script, funcao, correcao de bug) - escrever o teste antes do codigo, ciclo vermelho-verde-refatorar.
version: 1.0.0
---

# Testes antes do codigo (TDD no TEO)

## Ciclo em 4 passos (pequenos e repetidos)
1. Vermelho: escrever PRIMEIRO o teste do comportamento que falta, com nome que
   descreve o comportamento (ex.: test_total_com_desconto_nao_passa_de_100).
   Rodar o teste e VER FALHAR (se passou sem codigo, o teste nao testa nada).
2. Verde: escrever o MENOR codigo que faz o teste passar. Nada alem disso.
3. Conferir: rodar todos os testes do arquivo, nao so o novo. Todos verdes.
4. Refatorar: limpar nomes e duplicacao mantendo tudo verde. Teste continua verde
   = mudanca segura; teste vermelho = voltou atras no ultimo passo.

## Como rodar no TEO
- Teste Python sem instalar nada: stdlib `unittest`
  (classe TestX(unittest.TestCase), def test_..., `python -m unittest -v nome_do_arquivo`).
- Projeto do usuario ja usa pytest? Manter pytest (instalar com instalar_pacote se faltar).
- Arquivos de teste vivem junto do codigo do projeto (`test_*.py`); scripts soltos
  do TEO vivem no scratch.
- Bug relatado pelo usuario: comecar escrevendo o teste que reproduz o bug (vermelho),
  so depois corrigir - assim a correcao fica provada e o bug nao volta escondido.

## Regras de qualidade
- Um comportamento por teste; teste grande demais esconde qual parte quebrou.
- Testar comportamento pela borda de entrada/saida, nao detalhes internos.
- Nao testar o que nao muda (biblioteca de terceiros, rede externa): mock simples.
- Codigo sem teste nao esta pronto: ao terminar, listar quantos testes existem e
  colar a ultima rodada verde na resposta.
- Se o usuario insiste em "so fazer rapido": oferecer no minimo um teste de smoke
  (importa e roda sem erro) - e combinar com ele, nunca pular em silencio.

---
name: internet-research
description: Use when o usuario precisa de informacao atualizada: preco, tutorial, noticia, especificacao, download.
version: 1.0.0
---

# Pesquisa na internet (sem API paga)

## Fluxo
1. web_search com termos concretos (produto + modelo + "site:.gov.br" quando aplicavel).
2. Escolha ate 2 resultados confiaveis (dominio oficial, gov.br, orgao reconhecido) e confirme com web_extract.
3. So afirme o que estava na pagina; nada de "acredito que".

## Confiabilidade
- Preferir: site oficial do fabricante/governo > portal de noticia > blog/forum.
- Data importa: para preco/versao/imposto, confira a data da pagina e avise se estiver velha.
- Duas fontes discordam? Diga as duas com as fontes, nao escolha sozinho.

## Downloads
- Baixar programa: apontar SEMPRE link oficial; antes de instalar, mostrar o comando e aguardar aprovacao.
- Nunca `curl ... | sh` sem avisar o que faz.

## Citar
- Toda resposta informativa termina com: Fonte: <dominio> (<titulo da pagina>).

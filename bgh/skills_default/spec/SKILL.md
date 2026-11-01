---
name: spec
description: Use quando o usuario quer pedir, descrever ou contratar um sistema/app - transformar a ideia em especificacao pronta para um desenvolvedor executar.
version: 1.0.0
---

# Especificacao pronta para entregar (spec)

## Quando usar
- O usuario quer encomendar um programa, app ou automacao para outra pessoa (ou para si mesmo depois).
- O usuario descreve uma ideia confusa e precisa organizar antes de construir.
- Existe codigo e o usuario quer mudar algo: primeiro a spec da mudanca, depois a execucao.

## Estrutura obrigatoria de uma boa spec
Escreva na ordem abaixo, uma ideia por linha, requisitos numerados:

1. Objetivo: que problema isso resolve e para quem (1 paragrafo curto).
2. Contexto: o que ja existe (sistema, arquivos, rotinas). Se ha projeto, leia com
   read_file/search_files antes e cite o que existe de verdade - nunca inventar.
3. Requisitos funcionais: R1, R2, R3... cada um em UMA linha, no formato
   "o sistema deve <comportamento observavel>".
4. Criterios de aceite: para cada Rx, uma frase testavel: "dado <situacao>,
   quando <acao>, entao <resultado esperado>". Criterio que ninguem consegue
   testar nao e criterio.
5. Fora do escopo: o que NAO fazer nesta etapa (evita cobranca do desenvolvedor).
6. Restricoes reais: prazo, maquina onde vai rodar, idioma, custo, dados
   sensiveis. So liste restricao que o usuario confirmou.
7. Duvidas abertas: perguntas que precisam de resposta ANTES de codar. Se houver
   duvida relevante, pergunte ao usuario e finalize a spec depois da resposta.

## Regras de qualidade
- Nao escrever implementacao (linguagem, framework, banco) a menos que o usuario
  impoe como restricao: spec diz O QUE, o dev decide COMO.
- Todo requisito precisa de criterio de aceite; requisito solto vira discusao.
- Numeracao estavel: o dev e o usuario citam "R3" sem ambiguidade.
- Entregue como documento com make_document (formato md ou html), avise o caminho.
- Se o pedido do usuario virou preferencia recorrente (ex.: "sempre quero spec
  antes de codigo"), grave em memory(target=user).

## Anti-padroes (o que estraga a spec)
- Adjetivos sem teste: "bonito", "rapido", "intuitivo" -> converter em numero ou
  exemplo concreto ("responder em ate 2 segundos", "caber numa tela de celular").
- Lista de desejos sem prioridade: marque Must (agora) / Later (depois).
- Historias longas: cada requisito cabe em uma linha; se precisa de paragrafo,
  sao dois requisitos.

---
name: document-writing
description: Use when o usuario pede documento: relatorio, carta, contrato simples, guia, lista, curriculum.
version: 1.0.0
---

# Escrevendo documentos para o usuario

## Estrutura padrao (use make_document)
- Titulo claro, data no inicio, linguagem simples (sem juridiqueses/techiqueses desnecessarios).
- Carta: destinatario, corpo curto, despedida, assinatura.
- Relatorio: resumo executivo (3 linhas), desenvolvimento, conclusao com proximos passos.
- Guia passo a passo: numerado, um comando/acao por item.

## Formato
- md para guardar/imprimir depois; html quando o usuario quer abrir no navegador ou enviar por WhatsApp.
- Salvar SEMPRE em ~/Documentos, nome em minusculo com hifen (ex.: relatorio-vendas-2026.html).
- Ao terminar, informe o caminho completo e sugira abrir: `xdg-open <arquivo>`.

## Conteudo
- Numeros que aparecem no documento tem que vir de medicao real (run_command/run_python) ou de pesquisa citada.
- Nunca inventar dados, valores ou nomes. Faltou dado? Pergunta ou marca como "a confirmar".

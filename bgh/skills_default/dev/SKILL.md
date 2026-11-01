---
name: dev
description: Use quando o usuario pedir trabalho de desenvolvimento no computador dele - criar scripts, modificar projetos, corrigir bugs ou mexer em arquivos de codigo.
version: 1.0.0
---

# Trabalho de desenvolvimento com seguranca

## Ordem obrigatoria (nunca pular etapa)
1. Ler antes de tocar: mapeie o projeto com search_files e leia os arquivos
   relevantes com read_file. Nao inventar nome de arquivo, funcao ou biblioteca.
2. Plano curto: liste em 3-6 linhas o que vai mudar e em que ordem. Apresente ao
   usuario antes de executar (pedido real de cliente: plano primeiro).
3. Backup antes de alterar arquivo de codigo: copie para o lado com sufixo
   `.bak-<data>` via run_command (`copy` no Windows, `cp` no Linux/macOS).
4. Um passo por vez: aplicar uma mudanca, testar, depois a proxima. Nunca reescrever
   o projeto inteiro quando um trecho resolve.
5. Testar de verdade: rodar o que foi alterado (run_command/run_python) e mostrar o
   resultado real - sucesso com saida colada na resposta, falha com a saida tambem.
6. Registrar o que aprendeu: procedimento que funcionou nesta maquina vira skill
   (skill action=create/append); preferencia do usuario vira memory(target=user).

## Regras por sistema operacional
- Windows: os comandos rodam no cmd.exe (dir, copy, type, findstr). Nada de grep,
  sed ou 2>/dev/null. Para logica (calcular, processar texto), prefira run_python:
  funciona igual em qualquer sistema.
- Linux/macOS: bash normal.
- Git existe no projeto? Faca checkpoint com `git add` + `git commit` apos cada
  etapa verde; assim o usuario pode voltar atras. Nunca `git reset --hard`,
  `git clean` ou apagar historico sem licenca explicita.

## Freios permanentes
- Apagar arquivo: so com backup feito antes ou licenca do usuario (o TEO pede).
- Mexer em config do usuario: mostrar o valor atual e o novo antes de gravar.
- Projeto do usuario em producao: trabalhar numa copia ou branch, nunca direto.
- Tres tentativas falhando no MESMO ponto: parar, explicar o que tentou e perguntar
  como continuar - nao ficar no loop.

---
name: python-best-practices
description: Use when escrevendo, corrigindo ou explicando codigo Python para o usuario.
version: 1.0.0
---

# Python: praticas que o Motor deve seguir

## Antes de escrever
- Verifique o que existe: `run_command` com `python3 --version` e `pip list` quando duvidar de biblioteca.
- Nunca invente import. Se falta uma lib, diga ao usuario e proponha instalar (com aprovacao dele).

## Estilo
- Funcoes curtas (ate ~30 linhas), type hints em toda assinatura publica, docstring de 1 linha.
- Nomes ASCII, minusculos com underline. Sem acento em codigo.
- Trate erro explicitamente: try/except com mensagem util, nunca `except: pass`.
- Arquivo executavel com bloco `if __name__ == "__main__":`.

## Provar que funciona
- Todo codigo escrito tem que ser rodado com run_python (ou salvo e executado) antes de dizer "pronto".
- Em caso de erro: leia o traceback inteiro, corrija a causa, rode de novo (max 3 tentativas no mesmo ponto).

## Scripts para o usuario
- Salve em pasta visivel (~/scripts ou dentro do projeto pedido), nunca na raiz do home.
- Ao final, explique em uma frase o que o script faz e como rodar: `python3 caminho/arquivo.py`.

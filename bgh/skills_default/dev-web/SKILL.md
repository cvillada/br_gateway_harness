---
name: dev-web
description: Use quando o usuario pedir pagina web, site, landing page, painel ou demo HTML - criar, testar local e entregar arquivo unico pronto para abrir no navegador.
version: 1.0.0
---

# Desenvolvimento web sem depender de servidor

## Regra de ouro: comecar por arquivo unico
- Pagina, demo ou painel comecam como UM arquivo HTML com CSS e JS embutidos.
  Sem framework, sem build, sem npm - o usuario abre com dois cliques no navegador.
- So partir para projeto multi-arquivo (node, framework) quando o usuario ja tem um
  e pediu mexer nele; nesse caso seguir a skill dev (ler antes, backup, passo a passo).

## Criar
- Escrever o arquivo com write_file (extensao .html). Conteudo na ordem:
  `<meta charset="utf-8">`, viewport (funciona no celular), CSS simples, conteudo,
  JS no fim. Fontes e cores discretas; nada de biblioteca externa por CDN sem o
  usuario pedir (funciona offline assim).
- Documento entregue ao usuario final (relatorio, convite, cartaz) segue a skill
  document-writing; aqui o foco e pagina interativa.

## Testar localmente (prova, nao chute)
1. Servir: `python -m http.server 8000` na pasta do arquivo (run_command, em segundo
   plano se o comando fica rodando) e abrir `http://127.0.0.1:8000/arquivo.html`.
2. Sem navegador disponivel: validar estrutura - arquivo parseia, links internos
   apontam para arquivos que existem (search_files), JS revisado ponto a ponto.
3. Nunca dizer "pronto, e so abrir" sem ter aberto/testado de alguma forma; se nao
   deu para testar, dizer isso com honestidade e explicar como testar.

## Mudar em projeto web existente
- Mapear com search_files (onde esta o HTML, CSS, JS; tem package.json?).
- Tem package.json? Usar os scripts que o projeto ja define (`npm run ...`); checar
  node existe (`node --version`) antes de prometer build; falta node -> explicar e
  oferecer o caminho simples (arquivo unico) enquanto o usuario decide.
- Mexer em template/CSS: fazer a mudanca pequena, mostrar o resultado, nao reformular
  a identidade visual inteira sem licenca.

## Entregar
- Avise o caminho completo do arquivo (regra da casa) e como abrir (dois cliques ou
  endereco local).
- Se o usuario quer publicar: perguntar onde (ele tem servidor? prefere servico
  gratuito?); nao subir nada para lugar externo sem licenca explicita.

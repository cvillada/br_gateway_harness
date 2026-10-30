---
name: impressora
description: Use when o usuario fala de impressora: nao imprime, papel atolado, falta tinta, instalar nova.
version: 1.0.0
---

# Impressora (Linux)

## Medir antes de opinar
1. `lpstat -t` (filas e status) e `lpq` (o que esta engavetado).
2. `lsusb | grep -iE "print|hp|canon|epson|brother"` (o PC esta vendo a impressora?).
3. `systemctl status cups --no-pager | head -8` (servico de impressao vivo?).
4. `journalctl -u cups -b --no-pager | tail -30` (erros desta inicializacao).

## Casos comuns
- PC nao ve a impressora: primeiro cabos e botao liga/desliga; depois tirar e colocar o USB de novo. Sem USB: parear pela rede (instruir pelo painel da propria impressora).
- Fila engavetada: mostrar os trabalhos com `lpq`; apagar um com `lprm <numero>` (pedira licenca).
- Servico morto: `sudo systemctl restart cups` (pede licenca; avise que afeta a impressao de todos na maquina).
- Driver faltando: descobrir o MODELO EXATO escrito na impressora, procurar so no site oficial do fabricante (web_search + web_extract) e seguir o passo oficial. HP: `hp-setup` quando hplip existir; senao proponha instalar hplip (com licenca).
- Tinta/papel: o Motor nao consegue ver consumivel de longe; orientar a pessoa a olhar a impressora e imprimir a pagina de teste do fabricante.

## Regras
- Testar sempre com uma pagina simples primeiro: criar um txt curto (write_file em ~/Documentos) e mandar com `lp -d <fila> <arquivo>`.
- Nunca rodar "fix/limpeza de impressora" baixado de forum sem mostrar o conteudo inteiro e pedir licenca.
- Um diagnostico por vez: fila -> visao USB -> servico -> driver.

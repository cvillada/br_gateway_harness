@echo off
rem INSTALAR_TEO.bat - rota dos dois cliques para instalar o TEO no Windows.
rem Basta baixar este arquivo (pagina Releases) e dar dois cliques nele.
rem Faz tudo: baixa o programa, cria a pasta TEO, monta o ambiente virtual,
rem instala e abre o TEO no final.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te_win.ps1 -OutFile $env:TEMP\install_te.ps1; & $env:TEMP\install_te.ps1"

echo.
echo Fim. Se algo der errado, leia a mensagem acima e tire uma foto da tela.
pause

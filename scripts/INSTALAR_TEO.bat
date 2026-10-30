@echo off
rem INSTALAR_TEO.bat - rota dos dois cliques para instalar o TEO no Windows.
rem Basta baixar este arquivo (pagina Releases) e dar dois cliques nele.
rem Faz tudo: baixa o programa, cria a pasta TEO, monta o ambiente virtual,
rem instala e abre o TEO no final.

echo ============================================
echo   INSTALADOR DO TEO
echo   As etapas vao aparecer escritas aqui.
echo   Pode demorar alguns minutos na primeira vez.
echo ============================================
echo.
echo [1/2] Baixando o instalador...
curl.exe -L -o "%TEMP%\install_te.ps1" https://raw.githubusercontent.com/cvillada/br_gateway_harness/main/scripts/install_te_win.ps1
if errorlevel 1 (
    echo FALHA ao baixar o instalador. Veja se ha internet e tente de novo.
    goto fim
)
echo [2/2] Rodando a instalacao...
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\install_te.ps1"
if errorlevel 1 echo A instalacao terminou com erro. Leia a mensagem acima.

:fim
echo.
echo Fim. Se algo der errado, leia a mensagem acima e tire uma foto da tela.
pause

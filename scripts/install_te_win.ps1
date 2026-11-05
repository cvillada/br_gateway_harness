# Instala o TEO no Windows do inicio ao fim:
#   baixa o wheel do Release mais novo, cria a pasta TEO, cria o ambiente virtual,
#   copia o wheel para la, roda o pip install e abre o programa.
# Uso (Prompt de Comando ou PowerShell):
#   powershell -NoProfile -ExecutionPolicy Bypass -File install_te_win.ps1

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"
$repo = "cvillada/br_gateway_harness"

Write-Host "Procurando a versao mais recente do TEO..."
$rel = Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest" -TimeoutSec 30
$whl = $rel.assets | Where-Object { $_.name -like "bgh_motor-*.whl" } | Select-Object -First 1
if (-not $whl) { throw "Nao encontrei arquivo .whl no Release mais novo." }

$dir = Join-Path $env:USERPROFILE "TEO"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Set-Location $dir
Write-Host "Pasta criada: $dir"

Write-Host "Criando ambiente virtual (.venv)..."
python -m venv .venv
if ($LASTEXITCODE -ne 0) {
    throw "Python nao funcionou. Instale Python 3.11+ de https://python.org (marque 'Add python.exe to PATH') e rode de novo."
}

$wheel_local = Join-Path $dir $whl.name
Write-Host "Removendo wheels de instalacoes anteriores..."
Remove-Item -Path (Join-Path $dir "bgh_motor-*.whl") -Force -ErrorAction SilentlyContinue
Write-Host ("Baixando " + $whl.name + " ...")
Invoke-WebRequest -Uri $whl.browser_download_url -OutFile $wheel_local -TimeoutSec 120

Write-Host "Instalando no ambiente virtual..."
& "$dir\.venv\Scripts\pip.exe" install --upgrade pip | Out-Null
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/$repo/main/requirements.txt" -OutFile (Join-Path $dir "requirements.txt") -TimeoutSec 30
& "$dir\.venv\Scripts\pip.exe" install -r (Join-Path $dir "requirements.txt") | Out-Null
# '--no-deps --force-reinstall' e obrigatorio: sem isso o pip ve a MESMA versao ja
# instalada, diz 'requirement already satisfied' e deixa o codigo velho no lugar
# (reinstalar nao atualizava). As dependencias vem do passo anterior.
& "$dir\.venv\Scripts\pip.exe" install --no-deps --force-reinstall $wheel_local
if ($LASTEXITCODE -ne 0) { throw "O pip install falhou." }
$versao = (& "$dir\.venv\Scripts\pip.exe" show bgh-motor | Select-String "^Version:")
Write-Host ("Versao instalada: " + $(if ($versao) { ($versao -split "\s+")[1] } else { "desconhecida" }))

Write-Host "Criando atalho com icone na area de trabalho..."
$bat = Join-Path $dir "abrir-teo.bat"
Set-Content -Path $bat -Encoding ASCII -Value @"
@echo off
rem Abre o TEO numa janela nova do Prompt de Comando (pode fechar as outras).
cd /d "$dir"
call "$dir\.venv\Scripts\activate.bat"
bgh
"@
try {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut((Join-Path $desktop "TEO.lnk"))
    $lnk.TargetPath = $bat
    $lnk.WorkingDirectory = $dir
    $lnk.Description = "Abrir o TEO"
    $lnk.Save()
    Write-Host "Pronto: existe um icone TEO na area de trabalho. Dois cliques nele = conversar."
} catch {
    Write-Host "O icone nao saiu, mas o atalho funciona: de dois cliques em $dir\abrir-teo.bat"
}

Write-Host ""
Write-Host "TEO instalado em $dir"
Write-Host "Para conversar outra vez, abra o Prompt de Comando e digite:"
Write-Host "  cd %USERPROFILE%\TEO"
Write-Host "  .venv\Scripts\activate"
Write-Host "  bgh"
Write-Host ""
Write-Host "Abrindo o TEO agora (na primeira vez ele pede a configuracao)..."
& "$dir\.venv\Scripts\bgh.exe"

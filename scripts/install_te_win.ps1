# Instala o TEO no Windows do inicio ao fim:
#   baixa o wheel do Release mais novo, cria a pasta TEO, cria o ambiente virtual,
#   copia o wheel para la, roda o pip install e abre o programa.
# Uso (Prompt de Comando ou PowerShell):
#   powershell -NoProfile -ExecutionPolicy Bypass -File install_te_win.ps1

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"
$repo = "cvillada/br_gateway_harness"

Write-Host "Procurando a versao mais recente do TEO..."
$rel = Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest"
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
Write-Host ("Baixando " + $whl.name + " ...")
Invoke-WebRequest -Uri $whl.browser_download_url -OutFile $wheel_local

Write-Host "Instalando no ambiente virtual..."
& "$dir\.venv\Scripts\pip.exe" install --upgrade pip | Out-Null
& "$dir\.venv\Scripts\pip.exe" install $wheel_local
if ($LASTEXITCODE -ne 0) { throw "O pip install falhou." }

Write-Host ""
Write-Host "TEO instalado em $dir"
Write-Host "Para conversar outra vez, abra o Prompt de Comando e digite:"
Write-Host "  cd %USERPROFILE%\TEO"
Write-Host "  .venv\Scripts\activate"
Write-Host "  bgh"
Write-Host ""
Write-Host "Abrindo o TEO agora (na primeira vez ele pede a configuracao)..."
& "$dir\.venv\Scripts\bgh.exe"

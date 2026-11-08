# Instala o TEO no Windows do inicio ao fim:
#   baixa o wheel do Release mais novo, cria a pasta TEO, cria o ambiente virtual,
#   copia o wheel para la, roda o pip install e abre o programa.
# Uso (Prompt de Comando ou PowerShell):
#   powershell -NoProfile -ExecutionPolicy Bypass -File install_te_win.ps1

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"
$repo = "cvillada/br_gateway_harness"

# Idioma da interface do TEO (as mensagens do instalador sao em portugues).
Write-Host "Idioma / Language / Idioma: 1) Portugues  2) English  3) Espanol"
$opcaoIdioma = Read-Host "Opcao [1]"
$idioma = switch ($opcaoIdioma) { "2" { "en" } "3" { "es" } default { "pt" } }

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
$py = Join-Path $dir ".venv\Scripts\python.exe"
# Sempre pelo python -m pip: o pip.exe do venv reclama "To modify pip, please run..."
# quando tenta se atualizar.
& $py -m pip install --upgrade pip | Out-Null
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/$repo/main/requirements.txt" -OutFile (Join-Path $dir "requirements.txt") -TimeoutSec 30
& $py -m pip install -r (Join-Path $dir "requirements.txt") | Out-Null
# --ignore-installed e o que salva instalacao quebrada: se o bgh antigo ficou SEM
# RECORD (o pip nao consegue desinstalar), --force-reinstall sozinho falha com
# "uninstall-no-record-file" e o cliente fica sem o programa. Com ignore-installed
# o pip sobrescreve os arquivos e escreve metadados novos. --no-deps porque as
# dependencias vieram no passo anterior.
& $py -m pip install --no-deps --ignore-installed --force-reinstall $wheel_local
if ($LASTEXITCODE -ne 0) {
    # Plano B: apaga restos de metadados quebrados e tenta de novo.
    Write-Host "Tentando de novo com limpeza dos restos da instalacao anterior..."
    Get-ChildItem -Path (Join-Path $dir ".venv\Lib\site-packages") -Filter "bgh_motor*" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    & $py -m pip install --no-deps --ignore-installed $wheel_local
}
if ($LASTEXITCODE -ne 0) {
    throw "O pip install falhou. Para resolver na mao, rode: `"$py`" -m pip install --ignore-installed --no-deps `"$wheel_local`""
}
$versao = (& $py -c "import bgh; print(bgh.__version__)" 2>$null)
Write-Host ("Versao instalada: " + $(if ($versao) { $versao } else { "desconhecida" }))

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
    # Icone do gato: vem DENTRO do pacote instalado (nada extra para baixar).
    $iconDir = ""
    try {
        $iconDir = (& $py -c "import bgh, os; print(os.path.join(os.path.dirname(bgh.__file__), 'assets'))")
    } catch { $iconDir = "" }
    if ($iconDir -and (Test-Path (Join-Path $iconDir "teo.ico"))) {
        $lnk.IconLocation = (Join-Path $iconDir "teo.ico")
    }
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
# Primeira execucao: o assistente ja abre no idioma escolhido (sem perguntar duas vezes).
$cfg = Join-Path $env:USERPROFILE ".bgh\config.json"
if (-not (Test-Path $cfg)) {
    Write-Host "Abrindo o assistente de configuracao do TEO (idioma: $idioma)..."
    & (Join-Path $dir ".venv\Scripts\bgh.exe") setup --lang $idioma
}
Write-Host "Abrindo o TEO agora..."
& "$dir\.venv\Scripts\bgh.exe"

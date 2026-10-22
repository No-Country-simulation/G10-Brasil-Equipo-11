# CommunityLab - verificacao completa no Windows. Responsavel: Renato.
#
# Uso, na pasta raiz do projeto:
#   powershell -ExecutionPolicy Bypass -File .\verificar.ps1
#   powershell -ExecutionPolicy Bypass -File .\verificar.ps1 -Real
#
# O que faz: confere o Python, cria o ambiente virtual .venv se nao existir,
# instala as dependencias e roda verificar.py (testes, API e painel).

param([switch]$Real)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Falhar($mensagem) {
    Write-Host "[FALHOU] $mensagem" -ForegroundColor Red
    Write-Host "Veja a secao 'Problemas comuns' em docs\EXECUCAO.md"
    exit 1
}

Write-Host ""
Write-Host "CommunityLab - preparando o ambiente" -ForegroundColor Cyan

# 1. Python 3.10+ (tenta o lancador 'py' e depois 'python')
$python = $null
foreach ($candidato in @("py -3", "python")) {
    try {
        $partes = $candidato.Split(" ")
        $versao = & $partes[0] $partes[1..9] -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$versao -ge [version]"3.10") { $python = $partes; break }
    } catch { }
}
if (-not $python) { Falhar "Python 3.10 ou mais novo nao encontrado. Instale em https://www.python.org/downloads/ marcando 'Add python.exe to PATH'." }
Write-Host "[ OK ] Python $versao encontrado"

# 2. Ambiente virtual
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "       Criando o ambiente virtual .venv (so na primeira vez)..."
    & $python[0] $python[1..9] -m venv .venv
    if ($LASTEXITCODE -ne 0) { Falhar "Nao foi possivel criar o ambiente virtual .venv" }
}
Write-Host "[ OK ] Ambiente virtual .venv"

# 3. Dependencias
Write-Host "       Instalando dependencias (a primeira vez leva alguns minutos)..."
& $venvPython -m pip install --quiet --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) { Falhar "pip install -r requirements.txt falhou" }
& $venvPython -m pip install --quiet --disable-pip-version-check -e .
if ($LASTEXITCODE -ne 0) { Falhar "pip install -e . falhou" }
Write-Host "[ OK ] Dependencias instaladas"

# 4. Verificacao propriamente dita
$argumentos = @("verificar.py")
if ($Real) { $argumentos += "--real" }
& $venvPython @argumentos
exit $LASTEXITCODE

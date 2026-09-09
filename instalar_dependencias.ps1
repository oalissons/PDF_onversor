#Requires -Version 5.1

<#
.SYNOPSIS
    Instala Python 3, Pillow e PyMuPDF automaticamente no Windows.
.DESCRIPTION
    Usa winget (preferencial) ou download direto da python.org.
#>

$ErrorActionPreference = "Stop"
$pythonUrl = "https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe"
$pythonInstaller = "$env:TEMP\python-3.14.0-amd64.exe"

Write-Host "=== Instalador de Dependencias ===" -ForegroundColor Cyan

# --- 1. Verifica se Python já existe ---
function Test-Python {
    try {
        $v = & python --version 2>&1
        if ($v -match "Python 3\.\d+") { return $true }
    } catch {}
    return $false
}

if (Test-Python) {
    Write-Host "[OK] Python ja instalado: $(python --version 2>&1)" -ForegroundColor Green
} else {
    Write-Host "[...] Instalando Python..." -ForegroundColor Yellow

    # Tenta winget primeiro
    $wingetOk = $false
    try {
        $wingetCheck = Get-Command winget -ErrorAction SilentlyContinue
        if ($wingetCheck) {
            Write-Host "  Via winget..." -ForegroundColor Gray
            & winget install Python.Python.3.14 --silent --accept-package-agreements 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { $wingetOk = $true }
        }
    } catch {}

    if (-not $wingetOk) {
        Write-Host "  Download via python.org..." -ForegroundColor Gray
        try {
            Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing
            Write-Host "  Instalando..." -ForegroundColor Gray
            Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait
        } catch {
            Write-Host "  Falha no download. Tentando via nuget..." -ForegroundColor Yellow
            & python -m pip install --upgrade pip 2>&1 | Out-Null  # tenta ver se pip existe
        }
    }

    # Atualiza PATH para sessao atual
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:Path"

    if (Test-Python) {
        Write-Host "[OK] Python instalado: $(python --version 2>&1)" -ForegroundColor Green
    } else {
        Write-Host "[ERRO] Nao foi possivel instalar Python." -ForegroundColor Red
        Write-Host "Instale manualmente de: https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
}

# --- 2. Instala pacotes pip ---
Write-Host "[...] Instalando pacotes pip..." -ForegroundColor Yellow
try {
    Write-Host "  Rodando: pip install --upgrade pip..." -ForegroundColor Gray
    & python -m pip install --upgrade pip 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

    Write-Host "  Rodando: pip install Pillow PyMuPDF (timeout 5min)..." -ForegroundColor Gray
    $pipJob = Start-Job -ScriptBlock { & python -m pip install Pillow PyMuPDF 2>&1 }
    if (Wait-Job $pipJob -Timeout 300) {
        Receive-Job $pipJob | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Stop-Job $pipJob
        Write-Host "[ERRO] pip install excedeu o tempo limite (5min)." -ForegroundColor Red
        Remove-Job $pipJob -Force
        exit 1
    }
    Remove-Job $pipJob -Force
} catch {
    Write-Host "[ERRO] Falha ao instalar pacotes pip." -ForegroundColor Red
    exit 1
}

# --- 3. Verifica ---
try {
    & python -c "from PIL import Image; import fitz; print('OK')" 2>&1 | Out-Null
    Write-Host "[OK] Tudo instalado corretamente!" -ForegroundColor Green
    Write-Host "     Pillow + PyMuPDF prontos para uso." -ForegroundColor Green
} catch {
    Write-Host "[ERRO] Verificacao falhou." -ForegroundColor Red
    exit 1
}

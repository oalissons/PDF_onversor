#Requires -Version 5.1

<#
.SYNOPSIS
    Converte todos os arquivos JPEG de uma pasta da rede para PDF,
    recriando a estrutura de pastas com o sufixo " PDF".
.DESCRIPTION
    Para cada pasta dentro do diretório raiz, cria uma pasta espelho com
    " PDF" no nome e converte todos os JPEGs (JPG/JPEG) encontrados para PDF.
    Arquivos no nível raiz também são convertidos para uma pasta "0 - Raiz PDF".
.NOTES
    Requer Python 3.x com Pillow + PyMuPDF.
    Verificação: python -c "from PIL import Image; import fitz; print('OK')"
#>

param([string]$rootDir = "$env:USERPROFILE\Desktop\ORDENS")
$pythonCmd = "python"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Conversor JPEG -> PDF ===" -ForegroundColor Cyan
Write-Host "Raiz: $rootDir" -ForegroundColor Yellow

if (-not (Test-Path $rootDir)) {
    Write-Host "ERRO: $rootDir nao encontrado. Verifique o caminho ou use: " -ForegroundColor Red
    Write-Host "  powershell -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`" -rootDir `"C:\Seu\Caminho`"" -ForegroundColor Yellow
    Read-Host "`nPressione Enter para sair..."
    exit 1
}

# --- Auto-instala dependencias se faltar ---
function Test-Python {
    try { $v = & $pythonCmd --version 2>&1; return ($v -match "Python 3\.\d+") } catch { return $false }
}
function Test-Deps {
    try { $c = & $pythonCmd -c "from PIL import Image; import fitz; print('OK')" 2>&1; return ($c -eq "OK") } catch { return $false }
}

if (-not (Test-Python) -or -not (Test-Deps)) {
    Write-Host "[...] Instalando dependencias..." -ForegroundColor Yellow
    $installScript = Join-Path $scriptDir "instalar_dependencias.ps1"
    if (Test-Path $installScript) {
        & $installScript
    } else {
        Write-Host "[AVISO] Script de instalacao nao encontrado." -ForegroundColor Yellow
        Write-Host "Baixando e instalando Python + pacotes..." -ForegroundColor Yellow

        # Tenta winget para Python
        try {
            $wc = Get-Command winget -ErrorAction SilentlyContinue
            if ($wc) { & winget install Python.Python.3.14 --silent --accept-package-agreements 2>&1 | Out-Null }
        } catch {}
        if (-not (Test-Python)) {
            Write-Host "Python nao encontrado. Execute primeiro:" -ForegroundColor Red
            Write-Host "  powershell -ExecutionPolicy Bypass -File `"$scriptDir\instalar_dependencias.ps1`"" -ForegroundColor Yellow
            Read-Host "`nPressione Enter para sair..."
            exit 1
        }

        # Instala pacotes com timeout de 300s
        Write-Host "  Rodando: pip install Pillow PyMuPDF (timeout 5min)..." -ForegroundColor Gray
        $pipJob = Start-Job -ScriptBlock { & python -m pip install Pillow PyMuPDF 2>&1 }
        if (Wait-Job $pipJob -Timeout 300) {
            Receive-Job $pipJob | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        } else {
            Stop-Job $pipJob
            Write-Host "[ERRO] pip install excedeu o tempo limite (5min)." -ForegroundColor Red
            Remove-Job $pipJob -Force
            Read-Host "`nPressione Enter para sair..."
            exit 1
        }
        Remove-Job $pipJob -Force
    }

    # Atualiza PATH
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:Path"

    if (-not (Test-Deps)) {
        Write-Host "[ERRO] Nao foi possivel instalar as dependencias." -ForegroundColor Red
        Read-Host "`nPressione Enter para sair..."
        exit 1
    }
    Write-Host "[OK] Dependencias prontas!" -ForegroundColor Green
}

# --- Coleta diretórios com JPEGs ---
$dirs = [System.Collections.Generic.List[string]]::new()
$dirs.Add($rootDir)  # raiz também
Get-ChildItem $rootDir -Directory | Where-Object { $_.Name -notlike '* PDF' } | ForEach-Object { $dirs.Add($_.FullName) }

$totalDirs = $dirs.Count
$processedDirs = 0
$totalFiles = 0
$convertedFiles = 0
$skippedFiles = 0
$failedFiles = 0

Write-Host "Processando $totalDirs pasta(s)..." -ForegroundColor Cyan

foreach ($srcDir in $dirs) {
    $processedDirs++

    # Define nome da pasta destino
    if ($srcDir -eq $rootDir) {
        $destDir = Join-Path $rootDir "0 - Raiz PDF"
    } else {
        $dirName = Split-Path $srcDir -Leaf
        $parentDir = Split-Path $srcDir -Parent
        $destDir = Join-Path $parentDir "${dirName} PDF"
    }

    # Pula se já existe (opção: descomentar para pular pastas já existentes)
    # if (Test-Path $destDir) { Write-Host "  [PULANDO] $destDir já existe"; continue }

    # Busca JPEGs
    $jpegs = Get-ChildItem $srcDir -File | Where-Object {
        $_.Extension -match '^\.jpe?g$' -and $_.Name -notlike 'Thumbs.db'
    }

    if ($jpegs.Count -eq 0) {
        Write-Host "[$processedDirs/$totalDirs] NENHUM JPEG em: $srcDir"
        continue
    }

    Write-Host "[$processedDirs/$totalDirs] $srcDir -> $destDir ($($jpegs.Count) arquivos)"

    # Cria pasta destino
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null

    foreach ($jpg in $jpegs) {
        $totalFiles++
        $pdfPath = Join-Path $destDir "$($jpg.BaseName).pdf"

        # Pula se PDF já existe
        if (Test-Path $pdfPath) {
            $skippedFiles++
            continue
        }

        try {
            & $pythonCmd -c @"
from PIL import Image
import fitz, sys, io
A4L = (841.89, 595.28)
f = r'$($jpg.FullName)'
out = r'$pdfPath'
try:
    img = Image.open(f).convert('RGB')
    w, h = img.size
    bg = tuple((img.getpixel((0,0))[i] + img.getpixel((w-1,0))[i] +
                img.getpixel((0,h-1))[i] + img.getpixel((w-1,h-1))[i]) // 4 for i in range(3))
    def is_bg(px): return max(abs(px[i]-bg[i]) for i in range(3)) <= 40
    step = 3
    left = next((x for x in range(w) if sum(1 for y in range(0,h,step) if not is_bg(img.getpixel((x,y)))) > h//step*0.01), 0)
    right = next((x for x in range(w-1,-1,-1) if sum(1 for y in range(0,h,step) if not is_bg(img.getpixel((x,y)))) > h//step*0.01), w-1)
    top = next((y for y in range(h) if sum(1 for x in range(0,w,step) if not is_bg(img.getpixel((x,y)))) > w//step*0.01), 0)
    bottom = next((y for y in range(h-1,-1,-1) if sum(1 for x in range(0,w,step) if not is_bg(img.getpixel((x,y)))) > w//step*0.01), h-1)
    img_crop = img.crop((left, top, right+1, bottom+1))
    buf = io.BytesIO()
    img_crop.save(buf, 'PNG')
    buf.seek(0)
    doc = fitz.open()
    page = doc.new_page(width=A4L[0], height=A4L[1])
    page.draw_rect(page.rect, color=(1,1,1), fill=(1,1,1))
    m = 8.5
    img_rect = fitz.Rect(m, m, A4L[0]-m, A4L[1]-m)
    page.insert_image(img_rect, stream=buf.read(), keep_proportion=True)
    doc.save(out, garbage=4, deflate=True)
    doc.close(); buf.close()
    print('OK')
except Exception as e:
    print(f'ERRO: {e}'); sys.exit(1)
"@ 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                $convertedFiles++
                Write-Host "    OK: $($jpg.Name)" -ForegroundColor Green
            } else {
                $failedFiles++
                Write-Host "    FALHA: $($jpg.Name)" -ForegroundColor Red
            }
        } catch {
            $failedFiles++
            Write-Host "    EXCEÇÃO: $($jpg.Name) - $_" -ForegroundColor Red
        }
    }
}

Write-Host "`n=== RESUMO ===" -ForegroundColor Cyan
Write-Host "Pastas processadas: $processedDirs" -ForegroundColor White
Write-Host "Arquivos encontrados: $totalFiles" -ForegroundColor White
Write-Host "Convertidos: $convertedFiles" -ForegroundColor Green
Write-Host "Falhas: $failedFiles" -ForegroundColor Red
Write-Host "Pulados (já existem): $skippedFiles" -ForegroundColor Yellow
Write-Host "Concluído!" -ForegroundColor Cyan

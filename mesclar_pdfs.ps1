param([string]$diretorio = "$env:USERPROFILE\Desktop\ORDENS")

if (-not (Test-Path $diretorio)) {
    Write-Host "ERRO: Diretorio nao encontrado: $diretorio" -ForegroundColor Red
    do { $r = Read-Host "`nDigite S para sair ou N para continuar" } while ($r -notin @('s','S','n','N'))
    exit 1
}

$pastas = @()
# Inclui a propria raiz se tiver PDFs
if ((Get-ChildItem $diretorio -Filter "*.pdf" -File).Count -gt 0) {
    $pastas += $diretorio
}
# Adiciona subpastas que contem PDFs
Get-ChildItem $diretorio -Directory | Where-Object {
    (Get-ChildItem $_.FullName -Filter "*.pdf" -File).Count -gt 0
} | ForEach-Object { $pastas += $_.FullName }

if ($pastas.Count -eq 0) {
    Write-Host "Nenhum PDF encontrado em: $diretorio" -ForegroundColor Yellow
    Write-Host "Uso: powershell -File mesclar_pdfs.ps1 -diretorio `"\\caminho\com\pdfs`"" -ForegroundColor Gray
    do { $r = Read-Host "`nDigite S para sair ou N para continuar" } while ($r -notin @('s','S','n','N'))
    exit 0
}

Write-Host "Pastas a processar: $($pastas.Count)" -ForegroundColor Cyan
$pastas | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }

$totalGeral = 0
$backupDir = Join-Path $diretorio "_backup"

function Restaurar-Backup {
    param($backup, $destino)
    if (Test-Path $backup) {
        Copy-Item -LiteralPath "$backup\*" -Destination $destino -Recurse -Force
    }
}

foreach ($pasta in $pastas) {
    Write-Host "`n>>> Processando: $pasta" -ForegroundColor Cyan
    $pdfs = Get-ChildItem $pasta -Filter "*.pdf" -File | Where-Object { $_.Name -notlike '*_merged_temp*' }
    $grupos = @{}

    foreach ($pdf in $pdfs) {
        $stem = $pdf.BaseName
        if ($stem -match '^(.+?)\s*-\s*(\d+)$') {
            $base = $matches[1].Trim()
        } else {
            $base = $stem.Trim()
        }
        if (-not $grupos.ContainsKey($base)) { $grupos[$base] = @() }
        $grupos[$base] += $pdf
    }

    $totalPasta = 0

    foreach ($base in $grupos.Keys) {
        $arquivos = $grupos[$base]
        $sorted = $arquivos | Sort-Object {
            $s = $_.BaseName
            if ($s -match '\s*-\s*(\d+)$') { [int]$matches[1] } else { 0 }
        }

        if ($sorted.Count -lt 2) { continue }

        $totalPasta++
        $output = Join-Path $pasta "$base.pdf"
        $temp = Join-Path $pasta "$base`_merged_temp.pdf"

        Write-Host "  [$totalPasta] $base ($($sorted.Count) arquivos)" -ForegroundColor Cyan

        # --- 1. MERGE ---
        $fileList = ($sorted.FullName) -join '|'
        if (Test-Path $temp) { Remove-Item -LiteralPath $temp -Force }

        $result = & python -c @"
import fitz, sys, os
files = r'$fileList'.split('|')
output = r'$temp'
doc = fitz.open()
for f in files:
    if not os.path.isfile(f):
        print(f'ERRO: arquivo nao encontrado: {f}')
        sys.exit(1)
    src = fitz.open(f)
    doc.insert_pdf(src)
    src.close()
doc.save(output, garbage=4, deflate=True)
doc.close()
print('OK')
"@ 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "    ERRO no merge: $result" -ForegroundColor Red
            Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
            continue
        }

        if (-not (Test-Path $temp)) {
            Write-Host "    ERRO: arquivo temporario nao foi criado" -ForegroundColor Red
            continue
        }

        # --- 2. VERIFICA TEMP ---
        $verify = & python -c @"
import fitz, sys
try:
    doc = fitz.open(r'$temp')
    pag = doc.page_count
    doc.close()
    print(f'OK:{pag}')
except Exception as e:
    print(f'ERRO:{e}')
    sys.exit(1)
"@ 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "    ERRO: PDF temporario corrompido - $verify" -ForegroundColor Red
            Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
            continue
        }

        # --- 3. BACKUP DOS ORIGINAIS ---
        try {
            if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }
            foreach ($f in $sorted) {
                $bakPath = Join-Path $backupDir "$($f.Name).bak"
                Copy-Item -LiteralPath $f.FullName -Destination $bakPath -Force
            }
        } catch {
            Write-Host "    ERRO ao criar backup: $_" -ForegroundColor Red
            Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
            continue
        }

        # --- 4. REMOVE ORIGINAIS ---
        try {
            foreach ($f in $sorted) {
                if (Test-Path $f.FullName) { Remove-Item -LiteralPath $f.FullName -Force }
            }
        } catch {
            Write-Host "    ERRO ao remover originais: $_" -ForegroundColor Red
            Restaurar-Backup -backup $backupDir -destino $pasta
            Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
            continue
        }

        # --- 5. RENOMEIA TEMP ---
        try {
            if (Test-Path $output) { Remove-Item -LiteralPath $output -Force }
            Rename-Item -LiteralPath $temp -NewName "$base.pdf"
        } catch {
            Write-Host "    ERRO ao renomear: $_" -ForegroundColor Red
            Restaurar-Backup -backup $backupDir -destino $pasta
            Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
            continue
        }

        # --- 6. LIMPA BACKUP DESTE GRUPO ---
        foreach ($f in $sorted) {
            $bakPath = Join-Path $backupDir "$($f.Name).bak"
            Remove-Item -LiteralPath $bakPath -Force -ErrorAction SilentlyContinue
        }

        $paginas = ($verify -split ':')[1]
        Write-Host "    OK: $base.pdf ($paginas paginas)" -ForegroundColor Green
    }

    if ($totalPasta -eq 0) {
        Write-Host "  Nenhum grupo para mesclar nesta pasta" -ForegroundColor Yellow
    }
    $totalGeral += $totalPasta
}

# Remove backup dir se vazio
if ((Test-Path $backupDir) -and ((Get-ChildItem $backupDir).Count -eq 0)) {
    Remove-Item -LiteralPath $backupDir -Force -ErrorAction SilentlyContinue
}

Write-Host "`n=== RESUMO ===" -ForegroundColor Cyan
if ($totalGeral -eq 0) {
    Write-Host "Nenhum grupo mesclado" -ForegroundColor Yellow
} else {
    Write-Host "Total de grupos mesclados: $totalGeral" -ForegroundColor Green
}
Write-Host "Concluido!" -ForegroundColor Cyan

do { $r = Read-Host "`nDigite S para sair ou N para continuar" } while ($r -notin @('s','S','n','N'))

param([string]$diretorio = "$env:USERPROFILE\Desktop\ORDENS")

if (-not (Test-Path $diretorio)) {
    Write-Host "ERRO: Diretorio nao encontrado: $diretorio" -ForegroundColor Red
    do { $r = Read-Host "`nDigite S para sair ou N para continuar" } while ($r -notin @('s','S','n','N'))
    exit 1
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "converter_pdf_para_html.py"

if (-not (Test-Path $pythonScript)) {
    Write-Host "ERRO: Script Python nao encontrado: $pythonScript" -ForegroundColor Red
    do { $r = Read-Host "`nDigite S para sair ou N para continuar" } while ($r -notin @('s','S','n','N'))
    exit 1
}

Write-Host "=== Conversor PDF -> HTML ===" -ForegroundColor Cyan
Write-Host "Diretorio: $diretorio" -ForegroundColor Yellow

try {
    & python "$pythonScript" "$diretorio" 2>&1 | ForEach-Object { Write-Host "$_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n[ERRO] Conversao falhou (codigo $LASTEXITCODE)." -ForegroundColor Red
    }
} catch {
    Write-Host "`n[ERRO] Falha ao executar Python: $_" -ForegroundColor Red
}

do { $r = Read-Host "`nDigite S para sair ou N para continuar" } while ($r -notin @('s','S','n','N'))

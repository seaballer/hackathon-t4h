# Script para executar o colaborador-digital-equipamentos
# Uso: .\executar.ps1

Write-Host "Colaborador Digital - Gestao de Equipamentos" -ForegroundColor Cyan
Write-Host "Hackathon UNIFEI 2026" -ForegroundColor Cyan
Write-Host ""

# Verificar se o venv do hackathon-t4h existe
$venv_path = "..\hackathon-t4h\venv\Scripts\python.exe"
if (-not (Test-Path $venv_path)) {
    Write-Host "ERRO: venv do hackathon-t4h nao encontrado!" -ForegroundColor Red
    Write-Host "Crie o venv em hackathon-t4h primeiro:" -ForegroundColor Yellow
    Write-Host "cd ..\hackathon-t4h" -ForegroundColor White
    Write-Host "python -m venv venv" -ForegroundColor White
    exit 1
}

Write-Host "Usando Python do venv: $venv_path" -ForegroundColor Yellow
Write-Host ""

# Executar o programa
Write-Host "Executando colaborador-digital-equipamentos..." -ForegroundColor Green
Write-Host ""

& $venv_path main.py @args

Write-Host ""
Write-Host "Execucao concluida" -ForegroundColor Green

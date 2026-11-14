# Script para executar o servidor MCP e o main.py em janelas separadas
# Uso: .\executar_completo.ps1

Write-Host "Colaborador Digital - Gestao de Equipamentos" -ForegroundColor Cyan
Write-Host "Hackathon UNIFEI 2026" -ForegroundColor Cyan
Write-Host ""

# Verificar se o venv existe
$venv_path = ".\venv\Scripts\python.exe"
if (-not (Test-Path $venv_path)) {
    Write-Host "ERRO: venv nao encontrado!" -ForegroundColor Red
    Write-Host "Crie o venv primeiro:" -ForegroundColor Yellow
    Write-Host "python -m venv venv" -ForegroundColor White
    Write-Host "pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

Write-Host "Usando Python do venv: $venv_path" -ForegroundColor Yellow
Write-Host ""

# Iniciar o servidor MCP em uma nova janela
Write-Host "Iniciando servidor MCP em nova janela..." -ForegroundColor Green
Start-Process -FilePath $venv_path -ArgumentList "-m src.mcp_server" -WindowStyle Normal

# Aguardar um pouco para o servidor iniciar
Write-Host "Aguardando servidor MCP iniciar..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Iniciar o main.py
Write-Host "Iniciando main.py..." -ForegroundColor Green
Write-Host ""

& $venv_path main.py @args

Write-Host ""
Write-Host "Execucao concluida" -ForegroundColor Green

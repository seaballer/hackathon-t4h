# Script para iniciar o servidor MCP
# Uso: .\iniciar_mcp.ps1

Write-Host "Iniciando Servidor MCP..." -ForegroundColor Cyan
Write-Host ""

# Verificar se o venv existe
$venv_path = ".\venv\Scripts\python.exe"
if (-not (Test-Path $venv_path)) {
    Write-Host "ERRO: venv nao encontrado!" -ForegroundColor Red
    Write-Host "Crie o venv primeiro:" -ForegroundColor Yellow
    Write-Host "python -m venv venv" -ForegroundColor White
    exit 1
}

Write-Host "Usando Python do venv: $venv_path" -ForegroundColor Yellow
Write-Host ""

# Executar o servidor MCP
Write-Host "Servidor MCP rodando em http://localhost:8765/mcp" -ForegroundColor Green
Write-Host "Pressione Ctrl+C para parar" -ForegroundColor Yellow
Write-Host ""

& $venv_path -m src.mcp_server

Write-Host ""
Write-Host "Servidor MCP parado" -ForegroundColor Yellow

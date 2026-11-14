# Script para iniciar MCP Server e Aplicação
# Uso: .\iniciar.ps1

Write-Host "=== Iniciando Sistema de Agentes ===" -ForegroundColor Green
Write-Host ""

# Ativar venv
Write-Host "1. Ativando ambiente virtual..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Iniciar MCP Server em background
Write-Host "2. Iniciando MCP Server..." -ForegroundColor Cyan
$mcp_process = Start-Process -FilePath "python" -ArgumentList "-m src.mcp_server" -PassThru -NoNewWindow
Write-Host "   MCP Server iniciado (PID: $($mcp_process.Id))" -ForegroundColor Green

# Aguardar um pouco para o servidor iniciar
Write-Host "3. Aguardando MCP Server iniciar..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Verificar se o arquivo .mcp_port foi criado
$max_attempts = 10
$attempt = 0
while (-not (Test-Path ".mcp_port") -and $attempt -lt $max_attempts) {
    Write-Host "   Tentativa $($attempt + 1)/$max_attempts..." -ForegroundColor Yellow
    Start-Sleep -Seconds 1
    $attempt++
}

if (Test-Path ".mcp_port") {
    $porta = Get-Content ".mcp_port"
    Write-Host "   MCP Server rodando na porta: $porta" -ForegroundColor Green
} else {
    Write-Host "   AVISO: Arquivo .mcp_port não encontrado" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "4. Iniciando Aplicação..." -ForegroundColor Cyan
Write-Host ""

# Rodar aplicação
python main.py

# Limpar
Write-Host ""
Write-Host "5. Encerrando MCP Server..." -ForegroundColor Cyan
Stop-Process -Id $mcp_process.Id -Force -ErrorAction SilentlyContinue
Write-Host "   MCP Server encerrado" -ForegroundColor Green

Write-Host ""
Write-Host "=== Sistema Encerrado ===" -ForegroundColor Green

# Script para testar a conexão com o MCP Server
# Use: .\testar_mcp.ps1

param(
    [string]$HostName = "localhost",
    [int]$Port = 8766
)

$BaseUrl = "http://$HostName`:$Port"
$McpUrl = "$BaseUrl/mcp"

Write-Host "=== Testando Conexão com MCP Server ===" -ForegroundColor Cyan
Write-Host "URL Base: $BaseUrl" -ForegroundColor Gray
Write-Host ""

# Teste 1: Health Check
Write-Host "1. Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Servidor respondendo!" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   Resposta: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Servidor não respondendo!" -ForegroundColor Red
    Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Teste 2: Próximo Evento
Write-Host "2. Próximo Evento..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$McpUrl/proximo_evento?esperar_segundos=1" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Endpoint respondendo!" -ForegroundColor Green
    Write-Host "   Resposta: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Erro ao chamar endpoint" -ForegroundColor Yellow
    Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""

# Teste 3: Consultar Inventário
Write-Host "3. Consultar Inventário..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$McpUrl/consultar_inventario?equipamento_id=eq_001" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Endpoint respondendo!" -ForegroundColor Green
    Write-Host "   Resposta: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Erro ao chamar endpoint" -ForegroundColor Yellow
    Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Teste Concluído ===" -ForegroundColor Cyan

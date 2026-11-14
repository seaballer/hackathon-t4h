# Script para testar localhost enquanto o servidor está rodando
# Execute em outro terminal enquanto .\iniciar.ps1 está rodando

Write-Host "=== Testando Localhost ===" -ForegroundColor Cyan
Write-Host ""

# Aguardar um pouco para o servidor iniciar
Write-Host "Aguardando servidor iniciar..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Teste 1: Health Check
Write-Host "1. Testando http://localhost:8766/health" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8766/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Sucesso!" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   Resposta: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Falhou!" -ForegroundColor Red
    Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Teste 2: Próximo Evento
Write-Host "2. Testando http://localhost:8766/mcp/proximo_evento" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8766/mcp/proximo_evento?esperar_segundos=1" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Sucesso!" -ForegroundColor Green
    Write-Host "   Resposta: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Falhou!" -ForegroundColor Red
    Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Teste 3: Consultar Inventário
Write-Host "3. Testando http://localhost:8766/mcp/consultar_inventario" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8766/mcp/consultar_inventario?equipamento_id=PAT-001" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Sucesso!" -ForegroundColor Green
    Write-Host "   Resposta: $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Falhou!" -ForegroundColor Red
    Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Teste Concluído ===" -ForegroundColor Cyan

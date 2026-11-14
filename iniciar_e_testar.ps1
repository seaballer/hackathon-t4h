# Script que inicia o servidor MCP local, testa a conexao e o MANTEM rodando
# Uso: .\iniciar_e_testar.ps1        (Ctrl+C para encerrar o servidor)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Iniciando Sistema com Teste ===" -ForegroundColor Cyan
Write-Host ""

$python = ".\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "ERRO: venv nao encontrado. Rode: python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

# Remove porta antiga para nao ler um valor de uma execucao anterior
Remove-Item ".mcp_port" -ErrorAction SilentlyContinue

Write-Host "1. Iniciando MCP Server em background..." -ForegroundColor Yellow
$mcp_process = Start-Process -FilePath $python -ArgumentList "-m", "src.mcp_server" -PassThru -NoNewWindow
Write-Host "   MCP Server iniciado (PID: $($mcp_process.Id))" -ForegroundColor Green

try {
    # Aguarda o servidor gravar a porta e responder no /health (ate 20 s)
    Write-Host "2. Aguardando servidor iniciar..." -ForegroundColor Yellow
    $port = $null
    $limite = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $limite) {
        if ($mcp_process.HasExited) { throw "Servidor MCP encerrou ao iniciar." }
        if (Test-Path ".mcp_port") {
            $port = (Get-Content ".mcp_port" -Raw).Trim()
            try {
                Invoke-WebRequest -Uri "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
                break
            } catch { }
        }
        Start-Sleep -Milliseconds 300
    }
    if (-not $port) { throw "Servidor MCP nao respondeu em 20 s." }
    $base = "http://127.0.0.1:$port"
    Write-Host "   Servidor pronto na porta $port" -ForegroundColor Green

    Write-Host ""
    Write-Host "=== Testando Conexao ===" -ForegroundColor Cyan

    $testes = @(
        @{ Nome = "GET  /health";                    Uri = "$base/health" },
        @{ Nome = "GET  /mcp/proximo_evento";        Uri = "$base/mcp/proximo_evento?esperar_segundos=1" },
        @{ Nome = "POST /mcp/consultar_inventario";  Uri = "$base/mcp/consultar_inventario"; Metodo = "POST";
           Corpo = (@{ equipamento_id = "PAT-001" } | ConvertTo-Json) }
    )
    foreach ($t in $testes) {
        Write-Host ""
        Write-Host "- $($t.Nome)" -ForegroundColor Yellow
        try {
            $params = @{ Uri = $t.Uri; UseBasicParsing = $true; TimeoutSec = 5 }
            if ($t.Metodo) { $params.Method = $t.Metodo; $params.Body = $t.Corpo; $params.ContentType = "application/json" }
            $r = Invoke-WebRequest @params
            Write-Host "  [OK] $($r.StatusCode): $($r.Content)" -ForegroundColor Green
        } catch {
            Write-Host "  [FALHOU] $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    Write-Host ""
    Write-Host "=== Servidor MCP rodando ===" -ForegroundColor Cyan
    Write-Host "  Raiz:   $base/" -ForegroundColor White
    Write-Host "  Health: $base/health" -ForegroundColor White
    Write-Host "  Docs:   $base/docs" -ForegroundColor White
    Write-Host "  Agentes (outro terminal): python main.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Pressione Ctrl+C para encerrar o servidor." -ForegroundColor Yellow
    Wait-Process -Id $mcp_process.Id
}
finally {
    # Encerra o servidor e o processo filho (o python.exe do venv e um lancador)
    if (-not $mcp_process.HasExited) {
        Write-Host ""
        Write-Host "Encerrando MCP Server..." -ForegroundColor Yellow
        taskkill /PID $mcp_process.Id /T /F | Out-Null
    }
    Remove-Item ".mcp_port" -ErrorAction SilentlyContinue
    Write-Host "MCP Server encerrado" -ForegroundColor Green
}
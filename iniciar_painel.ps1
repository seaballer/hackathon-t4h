# Inicia o servidor OFICIAL do hackathon (mundo.py) com o painel ao vivo.
# Uso: .\iniciar_painel.ps1            (Ctrl+C para parar)
#      .\iniciar_painel.ps1 -SemErros  (desliga as falhas simuladas, bom para desenvolver)

param([switch]$SemErros)

$servidor = Join-Path $PSScriptRoot "..\Outros\Servidor MCP (Compartilhado)"
$python = Join-Path $servidor ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Criando ambiente do servidor (Python 3.11+)..." -ForegroundColor Yellow
    Push-Location $servidor
    py -3.14 -m venv .venv
    & $python -m pip install -q -r requirements.txt
    Pop-Location
}

$argumentos = @("mundo.py", "--tema", "equipamentos")
if ($SemErros) { $argumentos += @("--erros", "0") }

Write-Host ""
Write-Host "=== Servidor oficial do Hackathon (Tema 3 - Equipamentos) ===" -ForegroundColor Cyan
Write-Host "  Painel ao vivo: http://localhost:8765"        -ForegroundColor White
Write-Host "  MCP:            http://localhost:8765/mcp"    -ForegroundColor White
Write-Host "  Sistemas legado: http://localhost:8765/legado" -ForegroundColor White
Write-Host "  O painel abre sozinho no navegador. Ctrl+C para parar." -ForegroundColor Yellow
Write-Host ""

Push-Location $servidor
try { & $python @argumentos } finally { Pop-Location }
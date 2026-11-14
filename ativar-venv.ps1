# Script para ativar o venv automaticamente
# Uso: .\ativar-venv.ps1

Write-Host "Ativacao do Ambiente Virtual" -ForegroundColor Cyan
Write-Host "hackathon-t4h" -ForegroundColor Cyan
Write-Host ""

# Verificar se o venv existe
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "ERRO: venv nao encontrado!" -ForegroundColor Red
    Write-Host "Criando venv..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "venv criado com sucesso" -ForegroundColor Green
    Write-Host ""
}

# Ativar venv
Write-Host "Ativando ambiente virtual..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "AMBIENTE VIRTUAL ATIVADO!" -ForegroundColor Green
Write-Host ""
Write-Host "Informacoes do Ambiente" -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Cyan
python --version
Write-Host ""
Write-Host "Pacotes Instalados:" -ForegroundColor Cyan
pip list | Select-Object -First 15
Write-Host ""
Write-Host "Proximos Passos:" -ForegroundColor Cyan
Write-Host "1. Configurar .env: cp .env.example .env" -ForegroundColor White
Write-Host "2. Executar testes: pytest -v" -ForegroundColor White
Write-Host "3. Executar programa: python main.py --help" -ForegroundColor White
Write-Host ""
Write-Host "Para desativar o venv, digite: deactivate" -ForegroundColor Yellow
Write-Host ""

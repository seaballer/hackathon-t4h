# Script para executar o main.py com o venv ativado

Write-Host "Ativando venv..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"

Write-Host "Executando main.py..." -ForegroundColor Green
python main.py

Write-Host "Execução concluída" -ForegroundColor Yellow

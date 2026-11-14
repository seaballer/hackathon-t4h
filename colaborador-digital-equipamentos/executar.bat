@echo off
REM Script para executar o colaborador-digital-equipamentos
REM Uso: executar.bat [argumentos]

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║              COLABORADOR DIGITAL — GESTÃO DE EQUIPAMENTOS                 ║
echo ║                         Hackathon UNIFEI 2026                             ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Verificar se o venv do hackathon-t4h existe
if not exist "..\hackathon-t4h\venv\Scripts\python.exe" (
    echo ❌ ERRO: venv do hackathon-t4h não encontrado!
    echo    Crie o venv em hackathon-t4h primeiro:
    echo    cd ..\hackathon-t4h
    echo    python -m venv venv
    exit /b 1
)

echo 🐍 Usando Python do venv: ..\hackathon-t4h\venv\Scripts\python.exe
echo.

REM Executar o programa
echo 🚀 Executando colaborador-digital-equipamentos...
echo.

..\hackathon-t4h\venv\Scripts\python.exe main.py %*

echo.
echo ✅ Execução concluída

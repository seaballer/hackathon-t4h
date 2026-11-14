@echo off
REM Script para iniciar o servidor MCP

echo Iniciando Servidor MCP...
echo.

REM Verificar se o venv existe
if not exist "venv\Scripts\python.exe" (
    echo ERRO: venv nao encontrado!
    echo Crie o venv primeiro:
    echo python -m venv venv
    exit /b 1
)

echo Usando Python do venv
echo.

REM Executar o servidor MCP
echo Servidor MCP rodando em http://localhost:8765/mcp
echo Pressione Ctrl+C para parar
echo.

venv\Scripts\python.exe -m src.mcp_server

echo.
echo Servidor MCP parado

@echo off
REM Script para ativar o venv automaticamente (CMD)
REM Uso: ativar-venv.bat

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║                    ATIVAÇÃO DO AMBIENTE VIRTUAL                           ║
echo ║                         hackathon-t4h                                     ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Verificar se o venv existe
if not exist "venv\Scripts\activate.bat" (
    echo ❌ ERRO: venv não encontrado!
    echo    Criando venv...
    python -m venv venv
    echo ✅ venv criado com sucesso
    echo.
)

REM Ativar venv
echo 🐍 Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo.
echo ✅ AMBIENTE VIRTUAL ATIVADO!
echo.
echo 📊 Informações do Ambiente
echo ─────────────────────────────────────────────────────────────────────────────
python --version
echo.
echo 📦 Pacotes Instalados:
pip list | findstr /V "^$"
echo.
echo 🎯 Próximos Passos:
echo    1. Configurar .env: copy .env.example .env
echo    2. Executar testes: pytest -v
echo    3. Executar programa: python main.py --help
echo.
echo 💡 Para desativar o venv, digite: deactivate
echo.

@echo off
setlocal

REM Define o diretório do projeto
set "PROJECT_DIR=I:\UNIP\TCC\SUMO"

REM Verifica se o diretório existe
if not exist "%PROJECT_DIR%" (
    echo ERRO: Diretório do projeto não encontrado: %PROJECT_DIR%
    pause
    exit /b 1
)

REM Caminhos para executáveis - corrigido para usar SUMO_HOME do sistema
if defined SUMO_HOME (
    set "SUMO_HOME_TOOLS=%SUMO_HOME%\tools"
) else (
    set "SUMO_HOME_TOOLS=C:\Users\RoHenPer\Desktop\SUMO\tools"
)
set "NETEDIT_EXE=%SUMO_HOME_TOOLS%\netedit.exe"

color 0A

:MAIN_MENU
cls
echo =======================================================
echo              MENU PRINCIPAL DO PROJETO SUMO
echo =======================================================
echo.
echo   [1] Iniciar Simulacao SUMO e Dashboard (Modo Dinamico)
echo   [2] Iniciar Simulacao SUMO e Dashboard (Modo Conservador)
echo   [3] Iniciar Somente Simulacao SUMO (sem dashboard)
echo   [4] Iniciar Somente Dashboard (usando ultimo arquivo salvo)
echo   [5] Gerar Malha para o SUMO (Abrir Netedit)
echo   [6] Gerar Malha para a Unity (Instrucoes)
echo   [7] Comparar Modos Conservador vs. Dinamico
echo   [8] Sair do Programa
echo.
echo =======================================================
set /p "CHOICE=Digite o numero da opcao e pressione Enter: "

if "%CHOICE%"=="1" goto RUN_DYNAMIC_FLOW
if "%CHOICE%"=="2" goto RUN_CONSERVATIVE_FLOW
if "%CHOICE%"=="3" goto RUN_SUMO_ONLY_FLOW
if "%CHOICE%"=="4" goto RUN_DASH_ONLY_FLOW
if "%CHOICE%"=="5" goto GENERATE_SUMO_MESH
if "%CHOICE%"=="6" goto GENERATE_UNITY_MESH
if "%CHOICE%"=="7" goto RUN_COMPARISON
if "%CHOICE%"=="8" goto EXIT_PROGRAM

echo.
echo Opcao invalida. Digite 1, 2, 3, 4, 5, 6, 7 ou 8.
timeout /t 2 >nul
goto MAIN_MENU

:RUN_DYNAMIC_FLOW
set "MODE_ARG=--mode dynamic"
set "RUN_DASH=yes"
goto COMMON_SUMO_RUN

:RUN_CONSERVATIVE_FLOW
set "MODE_ARG=--mode conservative"
set "RUN_DASH=yes"
goto COMMON_SUMO_RUN

:RUN_SUMO_ONLY_FLOW
set "MODE_ARG=--mode dynamic"
set "RUN_DASH=no"
goto COMMON_SUMO_RUN

:RUN_DASH_ONLY_FLOW
cls
echo =======================================================
echo              INICIANDO SOMENTE DASHBOARD
echo =======================================================
echo.
cd /d "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio! & pause & exit /b 1)

REM Ativa o ambiente virtual, se existir
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    echo Ambiente virtual ativado.
) else (
    echo Aviso: Ambiente virtual 'venv' nao encontrado. Executando com o interpretador Python do sistema.
)

REM Encontra o arquivo JSON de dados mais recente em dashboard_output
set "LATEST_FILE="
for /f "delims=" %%i in ('dir /b /o-d "%PROJECT_DIR%\dashboard_output\simulation_dashboard_data_*.json" 2^>nul') do (
    set "LATEST_FILE=%%i"
    goto FILE_FOUND
)

echo ERRO: Nao foram encontrados arquivos de dados de simulacao em "%PROJECT_DIR%\dashboard_output\".
pause
goto ASK_RETURN_TO_MENU

:FILE_FOUND
echo Usando o arquivo de dados mais recente: %LATEST_FILE%
echo.
echo Iniciando Dashboard...
python dashboard.py "%PROJECT_DIR%\dashboard_output\%LATEST_FILE%" --mode dynamic

echo.
echo Dashboard encerrado.
goto ASK_RETURN_TO_MENU

:GENERATE_SUMO_ME
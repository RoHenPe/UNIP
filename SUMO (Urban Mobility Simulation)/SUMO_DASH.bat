@echo off
setlocal

REM --- CONFIGURACAO ---
set "PROJECT_DIR=I:\UNIP\TCC\SUMO"

REM --- VERIFICACAO DO AMBIENTE ---
if not exist "%PROJECT_DIR%" (
    echo ERRO: O diretorio do projeto nao foi encontrado: %PROJECT_DIR%
    pause
    exit /b 1
)
cd /d "%PROJECT_DIR%"

if defined SUMO_HOME (
    set "PATH=%SUMO_HOME%\bin;%PATH%"
    echo SUMO_HOME encontrado. Adicionando '%SUMO_HOME%\bin' ao PATH.
) else (
    echo AVISO: Variavel de ambiente SUMO_HOME nao definida. A execucao pode falhar.
)

:MAIN_MENU
cls
echo =======================================================
echo              MENU PRINCIPAL DO PROJETO SUMO
echo =======================================================
echo.
echo   [1] Iniciar Simulacao DINAMICA (Modo Interativo)
echo   [2] Iniciar Simulacao CONVENCIONAL (Modo Interativo)
echo   [3] Apenas Gerar Dashboard (com ultimos dados salvos)
echo   [4] Abrir Editor de Malha (Netedit)
echo   [5] Sair
echo.
echo =======================================================
set /p "CHOICE=Digite o numero da opcao e pressione Enter: "

if "%CHOICE%"=="1" goto RUN_DYNAMIC
if "%CHOICE%"=="2" goto RUN_CONVENTIONAL
if "%CHOICE%"=="3" goto RUN_DASH_ONLY
if "%CHOICE%"=="4" goto OPEN_NETEDIT
if "%CHOICE%"=="5" goto EXIT_PROGRAM

echo.
echo Opcao invalida. Pressione qualquer tecla para tentar novamente.
pause >nul
goto MAIN_MENU

:RUN_DYNAMIC
call :RUN_SIMULATION --mode dynamic
goto AFTER_SIMULATION

:RUN_CONVENTIONAL
call :RUN_SIMULATION --mode conventional
goto AFTER_SIMULATION

:RUN_SIMULATION
cls
echo =======================================================
echo       INICIANDO SIMULACAO SUMO (Modo: %2)
echo =======================================================
echo.
echo A simulacao ira rodar em blocos de 01 minutos.
echo Voce sera perguntado se deseja continuar no final de cada bloco.
echo.
pause

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python controle_semaforo.py %1 %2
goto :eof

:AFTER_SIMULATION
cls
echo.
echo Simulacao finalizada pelo usuario.
echo.
set /p "DASH_CHOICE=Deseja gerar e abrir o dashboard com os resultados? (s/n): "
if /i "%DASH_CHOICE%"=="s" (
    goto RUN_DASH_ONLY
) else (
    goto ASK_RETURN_TO_MENU
)

:RUN_DASH_ONLY
cls
echo =======================================================
echo              GERANDO O DASHBOARD
echo =======================================================
echo.
if not exist "dashboard_output\simulation_dashboard_data.json" (
    echo ERRO: Arquivo 'simulation_dashboard_data.json' nao encontrado.
    goto ASK_RETURN_TO_MENU
)

echo Iniciando o script do dashboard...
python dashboard.py

goto ASK_RETURN_TO_MENU

:OPEN_NETEDIT
cls
echo Abrindo o Netedit...
if defined SUMO_HOME (
    start "" "%SUMO_HOME%\bin\netedit.exe"
) else (
    echo ERRO: Nao foi possivel encontrar o Netedit. Defina a variavel SUMO_HOME.
)
goto MAIN_MENU

:ASK_RETURN_TO_MENU
echo.
echo =======================================================
echo Tarefa concluida.
echo.
set /p "RETURN_CHOICE=Pressione 'M' para voltar ao menu ou outra tecla para sair: "
if /i "%RETURN_CHOICE%"=="m" goto MAIN_MENU
goto EXIT_PROGRAM

:EXIT_PROGRAM
cls
echo Encerrando...
endlocal
exit /b 0
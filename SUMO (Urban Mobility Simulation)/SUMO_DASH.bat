@echo off
REM --- ATENCAO: Este script contem um caminho fixo para o projeto.
REM --- Se o projeto for movido, ajuste 'C:\Users\RoHenPer\Desktop\TR\sumo_ark'
REM --- na linha 'set "PROJECT_DIR=..."' abaixo.

REM Define o caminho fixo do projeto.
set "PROJECT_DIR=I:\SUMO\TR\SUMO_ARK"

color 0A

:MAIN_MENU
cls
echo =======================================================
echo              MENU PRINCIPAL DO PROJETO SUMO
echo =======================================================
echo.
echo Escolha uma opcao:
echo.
echo   [1] Iniciar Simulacao SUMO e Dashboard
echo   [2] Iniciar Somente Simulacao SUMO
echo   [3] Iniciar Somente Dashboard
echo   [4] Sair do Programa
echo.
echo =======================================================
set /p "CHOICE=Digite o numero da opcao e pressione Enter: "

if "%CHOICE%"=="1" ( goto RUN_SUMO_AND_DASH_FLOW )
if "%CHOICE%"=="2" ( goto RUN_SUMO_ONLY_FLOW )
if "%CHOICE%"=="3" ( goto RUN_DASH_ONLY_FLOW )
if "%CHOICE%"=="4" ( goto EXIT_PROGRAM )

echo.
echo Opcao invalida. Digite 1, 2, 3 ou 4.
pause
goto MAIN_MENU

:RUN_SUMO_AND_DASH_FLOW
cls
echo =======================================================
echo              INICIANDO FLUXO COMPLETO
echo =======================================================
echo.
echo Iniciando Simulacao SUMO...
echo Apos o termino digite (s/n) para continuar:
cd "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio. & pause & exit /b 1)

REM Redireciona a saida do console de controle_semaforo.py para um arquivo de log.
python controle_semaforo.py > sumo_simulation.log 2>&1

echo.
echo Simulacao SUMO concluida. REMOVENDO A MENSAGEM 'Simulacao SUMO concluida.' PARA AQUI.
echo (Detalhes da execucao em sumo_simulation.log no diretorio do projeto)
echo.
goto COMMON_DASHBOARD_FLOW

:RUN_SUMO_ONLY_FLOW
cls
echo =======================================================
echo              INICIANDO SOMENTE SIMULACAO SUMO
echo =======================================================
echo.
echo Iniciando Simulacao SUMO...
echo Apos o termino digite (s/n) para continuar:
cd "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio. & pause & exit /b 1)

REM Redireciona a saida do console de controle_semaforo.py para um arquivo de log.
python controle_semaforo.py > sumo_simulation.log 2>&1

echo.
echo Simulacao SUMO concluida. REMOVENDO A MENSAGEM 'Simulacao SUMO concluida.' PARA AQUI.
echo (Detalhes em sumo_simulation.log no diretorio do projeto)
echo.
goto ASK_RETURN_TO_MENU

:RUN_DASH_ONLY_FLOW
cls
echo =======================================================
echo              INICIANDO SOMENTE DASHBOARD
echo =======================================================
echo.
echo Pulando execucao da simulacao.
echo.
goto COMMON_DASHBOARD_FLOW

:COMMON_DASHBOARD_FLOW
title Dashboard de Trafego
echo.
echo Preparando ambiente e iniciando Dashboard...
cd /d "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio. & pause & exit /b 1)

echo Verificando ambiente virtual...
if not exist "venv\" (
    echo Criando ambiente virtual...
    python -m venv venv || (echo ERRO: Falha ao criar venv. & pause & exit /b 1)
)
call .\venv\Scripts\activate.bat || (echo ERRO: Falha ao ativar venv. & pause & exit /b 1)
echo venv ativado.

echo Atualizando pip e instalando dependencias...
python -m pip install --upgrade pip >nul 2>&1
pip install dash plotly pandas lxml >nul 2>&1
echo Dependencias OK.

echo.
echo Verificando arquivos de dados para o Dashboard...
if not exist "dashboard_output\simulation_dashboard_data.json" (echo AVISO: Dados JSON nao encontrados!)
if not exist "emission.xml" (echo AVISO: emission.xml nao encontrado!)
if not exist "tripinfo.xml" (echo AVISO: tripinfo.xml nao encontrado!)

echo.
echo Iniciando Dashboard (porta 8050)...
echo O Dashboard deve abrir no seu navegador.
echo Se nao abrir, acesse manualmente: http://localhost:8050
echo.

python dashboard.py

echo.
echo Dashboard encerrado.
goto ASK_RETURN_TO_MENU

:ASK_RETURN_TO_MENU
echo =======================================================
echo                  PROCESSO CONCLUIDO
echo =======================================================
echo.
set /p "RETURN_CHOICE=Voltar ao Menu Principal? (S/N): "

if /I "%RETURN_CHOICE%"=="S" ( goto MAIN_MENU )
goto EXIT_PROGRAM

:EXIT_PROGRAM
echo.
echo Encerrando o programa.
echo.
pause
exit /b 0
@echo off
setlocal enabledelayedexpansion

REM --- CONFIGURACAO DE DIRETORIOS ---
set "PROJECT_DIR=I:\UNIP\TCC\SUMO"
set "ARCH_DIR=%PROJECT_DIR%\Arq.Base"
set "OUTPUT_DIR=%PROJECT_DIR%\simulation_output"

REM Verifica se os diretorios de base existem
if not exist "%PROJECT_DIR%" (
    echo ERRO: Diretorio do projeto nao encontrado: %PROJECT_DIR%
    pause
    exit /b 1
)
if not exist "%ARCH_DIR%" (
    echo ERRO: Diretorio de arquivos base nao encontrado: %ARCH_DIR%
    echo Verifique se a pasta 'Arq.Base' com os scripts .py e a malha existe.
    pause
    exit /b 1
)

REM --- CAMINHOS PARA SCRIPTS PYTHON (AGORA EM ARQ.BASE) ---
set "PYTHON_SCRIPT=%ARCH_DIR%\controle_semaforo.py"
set "DASHBOARD_SCRIPT=%ARCH_DIR%\dashboard.py"
set "UNITY_SCRIPT=%ARCH_DIR%\gerador_rede_viaria.py"

REM --- CAMINHOS PARA EXECUTAVEIS DO SUMO ---
if defined SUMO_HOME (
    set "SUMO_HOME_TOOLS=%SUMO_HOME%\tools"
    set "SUMO_BIN=%SUMO_HOME%\bin"
) else (
    set "SUMO_INSTALL_DIR=%PROJECT_DIR%\SUMO_Raiz"
    if exist "%SUMO_INSTALL_DIR%\tools" (
        set "SUMO_HOME_TOOLS=%SUMO_INSTALL_DIR%\tools"
        set "SUMO_BIN=%SUMO_INSTALL_DIR%\bin"
    ) else (
        echo ERRO: Nao foi possivel encontrar o diretorio de ferramentas do SUMO.
        pause
        exit /b 1
    )
)

REM --- CRIA DIRETORIO DE SAIDA PRINCIPAL ---
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

color 0f

:MAIN_MENU
cls
echo =======================================================
echo              MENU PRINCIPAL DO PROJETO SUMO
echo =======================================================
echo.
echo   [1] Iniciar Simulacao SUMO e Dashboard (Modo Dinamico)
echo   [2] Iniciar Simulacao SUMO e Dashboard (Modo Conservador)
echo   [3] Comparar Modos Conservador vs. Dinamico
echo   [4] Iniciar Somente Simulacao SUMO (Modo Dinamico)
echo   [5] Iniciar Somente Dashboard (visualizar dados salvos)
echo   [6] Gerar Malha para o SUMO (Abrir Netedit)
echo   [7] Gerar Malha para a Unity (3D)
echo   [8] Sair do Programa
echo.
echo =======================================================
set /p "CHOICE=Digite o numero da opcao e pressione Enter: "

if "%CHOICE%"=="" goto MAIN_MENU
if "%CHOICE%"=="1" goto RUN_DYNAMIC_FLOW
if "%CHOICE%"=="2" goto RUN_CONSERVATIVE_FLOW
if "%CHOICE%"=="3" goto RUN_COMPARISON
if "%CHOICE%"=="4" goto RUN_SUMO_ONLY_FLOW
if "%CHOICE%"=="5" goto RUN_DASH_ONLY_FLOW
if "%CHOICE%"=="6" goto GENERATE_SUMO_MESH
if "%CHOICE%"=="7" goto GENERATE_UNITY_MESH
if "%CHOICE%"=="8" goto EXIT_PROGRAM
if "%CHOICE%"=="99" goto EASTER_EGG

echo.
echo Opcao invalida. Digite 1, 2, 3, 4, 5, 6, 7 ou 8.
timeout /t 2 >nul
goto MAIN_MENU

REM --- FLUXOS DE EXECUCAO ---

:RUN_DYNAMIC_FLOW
set "MODE=dynamic"
set "RUN_DASH=yes"
set "MODE_OUTPUT_DIR=%OUTPUT_DIR%\dynamic_output"
goto ASK_FOR_STEPS

:RUN_CONSERVATIVE_FLOW
set "MODE=conservative"
set "RUN_DASH=yes"
set "MODE_OUTPUT_DIR=%OUTPUT_DIR%\conservative_output"
goto ASK_FOR_STEPS

:RUN_SUMO_ONLY_FLOW
set "MODE=dynamic"
set "RUN_DASH=no"
set "MODE_OUTPUT_DIR=%OUTPUT_DIR%\dynamic_only_output"
goto ASK_FOR_STEPS

:ASK_FOR_STEPS
cls
echo =======================================================
echo          CONFIGURACAO DO TEMPO DE SIMULACAO
echo =======================================================
echo.
echo Cada passo de simulacao corresponde a 1 segundo no SUMO.
echo 3000 passos = 50 minutos de simulacao
echo.
set /p STEPS="Digite o numero de passos para a simulacao (ex: 3000): "

if not defined STEPS (
    echo Numero de passos nao informado. Usando padrao: 3000
    set STEPS=3000
    timeout /t 2 >nul
)
goto COMMON_SUMO_RUN

:COMMON_SUMO_RUN
cls
echo =======================================================
echo              INICIANDO SIMULACAO SUMO
echo =======================================================
echo.
echo Criando diretorio de saida em: !MODE_OUTPUT_DIR!
if not exist "!MODE_OUTPUT_DIR!" mkdir "!MODE_OUTPUT_DIR!"
echo.

cd /d "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio! & pause & exit /b 1)

REM Ativa o ambiente virtual, se existir
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    echo Ambiente virtual ativado.
) else (
    echo Aviso: Ambiente virtual 'venv' nao encontrado.
)

echo Executando simulacao no modo: !MODE! com !STEPS! passos...
echo Os arquivos serao salvos em: !MODE_OUTPUT_DIR!
python "%PYTHON_SCRIPT%" --mode !MODE! --steps !STEPS! --output "!MODE_OUTPUT_DIR!"

if errorlevel 1 (
    echo.
    echo ERRO: Falha na execucao da simulacao.
    pause
    goto MAIN_MENU
)

if "!RUN_DASH!"=="yes" (
    echo.
    echo Iniciando Dashboard...
    python "%DASHBOARD_SCRIPT%" --source "!MODE_OUTPUT_DIR!"
)

goto ASK_RETURN_TO_MENU

:RUN_DASH_ONLY_FLOW
cls
echo =======================================================
echo          INICIANDO DASHBOARD (DADOS SALVOS)
echo =======================================================
echo.
echo Qual conjunto de dados voce deseja visualizar?
echo   [1] Dados da simulacao Dinamica
echo   [2] Dados da simulacao Conservadora
echo.
set /p "DASH_CHOICE=Digite a opcao: "

if "!DASH_CHOICE!"=="1" set "DASH_SOURCE_DIR=%OUTPUT_DIR%\dynamic_output"
if "!DASH_CHOICE!"=="2" set "DASH_SOURCE_DIR=%OUTPUT_DIR%\conservative_output"

if not exist "!DASH_SOURCE_DIR!" (
    echo ERRO: O diretorio de dados '!DASH_SOURCE_DIR!' nao foi encontrado.
    echo Execute a simulacao correspondente primeiro.
    pause
    goto MAIN_MENU
)

cd /d "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio! & pause & exit /b 1)
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"

echo Iniciando dashboard com dados de: !DASH_SOURCE_DIR!
python "%DASHBOARD_SCRIPT%" --source "!DASH_SOURCE_DIR!"

goto ASK_RETURN_TO_MENU

:GENERATE_SUMO_MESH
cls
echo =======================================================
echo              ABRINDO NETEDIT DO SUMO
echo =======================================================
echo.
set "NETEDIT_EXE=%SUMO_BIN%\netedit.exe"

if exist "!NETEDIT_EXE!" (
    start "" "!NETEDIT_EXE!"
    echo Netedit iniciado. Lembre-se de salvar sua malha em '%ARCH_DIR%'.
) else (
    echo ERRO: Netedit nao encontrado em: !NETEDIT_EXE!
)
echo.
pause
goto ASK_RETURN_TO_MENU

:GENERATE_UNITY_MESH
cls

echo
echo =======================================================
echo          GERANDO MALHA 3D PARA UNITY
echo =======================================================
echo.
set "UNITY_OUTPUT_DIR=%OUTPUT_DIR%\Malha_UNITY"
echo Criando diretorio de saida em: %UNITY_OUTPUT_DIR%
if not exist "%UNITY_OUTPUT_DIR%" mkdir "%UNITY_OUTPUT_DIR%"
echo.

if not exist "%UNITY_SCRIPT%" (
    echo ERRO: Script de geracao para Unity nao encontrado: %UNITY_SCRIPT%
    pause
    goto MAIN_MENU
)

cd /d "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio! & pause & exit /b 1)
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"

echo Executando script de geracao de malha...
python "%UNITY_SCRIPT%" --output "%UNITY_OUTPUT_DIR%"

echo.
echo Verifique os arquivos gerados em:
echo %UNITY_OUTPUT_DIR%
pause
goto ASK_RETURN_TO_MENU

:RUN_COMPARISON
cls
echo =======================================================
echo          EXECUTANDO COMPARACAO ENTRE MODOS
echo =======================================================
echo.
set /p COMP_STEPS="Digite o numero de passos para comparacao (ex: 3000): "
if not defined COMP_STEPS set "COMP_STEPS=3000"

set "DYNAMIC_COMP_DIR=%OUTPUT_DIR%\dynamic_output"
set "CONSERVATIVE_COMP_DIR=%OUTPUT_DIR%\conservative_output"

if not exist "%DYNAMIC_COMP_DIR%" mkdir "%DYNAMIC_COMP_DIR%"
if not exist "%CONSERVATIVE_COMP_DIR%" mkdir "%CONSERVATIVE_COMP_DIR%"

cd /d "%PROJECT_DIR%" || (echo ERRO: Falha ao acessar diretorio! & pause & exit /b 1)
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"

echo.
echo [1/3] Executando modo dinamico com !COMP_STEPS! passos...
echo       Saida em: %DYNAMIC_COMP_DIR%
python "%PYTHON_SCRIPT%" --mode dynamic --steps !COMP_STEPS! --output "%DYNAMIC_COMP_DIR%"
if errorlevel 1 (echo ERRO. Abortando. & pause & goto MAIN_MENU)

echo.
echo [2/3] Executando modo conservador com !COMP_STEPS! passos...
echo       Saida em: %CONSERVATIVE_COMP_DIR%
python "%PYTHON_SCRIPT%" --mode conservative --steps !COMP_STEPS! --output "%CONSERVATIVE_COMP_DIR%"
if errorlevel 1 (echo ERRO. Abortando. & pause & goto MAIN_MENU)

echo.
echo [3/3] Iniciando dashboard comparativo...
python "%DASHBOARD_SCRIPT%" --mode compare --dynamic_source "%DYNAMIC_COMP_DIR%" --conservative_source "%CONSERVATIVE_COMP_DIR%"

goto ASK_RETURN_TO_MENU

:EASTER_EGG
cls
echo Carregando... Divirta-se!
start "" "https://pointerpointer.com/" >nul 2>&1
echo.
echo
echo
echo                            ..,,,,,,,,,.. 
echo                      .,;%%%%%%%%%%%%%%%%%%%%;,. 
echo                    %%%%%%%%%%%%%%%%%%%%////%%%%%%, .,;%%;, 
echo             .,;%/,%%%%%/////%%%%%%%%%%%%%%////%%%%,%%//%%%, 
echo         .,;%%%%/,%%%///%%%%%%%%%%%%%%%%%%%%%%%%%%%%,////%%%%;, 
echo      .,%%%%%%//,%%%%%%%%%%%%%%%%@@%a%%%%%%%%%%%%%%%%,%%/%%%%%%%;, 
echo   .,%//%%%%//,%%%%///////%%%%%%%@@@%%%%%%///////%%%%,%%//%%%%%%%%, 
echo  ,%%%%%///%%//,%%//%%%%%///%%%%%@@@%%%%%////%%%%%%%%%,/%%%%%%%%%%%%% 
echo .%%%%%%%%%////,%%%%%%%//%///%%%%@@@@%%%////%%/////%%%,/;%%%%%%%%/%%% 
echo %/%%%%%%%/////,%%%%///%%////%%%@@@@@%%%///%%/%%%%%//%,////%%%%//%%%' 
echo %//%%%%%//////,%/%a`  'a%///%%%@@@@@@%%////a`  'a%%%%,//%///%/%%%%% 
echo %///%%%%%%///,%%%%@@aa@@%//%%%@@@@S@@@%%///@@aa@@%%%%%,/%////%%%%% 
echo %%//%%%%%%%//,%%%%%///////%%%@S@@@@SS@@@%%/////%%%%%%%,%////%%%%%' 
echo %%//%%%%%%%//,%%%%/////%%@%@SS@@@@@@@S@@@@%%%%/////%%%,////%%%%%' 
echo `%/%%%%//%%//,%%%///%%%%@@@S@@@@@@@@@@@@@@@S%%%%////%%,///%%%%%' 
echo   %%%%//%%%%/,%%%%%%%%@@@@@@@@@@@@@@@@@@@@@SS@%%%%%%%%,//%%%%%' 
echo   `%%%//%%%%/,%%%%@%@@@@@@@@@@@@@@@@@@@@@@@@@S@@%%%%%,/////%%' 
echo    `%%%//%%%/,%%%@@@SS@@SSs@@@@@@@@@@@@@sSS@@@@@@%%%,//%%//%' 
echo     `%%%%%%/  %%S@@SS@@@@@Ss` .,,.    'sS@@@S@@@@%'  ///%/%' 
echo       `%%%/    %SS@@@@SSS@@S.         .S@@SSS@@@@'    //%%' 
echo               /`S@@@@@@SSSSSs,     ,sSSSSS@@@@@' 
echo              %%//`@@@@@@@@@@@@@Ss,sS@@@@@@@@@@@'/ 
echo            %%%%@@00`@@@@@@@@@@@@@'@@@@@@@@@@@'//%% 
echo        %%%%%%a%@@@@000aaaaaaaaa00a00aaaaaaa00%@%%%%% 
echo     %%%%%%a%%@@@@@@@@@@000000000000000000@@@%@@%%%@%%% 
echo  %%%%%%a%%@@@%@@@@@@@@@@@00000000000000@@@@@@@@@%@@%%@%% 
echo %%%aa%@@@@@@@@@@@@@@0000000000000000000000@@@@@@@@%@@@%%%% 
echo %%@@@@@@@@@@@@@@@00000000000000000000000000000@@@@@@@@@%%%%%
echo.
echo Pressione qualquer tecla para voltar ao menu...
pause >nul
goto MAIN_MENU

:ASK_RETURN_TO_MENU
echo.
set /p "RETURN_CHOICE=Pressione 'M' para voltar ao menu ou qualquer outra tecla para sair: "
if /i "!RETURN_CHOICE!"=="M" goto MAIN_MENU

:EXIT_PROGRAM
echo Encerrando programa...
endlocal
exit /b 0
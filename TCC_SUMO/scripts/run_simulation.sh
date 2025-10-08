#!/bin/bash
# ==============================================================================
#   SCRIPT ORQUESTRADOR PARA EXECUÇÃO DA SIMULAÇÃO DE TRÁFEGO
# ==============================================================================

# --- Configuração de Caminhos ---
# Deteta o diretório absoluto do script.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# CORREÇÃO CRÍTICA: MUDAR O DIRETÓRIO DE TRABALHO PARA A RAIZ DO PROJETO (TCC_SUMO/)
# Assume que run_simulation.sh está em scripts/, então sobe um nível.
cd "$SCRIPT_DIR/.." || exit

# Agora, o diretório de trabalho é TCC_SUMO/
PROJECT_ROOT_DIR="$(pwd)"

# Adiciona a pasta 'src' ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT_DIR}/src"

# Define o caminho absoluto correto para os logs
LOG_DIR="${PROJECT_ROOT_DIR}/logs"

# --- Ativa o Ambiente Virtual, se existir ---
VENV_PATH=".venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
fi

# --- Função de Spinner e Execução em Background ---
execute_with_spinner() {
    local cmd_to_run="$1"; local log_file_name="$2"; local spinner_message="$3"
    mkdir -p "$LOG_DIR"
    local log_file_path="${LOG_DIR}/${log_file_name}"
    
    # [CORREÇÃO: PRESERVAÇÃO DE LOGS]
    # A opção original era limpar o log antes da execução (>).
    # Agora, permitimos que os logs (que já usam RotatingFileHandler) e 
    # o shell (com >>) APENDEM o novo conteúdo para preservar o histórico.
    if [ "$log_file_name" == "analysis.log" ] || [ "$log_file_name" == "sumo_simulation.log" ]; then
        # Estes logs são limpos, pois são logs auxiliares que devem ser frescos por execução.
        >"$log_file_path"
    fi
    
    # Redireciona a saída do shell (STDOUT e STDERR) para o arquivo, APENDANDO (>>)
    eval $cmd_to_run >> "$log_file_path" 2>&1 &
    local pid=$!; local spin='|/-\'; local i=0
    
    echo -n "$spinner_message "
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) %4 )); printf "\b${spin:$i:1}"; sleep .1
    done
    printf "\b "; wait $pid; local exit_code=$?
    
    echo "";
    if [ $exit_code -eq 0 ]; then
        echo "[✓] Processo concluído com sucesso."
    else
        echo "[✗] ERRO: Ocorreu uma falha. Verifique os detalhes em '$log_file_path'."
    fi
    echo "----------------------------------------------------------------"
}

# --- Função para Perguntar a Densidade de Tráfego ---
prompt_for_density() {
    clear
    cat << "EOF"
================================================================
           SELECIONE A DENSIDADE DE TRÁFEGO
================================================================
   1. Rápido (5,000 veículos)   - Para testes e validação
   2. Detalhado (50,000 veículos) - Para análise de performance
   3. Massivo (150,000 veículos) - Para simulações de stress
   4. Personalizado             - Inserir um valor manualmente
----------------------------------------------------------------
EOF
    read -p "Selecione o nível de densidade: " density_choice
    
    case $density_choice in
        1) export VEHICLE_COUNT=5000 ;;
        2) export VEHICLE_COUNT=50000 ;;
        3) export VEHICLE_COUNT=150000 ;;
        4) read -p "Digite a quantidade de veículos desejada: " custom_count
           if [[ "$custom_count" =~ ^[0-9]+$ ]]; then export VEHICLE_COUNT=$custom_count
           else echo "Valor inválido. A usar o padrão de 50,000."; export VEHICLE_COUNT=50000; sleep 2; fi ;;
        *) echo "Opção inválida. A usar o padrão de 50,000."; export VEHICLE_COUNT=50000; sleep 2 ;;
    esac
}

# --- Loop do Menu Principal ---
while true; do
    clear
    cat << "EOF"
================================================================
      TCC - SIMULADOR DE TRÁFEGO URBANO COM SUMO
================================================================
 Geração de Cenários:
   1. Gerar/Recriar Cenário OpenStreetMap (OSM)
   2. Gerar/Recriar Cenário via API

 Simulação - Cenário OSM:
   3. Simular Modo Estático       - OSM
   4. Simular Modo Adaptativo     - OSM

 Simulação - Cenário API:
   5. Simular Modo Estático       - API
   6. Simular Modo Adaptativo     - API

 Análise de Resultados:
   7. Gerar Dashboard de Logs
   8. Gerar Dashboard de Tráfego

 Outras Opções:
   9. Limpar Ficheiros de Log e Cenários Gerados
   0. Sair
================================================================
EOF
    
    read -p "Selecione uma opção: " choice
    
    case $choice in
        1) prompt_for_density
           cmd="python3 -m tcc_sumo.tools.scenario_generator --type osm --input osm_bbox.osm.xml"
           log="generation.log"; msg="[ ] Gerando cenário OSM com ${VEHICLE_COUNT} veículos..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        2) prompt_for_density
           cmd="python3 -m tcc_sumo.tools.scenario_generator --type api --input dados_api.json"
           log="generation.log"; msg="[ ] Gerando cenário API com ${VEHICLE_COUNT} veículos..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        # CORREÇÃO: Consolida o logging da simulação para um único ficheiro (simulation.log)
        3) cmd="python3 -m main --scenario osm --mode STATIC"
           log="simulation.log"; msg="[ ] Rodando simulação OSM Estático..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        4) cmd="python3 -m main --scenario osm --mode ADAPTIVE"
           log="simulation.log"; msg="[ ] Rodando simulação OSM Adaptativo..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        5) cmd="python3 -m main --scenario api --mode STATIC"
           log="simulation.log"; msg="[ ] Rodando simulação API Estático..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        6) cmd="python3 -m main --scenario api --mode ADAPTIVE"
           log="simulation.log"; msg="[ ] Rodando simulação API Adaptativo..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        7) cmd="python3 -m tcc_sumo.tools.traffic_analyzer --source logs"
           log="analysis.log"; msg="[ ] Gerando Dashboard de Logs..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        8) cmd="python3 -m tcc_sumo.tools.traffic_analyzer --source traffic"
           log="analysis.log"; msg="[ ] Gerando Dashboard de Tráfego..."
           execute_with_spinner "$cmd" "$log" "$msg";;
        9) echo "Limpando diretórios..."; rm -f logs/* output/*; rm -rf scenarios/from_api/* scenarios/from_osm/*
           echo "[✓] Limpeza concluída."; sleep 1;;
        0) echo "Encerrando o simulador."; break;;
        *) echo "Opção inválida."; sleep 1;;
    esac
    if [[ "$choice" != "0" ]]; then
        read -n 1 -s -r -p "Pressione qualquer tecla para voltar ao menu..."
    fi
done
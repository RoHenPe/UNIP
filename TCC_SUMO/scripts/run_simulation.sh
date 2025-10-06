#!/bin/bash
# ==============================================================================
#   SCRIPT ORQUESTRADOR PARA EXECUÇÃO DA SIMULAÇÃO DE TRÁFEGO
# ==============================================================================
#
#   Este script fornece um menu interativo para o usuário, simplificando a
#   geração de cenários, execução da simulação, análise de dados e limpeza.
#

# --- Ativa o Ambiente Virtual, se existir ---
VENV_PATH=".venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
fi

# --- Função para Executar a Simulação ---
run_python_simulation() {
    local scenario="$1"
    local mode="$2"
    
    echo "[$(date +'%d/%m/%Y - %H:%M:%S')] [INFO    ] [run_simulation.sh      ] : Iniciando simulação: Cenário=$scenario, Modo=$mode" >> logs/simulation.log
    
    python3 src/main.py --scenario "$scenario" --mode "$mode"
}

# --- Loop do Menu Principal ---
while true; do
    clear
    echo "================================================================"
    echo "      TCC - SIMULADOR DE TRÁFEGO URBANO COM SUMO"
    echo "================================================================"
    echo " Geração de Cenários:"
    echo "   1. Gerar/Recriar Cenário OpenStreetMap (OSM)"
    echo "   2. Gerar/Recriar Cenário via API"
    echo
    echo " Simulação - Cenário OSM:"
    echo "   3. Simular Modo Estático       - OSM"
    echo "   4. Simular Modo Adaptativo     - OSM"
    echo
    echo " Simulação - Cenário API:"
    echo "   5. Simular Modo Estático       - API"
    echo "   6. Simular Modo Adaptativo     - API"
    echo
    echo " Análise de Resultados:"
    echo "   7. Gerar Dashboard de Logs"
    echo "   8. Gerar Dashboard de Tráfego"
    echo
    echo " Outras Opções:"
    echo "   9. Limpar Arquivos de Log e Dados"
    echo "   0. Sair"
    echo "================================================================"
    
    read -p "Selecione uma opção: " choice
    
    case $choice in
        1)
            python3 src/tcc_sumo/tools/scenario_generator.py --type osm --input "osm_bbox.osm.xml"
            ;;
        2)
            python3 src/tcc_sumo/tools/scenario_generator.py --type api --input "dados_api.json"
            ;;
        3) run_python_simulation "osm" "STATIC" ;;
        4) run_python_simulation "osm" "ADAPTIVE" ;;
        5) run_python_simulation "api" "STATIC" ;;
        6) run_python_simulation "api" "ADAPTIVE" ;;
        7)
            echo "Gerando Dashboard de Logs..."
            python3 src/tcc_sumo/tools/traffic_analyzer.py --source logs
            ;;
        8)
            echo "Gerando Dashboard de Tráfego..."
            python3 src/tcc_sumo/tools/traffic_analyzer.py --source traffic
            ;;
        9)
            echo "Limpando arquivos de log e dados..."
            rm -f logs/*.log output/*.json output/*.html
            rm -rf scenarios/from_api/* scenarios/from_osm/*
            echo "Arquivos de log, relatórios, dashboards e cenários gerados foram removidos."
            ;;
        0)
            echo "Encerrando o simulador."
            break
            ;;
        *)
            echo "Opção inválida. Por favor, tente novamente."
            ;;
    esac
    
    echo
    read -p "Pressione Enter para continuar..."
done
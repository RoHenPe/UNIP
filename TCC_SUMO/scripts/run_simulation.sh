#!/bin/bash
# ==============================================================================
#   SCRIPT ORQUESTRADOR PARA EXECUÇÃO DA SIMULAÇÃO DE TRÁFEGO
# ==============================================================================
#
#   Este script fornece um menu interativo para o usuário, simplificando a
#   execução da simulação, geração de cenários, análise de dados e limpeza
#   de logs.
#

# --- Navega para o diretório raiz do projeto ---
cd "$(dirname "$0")/.."

# --- Ativa o Ambiente Virtual, se existir ---
VENV_PATH=".venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
fi

# --- Função para Executar a Simulação ---
run_python_simulation() {
    local scenario="$1"
    local mode="$2"
    
    # Registra o início da simulação no arquivo de log
    echo "[$(date +'%d/%m/%Y - %H:%M:%S')] [INFO    ] [run_simulation.sh      ] : Iniciando simulação: Cenário=$scenario, Modo=$mode" >> logs/simulation.log
    
    python3 src/main.py --scenario "$scenario" --mode "$mode"
}

# --- Loop do Menu Principal ---
while true; do
    clear
    echo "================================================================"
    echo "      TCC - SIMULADOR DE TRÁFEGO URBANO COM SUMO"
    echo "================================================================"
    echo " Cenário OpenStreetMap (OSM):"
    echo "   1. Simular Modo Estático       - OSM"
    echo "   2. Simular Modo Adaptativo     - OSM"
    echo
    echo " Cenário Gerado via API:"
    echo "   3. Gerar Novo Cenário via API"
    echo "   4. Simular Modo Estático       - API"
    echo "   5. Simular Modo Adaptativo     - API"
    echo
    echo " Análise de Resultados:"
    echo "   6. Gerar Dashboard de Logs (analisa simulation.log)"
    echo "   7. Gerar Dashboard de Tráfego (analisa consolidated_data.json)"
    echo
    echo " Outras Opções:"
    echo "   8. Limpar Arquivos de Log e Dados"
    echo "   0. Sair"
    echo "================================================================"
    
    read -p "Selecione uma opção: " choice
    
    case $choice in
        1) run_python_simulation "osm" "STATIC" ;;
        2) run_python_simulation "osm" "ADAPTIVE" ;;
        3)
            echo "Executando o gerador de cenário via API..."
            python3 src/tcc_sumo/tools/scenario_generator.py
            ;;
        4) run_python_simulation "api" "STATIC" ;;
        5) run_python_simulation "api" "ADAPTIVE" ;;
        6)
            echo "Gerando Dashboard de Logs..."
            python3 src/tcc_sumo/tools/traffic_analyzer.py --source logs
            ;;
        7)
            echo "Gerando Dashboard de Tráfego..."
            python3 src/tcc_sumo/tools/traffic_analyzer.py --source traffic
            ;;
        8)
            echo "Limpando arquivos de log e dados..."
            rm -f logs/simulation.log logs/simulation_report.log output/consolidated_data.json output/*.html
            echo "Arquivos de log, relatórios e dashboards foram removidos."
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
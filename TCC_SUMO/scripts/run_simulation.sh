#!/bin/bash

# Define o diretório raiz do projeto e o diretório de origem
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
SRC_DIR="$PROJECT_ROOT/src"

# Função para exibir o menu
show_menu() {
    clear
    echo "================================================================"
    echo "          TCC - SIMULADOR DE TRÁFEGO URBANO COM SUMO"
    echo "================================================================"
    echo "  Selecione o Cenário e o Modo de Simulação:"
    echo
    echo "  Cenário OpenStreetMap (OSM):"
    echo "    1. Simular Modo Estático      - OSM"
    echo "    2. Simular Modo Adaptativo    - OSM"
    echo
    echo "  Cenário Gerado via API:"
    echo "    3. Gerar Novo Cenário via API"
    echo "    4. Simular Modo Estático      - API"
    echo "    5. Simular Modo Adaptativo    - API"
    echo
    echo "  Outras Opções:"
    echo "    6. Limpar Arquivos de Log"
    echo "    7. Gerar e Abrir Dashboard de Logs"
    echo "    8. Sair"
    echo "================================================================"
}

# Função para executar a simulação
run_simulation() {
    local mode=$1
    local steps=$2
    local scenario=$3
    
    echo "Iniciando simulação: Modo=$mode, Cenário=$scenario, Passos=$steps..."
    python3 "$SRC_DIR/main.py" --mode "$mode" --steps "$steps" --scenario "$scenario"
}

# Loop principal do menu
while true; do
    show_menu
    read -p "Selecione uma opção de comando: " choice
    
    case $choice in
        1) run_simulation "STATIC" 5000 "osm" ;;
        2) run_simulation "ADAPTIVE" 5000 "osm" ;;
        3) python3 "$SRC_DIR/tcc_sumo/tools/scenario_generator.py" && read -p "Pressione [Enter] para continuar..." ;;
        
        # Padronizado para usar "api" como a chave do cenário
        4) run_simulation "STATIC" 5000 "api" ;;
        5) run_simulation "ADAPTIVE" 5000 "api" ;;

        6) rm -f "$PROJECT_ROOT/logs/"*.log && echo "Arquivos de log limpos." && sleep 2 ;;
        7) python3 "$SRC_DIR/tcc_sumo/tools/dashboard_generator.py" && xdg-open "$PROJECT_ROOT/logs/dashboard.html" && read -p "Pressione [Enter] para continuar..." ;;
        8) break ;;
        *) echo "Opção inválida. Tente novamente." && sleep 2 ;;
    esac
done
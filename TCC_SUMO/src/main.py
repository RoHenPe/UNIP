# Arquivo: TCC_SUMO/src/main.py
# Ponto de entrada principal para o sistema TCC_SUMO.
# Oferece um menu interativo para o usuário escolher entre várias opções,
# incluindo iniciar a simulação, gerar cenários, criar relatórios e visualizar dashboards de logs.
# Também suporta execução via linha de comando com argumentos para automação.

import sys
import argparse
import time
from pathlib import Path

# Adiciona 'src' ao path para encontrar os módulos
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# --- MÓDULOS DE FUNÇÃO ---
# Importa módulos de TOOLS (apenas o log_analyzer para a Opção 7)
try:
    from tcc_sumo.tools.log_analyzer import generate_and_open_log_dashboard
    from tcc_sumo.tools.reporter import main as run_reporter
    from tcc_sumo.tools.scenario_generator import main as run_scenario_generator
except ImportError as e:
    # Cria fallbacks para que o menu não quebre
    print(f"AVISO CRÍTICO: Falha ao importar módulos. Opções 2, 3 e 7 podem falhar. Detalhe: {e}")
    def generate_and_open_log_dashboard():
        print("Dashboard indisponível.")
    def run_reporter():
        print("Relatório indisponível.")
    def run_scenario_generator():
        print("Gerador de Cenário indisponível.")


# PREPARA O AMBIENTE SUMO
from tcc_sumo.utils.helpers import ensure_sumo_home, load_config, setup_logging, get_logger
ensure_sumo_home()

# Importa módulos de simulação
import traci 
from tcc_sumo.simulation.manager import SimulationManager
from tcc_sumo.simulation.traci_connection import close as close_traci

# --- FUNÇÕES DE EXECUÇÃO ---

def run_cli_simulation(args: argparse.Namespace):
    """Executa a simulação principal com argumentos de modo, passos e cenário."""
    setup_logging()
    logger = get_logger("main")
    sim_manager = None

    try:
        config = load_config()
        
        sim_manager = SimulationManager(
            config=config,
            simulation_mode=args.mode,
            max_steps=args.steps,
            scenario_key=args.scenario
        )
        sim_manager.run()

    except Exception as e:
        logger.critical(f"FALHA CATASTRÓFICA: O programa principal encontrou um erro: {e}", exc_info=True)
        print("\n\n  !! OCORREU UM ERRO INESPERADO !!")
        print("     Consulte o arquivo 'simulation.log' para detalhes técnicos.")
        time.sleep(4)
    
    finally:
        if sim_manager:
            sim_manager.cleanup()
        close_traci()
        time.sleep(1) # Pausa para ver o resultado


def run_interactive_menu():
    """Roda o programa com o menu interativo principal, acionado como fallback."""
    
    def exibir_menu():
        print("\n----- Menu Principal TCC_SUMO -----")
        # Opções originais
        print("1 - Iniciar Simulação (Padrão: STATIC, 600 Passos, Cenário OSM)")
        print("2 - Gerar Cenário (via API)")
        print("3 - Gerar Relatório Estruturado (JSON)")
        
        # Opção da Dashboard (Na Opção 7)
        print("7 - Gerar e Abrir DASHBOARD de Logs (Checklist Automático)") 
        print("0 - Sair")

    def processar_opcao(opcao):
        if opcao == '1':
            print("\n>> Iniciando Simulação Padrão <<")
            
            # Execução direta com valores padrão (STATIC, 600, osm)
            temp_args = argparse.Namespace(mode='STATIC', steps=600, scenario='osm')
            run_cli_simulation(temp_args)

        elif opcao == '2':
            print("-> Gerando Cenário (via API)...")
            run_scenario_generator()

        elif opcao == '3':
            print("-> Gerando Relatório Estruturado (JSON)...")
            run_reporter()
        
        elif opcao == '7':
            # CHAMADA AGORA COM O CHECKLIST
            generate_and_open_log_dashboard()

        elif opcao == '0':
            print("Saindo do sistema. Adeus!")
            return False
        else:
            print("Opção inválida. Tente novamente.")
        
        return True

    setup_logging()
    logger = get_logger("main")
    logger.info("Sistema iniciado em modo interativo.")

    while True:
        exibir_menu()
        opcao = input("Selecione uma opção: ").strip()
        if not processar_opcao(opcao):
            break
        

def main():
    """Ponto de entrada principal, com tratamento de erros para um terminal limpo."""
    
    # Tenta rodar a simulação no modo CLI (comportamento original)
    try:
        parser = argparse.ArgumentParser()
        # Os argumentos são obrigatórios para a simulação CLI
        parser.add_argument("--mode", required=True, type=str.upper)
        parser.add_argument("--steps", required=True, type=int)
        parser.add_argument("--scenario", required=True, type=str.lower)
        
        args = parser.parse_args()
        
        # Se os argumentos estiverem presentes, executa a simulação
        run_cli_simulation(args)

    except SystemExit:
        # SE FALLBACK: Se a simulação CLI falhar (ex: argumentos ausentes), executa o menu interativo.
        run_interactive_menu()

    except Exception as e:
        # Captura QUALQUER erro inesperado para proteger o terminal.
        setup_logging()
        logger = get_logger("main")
        logger.critical(f"FALHA CATASTRÓFICA: O programa principal encontrou um erro: {e}", exc_info=True)
        print("\n\n  !! OCORREU UM ERRO INESPERADO !!")
        print("     A simulação foi interrompida de forma anormal.")
        print("     Consulte o arquivo 'simulation.log' para detalhes técnicos.")
        time.sleep(4)


if __name__ == "__main__":
    main()
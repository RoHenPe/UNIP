import sys
import argparse
import time
from pathlib import Path

# Adiciona 'src' ao path para encontrar os módulos
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Prepara o ambiente do SUMO
from tcc_sumo.utils.helpers import ensure_sumo_home
ensure_sumo_home()

# Importa traci aqui para que o 'except' funcione corretamente
import traci
from tcc_sumo.simulation.manager import SimulationManager
from tcc_sumo.utils.helpers import load_config, setup_logging, get_logger

def main():
    """Ponto de entrada principal, com tratamento de erros para um terminal limpo."""
    setup_logging()
    logger = get_logger("main")
    sim_manager = None

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--mode", required=True, type=str.upper)
        parser.add_argument("--steps", required=True, type=int)
        parser.add_argument("--scenario", required=True, type=str.lower)
        args = parser.parse_args()

        config = load_config()
        
        sim_manager = SimulationManager(
            config=config,
            simulation_mode=args.mode,
            max_steps=args.steps,
            scenario_key=args.scenario
        )
        sim_manager.run()

    except Exception as e:
        # Captura QUALQUER erro inesperado para proteger o terminal.
        logger.critical(f"FALHA CATASTRÓFICA: O programa principal encontrou um erro: {e}", exc_info=True)
        # Mostra uma mensagem amigável em vez do traceback
        print("\n\n  !! OCORREU UM ERRO INESPERADO !!")
        print("     A simulação foi interrompida de forma anormal.")
        print("     Consulte o arquivo 'simulation.log' para detalhes técnicos.")
        time.sleep(4)
    
    finally:
        # Garante que, aconteça o que acontecer, a limpeza final seja chamada.
        if sim_manager:
            sim_manager.cleanup()
        
        input("\n     Pressione [Enter] para retornar ao menu principal...")

if __name__ == "__main__":
    main()
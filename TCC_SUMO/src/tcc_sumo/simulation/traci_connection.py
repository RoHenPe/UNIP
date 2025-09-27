import traci
import os
import sys
from tcc_sumo.utils.helpers import get_logger

logger = get_logger(__name__)

def ensure_sumo_home():
    """Verifica e configura a variável de ambiente SUMO_HOME."""
    if 'SUMO_HOME' not in os.environ:
        sys.exit("CRITICAL ERROR: A variável de ambiente 'SUMO_HOME' não foi declarada.")
    
    tools_path = os.path.join(os.environ['SUMO_HOME'], 'tools')
    if tools_path not in sys.path:
        sys.path.append(tools_path)

def connect(port: int, sumo_executable: str, config_file: str):
    """Inicia o SUMO como um subprocesso e conecta o TraCI."""
    ensure_sumo_home()
    
    logger.info("Iniciando o simulador SUMO e a conexão TraCI...")
    sumo_cmd = [
        sumo_executable,
        "-c", config_file,
        "--remote-port", str(port),
        "--step-length", "1",
        "--time-to-teleport", "-1"
    ]
    
    traci.start(sumo_cmd)
    logger.info("Conexão TraCI estabelecida.")

def close():
    """Encerra a conexão TraCI de forma segura."""
    try:
        traci.close()
        logger.info("Conexão TraCI encerrada.")
    except (traci.TraCIException, AttributeError):
        logger.warning("Não foi possível encerrar a conexão TraCI (pode já estar fechada).")
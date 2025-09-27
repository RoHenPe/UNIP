import yaml
import json
import logging
import logging.config
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def ensure_sumo_home():
    """Verifica e configura a variável de ambiente SUMO_HOME."""
    if 'SUMO_HOME' not in os.environ:
        sys.exit("ERRO CRÍTICO: A variável de ambiente 'SUMO_HOME' não foi declarada.")
    
    tools_path = Path(os.environ['SUMO_HOME']) / 'tools'
    if str(tools_path) not in sys.path:
        sys.path.append(str(tools_path))

def load_config(config_path: Path = None) -> dict:
    """Carrega o arquivo de configuração principal (config.yaml)."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "config.yaml"

    if not config_path.is_file():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def setup_logging(config_path: Path = None):
    """Configura o sistema de logging a partir de um arquivo de configuração JSON."""
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "logging_config.json"
    
    if not config_path.is_file():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.warning(f"Arquivo de configuração de log não encontrado em {config_path}. Usando logging básico.")
        return
    
    with open(config_path, 'rt', encoding='utf-8') as f:
        log_config_data = json.load(f)
    
    for handler in log_config_data.get('handlers', {}).values():
        if 'filename' in handler:
            log_filename = Path(handler['filename'])
            if not log_filename.is_absolute():
                full_log_path = PROJECT_ROOT / log_filename
                full_log_path.parent.mkdir(parents=True, exist_ok=True)
                handler['filename'] = str(full_log_path)

    logging.config.dictConfig(log_config_data)
    root_logger = logging.getLogger()
    root_logger.info("="*60)
    root_logger.info("Sistema de Log inicializado.")
    root_logger.info(f"Log principal: {PROJECT_ROOT / 'logs/simulation.log'}")
    root_logger.info(f"Log do Simulador SUMO: {PROJECT_ROOT / 'logs/sumo_output.log'}")
    root_logger.info("="*60)

def get_logger(name: str) -> logging.Logger:
    """Retorna uma instância de logger com o nome fornecido."""
    return logging.getLogger(name)
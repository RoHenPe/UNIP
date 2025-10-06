import os
import sys
import logging
import logging.config
import json
import yaml
from pathlib import Path

# Define a raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# --- LÓGICA DO CHECKLIST ---
def task_start(message: str):
    """Exibe uma tarefa em andamento."""
    print(f"[ ] {message}...", end='\r')

def task_success(message: str):
    """Marca a tarefa como concluída."""
    print(' ' * 80, end='\r')
    print(f"[✓] {message}")

def task_fail(message: str):
    """Marca a tarefa como falha."""
    print(' ' * 80, end='\r')
    print(f"[✗] {message}")
# --- FIM DO CHECKLIST ---

def format_seconds_to_ms(seconds):
    """Converte segundos para uma string formatada em minutos e segundos."""
    if seconds is None or not isinstance(seconds, (int, float)):
        return "00m 00s"
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}m {seconds:02d}s"

def get_project_root():
    """Retorna a raiz do projeto."""
    return PROJECT_ROOT

def ensure_sumo_home():
    """Garante que a variável de ambiente SUMO_HOME esteja configurada."""
    if 'SUMO_HOME' not in os.environ:
        os.environ['SUMO_HOME'] = "/usr/share/sumo"

def setup_logging():
    """Configura o sistema de logging a partir de um ficheiro JSON."""
    LOGS_DIR.mkdir(exist_ok=True)
    config_path = PROJECT_ROOT / "config" / "logging_config.json"
    
    try:
        with open(config_path, 'rt') as f:
            config = json.load(f)
        
        if 'file' in config['handlers']:
            log_filename = LOGS_DIR / "simulation.log"
            config['handlers']['file']['filename'] = str(log_filename)
        
        logging.config.dictConfig(config)
    except Exception as e:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.warning(f"Falha ao carregar config de log: {e}. Usando config básica.")
    
    return logging.getLogger()

def get_logger(name):
    """Obtém um logger configurado pelo nome."""
    return logging.getLogger(name)
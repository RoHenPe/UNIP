# -*- coding: utf-8 -*-
import logging
import logging.config
import os
import json
from pathlib import Path

# --- CORREÇÃO CRÍTICA ---
# PILAR DE QUALIDADE: Robustez
# DESCRIÇÃO: Define a raiz do projeto de forma programática e correta,
# garantindo que todos os caminhos para 'scenarios/', 'config/', etc.,
# sejam resolvidos corretamente a partir de qualquer local de execução.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

def setup_logging(config_path: Path = PROJECT_ROOT / "config" / "logging_config.json", default_level=logging.INFO):
    # PILAR DE QUALIDADE: Diagnósticabilidade
    # DESCRIÇÃO: Padroniza a configuração de logs para toda a aplicação,
    # assegurando que as mensagens sejam consistentes em formato e nível.
    if config_path.exists():
        with open(config_path, 'rt', encoding='utf-8') as f:
            config = json.load(f)
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.warning(f"Ficheiro 'logging_config.json' não encontrado. A usar configuração de log básica.")

def get_logger(name: str) -> logging.Logger:
    """Função de conveniência para obter um logger."""
    return logging.getLogger(name)

def task_start(message: str):
    """Imprime uma mensagem de início de tarefa."""
    print(f"[ ] {message}...")

def task_success(message: str):
    """Imprime uma mensagem de sucesso."""
    print(f"[✓] {message}")

def task_fail(message: str):
    """Imprime uma mensagem de falha."""
    print(f"[✗] {message}")

def ensure_sumo_home():
    # PILAR DE QUALIDADE: Robustez
    # DESCRIÇÃO: Valida a existência de dependências externas críticas antes
    # da execução, prevenindo falhas e fornecendo mensagens de erro claras.
    if 'SUMO_HOME' not in os.environ:
        logger = get_logger("SUMO_CHECK")
        error_msg = "A variável de ambiente SUMO_HOME não está definida."
        logger.critical(error_msg)
        raise EnvironmentError(error_msg)

def format_time(seconds: float) -> str:
    # PILAR DE QUALIDADE: Usabilidade
    # DESCRIÇÃO: Converte dados numéricos numa representação compreensível
    # por humanos, melhorando a clareza dos logs e relatórios.
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
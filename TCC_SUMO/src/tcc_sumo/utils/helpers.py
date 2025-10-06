import os
import sys
import logging
import logging.config
import json
from pathlib import Path
from typing import Dict, Any

"""
helpers.py
Este módulo fornece funções utilitárias para o projeto, incluindo:
- Definição do diretório raiz do projeto e diretório de logs.
- Funções para exibir feedback de tarefas no console em formato de checklist.
- Função para formatar tempo em segundos para o formato HHh MMm SSs.
- Função para obter o caminho absoluto da raiz do projeto.
- Função para garantir que a variável de ambiente SUMO_HOME esteja configurada.
- Função para configurar o sistema de logging a partir de um arquivo JSON, com fallback para configuração básica.
- Função para obter instâncias de logger configuradas.
Funções:
    task_start(message: str) -> None
        Exibe uma mensagem de tarefa em andamento no console.
    task_success(message: str) -> None
        Marca a tarefa como concluída, limpando a linha anterior.
    task_fail(message: str) -> None
        Marca a tarefa como falha, limpando a linha anterior.
    format_time(seconds: float) -> str
        Converte segundos para o formato HHh MMm SSs.
    get_project_root() -> Path
        Retorna o caminho absoluto para a raiz do projeto.
    ensure_sumo_home() -> None
    setup_logging() -> None
        Configura o sistema de logging a partir de um arquivo JSON, com fallback para configuração básica.
    get_logger(name: str) -> logging.Logger
        Obtém uma instância de logger configurada pelo nome.
"""

# Define a raiz do projeto para ser usada em outros módulos
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

# --- LÓGICA DO CHECKLIST PARA FEEDBACK NO CONSOLE ---
def task_start(message: str) -> None:
    """Exibe uma mensagem de tarefa em andamento no console."""
    print(f"[ ] {message}...", end='\r', flush=True)

def task_success(message: str) -> None:
    """Marca a tarefa como concluída, limpando a linha anterior."""
    print(' ' * 80, end='\r')
    print(f"[✓] {message}")

def task_fail(message: str) -> None:
    """Marca a tarefa como falha, limpando a linha anterior."""
    print(' ' * 80, end='\r')
    print(f"[✗] {message}")
# --- FIM DO CHECKLIST ---

def format_time(seconds: float) -> str:
    """Converte segundos para o formato HHh MMm SSs."""
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    return f"{hours:02d}h {minutes:02d}m {secs:02d}s"

def get_project_root() -> Path:
    """Retorna o caminho absoluto para a raiz do projeto."""
    return PROJECT_ROOT

def ensure_sumo_home() -> None:
    """
    Garante que a variável de ambiente SUMO_HOME esteja configurada.
    Se não estiver, define um valor padrão para sistemas Linux.
    """
    if 'SUMO_HOME' not in os.environ:
        os.environ['SUMO_HOME'] = "/usr/share/sumo"
        logging.info("Variável 'SUMO_HOME' não definida. Usando valor padrão: /usr/share/sumo")

def setup_logging() -> None:
    """
    Configura o sistema de logging a partir de um arquivo JSON.
    Se o arquivo não for encontrado, usa uma configuração básica.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    # CORREÇÃO DE ROBUSTEZ: Tenta encontrar o arquivo de configuração no diretório 'config' 
    # ou na raiz, garantindo que o caminho seja sempre absoluto.
    config_path = PROJECT_ROOT / "config" / "logging_config.json"
    if not config_path.is_file():
        # Fallback para o caso do arquivo estar na raiz do projeto (como no upload)
        config_path = PROJECT_ROOT / "logging_config.json"
    
    try:
        with open(config_path, 'rt', encoding='utf-8') as f:
            config = json.load(f)
        
        if 'file' in config.get('handlers', {}):
            # Resolve o caminho do arquivo de log de forma absoluta a partir da raiz do projeto
            # 'filename' deve ser um caminho relativo à raiz (e.g., 'logs/simulation.log')
            log_filename_relative = config['handlers']['file'].get('filename', 'logs/simulation.log')
            log_filename_absolute = PROJECT_ROOT / log_filename_relative
            config['handlers']['file']['filename'] = str(log_filename_absolute)
        
        logging.config.dictConfig(config)
    except Exception as e:
        # Fallback para o caso de erro ou arquivo não encontrado
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.warning(f"Falha ao carregar config de log: {e}. Usando config básica.")
    
def get_logger(name: str) -> logging.Logger:
    """Obtém uma instância de logger configurada pelo nome."""
    return logging.getLogger(name)
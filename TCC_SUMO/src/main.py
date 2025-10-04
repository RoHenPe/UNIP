# -*- coding: utf-8 -*-
"""Ponto de entrada principal para a execução da simulação de tráfego."""

import argparse
import json
import logging
import logging.config
import os
import sys
import yaml

# Adiciona o diretório 'src' ao path para importações corretas.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from tcc_sumo.simulation.manager import SimulationManager
from tcc_sumo.utils.helpers import task_start, task_success, task_fail

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def setup_logging(config_path: str = 'config/logging_config.json'):
    """Configura o sistema de logging a partir de um arquivo JSON."""
    path = os.path.join(PROJECT_ROOT, config_path)
    if os.path.exists(path):
        with open(path, 'rt', encoding='utf-8') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        # Fallback caso o arquivo de config não exista.
        logging.basicConfig(level=logging.DEBUG, filename='logs/fallback_simulation.log')

def main():
    """Função principal que orquestra a execução da simulação."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=str, required=True, choices=['osm', 'api'])
    parser.add_argument('--mode', type=str, required=True, choices=['STATIC', 'ADAPTIVE'])
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        task_start("Carregando configurações")
        with open('config/config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        task_success("Configurações carregadas")
        logger.info("Configurações carregadas com sucesso.")
    except Exception as e:
        task_fail("Falha ao carregar 'config.yaml'")
        logger.critical(f"Falha ao carregar config.yaml: {e}", exc_info=True)
        return

    manager = SimulationManager(config=config, scenario_name=args.scenario, mode_name=args.mode)
    manager.run()

if __name__ == "__main__":
    main()
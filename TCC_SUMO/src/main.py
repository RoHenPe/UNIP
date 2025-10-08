# -*- coding: utf-8 -*-
"""
Ponto de entrada único da aplicação.

PILAR DE QUALIDADE: Manutenibilidade
DESCRIÇÃO: Centraliza o início da execução, simplificando a depuração
e mantendo a lógica de negócio desacoplada.
"""

import argparse
import logging
import os
import sys
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from tcc_sumo.simulation.manager import SimulationManager
from tcc_sumo.utils.helpers import task_start, task_success, task_fail, setup_logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def load_configuration(config_path: str) -> dict:
    # PILAR DE QUALIDADE: Robustez
    # DESCRIÇÃO: Isola o carregamento de configuração, permitindo um
    # tratamento de erros focado e mensagens claras.
    task_start("Carregando configurações do projeto")
    if not os.path.exists(config_path):
        task_fail(f"Arquivo de configuração não encontrado em '{config_path}'")
        raise FileNotFoundError(f"O arquivo de configuração '{config_path}' não existe.")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        task_success("Configurações carregadas com sucesso")
        logging.getLogger(__name__).info("Configurações do arquivo 'config.yaml' carregadas.")
        return config
    except yaml.YAMLError as e:
        task_fail("Falha ao ler 'config.yaml' (formato inválido)")
        logging.getLogger(__name__).critical(f"Erro de formato no arquivo YAML: {e}", exc_info=True)
        raise

def main():
    # PILAR DE QUALIDADE: Usabilidade
    # DESCRIÇÃO: Argumentos de linha de comando claros e com ajuda integrada.
    parser = argparse.ArgumentParser(description="Executa uma simulação de tráfego com SUMO.")
    parser.add_argument('--scenario', type=str, required=True, choices=['osm', 'api'], help="Cenário a ser executado.")
    parser.add_argument('--mode', type=str, required=True, choices=['STATIC', 'ADAPTIVE'], help="Modo de controlo dos semáforos.")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        config_path = os.path.join(PROJECT_ROOT, 'config/config.yaml')
        config = load_configuration(config_path)
        manager = SimulationManager(config=config, scenario_name=args.scenario, mode_name=args.mode)
        manager.run()
    except FileNotFoundError:
        logger.critical("Execução interrompida: arquivo de configuração não encontrado.")
    except Exception as e:
        logger.critical(f"Um erro crítico e inesperado ocorreu: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
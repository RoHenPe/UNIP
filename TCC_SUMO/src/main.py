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
from tcc_sumo.utils.helpers import task_start, task_success, task_fail, setup_logging

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def main():
    """
    Função principal que orquestra a execução da simulação.
    Lê os argumentos da linha de comando, carrega as configurações
    e inicia o gerenciador de simulação.
    """
    parser = argparse.ArgumentParser(description="Executa uma simulação de tráfego com SUMO.")
    parser.add_argument('--scenario', type=str, required=True, choices=['osm', 'api'], help="Cenário a ser executado.")
    # CORREÇÃO DE ERRO: Incluindo os nomes antigos ('CONSERVATIVE', 'DYNAMIC') para aceitação de argumentos
    parser.add_argument('--mode', type=str, required=True, choices=['STATIC', 'ADAPTIVE', 'CONSERVATIVE', 'DYNAMIC'], help="Modo de controle dos semáforos.")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        task_start("Carregando configurações do projeto")
        # Assume que config.yaml está na raiz do projeto (PROJECT_ROOT) ou em config/
        config_path = os.path.join(PROJECT_ROOT, 'config/config.yaml')
        if not os.path.exists(config_path):
             config_path = os.path.join(PROJECT_ROOT, 'config.yaml')

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        task_success("Configurações carregadas com sucesso")
        logger.info("Configurações do arquivo 'config.yaml' carregadas.")
    except Exception as e:
        task_fail("Falha ao carregar 'config.yaml'")
        logger.critical(f"Não foi possível ler o arquivo de configuração: {e}", exc_info=True)
        return

    # CORREÇÃO DE ERRO: Mapeia os modos antigos para os novos antes de iniciar o Manager
    mode_map = {'CONSERVATIVE': 'STATIC', 'DYNAMIC': 'ADAPTIVE'}
    final_mode = mode_map.get(args.mode, args.mode)

    manager = SimulationManager(config=config, scenario_name=args.scenario, mode_name=final_mode)
    manager.run()

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""Módulo para o gerenciamento do ciclo de vida da simulação."""

import logging
import os
import sys

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("ERRO CRÍTICO: A variável de ambiente 'SUMO_HOME' não está definida.")

import traci
from traci.exceptions import TraCIException, FatalTraCIError

from tcc_sumo.simulation.traci_connection import TraciConnection
from tcc_sumo.tools.reporter import Reporter
from tcc_sumo.utils.helpers import task_start, task_success, task_fail

logger = logging.getLogger(__name__)


class SimulationManager:
    """Orquestra a simulação, gerenciando conexão, loop e relatórios."""

    def __init__(self, config: dict, scenario_name: str, mode_name: str):
        self.config = config
        self.scenario_name = scenario_name
        self.mode_name = mode_name
        self.reporter = Reporter()
        self.traci_connection = TraciConnection(
            config.get('sumo_executable', 'sumo-gui'),
            config['scenarios'][scenario_name],
            config.get('traci_port', 8813)
        )
        task_success(f"Sistema inicializado em modo '{self.mode_name}'")
        logger.info(f"Controlador do tipo '{self.mode_name}' foi inicializado.")

    def run(self):
        """Inicia a conexão e executa a simulação."""
        try:
            task_start("Conectando ao simulador SUMO")
            self.traci_connection.start()
            task_success("Conectado ao simulador SUMO")
            logger.info("Conexão com o SUMO estabelecida.")
            self._simulation_loop()
        except Exception as e:
            task_fail("Ocorreu um erro crítico inesperado")
            logger.critical("Erro não tratado no manager.run", exc_info=True)
        finally:
            task_start("Encerrando conexão")
            self.traci_connection.close()
            task_success("Conexão encerrada")
            logger.info("Conexão com o SUMO encerrada.")
            
            task_start("Gerando relatórios")
            self.reporter.generate_simulation_report(
                self.config, self.scenario_name, self.mode_name
            )
            task_success("Relatórios gerados")
            logger.info("Relatórios gerados com sucesso.")

    def _simulation_loop(self):
        """Contém o loop principal da simulação."""
        step = 0
        while True:
            try:
                traci.simulationStep()
                step += 1
                # A linha de log de cada passo foi removida para limpar o log
                self.reporter.collect_data_step()
            except (TraCIException, FatalTraCIError):
                task_success(f"Simulação interrompida pelo usuário no passo {step}")
                logger.warning(f"Simulação encerrada no passo {step} (conexão perdida).")
                break
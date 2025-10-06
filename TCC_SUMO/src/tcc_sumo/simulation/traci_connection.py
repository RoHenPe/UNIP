# -*- coding: utf-8 -*-
"""Módulo para abstrair e gerenciar a conexão com o simulador SUMO via TraCI."""

import logging
import subprocess
import time
import traci
import sys
import os

logger = logging.getLogger(__name__)

class TraciConnection:
    """Gerencia o ciclo de vida da conexão com o processo do SUMO."""

    def __init__(self, sumo_executable: str, config_file: str, port: int):
        self.sumo_executable = sumo_executable
        self.config_file = config_file
        self.port = port
        self.sumo_process = None
        self.is_connected = False

    def start(self):
        """Inicia o processo do SUMO e estabelece a conexão TraCI."""
        logger.info(f"Iniciando processo do SUMO com o arquivo: {self.config_file}")
        
        sumo_command = [
            self.sumo_executable,
            "-c", self.config_file,
            "--remote-port", str(self.port)
        ]
        
        log_file_handle = open("logs/simulation.log", "a")
        self.sumo_process = subprocess.Popen(
            sumo_command,
            stdout=subprocess.DEVNULL,
            stderr=log_file_handle
        )
        
        max_retries = 10
        for i in range(max_retries):
            try:
                # Bloco seguro para silenciar a saída do TraCI
                original_stdout = sys.stdout
                sys.stdout = open(os.devnull, 'w')
                try:
                    traci.init(self.port)
                finally:
                    # Garante que a saída do terminal seja sempre restaurada
                    if not sys.stdout.closed:
                        sys.stdout.close()
                    sys.stdout = original_stdout

                self.is_connected = True
                logger.info(f"Conexão TraCI estabelecida com sucesso na porta {self.port}.")
                return
            except traci.TraCIException:
                logger.debug(f"Aguardando o SUMO... (tentativa {i + 1}/{max_retries})")
                time.sleep(1)
            except KeyboardInterrupt:
                # Permite que a interrupção do usuário pare o processo de forma limpa
                logger.warning("Conexão com o SUMO interrompida pelo usuário.")
                self.close()
                raise
        
        raise Exception("Não foi possível estabelecer a conexão com o SUMO/TraCI.")

    def close(self):
        """Encerra a conexão TraCI e o processo do SUMO de forma segura."""
        if self.is_connected:
            try:
                traci.close()
                logger.info("Conexão TraCI encerrada.")
            except (traci.TraCIException, AttributeError):
                logger.warning("Não foi possível fechar a conexão TraCI. Pode já estar encerrada.")
        
        if self.sumo_process:
            self.sumo_process.terminate()
            logger.info("Processo do SUMO finalizado.")
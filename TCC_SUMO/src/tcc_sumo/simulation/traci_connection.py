# -*- coding: utf-8 -*-
"""
Módulo dedicado a gerir a conexão com a simulação SUMO via TraCI.
"""
import logging
import subprocess
import time
import sys
import traci
from traci.exceptions import TraCIException

from tcc_sumo.utils.helpers import get_logger

logger = get_logger("tcc_sumo.simulation.traci_connection")

class TraciConnection:
    """
    Encapsula a lógica para iniciar o SUMO como um subprocesso e conectar via TraCI.
    """
    def __init__(self, sumo_executable: str, config_file: str, port: int):
        self.sumo_executable = sumo_executable
        self.config_file = config_file
        self.port = port
        self.sumo_process = None

    def start(self) -> None:
        """
        Inicia o processo do SUMO e estabelece a conexão TraCI.
        """
        sumo_cmd = [
            self.sumo_executable,
            "-c", self.config_file,
            "--remote-port", str(self.port),
            "--start",
            "--quit-on-end",
            # --- CORREÇÃO DEFINITIVA ---
            # PILAR DE QUALIDADE: Realismo da Simulação
            # DESCRIÇÃO: O argumento '--time-to-teleport -1' instrui o SUMO a
            # desabilitar completamente o teletransporte de veículos. Agora,
            # se um veículo ficar preso, ele permanecerá preso, refletindo
            # um congestionamento real, o que é crucial para a análise.
            "--time-to-teleport", "-1"
        ]
        logger.info(f"Iniciando processo do SUMO: {' '.join(sumo_cmd)}")

        self.sumo_process = subprocess.Popen(sumo_cmd, stdout=sys.stdout, stderr=sys.stderr)

        # Lógica de retry para a conexão
        retries = 5
        for i in range(retries):
            try:
                traci.init(self.port)
                logger.info(f"Conexão TraCI estabelecida na porta {self.port}.")
                return
            except TraCIException as e:
                logger.warning(f"Não foi possível conectar ao servidor TraCI na porta {self.port}: {e}")
                logger.warning(f"Tentando novamente em {i+1} segundos...")
                time.sleep(i + 1)
        
        logger.critical("Falha ao estabelecer conexão TraCI após várias tentativas.")
        self.close()
        raise RuntimeError("Não foi possível conectar ao SUMO via TraCI.")

    def close(self) -> None:
        """
        Fecha a conexão TraCI e termina o processo do SUMO.
        """
        try:
            traci.close()
            logger.info("Conexão TraCI encerrada.")
        except TraCIException:
            logger.warning("Tentativa de fechar uma conexão TraCI já inexistente.")
        finally:
            if self.sumo_process:
                self.sumo_process.terminate()
                self.sumo_process.wait()
                logger.info("Processo do SUMO finalizado.")
                self.sumo_process = None
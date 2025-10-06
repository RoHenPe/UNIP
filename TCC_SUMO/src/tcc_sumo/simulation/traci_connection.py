import logging
import subprocess
import time
import traci
import sys
import os
from typing import Optional

logger = logging.getLogger(__name__)

class TraciConnection:
    """Gerencia o ciclo de vida da conexão com o processo do SUMO."""

    def __init__(self, sumo_executable: str, config_file: str, port: int):
        self.sumo_executable = sumo_executable
        self.config_file = config_file
        self.port = port
        self.sumo_process: Optional[subprocess.Popen] = None
        self.is_connected = False

    def start(self) -> None:
        """Inicia o processo do SUMO e estabelece a conexão TraCI com múltiplas tentativas."""
        logger.info(f"Iniciando processo do SUMO: {self.config_file}")
        
        sumo_command = [
            self.sumo_executable,
            "-c", self.config_file,
            "--remote-port", str(self.port),
            "--log", "logs/sumo_simulation.log", # Log dedicado do SUMO
            "--time-to-teleport", "-1" # CORREÇÃO: Desabilita o teletransporte (simulação real)
        ]
        
        os.makedirs("logs", exist_ok=True)
        
        self.sumo_process = subprocess.Popen(
            sumo_command,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        max_retries = 15
        for i in range(max_retries):
            try:
                traci.init(self.port)
                self.is_connected = True
                logger.info(f"Conexão TraCI estabelecida na porta {self.port}.")
                return
            except traci.TraCIException:
                logger.debug(f"Aguardando SUMO... (tentativa {i + 1}/{max_retries})")
                time.sleep(2)
        
        raise ConnectionError("Não foi possível conectar ao SUMO/TraCI.")

    def close(self) -> None:
        """Encerra a conexão TraCI e o processo do SUMO."""
        if self.is_connected:
            try:
                traci.close()
                logger.info("Conexão TraCI encerrada.")
                self.is_connected = False
            except (traci.TraCIException, AttributeError):
                logger.warning("Conexão TraCI já estava encerrada.")
        
        if self.sumo_process and self.sumo_process.poll() is None:
            try:
                self.sumo_process.terminate()
                self.sumo_process.wait(timeout=5)
                logger.info("Processo do SUMO finalizado.")
            except subprocess.TimeoutExpired:
                self.sumo_process.kill()
                logger.warning("Processo do SUMO forçado a fechar (kill).")
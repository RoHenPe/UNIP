import logging
import subprocess
import time
import traci
import sys
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class TraciConnection:
    """Gerencia o ciclo de vida da conexão com o processo do SUMO."""

    def __init__(self, sumo_executable: str, config_file: str, port: int):
        self.sumo_executable = sumo_executable
        self.config_file = config_file
        self.port = port
        self.sumo_process: Optional[subprocess.Popen] = None
        self.is_connected = False
        
        # [LÓGICA DE DETECÇÃO DO SUMO LOCAL (1.24.0)]
        self._resolve_sumo_executable()

    def _resolve_sumo_executable(self):
        # Resolve o caminho absoluto para a raiz do projeto (sobe 4 níveis a partir deste arquivo)
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        
        # Define o caminho que *deve* conter o binário 1.24.0
        local_sumo_path = project_root / "sumo-1.24.0" / "bin" / self.sumo_executable
        
        if local_sumo_path.exists():
            # 1. Sucesso: Usa a versão 1.24.0 local.
            self.sumo_executable = str(local_sumo_path)
            logger.info(f"Usando SUMO Local (1.24.0): {self.sumo_executable}")
        elif os.path.exists(self.sumo_executable):
            # 2. Fallback: Se o nome for um caminho absoluto existente (como '/usr/bin/sumo-gui')
            #    ou um executável que pode ser resolvido pelo PATH (versão 1.18.0), use-o.
            logger.warning(f"SUMO Local (1.24.0) não encontrado em {local_sumo_path}. Usando o executável '{self.sumo_executable}' do PATH (provavelmente 1.18).")
        else:
            # 3. Falha: A versão 1.24.0 local não existe E o executável não está no PATH.
            #    Mantemos o nome para que o subprocesso tente usar o PATH e falhe com um erro claro.
            logger.critical(f"Erro: O executável '{self.sumo_executable}' não foi encontrado em '{local_sumo_path}' nem no PATH do sistema. A simulação irá falhar.")
            

    def start(self) -> None:
        """Inicia o processo do SUMO e estabelece a conexão TraCI com múltiplas tentativas."""
        logger.info(f"Iniciando processo do SUMO: {self.config_file}")
        
        sumo_command = [
            self.sumo_executable,
            "-c", self.config_file,
            "--remote-port", str(self.port),
            "--log", "logs/sumo_simulation.log", # Log dedicado do SUMO
            "--time-to-teleport", "-1" # Desabilita o teletransporte (simulação real)
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
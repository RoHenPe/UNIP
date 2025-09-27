import traci
import os
import sys
import time
from pathlib import Path
import datetime
from tcc_sumo.utils.helpers import get_logger, PROJECT_ROOT
from tcc_sumo.traffic_logic.controllers import TrafficController

logger = get_logger(__name__)

def print_status(message, status="OK", width=50):
    """Imprime uma mensagem de status formatada."""
    message = (message[:width-10] + '...') if len(message) > width-10 else message
    dots = "." * (width - len(message) - len(status))
    print(f"  {message} {dots} [{status}]", end='\r', flush=True)

class SimulationManager:
    """Orquestra a simulação."""
    
    def __init__(self, config: dict, simulation_mode: str, max_steps: int, scenario_key: str):
        self.config = config
        self.mode = simulation_mode
        self.max_steps = max_steps
        self.scenario_key = scenario_key
        self.sumo_log_file = PROJECT_ROOT / "logs" / "sumo_output.log"
        self.is_connected = False
        self.simulation_failed = False
        logger.info(f"SimulationManager iniciado para o cenário: '{scenario_key}'")

    def _connect(self) -> bool:
        """Inicia o SUMO e conecta o TraCI."""
        print("\n  Iniciando pré-configuração da simulação...")
        
        if self.scenario_key not in self.config.get('scenarios', {}):
            print_status("Verificando config", "NOK"); print()
            logger.error(f"Chave de cenário '{self.scenario_key}' não encontrada em config.yaml.")
            return False
        print_status("Verificando config", "OK"); print()
        
        scenario_path = PROJECT_ROOT / self.config['scenarios'][self.scenario_key]
        if not scenario_path.is_file():
            print_status(f"Verificando arquivo '{scenario_path.name}'", "NOK"); print()
            logger.error(f"Arquivo de cenário não encontrado em: {scenario_path}")
            return False
        print_status(f"Verificando arquivo '{scenario_path.name}'", "OK"); print()

        self.original_cwd = os.getcwd()
        os.chdir(scenario_path.parent)
        
        sumo_cmd = [
            self.config.get('sumo_executable', 'sumo-gui'), "-c", scenario_path.name,
            "--log", str(self.sumo_log_file), "--tripinfo-output", "tripinfo.xml"
        ]
        
        if self.scenario_key == 'api':
            now = datetime.datetime.now()
            seconds = now.hour * 3600 + now.minute * 60 + now.second
            sumo_cmd.extend(["--begin", str(seconds)])
        
        print_status("Conectando ao simulador", "PENDENTE")
        try:
            with open(os.devnull, 'w') as devnull:
                original_stdout, sys.stdout = sys.stdout, devnull
                traci.start(sumo_cmd, port=self.config.get('traci_port', 8813))
            sys.stdout = original_stdout
            self.is_connected = True
            print_status("Conectando ao simulador", "OK"); print()
            return True
        except Exception:
            print_status("Conectando ao simulador", "NOK"); print()
            print("\n  !! ERRO: Falha ao iniciar SUMO. Consulte 'logs/sumo_output.log'.")
            return False

    def _close(self):
        """Encerra a conexão TraCI."""
        if self.is_connected:
            try: traci.close()
            except Exception: pass
        if hasattr(self, 'original_cwd'):
            os.chdir(self.original_cwd)
        self.is_connected = False

    def run(self):
        """Executa o ciclo de vida completo da simulação."""
        try:
            if not self._connect():
                self.simulation_failed = True; return

            self.controller = None
            if 'traffic_lights' in self.config and self.config['traffic_lights']:
                sim_tls_ids = set(traci.trafficlight.getIDList())
                tls_config_to_run = [
                    tls for tls in self.config['traffic_lights'] 
                    if str(tls.get('id')) in sim_tls_ids
                ]
                
                if tls_config_to_run:
                    self.controller = TrafficController(tls_config_to_run, self.mode)
                    print_status(f"Simulação em modo '{self.mode}'", "EM ANDAMENTO")
                else:
                    logger.warning("Nenhum semáforo da config foi encontrado na malha. Rodando em modo de observação.")
                    print_status("Simulação em modo de observação", "EM ANDAMENTO")
            else:
                print_status("Simulação em modo de observação", "EM ANDAMENTO")

            step = 0
            while step < self.max_steps and traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()
                if self.controller: self.controller.update_logic(step)
                step += 1
            
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            if self.is_connected: print_status("Simulação", "OK")
            
        except traci.TraCIException as e:
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            status = "FECHADA PELO USUÁRIO" if "connection closed by SUMO" in str(e) else "INTERROMPIDA"
            print_status("Simulação", status)
            if status == "INTERROMPIDA": self.simulation_failed = True
        except Exception as e:
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            print_status("Simulação", "NOK")
            logger.critical(f"Erro inesperado no loop: {e}", exc_info=True)
            self.simulation_failed = True

    def cleanup(self):
        """Garante o encerramento seguro."""
        self._close()
        print_status("Finalizando ambiente", "OK")
        
        if self.simulation_failed:
             print("\n\n  >> A simulação não foi concluída. Verifique os logs.")
        else:
             print("\n\n  >> Simulação finalizada com sucesso.")
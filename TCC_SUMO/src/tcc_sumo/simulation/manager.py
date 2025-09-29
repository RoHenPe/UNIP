#arquivo: TCC_SUMO/src/tcc_sumo/simulation/manager.py
"""Gerencia a simulação SUMO via TraCI."""

import traci
import os
import sys
import time
from pathlib import Path
import datetime
import json
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
        # Convertendo o modo (DYNAMIC/CONSERVATIVE) para minúsculas para nomear o arquivo
        self.mode = simulation_mode.upper()
        self.max_steps = max_steps
        self.scenario_key = scenario_key
        
        # Obtém o diretório de logs e prepara o nome do arquivo JSON
        output_log_dir = self.config.get('output_paths', {}).get('logs', 'logs')
        mode_lower = self.mode.lower()
        
        # 1. SUMO Log File (Separado por cenário E modo, como solicitado)
        self.sumo_log_file = PROJECT_ROOT / output_log_dir / f"sumo_output_{self.scenario_key}_{mode_lower}.log"
        
        # 2. Arquivo de Relatório JSON Estruturado para BI (Um arquivo por combinação)
        self.json_report_file = PROJECT_ROOT / output_log_dir / f"report_{self.scenario_key}_{mode_lower}.json"
        
        # Inicializa o dicionário de métricas
        self.metrics = {
            "scenario": self.scenario_key,
            "mode": self.mode,
            "max_steps": self.max_steps,
            "duration_s": 0.0,
            "total_vehicles_loaded": 0,
            "avg_speed_final_mps": 0.0,
            "teleports_total": 0,
            "simulation_status": "NOT_STARTED",
            "log_file": str(self.sumo_log_file)
        }
        self.is_connected = False
        self.simulation_failed = False
        logger.info(f"SimulationManager iniciado para o cenário: '{scenario_key}' no modo: '{self.mode}'")

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
        
        # Comando SUMO: Apenas o --log é injetado, o resto vem do .sumocfg original (conforme solicitado).
        sumo_cmd = [
            self.config.get('sumo_executable', 'sumo-gui'), "-c", scenario_path.name,
            "--log", str(self.sumo_log_file) 
        ]
        
        # Lógica para modo 'api' (adiciona o argumento --begin para simulação dinâmica)
        if self.scenario_key == 'api':
            now = datetime.datetime.now()
            # Inicia a simulação no SUMO em um tempo específico (hora atual em segundos) para TraCI
            seconds = now.hour * 3600 + now.minute * 60 + now.second
            sumo_cmd.extend(["--begin", str(seconds)])
        
        print_status("Conectando ao simulador", "PENDENTE")
        try:
            # Redireciona a saída padrão (stdout) para silenciar o SUMO
            with open(os.devnull, 'w') as devnull:
                original_stdout, sys.stdout = sys.stdout, devnull
                traci.start(sumo_cmd, port=self.config.get('traci_port', 8813))
            sys.stdout = original_stdout # Restaura a saída padrão
            self.is_connected = True
            print_status("Conectando ao simulador", "OK"); print()
            self.metrics["simulation_status"] = "RUNNING"
            return True
        except Exception:
            sys.stdout = original_stdout # Garante que a saída seja restaurada mesmo em erro
            print_status("Conectando ao simulador", "NOK"); print()
            print(f"\n  !! ERRO: Falha ao iniciar SUMO. Consulte '{self.sumo_log_file}'.")
            self.metrics["simulation_status"] = "CONNECTION_ERROR"
            return False

    def _collect_metrics(self):
        """Coleta métricas finais usando TraCI."""
        try:
            self.metrics["total_vehicles_loaded"] = traci.simulation.getLoadedNumber()
            self.metrics["teleports_total"] = traci.simulation.getStartingTeleportNumber()

            # Tenta obter a velocidade média da rede (funciona se houver veículos)
            if self.metrics["total_vehicles_loaded"] > 0 and len(traci.edge.getIDList()) > 0:
                total_speed = 0.0
                edge_count = 0
                for edge_id in traci.edge.getIDList():
                    speed = traci.edge.getLastStepMeanSpeed(edge_id)
                    # Exclui valores de 0.0 que podem indicar trechos sem veículos
                    if speed > 0.0:
                        total_speed += speed
                        edge_count += 1
                
                if edge_count > 0:
                    self.metrics["avg_speed_final_mps"] = round(total_speed / edge_count, 3)

        except traci.TraCIException as e:
            logger.warning(f"Falha ao coletar métricas TraCI: {e}")
            # Mantém o status original, mas registra o erro de métricas
            self.metrics["simulation_status"] = "METRIC_ERROR" if self.metrics["simulation_status"] == "COMPLETED" else self.metrics["simulation_status"]
        except Exception as e:
             logger.warning(f"Erro inesperado na coleta de métricas: {e}")
             self.metrics["simulation_status"] = "UNEXPECTED_ERROR_METRICS"


    def run(self):
        """Executa o ciclo de vida completo da simulação."""
        start_time = time.time()
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
            
            self.metrics["simulation_status"] = "COMPLETED"
            
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            if self.is_connected: print_status("Simulação", "OK")
            
        except traci.TraCIException as e:
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            status = "FECHADA PELO USUÁRIO" if "connection closed by SUMO" in str(e) else "INTERROMPIDA"
            print_status("Simulação", status)
            if status == "INTERROMPIDA": self.simulation_failed = True
            self.metrics["simulation_status"] = "INTERRUPTED"
        except Exception as e:
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            print_status("Simulação", "NOK")
            logger.critical(f"Erro inesperado no loop: {e}", exc_info=True)
            self.simulation_failed = True
            self.metrics["simulation_status"] = "UNEXPECTED_ERROR"
            
        finally:
            end_time = time.time()
            # Arredonda e calcula a duração total
            self.metrics["duration_s"] = round(end_time - start_time, 2)
            if self.is_connected:
                self._collect_metrics()


    def cleanup(self):
        """Garante o encerramento seguro e gera o relatório JSON."""
        self._close()
        
        # Garante que o diretório de logs exista antes de tentar escrever
        self.json_report_file.parent.mkdir(parents=True, exist_ok=True)

        # Geração do Arquivo JSON para BI
        try:
            with open(self.json_report_file, 'w') as f:
                json.dump(self.metrics, f, indent=4)
            print_status(f"Relatório '{self.json_report_file.name}'", "JSON OK")
        except Exception as e:
            logger.error(f"Falha ao gerar o relatório JSON: {e}")
            print_status("Relatório JSON", "NOK")
            
        print_status("Finalizando ambiente", "OK")
        
        if self.simulation_failed:
             print("\n\n  >> A simulação não foi concluída. Verifique os logs.")
        else:
             print(f"\n\n  >> Simulação finalizada com sucesso. Relatório JSON gerado em '{self.json_report_file}'.")
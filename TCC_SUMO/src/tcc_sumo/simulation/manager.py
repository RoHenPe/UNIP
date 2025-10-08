import logging
import os
import sys
from pathlib import Path
import traci
from traci.exceptions import TraCIException, FatalTraCIError
import pandas as pd

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
else:
    # A correção no traci_connection.py já garante o uso da versão local,
    # mas esta verificação de ambiente é mantida para o módulo tools do SUMO.
    pass

from tcc_sumo.simulation.traci_connection import TraciConnection
from tcc_sumo.tools.log_analyzer import LogAnalyzer
from tcc_sumo.utils.helpers import task_start, task_success, task_fail, PROJECT_ROOT, format_time
from tcc_sumo.traffic_logic.controllers import StaticController, AdaptiveController

logger = logging.getLogger(__name__)

class SimulationManager:
    def __init__(self, config: dict, scenario_name: str, mode_name: str):
        self.config, self.scenario_name, self.mode_name = config, scenario_name, mode_name.upper()
        self.step = 0
        logger.debug(f"Iniciando SimulationManager com cenário='{scenario_name}' e modo='{mode_name}'.")
        self.traci_connection = TraciConnection(
            config.get('sumo_executable', 'sumo-gui'),
            config['scenarios'][scenario_name],
            config.get('traci_port', 8813)
        )
        self.controller = AdaptiveController() if self.mode_name == 'ADAPTIVE' else StaticController()
        task_success(f"Sistema inicializado em modo '{self.mode_name}'")

    def run(self):
        try:
            task_start("Conectando ao SUMO")
            self.traci_connection.start()
            task_success("Conectado ao SUMO")
            self._simulation_loop()
        except KeyboardInterrupt:
            task_fail("Simulação interrompida pelo teclado")
            logger.warning("Simulação interrompida pelo usuário via CTRL+C.")
        except (FatalTraCIError, TraCIException) as e:
            # CORREÇÃO: Eleva o nível para WARNING, pois é um encerramento não planeado (como fechar a GUI).
            task_success("Simulação encerrada pelo usuário (janela fechada)")
            logger.warning(f"A simulação foi encerrada via TraCI: {e}")
        except Exception as e:
            task_fail("Erro crítico inesperado")
            logger.critical("Erro não tratado no manager.run", exc_info=True)
        finally:
            self._cleanup()
            
    def _simulation_loop(self):
        task_start(f"Simulação iniciada em modo '{self.mode_name}'...")
        logger.info(f"Loop de simulação iniciado. Modo: {self.mode_name}.")
        while True:
            traci.simulationStep()
            logger.debug(f"Passo {self.step}: Executando simulationStep.")
            self.controller.manage_traffic_lights(self.step)
            if self.step % 100 == 0: self._log_progress()
            self.step += 1

    def _log_progress(self):
        try:
            active = traci.vehicle.getIDCount(); arrived = traci.simulation.getArrivedNumber()
            logger.info(f"Progresso - Passo: {self.step} ({format_time(self.step)}) | Ativos: {active} | Chegaram: {arrived}")
        except traci.TraCIException as e:
            logger.warning(f"Não foi possível obter dados de progresso no passo {self.step}: {e}")

    def _cleanup(self):
        task_start("Encerrando conexão"); self.traci_connection.close(); task_success("Conexão encerrada")
        if self.step > 0:
            task_start("Analisando resultados"); self._analyze_and_report()
        else:
            logger.warning("Nenhum passo de simulação executado. Análise ignorada.")

    def _analyze_and_report(self):
        try:
            logger.info("Iniciando fase de análise e geração de relatórios.")
            output_dir = Path(self.config['scenarios'][self.scenario_name]).parent
            analyzer = LogAnalyzer(
                trip_info_path=str(output_dir / "tripinfo.xml"),
                emission_path=str(output_dir / "emissions.xml"),
                queue_info_path=str(output_dir / "queueinfo.xml")
            )
            data = analyzer.run_analysis({"scenario": self.scenario_name, "mode": self.mode_name}, self.step)
            self.generate_reports(data); self._display_summary_labels(data)
            task_success("Análise e relatórios concluídos")
        except Exception as e:
            task_fail("Falha na análise dos resultados")
            logger.critical(f"Erro na fase de análise: {e}", exc_info=True)

    def generate_reports(self, data: dict):
        json_path = PROJECT_ROOT / "logs" / "consolidated_data.json"
        if json_path.exists():
            logger.info(f"Dados estruturados para base de dados disponíveis em '{json_path}'.")
        else:
            logger.error("Ficheiro JSON consolidado não foi gerado.")
            
        report_ticket_path = PROJECT_ROOT / "logs" / "human_analysis_report.log"
        metrics, pollution, queue = data.get("metrics",{}), data.get("pollution",{}), data.get("queue_metrics",{})
        total, completed, removed = metrics.get('Veículos Processados (Entraram na Malha)',0), metrics.get('Veículos que Concluíram a Viagem',0), metrics.get('Veículos Removidos (Não Concluídos)', 0) # Usa o novo campo
        rate = (completed / total * 100) if total > 0 else 0

        summary_text = "Análise concluída com sucesso."
        if removed > total * 0.05 and total > 0:
            summary_text = "A simulação indicou ALTOS NÍVEIS DE CONGESTIONAMENTO, com um número significativo de veículos removidos (não concluídos)."
        elif removed > 0:
            summary_text = "A simulação indicou FOCOS DE CONGESTIONAMENTO MODERADO, resultando em alguns veículos removidos (não concluídos)."
        else:
            summary_text = "A simulação demonstrou um FLUXO DE TRÁFEGO ESTÁVEL, com congestionamentos mínimos ou inexistentes."

        # TEMPLATE DE RELATÓRIO HUMANIZADO (TICKET)
        ticket_template = f"""
#########################################################################
#                                                                       #
#          RELATÓRIO RESUMIDO DE ANÁLISE DE TRÁFEGO (SUMO)              #
#                                                                       #
#########################################################################

ID DO RELATÓRIO: SIM-{pd.Timestamp(data.get('analysis_timestamp')).strftime('%Y%m%d-%H%M%S')}
DATA DA ANÁLISE: {pd.Timestamp(data.get('analysis_timestamp')).strftime('%d/%m/%Y %H:%M:%S')}

CENÁRIO: {data.get('scenario', 'N/A').upper()}
MODO DE CONTROLE: {data.get('mode', 'N/A').upper()}
DURAÇÃO TOTAL: {format_time(metrics.get('simulation_duration_seconds', 0))}

-------------------------------------------------------------------------
                           SUMÁRIO EXECUTIVO
-------------------------------------------------------------------------

{summary_text}

-------------------------------------------------------------------------
                      INDICADORES CHAVE DE PERFORMANCE (KPIs)
-------------------------------------------------------------------------

  - FLUXO EFICIENTE (Viagens Concluídas).: {completed} de {total} ({rate:.2f}%)
  - NÍVEL DE CONGESTIONAMENTO (Removidos): {removed} Veículos Removidos
  - VELOCIDADE MÉDIA GERAL.............: {metrics.get('Velocidade Média Geral (km/h)', 0):.2f} km/h

-------------------------------------------------------------------------
                       DETALHES DA EFICIÊNCIA DE VIAGEM
-------------------------------------------------------------------------

  [+] TEMPO MÉDIO TOTAL POR VIAGEM: {format_time(metrics.get('Tempo Médio de Viagem (s)', 0))}
      - Tempo Perdido em Congestionamento.: {format_time(metrics.get('Tempo Médio Perdido (s)', 0))} ({metrics.get('Percentual de Tempo Perdido', 0):.2f}%)
      - Tempo de Espera em Semáforos......: {format_time(metrics.get('Tempo Médio de Espera (s)', 0))} ({metrics.get('Percentual de Tempo de Espera', 0):.2f}%)

  [+] PONTOS CRÍTICOS:
      - Tamanho Médio da Fila............: {queue.get('Tamanho Médio da Fila (veículos)', 0):.2f} veículos
      - Pico de Espera numa Fila.........: {format_time(queue.get('Tempo Máximo de Espera (s)', 0))}

-------------------------------------------------------------------------
                          IMPACTO AMBIENTAL
-------------------------------------------------------------------------

  - Consumo Total de Combustível..: {pollution.get('Total de fuel', '0.00 L')}
  - Emissão Total de CO2..........: {pollution.get('Total de CO2', '0.00 kg')}
  - Emissão Total de NOx..........: {pollution.get('Total de NOx', '0.00 kg')}

#########################################################################
#                         FIM DO RELATÓRIO                              #
#########################################################################
"""
        with open(report_ticket_path, 'a', encoding='utf-8') as f: f.write(ticket_template)
        logger.info(f"Relatório de análise humana (ticket) salvo em '{report_ticket_path}'.")

    def _display_summary_labels(self, data: dict):
        metrics = data.get("metrics", {})
        total, completed, removed = metrics.get('Veículos Processados (Entraram na Malha)',0), metrics.get('Veículos que Concluíram a Viagem',0), metrics.get('Veículos Removidos (Não Concluídos)', 0) # Usa o novo campo
        rate = (completed / total * 100) if total > 0 else 0
        RED, ENDC = '\033[91m', '\033[0m'
        removed_str = f"{RED}{removed}{ENDC}"
        summary = f"""
+-----------------------------------------------------+
|              RESUMO DA SIMULAÇÃO                    |
+-----------------------------------------------------+
| Cenário: {data.get('scenario', 'N/A'):<15} | Modo: {data.get('mode', 'N/A'):<16} |
| Duração: {format_time(metrics.get('simulation_duration_seconds', 0)):<15} |
+-----------------------------------------------------+
| Veículos na Malha: {total:<26} |
| Viagens Concluídas: {completed:<24} |
| Taxa de Conclusão: {rate:<7.2f}%{'' :<25} |
| Veículos Removidos: {removed_str:<35} |
| Velocidade Média: {metrics.get('Velocidade Média Geral (km/h)', 0):<7.2f} km/h{'' :<20} |
| Tempo Médio Viagem: {format_time(metrics.get('Tempo Médio de Viagem (s)', 0)):<22} |
+-----------------------------------------------------+
"""
        print(summary)
# -*- coding: utf-8 -*-
"""
Módulo responsável por gerenciar todo o ciclo de vida da simulação.

PILAR DE QUALIDADE: Coesão e Baixo Acoplamento
DESCRIÇÃO: A classe SimulationManager orquestra a simulação, mas delega
responsabilidades específicas (conexão TraCI, lógica de tráfego) para
outras classes. Isso mantém o código organizado e fácil de manter.
"""
import logging
import os
import sys
from pathlib import Path
import traci
from traci.exceptions import TraCIException, FatalTraCIError
import pandas as pd

from tcc_sumo.simulation.traci_connection import TraciConnection
from tcc_sumo.tools.log_analyzer import LogAnalyzer
from tcc_sumo.traffic_logic.controllers import StaticController, AdaptiveController, BaseController
from tcc_sumo.utils.helpers import task_start, task_success, task_fail, PROJECT_ROOT, format_time

logger = logging.getLogger(__name__)

class SimulationManager:
    """
    Orquestra a inicialização, execução e finalização da simulação SUMO.
    """
    def __init__(self, config: dict, scenario_name: str, mode_name: str):
        self.config = config
        self.scenario_name = scenario_name
        self.mode_name = mode_name.upper()
        self.step = 0
        self.controller: BaseController

        self.traci_connection = TraciConnection(
            config.get('sumo_executable', 'sumo-gui'),
            config['scenarios'][scenario_name],
            config.get('traci_port', 8813)
        )
        self._setup_controller()
        task_success(f"Sistema inicializado em modo '{self.mode_name}'")

    def _setup_controller(self):
        """Inicializa o controlador de tráfego correto com base no modo."""
        if self.mode_name == 'ADAPTIVE':
            self.controller = AdaptiveController()
        else:
            self.controller = StaticController()
        logger.info(f"Controlador '{self.controller.__class__.__name__}' selecionado.")

    def run(self):
        """Ponto principal de execução do ciclo de vida da simulação."""
        try:
            task_start("Conectando ao SUMO")
            self.traci_connection.start()
            task_success("Conectado ao SUMO")
            self.controller.setup()
            self._simulation_loop()
        except KeyboardInterrupt:
            task_fail("Simulação interrompida pelo teclado")
            logger.warning("Simulação interrompida pelo usuário via CTRL+C.")
        except (FatalTraCIError, TraCIException) as e:
            task_success("Simulação encerrada pelo usuário (janela fechada)")
            logger.warning(f"A simulação foi encerrada via TraCI: {e}")
        except Exception:
            task_fail("Erro crítico inesperado durante a simulação")
            logger.critical("Erro não tratado no manager.run", exc_info=True)
        finally:
            self._cleanup()

    def _simulation_loop(self):
        """Executa o loop principal da simulação, avançando os passos."""
        task_start(f"Simulação iniciada em modo '{self.mode_name}'...")
        logger.info(f"Loop de simulação iniciado. Modo: {self.mode_name}.")
        # Melhoria: O loop agora verifica se ainda há veículos na simulação.
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            self.controller.manage_traffic_lights(self.step)
            if self.step % 100 == 0:
                self._log_progress()
            self.step += 1
        logger.info("Todos os veículos concluíram suas rotas ou foram removidos. Encerrando simulação.")

    def _log_progress(self):
        """Registra o progresso da simulação no log."""
        try:
            active = traci.vehicle.getIDCount()
            arrived = traci.simulation.getArrivedNumber()
            logger.info(f"Progresso - Passo: {self.step} ({format_time(self.step)}) | Ativos: {active} | Chegaram: {arrived}")
        except traci.TraCIException as e:
            logger.warning(f"Não foi possível obter dados de progresso no passo {self.step}: {e}")

    def _cleanup(self):
        """Encerra a conexão e dispara a análise de resultados."""
        task_start("Encerrando conexão")
        self.traci_connection.close()
        task_success("Conexão encerrada")
        if self.step > 0:
            task_start("Analisando resultados")
            self._analyze_and_report()
        else:
            logger.warning("Nenhum passo de simulação executado. Análise ignorada.")

    def _analyze_and_report(self):
        """
        FUNCIONALIDADE RESTAURADA:
        Coordena a análise dos arquivos de saída e a geração de relatórios.
        """
        try:
            logger.info("Iniciando fase de análise e geração de relatórios.")
            output_dir = Path(self.config['scenarios'][self.scenario_name]).parent
            analyzer = LogAnalyzer(
                trip_info_path=str(output_dir / "tripinfo.xml"),
                emission_path=str(output_dir / "emissions.xml"),
                queue_info_path=str(output_dir / "queueinfo.xml")
            )
            data = analyzer.run_analysis({"scenario": self.scenario_name, "mode": self.mode_name}, self.step)
            self.generate_reports(data)
            self._display_summary_labels(data)
            task_success("Análise e relatórios concluídos")
        except Exception as e:
            task_fail("Falha na análise dos resultados")
            logger.critical(f"Erro na fase de análise: {e}", exc_info=True)

    def generate_reports(self, data: dict):
        """
        FUNCIONALIDADE RESTAURADA:
        Gera o relatório de análise em formato de "ticket".
        """
        report_ticket_path = PROJECT_ROOT / "logs" / "human_analysis_report.log"
        metrics, pollution, queue = data.get("metrics",{}), data.get("pollution",{}), data.get("queue_metrics",{})
        total = metrics.get('Veículos Processados (Entraram na Malha)',0)
        completed = metrics.get('Veículos que Concluíram a Viagem',0)
        removed = metrics.get('Veículos Removidos (Não Concluídos)', 0)
        rate = (completed / total * 100) if total > 0 else 0

        summary_text = "Análise concluída com sucesso."
        if removed > total * 0.05 and total > 0:
            summary_text = "A simulação indicou ALTOS NÍVEIS DE CONGESTIONAMENTO, com um número significativo de veículos removidos (não concluídos)."
        elif removed > 0:
            summary_text = "A simulação indicou FOCOS DE CONGESTIONAMENTO MODERADO, resultando em alguns veículos removidos (não concluídos)."
        else:
            summary_text = "A simulação demonstrou um FLUXO DE TRÁFEGO ESTÁVEL, com congestionamentos mínimos ou inexistentes."

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
        """
        FUNCIONALIDADE RESTAURADA:
        Exibe a tabela de resumo da simulação no console.
        """
        metrics = data.get("metrics", {})
        total = metrics.get('Veículos Processados (Entraram na Malha)',0)
        completed = metrics.get('Veículos que Concluíram a Viagem',0)
        removed = metrics.get('Veículos Removidos (Não Concluídos)', 0)
        rate = (completed / total * 100) if total > 0 else 0
        removed_str = str(removed)
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
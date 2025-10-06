# -*- coding: utf-8 -*-
"""Módulo para o gerenciamento do ciclo de vida da simulação."""

import logging
import os
import sys
from pathlib import Path
from datetime import timedelta

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("ERRO CRÍTICO: A variável de ambiente 'SUMO_HOME' não está definida.")

import traci
from traci.exceptions import TraCIException, FatalTraCIError

from tcc_sumo.simulation.traci_connection import TraciConnection
from tcc_sumo.tools.log_analyzer import LogAnalyzer
from tcc_sumo.utils.helpers import task_start, task_success, task_fail, PROJECT_ROOT, format_seconds_to_ms

logger = logging.getLogger(__name__)

class SimulationManager:
    """Orquestra a simulação, gerenciando conexão, loop e relatórios."""

    def __init__(self, config: dict, scenario_name: str, mode_name: str):
        self.config = config
        self.scenario_name = scenario_name
        self.mode_name = mode_name
        self.traci_connection = TraciConnection(
            config.get('sumo_executable', 'sumo-gui'),
            config['scenarios'][scenario_name],
            config.get('traci_port', 8813)
        )
        task_success(f"Sistema inicializado em modo '{self.mode_name}'")
        logger.info(f"Controlador do tipo '{self.mode_name}' foi inicializado.")

    def run(self):
        """Inicia a conexão e executa a simulação."""
        simulation_step_count = 0
        try:
            task_start("Conectando ao simulador SUMO")
            self.traci_connection.start()
            task_success("Conectado ao simulador SUMO")
            logger.info("Conexão com o SUMO estabelecida.")
            simulation_step_count = self._simulation_loop()
        except KeyboardInterrupt:
            # Captura a interrupção do usuário para uma saída limpa
            task_fail("Simulação interrompida pelo usuário")
            logger.warning("Execução interrompida pelo usuário via teclado.")
        except Exception as e:
            task_fail("Ocorreu um erro crítico inesperado")
            logger.critical("Erro não tratado no manager.run", exc_info=True)
        finally:
            task_start("Encerrando conexão")
            self.traci_connection.close()
            task_success("Conexão encerrada")
            logger.info("Conexão com o SUMO encerrada.")
            
            # Só analisa se a simulação rodou por pelo menos um passo
            if simulation_step_count > 0:
                task_start("Analisando resultados e gerando relatórios")
                self._analyze_and_report(simulation_step_count)

    def _analyze_and_report(self, step_count):
        """Chama o LogAnalyzer para processar os arquivos de saída do SUMO."""
        try:
            scenario_config_path = Path(self.config['scenarios'][self.scenario_name])
            output_dir = scenario_config_path.parent

            trip_info_path = output_dir / "tripinfo.xml"
            emission_path = output_dir / "emissions.xml"
            queue_info_path = output_dir / "queueinfo.xml"

            analyzer = LogAnalyzer(
                trip_info_path=str(trip_info_path),
                emission_path=str(emission_path),
                queue_info_path=str(queue_info_path)
            )
            
            simulation_metadata = {"scenario": self.scenario_name, "mode": self.mode_name}
            consolidated_data = analyzer.run_analysis(simulation_metadata, simulation_duration_seconds=step_count)
            
            self._generate_text_report(consolidated_data)
            task_success("Análise concluída e relatórios gerados")
            logger.info("Relatórios gerados com sucesso.")

        except FileNotFoundError as e:
            task_fail(f"Arquivos de output do SUMO não encontrados: {e}")
            logger.error("Certifique-se de que o cenário está configurado para gerar os outputs necessários.")
        except Exception as e:
            task_fail("Falha ao analisar resultados")
            logger.critical(f"Falha ao gerar relatórios: {e}", exc_info=True)

    def _generate_text_report(self, data: dict):
        """Gera o relatório de texto a partir dos dados consolidados."""
        report_path = PROJECT_ROOT / self.config['output_paths']['logs'] / "simulation_report.log"
        metrics = data.get("metrics", {})
        pollution = data.get("pollution", {})
        queue_metrics = data.get("queue_metrics", {})

        total_vehicles = metrics.get('Veículos Processados (Entraram na Malha)', 0)
        completed_vehicles = metrics.get('Veículos que Concluíram a Viagem', 0)
        completion_rate = (completed_vehicles / total_vehicles * 100) if total_vehicles > 0 else 0
        
        avg_queue_vehicles = queue_metrics.get('Tamanho Médio da Fila (veículos)', 0)
        avg_car_length_m = 7.5
        avg_queue_km = (avg_queue_vehicles * avg_car_length_m) / 1000

        report_template = f"""
=================================================================
             RELATÓRIO DE SIMULAÇÃO DE TRÁFEGO
=================================================================
- Data da Análise: {data.get('analysis_timestamp')}
- Cenário: {data.get('scenario')}
- Modo: {data.get('mode')}

--- MÉTRICAS DE FLUXO E EFICIÊNCIA ---
- Veículos Processados (Entraram na Malha): {total_vehicles}
- Veículos que Concluíram a Viagem: {completed_vehicles}
- Taxa de Conclusão: {completion_rate:.2f}%
- Tempo de simulação: {format_seconds_to_ms(metrics.get('simulation_duration_seconds', 0))}
- Velocidade Média Geral: {metrics.get('Velocidade Média Geral (km/h)', 0):.2f} km/h
- Tempo Médio de Viagem: {format_seconds_to_ms(metrics.get('Tempo Médio de Viagem (s)', 0))}
- Tempo Médio Perdido: {format_seconds_to_ms(metrics.get('Tempo Médio Perdido (s)', 0))}

--- MÉTRICAS DE CONGESTIONAMENTO ---
- Tamanho Médio da Fila: {avg_queue_vehicles:.2f} veículos
- Extensão Média da Fila: {avg_queue_km:.3f} km
- Tempo Máximo de Espera: {format_seconds_to_ms(queue_metrics.get('Tempo Máximo de Espera (s)', 0))}

--- MÉTRICAS DE POLUIÇÃO ---
- Consumo Total de Combustível: {pollution.get('Total de fuel', '0.00 L')}
- Emissão Total de CO2: {pollution.get('Total de CO2', '0.00 kg')}
- Emissão Total de NOx: {pollution.get('Total de NOx', '0.00 kg')}
- Emissão Total de PMx: {pollution.get('Total de PMx', '0.00 kg')}
=================================================================
"""
        with open(report_path, 'a', encoding='utf-8') as f:
            f.write(report_template)

    def _simulation_loop(self):
        """Contém o loop principal da simulação e retorna o número de passos."""
        step = 0
        while True:
            try:
                traci.simulationStep()
                step += 1
            except (TraCIException, FatalTraCIError):
                task_success(f"Simulação interrompida pelo usuário no passo {step}")
                logger.warning(f"Simulação encerrada no passo {step} (conexão perdida).")
                break
        return step
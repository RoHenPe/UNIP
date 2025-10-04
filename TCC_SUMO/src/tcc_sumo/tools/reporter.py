# -*- coding: utf-8 -*-
"""Módulo responsável por toda a lógica de relatórios da simulação."""

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("ERRO: Declare a variável de ambiente 'SUMO_HOME'.")

import traci

logger = logging.getLogger(__name__)


class Reporter:
    """Coleta dados da simulação e gera relatórios de alto nível."""

    def __init__(self):
        self.arrived_vehicles = set()
        self.completed_trips_data: List[Dict[str, float]] = []
        self.co2_emissions_mg: Dict[str, float] = defaultdict(float)
        logger.info("Instância do Reporter criada.")

    def collect_data_step(self):
        """Coleta dados em tempo real a cada passo da simulação."""
        arrived_ids_this_step = traci.simulation.getArrivedIDList()
        for vehicle_id in arrived_ids_this_step:
            if vehicle_id not in self.arrived_vehicles:
                try:
                    # Corrigido: getTripInfo não existe em traci.vehicle.
                    # Os dados de duração e perda de tempo são melhor analisados
                    # a partir dos arquivos de saída XML.
                    self.completed_trips_data.append({
                        "duration": 0,
                        "timeLoss": 0,
                        "waitingTime": traci.vehicle.getWaitingTime(vehicle_id),
                    })
                    self.arrived_vehicles.add(vehicle_id)
                except traci.TraCIException:
                    logger.debug(f"Não foi possível obter dados para o veículo {vehicle_id}.")

        for vehicle_id in traci.vehicle.getIDList():
            self.co2_emissions_mg[vehicle_id] += traci.vehicle.getCO2Emission(vehicle_id)

    def _calculate_metrics(self) -> Dict[str, float]:
        """Processa os dados brutos e calcula as métricas consolidadas."""
        num_trips = len(self.completed_trips_data)
        avg_duration = sum(d['duration'] for d in self.completed_trips_data) / num_trips if num_trips else 0
        avg_time_loss = sum(d['timeLoss'] for d in self.completed_trips_data) / num_trips if num_trips else 0
        avg_waiting_time = sum(d['waitingTime'] for d in self.completed_trips_data) / num_trips if num_trips else 0
        total_co2_mg = sum(self.co2_emissions_mg.values())
        total_co2_kg = total_co2_mg / 1_000_000.0
        avg_co2_kg = total_co2_kg / num_trips if num_trips else 0

        return {
            "completed_trips": num_trips, "avg_duration": avg_duration, "avg_time_loss": avg_time_loss,
            "avg_waiting_time": avg_waiting_time, "total_co2_kg": total_co2_kg,
            "avg_co2_kg_per_vehicle": avg_co2_kg,
        }

    def _prepare_report_data(self, metrics: Dict[str, float], scenario: str, mode: str) -> Dict[str, Any]:
        """Formata os dados calculados em um dicionário estruturado."""
        return {
            "analysis_timestamp": datetime.now().isoformat(), "scenario": scenario, "mode": mode,
            "metrics": {
                "completed_trips": metrics["completed_trips"],
                "average_trip_duration_s": round(metrics["avg_duration"], 2),
                "average_time_loss_s": round(metrics["avg_time_loss"], 2),
                "average_waiting_time_s": round(metrics["avg_waiting_time"], 2),
            },
            "pollution": {
                "total_co2_emission_kg": round(metrics["total_co2_kg"], 2),
                "average_co2_emission_per_vehicle_kg": round(metrics["avg_co2_kg_per_vehicle"], 2),
            },
        }

    def generate_simulation_report(self, config: Dict[str, Any], scenario: str, mode: str):
        """Orquestra a geração e escrita de todos os arquivos de relatório."""
        logger.info("Iniciando a geração dos relatórios.")
        try:
            calculated_metrics = self._calculate_metrics()
            report_data = self._prepare_report_data(calculated_metrics, scenario, mode)
            self._write_text_report(config, report_data)
            self._update_consolidated_json(config, report_data)
            logger.info("Relatórios gerados com sucesso.")
        except Exception as e:
            logger.critical("Falha ao gerar relatórios.", exc_info=True)

    def _write_text_report(self, config: Dict[str, Any], data: Dict[str, Any]):
        """Escreve o relatório de texto (`simulation_report.log`)."""
        path = os.path.join(config['output_paths']['logs'], config['output_paths']['report_file'])
        report_template = f"""
=================================================================
             RELATÓRIO DE SIMULAÇÃO DE TRÁFEGO
=================================================================
- Data da Análise: {data['analysis_timestamp']}
- Cenário: {data['scenario']}
- Modo: {data['mode']}

--- MÉTRICAS GERAIS (MÉDIAS) ---
- Veículos que Concluíram a Viagem: {data['metrics']['completed_trips']}
- Tempo Médio de Viagem: {data['metrics']['average_trip_duration_s']}s
- Tempo Médio Perdido: {data['metrics']['average_time_loss_s']}s
- Tempo Médio de Espera: {data['metrics']['average_waiting_time_s']}s

--- MÉTRICAS DE POLUIÇÃO (CO2) ---
- Emissão Total de CO2: {data['pollution']['total_co2_emission_kg']} kg
- Emissão Média por Veículo: {data['pollution']['average_co2_emission_per_vehicle_kg']} kg
=================================================================
"""
        with open(path, 'a', encoding='utf-8') as f:
            f.write(report_template)

    def _update_consolidated_json(self, config: Dict[str, Any], data: Dict[str, Any]):
        """Atualiza o arquivo de dados consolidado (`consolidated_data.json`)."""
        path = os.path.join(config['output_paths']['dashboards'], config['output_paths']['consolidated_data'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        records = []
        if os.path.exists(path) and os.path.getsize(path) > 0:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                if not isinstance(records, list):
                    records = []
            except (IOError, json.JSONDecodeError):
                records = []
        records.append(data)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=4, ensure_ascii=False)
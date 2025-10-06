import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from datetime import datetime

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tcc_sumo.utils.helpers import get_logger, PROJECT_ROOT

logger = get_logger("LogAnalyzer")
LOGS_DIR = PROJECT_ROOT / "logs"

class LogAnalyzer:
    def __init__(self, trip_info_path, emission_path=None, queue_info_path=None):
        self.trip_info_path = Path(trip_info_path) if trip_info_path else None
        self.emission_path = Path(emission_path) if emission_path else None
        self.queue_info_path = Path(queue_info_path) if queue_info_path else None
        self.consolidated_data = {}

        if not self.trip_info_path or not self.trip_info_path.is_file():
            raise FileNotFoundError(f"Ficheiro tripinfo não encontrado: {self.trip_info_path}")

    def _parse_xml_to_dataframe(self, xml_path, element_tag):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            all_elements = root.findall(element_tag)
            data = [child.attrib for child in all_elements]
            return pd.DataFrame(data), len(all_elements)
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar o ficheiro {xml_path.name}: {e}")
            return pd.DataFrame(), 0

    def _calculate_trip_metrics(self, df, total_vehicles):
        if df.empty: return {}
        
        completed_df = df[pd.to_numeric(df['duration'], errors='coerce').notna()].copy()
        
        calculated_metrics = {
            "Veículos Processados (Entraram na Malha)": total_vehicles,
            "Veículos que Concluíram a Viagem": int(len(completed_df))
        }
        
        metric_cols = {
            'duration': 'Tempo Médio de Viagem (s)',
            'timeLoss': 'Tempo Médio Perdido (s)',
        }

        for col, name in metric_cols.items():
            if col in completed_df.columns:
                numeric_series = pd.to_numeric(completed_df[col], errors='coerce')
                calculated_metrics[name] = round(numeric_series.mean(), 2) if not numeric_series.empty else 0
            else:
                calculated_metrics[name] = 0
        
        if 'routeLength' in completed_df.columns and 'duration' in completed_df.columns:
            completed_df['speed_mps'] = pd.to_numeric(completed_df['routeLength'], errors='coerce') / pd.to_numeric(completed_df['duration'], errors='coerce')
            avg_speed_kmh = (completed_df['speed_mps'].mean() * 3.6) if not completed_df['speed_mps'].empty else 0
            calculated_metrics["Velocidade Média Geral (km/h)"] = round(avg_speed_kmh, 2)

        return calculated_metrics

    def _calculate_pollution_metrics(self, df):
        if df.empty: return {}
        
        pollution_metrics = {}
        
        pollutants_to_process = {
            'CO2': 1_000_000, 
            'fuel': 1_000, 
            'NOx': 1_000_000, 
            'PMx': 1_000_000, 
        }

        for poll, divisor in pollutants_to_process.items():
            if poll in df.columns:
                total_emission = pd.to_numeric(df[poll], errors='coerce').sum() / divisor
                unit = 'kg' if poll != 'fuel' else 'L'
                pollution_metrics[f"Total de {poll}"] = f"{total_emission:.2f} {unit}"
        
        return pollution_metrics
    
    def _calculate_queue_metrics(self, xml_path):
        if not xml_path or not xml_path.is_file():
            return {}
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            total_queueing_vehicles = 0
            max_waiting_time = 0.0
            timestep_count = 0
            
            for timestep in root.findall('.//data'):
                timestep_count += 1
                for lane in timestep.findall('.//lane'):
                    total_queueing_vehicles += float(lane.get('queueing_length', 0.0))
                    # CORREÇÃO: O atributo correto é 'maxWaitingTime'
                    if lane.get('maxWaitingTime'):
                        max_waiting_time = max(max_waiting_time, float(lane.get('maxWaitingTime')))

            avg_queue_length = (total_queueing_vehicles / timestep_count) if timestep_count > 0 else 0

            return {
                "Tamanho Médio da Fila (veículos)": round(avg_queue_length, 2),
                "Tempo Máximo de Espera (s)": round(max_waiting_time, 2)
            }
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar o ficheiro de filas {xml_path.name}: {e}")
            return {}

    def run_analysis(self, simulation_metadata, simulation_duration_seconds=0):
        # A contagem de 'total_vehicles' aqui representa os veículos no tripinfo, ou seja, os que entraram na malha.
        trip_df, total_vehicles = self._parse_xml_to_dataframe(self.trip_info_path, ".//tripinfo")
        self.consolidated_data["metrics"] = self._calculate_trip_metrics(trip_df, total_vehicles)
        
        self.consolidated_data["metrics"]["simulation_duration_seconds"] = simulation_duration_seconds

        if self.emission_path and self.emission_path.exists():
            emission_df, _ = self._parse_xml_to_dataframe(self.emission_path, ".//vehicle")
            self.consolidated_data["pollution"] = self._calculate_pollution_metrics(emission_df)
            
        if self.queue_info_path and self.queue_info_path.exists():
            self.consolidated_data["queue_metrics"] = self._calculate_queue_metrics(self.queue_info_path)
        
        json_path = LOGS_DIR / "consolidated_data.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            self.consolidated_data.update(simulation_metadata)
            self.consolidated_data["analysis_timestamp"] = datetime.now().isoformat()
            json.dump(self.consolidated_data, f, indent=4, ensure_ascii=False)
        
        return self.consolidated_data
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
    def __init__(self, trip_info_path, emission_path=None):
        self.trip_info_path = Path(trip_info_path)
        self.emission_path = Path(emission_path) if emission_path else None
        self.consolidated_data = {}

        if not self.trip_info_path.is_file():
            raise FileNotFoundError(f"Ficheiro tripinfo não encontrado: {self.trip_info_path}")

    def _parse_xml_to_dataframe(self, xml_path, element_tag):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            data = [child.attrib for child in root.findall(element_tag)]
            return pd.DataFrame(data)
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar o ficheiro {xml_path.name}: {e}")
            return pd.DataFrame()

    def _calculate_trip_metrics(self, df):
        if df.empty: return {}
        
        calculated_metrics = {"Veículos que Concluíram a Viagem": int(len(df))}
        
        metric_cols = {
            'duration': 'Tempo Médio de Viagem (s)',
            'waitTime': 'Tempo Médio de Parada (s)',
            'timeLoss': 'Tempo Médio Perdido (s)'
        }

        for col, name in metric_cols.items():
            if col in df.columns:
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                calculated_metrics[name] = round(numeric_series.mean(), 2)
            else:
                calculated_metrics[name] = 0

        return calculated_metrics

    def _calculate_pollution_metrics(self, df):
        if df.empty: return {}
        if 'CO2' not in df.columns: return {}

        df['CO2_kg'] = pd.to_numeric(df['CO2'], errors='coerce') / 1_000_000
        df['vehicle_type'] = df['id'].apply(lambda x: x.split('_')[0])
        
        pollution_by_type = df.groupby('vehicle_type')['CO2_kg'].sum().round(2).to_dict()
        
        return {f"Emissão Total de CO2 ({v_type})": f"{total_kg} kg" for v_type, total_kg in pollution_by_type.items()}

    def run_analysis(self, simulation_metadata):
        trip_df = self._parse_xml_to_dataframe(self.trip_info_path, ".//tripinfo")
        self.consolidated_data["metrics"] = self._calculate_trip_metrics(trip_df)
        
        if self.emission_path and self.emission_path.exists():
            emission_df = self._parse_xml_to_dataframe(self.emission_path, ".//vehicle")
            self.consolidated_data["pollution"] = self._calculate_pollution_metrics(emission_df)
        
        json_path = LOGS_DIR / "consolidated_data.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            self.consolidated_data.update(simulation_metadata)
            self.consolidated_data["analysis_timestamp"] = datetime.now().isoformat()
            json.dump(self.consolidated_data, f, indent=4)
        
        return self.consolidated_data
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import json
from datetime import datetime
import sys
import os
import re

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
        logger.debug(f"LogAnalyzer inicializado para o cenário em '{self.trip_info_path.parent if self.trip_info_path else 'N/A'}'.")

    def _parse_xml_to_dataframe(self, xml_path, element_tag):
        logger.debug(f"A processar ficheiro XML: {xml_path}")
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            data = [child.attrib for child in root.findall(element_tag)]
            return pd.DataFrame(data)
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar o ficheiro {xml_path.name}: {e}")
            return pd.DataFrame()

    def _parse_emission_xml(self, xml_path: Path) -> pd.DataFrame:
        if not xml_path or not xml_path.is_file(): return pd.DataFrame()
        logger.debug(f"A processar ficheiro de emissões XML: {xml_path}")
        try:
            records = []
            for _, elem in ET.iterparse(xml_path):
                if elem.tag == 'timestep':
                    time = float(elem.get('time', 0))
                    for vehicle in elem.findall('vehicle'):
                        v_data = vehicle.attrib; v_data['time'] = time; records.append(v_data)
                    elem.clear()
            return pd.DataFrame(records)
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar o ficheiro de emissões {xml_path.name}: {e}"); return pd.DataFrame()

    def _count_teleports_from_log(self) -> int:
        # CORREÇÃO: O teletransporte foi DESABILITADO. Retorna 0 para a métrica de teletransporte.
        return 0

    def _calculate_trip_metrics(self, df: pd.DataFrame, total_vehicles_in_malha: int):
        if df.empty: return {}, pd.DataFrame()
        numeric_cols = ['duration', 'timeLoss', 'waitingTime', 'routeLength']
        for col in numeric_cols: df[col] = pd.to_numeric(df.get(col), errors='coerce')
        completed_df = df.dropna(subset=['duration']).copy()
        if completed_df.empty: return {}, pd.DataFrame()
        metrics = {"Veículos Processados (Entraram na Malha)": total_vehicles_in_malha,
                   "Veículos que Concluíram a Viagem": len(completed_df),
                   'Tempo Médio de Viagem (s)': round(completed_df['duration'].mean(), 2),
                   'Tempo Médio Perdido (s)': round(completed_df['timeLoss'].mean(), 2),
                   'Tempo Médio de Espera (s)': round(completed_df['waitingTime'].mean(), 2)}
        # NOVA MÉTRICA DE CONGESTIONAMENTO: Veículos Removidos (Não Concluídos)
        metrics["Veículos Removidos (Não Concluídos)"] = total_vehicles_in_malha - len(completed_df)
        
        if metrics['Tempo Médio de Viagem (s)'] > 0:
            metrics['Percentual de Tempo Perdido'] = round((metrics['Tempo Médio Perdido (s)'] / metrics['Tempo Médio de Viagem (s)']) * 100, 2)
            metrics['Percentual de Tempo de Espera'] = round((metrics['Tempo Médio de Espera (s)'] / metrics['Tempo Médio de Viagem (s)']) * 100, 2)
        if 'routeLength' in completed_df.columns:
            completed_df['speed_mps'] = completed_df['routeLength'] / completed_df['duration']
            metrics["Velocidade Média Geral (km/h)"] = round((completed_df['speed_mps'].mean() * 3.6), 2)
        return metrics, completed_df

    def _calculate_pollution_metrics(self, df: pd.DataFrame):
        if df.empty or 'id' not in df.columns:
            logger.warning("DataFrame de emissões está vazio ou inválido. Saltando cálculo de poluição.")
            return {}
            
        pollution_metrics = {}
        pollutants = {'CO2': 1_000_000, 'fuel': 1_000, 'NOx': 1_000_000, 'PMx': 1_000_000}

        for poll in pollutants.keys():
            if poll in df.columns:
                df[poll] = pd.to_numeric(df[poll], errors='coerce')

        for poll, divisor in pollutants.items():
            if poll in df.columns:
                total_emission = df.groupby('id')[poll].sum().sum() / divisor
                unit = 'kg' if poll != 'fuel' else 'L'
                pollution_metrics[f"Total de {poll}"] = f"{total_emission:.2f} {unit}"
        return pollution_metrics

    def _calculate_queue_metrics(self, xml_path: Path):
        if not xml_path or not xml_path.is_file(): return {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            total_queue, max_wait, count = 0.0, 0.0, 0
            for timestep in root.findall('.//data'):
                count += 1
                for lane in timestep.findall('.//lane'):
                    total_queue += float(lane.get('queueing_length', 0.0))
                    max_wait = max(max_wait, float(lane.get('maxWaitingTime', 0.0)))
            avg_queue = (total_queue / count) if count > 0 else 0
            return {"Tamanho Médio da Fila (veículos)": round(avg_queue, 2), "Tempo Máximo de Espera (s)": round(max_wait, 2)}
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar ficheiro de filas {xml_path.name}: {e}"); return {}

    def run_analysis(self, simulation_metadata: dict, simulation_duration_seconds: int):
        if not self.trip_info_path:
             logger.critical("Caminho para trip_info_path não foi fornecido."); return {}
        
        trip_df = self._parse_xml_to_dataframe(self.trip_info_path, ".//tripinfo")
        emission_df = self._parse_emission_xml(self.emission_path)
        total_vehicles_in_malha = len(emission_df['id'].unique()) if not emission_df.empty and 'id' in emission_df.columns else len(trip_df)
        
        self.consolidated_data["metrics"], completed_df = self._calculate_trip_metrics(trip_df, total_vehicles_in_malha)
        self.consolidated_data["metrics"]["simulation_duration_seconds"] = simulation_duration_seconds
        # O campo 'Veículos Teleportados' é mantido por compatibilidade de relatório (valor 0)
        self.consolidated_data["metrics"]["Veículos Teleportados"] = self._count_teleports_from_log() 
        
        if not completed_df.empty and 'id' in completed_df.columns:
            all_vehicle_ids = set(emission_df['id'].unique()) if not emission_df.empty and 'id' in emission_df.columns else set(completed_df['id'])
            completed_vehicle_ids = set(completed_df['id'])
            all_vehicles_data = []
            completed_df_copy = completed_df.copy(); completed_df_copy['status'] = 'completed'
            all_vehicles_data.extend(completed_df_copy.to_dict('records'))
            unfinished_ids = all_vehicle_ids - completed_vehicle_ids
            if not emission_df.empty and unfinished_ids and 'id' in emission_df.columns:
                unfinished_df = emission_df[emission_df['id'].isin(unfinished_ids)]
                agg_data = unfinished_df.groupby('id').agg(startTime=('time','min'), endTime=('time','max')).reset_index()
                agg_data['duration'] = agg_data['endTime'] - agg_data['startTime']; agg_data['status'] = 'unfinished'
                all_vehicles_data.extend(agg_data[['id','duration','status']].to_dict('records'))
            raw_data_path = self.trip_info_path.parent / "raw_vehicle_data.json"
            with open(raw_data_path, 'w', encoding='utf-8') as f: json.dump(all_vehicles_data, f, indent=4)
            logger.info(f"Dados brutos de {len(all_vehicles_data)} veículos salvos em: {raw_data_path}")
        
        self.consolidated_data["pollution"] = self._calculate_pollution_metrics(emission_df)
        self.consolidated_data["queue_metrics"] = self._calculate_queue_metrics(self.queue_info_path)
        
        # O campo 'consolidated_data.json' é o seu dado em linguagem de máquina
        json_path = LOGS_DIR / "consolidated_data.json"
        
        # Leitura da lista existente para massificação dos dados
        records = []
        if os.path.exists(json_path) and os.path.getsize(json_path) > 0:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                if not isinstance(records, list): records = []
            except (IOError, json.JSONDecodeError): records = []

        new_record = self.consolidated_data.copy()
        new_record.update(simulation_metadata)
        # CORREÇÃO CRÍTICA: Adiciona o timestamp ao registro que será retornado
        new_record["analysis_timestamp"] = datetime.now().isoformat()
        records.append(new_record)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=4, ensure_ascii=False)
            
        # Retorna o dicionário COMPLETO com o timestamp e metadata.
        return new_record
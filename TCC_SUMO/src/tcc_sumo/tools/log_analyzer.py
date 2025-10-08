# -*- coding: utf-8 -*-
"""
Módulo para análise e processamento dos ficheiros de output do SUMO.

PILAR DE QUALIDADE: Coesão, Reusabilidade
DESCRIÇÃO: Esta classe foca-se exclusivamente na tarefa de ler, analisar e
agregar dados dos outputs do SUMO. A sua lógica pode ser reutilizada tanto pelo
SimulationManager após uma simulação, como por scripts de análise independentes.
"""
import xml.etree.ElementTree as ET
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import os

from tcc_sumo.utils.helpers import get_logger, PROJECT_ROOT

logger = get_logger("LogAnalyzer")
LOGS_DIR = PROJECT_ROOT / "logs"

class LogAnalyzer:
    """
    Analisa os ficheiros de log gerados pelo SUMO para extrair métricas de performance.
    """
    def __init__(self, trip_info_path: str, emission_path: str, queue_info_path: str):
        # Ponto de manutenibilidade: Os caminhos são recebidos como argumentos,
        # tornando a classe mais testável e independente de uma estrutura fixa.
        self.trip_info_path = Path(trip_info_path) if trip_info_path else None
        self.emission_path = Path(emission_path) if emission_path else None
        self.queue_info_path = Path(queue_info_path) if queue_info_path else None
        logger.debug(f"LogAnalyzer inicializado para o cenário em '{self.trip_info_path.parent if self.trip_info_path else 'N/A'}'.")

    def _parse_xml_to_dataframe(self, xml_path: Path, element_tag: str) -> pd.DataFrame:
        """
        Analisa um ficheiro XML genérico e converte-o para um DataFrame pandas.

        PILAR DE QUALIDADE: Robustez
        DESCRIÇÃO: Utiliza um tratamento de exceções para lidar com ficheiros
        inexistentes ou malformados, evitando que o processo de análise falhe
        inesperadamente e registando um erro claro no log.
        """
        if not xml_path or not xml_path.is_file():
            logger.warning(f"Ficheiro XML não encontrado em: {xml_path}")
            return pd.DataFrame()
        
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
        """
        Analisa o ficheiro de emissões de forma eficiente em termos de memória.

        PILAR DE QUALIDADE: Eficiência
        DESCRIÇÃO: Usa `ET.iterparse` para processar o XML de emissões, que pode
        ser muito grande. Este método não carrega o ficheiro inteiro para a memória
        de uma só vez, prevenindo problemas de consumo de recursos.
        """
        if not xml_path or not xml_path.is_file(): return pd.DataFrame()
        
        logger.debug(f"A processar ficheiro de emissões XML: {xml_path}")
        try:
            records = []
            for _, elem in ET.iterparse(xml_path):
                if elem.tag == 'timestep':
                    time = float(elem.get('time', 0))
                    for vehicle in elem.findall('vehicle'):
                        v_data = vehicle.attrib
                        v_data['time'] = time
                        records.append(v_data)
                    elem.clear()  # Liberta a memória do elemento processado
            return pd.DataFrame(records)
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar o ficheiro de emissões {xml_path.name}: {e}")
            return pd.DataFrame()

    def _calculate_trip_metrics(self, df: pd.DataFrame, total_vehicles_in_malha: int) -> tuple[dict, pd.DataFrame]:
        """
        Calcula as principais métricas de viagem a partir dos dados de tripinfo.

        PILAR DE QUALIDADE: Manutenibilidade
        DESCRIÇÃO: Isola a lógica de cálculo das métricas de viagem. Se uma nova
        métrica precisar de ser adicionada no futuro, apenas este método precisa de
        ser modificado, mantendo o resto da classe intacto.
        """
        if df.empty: return {}, pd.DataFrame()
        
        numeric_cols = ['duration', 'timeLoss', 'waitingTime', 'routeLength']
        for col in numeric_cols: df[col] = pd.to_numeric(df.get(col), errors='coerce')
        
        completed_df = df.dropna(subset=['duration']).copy()
        if completed_df.empty: return {}, pd.DataFrame()

        metrics = {
            "Veículos Processados (Entraram na Malha)": total_vehicles_in_malha,
            "Veículos que Concluíram a Viagem": len(completed_df),
            'Tempo Médio de Viagem (s)': round(completed_df['duration'].mean(), 2),
            'Tempo Médio Perdido (s)': round(completed_df['timeLoss'].mean(), 2),
            'Tempo Médio de Espera (s)': round(completed_df['waitingTime'].mean(), 2),
            "Veículos Removidos (Não Concluídos)": total_vehicles_in_malha - len(completed_df),
            "Veículos Teleportados": 0  # Desabilitado, mantido por compatibilidade
        }
        
        if metrics['Tempo Médio de Viagem (s)'] > 0:
            metrics['Percentual de Tempo Perdido'] = round((metrics['Tempo Médio Perdido (s)'] / metrics['Tempo Médio de Viagem (s)']) * 100, 2)
            metrics['Percentual de Tempo de Espera'] = round((metrics['Tempo Médio de Espera (s)'] / metrics['Tempo Médio de Viagem (s)']) * 100, 2)
        
        if 'routeLength' in completed_df.columns and not completed_df['duration'].eq(0).all():
            completed_df['speed_mps'] = completed_df['routeLength'] / completed_df['duration']
            metrics["Velocidade Média Geral (km/h)"] = round((completed_df['speed_mps'].mean() * 3.6), 2)
            
        return metrics, completed_df

    def _calculate_pollution_metrics(self, df: pd.DataFrame) -> dict:
        """Calcula as métricas de poluição a partir dos dados de emissões."""
        if df.empty or 'id' not in df.columns:
            logger.warning("DataFrame de emissões vazio ou inválido. A saltar cálculo de poluição.")
            return {}
            
        pollution_metrics = {}
        pollutants = {'CO2': 1_000_000, 'fuel': 1_000, 'NOx': 1_000_000, 'PMx': 1_000_000}

        for poll in pollutants:
            if poll in df.columns:
                df[poll] = pd.to_numeric(df[poll], errors='coerce')

        for poll, divisor in pollutants.items():
            if poll in df.columns:
                total_emission = df[poll].sum() / divisor
                unit = 'kg' if poll != 'fuel' else 'L'
                pollution_metrics[f"Total de {poll}"] = f"{total_emission:.2f} {unit}"
        return pollution_metrics

    def _calculate_queue_metrics(self, xml_path: Path) -> dict:
        """Calcula as métricas de fila a partir do ficheiro queueinfo.xml."""
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
            
            # A média do tamanho da fila deve considerar o comprimento médio de um veículo (aprox. 5m)
            avg_queue_vehicles = (total_queue / count / 5) if count > 0 else 0
            
            return {
                "Tamanho Médio da Fila (veículos)": round(avg_queue_vehicles, 2),
                "Tempo Máximo de Espera (s)": round(max_wait, 2)
            }
        except (ET.ParseError, FileNotFoundError) as e:
            logger.error(f"Erro ao processar ficheiro de filas {xml_path.name}: {e}")
            return {}

    def run_analysis(self, simulation_metadata: dict, simulation_duration_seconds: int) -> dict:
        """
        Orquestra todo o processo de análise dos ficheiros de output.
        """
        if not self.trip_info_path:
             logger.critical("Caminho para trip_info_path não foi fornecido.")
             return {}
        
        trip_df = self._parse_xml_to_dataframe(self.trip_info_path, ".//tripinfo")
        emission_df = self._parse_emission_xml(self.emission_path)
        
        total_vehicles_in_malha = len(emission_df['id'].unique()) if not emission_df.empty and 'id' in emission_df.columns else len(trip_df)
        
        metrics, completed_df = self._calculate_trip_metrics(trip_df, total_vehicles_in_malha)
        metrics["simulation_duration_seconds"] = simulation_duration_seconds
        
        pollution = self._calculate_pollution_metrics(emission_df)
        queue_metrics = self._calculate_queue_metrics(self.queue_info_path)
        
        # Consolida todos os dados num único registo
        new_record = {
            "metrics": metrics,
            "pollution": pollution,
            "queue_metrics": queue_metrics,
            **simulation_metadata,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Lógica para guardar dados brutos por veículo
        self._save_raw_vehicle_data(emission_df, completed_df)
        
        # Adiciona o novo registo ao ficheiro consolidado
        self._append_to_consolidated_json(new_record)
            
        return new_record

    def _save_raw_vehicle_data(self, emission_df: pd.DataFrame, completed_df: pd.DataFrame):
        """Salva um JSON com o status (completed/unfinished) de cada veículo."""
        if completed_df.empty or 'id' not in completed_df.columns:
            return

        all_vehicle_ids = set(emission_df['id'].unique()) if not emission_df.empty and 'id' in emission_df.columns else set(completed_df['id'])
        completed_vehicle_ids = set(completed_df['id'])
        
        all_vehicles_data = []
        completed_df_copy = completed_df.copy()
        completed_df_copy['status'] = 'completed'
        all_vehicles_data.extend(completed_df_copy.to_dict('records'))
        
        unfinished_ids = all_vehicle_ids - completed_vehicle_ids
        if not emission_df.empty and unfinished_ids and 'id' in emission_df.columns:
            unfinished_df = emission_df[emission_df['id'].isin(unfinished_ids)]
            agg_data = unfinished_df.groupby('id').agg(startTime=('time','min'), endTime=('time','max')).reset_index()
            agg_data['duration'] = agg_data['endTime'] - agg_data['startTime']
            agg_data['status'] = 'unfinished'
            all_vehicles_data.extend(agg_data[['id','duration','status']].to_dict('records'))
            
        raw_data_path = self.trip_info_path.parent / "raw_vehicle_data.json"
        try:
            with open(raw_data_path, 'w', encoding='utf-8') as f:
                json.dump(all_vehicles_data, f, indent=4)
            logger.info(f"Dados brutos de {len(all_vehicles_data)} veículos salvos em: {raw_data_path}")
        except IOError as e:
            logger.error(f"Não foi possível guardar os dados brutos dos veículos: {e}")

    def _append_to_consolidated_json(self, new_record: dict):
        """Adiciona um novo registo de simulação a um ficheiro JSON consolidado."""
        json_path = LOGS_DIR / "consolidated_data.json"
        records = []
        if json_path.exists() and json_path.stat().st_size > 0:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                if not isinstance(records, list):
                    records = []
            except (IOError, json.JSONDecodeError) as e:
                logger.warning(f"Não foi possível ler o ficheiro de dados consolidado existente. A criar um novo. Erro: {e}")
                records = []
        
        records.append(new_record)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=4, ensure_ascii=False)
            logger.info(f"Dados consolidados atualizados em '{json_path}'.")
        except IOError as e:
            logger.error(f"Não foi possível escrever no ficheiro de dados consolidado: {e}")
import argparse
import json
import re
from pathlib import Path
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import sys
import os

# --- Configuração de Paths ---
# O script confia que o run_simulation.sh (ou o ambiente de execução)
# já configurou o PYTHONPATH para permitir a importação direta.
try:
    from tcc_sumo.utils.helpers import get_logger, setup_logging, PROJECT_ROOT
except ImportError:
    # Fallback para execução direta
    src_path = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(src_path))
    from tcc_sumo.utils.helpers import get_logger, setup_logging, PROJECT_ROOT

setup_logging()
logger = get_logger("TrafficAnalyzer")

# --- Lógica para Dashboard de LOGS ---

def parse_log_file(file_path: Path) -> pd.DataFrame:
    """Lê um ficheiro de log e o transforma num DataFrame do Pandas."""
    log_pattern = re.compile(r"\[(.*?)\] \[(.*?)\] \[(.*?)\] : (.*)")
    log_records = []
    if not file_path.exists():
        logger.warning(f"Ficheiro de log não encontrado: {file_path}")
        return pd.DataFrame()

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = log_pattern.match(line)
            if match:
                log_records.append({
                    'timestamp': match.group(1).strip(),
                    'level': match.group(2).strip(),
                    'module': match.group(3).strip(),
                    'message': match.group(4).strip(),
                })
    return pd.DataFrame(log_records)

# Definimos as cores para os níveis de log (adaptado da sua imagem)
LEVEL_COLORS = {
    'CRITICAL': '#000000', # Preto
    'ERROR': '#dc3545',    # Vermelho
    'WARNING': '#ffc107',  # Amarelo/Laranja
    'INFO': '#007bff',     # Azul
    'DEBUG': '#6c757d',    # Cinza
    'NOTSET': '#6c757d'
}
# Define a ordem que as chaves devem aparecer no Dashboard
LEVEL_ORDER = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

def generate_log_dashboard():
    """Gera o dashboard de análise dos ficheiros de log."""
    logger.info("Iniciando geração do Dashboard de Logs.")
    
    # Carrega os logs
    sim_log_df = parse_log_file(PROJECT_ROOT / "logs" / "simulation.log")
    gen_log_df = parse_log_file(PROJECT_ROOT / "logs" / "generation.log")
    
    if sim_log_df.empty and gen_log_df.empty:
        logger.error("Nenhum dado de log encontrado para gerar o dashboard.")
        print("[✗] Nenhum dado de log encontrado.")
        return

    # Processa os dados
    log_summary = {}
    
    # Adiciona a coluna de classes para o template usar no JS
    if not sim_log_df.empty:
        # Usamos apenas logs de simulação e ajustamos a coluna de classes para o JS
        sim_log_df['level_class'] = sim_log_df['level'].apply(lambda x: x.lower())
        
        # Consolida todos os logs estruturados (simulação + geração)
        all_logs_df = pd.concat([sim_log_df, gen_log_df.copy()], ignore_index=True)
        
        # 1. Total de Contagens por Nível
        level_counts_raw = all_logs_df['level'].value_counts()
        
        log_summary['all_level_counts'] = []
        for level in LEVEL_ORDER:
            count = level_counts_raw.get(level, 0)
            log_summary['all_level_counts'].append({
                'level': level,
                'count': int(count),
                'color': LEVEL_COLORS.get(level, '#6c757d')
            })
        
        log_summary['total_logs'] = all_logs_df.shape[0]

    # Renderiza o template HTML
    env = Environment(loader=FileSystemLoader(str(PROJECT_ROOT / "src/tcc_sumo/templates")))
    template = env.get_template("log_dashboard.html")
    html_content = template.render(
        generation_time=pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S'),
        summary=log_summary,
        # Passamos todos os logs de simulação, agora com a classe de nível
        simulation_logs=sim_log_df.to_dict(orient='records'),
    )
    
    output_path = PROJECT_ROOT / "output"
    output_path.mkdir(exist_ok=True)
    dashboard_file = output_path / "log_dashboard.html"
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Dashboard de Logs gerado com sucesso em '{dashboard_file}'.")
    print(f"[✓] Dashboard de Logs disponível em: {dashboard_file}")


# --- Lógica para Dashboard de TRÁFEGO ---

def generate_traffic_dashboard():
    """Gera o dashboard de análise dos resultados da simulação."""
    logger.info("Iniciando geração do Dashboard de Tráfego.")
    
    data_path = PROJECT_ROOT / "logs" / "consolidated_data.json"
    if not data_path.exists():
        logger.error("Ficheiro 'consolidated_data.json' não encontrado. Execute uma simulação primeiro.")
        print("[✗] Ficheiro de dados não encontrado. Execute uma simulação primeiro.")
        return

    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Extrai as métricas para o template
    data_record = data[-1] if isinstance(data, list) and data else {}
    
    metrics = data_record.get("metrics", {})
    pollution = data_record.get("pollution", {})
    queue_metrics = data_record.get("queue_metrics", {})
    
    # Lógica para encontrar o ficheiro de dados brutos
    raw_data_path = PROJECT_ROOT / "scenarios" / f"from_{data_record.get('scenario')}" / "raw_vehicle_data.json"
    raw_data = []
    if raw_data_path.exists():
        with open(raw_data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

    # Renderiza o template HTML
    env = Environment(loader=FileSystemLoader(str(PROJECT_ROOT / "src/tcc_sumo/templates")))
    template = env.get_template("traffic_dashboard.html")
    html_content = template.render(
        generation_time=pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S'),
        data=data_record,
        metrics=metrics,
        pollution=pollution,
        queue_metrics=queue_metrics,
        vehicle_count=len(raw_data)
    )
    
    output_path = PROJECT_ROOT / "output"
    output_path.mkdir(exist_ok=True)
    dashboard_file = output_path / "traffic_dashboard.html"
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    logger.info(f"Dashboard de Tráfego gerado com sucesso em '{dashboard_file}'.")
    print(f"[✓] Dashboard de Tráfego disponível em: {dashboard_file}")


# --- Ponto de Entrada do Script ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de Dashboards de Análise para a Simulação SUMO.")
    parser.add_argument('--source', type=str, required=True, choices=['logs', 'traffic'],
                        help="Define a fonte de dados para gerar o dashboard ('logs' ou 'traffic').")
    args = parser.parse_args()

    if args.source == 'logs':
        generate_log_dashboard()
    elif args.source == 'traffic':
        generate_traffic_dashboard()
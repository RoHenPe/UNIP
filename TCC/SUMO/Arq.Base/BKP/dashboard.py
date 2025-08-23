import json
import pandas as pd
import matplotlib.pyplot as plt
import os
import xml.etree.ElementTree as ET
import webbrowser
import pathlib
from datetime import datetime
import math
import random
import numpy as np
from matplotlib.ticker import MaxNLocator
from scipy.ndimage import gaussian_filter1d

# --- Constantes ---
OUTPUT_DIR = "dashboard_output_final"
SIM_DATA_JSON = os.path.join("dashboard_output", "simulation_dashboard_data.json")
EMISSION_FILE = "emission.xml"
TRIPINFO_FILE = "tripinfo.xml"
DASHBOARD_HTML_FILENAME = "sumo_traffic_dashboard.html"
CO2_PER_CAR_PER_STEP_G = 0.75
HELP_URL = "https://docs.google.com/document/d/17R3UoVEYx7hObFm-laUh6Y7XuCOMXg2rxg7D5QMgdWw/edit?usp=sharing"

# Paleta de cores aprimorada para os gráficos
COLORS = {
    "CO2_EMISSION": '#e74c3c',
    "TRAFFIC_DENSITY": '#3498db',
    "AVG_WAIT_TIME": '#f39c12',
    "QUEUE_EAST_WEST": '#9b59b6',
    "QUEUE_NORTH_SOUTH": '#2ecc71',
    "TELEPORTED_VEHICLES": '#95a5a6',
    "TOTAL_WAITING_TIME": '#c0392b',
    "TIME_LOSS": '#27ae60',
    "COMPLETED_TRIPS_PER_STEP": '#8e44ad',
    "AVG_TIME_LOSS_PER_VEHICLE": '#007bff',
    "STOPPED_VEHICLES": '#d35400',
    "REGION_NORTE": '#3498db',
    "REGION_SUL": '#e74c3c',
    "REGION_LESTE": '#2ecc71',
    "REGION_OESTE": '#9b59b6',
    "TREND_LINE": '#ff5733'
}
MARKERS = {
    "CO2_EMISSION": 'o',
    "TRAFFIC_DENSITY": 's',
    "AVG_WAIT_TIME": 'D',
    "QUEUE_EAST_WEST": '^',
    "QUEUE_NORTH_SOUTH": 'v',
    "TELEPORTED_VEHICLES": 'x',
    "TOTAL_WAITING_TIME": '*',
    "TIME_LOSS": 'p',
    "COMPLETED_TRIPS_PER_STEP": 'h',
    "AVG_TIME_LOSS_PER_VEHICLE": 'o',
    "STOPPED_VEHICLES": 's',
    "REGION_NORTE": 'o',
    "REGION_SUL": 's',
    "REGION_LESTE": 'D',
    "REGION_OESTE": '^'
}

# Direções para agrupamento
REGIONS = ["Norte", "Sul", "Leste", "Oeste"]

# --- Funções de Parsing ---
def parse_tripinfo(tripinfo_file_path):
    """Analisa o arquivo tripinfo.xml para obter dados de tempo perdido por viagem"""
    time_loss_data = []
    try:
        if not os.path.exists(tripinfo_file_path):
            print(f"AVISO: Arquivo tripinfo '{tripinfo_file_path}' não encontrado.")
            return pd.DataFrame()

        tree = ET.parse(tripinfo_file_path)
        root = tree.getroot()
        
        for tripinfo in root.findall('tripinfo'):
            try:
                depart = float(tripinfo.get('depart', '0'))
                time_loss = float(tripinfo.get('timeLoss', '0'))
                # Converter tempo perdido para minutos
                time_loss_min = time_loss / 60.0
                time_loss_data.append({
                    "depart_time": depart,
                    "time_loss_min": time_loss_min
                })
            except (ValueError, TypeError) as e:
                print(f"AVISO: Erro ao processar dados da viagem: {e}")
                
        return pd.DataFrame(time_loss_data)
    
    except ET.ParseError as e:
        print(f"ERRO ao analisar '{tripinfo_file_path}': {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Erro inesperado ao processar '{tripinfo_file_path}': {e}")
        return pd.DataFrame()

def parse_emissions(emission_file_path):
    co2_by_step_dict = {}
    total_co2_emitted_simulation = 0
    try:
        if not os.path.exists(emission_file_path):
            print(f"AVISO: Arquivo de emissões '{emission_file_path}' não encontrado.")
            return {}, 0
        tree = ET.parse(emission_file_path)
        root = tree.getroot()
        for timestep in root.findall('timestep'):
            time_str = timestep.get('time')
            if time_str is None: continue
            time = float(time_str)
            current_co2_total_timestep = 0
            for vehicle in timestep.findall('vehicle'):
                co2_val_str = vehicle.get('CO2', '0')
                try:
                    co2_val = float(co2_val_str)
                    current_co2_total_timestep += co2_val
                    total_co2_emitted_simulation += co2_val
                except ValueError:
                    print(f"AVISO: Valor CO2 inválido para veículo no passo {time_str}. Ignorando.")
                    pass
            co2_by_step_dict[time] = co2_by_step_dict.get(time, 0) + current_co2_total_timestep
    except ET.ParseError:
        print(f"AVISO: Erro ao analisar '{emission_file_path}'. Métricas de CO2 podem estar incompletas.")
    except Exception as e:
        print(f"Erro inesperado ao processar '{emission_file_path}': {e}")
    return co2_by_step_dict, total_co2_emitted_simulation

# --- Funções de Formatação ---
def format_large_number(num, precision=0):
    if pd.isna(num) or num == 0:
        return "0"
    num_float = float(num)
    if abs(num_float) < 1000:
        return f"{num_float:.{precision}f}"
    if abs(num_float) < 1_000_000:
        return f"{num_float/1000:.1f}k"
    return f"{num_float/1_000_000:.1f}M"

def format_duration_for_axis(total_seconds_float):
    if pd.isna(total_seconds_float):
        return ""
    total_seconds = int(round(total_seconds_float))
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds:02d}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes:02d}m"

# --- Funções de Geração de Gráficos ---
def plot_time_loss_per_vehicle(tripinfo_df, output_dir):
    """Gera um gráfico preciso do tempo perdido médio por veículo"""
    chart_filename = "avg_time_loss_per_vehicle_corrected.png"
    chart_full_path = os.path.join(output_dir, chart_filename)
    
    if tripinfo_df.empty or 'time_loss_min' not in tripinfo_df.columns:
        print("Dados de tempo perdido insuficientes. Gerando placeholder.")
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, 'Dados de Tempo Perdido Indisponíveis', ha='center', va='center', fontsize=18, color='grey')
        plt.xticks([])
        plt.yticks([])
        plt.savefig(chart_full_path)
        plt.close()
        return chart_filename

    # Agrupar dados por minuto para suavizar
    tripinfo_df['depart_minute'] = (tripinfo_df['depart_time'] / 60).astype(int)
    grouped = tripinfo_df.groupby('depart_minute')['time_loss_min'].mean().reset_index()
    
    if grouped.empty:
        print("Dados agrupados de tempo perdido insuficientes.")
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, 'Dados de Tempo Perdido Insuficientes', ha='center', va='center', fontsize=18, color='grey')
        plt.xticks([])
        plt.yticks([])
        plt.savefig(chart_full_path)
        plt.close()
        return chart_filename

    # Aplicar suavização Gaussiana
    sigma = 1.5  # Nível de suavização
    smoothed = gaussian_filter1d(grouped['time_loss_min'], sigma)
    
    plt.figure(figsize=(10, 6))
    
    # Plotar dados originais e linha suavizada
    plt.plot(grouped['depart_minute'], grouped['time_loss_min'], 
             'o', markersize=4, alpha=0.4, color=COLORS['AVG_TIME_LOSS_PER_VEHICLE'], 
             label='Dados por Viagem')
    
    plt.plot(grouped['depart_minute'], smoothed, 
             '-', linewidth=2.5, color=COLORS['TREND_LINE'], 
             label='Tendência (média móvel)')
    
    # Destacar valores acima de 5 minutos
    high_loss = grouped[grouped['time_loss_min'] > 5]
    if not high_loss.empty:
        plt.plot(high_loss['depart_minute'], high_loss['time_loss_min'], 
                 'ro', markersize=6, alpha=0.7, label='Alto Tempo Perdido (>5 min)')
    
    # Configurações do gráfico
    plt.xlabel('Tempo da Simulação (minutos)', fontsize=14, color='#34495e')
    plt.ylabel('Tempo Perdido por Veículo (minutos)', fontsize=14, color='#34495e')
    plt.title('Tempo Perdido Médio por Viagem', fontsize=16, color='#2c3e50', fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(fontsize=12)
    
    # Configurar eixo Y
    max_val = max(grouped['time_loss_min'].max(), 5) * 1.2
    plt.ylim(0, max_val)
    plt.yticks(fontsize=12)
    
    # Configurar eixo X
    plt.xticks(fontsize=12)
    plt.xlim(0, grouped['depart_minute'].max() * 1.05)
    
    plt.tight_layout()
    plt.savefig(chart_full_path)
    plt.close()
    
    print(f"Gráfico de tempo perdido corrigido gerado: {chart_filename}")
    return chart_filename

def plot_data(df, x_col, y_col, title, xlabel, ylabel, filename_suffix, output_dir, is_cumulative=False, color=None, marker=None):
    # Títulos simplificados para não técnicos
    SIMPLIFIED_YLABELS = {
        "CO² Emitido (g)": "Poluição (CO²)",
        "Número de Veículos": "Quantidade de Carros",
        "Tempo Médio de Espera (s)": "Tempo de Espera (s)",
        "Tamanho da Fila (veículos)": "Carros na Fila",
        "Tempo (s)": "Tempo Total (s)",
        "Tempo Perdido por Veículo (s)": "Tempo Perdido (s)",
        "Número de Viagens": "Viagens Concluídas",
        "Carros Parados": "Carros Parados"
    }
    
    simplified_ylabel = SIMPLIFIED_YLABELS.get(ylabel, ylabel)
    
    chart_filename = f"{filename_suffix}.png"
    chart_full_path = os.path.join(output_dir, chart_filename)
    data_valid = True
    reason = ""
    
    if y_col not in df.columns or df.get(y_col, pd.Series(dtype='float64')).isnull().all() or (pd.to_numeric(df.get(y_col), errors='coerce').fillna(0).eq(0).all() and is_cumulative):
        reason = f"Coluna Y '{y_col}' ausente, nula ou com dados insuficientes"
        data_valid = False
    elif df.empty or x_col not in df.columns:
        reason = "DataFrame vazio ou coluna X ausente"
        data_valid = False
        
    if not data_valid:
        print(f"Dados para '{title}' insuficientes ({reason}). Gerando placeholder.")
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, 'Dados Indisponíveis', ha='center', va='center', fontsize=18, color='grey')
        plt.xticks([])
        plt.yticks([])
        plt.savefig(chart_full_path)
        plt.close()
        return chart_filename
    
    plt.figure(figsize=(10, 5))
    y_values_numeric = pd.to_numeric(df.get(y_col), errors='coerce').fillna(0)
    y_values_plot = y_values_numeric.cumsum() if is_cumulative else y_values_numeric
    
    plot_color = color if color else COLORS.get(filename_suffix.upper().replace("_PER_STEP", "").replace("_OVER_TIME", ""), 'gray')
    plot_marker = marker if marker else MARKERS.get(filename_suffix.upper().replace("_PER_STEP", "").replace("_OVER_TIME", ""), '.')

    plt.plot(df.get(x_col), y_values_plot, marker=plot_marker, linestyle='-', color=plot_color, linewidth=2, markersize=5)
    
    plt.xlabel(xlabel, fontsize=15, color='#34495e')
    plt.ylabel(simplified_ylabel, fontsize=15, color='#34495e')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    
    try:
        max_y = y_values_plot.max()
        if "Tempo" in ylabel and max_y > 60:
            formatter = plt.FuncFormatter(lambda x, p: format_duration_for_axis(x))
        elif max_y > 1000:
            formatter = plt.FuncFormatter(lambda x, p: format_large_number(x, 1 if x >= 1000 else 0))
        else:
            formatter = None
        if formatter:
            plt.gca().yaxis.set_major_formatter(formatter)
    except Exception as e:
        print(f"Aviso: Erro na formatação dos ticks do eixo Y para '{title}': {e}")

    plt.tight_layout(pad=0.5)
    
    plt.savefig(chart_full_path)
    plt.close()
    return chart_filename

def plot_regional_data(raw_data, regions, output_dir):
    """Gera um único visual com múltiplos pequenos, otimizado para economia de espaço e legibilidade."""
    regional_data = []
    
    for entry in raw_data:
        if "step" in entry and "region_data" in entry:
            step = entry["step"]
            for region in regions:
                if region in entry["region_data"]:
                    regional_data.append({
                        "step": step,
                        "region": region,
                        "stopped": entry["region_data"][region].get("stopped_vehicles", 0)
                    })
    
    chart_filename = "regional_stopped_vehicles.png"
    chart_full_path = os.path.join(output_dir, chart_filename)

    if not regional_data:
        plt.figure(figsize=(10, 8))
        plt.text(0.5, 0.5, 'Dados Regionais Indisponíveis', ha='center', va='center', fontsize=18, color='grey')
        plt.xticks([])
        plt.yticks([])
        plt.savefig(chart_full_path)
        plt.close()
        return {"Veículos Parados por Região": chart_filename}

    df_regional = pd.DataFrame(regional_data)
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=False) 
    axes_flat = axes.flatten()

    fig.subplots_adjust(hspace=0.25, wspace=0.15, top=0.92, bottom=0.12, left=0.1, right=0.95)

    for i, region in enumerate(regions):
        ax = axes_flat[i]
        df_region = df_regional[df_regional["region"] == region]
        
        if not df_region.empty:
            color = COLORS.get(f"REGION_{region.upper()}", '#3498db')
            ax.plot(df_region["step"], df_region["stopped"], color=color, linewidth=2.5)
            ax.fill_between(df_region["step"], df_region["stopped"], color=color, alpha=0.1)
        
        ax.set_title(region, fontsize=18, color='#34495e', fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        ax.tick_params(axis='both', labelsize=14)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, prune='both'))
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5))

    for i in range(len(regions), len(axes_flat)):
        fig.delaxes(axes_flat[i])
        
    fig.text(0.5, 0.02, 'Tempo da Simulação (s)', ha='center', va='center', fontsize=16, color='#34495e')
    fig.text(0.03, 0.5, 'Veículos Parados', ha='center', va='center', rotation='vertical', fontsize=16, color='#34495e')

    plt.savefig(chart_full_path)
    plt.close()
    
    return {"Veículos Parados por Região": chart_filename}

# --- Função Principal de Geração do HTML ---
def generate_dashboard_html_from_template(metrics_dict, charts_relative_paths, output_dir):
    current_time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    co2_log_path = os.path.relpath(EMISSION_FILE, output_dir) if charts_relative_paths.get("Emissões de CO2") != "placeholder.png" and os.path.exists(EMISSION_FILE) else "#"
    density_log_path = os.path.relpath(SIM_DATA_JSON, output_dir) if charts_relative_paths.get("Densidade de Tráfego") != "placeholder.png" and os.path.exists(SIM_DATA_JSON) else "#"
    
    wait_time_card_title_html = metrics_dict.get("wait_time_chart_title", "Tempo Médio de Espera") 
    wait_time_data_key_for_dict = metrics_dict.get("wait_time_chart_key", "placeholder_key")
    wait_time_img_src = charts_relative_paths.get(wait_time_data_key_for_dict, "placeholder.png")
    wait_time_log_path = os.path.relpath(SIM_DATA_JSON, output_dir) if wait_time_img_src != "placeholder.png" and os.path.exists(SIM_DATA_JSON) else "#"
    wait_time_description = metrics_dict.get("wait_time_chart_description", "Dados não disponíveis.")

    def get_sim_data_log_path(chart_key):
        return os.path.relpath(SIM_DATA_JSON, output_dir) if charts_relative_paths.get(chart_key) != "placeholder.png" and os.path.exists(SIM_DATA_JSON) else "#"

    html_content = f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SUMO</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>:root{{--primary:#2c3e50;--secondary:#3498db;--success:#27ae60;--light-bg:#f8f9fa;}}body{{background-color:#f0f3f5;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#495057;}}.header{{background:linear-gradient(135deg,var(--primary) 0%,#1a2530 100%);color:white;box-shadow:0 4px 12px rgba(0,0,0,0.1);}}.card{{transition:transform 0.3s,box-shadow 0.3s;border:none;border-radius:10px;overflow:hidden;box-shadow:0 4px 8px rgba(0,0,0,0.05);background-color:#fff;}}.card:hover{{transform:translateY(-5px);box-shadow:0 8px 16px rgba(0,0,0,0.1);}}.metric-card{{border-left:4px solid var(--secondary);border-radius:8px;}}.metric-card .card-title{{color:#6c757d;font-size:0.9em;font-weight:500;margin-bottom:0.2rem;}}.metric-card h2.card-text{{font-size:2.1rem;font-weight:700;color:var(--primary);margin-bottom:0.2rem;line-height:1.2;}}.metric-card p.card-text.description{{font-size:0.8em;color:#777;font-weight:400;margin-bottom:0;line-height:1.3;}}.chart-container{{background:white;border-radius:10px;padding:20px;margin-bottom:25px;box-shadow:0 4px 8px rgba(0,0,0,0.05);}}.chart-container h4{{color:var(--primary);font-size:1.1rem;margin-bottom:0;}}.chart-info{{background-color:var(--light-bg);border-radius:8px;padding:15px;margin-top:15px;border:1px solid #e9ecef;}}.chart-info p{{margin-bottom:0.25rem;font-size:0.9rem;}}.chart-info p.description{{font-size:0.85rem;color:#6c757d;margin-bottom:0;}}.log-btn{{background-color:var(--primary);color:white;border:none;transition:background-color 0.3s;font-size:0.8rem;padding:0.25rem 0.75rem;}}.log-btn:hover{{background-color:var(--secondary);}}.last-update{{font-size:0.85rem;color:#e9ecef;}}.section-title{{color:var(--primary);font-weight:500;border-bottom:2px solid #dee2e6;padding-bottom:0.5rem;font-size:1.5rem;}}.badge.bg-dark{{background-color:var(--primary) !important;}}.img-fluid{{max-width:100%;height:auto;display:block;margin-left:auto;margin-right:auto;}}</style>
    </head><body>
    <header class="header py-3 mb-4"><div class="container"><div class="d-flex justify-content-between align-items-center"><div><h1 class="mb-0 h2"><i class="fas fa-traffic-light me-2"></i>Dashboard de Simulação de Tráfego</h1><p class="mb-0 last-update">Última atualização: {current_time_str}</p></div><div><button onclick="window.print();" class="btn btn-outline-light me-2"><i class="fas fa-download me-1"></i> Exportar</button></div></div></div></header>
    <div class="container mb-5">
        <div class="row mb-4"><div class="col-md-12"><div class="alert alert-primary d-flex align-items-center"><i class="fas fa-info-circle fa-2x me-3"></i><div>Este painel mostra como o trânsito está funcionando na cidade virtual. Veja como estão o congestionamento, a poluição e o tempo que os carros ficam parados.</div></div></div></div>
        <h2 class="mb-4 border-bottom pb-2 section-title"><i class="fas fa-chart-bar me-2"></i>Resumo do Trânsito</h2>
        <div class="row g-4 mb-5">
            <div class="col-md-3"><div class="card metric-card h-100"><div class="card-body text-center"><h5 class="card-title">Carros na Cidade</h5><h2 class="card-text">{metrics_dict.get("vehicles_final", "N/A")}</h2><p class="card-text description">Total de carros circulando</p></div></div></div>
            <div class="col-md-3"><div class="card metric-card h-100"><div class="card-body text-center"><h5 class="card-title">Tempo Médio de Viagem</h5><h2 class="card-text">{metrics_dict.get("avg_trip_duration_formatted", "N/A")}</h2><p class="card-text description">Tempo que os carros levam para chegar</p></div></div></div>
            <div class="col-md-3"><div class="card metric-card h-100"><div class="card-body text-center"><h5 class="card-title">Poluição do Ar (CO²)</h5><h2 class="card-text">{metrics_dict.get("total_co2_kg_formatted", "N/A")} kg</h2><p class="card-text description">Poluição gerada pelos carros</p></div></div></div>
            <div class="col-md-3"><div class="card metric-card h-100"><div class="card-body text-center"><h5 class="card-title">Viagens Concluídas</h5><h2 class="card-text">{metrics_dict.get("num_trips_completed", "N/A")}</h2><p class="card-text description">Viagens completadas com sucesso</p></div></div></div>
        </div>
        <h2 class="mb-4 border-bottom pb-2 section-title"><i class="fas fa-chart-line me-2"></i>Como o Trânsito Mudou</h2>
        <div class="row g-4">
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Poluição do Ar (CO²)</h4><a href="{co2_log_path}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Emissões de CO2", "placeholder.png")}" alt="Poluição do Ar" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quanto os carros estão poluindo o ar ao longo do tempo.<br><small><i>Nota: Quando não temos dados exatos, usamos uma estimativa ({CO2_PER_CAR_PER_STEP_G:.2f}g por carro).</i></small></p></div></div></div>
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Congestionamento</h4><a href="{density_log_path}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Densidade de Tráfego", "placeholder.png")}" alt="Congestionamento" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros estão nas ruas a cada momento.</p></div></div></div>
        </div>
        <div class="row g-4 mt-1">
            <div class="col-lg-6">
                <div class="chart-container">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4>{wait_time_card_title_html}</h4>
                        <a href="{wait_time_log_path}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a>
                    </div>
                    <img src="{wait_time_img_src}" alt="{wait_time_card_title_html}" class="img-fluid rounded mb-3">
                    <div class="chart-info">
                        <p class="mb-1"><strong>O que significa?</strong></p>
                        <p class="mb-0 description">{wait_time_description}</p>
                    </div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="chart-container">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h4>Veículos Parados por Região</h4>
                        <a href="{get_sim_data_log_path('Veículos Parados por Região')}" class="btn btn-sm log-btn" target="_blank">
                            <i class="fas fa-file-alt me-1"></i> Ver Log
                        </a>
                    </div>
                    <img src="{charts_relative_paths.get('Veículos Parados por Região', 'placeholder.png')}" alt="Veículos Parados por Região" class="img-fluid rounded mb-3">
                    <div class="chart-info">
                        <p class="mb-1"><strong>O que significa?</strong></p>
                        <p class="mb-0 description">
                            Mostra a quantidade de veículos parados em cada região da cidade ao longo do tempo.
                            Permite comparar o congestionamento entre diferentes áreas.
                        </p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row g-4 mt-1">
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Viagens Concluídas</h4><a href="{get_sim_data_log_path('Viagens Concluídas por Tempo')}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get('Viagens Concluídas por Tempo', 'placeholder.png')}" alt="Viagens Concluídas" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros chegaram ao destino a cada momento. Indica a eficiência do trânsito.</p></div></div></div>
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Tempo Perdido por Carro</h4><a href="{get_sim_data_log_path('Perda de Tempo Média por Veículo')}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get('Perda de Tempo Média por Veículo', 'placeholder.png')}" alt="Tempo Perdido por Carro" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Tempo extra que cada carro levou por causa do trânsito. Quanto mais alto, mais ineficiente está o sistema.</p></div></div></div>
        </div>
        
    </div>
    <footer class="bg-dark text-white py-4 mt-5"><div class="container"><div class="row align-items-center"><div class="col-md-6"><h5><i class="fas fa-project-diagram me-2"></i>Simulação de Tráfego Urbano</h5><p class="mb-0" style="font-size: 0.9rem;">Dashboard gerado automaticamente a partir de dados de simulação.</p></div><div class="col-md-6 text-md-end mt-3 mt-md-0"><button class="btn btn-outline-light me-2 btn-sm" onclick="window.location.reload();"><i class="fas fa-redo me-1"></i> Recarregar Dados</button><a href="{HELP_URL}" target="_blank" class="btn btn-light btn-sm"><i class="fas fa-question-circle me-1"></i> Ajuda</a></div></div></div></footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body></html>
    """
    output_html_path = os.path.join(output_dir, DASHBOARD_HTML_FILENAME)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dashboard HTML gerado em: {output_html_path}")
    try:
        abs_html_path = os.path.abspath(output_html_path)
        html_uri = pathlib.Path(abs_html_path).as_uri()
        print(f"Para visualizar o dashboard, abra este arquivo no seu navegador: {html_uri}")
        webbrowser.open(html_uri)
    except Exception as e:
        print(f"Não foi possível obter o URI do arquivo: {e}. Abra manualmente: {os.path.abspath(output_html_path)}")

# --- Função Principal ---
def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Diretório de saída criado: {OUTPUT_DIR}")

    if not os.path.exists(SIM_DATA_JSON):
        print(f"AVISO: Arquivo '{SIM_DATA_JSON}' não encontrado. Criando dados de exemplo.")
        dummy_data = []
        for i in range(0, 3601, 60):
            total_vehicles = max(1, int(65 - (i/40) + (10 * abs(math.sin(i/100)))))
            estimated_co2 = CO2_PER_CAR_PER_STEP_G * total_vehicles * (1 + 0.2 * math.sin(i/200))
            avg_stopped_wait_dummy = max(0, 20 + 30 * abs(math.sin(i/300)) + random.uniform(-5, 5)) if total_vehicles > 10 else random.uniform(0,10)
            total_wait_dummy = total_vehicles * (20 + 10 * abs(math.sin(i/300)))
            teleported_count = random.randint(0, 2) if i > 500 and i % 300 == 0 else 0
            completed_trips_this_step = max(0, int(total_vehicles / 10 + random.uniform(-2, 2))) if i % 120 == 0 else 0
            region_data = {}
            for region in REGIONS:
                region_data[region] = { "stopped_vehicles": int(total_vehicles * (0.2 + 0.1 * random.random())), "queues": int(total_vehicles * (0.15 + 0.1 * random.random())) }
            dummy_entry = { "step": i, "total_vehicles_network": total_vehicles, "total_system_waiting_time": round(total_wait_dummy, 1), "teleported_vehicles_this_step": teleported_count, "co2_emission": round(estimated_co2, 2), "avg_stopped_vehicle_wait_time_sec": round(avg_stopped_wait_dummy,1), "time_loss": round(total_wait_dummy * 1.5, 1), "completed_trips": completed_trips_this_step, "region_data": region_data }
            dummy_data.append(dummy_entry)
        try:
            os.makedirs(os.path.dirname(SIM_DATA_JSON), exist_ok=True)
            with open(SIM_DATA_JSON, "w", encoding="utf-8") as f_json:
                json.dump(dummy_data, f_json, indent=4)
            print(f"'{SIM_DATA_JSON}' criado com dados de exemplo.")
        except Exception as e:
            print(f"ERRO ao criar JSON de exemplo: {e}")
            return

    try:
        with open(SIM_DATA_JSON, "r", encoding="utf-8") as f:
            raw_data_from_json = json.load(f)
    except Exception as e:
        print(f"ERRO: Falha ao ler {SIM_DATA_JSON}: {e}")
        return

    if not raw_data_from_json:
        print("Arquivo de dados da simulação JSON está vazio.")
        return
    
    if isinstance(raw_data_from_json, dict):
        raw_data_from_json = [raw_data_from_json]

    df_sim = pd.DataFrame(raw_data_from_json)
    if df_sim.empty:
        print("DataFrame da simulação vazio após carregar JSON.")
        return

    cols_to_ensure_numeric = { "step": 0, "total_vehicles_network": 0, "total_system_waiting_time": 0.0, "teleported_vehicles_this_step": 0, "co2_emission": 0.0, "avg_stopped_vehicle_wait_time_sec": np.nan, "time_loss": 0.0, "completed_trips": 0 }
    for col, default_val in cols_to_ensure_numeric.items():
        if col not in df_sim.columns:
            df_sim[col] = default_val
        df_sim[col] = pd.to_numeric(df_sim[col], errors='coerce').fillna(default_val)

    if "co2_emission" not in df_sim.columns or df_sim["co2_emission"].fillna(0).eq(0).all():
        if "total_vehicles_network" in df_sim.columns and not df_sim["total_vehicles_network"].fillna(0).eq(0).all():
            print(f"AVISO: 'co2_emission' ausente/zerada. Estimando como {CO2_PER_CAR_PER_STEP_G:.2f} * 'total_vehicles_network' para o gráfico.")
            df_sim["co2_emission"] = CO2_PER_CAR_PER_STEP_G * df_sim["total_vehicles_network"]
    df_sim["co2_emission"] = pd.to_numeric(df_sim["co2_emission"], errors='coerce').fillna(0)

    # Processar dados do tripinfo para obter tempo perdido preciso
    tripinfo_df = parse_tripinfo(TRIPINFO_FILE)
    
    # Obter estatísticas de tempo perdido
    metrics = {}
    if not tripinfo_df.empty and 'time_loss_min' in tripinfo_df.columns:
        avg_time_loss_min = tripinfo_df['time_loss_min'].mean()
        median_time_loss_min = tripinfo_df['time_loss_min'].median()
        max_time_loss_min = tripinfo_df['time_loss_min'].max()
        
        metrics["avg_time_loss_min"] = f"{avg_time_loss_min:.1f} min"
        metrics["median_time_loss_min"] = f"{median_time_loss_min:.1f} min"
        metrics["max_time_loss_min"] = f"{max_time_loss_min:.1f} min"
    else:
        metrics["avg_time_loss_min"] = "N/A"
        metrics["median_time_loss_min"] = "N/A"
        metrics["max_time_loss_min"] = "N/A"

    # Processar emissões e viagens
    _, total_co2_from_emission_file_g = parse_emissions(EMISSION_FILE)
    total_co2_kg_val = total_co2_from_emission_file_g / 1000.0 if total_co2_from_emission_file_g > 0 else (df_sim["co2_emission"].sum() / 1000.0 if "co2_emission" in df_sim.columns else 0)

    # Adicionar métricas gerais
    metrics["vehicles_final"] = format_large_number(df_sim["total_vehicles_network"].iloc[-1] if not df_sim.empty and "total_vehicles_network" in df_sim.columns and not df_sim["total_vehicles_network"].empty else 0, 0)
    metrics["num_trips_completed"] = format_large_number(len(tripinfo_df) if not tripinfo_df.empty else 0)
    metrics["total_co2_kg_formatted"] = format_large_number(total_co2_kg_val, 1 if total_co2_kg_val >= 1000 else 2)
    
    # Calcular tempo médio de viagem (aproximado)
    if not tripinfo_df.empty and 'depart_time' in tripinfo_df.columns:
        avg_trip_duration = (tripinfo_df['depart_time'].max() - tripinfo_df['depart_time'].min()) / len(tripinfo_df) if len(tripinfo_df) > 0 else 0
        metrics["avg_trip_duration_formatted"] = format_duration_for_axis(avg_trip_duration)
    else:
        metrics["avg_trip_duration_formatted"] = "N/A"

    charts_relative_paths = {}
    charts_relative_paths["Emissões de CO2"] = plot_data(df_sim, "step", "co2_emission", "Emissões de CO² ao Longo do Tempo", "Tempo da Simulação (s)", "CO² Emitido (g)", "co2_per_step", OUTPUT_DIR, color=COLORS["CO2_EMISSION"], marker=MARKERS["CO2_EMISSION"])
    charts_relative_paths["Densidade de Tráfego"] = plot_data(df_sim, "step", "total_vehicles_network", "Veículos na Malha ao Longo do Tempo", "Tempo da Simulação (s)", "Número de Veículos", "density_over_time", OUTPUT_DIR, color=COLORS["TRAFFIC_DENSITY"], marker=MARKERS["TRAFFIC_DENSITY"])
    
    # Gráfico corrigido de tempo perdido
    charts_relative_paths["Perda de Tempo Média por Veículo"] = plot_time_loss_per_vehicle(tripinfo_df, OUTPUT_DIR)
    
    wait_time_plot_y_col = "avg_stopped_vehicle_wait_time_sec"
    wait_time_plot_title = "Tempo Médio de Espera (Veículos Parados)"
    wait_time_plot_ylabel = "Tempo Médio de Espera (s)"
    wait_time_plot_filename_suffix = "avg_stopped_vehicle_wait_time"
    wait_time_chart_key_for_dict = "Tempo Médio de Espera (Veículos Parados) (s)"
    wait_time_card_title_html = "Tempo Médio de Espera (Veículos Parados)"
    wait_time_description = "Representa o tempo médio de espera (em segundos) apenas dos veículos que estavam parados na malha em cada intervalo de coleta."

    if wait_time_plot_y_col not in df_sim.columns or (pd.to_numeric(df_sim[wait_time_plot_y_col], errors='coerce').fillna(0)).eq(0).all():
        if "total_system_waiting_time" in df_sim.columns and "total_vehicles_network" in df_sim.columns and not df_sim["total_vehicles_network"].fillna(0).eq(0).all():
            df_sim["avg_system_wait_time_per_vehicle_sec"] = df_sim["total_system_waiting_time"].astype(float) / df_sim["total_vehicles_network"].astype(float).replace(0, float('nan'))
            df_sim["avg_system_wait_time_per_vehicle_sec"] = df_sim["avg_system_wait_time_per_vehicle_sec"].fillna(0)
            wait_time_plot_y_col = "avg_system_wait_time_per_vehicle_sec"
            wait_time_card_title_html = "Tempo Médio de Espera (Sistema)"
            wait_time_description = "Média de espera (tempo total de espera / nº de veículos). Dados específicos de 'veículos parados' não encontrados."
            
    metrics["wait_time_chart_title"] = wait_time_card_title_html
    metrics["wait_time_chart_key"] = wait_time_chart_key_for_dict
    metrics["wait_time_chart_description"] = wait_time_description
    charts_relative_paths[wait_time_chart_key_for_dict] = plot_data(df_sim, "step", wait_time_plot_y_col, "Tempo Médio de Espera", "Tempo da Simulação (s)", "Tempo Médio de Espera (s)", "avg_wait_time", OUTPUT_DIR, color=COLORS["AVG_WAIT_TIME"], marker=MARKERS["AVG_WAIT_TIME"])

    charts_relative_paths["Viagens Concluídas por Tempo"] = plot_data(df_sim, "step", "completed_trips", "Viagens Concluídas por Tempo", "Tempo da Simulação (s)", "Número de Viagens", "completed_trips_per_step", OUTPUT_DIR, is_cumulative=True, color=COLORS["COMPLETED_TRIPS_PER_STEP"], marker=MARKERS["COMPLETED_TRIPS_PER_STEP"])
    
    regional_charts = plot_regional_data(raw_data_from_json, REGIONS, OUTPUT_DIR)
    charts_relative_paths.update(regional_charts)

    generate_dashboard_html_from_template(metrics, charts_relative_paths, OUTPUT_DIR)

if __name__ == "__main__":
    main()
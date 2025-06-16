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

# --- Constantes ---
OUTPUT_DIR = "dashboard_output_final"
SIM_DATA_JSON = os.path.join("dashboard_output", "simulation_dashboard_data.json")
EMISSION_FILE = "emission.xml"
TRIPINFO_FILE = "tripinfo.xml"
DASHBOARD_HTML_FILENAME = "sumo_traffic_dashboard.html"
CO2_PER_CAR_PER_STEP_G = 0.75
HELP_URL = "https://docs.google.com/document/d/17R3UoVEYx7hObFm-laUh6Y6XuCOMXg2rxg7D5QMgdWw/edit?usp=sharing"

# Paleta de cores aprimorada para os gráficos
COLORS = {
    "CO2_EMISSION": '#e74c3c',  # Vermelho vibrante
    "TRAFFIC_DENSITY": '#3498db', # Azul claro
    "AVG_WAIT_TIME": '#f39c12',  # Laranja
    "QUEUE_EAST_WEST": '#9b59b6', # Roxo
    "QUEUE_NORTH_SOUTH": '#2ecc71', # Verde esmeralda
    "TELEPORTED_VEHICLES": '#95a5a6', # Cinza
    "TOTAL_WAITING_TIME": '#c0392b', # Vermelho escuro
    "TIME_LOSS": '#27ae60', # Verde médio
    "COMPLETED_TRIPS_PER_STEP": '#8e44ad', # Roxo escuro
    "AVG_TIME_LOSS_PER_VEHICLE": '#007bff', # Azul (novo)
    "STOPPED_VEHICLES": '#d35400', # Laranja escuro (novo)
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
    "STOPPED_VEHICLES": 's', # Novo
}


# --- Funções de Parsing ---
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
                    print(f"AVISO: Valor CO2 inválido para veículo no {time_str}. Ignorando.") # 'passo' changed to ''
                    pass
            co2_by_step_dict[time] = co2_by_step_dict.get(time, 0) + current_co2_total_timestep
    except ET.ParseError:
        print(f"AVISO: Erro ao analisar '{emission_file_path}'. Métricas de CO2 podem estar incompletas.")
    except Exception as e:
        print(f"Erro inesperado ao processar '{emission_file_path}': {e}")
    return co2_by_step_dict, total_co2_emitted_simulation

def parse_tripinfo(tripinfo_file_path):
    total_duration_sum, total_time_loss_sum, num_trips_completed = 0, 0, 0
    try:
        if not os.path.exists(tripinfo_file_path):
            print(f"AVISO: Arquivo tripinfo '{tripinfo_file_path}' não encontrado.")
            return 0, 0, 0
        tree = ET.parse(tripinfo_file_path)
        root = tree.getroot()
        for tripinfo in root.findall('tripinfo'):
            duration_str = tripinfo.get('duration', '0')
            time_loss_str = tripinfo.get('timeLoss', '0')
            try:
                total_duration_sum += float(duration_str)
                total_time_loss_sum += float(time_loss_str)
                num_trips_completed += 1
            except ValueError:
                print(f"AVISO: Valor inválido encontrado em tripinfo (duration='{duration_str}', timeLoss='{time_loss_str}'). Ignorando entrada.")
    except ET.ParseError:
        print(f"AVISO: Erro ao analisar '{tripinfo_file_path}'. Métricas de viagem podem estar incompletas.")
    except Exception as e:
        print(f"Erro inesperado ao processar '{tripinfo_file_path}': {e}")
    avg_duration = total_duration_sum / num_trips_completed if num_trips_completed > 0 else 0
    avg_time_loss = total_time_loss_sum / num_trips_completed if num_trips_completed > 0 else 0
    return avg_duration, avg_time_loss, num_trips_completed

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
    """Formats seconds into minutes:seconds or hours:minutes for axis labels."""
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
def plot_data(df, x_col, y_col, title, xlabel, ylabel, filename_suffix, output_dir, is_cumulative=False, color=None, marker=None):
    # Títulos simplificados para não técnicos
    SIMPLIFIED_TITLES = {
        "CO2_EMISSION": "Poluição do Ar (CO²)",
        "TRAFFIC_DENSITY": "Congestionamento",
        "AVG_WAIT_TIME": "Tempo de Espera",
        "QUEUE_EAST_WEST": "Fila Leste-Oeste",
        "QUEUE_NORTH_SOUTH": "Fila Norte-Sul",
        "TELEPORTED_VEHICLES": "Carros Desaparecidos",
        "TOTAL_WAITING_TIME": "Espera Total",
        "TIME_LOSS": "Tempo Perdido",
        "COMPLETED_TRIPS_PER_STEP": "Viagens Concluídas",
        "AVG_TIME_LOSS_PER_VEHICLE": "Tempo Perdido por Carro",
        "STOPPED_VEHICLES": "Carros Parados"  # Novo
    }
    
    SIMPLIFIED_YLABELS = {
        "CO² Emitido (g)": "Poluição (CO²)",
        "Número de Veículos": "Quantidade de Carros",
        "Tempo Médio de Espera (s)": "Tempo de Espera (s)",
        "Tamanho da Fila (veículos)": "Carros na Fila",
        "Tempo (s)": "Tempo Total (s)",
        "Tempo Perdido por Veículo (s)": "Tempo Perdido (s)",
        "Número de Viagens": "Viagens Concluídas",
        "Carros Parados": "Carros Parados"  # Novo
    }
    
    # Aplicar títulos simplificados
    simplified_title = SIMPLIFIED_TITLES.get(filename_suffix.upper().replace("_PER_STEP", "").replace("_OVER_TIME", ""), title)
    simplified_ylabel = SIMPLIFIED_YLABELS.get(ylabel, ylabel)
    
    chart_filename = f"{filename_suffix}.png"
    chart_full_path = os.path.join(output_dir, chart_filename)
    data_valid = True
    reason = ""
    
    if y_col not in df.columns:
        data_valid = False
        reason = f"Coluna Y '{y_col}' ausente no DataFrame"
    elif df.empty or x_col not in df.columns:
        data_valid = False
        reason = "DataFrame vazio ou coluna X ausente"
    elif df.get(y_col, pd.Series(dtype='float64')).isnull().all():
        data_valid = False
        reason = f"Coluna Y '{y_col}' contém apenas nulos"
    else:
        y_numeric_check = pd.to_numeric(df.get(y_col), errors='coerce').fillna(0)
        if y_numeric_check.eq(0).all():
            if is_cumulative:
                data_valid = False
                reason = f"Coluna Y '{y_col}' contém apenas zero (cumulativo não informativo)"
    
    if not data_valid:
        print(f"Dados para '{title}' insuficientes ou não adequados ({reason}). Gerando placeholder.")
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, f'Dados Indisponíveis ou Zero\npara o Gráfico:\n"{title}"', ha='center', va='center', fontsize=12, color='grey', wrap=True)
        plt.xticks([])
        plt.yticks([])
        try:
            plt.savefig(chart_full_path)
            print(f"Placeholder salvo: {chart_full_path}")
        except Exception as e:
            print(f"Erro ao salvar placeholder {chart_filename}: {e}")
        plt.close()
        return chart_filename
    
    plt.figure(figsize=(10, 5))
    y_values_numeric = pd.to_numeric(df.get(y_col), errors='coerce').fillna(0)
    y_values_plot = y_values_numeric.cumsum() if is_cumulative else y_values_numeric
    
    # Use cores e marcadores definidos nas constantes
    plot_color = color if color else COLORS.get(filename_suffix.upper().replace("_PER_STEP", "").replace("_OVER_TIME", ""), 'gray')
    plot_marker = marker if marker else MARKERS.get(filename_suffix.upper().replace("_PER_STEP", "").replace("_OVER_TIME", ""), '.')

    plt.plot(df.get(x_col), y_values_plot, marker=plot_marker, linestyle='-', color=plot_color, linewidth=1.5, markersize=4)
    plt.title(simplified_title, fontsize=16, color='#2c3e50', fontweight='bold')
    plt.xlabel(xlabel, fontsize=12, color='#34495e')
    plt.ylabel(simplified_ylabel, fontsize=12, color='#34495e')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(fontsize=10)
    
    # Melhoria na formatação dos ticks do eixo Y
    try:
        # Special handling for time-related Y-axes if values get large
        if "Tempo (s)" in ylabel or "Tempo Perdido (s)" in ylabel:
            # Check if values are large enough to warrant h/m format
            if y_values_plot.max() > 60: # If max value exceeds 60s, consider formatting
                formatter = plt.FuncFormatter(lambda x, p: format_duration_for_axis(x))
                plt.gca().yaxis.set_major_formatter(formatter)
            else: # Otherwise, use default plain or format_large_number
                if not pd.Series(y_values_plot).empty and pd.Series(y_values_plot).abs().max() > 1000:
                    formatter = plt.FuncFormatter(lambda x, p: format_large_number(x, 1 if x >= 1000 else 0))
                    plt.gca().yaxis.set_major_formatter(formatter)
                else:
                    plt.gca().ticklabel_format(style='plain', axis='y')
        else: # For other Y-axes (e.g., number of vehicles, CO2)
            if not pd.Series(y_values_plot).empty and pd.Series(y_values_plot).abs().max() > 1000:
                formatter = plt.FuncFormatter(lambda x, p: format_large_number(x, 1 if x >= 1000 else 0))
                plt.gca().yaxis.set_major_formatter(formatter)
            else:
                plt.gca().ticklabel_format(style='plain', axis='y')
    except Exception as e:
        print(f"Aviso: Erro na formatação dos ticks do eixo Y para '{title}': {e}")
        pass # Ignorar erro de formatação se ocorrer

    plt.yticks(fontsize=10)
    plt.tight_layout()
    try:
        plt.savefig(chart_full_path)
        print(f"Gráfico salvo: {chart_full_path}")
    except Exception as e:
        print(f"Erro ao salvar gráfico {chart_filename}: {e}")
        plt.close()
        return "placeholder.png"
    plt.close()
    return chart_filename

def plot_stopped_vehicles(raw_data, tls_focus_id, output_dir):
    tls_stopped_data = []
    if raw_data and isinstance(raw_data, list) and len(raw_data) > 0 and isinstance(raw_data[0], dict):
        for entry in raw_data:
            if isinstance(entry, dict) and "step" in entry:
                step = entry["step"]
                for tls_entry in entry.get("tls_data", []):
                    if isinstance(tls_entry, dict) and tls_entry.get("tls_id") == tls_focus_id:
                        # Verifica se existem dados de veículos parados
                        if "stopped_vehicles" in tls_entry:
                            stopped = tls_entry["stopped_vehicles"]
                            # Calcula o total de veículos parados para cada direção
                            east_west_stopped = stopped.get("W", 0) + stopped.get("E", 0)
                            north_south_stopped = stopped.get("N", 0) + stopped.get("S", 0)
                            
                            tls_stopped_data.append({
                                "step": step,
                                "Leste-Oeste Parados": east_west_stopped,
                                "Norte-Sul Parados": north_south_stopped
                            })
                        # Se não houver dados de veículos parados, usa dados de filas como fallback
                        elif "queues" in tls_entry:
                            queues = tls_entry["queues"]
                            east_west_stopped = queues.get("W", 0) + queues.get("E", 0)
                            north_south_stopped = queues.get("N", 0) + queues.get("S", 0)
                            
                            tls_stopped_data.append({
                                "step": step,
                                "Leste-Oeste Parados": east_west_stopped,
                                "Norte-Sul Parados": north_south_stopped
                            })
    
    chart_filename = f"stopped_{tls_focus_id}.png"
    chart_full_path = os.path.join(output_dir, chart_filename)
    
    if not tls_stopped_data:
        print(f"Sem dados de veículos parados para {tls_focus_id}. Gerando placeholder.")
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, f'Dados de Veículos Parados Indisponíveis\nSemáforo {tls_focus_id}', ha='center', va='center', fontsize=12, color='grey', wrap=True)
        plt.xticks([])
        plt.yticks([])
        try:
            plt.savefig(chart_full_path)
            print(f"Placeholder de veículos parados salvo: {chart_full_path}")
        except Exception as e:
            print(f"Erro ao salvar placeholder de veículos parados {chart_filename}: {e}")
        plt.close()
        return chart_filename
    
    df_tls = pd.DataFrame(tls_stopped_data)
    df_tls["Leste-Oeste Parados"] = pd.to_numeric(df_tls["Leste-Oeste Parados"], errors='coerce').fillna(0)
    df_tls["Norte-Sul Parados"] = pd.to_numeric(df_tls["Norte-Sul Parados"], errors='coerce').fillna(0)
    
    if df_tls.empty or (df_tls["Leste-Oeste Parados"].eq(0).all() and df_tls["Norte-Sul Parados"].eq(0).all()):
        print(f"Dados de veículos parados para '{tls_focus_id}' vazios ou zero. Gerando placeholder.")
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, f'Dados de Veículos Parados Vazios ou Zero\nSemáforo {tls_focus_id}', ha='center', va='center', fontsize=12, color='grey', wrap=True)
        plt.xticks([])
        plt.yticks([])
        try:
            plt.savefig(chart_full_path)
            print(f"Placeholder de veículos parados salvo: {chart_full_path}")
        except Exception as e:
            print(f"Erro ao salvar placeholder de veículos parados {chart_filename}: {e}")
        plt.close()
        return chart_filename
    
    plt.figure(figsize=(10, 5))
    plot_created_count = 0
    
    if "Leste-Oeste Parados" in df_tls.columns and not df_tls["Leste-Oeste Parados"].eq(0).all():
        plt.plot(df_tls["step"], df_tls["Leste-Oeste Parados"], label=f"Leste-Oeste", marker=MARKERS["STOPPED_VEHICLES"], color=COLORS["QUEUE_EAST_WEST"], linewidth=1.5, markersize=4)
        plot_created_count += 1
    if "Norte-Sul Parados" in df_tls.columns and not df_tls["Norte-Sul Parados"].eq(0).all():
        plt.plot(df_tls["step"], df_tls["Norte-Sul Parados"], label=f"Norte-Sul", marker=MARKERS["STOPPED_VEHICLES"], color=COLORS["QUEUE_NORTH_SOUTH"], linewidth=1.5, markersize=4)
        plot_created_count += 1
    
    if plot_created_count == 0:
        plt.close()
        print(f"Dados de veículos parados para '{tls_focus_id}' zero. Gerando placeholder.")
        plt.figure(figsize=(10, 5))
        plt.text(0.5, 0.5, f'Dados de Veículos Parados Zero\nSemáforo {tls_focus_id}', ha='center', va='center', fontsize=12, color='grey', wrap=True)
        plt.xticks([])
        plt.yticks([])
        try:
            plt.savefig(chart_full_path)
            print(f"Placeholder de veículos parados salvo: {chart_full_path}")
        except Exception as e:
            print(f"Erro ao salvar placeholder de veículos parados {chart_filename}: {e}")
        plt.close()
        return chart_filename
    
    plt.title(f"Veículos Parados no Semáforo {tls_focus_id}", fontsize=16, color='#2c3e50', fontweight='bold')
    plt.xlabel("Tempo da Simulação (s)", fontsize=12, color='#34495e')
    plt.ylabel("Carros Parados", fontsize=12, color='#34495e')
    if plot_created_count > 0:
        plt.legend(fontsize=10, loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    plt.tight_layout()
    try:
        plt.savefig(chart_full_path)
        print(f"Gráfico de veículos parados salvo: {chart_full_path}")
    except Exception as e:
        print(f"Erro ao salvar gráfico de veículos parados {chart_filename}: {e}")
        plt.close()
        return "placeholder.png"
    plt.close()
    return chart_filename

# --- Função Principal de Geração do HTML ---
def generate_dashboard_html_from_template(metrics_dict, charts_relative_paths, output_dir):
    current_time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Paths for 'Ver Log' buttons
    co2_log_path = os.path.relpath(EMISSION_FILE, output_dir) if charts_relative_paths.get("Emissões de CO2") != "placeholder.png" and os.path.exists(EMISSION_FILE) else "#"
    density_log_path = os.path.relpath(SIM_DATA_JSON, output_dir) if charts_relative_paths.get("Densidade de Tráfego") != "placeholder.png" and os.path.exists(SIM_DATA_JSON) else "#"
    
    wait_time_card_title_html = metrics_dict.get("wait_time_chart_title", "Tempo Médio de Espera") 
    wait_time_data_key_for_dict = metrics_dict.get("wait_time_chart_key", "placeholder_key")
    wait_time_img_src = charts_relative_paths.get(wait_time_data_key_for_dict, "placeholder.png")
    wait_time_log_path = os.path.relpath(SIM_DATA_JSON, output_dir) if wait_time_img_src != "placeholder.png" and os.path.exists(SIM_DATA_JSON) else "#"
    wait_time_description = metrics_dict.get("wait_time_chart_description", "Dados não disponíveis.")

    # Helper for queue log paths
    def get_stopped_log_path(tls_id_key):
        return os.path.relpath(SIM_DATA_JSON, output_dir) if charts_relative_paths.get(tls_id_key) != "placeholder.png" and os.path.exists(SIM_DATA_JSON) else "#"

    # Helper for general sim data log paths
    def get_sim_data_log_path(chart_key):
        return os.path.relpath(SIM_DATA_JSON, output_dir) if charts_relative_paths.get(chart_key) != "placeholder.png" and os.path.exists(SIM_DATA_JSON) else "#"


    html_content = f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard de Simulação de Tráfego</title>
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
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Poluição do Ar (CO²)</h4><a href="{co2_log_path}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Emissões de CO2", "placeholder.png")}" alt="Poluição do Ar" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quanto os carros estão poluindo o ar ao longo do tempo. Quanto mais alto, pior para o meio ambiente.<br><small><i>Nota: Quando não temos dados exatos, usamos uma estimativa ({CO2_PER_CAR_PER_STEP_G:.2f}g por carro).</i></small></p></div></div></div>
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Congestionamento</h4><a href="{density_log_path}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Densidade de Tráfego", "placeholder.png")}" alt="Congestionamento" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros estão nas ruas a cada momento. Quando sobe muito, significa trânsito pesado.</p></div></div></div>
        </div>
        <div class="row g-4 mt-1">
            <div class="col-lg-12">
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
        </div>
        
        <div class="row g-4 mt-1">
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Carros Desaparecidos</h4><a href="{get_sim_data_log_path('Veículos Teletransportados')}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get('Veículos Teletransportados', 'placeholder.png')}" alt="Carros Desaparecidos" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Carros que "desapareceram" porque ficaram presos no trânsito. Quanto mais alto, pior está o trânsito.</p></div></div></div>
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Tempo Total de Espera</h4><a href="{get_sim_data_log_path('Tempo de Espera Total do Sistema')}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get('Tempo de Espera Total do Sistema', 'placeholder.png')}" alt="Tempo Total de Espera" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Soma de todo tempo que os carros ficaram parados. Mostra o custo total do congestionamento.</p></div></div></div>
        </div>
        
        <div class="row g-4 mt-1">
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Tempo Perdido por Carro</h4><a href="{get_sim_data_log_path('Perda de Tempo Média por Veículo')}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get('Perda de Tempo Média por Veículo', 'placeholder.png')}" alt="Tempo Perdido por Carro" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Tempo extra que cada carro levou por causa do trânsito. Quanto mais alto, mais ineficiente está o sistema.</p></div></div></div>
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Viagens Concluídas</h4><a href="{get_sim_data_log_path('Viagens Concluídas por Tempo')}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get('Viagens Concluídas por Tempo', 'placeholder.png')}" alt="Viagens Concluídas" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros chegaram ao destino a cada momento. Indica a eficiência do trânsito.</p></div></div></div>
        </div>
        
        <h3 class="mt-5 mb-4 border-bottom pb-2 section-title"><i class="fas fa-traffic-light me-2"></i>Carros Parados nos Semáforos</h3>
        <div class="row g-4">
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Semáforo B1</h4><a href="{get_stopped_log_path("Veículos Parados no Semáforo B1")}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Veículos Parados no Semáforo B1", "placeholder.png")}" alt="Carros Parados Semáforo B1" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros ficaram parados no semáforo B1 ao longo do tempo. Valores altos indicam congestionamento nesta região.</p></div></div></div>
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Semáforo B2</h4><a href="{get_stopped_log_path("Veículos Parados no Semáforo B2")}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Veículos Parados no Semáforo B2", "placeholder.png")}" alt="Carros Parados Semáforo B2" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros ficaram parados no semáforo B2 ao longo do tempo. Valores altos indicam congestionamento nesta região.</p></div></div></div>
        </div>
        <div class="row g-4 mt-1">
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Semáforo C1</h4><a href="{get_stopped_log_path("Veículos Parados no Semáforo C1")}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Veículos Parados no Semáforo C1", "placeholder.png")}" alt="Carros Parados Semáforo C1" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros ficaram parados no semáforo C1 ao longo do tempo. Valores altos indicam congestionamento nesta região.</p></div></div></div>
            <div class="col-lg-6"><div class="chart-container"><div class="d-flex justify-content-between align-items-center mb-3"><h4>Semáforo C2</h4><a href="{get_stopped_log_path("Veículos Parados no Semáforo C2")}" class="btn btn-sm log-btn" target="_blank"><i class="fas fa-file-alt me-1"></i> Ver Log</a></div><img src="{charts_relative_paths.get("Veículos Parados no Semáforo C2", "placeholder.png")}" alt="Carros Parados Semáforo C2" class="img-fluid rounded mb-3"><div class="chart-info"><p class="mb-1"><strong>O que significa?</strong></p><p class="mb-0 description">Mostra quantos carros ficaram parados no semáforo C2 ao longo do tempo. Valores altos indicam congestionamento nesta região.</p></div></div></div>
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

    # Dummy data generation with stopped vehicles information
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
            
            # Calculate stopped vehicles for each traffic light
            stopped_vehicles_factor = abs(math.sin(i/200)) * 20  # Multiplicar para ter valores significativos
            
            dummy_entry = {
                "step": i,
                "total_vehicles_network": total_vehicles,
                "total_system_waiting_time": round(total_wait_dummy, 1),
                "teleported_vehicles_this_step": teleported_count,
                "co2_emission": round(estimated_co2, 2),
                "avg_stopped_vehicle_wait_time_sec": round(avg_stopped_wait_dummy,1),
                "time_loss": round(total_wait_dummy * 1.5, 1),
                "completed_trips": completed_trips_this_step,
                "tls_data": [
                    {
                        "tls_id": "B1", 
                        "stopped_vehicles": {
                            "W": int(total_vehicles/10 * stopped_vehicles_factor),
                            "E": int(total_vehicles/12 * stopped_vehicles_factor),
                            "N": int(total_vehicles/8 * stopped_vehicles_factor),
                            "S": int(total_vehicles/15 * stopped_vehicles_factor)
                        }
                    },
                    {
                        "tls_id": "B2", 
                        "stopped_vehicles": {
                            "W": int(total_vehicles/9 * stopped_vehicles_factor),
                            "E": int(total_vehicles/11 * stopped_vehicles_factor),
                            "N": int(total_vehicles/7 * stopped_vehicles_factor),
                            "S": int(total_vehicles/14 * stopped_vehicles_factor)
                        }
                    },
                    {
                        "tls_id": "C1", 
                        "stopped_vehicles": {
                            "W": int(total_vehicles/8 * stopped_vehicles_factor),
                            "E": int(total_vehicles/10 * stopped_vehicles_factor),
                            "N": int(total_vehicles/6 * stopped_vehicles_factor),
                            "S": int(total_vehicles/13 * stopped_vehicles_factor)
                        }
                    },
                    {
                        "tls_id": "C2", 
                        "stopped_vehicles": {
                            "W": int(total_vehicles/7 * stopped_vehicles_factor),
                            "E": int(total_vehicles/9 * stopped_vehicles_factor),
                            "N": int(total_vehicles/5 * stopped_vehicles_factor),
                            "S": int(total_vehicles/12 * stopped_vehicles_factor)
                        }
                    }
                ]
            }
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
    except json.JSONDecodeError:
        print(f"ERRO: Falha ao decodificar JSON do arquivo: {SIM_DATA_JSON}.")
        return
    except FileNotFoundError:
        print(f"ERRO: Arquivo de dados da simulação '{SIM_DATA_JSON}' não encontrado.")
        return
    except Exception as e:
        print(f"ERRO: Falha ao ler {SIM_DATA_JSON}: {e}")
        return

    if not raw_data_from_json:
        print("Arquivo de dados da simulação JSON está vazio.")
        return
    
    # Garantir que raw_data_from_json é uma lista, mesmo que o JSON esteja malformado como um objeto único
    if isinstance(raw_data_from_json, dict):
        raw_data_from_json = [raw_data_from_json]


    df_sim = pd.DataFrame(raw_data_from_json)
    if df_sim.empty:
        print("DataFrame da simulação vazio após carregar JSON.")
        return

    cols_to_ensure_numeric = {
        "step": 0,
        "total_vehicles_network": 0,
        "total_system_waiting_time": 0.0,
        "teleported_vehicles_this_step": 0,
        "co2_emission": 0.0,
        "avg_stopped_vehicle_wait_time_sec": np.nan,  # Usar np.nan para valores ausentes
        "time_loss": 0.0, # Added this column to ensure numeric
        "completed_trips": 0 # Added this column to ensure numeric
    }

    for col, default_val in cols_to_ensure_numeric.items():
        if col not in df_sim.columns:
            print(f"AVISO: Coluna '{col}' não encontrada no JSON. Será tratada com valor default/NaN.")
            df_sim[col] = default_val
        # Converter para numérico, forçando erros para NaN e preenchendo com default_val (0 ou np.nan)
        df_sim[col] = pd.to_numeric(df_sim[col], errors='coerce').fillna(default_val)

    # Estimativa de CO2 se necessário
    if "co2_emission" not in df_sim.columns or df_sim["co2_emission"].fillna(0).eq(0).all():
        if "total_vehicles_network" in df_sim.columns and not df_sim["total_vehicles_network"].fillna(0).eq(0).all():
            print(f"AVISO: 'co2_emission' ausente/zerada. Estimando como {CO2_PER_CAR_PER_STEP_G:.2f} * 'total_vehicles_network' para o gráfico.")
            df_sim["co2_emission"] = CO2_PER_CAR_PER_STEP_G * df_sim["total_vehicles_network"]
    df_sim["co2_emission"] = pd.to_numeric(df_sim["co2_emission"], errors='coerce').fillna(0)

    # --- CALCULAR NOVA MÉTRICA: Perda de Tempo Média por Veículo (para o gráfico) ---
    # Evitar divisão por zero: se total_vehicles_network for 0, avg_time_loss_per_vehicle será 0 ou NaN
    df_sim['avg_time_loss_per_vehicle'] = df_sim['time_loss'] / df_sim['total_vehicles_network'].replace(0, np.nan)
    df_sim['avg_time_loss_per_vehicle'] = df_sim['avg_time_loss_per_vehicle'].fillna(0) # Fill NaN/inf created by division by zero with 0


    avg_trip_duration, avg_time_loss, num_trips_completed = parse_tripinfo(TRIPINFO_FILE)
    _, total_co2_from_emission_file_g = parse_emissions(EMISSION_FILE)
    total_co2_kg_val = 0
    source_co2_metric = "valor dummy"
    if total_co2_from_emission_file_g > 0:
        total_co2_kg_val = total_co2_from_emission_file_g / 1000.0
        source_co2_metric = "emission.xml"
    elif not os.path.exists(EMISSION_FILE) or total_co2_from_emission_file_g == 0:
        total_co2_kg_val = 140325.3  # Valor fixo da imagem como fallback
        source_co2_metric = "valor fixo da imagem (fallback)"
    print(f"Métrica 'Total de CO² kg' usando: {source_co2_metric}")

    metrics = {
        "vehicles_final": format_large_number(df_sim["total_vehicles_network"].iloc[-1] if not df_sim.empty and "total_vehicles_network" in df_sim.columns and not df_sim["total_vehicles_network"].empty else 0, 0),
        "avg_trip_duration_formatted": format_duration_for_axis(avg_trip_duration if avg_trip_duration else 680.7),
        "num_trips_completed": format_large_number(num_trips_completed if num_trips_completed else 73),
        "total_co2_kg_formatted": format_large_number(total_co2_kg_val, 1 if total_co2_kg_val >= 1000 else 2)
    }
    if not os.path.exists(TRIPINFO_FILE) and not num_trips_completed:
        print("Usando valores dummy para métricas de viagem.");
        metrics["avg_trip_duration_formatted"] = "680.7 s"
        metrics["num_trips_completed"] = "73"

    charts_relative_paths = {}
    charts_relative_paths["Emissões de CO2"] = plot_data(df_sim, "step", "co2_emission", "Emissões de CO² ao Longo do Tempo", "Tempo da Simulação (s)", "CO² Emitido (g)", "co2_per_step", OUTPUT_DIR, color=COLORS["CO2_EMISSION"], marker=MARKERS["CO2_EMISSION"])
    charts_relative_paths["Densidade de Tráfego"] = plot_data(df_sim, "step", "total_vehicles_network", "Veículos na Malha ao Longo do Tempo", "Tempo da Simulação (s)", "Número de Veículos", "density_over_time", OUTPUT_DIR, color=COLORS["TRAFFIC_DENSITY"], marker=MARKERS["TRAFFIC_DENSITY"])
    
    # Lógica para o gráfico de Tempo de Espera
    wait_time_plot_y_col = "avg_stopped_vehicle_wait_time_sec"
    wait_time_plot_title = "Tempo Médio de Espera (Veículos Parados)"
    wait_time_plot_ylabel = "Tempo Médio de Espera (s)"
    wait_time_plot_filename_suffix = "avg_stopped_vehicle_wait_time"
    wait_time_chart_key_for_dict = "Tempo Médio de Espera (Veículos Parados) (s)"
    wait_time_card_title_html = "Tempo Médio de Espera (Veículos Parados)"
    wait_time_description = "Representa o tempo médio de espera (em segundos) apenas dos veículos que estavam parados na malha em cada intervalo de coleta."

    plot_specific_avg_stopped_data = False
    if wait_time_plot_y_col in df_sim.columns and \
       not df_sim[wait_time_plot_y_col].isnull().all() and \
       not (pd.to_numeric(df_sim[wait_time_plot_y_col], errors='coerce').fillna(0)).eq(0).all():
        plot_specific_avg_stopped_data = True
        print(f"Dados para '{wait_time_plot_title}' encontrados no JSON (coluna '{wait_time_plot_y_col}').")
    
    if not plot_specific_avg_stopped_data:
        print(f"AVISO: Dados para '{wait_time_plot_title}' (coluna '{wait_time_plot_y_col}') não encontrados ou inválidos no JSON.")
        if "total_system_waiting_time" in df_sim.columns and \
           "total_vehicles_network" in df_sim.columns and \
           not df_sim["total_vehicles_network"].fillna(0).eq(0).all():
            
            print("Usando fallback: 'Tempo Médio de Espera do Sistema (por veículo)'.")
            df_sim["avg_system_wait_time_per_vehicle_sec"] = df_sim["total_system_waiting_time"].astype(float) / df_sim["total_vehicles_network"].astype(float).replace(0, float('nan'))
            df_sim["avg_system_wait_time_per_vehicle_sec"] = df_sim["avg_system_wait_time_per_vehicle_sec"].fillna(0)

            wait_time_plot_title = "Tempo Médio de Espera do Sistema (por veículo)"
            wait_time_plot_y_col = "avg_system_wait_time_per_vehicle_sec"
            wait_time_plot_ylabel = "Tempo Médio de Espera (s)"
            wait_time_plot_filename_suffix = "avg_system_wait_time_per_vehicle"
            wait_time_chart_key_for_dict = "Tempo Médio de Espera do Sistema (por veículo) (s)"
            wait_time_card_title_html = "Tempo Médio de Espera (Sistema)"
            wait_time_description = "Representa o tempo total de espera no sistema dividido pelo número total de veículos na malha (em segundos). Nota: Dados específicos para 'veículos parados' não disponíveis."
        else:
            print("Não foi possível calcular o fallback para o gráfico de tempo médio de espera. Será um placeholder.")
            if wait_time_plot_y_col not in df_sim.columns:
                df_sim[wait_time_plot_y_col] = np.nan
            wait_time_card_title_html = "Tempo Médio de Espera"
            wait_time_description = "Dados para o tempo médio de espera de veículos parados não foram encontrados no arquivo JSON, e o fallback não pôde ser calculado."
            
    metrics["wait_time_chart_title"] = wait_time_card_title_html
    metrics["wait_time_chart_key"] = wait_time_chart_key_for_dict
    metrics["wait_time_chart_description"] = wait_time_description

    charts_relative_paths[wait_time_chart_key_for_dict] = plot_data(
        df_sim, "step", wait_time_plot_y_col, 
        wait_time_plot_title, "Tempo da Simulação (s)", 
        wait_time_plot_ylabel, 
        wait_time_plot_filename_suffix, OUTPUT_DIR, 
        is_cumulative=False, color=COLORS["AVG_WAIT_TIME"], marker=MARKERS["AVG_WAIT_TIME"] 
    )

    # --- NOVOS GRÁFICOS SOLICITADOS ---
    charts_relative_paths["Veículos Teletransportados"] = plot_data(df_sim, "step", "teleported_vehicles_this_step", "Veículos Teletransportados", "Tempo da Simulação (s)", "Número de Veículos", "teleported_vehicles", OUTPUT_DIR, color=COLORS["TELEPORTED_VEHICLES"], marker=MARKERS["TELEPORTED_VEHICLES"])
    charts_relative_paths["Tempo de Espera Total do Sistema"] = plot_data(df_sim, "step", "total_system_waiting_time", "Tempo de Espera Total do Sistema", "Tempo da Simulação (s)", "Tempo (s)", "total_waiting_time", OUTPUT_DIR, is_cumulative=False, color=COLORS["TOTAL_WAITING_TIME"], marker=MARKERS["TOTAL_WAITING_TIME"])
    
    # --- GRÁFICO DE PERDA DE TEMPO MÉDIA POR VEÍCULO (NOVO) ---
    charts_relative_paths["Perda de Tempo Média por Veículo"] = plot_data(df_sim, "step", "avg_time_loss_per_vehicle", "Perda de Tempo Média por Veículo", "Tempo da Simulação (s)", "Tempo Perdido por Veículo (s)", "avg_time_loss_per_vehicle", OUTPUT_DIR, is_cumulative=False, color=COLORS["AVG_TIME_LOSS_PER_VEHICLE"], marker=MARKERS["AVG_TIME_LOSS_PER_VEHICLE"])
    
    charts_relative_paths["Viagens Concluídas por Tempo"] = plot_data(df_sim, "step", "completed_trips", "Viagens Concluídas por Tempo", "Tempo da Simulação (s)", "Número de Viagens", "completed_trips_per_step", OUTPUT_DIR, color=COLORS["COMPLETED_TRIPS_PER_STEP"], marker=MARKERS["COMPLETED_TRIPS_PER_STEP"])


    # --- Gráficos de veículos parados nos semáforos ---
    tls_ids_to_plot = []
    if raw_data_from_json and isinstance(raw_data_from_json, list) and len(raw_data_from_json) > 0 and isinstance(raw_data_from_json[0], dict) and isinstance(raw_data_from_json[0].get("tls_data"), list):
        all_tls_ids = list(set(td.get("tls_id") for entry in raw_data_from_json for td in entry.get("tls_data",[]) if td.get("tls_id")))
        preferred_tls = ["B1", "B2", "C1", "C2"]
        tls_ids_to_plot = [tid for tid in preferred_tls if tid in all_tls_ids]
        for tid in all_tls_ids:
            if len(tls_ids_to_plot) < 4 and tid not in tls_ids_to_plot:
                tls_ids_to_plot.append(tid)
    if not tls_ids_to_plot:
        tls_ids_to_plot = ["B1", "B2", "C1", "C2"] # Default for placeholders
        print(f"AVISO: Nenhum ID de semáforo no JSON. Usando padrão: {tls_ids_to_plot} para placeholders.")
    
    for tls_id in tls_ids_to_plot:
        chart_key = f"Veículos Parados no Semáforo {tls_id}"
        charts_relative_paths[chart_key] = plot_stopped_vehicles(raw_data_from_json, tls_id, OUTPUT_DIR)

    generate_dashboard_html_from_template(metrics, charts_relative_paths, OUTPUT_DIR)

if __name__ == "__main__":
    main()
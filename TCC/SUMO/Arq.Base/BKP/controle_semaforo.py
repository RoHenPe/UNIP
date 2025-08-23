import os
import sys
import traci
import json
import argparse
from typing import Dict, List, Any, cast
import pandas as pd
import webbrowser

# --- Configuração do SUMO_HOME ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("ERRO: A variável de ambiente SUMO_HOME não está definida.")

# --- Constantes e Configurações ---
SUMO_CONFIG_FILE = "grid.sumocfg"
SUMO_BINARY = "sumo-gui"
SIMULATION_CHUNK_SIZE = 3000

# Gerar automaticamente IDs dos semáforos para malha 4x4 (A1-D4)
TLS_IDS = [f"{letter}{number}" for letter in "ABCD" for number in range(1, 5)]

# --- Constantes dos Modos de Semáforo ---
# Modo Convencional (tempo fixo)
GREEN_TIME_FIXED = 30
YELLOW_TIME_FIXED = 4
RED_TIME_FIXED = 30  # Adicionado tempo de vermelho

# Modo Dinâmico
MIN_GREEN_TIME_DYNAMIC = 15
MAX_GREEN_TIME_DYNAMIC = 60
YELLOW_TIME_DYNAMIC = 4
RED_TIME_DYNAMIC = 15
WAITING_TIME_THRESHOLD = 300  # 5 minutos de tempo total de espera

# Modo Conservador (pior cenário)
GREEN_TIME_CONSERVATIVE = 40
YELLOW_TIME_CONSERVATIVE = 3
RED_TIME_CONSERVATIVE = 40

# Mapeamento de Fases para todos os semáforos da malha 4x4
def generate_phase_map() -> Dict[str, Dict[str, Any]]:
    """Gera automaticamente o mapeamento de fases para todos os semáforos da malha 4x4."""
    phase_map: Dict[str, Dict[str, Any]] = {}
    for tls_id in TLS_IDS:
        letter, number = tls_id[0], int(tls_id[1])
        
        # Determinar faixas baseado na posição na malha
        lanes_ns: List[str] = []
        lanes_ew: List[str] = []
        lanes_south: List[str] = []
        lanes_west: List[str] = []
        
        # Adicionar faixas norte-sul
        if number > 1:
            lanes_ns.append(f"{letter}{number-1}{tls_id}_0")
        if number < 4:
            lanes_ns.append(f"{letter}{number+1}{tls_id}_0")
        
        # Adicionar faixas leste-oeste
        if letter > 'A':
            prev_letter = chr(ord(letter) - 1)
            lanes_ew.append(f"{prev_letter}{number}{tls_id}_0")
        if letter < 'D':
            next_letter = chr(ord(letter) + 1)
            lanes_ew.append(f"{next_letter}{number}{tls_id}_0")
        
        # Adicionar faixas sul
        if number < 4:
            lanes_south.append(f"{tls_id}{letter}{number+1}_0")
        
        # Adicionar faixas oeste
        if letter > 'A':
            prev_letter = chr(ord(letter) - 1)
            lanes_west.append(f"{tls_id}{prev_letter}{number}_0")
        
        phase_map[tls_id] = {
            "lanes_ns": lanes_ns,
            "lanes_ew": lanes_ew,
            "lanes_south": lanes_south,
            "lanes_west": lanes_west,
            "green_ns": 0,
            "yellow_ns": 1,
            "red_ns": 2,
            "green_ew": 3,
            "yellow_ew": 4,
            "red_ew": 5
        }
    return phase_map

PHASE_MAP = generate_phase_map()

# Estrutura para Manter o Estado dos Semáforos
tls_states: Dict[str, Dict[str, Any]] = {}


class TrafficLightController:
    """Controlador de semáforos para diferentes modos de operação."""
    
    def __init__(self):
        self.mode_functions = {
            'dynamic': self.control_dynamic,
            'conventional': self.control_conventional,
            'conservative': self.control_conservative
        }
    
    def control_lights(self, step: int, mode: str) -> None:
        """Controla os semáforos de acordo com the modo especificado."""
        if mode in self.mode_functions:
            self.mode_functions[mode](step)
    
    def get_total_waiting_time(self, lanes: List[str]) -> float:
        """Calcula o tempo total de espera em uma lista de faixas."""
        total_waiting = 0.0
        for lane_id in lanes:
            try:
                # Soma o tempo de espera de todos os veículos na faixa
                vehicle_ids = traci.lane.getLastStepVehicleIDs(lane_id)  # type: ignore
                for veh_id in vehicle_ids:
                    waiting_time = traci.vehicle.getWaitingTime(veh_id)  # type: ignore
                    total_waiting += waiting_time
            except traci.TraCIException:
                continue
        return total_waiting
    
    def control_conventional(self, step: int) -> None:
        """Lógica de controle para semáforos com tempo fixo."""
        for tls_id in TLS_IDS:
            if tls_id not in tls_states:
                continue
                
            state = tls_states[tls_id]
            time_in_phase = step - state["phase_start_time"]
            current_phase = traci.trafficlight.getPhase(tls_id)  # type: ignore

            # Verifica se está em fase verde e se deve mudar para amarelo
            is_green_phase = current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["green_ew"]]
            if is_green_phase and time_in_phase >= GREEN_TIME_FIXED:
                traci.trafficlight.setPhase(tls_id, current_phase + 1)  # type: ignore
                state["phase_start_time"] = step

            # Verifica se está em fase amarela e se deve mudar para vermelho
            is_yellow_phase = current_phase in [PHASE_MAP[tls_id]["yellow_ns"], PHASE_MAP[tls_id]["yellow_ew"]]
            if is_yellow_phase and time_in_phase >= YELLOW_TIME_FIXED:
                # Muda para a próxima fase (vermelho da direção atual, verde da oposta)
                next_phase = (current_phase + 1) % 6  # 6 fases no total
                traci.trafficlight.setPhase(tls_id, next_phase)  # type: ignore
                state["phase_start_time"] = step

            # Verifica se está em fase vermelha e se deve mudar para verde
            is_red_phase = current_phase in [PHASE_MAP[tls_id]["red_ns"], PHASE_MAP[tls_id]["red_ew"]]
            if is_red_phase and time_in_phase >= RED_TIME_FIXED:
                # Muda para a próxima fase (verde da direção oposta)
                next_phase = (current_phase + 1) % 6  # 6 fases no total
                traci.trafficlight.setPhase(tls_id, next_phase)  # type: ignore
                state["phase_start_time"] = step

    def control_dynamic(self, step: int) -> None:
        """Lógica de controle adaptativa baseada no tempo de espera."""
        for tls_id in TLS_IDS:
            if tls_id not in tls_states or tls_id not in PHASE_MAP:
                continue
            
            state = tls_states[tls_id]
            time_in_phase = step - state["phase_start_time"]
            current_phase = traci.trafficlight.getPhase(tls_id)  # type: ignore
            
            # Determinar direção atual e oposta
            if current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["yellow_ns"], PHASE_MAP[tls_id]["red_ns"]]:
                current_direction = "ns"
                opposite_direction = "ew"
                next_green_phase = PHASE_MAP[tls_id]["green_ew"]
            else:
                current_direction = "ew"
                opposite_direction = "ns"
                next_green_phase = PHASE_MAP[tls_id]["green_ns"]
            
            # Fase verde: verificar se deve mudar para amarelo
            is_green_phase = current_phase in [PHASE_MAP[tls_id][f"green_{current_direction}"]]
            if is_green_phase:
                # Calcular tempo de espera total na direção oposta
                waiting_time_opposite = self.get_total_waiting_time(PHASE_MAP[tls_id][f"lanes_{opposite_direction}"])
                
                time_exceeded_min = time_in_phase >= MIN_GREEN_TIME_DYNAMIC
                time_exceeded_max = time_in_phase >= MAX_GREEN_TIME_DYNAMIC
                pressure_high = waiting_time_opposite >= WAITING_TIME_THRESHOLD
                
                if time_exceeded_max or (time_exceeded_min and pressure_high):
                    traci.trafficlight.setPhase(tls_id, PHASE_MAP[tls_id][f"yellow_{current_direction}"])  # type: ignore
                    state["phase_start_time"] = step

            # Fase amarela: mudar para vermelho após tempo determinado
            is_yellow_phase = current_phase in [PHASE_MAP[tls_id][f"yellow_{current_direction}"]]
            if is_yellow_phase and time_in_phase >= YELLOW_TIME_DYNAMIC:
                traci.trafficlight.setPhase(tls_id, PHASE_MAP[tls_id][f"red_{current_direction}"])  # type: ignore
                state["phase_start_time"] = step

            # Fase vermelha: mudar para verde após tempo determinado ou se não há veículos esperando
            is_red_phase = current_phase in [PHASE_MAP[tls_id][f"red_{current_direction}"]]
            if is_red_phase:
                waiting_time_current = self.get_total_waiting_time(PHASE_MAP[tls_id][f"lanes_{current_direction}"])
                
                time_exceeded = time_in_phase >= RED_TIME_DYNAMIC
                no_waiting = waiting_time_current == 0
                
                if time_exceeded or no_waiting:
                    traci.trafficlight.setPhase(tls_id, next_green_phase)  # type: ignore
                    state["phase_start_time"] = step

    def control_conservative(self, step: int) -> None:
        """Lógica de controle conservadora com tempos fixos longos."""
        for tls_id in TLS_IDS:
            if tls_id not in tls_states:
                continue
                
            state = tls_states[tls_id]
            time_in_phase = step - state["phase_start_time"]
            current_phase = traci.trafficlight.getPhase(tls_id)  # type: ignore

            # Verifica se está em fase verde e se deve mudar para amarelo
            is_green_phase = current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["green_ew"]]
            if is_green_phase and time_in_phase >= GREEN_TIME_CONSERVATIVE:
                traci.trafficlight.setPhase(tls_id, current_phase + 1)  # type: ignore
                state["phase_start_time"] = step

            # Verifica se está em fase amarela e se deve mudar para vermelho
            is_yellow_phase = current_phase in [PHASE_MAP[tls_id]["yellow_ns"], PHASE_MAP[tls_id]["yellow_ew"]]
            if is_yellow_phase and time_in_phase >= YELLOW_TIME_CONSERVATIVE:
                # Muda para a próxima fase (vermelho da direção atual, verde da oposta)
                next_phase = (current_phase + 1) % 6  # 6 fases no total
                traci.trafficlight.setPhase(tls_id, next_phase)  # type: ignore
                state["phase_start_time"] = step

            # Verifica se está em fase vermelha e se deve mudar para verde
            is_red_phase = current_phase in [PHASE_MAP[tls_id]["red_ns"], PHASE_MAP[tls_id]["red_ew"]]
            if is_red_phase and time_in_phase >= RED_TIME_CONSERVATIVE:
                # Muda para a próxima fase (verde da direção oposta)
                next_phase = (current_phase + 1) % 6  # 6 fases no total
                traci.trafficlight.setPhase(tls_id, next_phase)  # type: ignore
                state["phase_start_time"] = step


def get_queue_length(lanes: List[str]) -> int:
    """Calcula o total de veículos parados em uma lista de faixas."""
    total_queue = 0
    for lane_id in lanes:
        try:
            total_queue += traci.lane.getLastStepHaltingNumber(lane_id)  # type: ignore
        except traci.TraCIException:
            continue
    return total_queue


def get_throughput(lanes: List[str]) -> int:
    """Calcula o throughput (veículos que passaram) em uma lista de faixas."""
    total_throughput = 0
    for lane_id in lanes:
        try:
            total_throughput += traci.lane.getLastStepVehicleNumber(lane_id)  # type: ignore
        except traci.TraCIException:
            continue
    return total_throughput


def initialize_tls_states() -> None:
    """Inicializa o estado de cada semáforo no início da simulação."""
    for tls_id in TLS_IDS:
        try:
            current_phase = traci.trafficlight.getPhase(tls_id)  # type: ignore
            tls_states[tls_id] = {
                "current_phase_index": current_phase,
                "phase_start_time": 0
            }
        except traci.TraCIException:
            print(f"Aviso: Semáforo {tls_id} não encontrado, pulando...")
            continue


def collect_region_data() -> Dict[str, Dict[str, int]]:
    """Coleta dados de todas as regiões."""
    region_data: Dict[str, Dict[str, int]] = {}
    
    # Coletar dados para cada região da malha 4x4
    for tls_id in TLS_IDS:
        if tls_id not in PHASE_MAP:
            continue
            
        # Determinar a região com base no ID do semáforo
        letter, number = tls_id[0], int(tls_id[1])
        region_name = f"{letter}{number}"
        
        region_data[region_name] = {
            "stopped_vehicles": get_queue_length(PHASE_MAP[tls_id].get("lanes_ns", []) + 
                                               PHASE_MAP[tls_id].get("lanes_ew", [])),
            "throughput": get_throughput(PHASE_MAP[tls_id].get("lanes_ns", []) + 
                                       PHASE_MAP[tls_id].get("lanes_ew", [])),
            "waiting_time_ns": 0,  # Será calculado posteriormente
            "waiting_time_ew": 0   # Será calculado posteriormente
        }
    
    return region_data


def collect_step_data(step: int, controller: TrafficLightController) -> Dict[str, Any]:
    """Coleta dados de um passo de simulação."""
    total_vehicles = traci.vehicle.getIDCount()  # type: ignore
    vehicle_ids = traci.vehicle.getIDList()  # type: ignore
    
    # Calcular tempo total de espera
    total_wait_time = 0.0
    for veh_id in vehicle_ids:
        total_wait_time += traci.vehicle.getWaitingTime(veh_id)  # type: ignore
    
    # Calcular tempo de espera por região
    region_data = collect_region_data()
    for tls_id in TLS_IDS:
        if tls_id not in PHASE_MAP:
            continue
            
        letter, number = tls_id[0], int(tls_id[1])
        region_name = f"{letter}{number}"
        
        if region_name in region_data:
            region_data[region_name]["waiting_time_ns"] = int(controller.get_total_waiting_time(
                PHASE_MAP[tls_id].get("lanes_ns", [])))
            region_data[region_name]["waiting_time_ew"] = int(controller.get_total_waiting_time(
                PHASE_MAP[tls_id].get("lanes_ew", [])))
    
    return {
        "step": step,
        "total_vehicles_network": total_vehicles,
        "total_system_waiting_time": total_wait_time,
        "teleported_vehicles_this_step": traci.simulation.getStartingTeleportNumber(),  # type: ignore
        "completed_trips": traci.simulation.getArrivedNumber(),  # type: ignore
        "avg_stopped_vehicle_wait_time_sec": total_wait_time / total_vehicles if total_vehicles > 0 else 0,
        "region_data": region_data
    }


def run_simulation_chunk(controller: TrafficLightController, step: int, chunk_size: int, 
                         mode: str, simulation_data: List[Dict[str, Any]]) -> int:
    """Executa um bloco/chunk da simulação."""
    chunk_end_step = step + chunk_size
    
    while step < chunk_end_step:
        if traci.simulation.getMinExpectedNumber() <= 0:  # type: ignore
            break
        
        traci.simulationStep()  # type: ignore
        controller.control_lights(step, mode)
        
        if step % 60 == 0:  # Coletar dados a cada minuto
            step_data = collect_step_data(step, controller)
            simulation_data.append(step_data)
        
        step += 1
    
    return step


def run_simulation(mode: str) -> str:
    """Executa a simulação completa de forma interativa."""
    sumo_cmd = [
        SUMO_BINARY, "-c", SUMO_CONFIG_FILE,
        "--tripinfo-output", "tripinfo.xml",
        "--emission-output", "emission.xml",
        "--quit-on-end"
    ]

    try:
        traci.start(sumo_cmd)  # type: ignore
        print(f"SUMO iniciado com sucesso no modo: {mode}")
    except traci.FatalTraCIError as e:
        print(f"ERRO fatal ao iniciar o SUMO. Verifique a configuração e o PATH. Detalhes: {e}")
        return ""

    controller = TrafficLightController()
    initialize_tls_states()
    step = 0
    simulation_data: List[Dict[str, Any]] = []
    
    try:
        while True:
            if traci.simulation.getMinExpectedNumber() <= 0:  # type: ignore
                print("Todos os veículos completaram suas viagens. Simulação encerrada.")
                break

            print(f"\nIniciando bloco de simulação de {SIMULATION_CHUNK_SIZE} passos (01 minutos)...")
            
            step = run_simulation_chunk(controller, step, SIMULATION_CHUNK_SIZE, mode, simulation_data)

            print(f"\n--- Blço Concluído no passo {step} ---")
            
            if traci.simulation.getMinExpectedNumber() <= 0:  # type: ignore
                print("Todos os veículos completaram suas viagens. Simulação encerrada.")
                break

            user_choice = input("Deseja simular por mais 01 minutos? (s/n): ").lower()
            if user_choice != 's':
                break
    
    except traci.TraCIException as e:
        print(f"\nERRO INESPERADO DURANTE A SIMULAÇÃO: {e}")
        print("A simulação foi interrompida. Verifique os arquivos de rota (.rou.xml) and a malha.")
    
    finally:
        traci.close()  # type: ignore
        print("\nConexão com o SUMO fechada.")
        
        output_dir = "dashboard_output"
        os.makedirs(output_dir, exist_ok=True)
        data_file_path = os.path.join(output_dir, f"simulation_dashboard_data_{mode}.json")
        
        with open(data_file_path, "w", encoding="utf-8") as f:
            json.dump(simulation_data, f, indent=4)
        print(f"Dados finais da simulação salvos em: {data_file_path}")
        
        return data_file_path


def run_both_modes_and_compare() -> None:
    """Executa ambos os modos e gera um comparativo"""
    print("=== INICIANDO MODO DINÂMICO (IOT) ===")
    dynamic_file = run_simulation('dynamic')
    
    print("\n=== INICIANDO MODO CONSERVADOR (PIOR CENÁRIO) ===")
    conservative_file = run_simulation('conservative')
    
    # Gerar dashboard comparativo
    generate_comparison_dashboard(dynamic_file, conservative_file)


def calculate_comprehensive_metrics(simulation_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calcula métricas mais abrangentes a partir dos dados de simulação."""
    if not simulation_data:
        return {}
    
    df = pd.DataFrame(simulation_data)
    
    # Calcular throughput total e veículos parados
    total_throughput = 0
    total_stopped_vehicles = 0
    total_waiting_time = 0.0
    
    for step in simulation_data:
        for region in step["region_data"].values():
            total_throughput += region.get("throughput", 0)
            total_stopped_vehicles += region.get("stopped_vehicles", 0)
            total_waiting_time += region.get("waiting_time_ns", 0) + region.get("waiting_time_ew", 0)
    
    metrics = {
        "total_vehicles": float(df["total_vehicles_network"].sum()),
        "total_wait_time": float(df["total_system_waiting_time"].sum()),
        "total_region_wait_time": total_waiting_time,
        "avg_wait_time": float(df["total_system_waiting_time"].sum() / df["total_vehicles_network"].sum() if df["total_vehicles_network"].sum() > 0 else 0),
        "completed_trips": float(df["completed_trips"].iloc[-1] if len(df) > 0 else 0),
        "teleported_vehicles": float(df["teleported_vehicles_this_step"].sum()),
        "total_stopped_vehicles": float(total_stopped_vehicles),
        "total_throughput": float(total_throughput),
        "avg_throughput_per_step": float(total_throughput / len(simulation_data) if len(simulation_data) > 0 else 0)
    }
    
    return metrics


def compare_simulation_results(dynamic_data: List[Dict[str, Any]], 
                              conservative_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compara os resultados das duas simulações."""
    metrics: Dict[str, float] = {}
    
    # Calcular métricas para modo dinâmico
    dynamic_metrics = calculate_comprehensive_metrics(dynamic_data)
    
    # Calcular métricas para modo conservador
    conservative_metrics = calculate_comprehensive_metrics(conservative_data)
    
    # Calcular diferenças percentuais
    for key in dynamic_metrics.keys():
        if key in conservative_metrics and conservative_metrics[key] != 0:
            metrics[f"{key}_dynamic"] = dynamic_metrics[key]
            metrics[f"{key}_conservative"] = conservative_metrics[key]
            metrics[f"{key}_difference"] = ((dynamic_metrics[key] - conservative_metrics[key]) / conservative_metrics[key]) * 100
    
    return metrics


def generate_comparison_dashboard(dynamic_file: str, conservative_file: str) -> None:
    """Gera um dashboard comparativo entre os dois modos."""
    try:
        # Carregar dados dos dois modos
        with open(dynamic_file, 'r') as f:
            dynamic_data = json.load(f)
        
        with open(conservative_file, 'r') as f:
            conservative_data = json.load(f)
        
        # Calcular métricas comparativas
        comparison_metrics = compare_simulation_results(dynamic_data, conservative_data)
        
        # Gerar HTML do dashboard comparativo
        output_dir = "dashboard_output"
        os.makedirs(output_dir, exist_ok=True)
        
        html_content = generate_comparison_html(comparison_metrics, dynamic_data, conservative_data)
        
        html_file_path = os.path.join(output_dir, "comparison_dashboard.html")
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"Dashboard comparativo gerado em: {html_file_path}")
        
        # Abrir automaticamente no navegador
        webbrowser.open(html_file_path)
        
    except Exception as e:
        print(f"Erro ao gerar dashboard comparativo: {e}")


def generate_comparison_html(metrics: Dict[str, float], dynamic_data: List[Dict[str, Any]], 
                            conservative_data: List[Dict[str, Any]]) -> str:
    """Gera HTML para o dashboard comparativo."""
    # Converter os dados para JSON string
    dynamic_data_str = json.dumps(dynamic_data)
    conservative_data_str = json.dumps(conservative_data)
    
    # Construir o HTML
    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Comparativo de Modos de Semáforo</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            h1, h2, h3 {{
                color: #333;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background-color: #f9f9f9;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #4CAF50;
            }}
            .metric-card.conservative {{
                border-left-color: #F44336;
            }}
            .metric-card.difference {{
                border-left-color: #2196F3;
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .metric-label {{
                font-size: 14px;
                color: #666;
            }}
            .positive-difference {{
                color: #4CAF50;
            }}
            .negative-difference {{
                color: #F44336;
            }}
            .charts-container {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}
            .chart-wrapper {{
                background-color: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 0 5px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Comparativo de Modos de Semáforo</h1>
            <p>Análise comparativa entre o modo dinâmico (IOT) e o modo conservador (pior cenário)</p>
            
            <h2>Métricas Comparativas</h2>
            <div class="metrics-grid">
    """
    
    # Adicionar métricas
    for key in ['total_vehicles', 'total_wait_time', 'avg_wait_time', 'completed_trips', 'total_stopped_vehicles', 'total_throughput']:
        if f'{key}_dynamic' in metrics:
            html_template += f"""
                <div class="metric-card">
                    <div class="metric-label">{" ".join([word.capitalize() for word in key.split("_")])} (Dinâmico)</div>
                    <div class="metric-value">{metrics.get(f'{key}_dynamic', 0):.0f}</div>
                </div>
                <div class="metric-card conservative">
                    <div class="metric-label">{" ".join([word.capitalize() for word in key.split("_")])} (Conservador)</div>
                    <div class="metric-value">{metrics.get(f'{key}_conservative', 0):.0f}</div>
                </div>
                <div class="metric-card difference">
                    <div class="metric-label">Diferença</div>
                    <div class="metric-value {'positive-difference' if metrics.get(f'{key}_difference', 0) > 0 else 'negative-difference'}">
                        {metrics.get(f'{key}_difference', 0):.1f}%
                    </div>
                </div>
            """
    
    html_template += """
            </div>
            
            <h2>Gráficos Comparativos</h2>
            <div class="charts-container">
                <div class="chart-wrapper">
                    <canvas id="vehiclesChart"></canvas>
                </div>
                <div class="chart-wrapper">
                    <canvas id="waitTimeChart"></canvas>
                </div>
                <div class="chart-wrapper">
                    <canvas id="throughputChart"></canvas>
                </div>
                <div class="chart-wrapper">
                    <canvas id="stoppedVehiclesChart"></canvas>
                </div>
            </div>
        </div>
        
        <script>
            // Dados para os gráficos
            const dynamicData = """ + dynamic_data_str + """;
            const conservativeData = """ + conservative_data_str + """;
            
            // Preparar dados para os gráficos
            const steps = dynamicData.map(item => item.step);
            const dynamicVehicles = dynamicData.map(item => item.total_vehicles_network);
            const conservativeVehicles = conservativeData.map(item => item.total_vehicles_network);
            
            const dynamicWaitTime = dynamicData.map(item => item.total_system_waiting_time);
            const conservativeWaitTime = conservativeData.map(item => item.total_system_waiting_time);
            
            // Calcular throughput total por passo
            const dynamicThroughput = dynamicData.map(item => {
                let throughput = 0;
                for (const region of Object.values(item.region_data)) {
                    throughput += region.throughput || 0;
                }
                return throughput;
            });
            
            const conservativeThroughput = conservativeData.map(item => {
                let throughput = 0;
                for (const region of Object.values(item.region_data)) {
                    throughput += region.throughput || 0;
                }
                return throughput;
            });
            
            // Calcular veículos parados por passo
            const dynamicStopped = dynamicData.map(item => {
                let stopped = 0;
                for (const region of Object.values(item.region_data)) {
                    stopped += region.stopped_vehicles || 0;
                }
                return stopped;
            });
            
            const conservativeStopped = conservativeData.map(item => {
                let stopped = 0;
                for (const region of Object.values(item.region_data)) {
                    stopped += region.stopped_vehicles || 0;
                }
                return stopped;
            });
            
            // Gráfico de veículos
            new Chart(document.getElementById('vehiclesChart'), {
                type: 'line',
                data: {
                    labels: steps,
                    datasets: [
                        {
                            label: 'Modo Dinâmico',
                            data: dynamicVehicles,
                            borderColor: 'rgb(76, 175, 80)',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            fill: true
                        },
                        {
                            label: 'Modo Conservador',
                            data: conservativeVehicles,
                            borderColor: 'rgb(244, 67, 54)',
                            backgroundColor: 'rgba(244, 67, 54, 0.1)',
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Veículos na Rede ao Longo do Tempo'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Tempo (s)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Número de Veículos'
                            }
                        }
                    }
                }
            });
            
            // Gráfico de tempo de espera
            new Chart(document.getElementById('waitTimeChart'), {
                type: 'line',
                data: {
                    labels: steps,
                    datasets: [
                        {
                            край label: 'Modo Dinâmico',
                            data: dynamicWaitTime,
                            borderColor: 'rgb(76, 175, 80)',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            fill: true
                        },
                        {
                            label: 'Modo Conservador',
                            data: conservativeWaitTime,
                            borderColor: 'rgb(244, 67, 54)',
                            backgroundColor: 'rgba(244, 67, 54, 0.1)',
                            край fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Tempo Total de Espera ao Longo do Tempo'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Tempo (s)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Tempo de Espera (s)'
                            }
                        }
                    }
                }
            });
            
            // Gráfico de throughput
            new Chart(document.getElementById('throughputChart'), {
                type: 'line',
                data: {
                    labels: steps,
                    datasets: [
                        {
                            label: 'Modo Dinâmico',
                            data: dynamicThroughput,
                            borderColor: 'rgb(76, 175, 80)',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            fill: true
                        },
                        {
                            label: 'Modo Conservador',
                            data: conservativeThroughput,
                            borderColor: 'rgb(244, 67, 54)',
                            backgroundColor: 'rgba(244, 67, 54, 0.1)',
                            fill: true
                        }
                    ]
                },
                край options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Throughput Total ao Longo do Tempo'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Tempo (s)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Throughput (veículos)'
                            }
                        }
                    }
                }
            });
            
            // Gráfico de veículos parados
            new Chart(document.getElementById('stoppedVehiclesChart'), {
                type: 'line',
                data: {
                    labels: steps,
                    datasets: [
                        {
                            label: 'Modo Dinâmico',
                            data: extremeStopped,
                            borderColor: 'rgb(76, 175, 80)',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            fill: true
                        },
                        {
                            label: 'Modo Conservador',
                            data: conservativeStopped,
                            borderColor: 'rgb(244, 67, 54)',
                            backgroundColor: 'rgba(244, 67, 54, 0.1)',
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Veículos Parados ao Longo do Tempo'
                        }
                    },
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Tempo (s)'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Veículos Parados'
                            }
                        }
                    }
                }
            });
        </script>
    </body>
    </html>
    """
    
    return html_template


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Controlador de Semáforos para Simulação SUMO.")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=['dynamic', 'conventional', 'conservative', 'compare'], 
        default='dynamic',
        help="Modo de operação do semáforo."
    )
    args = parser.parse_args()

    if not os.path.exists(SUMO_CONFIG_FILE):
        print(f"ERRO: Arquivo de configuração '{SUMO_CONFIG_FILE}' não encontrado!")
    else:
        if args.mode == 'compare':
            run_both_modes_and_compare()
        else:
            run_simulation(args.mode)
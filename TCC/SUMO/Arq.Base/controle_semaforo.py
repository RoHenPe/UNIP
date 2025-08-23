import os
import sys

# --- Configuração do Ambiente SUMO ---
SUMO_HOME = r"I:\UNIP\TCC\SUMO\SUMO_Raiz"
os.environ['SUMO_HOME'] = SUMO_HOME

# Adicionar tools do SUMO ao path do Python
SUMO_TOOLS = os.path.join(SUMO_HOME, 'tools')
sys.path.append(SUMO_TOOLS)

try:
    import traci
except ImportError:
    print("Erro: Não foi possível importar traci. Verifique se o SUMO está instalado corretamente.")
    sys.exit(1)

import json
import argparse
from typing import Dict, List, Any
import pandas as pd
import webbrowser
import datetime
import math

# --- Constantes e Configurações ---
PROJECT_DIR = r"I:\UNIP\TCC\SUMO"
ARQ_BASE_DIR = os.path.join(PROJECT_DIR, "Arq.Base")
SIMULATION_OUTPUT_DIR = os.path.join(PROJECT_DIR, "simulation_output")

# Configurações do SUMO
SUMO_CONFIG_FILE = os.path.join(ARQ_BASE_DIR, "grid.sumocfg")
SUMO_BINARY = os.path.join(SUMO_HOME, "bin", "sumo-gui.exe")

# Verificar se os arquivos existem
if not os.path.exists(SUMO_BINARY):
    print(f"ERRO: Executável do SUMO não encontrado em: {SUMO_BINARY}")
    sys.exit(1)

if not os.path.exists(SUMO_CONFIG_FILE):
    print(f"ERRO: Arquivo de configuração '{SUMO_CONFIG_FILE}' não encontrado!")
    sys.exit(1)

# Criar diretório de saída se não existir
os.makedirs(SIMULATION_OUTPUT_DIR, exist_ok=True)

# --- Parâmetros dos Modos de Semáforo ---
# Modo Dinâmico (OIT)
MIN_GREEN_TIME_DYNAMIC = 15
MAX_GREEN_TIME_DYNAMIC = 60
YELLOW_TIME_DYNAMIC = 4
RED_TIME_DYNAMIC = 15
WAITING_TIME_THRESHOLD = 300  # 5 minutos

# Modo Conservador (Tempo Fixo)
GREEN_TIME_CONSERVATIVE = 40
YELLOW_TIME_CONSERVATIVE = 3
RED_TIME_CONSERVATIVE = 40

# Constantes para métricas
CO2_PER_CAR_PER_STEP_G = 0.75
FUEL_CONSUMPTION_PER_STEP = 0.05

# Variáveis globais que serão definidas dinamicamente
TLS_IDS = []
PHASE_MAP = {}
tls_states = {}

def get_available_tls_ids():
    """Obtém dinamicamente os IDs dos semáforos disponíveis na simulação"""
    try:
        return traci.trafficlight.getIDList()
    except traci.TraCIException:
        print("Aviso: Não foi possível obter a lista de semáforos")
        return []

def generate_phase_map() -> Dict[str, Dict[str, Any]]:
    """Gera mapeamento de fases apenas para semáforos disponíveis"""
    phase_map = {}
    for tls_id in TLS_IDS:
        phase_map[tls_id] = {
            "green_ns": 0,
            "yellow_ns": 1,
            "red_ns": 2,
            "green_ew": 3,
            "yellow_ew": 4,
            "red_ew": 5
        }
    return phase_map

class TrafficLightController:
    """Controlador de semáforos para diferentes modos de operação."""
    
    def __init__(self):
        self.mode_functions = {
            'dynamic': self.control_dynamic,
            'conservative': self.control_conservative
        }
    
    def control_lights(self, step: int, mode: str) -> None:
        """Controla os semáforos de acordo com o modo especificado."""
        if mode in self.mode_functions:
            self.mode_functions[mode](step)
    
    def get_total_waiting_time(self, lanes: List[str]) -> float:
        """Calcula o tempo total de espera em uma lista de faixas."""
        total_waiting = 0.0
        for lane_id in lanes:
            try:
                vehicle_ids = traci.lane.getLastStepVehicleIDs(lane_id)
                for veh_id in vehicle_ids:
                    total_waiting += traci.vehicle.getWaitingTime(veh_id) or 0
            except traci.TraCIException:
                continue
        return total_waiting
    
    def control_dynamic(self, step: int) -> None:
        """Lógica de controle adaptativa baseada em sensores OIT."""
        for tls_id in list(tls_states.keys()):
            if tls_id not in TLS_IDS:
                continue
            
            state = tls_states[tls_id]
            time_in_phase = step - state["phase_start_time"]
            
            try:
                current_phase = traci.trafficlight.getPhase(tls_id)
            except traci.TraCIException:
                continue
            
            # Obter faixas controladas
            try:
                controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
            except traci.TraCIException:
                continue
            
            # Classificar faixas por direção
            lanes_ns = [lane for lane in controlled_lanes if 'ns' in lane]
            lanes_ew = [lane for lane in controlled_lanes if 'ew' in lane]
            
            # Determinar direção atual
            if current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["yellow_ns"], PHASE_MAP[tls_id]["red_ns"]]:
                current_dir = "ns"
                opposite_dir = "ew"
                next_green_phase = PHASE_MAP[tls_id]["green_ew"]
                current_lanes = lanes_ns
                opposite_lanes = lanes_ew
            else:
                current_dir = "ew"
                opposite_dir = "ns"
                next_green_phase = PHASE_MAP[tls_id]["green_ns"]
                current_lanes = lanes_ew
                opposite_lanes = lanes_ns
            
            # Lógica para fase verde
            is_green_phase = current_phase == PHASE_MAP[tls_id][f"green_{current_dir}"]
            if is_green_phase:
                waiting_time_opposite = self.get_total_waiting_time(opposite_lanes)
                
                min_time_exceeded = time_in_phase >= MIN_GREEN_TIME_DYNAMIC
                max_time_exceeded = time_in_phase >= MAX_GREEN_TIME_DYNAMIC
                high_pressure = waiting_time_opposite >= WAITING_TIME_THRESHOLD
                
                if max_time_exceeded or (min_time_exceeded and high_pressure):
                    try:
                        traci.trafficlight.setPhase(tls_id, PHASE_MAP[tls_id][f"yellow_{current_dir}"])
                        state["phase_start_time"] = step
                    except traci.TraCIException:
                        continue

            # Lógica para fase amarela
            is_yellow_phase = current_phase == PHASE_MAP[tls_id][f"yellow_{current_dir}"]
            if is_yellow_phase and time_in_phase >= YELLOW_TIME_DYNAMIC:
                try:
                    traci.trafficlight.setPhase(tls_id, PHASE_MAP[tls_id][f"red_{current_dir}"])
                    state["phase_start_time"] = step
                except traci.TraCIException:
                    continue

            # Lógica para fase vermelha
            is_red_phase = current_phase == PHASE_MAP[tls_id][f"red_{current_dir}"]
            if is_red_phase:
                waiting_time_current = self.get_total_waiting_time(current_lanes)
                
                time_exceeded = time_in_phase >= RED_TIME_DYNAMIC
                no_waiting = waiting_time_current == 0
                
                if time_exceeded or no_waiting:
                    try:
                        traci.trafficlight.setPhase(tls_id, next_green_phase)
                        state["phase_start_time"] = step
                    except traci.TraCIException:
                        continue

    def control_conservative(self, step: int) -> None:
        """Lógica de controle conservadora com tempos fixos."""
        for tls_id in list(tls_states.keys()):
            if tls_id not in TLS_IDS:
                continue
                
            state = tls_states[tls_id]
            time_in_phase = step - state["phase_start_time"]
            
            try:
                current_phase = traci.trafficlight.getPhase(tls_id)
            except traci.TraCIException:
                continue

            # Verificar se está em fase verde
            is_green_phase = current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["green_ew"]]
            if is_green_phase and time_in_phase >= GREEN_TIME_CONSERVATIVE:
                try:
                    traci.trafficlight.setPhase(tls_id, current_phase + 1)
                    state["phase_start_time"] = step
                except traci.TraCIException:
                    continue

            # Verificar se está em fase amarela
            is_yellow_phase = current_phase in [PHASE_MAP[tls_id]["yellow_ns"], PHASE_MAP[tls_id]["yellow_ew"]]
            if is_yellow_phase and time_in_phase >= YELLOW_TIME_CONSERVATIVE:
                next_phase = (current_phase + 1) % 6
                try:
                    traci.trafficlight.setPhase(tls_id, next_phase)
                    state["phase_start_time"] = step
                except traci.TraCIException:
                    continue

            # Verificar se está em fase vermelha
            is_red_phase = current_phase in [PHASE_MAP[tls_id]["red_ns"], PHASE_MAP[tls_id]["red_ew"]]
            if is_red_phase and time_in_phase >= RED_TIME_CONSERVATIVE:
                next_phase = (current_phase + 1) % 6
                try:
                    traci.trafficlight.setPhase(tls_id, next_phase)
                    state["phase_start_time"] = step
                except traci.TraCIException:
                    continue

def get_queue_length(lanes: List[str]) -> int:
    """Calcula o total de veículos parados em uma lista de faixas."""
    total_queue = 0
    for lane_id in lanes:
        try:
            total_queue += traci.lane.getLastStepHaltingNumber(lane_id)
        except traci.TraCIException:
            continue
    return total_queue

def get_throughput(lanes: List[str]) -> int:
    """Calcula o throughput em uma lista de faixas."""
    total_throughput = 0
    for lane_id in lanes:
        try:
            total_throughput += traci.lane.getLastStepVehicleNumber(lane_id)
        except traci.TraCIException:
            continue
    return total_throughput

def initialize_tls_states() -> None:
    """Inicializa o estado de cada semáforo disponível"""
    global TLS_IDS, PHASE_MAP
    
    # Atualiza a lista de semáforos disponíveis
    TLS_IDS = get_available_tls_ids()
    print(f"Semáforos identificados: {TLS_IDS}")
    
    # Gera o mapeamento de fases apenas para semáforos disponíveis
    PHASE_MAP = generate_phase_map()
    
    # Inicializa os estados apenas para semáforos disponíveis
    for tls_id in TLS_IDS:
        try:
            current_phase = traci.trafficlight.getPhase(tls_id)
            tls_states[tls_id] = {
                "current_phase_index": current_phase,
                "phase_start_time": 0
            }
        except traci.TraCIException:
            print(f"Aviso: Semáforo {tls_id} não encontrado, pulando...")
            continue

def collect_region_data() -> Dict[str, Dict[str, int]]:
    """Coleta dados apenas das regiões com semáforos existentes"""
    region_data = {}
    
    for tls_id in TLS_IDS:
        try:
            controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
            lanes_ns = [lane for lane in controlled_lanes if 'ns' in lane]
            lanes_ew = [lane for lane in controlled_lanes if 'ew' in lane]
        except traci.TraCIException:
            continue
            
        region_name = tls_id
        
        region_data[region_name] = {
            "stopped_vehicles": get_queue_length(lanes_ns + lanes_ew),
            "throughput": get_throughput(lanes_ns + lanes_ew),
            "waiting_time_ns": 0,
            "waiting_time_ew": 0
        }
    
    return region_data

def collect_step_data(step: int, controller: TrafficLightController) -> Dict[str, Any]:
    """Coleta dados de um passo de simulação."""
    total_vehicles = traci.vehicle.getIDCount()
    vehicle_ids = traci.vehicle.getIDList()
    total_wait_time = sum(traci.vehicle.getWaitingTime(veh_id) or 0 for veh_id in vehicle_ids)
    
    # Calcular tempo de espera por região
    region_data = {}
    for tls_id in list(tls_states.keys()):
        try:
            # Verifica se o semáforo ainda existe
            if tls_id not in TLS_IDS:
                continue
                
            controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
            lanes_ns = [lane for lane in controlled_lanes if 'ns' in lane]
            lanes_ew = [lane for lane in controlled_lanes if 'ew' in lane]
        except traci.TraCIException:
            # Remove semáforo inacessível
            tls_states.pop(tls_id, None)
            continue
            
        region_name = tls_id
        
        region_data[region_name] = {
            "stopped_vehicles": get_queue_length(lanes_ns + lanes_ew),
            "throughput": get_throughput(lanes_ns + lanes_ew),
            "waiting_time_ns": int(controller.get_total_waiting_time(lanes_ns)),
            "waiting_time_ew": int(controller.get_total_waiting_time(lanes_ew))
        }

    # Calcular métricas adicionais
    total_stopped_vehicles = sum(region["stopped_vehicles"] for region in region_data.values())
    congestion_level = total_stopped_vehicles / total_vehicles if total_vehicles > 0 else 0
    
    # Calcular emissões estimadas
    co2_emission = total_vehicles * CO2_PER_CAR_PER_STEP_G
    fuel_consumption = total_vehicles * FUEL_CONSUMPTION_PER_STEP
    
    # Calcular tempo perdido
    time_loss = total_wait_time * 1.5
    
    # Calcular eficiência dos semáforos
    efficiency_metrics = {}
    for tls_id in list(tls_states.keys()):
        if tls_id in TLS_IDS:
            try:
                current_phase = traci.trafficlight.getPhase(tls_id)
                is_green = current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["green_ew"]]
                efficiency_metrics[tls_id] = {
                    "is_green": is_green,
                    "time_in_phase": step - tls_states[tls_id]["phase_start_time"]
                }
            except traci.TraCIException:
                continue
    
    return {
        "step": step,
        "total_vehicles_network": total_vehicles,
        "total_system_waiting_time": total_wait_time,
        "teleported_vehicles_this_step": traci.simulation.getStartingTeleportNumber(),
        "completed_trips": traci.simulation.getArrivedNumber(),
        "avg_stopped_vehicle_wait_time_sec": total_wait_time / total_vehicles if total_vehicles > 0 else 0,
        "co2_emission": co2_emission,
        "fuel_consumption": fuel_consumption,
        "time_loss": time_loss,
        "congestion_level": congestion_level,
        "signal_efficiency": efficiency_metrics,
        "region_data": region_data
    }

def run_simulation(mode: str, steps: int, output_path: str) -> str:
    """Executa a simulação completa."""
    
    os.makedirs(output_path, exist_ok=True)
    
    sumo_cmd = [
        SUMO_BINARY, "-c", SUMO_CONFIG_FILE,
        "--tripinfo-output", os.path.join(output_path, "tripinfo.xml"),
        "--emission-output", os.path.join(output_path, "emission.xml"),
        "--quit-on-end"
    ]

    try:
        traci.start(sumo_cmd)
    except traci.FatalTraCIError as e:
        print(f"ERRO fatal ao iniciar o SUMO: {e}")
        return ""

    controller = TrafficLightController()
    initialize_tls_states()  # Inicializa semáforos após conectar com o SUMO
    step = 0
    simulation_data = []
    
    try:
        while step < steps:
            if traci.simulation.getMinExpectedNumber() <= 0:
                break

            traci.simulationStep()
            controller.control_lights(step, mode)
            
            if step % 60 == 0:  # Coletar dados a cada minuto
                step_data = collect_step_data(step, controller)
                simulation_data.append(step_data)
            
            step += 1
            
            if step % 100 == 0:
                print(f"Progresso: {step}/{steps} passos ({step/steps*100:.1f}%)")
    
    except traci.TraCIException as e:
        print(f"\nERRO durante a simulação: {e}")
    
    finally:
        traci.close()
        
        # Adicionar metadados à simulação
        simulation_metadata = {
            "simulation_mode": mode,
            "requested_steps": steps,
            "actual_steps": step,
            "simulation_date": datetime.datetime.now().isoformat(),
            "data_collection_interval": 60,
            "tls_ids_available": TLS_IDS,
            "controller_parameters": {
                "dynamic": {
                    "MIN_GREEN_TIME_DYNAMIC": MIN_GREEN_TIME_DYNAMIC,
                    "MAX_GREEN_TIME_DYNAMIC": MAX_GREEN_TIME_DYNAMIC,
                    "YELLOW_TIME_DYNAMIC": YELLOW_TIME_DYNAMIC,
                    "RED_TIME_DYNAMIC": RED_TIME_DYNAMIC,
                    "WAITING_TIME_THRESHOLD": WAITING_TIME_THRESHOLD
                },
                "conservative": {
                    "GREEN_TIME_CONSERVATIVE": GREEN_TIME_CONSERVATIVE,
                    "YELLOW_TIME_CONSERVATIVE": YELLOW_TIME_CONSERVATIVE,
                    "RED_TIME_CONSERVATIVE": RED_TIME_CONSERVATIVE
                }
            }
        }
        
        data_file_path = os.path.join(output_path, "simulation_dashboard_data.json")
        
        output_data = {
            "metadata": simulation_metadata,
            "simulation_data": simulation_data
        }
        
        with open(data_file_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4)
        
        return data_file_path

def run_both_modes(steps: int) -> None:
    """Executa ambos os modos (para comparação)"""
    print("\n=== INICIANDO MODO DINÂMICO (OIT) ===")
    run_simulation('dynamic', steps, os.path.join(SIMULATION_OUTPUT_DIR, "dynamic_output"))
    
    print("\n=== INICIANDO MODO CONSERVADOR ===")
    run_simulation('conservative', steps, os.path.join(SIMULATION_OUTPUT_DIR, "conservative_output"))

def main():
    """Função principal para interação com o terminal."""
    parser = argparse.ArgumentParser(description="SUMO Traffic Light Control Simulation")
    parser.add_argument("--steps", type=int, default=2500, help="Número de passos da simulação.")
    parser.add_argument("--mode", choices=['dynamic', 'conservative', 'compare'], help="Modo de simulação (dynamic, conservative ou compare).")
    parser.add_argument("--output", type=str, help="Diretório de saída para os arquivos da simulação.")
    
    args = parser.parse_args()

    if args.mode == 'compare':
        if args.output:
            print("Aviso: O argumento --output é ignorado no modo compare. Usando diretórios padrão.")
        run_both_modes(args.steps)
    elif args.mode:
        # Para modos individuais, use o diretório fornecido ou o padrão
        output_dir = args.output if args.output else os.path.join(SIMULATION_OUTPUT_DIR, f"{args.mode}_output")
        run_simulation(args.mode, args.steps, output_dir)
    else:
        # Modo interativo
        print("=== Simulador de Tráfego SUMO ===")
        print("Opções:")
        print("1 - Modo Dinâmico (OIT)")
        print("2 - Modo Conservador (Tempo Fixo)")
        print("3 - Executar Ambos os Modos (Para Comparação)")
        print("4 - Sair")
        
        choice = input("Escolha uma opção (1-4): ").strip()
        
        if choice == "1":
            steps = int(input("Tempo de simulação (passos): "))
            run_simulation('dynamic', steps, os.path.join(SIMULATION_OUTPUT_DIR, "dynamic_output"))
        elif choice == "2":
            steps = int(input("Tempo de simulação (passos): "))
            run_simulation('conservative', steps, os.path.join(SIMULATION_OUTPUT_DIR, "conservative_output"))
        elif choice == "3":
            steps = int(input("Tempo de simulação (passos): "))
            run_both_modes(steps)
        elif choice == "4":
            print("Saindo...")
        else:
            print("Opção inválida!")

if __name__ == "__main__":
    main()
import os
import sys
import traci
import json
import argparse
import time
from datetime import datetime

# --- Configuração do SUMO_HOME ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("ERRO: A variável de ambiente SUMO_HOME não está definida.")

# --- Constantes e Configurações ---
SUMO_CONFIG_FILE = "grid.sumocfg"
SUMO_BINARY = "sumo-gui"
SIMULATION_CHUNK_SIZE = 3000 # <--- MODIFICADO: Simular em blocos de 3000 passos
TLS_IDS = ["B1", "C1"]

# --- Constantes dos Modos de Semáforo ---
GREEN_TIME_FIXED = 30
YELLOW_TIME_FIXED = 4
MIN_GREEN_TIME_DYNAMIC = 15
MAX_GREEN_TIME_DYNAMIC = 60
YELLOW_TIME_DYNAMIC = 4
QUEUE_THRESHOLD = 10

# Mapeamento de Fases
PHASE_MAP = {
    "B1": {
        "lanes_ns": ["B2B1_0", "B0B1_0"], "lanes_ew": ["C1B1_0", "A1B1_0"],
        "green_ns": 0, "yellow_ns": 1, "green_ew": 2, "yellow_ew": 3
    },
    "C1": {
        "lanes_ns": ["C2C1_0", "C0C1_0"], "lanes_ew": ["D1C1_0", "B1C1_0"],
        "green_ns": 0, "yellow_ns": 1, "green_ew": 2, "yellow_ew": 3
    }
}

# Estrutura para Manter o Estado dos Semáforos
tls_states = {}

def get_queue_length(lanes):
    """Calcula o total de veículos parados em uma lista de faixas."""
    total_queue = 0
    for lane_id in lanes:
        try:
            total_queue += traci.lane.getLastStepHaltingNumber(lane_id)
        except traci.exceptions.TraCIException:
            pass
    return total_queue

def initialize_tls_states():
    """Inicializa o estado de cada semáforo no início da simulação."""
    for tls_id in TLS_IDS:
        tls_states[tls_id] = {
            "current_phase_index": 0,
            "phase_start_time": 0
        }

def control_traffic_lights_conventional(step):
    """Lógica de controle para semáforos com tempo fixo."""
    for tls_id in TLS_IDS:
        state = tls_states[tls_id]
        time_in_phase = step - state["phase_start_time"]
        current_phase = traci.trafficlight.getPhase(tls_id)

        is_green_phase = current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["green_ew"]]
        if is_green_phase and time_in_phase >= GREEN_TIME_FIXED:
            traci.trafficlight.setPhase(tls_id, current_phase + 1)
            state["phase_start_time"] = step

        is_yellow_phase = current_phase in [PHASE_MAP[tls_id]["yellow_ns"], PHASE_MAP[tls_id]["yellow_ew"]]
        if is_yellow_phase and time_in_phase >= YELLOW_TIME_FIXED:
            next_phase = (current_phase + 1) % 4
            traci.trafficlight.setPhase(tls_id, next_phase)
            state["phase_start_time"] = step

def control_traffic_lights_dynamic(step):
    """Lógica de controle adaptativa, conforme o TCC."""
    for tls_id in TLS_IDS:
        if tls_id not in PHASE_MAP: continue
        
        state = tls_states[tls_id]
        time_in_phase = step - state["phase_start_time"]
        current_phase = traci.trafficlight.getPhase(tls_id)
        
        is_ns_flow = current_phase == PHASE_MAP[tls_id]["green_ns"]
        
        if is_ns_flow:
            conflicting_lanes = PHASE_MAP[tls_id]["lanes_ew"]
            next_yellow_phase = PHASE_MAP[tls_id]["yellow_ns"]
        else:
            conflicting_lanes = PHASE_MAP[tls_id]["lanes_ns"]
            next_yellow_phase = PHASE_MAP[tls_id]["yellow_ew"]
            
        is_green_phase = current_phase in [PHASE_MAP[tls_id]["green_ns"], PHASE_MAP[tls_id]["green_ew"]]
        if is_green_phase and time_in_phase >= MIN_GREEN_TIME_DYNAMIC:
            queue_in_conflict = get_queue_length(conflicting_lanes)
            
            time_exceeded = time_in_phase >= MAX_GREEN_TIME_DYNAMIC
            pressure_high = queue_in_conflict >= QUEUE_THRESHOLD
            
            if time_exceeded or pressure_high:
                traci.trafficlight.setPhase(tls_id, next_yellow_phase)
                state["phase_start_time"] = step

        is_yellow_phase = current_phase in [PHASE_MAP[tls_id]["yellow_ns"], PHASE_MAP[tls_id]["yellow_ew"]]
        if is_yellow_phase and time_in_phase >= YELLOW_TIME_DYNAMIC:
            next_green_phase = (current_phase + 1) % 4
            traci.trafficlight.setPhase(tls_id, next_green_phase)
            state["phase_start_time"] = step


def run_simulation(mode):
    """Executa a simulação completa de forma interativa."""
    sumo_cmd = [
        SUMO_BINARY, "-c", SUMO_CONFIG_FILE,
        "--tripinfo-output", "tripinfo.xml",
        "--emission-output", "emission.xml",
        "--quit-on-end"
    ]

    try:
        traci.start(sumo_cmd)
        print(f"SUMO iniciado com sucesso no modo: {mode}")
    except traci.exceptions.FatalTraCIError as e:
        print(f"ERRO fatal ao iniciar o SUMO. Verifique a configuração e o PATH. Detalhes: {e}")
        return

    initialize_tls_states()
    step = 0
    simulation_data = []
    
    # <--- NOVO: Loop de simulação interativo ---
    try:
        while True:
            # Verifica se ainda há carros na simulação
            if traci.simulation.getMinExpectedNumber() <= 0:
                print("Todos os veiculos completaram suas viagens. Simulacao encerrada.")
                break

            print(f"\nIniciando bloco de simulacao de {SIMULATION_CHUNK_SIZE} passos (50 minutos)...")
            
            chunk_end_step = step + SIMULATION_CHUNK_SIZE
            
            while step < chunk_end_step:
                # Condição de parada caso os carros acabem no meio do bloco
                if traci.simulation.getMinExpectedNumber() <= 0:
                    break
                
                traci.simulationStep()
                
                if mode == 'dynamic':
                    control_traffic_lights_dynamic(step)
                elif mode == 'conventional':
                    control_traffic_lights_conventional(step)
                
                # Coleta de dados (a cada 60s)
                if step % 60 == 0:
                    total_vehicles = traci.vehicle.getIDCount()
                    total_wait_time = sum(traci.vehicle.getWaitingTime(v_id) for v_id in traci.vehicle.getIDList())
                    
                    step_data = {
                        "step": step,
                        "total_vehicles_network": total_vehicles,
                        "total_system_waiting_time": total_wait_time,
                        "teleported_vehicles_this_step": traci.simulation.getStartingTeleportNumber(),
                        "completed_trips": traci.simulation.getArrivedNumber(),
                        "avg_stopped_vehicle_wait_time_sec": total_wait_time / total_vehicles if total_vehicles > 0 else 0,
                        "region_data": {
                            "Norte": {"stopped_vehicles": get_queue_length(PHASE_MAP.get("C1", {}).get("lanes_ns", []))},
                            "Sul": {"stopped_vehicles": 0},
                            "Leste": {"stopped_vehicles": get_queue_length(PHASE_MAP.get("B1", {}).get("lanes_ew", []))},
                            "Oeste": {"stopped_vehicles": 0}
                        }
                    }
                    simulation_data.append(step_data)
                
                step += 1

            # --- Interação com o usuário ---
            print(f"\n--- Bloco Concluido no passo {step} ---")
            
            # Se a simulação acabou por falta de carros, sai do loop
            if traci.simulation.getMinExpectedNumber() <= 0:
                print("Todos os veiculos completaram suas viagens. Simulacao encerrada.")
                break

            user_choice = input("Deseja simular por mais 50 minutos? (s/n): ").lower()
            if user_choice != 's':
                break
    
    except traci.exceptions.TraCIException as e:
        print(f"\nERRO INESPERADO DURANTE A SIMULACAO: {e}")
        print("A simulacao foi interrompida. Verifique os arquivos de rota (.rou.xml) e a malha.")
    
    finally:
        # Garante que a conexão seja fechada e os dados salvos
        traci.close()
        print("\nConexao com o SUMO fechada.")
        
        output_dir = "dashboard_output"
        os.makedirs(output_dir, exist_ok=True)
        data_file_path = os.path.join(output_dir, "simulation_dashboard_data.json") 
        
        with open(data_file_path, "w", encoding="utf-8") as f:
            json.dump(simulation_data, f, indent=4)
        print(f"Dados finais da simulacao salvos em: {data_file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Controlador de Semáforos para Simulação SUMO.")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=['dynamic', 'conventional'], 
        default='dynamic',
        help="Modo de operação do semáforo."
    )
    args = parser.parse_args()

    if not os.path.exists(SUMO_CONFIG_FILE):
        print(f"ERRO: Arquivo de configuração '{SUMO_CONFIG_FILE}' não encontrado!")
    else:
        run_simulation(args.mode)
import os
import sys
import traci
import random
import json
import argparse
import time
from datetime import datetime
import math
import subprocess

# --- Configuração do SUMO_HOME ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    # Tenta encontrar o SUMO em locais comuns
    possible_paths = [
        "C:\\Program Files\\Eclipse\\Sumo",
        "C:\\Program Files (x86)\\Eclipse\\Sumo", 
        os.path.expanduser("~/Desktop/SUMO"),
        "I:\\UNIP\\TCC\\SUMO"
    ]
    
    for path in possible_paths:
        tools_path = os.path.join(path, 'tools')
        if os.path.exists(tools_path):
            sys.path.append(tools_path)
            os.environ['SUMO_HOME'] = path
            break
    else:
        sys.exit("ERRO: A variável de ambiente SUMO_HOME não está definida e não foi possível encontrar o SUMO.")

# --- Configuração de Diretórios do Projeto ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = "I:\\UNIP\\TCC\\SUMO"

if not os.path.exists(PROJECT_DIR):
    print(f"AVISO: Diretório do projeto '{PROJECT_DIR}' não encontrado. Usando diretório do script: {SCRIPT_DIR}")
    PROJECT_DIR = SCRIPT_DIR

# --- Parâmetros de Configuração ---
SUMO_CONFIG_FILE = os.path.join(PROJECT_DIR, "grid.sumocfg")
SUMO_BINARY = "sumo-gui"
TOTAL_SIMULATION_STEPS = 3600

# --- IDs dos Semáforos ---
TLS_IDS = ["B0", "B1", "B2", "C0", "C1", "C2", "D1", "D2"]

# --- Mapeamento de Fases e Lanes ---
PHASE_MAPPING = {
    "B1": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["B2B1_0", "B0B1_0"],
        "lanes_ew": ["C1B1_0", "A1B1_0"]
    },
    # Adicione outros semáforos aqui seguindo o mesmo padrão
    "B0": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["B1B0_0", "B3B0_0"],
        "lanes_ew": ["C0B0_0", "A0B0_0"]
    },
    "B2": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["B1B2_0", "B3B2_0"],
        "lanes_ew": ["C2B2_0", "A2B2_0"]
    },
    "C0": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["C1C0_0", "C3C0_0"],
        "lanes_ew": ["B0C0_0", "D0C0_0"]
    },
    "C1": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["C0C1_0", "C2C1_0"],
        "lanes_ew": ["B1C1_0", "D1C1_0"]
    },
    "C2": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["C1C2_0", "C3C2_0"],
        "lanes_ew": ["B2C2_0", "D2C2_0"]
    },
    "D1": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["D0D1_0", "D2D1_0"],
        "lanes_ew": ["C1D1_0", "E1D1_0"]
    },
    "D2": {
        "green_ns": 0,
        "yellow_ns": 1,
        "red_ew": 2,
        "green_ew": 3,
        "yellow_ew": 4,
        "red_ns": 5,
        "lanes_ns": ["D1D2_0", "D3D2_0"],
        "lanes_ew": ["C2D2_0", "E2D2_0"]
    }
}

def check_sumo_installation():
    """Verifica se o SUMO está instalado corretamente"""
    try:
        # Tenta executar o SUMO para verificar a instalação
        result = subprocess.run([SUMO_BINARY, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"SUMO encontrado: {result.stdout.splitlines()[0] if result.stdout else 'Versão desconhecida'}")
            return True
        else:
            print(f"SUMO retornou erro: {result.stderr}")
            return False
    except FileNotFoundError:
        print(f"ERRO: {SUMO_BINARY} não encontrado. Verifique a instalação do SUMO.")
        return False
    except Exception as e:
        print(f"ERRO ao verificar instalação do SUMO: {e}")
        return False

def get_queue_length(lanes):
    """Calcula o tamanho da fila total para um conjunto de lanes."""
    halting_count = 0
    for lane in lanes:
        try:
            halting_count += traci.lane.getLastStepHaltingNumber(lane)
        except:
            pass  # Ignora lanes que não existem
    return halting_count

def get_waiting_time(lanes):
    """Calcula o tempo de espera acumulado para um conjunto de lanes."""
    waiting_time = 0.0
    for lane in lanes:
        try:
            waiting_time += traci.lane.getWaitingTime(lane)
        except:
            pass  # Ignora lanes que não existem
    return waiting_time

def run_simulation(mode):
    """Executa a simulação com o modo de controle especificado."""
    # Verifica se o SUMO está instalado
    if not check_sumo_installation():
        return
    
    # Verifica se os arquivos necessários existem
    if not os.path.exists(SUMO_CONFIG_FILE):
        print(f"ERRO: Arquivo de configuração '{SUMO_CONFIG_FILE}' não encontrado!")
        print("Verifique se o arquivo grid.sumocfg existe no diretório do projeto.")
        return
    
    sumo_cmd = [SUMO_BINARY, "-c", SUMO_CONFIG_FILE, "--step-length", "1.0"]
    
    if mode == 'dynamic':
        # Usa uma porta fixa para evitar problemas de conexão
        port = 8813
        sumo_cmd.extend(["--remote-port", str(port)])
        print(f"Iniciando SUMO no modo dinâmico na porta {port}")
    else:
        # Para o modo conservador
        sumo_cmd.append("--quit-on-end")
        print("Iniciando SUMO no modo conservador (INTENCIONALMENTE INEFICIENTE)")

    # Adiciona opções para debugging
    sumo_cmd.extend(["--verbose", "--no-step-log"])

    # Aumenta o tempo de espera para conexão
    traci.setConnectionTimeout(10000)  # 10 segundos

    try:
        print("Iniciando SUMO...")
        traci.start(sumo_cmd, label="simulation1")
        print("SUMO iniciado com sucesso. Conectado ao TraCI.")
        
        # Verifica a conexão
        if not traci.is_connected("simulation1"):
            print("ERRO: Não foi possível estabelecer conexão com o SUMO.")
            return
            
    except traci.exceptions.FatalTraCIError as e:
        print(f"ERRO fatal do TraCI ao iniciar o SUMO: {e}")
        return
    except Exception as e:
        print(f"ERRO inesperado ao iniciar o SUMO: {e}")
        import traceback
        traceback.print_exc()
        return

    step = 0
    SIMULATION_DATA = []
    
    # Variáveis para controle de ineficiência no modo conservador
    conservative_inefficiency_counter = 0
    last_phase_change = {tls_id: 0 for tls_id in TLS_IDS}

    try:
        while step < TOTAL_SIMULATION_STEPS and traci.simulation.getMinExpectedNumber() > 0:
            try:
                traci.simulationStep()
                step += 1
                
                # Exibe progresso a cada 100 passos
                if step % 100 == 0:
                    print(f"Passo {step}/{TOTAL_SIMULATION_STEPS}")
                
                # Lógica para o modo Dinâmico (eficiente)
                if mode == 'dynamic':
                    for tls_id in TLS_IDS:
                        if tls_id in PHASE_MAPPING:
                            try:
                                current_phase = traci.trafficlight.getPhase(tls_id)
                                lanes_ns = PHASE_MAPPING[tls_id].get("lanes_ns", [])
                                lanes_ew = PHASE_MAPPING[tls_id].get("lanes_ew", [])
                                
                                queue_ns = get_queue_length(lanes_ns)
                                queue_ew = get_queue_length(lanes_ew)
                                
                                # Lógica adaptativa eficiente
                                if current_phase == PHASE_MAPPING[tls_id]["green_ns"] and queue_ew > queue_ns * 2:
                                    traci.trafficlight.setPhase(tls_id, PHASE_MAPPING[tls_id]["yellow_ns"])
                                    traci.trafficlight.setPhaseDuration(tls_id, 3)
                                elif current_phase == PHASE_MAPPING[tls_id]["green_ew"] and queue_ns > queue_ew * 2:
                                    traci.trafficlight.setPhase(tls_id, PHASE_MAPPING[tls_id]["yellow_ew"])
                                    traci.trafficlight.setPhaseDuration(tls_id, 3)
                            except Exception as e:
                                print(f"Erro ao processar semáforo {tls_id}: {e}")
                
                # Lógica para o modo Conservador (INTENCIONALMENTE INEFICIENTE)
                elif mode == 'conservative':
                    conservative_inefficiency_counter += 1
                    
                    # A cada 10 passos, introduz ineficiências
                    if conservative_inefficiency_counter % 10 == 0:
                        for tls_id in TLS_IDS:
                            if tls_id in PHASE_MAPPING:
                                try:
                                    current_phase = traci.trafficlight.getPhase(tls_id)
                                    current_duration = traci.trafficlight.getPhaseDuration(tls_id)
                                    
                                    # 1. Tempos de fase fixos muito longos
                                    if current_duration < 60:  # Se a fase atual é curta
                                        # Estende dramaticamente o tempo da fase verde
                                        traci.trafficlight.setPhaseDuration(tls_id, 60)
                                    
                                    # 2. Ignora completamente as condições de tráfego
                                    lanes_ns = PHASE_MAPPING[tls_id].get("lanes_ns", [])
                                    lanes_ew = PHASE_MAPPING[tls_id].get("lanes_ew", [])
                                    
                                    queue_ns = get_queue_length(lanes_ns)
                                    queue_ew = get_queue_length(lanes_ew)
                                    
                                    # 3. Mudanças de fase aleatórias e ineficientes
                                    if random.random() < 0.05:  # 5% de chance a cada 10 passos
                                        # Muda para uma fase aleatória, independente do tráfego
                                        new_phase = random.randint(0, 5)
                                        traci.trafficlight.setPhase(tls_id, new_phase)
                                        traci.trafficlight.setPhaseDuration(tls_id, random.randint(30, 90))
                                        last_phase_change[tls_id] = step
                                    
                                    # 4. Mantém fases verdes mesmo quando não há tráfego
                                    if (step - last_phase_change[tls_id]) > 100:  # A cada 100 passos sem mudança
                                        if queue_ns == 0 and queue_ew > 0 and current_phase == PHASE_MAPPING[tls_id]["green_ns"]:
                                            # Mantém verde na direção vazia por mais tempo
                                            traci.trafficlight.setPhaseDuration(tls_id, current_duration + 30)
                                        elif queue_ew == 0 and queue_ns > 0 and current_phase == PHASE_MAPPING[tls_id]["green_ew"]:
                                            # Mantém verde na direção vazia por mais tempo
                                            traci.trafficlight.setPhaseDuration(tls_id, current_duration + 30)
                                    
                                    # 5. Introduz atrasos desnecessários entre fases
                                    if current_phase in [PHASE_MAPPING[tls_id]["yellow_ns"], PHASE_MAPPING[tls_id]["yellow_ew"]]:
                                        # Estende o tempo do amarelo desnecessariamente
                                        traci.trafficlight.setPhaseDuration(tls_id, 10)
                                        
                                except Exception as e:
                                    print(f"Erro ao processar semáforo {tls_id}: {e}")
                
                # Coleta de dados a cada 10 passos
                if step % 10 == 0:
                    step_data = {
                        "step": step,
                        "timestamp": datetime.now().isoformat(),
                        "metrics": {
                            "completed_trips": traci.simulation.getArrivedNumber(),
                            "teleported_vehicles": traci.simulation.getStartingTeleportNumber(),
                            "total_waiting_time": traci.simulation.getWaitingTime(),
                            "mode": mode  # Adiciona o modo aos dados para análise
                        },
                        "tls_data": []
                    }
                    
                    for tls_id in TLS_IDS:
                        if tls_id in PHASE_MAPPING:
                            lanes_ns = PHASE_MAPPING[tls_id].get("lanes_ns", [])
                            lanes_ew = PHASE_MAPPING[tls_id].get("lanes_ew", [])
                            
                            queue_ns = get_queue_length(lanes_ns)
                            queue_ew = get_queue_length(lanes_ew)
                            
                            wait_time_ns = get_waiting_time(lanes_ns)
                            wait_time_ew = get_waiting_time(lanes_ew)

                            step_data["tls_data"].append({
                                "tls_id": tls_id,
                                "queue_N": queue_ns,
                                "queue_S": 0,
                                "queue_E": queue_ew,
                                "queue_W": 0,
                                "wait_time_N": wait_time_ns,
                                "wait_time_S": 0,
                                "wait_time_E": wait_time_ew,
                                "wait_time_W": 0,
                            })

                    SIMULATION_DATA.append(step_data)
            
            except traci.exceptions.TraCIException as e:
                print(f"ERRO do TraCI durante a simulação: {e}")
                break
                
    except Exception as e:
        print(f"ERRO inesperado na simulação: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if traci.is_connected("simulation1"):
                traci.close("simulation1")
                print("Conexão TraCI fechada.")
        except:
            pass
        
        # Salvando os dados
        output_dir_for_data = os.path.join(PROJECT_DIR, "dashboard_output")
        if not os.path.exists(output_dir_for_data):
            os.makedirs(output_dir_for_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_file_path = os.path.join(output_dir_for_data, f"simulation_dashboard_data_{mode}_{timestamp}.json")
        
        try:
            with open(data_file_path, "w", encoding="utf-8") as f:
                json.dump(SIMULATION_DATA, f, indent=4)
            print(f"Dados da simulação salvos em {data_file_path}")
            
            # Também salva um resumo dos resultados para comparação fácil
            summary = {
                "mode": mode,
                "total_steps": step,
                "completed_trips": SIMULATION_DATA[-1]["metrics"]["completed_trips"] if SIMULATION_DATA else 0,
                "total_waiting_time": SIMULATION_DATA[-1]["metrics"]["total_waiting_time"] if SIMULATION_DATA else 0,
                "teleported_vehicles": SIMULATION_DATA[-1]["metrics"]["teleported_vehicles"] if SIMULATION_DATA else 0,
                "timestamp": timestamp
            }
            
            summary_path = os.path.join(output_dir_for_data, f"simulation_summary_{mode}_{timestamp}.json")
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=4)
            print(f"Resu
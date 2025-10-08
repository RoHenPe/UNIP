# -*- coding: utf-8 -*-
"""
Módulo que contém a inteligência para controlo de semáforos.

PILAR DE QUALIDADE: Extensibilidade, Coesão
DESCRIÇÃO: Define uma interface comum (BaseController) e implementações
específicas para cada modo de controlo, facilitando a adição de novas lógicas de IA.
"""

import traci
from typing import List, Dict, Any, Set
from abc import ABC, abstractmethod
from tcc_sumo.utils.helpers import get_logger

logger = get_logger("TrafficController")

class BaseController(ABC):
    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def manage_traffic_lights(self, step: int) -> None:
        pass

class StaticController(BaseController):
    """
    Controlador para o modo Estático. Não realiza ações, pois os tempos
    são fixos e geridos diretamente pelo SUMO.
    """
    def setup(self):
        logger.info("Controlador Estático inicializado. Nenhuma ação dinâmica será tomada.")

    def manage_traffic_lights(self, step: int) -> None:
        # Ponto de eficiência: Nenhuma chamada ao TraCI é necessária a cada passo.
        pass

class AdaptiveController(BaseController):
    """
    Controlador Adaptativo que ajusta os semáforos com base no fluxo de tráfego.
    """
    def __init__(self, switch_threshold: int = 5, min_phase_time: int = 10):
        # --- REVISÃO 1: PARÂMETROS MAIS CONSERVADORES ---
        # PILAR DE QUALIDADE: Fiabilidade
        # DESCRIÇÃO: Aumentamos o limiar de troca (switch_threshold) para 5 e adicionamos
        # um tempo mínimo em fase (min_phase_time) de 10 segundos. Isto torna a IA
        # menos "nervosa", evitando trocas de sinal demasiado rápidas que, como visto nos logs,
        # podem desestabilizar o trânsito e causar congestionamento.
        self.traffic_light_ids: List[str] = []
        self.traffic_light_states: Dict[str, Dict[str, Any]] = {}
        self.SWITCH_THRESHOLD = switch_threshold
        self.MIN_PHASE_TIME = min_phase_time
        logger.info(f"Controlador Adaptativo instanciado com limiar de troca de {switch_threshold} veículos e tempo mínimo de fase de {min_phase_time}s.")

    def setup(self):
        try:
            self.traffic_light_ids = traci.trafficlight.getIDList()
            for tl_id in self.traffic_light_ids:
                self.traffic_light_states[tl_id] = {
                    'current_phase_index': traci.trafficlight.getPhase(tl_id),
                    'last_phase_change_step': 0
                }
            logger.info(f"Controlador Adaptativo configurado para {len(self.traffic_light_ids)} semáforos.")
        except traci.TraCIException as e:
            logger.critical(f"Falha CRÍTICA ao configurar o AdaptiveController: {e}")
            raise

    def manage_traffic_lights(self, step: int) -> None:
        if not self.traffic_light_ids:
            return

        for tl_id in self.traffic_light_ids:
            try:
                state = self.traffic_light_states[tl_id]
                logics = traci.trafficlight.getAllProgramLogics(tl_id)
                if not logics: continue

                current_logic = logics[0]
                current_phase_index = state['current_phase_index']
                current_phase = current_logic.phases[current_phase_index]
                time_in_phase = step - state['last_phase_change_step']

                is_green_phase = 'g' in current_phase.state.lower()

                # --- REVISÃO 2: LÓGICA DE DECISÃO MAIS ROBUSTA ---
                # A IA só atua em fases verdes e após um tempo mínimo ter passado.
                # A fase amarela é inviolável para garantir a segurança.
                if not is_green_phase or time_in_phase < self.MIN_PHASE_TIME:
                    continue

                should_switch = False
                # 1. Forçar a troca se o tempo máximo da fase for atingido.
                if time_in_phase > current_phase.maxDur:
                    should_switch = True
                    logger.debug(f"Semáforo {tl_id}: Troca forçada por tempo máximo atingido ({time_in_phase}s).")
                else:
                    # 2. Avaliar a troca com base na procura.
                    green_lanes = self._get_green_lanes_for_phase(tl_id, current_phase_index)
                    cars_on_green = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in green_lanes)

                    # Analisa a procura na PRÓXIMA fase que tiver um sinal verde
                    next_green_phase_index = self._find_next_green_phase(current_logic, current_phase_index)
                    if next_green_phase_index is not None:
                        next_green_lanes = self._get_green_lanes_for_phase(tl_id, next_green_phase_index)
                        cars_on_next = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in next_green_lanes)

                        # Troca apenas se a próxima fase tiver uma procura significativamente maior.
                        if cars_on_next > cars_on_green + self.SWITCH_THRESHOLD:
                            should_switch = True
                            logger.info(f"Semáforo {tl_id}: Decidiu trocar. Procura atual: {cars_on_green}, Próxima procura: {cars_on_next}.")
                        elif cars_on_green > 0:
                            logger.debug(f"Semáforo {tl_id}: Decidiu estender. Procura atual: {cars_on_green}.")

                if should_switch:
                    next_phase_index = (current_phase_index + 1) % len(current_logic.phases)
                    traci.trafficlight.setPhase(tl_id, next_phase_index)
                    state['current_phase_index'] = next_phase_index
                    state['last_phase_change_step'] = step

            except traci.TraCIException as e:
                logger.error(f"Erro ao controlar semáforo {tl_id} no passo {step}: {e}")

    def _find_next_green_phase(self, logic, current_index: int) -> int | None:
        """Encontra o índice da próxima fase que contenha um sinal verde."""
        num_phases = len(logic.phases)
        for i in range(1, num_phases):
            next_index = (current_index + i) % num_phases
            if 'g' in logic.phases[next_index].state.lower():
                return next_index
        return None

    def _get_green_lanes_for_phase(self, tl_id: str, phase_index: int) -> List[str]:
        lanes: Set[str] = set()
        links = traci.trafficlight.getControlledLinks(tl_id)
        if not links: return []

        program_logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
        phase_state = program_logic.phases[phase_index].state

        for i, link_group in enumerate(links):
            if i < len(phase_state) and phase_state[i].lower() in ('g', 'G'):
                for link in link_group:
                    lanes.add(link[0]) # Adiciona a lane de origem
        return list(lanes)
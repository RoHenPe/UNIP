import traci
from typing import List, Dict, Any, Set
from tcc_sumo.utils.helpers import get_logger

logger = get_logger("TrafficController")

class StaticController:
    """Controlador para o modo Estático, que não realiza ações dinâmicas."""
    def __init__(self):
        logger.info("Controlador Estático inicializado.")

    def manage_traffic_lights(self, step: int) -> None:
        """Nenhuma ação necessária, pois os tempos são fixos no SUMO."""
        pass

class AdaptiveController:
    """Controlador Adaptativo que ajusta os semáforos com base no tráfego."""
    def __init__(self):
        self.traffic_light_ids: List[str] = []
        self.traffic_light_states: Dict[str, Dict[str, Any]] = {}
        try:
            self.traffic_light_ids = traci.trafficlight.getIDList()
            for tl_id in self.traffic_light_ids:
                self.traffic_light_states[tl_id] = {
                    'current_phase_index': traci.trafficlight.getPhase(tl_id),
                    'last_phase_change_step': 0
                }
            logger.info(f"Controlador Adaptativo inicializado para {len(self.traffic_light_ids)} semáforos.")
        except traci.TraCIException:
            logger.warning("Não foi possível obter a lista de semáforos na inicialização.")

    def manage_traffic_lights(self, step: int) -> None:
        """Lógica de controle adaptativo para gerenciar os semáforos."""
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
                
                should_switch = False
                if is_green_phase and time_in_phase > current_phase.minDur:
                    green_lanes = self._get_green_lanes_for_phase(tl_id, current_phase_index)
                    cars_on_green = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in green_lanes)
                    
                    next_phase_index = (current_phase_index + 1) % len(current_logic.phases)
                    next_green_lanes = self._get_green_lanes_for_phase(tl_id, next_phase_index)
                    cars_on_next = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in next_green_lanes)

                    if cars_on_next > cars_on_green + 2: # Limiar para evitar trocas constantes
                        should_switch = True
                
                if time_in_phase > current_phase.maxDur:
                    should_switch = True
                
                if should_switch:
                    next_phase_index = (current_phase_index + 1) % len(current_logic.phases)
                    traci.trafficlight.setPhase(tl_id, next_phase_index)
                    state['current_phase_index'] = next_phase_index
                    state['last_phase_change_step'] = step

            except traci.TraCIException as e:
                logger.error(f"Erro ao controlar semáforo {tl_id}: {e}")

    def _get_green_lanes_for_phase(self, tl_id: str, phase_index: int) -> List[str]:
        """Retorna as faixas que ficam verdes para uma determinada fase."""
        lanes: Set[str] = set()
        links = traci.trafficlight.getControlledLinks(tl_id)
        if not links: return []
        
        program_logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
        phase_state = program_logic.phases[phase_index].state
        
        for i, link in enumerate(links):
            if i < len(phase_state) and phase_state[i].lower() == 'g':
                lanes.add(link[0][0])
        return list(lanes)
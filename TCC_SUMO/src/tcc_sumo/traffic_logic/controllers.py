import traci
from tcc_sumo.utils.helpers import get_logger

logger = get_logger(__name__)

class TrafficController:
    """Controla os semáforos com base no modo de simulação."""

    def __init__(self, traffic_lights_config: list, mode: str):
        self.mode = mode.upper()
        self.traffic_lights = {str(tls['id']): tls for tls in traffic_lights_config}
        self.states = {}

        for tls_id, config in self.traffic_lights.items():
            self.states[tls_id] = {
                'current_phase_index': 0,
                'phase_start_step': 0
            }
            initial_phase_state = config['phases'][0]['state']
            traci.trafficlight.setRedYellowGreenState(tls_id, initial_phase_state)
            logger.info(f"Semáforo '{tls_id}' inicializado para controle.")

        logger.info(f"Controlador de tráfego inicializado em modo '{self.mode}'.")

    def update_logic(self, current_step: int):
        """Atualiza a lógica de todos os semáforos controlados."""
        for tls_id, config in self.traffic_lights.items():
            if self.mode == 'STATIC':
                self._update_static_logic(tls_id, config, current_step)
            elif self.mode == 'ADAPTIVE':
                self._update_adaptive_logic(tls_id, config, current_step)

    def _update_static_logic(self, tls_id: str, config: dict, current_step: int):
        """Lógica ESTÁTICA (tempos fixos)."""
        state = self.states[tls_id]
        phases = config['phases']
        
        current_phase_index = state['current_phase_index']
        current_phase_info = phases[current_phase_index]
        phase_duration = current_phase_info['duration']
        
        if current_step >= state['phase_start_step'] + phase_duration:
            next_phase_index = (current_phase_index + 1) % len(phases)
            
            self.states[tls_id]['current_phase_index'] = next_phase_index
            self.states[tls_id]['phase_start_step'] = current_step
            
            new_phase_state_str = phases[next_phase_index]['state']
            traci.trafficlight.setRedYellowGreenState(tls_id, new_phase_state_str)

    def _update_adaptive_logic(self, tls_id: str, config: dict, current_step: int):
        """Lógica ADAPTATIVA (IoT - reage ao tráfego)."""
        state = self.states[tls_id]
        phases = config['phases']
        
        current_phase_index = state['current_phase_index']
        current_phase_info = phases[current_phase_index]
        
        is_green_phase = 'y' not in current_phase_info['state'].lower()
        
        green_lanes = self._get_lanes_for_phase(config['lanes'], current_phase_index)
        cars_on_green = sum(traci.lane.getLastStepHaltingNumber(lane) for lane in green_lanes)
        
        time_in_phase = current_step - state['phase_start_step']
        min_duration = current_phase_info.get('min_duration', 10)
        max_duration = current_phase_info.get('max_duration', 60)
        
        should_switch = False
        if time_in_phase >= min_duration:
            if is_green_phase and (cars_on_green == 0 or time_in_phase >= max_duration):
                should_switch = True
            elif not is_green_phase and time_in_phase >= current_phase_info['duration']:
                should_switch = True

        if should_switch:
            next_phase_index = (current_phase_index + 1) % len(phases)
            
            self.states[tls_id]['current_phase_index'] = next_phase_index
            self.states[tls_id]['phase_start_step'] = current_step
            
            new_phase_state_str = phases[next_phase_index]['state']
            traci.trafficlight.setRedYellowGreenState(tls_id, new_phase_state_str)

    def _get_lanes_for_phase(self, all_lanes: list, phase_index: int) -> list:
        """Retorna as vias que ficam verdes para uma determinada fase."""
        if phase_index == 0: return all_lanes[:2]
        elif phase_index == 2: return all_lanes[2:]
        return []
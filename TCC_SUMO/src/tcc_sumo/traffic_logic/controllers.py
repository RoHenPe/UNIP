import traci
from tcc_sumo.utils.helpers import get_logger

logger = get_logger("TrafficController")

class StaticController:
    """Controlador para o modo Estático."""
    def __init__(self):
        logger.info("Controlador Estático inicializado.")

    def manage_traffic_lights(self, step):
        """Nenhuma ação necessária no modo estático."""
        pass

class AdaptiveController:
    """Controlador para o modo Adaptativo."""
    def __init__(self):
        try:
            self.traffic_light_ids = traci.trafficlight.getIDList()
            logger.info(f"Controlador Adaptativo inicializado para {len(self.traffic_light_ids)} semáforos.")
        except traci.TraCIException:
            logger.warning("Não foi possível obter a lista de semáforos.")
            self.traffic_light_ids = []

    def manage_traffic_lights(self, step):
        """Lógica de exemplo para controle adaptativo."""
        if step > 0 and step % 120 == 0:
            for tl_id in self.traffic_light_ids:
                try:
                    current_phase = traci.trafficlight.getPhase(tl_id)
                    all_phases = traci.trafficlight.getAllProgramLogics(tl_id)[0].phases
                    next_phase_index = (current_phase + 1) % len(all_phases)
                    traci.trafficlight.setPhase(tl_id, next_phase_index)
                except traci.TraCIException as e:
                    logger.error(f"Erro ao controlar o semáforo {tl_id}: {e}")
import re
import json
import sys
from pathlib import Path
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
from tcc_sumo.utils.helpers import get_logger, setup_logging, PROJECT_ROOT
logger = get_logger("reporter")
LOG_FILE = PROJECT_ROOT / "logs" / "simulation.log"
OUTPUT_FILE = PROJECT_ROOT / "reports" / "final_report.json"
def analyze_log():
    logger.info(f"Analisando log: {LOG_FILE}")
    try:
        with open(LOG_FILE, 'r') as f: content = f.read()
    except FileNotFoundError: logger.error(f"Arquivo de log não encontrado."); return None
    trip_data_pattern = re.compile(r"TRIP_DATA;ID=(?P<id>.*?);duration=(?P<duration>.*?);timeLoss=(?P<timeLoss>.*?);waitingTime=(?P<waitingTime>.*)")
    trips = [match.groupdict() for match in trip_data_pattern.finditer(content)]
    if not trips: logger.warning("Nenhum dado de viagem encontrado no log."); return None
    total_vehicles = len(trips)
    avg_duration = sum(float(t['duration']) for t in trips) / total_vehicles
    avg_time_loss = sum(float(t['timeLoss']) for t in trips) / total_vehicles
    avg_waiting_time = sum(float(t['waitingTime']) for t in trips) / total_vehicles
    report = {
        "metadata": {"source_log": str(LOG_FILE), "total_vehicles": total_vehicles},
        "summary_statistics": {
            "avg_trip_duration": round(avg_duration, 2),
            "avg_time_loss": round(avg_time_loss, 2),
            "avg_waiting_time": round(avg_waiting_time, 2)
        }
    }
    return report
def main():
    setup_logging(); logger.info("Iniciando geração de relatório...")
    report_data = analyze_log()
    if report_data:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f: json.dump(report_data, f, indent=4)
        logger.info(f"Relatório salvo com sucesso em '{OUTPUT_FILE}'")
if __name__ == "__main__":
    main()
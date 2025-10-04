import os
import sys
import json
import subprocess
from pathlib import Path

# Adiciona o diretório 'src' ao sys.path para importações corretas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tcc_sumo.utils.helpers import get_logger, setup_logging, ensure_sumo_home, PROJECT_ROOT

# Inicializa o logging
setup_logging()
logger = get_logger("ScenarioGenerator")

# Define os caminhos dos arquivos de saída
OUTPUT_DIR = PROJECT_ROOT / "scenarios" / "from_api"
TRAFFIC_DIR = OUTPUT_DIR / "traffic"
API_DATA_FILE = OUTPUT_DIR / "dados_api.json"
NODES_FILE = OUTPUT_DIR / "api.nod.xml"
EDGES_FILE = OUTPUT_DIR / "api.edg.xml"
NET_FILE = OUTPUT_DIR / "api.net.xml"
ROUTES_FILE = TRAFFIC_DIR / "api.rou.xml"
TRIPS_FILE = TRAFFIC_DIR / "trips.trips.xml"
CONFIG_FILE = OUTPUT_DIR / "cenario.sumocfg"

def run_command(command):
    """Executa um comando no shell e registra a saída."""
    logger.debug(f"Executando comando: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.info(f"Saída (stderr) do comando '{command[0]}':\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Comando falhou com código {e.returncode}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        raise

def create_sumo_files_from_api():
    """Lê dados da API e cria os arquivos de nós e arestas do SUMO."""
    if not API_DATA_FILE.is_file():
        raise FileNotFoundError(f"Arquivo de dados da API '{API_DATA_FILE.name}' não encontrado.")
    
    logger.info(f"Lendo dados da API de: {API_DATA_FILE}")
    with open(API_DATA_FILE, "r", encoding='utf-8') as f:
        api_data = json.load(f)
    
    nodes = api_data.get('nodes', [])
    relationships = api_data.get('relationships', [])
    
    valid_nodes = [node for node in nodes if 'id' in node and node.get('properties', {}).get('lon') is not None]
    existing_node_ids = {str(node['id']) for node in valid_nodes}
    
    with open(NODES_FILE, "w", encoding='utf-8') as f:
        f.write("<nodes>\n")
        for node in valid_nodes:
            prop = node.get('properties', {})
            node_type = "traffic_light" if prop.get("highway") == "traffic_signals" else "priority"
            f.write(f'    <node id="{node["id"]}" x="{prop["lon"]}" y="{prop["lat"]}" type="{node_type}"/>\n')
        f.write("</nodes>")

    with open(EDGES_FILE, "w", encoding='utf-8') as f:
        f.write("<edges>\n")
        for edge in relationships:
            if str(edge.get('startNodeId')) in existing_node_ids and str(edge.get('endNodeId')) in existing_node_ids:
                f.write(f'    <edge id="{edge["id"]}" from="{edge["startNodeId"]}" to="{edge["endNodeId"]}" numLanes="1" speed="13.89"/>\n')
        f.write("</edges>")
    logger.info("Arquivos de nós e arestas gerados.")

def main():
    """Função principal para gerar o cenário completo."""
    print("\nIniciando geração de cenário a partir de dados da API...")
    try:
        ensure_sumo_home()
        sumo_bin_path = Path(os.environ['SUMO_HOME']) / 'bin'
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        TRAFFIC_DIR.mkdir(parents=True, exist_ok=True)
        
        create_sumo_files_from_api()
        print("  [✔] Arquivos de nós e arestas criados.")

        print("  [ ] Construindo malha de tráfego...")
        run_command([
            str(sumo_bin_path / 'netconvert'), '--node-files', str(NODES_FILE),
            '--edge-files', str(EDGES_FILE), '-o', str(NET_FILE), '--proj.utm',
            '--geometry.remove', '--roundabouts.guess', '--junctions.join',
            '--verbose'
        ])
        print("  [✔] Malha de tráfego construída.")

        print("  [ ] Gerando rotas de veículos...")
        run_command([
            "python3", str(Path(os.environ['SUMO_HOME']) / 'tools' / 'randomTrips.py'),
            "-n", str(NET_FILE), "-r", str(ROUTES_FILE), "-o", str(TRIPS_FILE),
            "-e", "500", "--period", "1", "--validate"
        ])
        print("  [✔] Rotas de veículos geradas.")
        
        print("  [ ] Criando arquivo de configuração final...")
        relative_route_path = Path(TRAFFIC_DIR.name) / ROUTES_FILE.name
        config_content = f"""<configuration>
    <input>
        <net-file value="{NET_FILE.name}"/>
        <route-files value="{relative_route_path}"/>
    </input>
    <output>
        <emission-output value="api.emissions.xml"/>
    </output>
</configuration>"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"  [✔] Cenário gerado com sucesso em: '{CONFIG_FILE}'")

    except Exception as e:
        print(f"\n  [ERRO] Ocorreu uma falha durante a geração do cenário.")
        print(f"     Consulte 'logs/simulation.log' para detalhes técnicos.")
        logger.critical(f"Falha na geração do cenário: {e}", exc_info=True)

if __name__ == "__main__":
    main()
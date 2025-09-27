import os
import sys
import json
import subprocess
import shutil
from pathlib import Path

# --- Bloco de Configuração de Ambiente ---
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tcc_sumo.utils.helpers import get_logger, setup_logging, ensure_sumo_home, PROJECT_ROOT

# --- Inicialização ---
setup_logging()
logger = get_logger("scenario_generator")

# --- Caminhos dos Arquivos (Definição Absoluta e Organizada) ---
OUTPUT_DIR = PROJECT_ROOT / "scenarios" / "from_api"
TRAFFIC_DIR = OUTPUT_DIR / "traffic" # Subpasta para organização

API_DATA_FILE = OUTPUT_DIR / "dados_api.json"
NODES_FILE = OUTPUT_DIR / "api.nod.xml"
EDGES_FILE = OUTPUT_DIR / "api.edg.xml"
NET_FILE = OUTPUT_DIR / "api.net.xml"
CONFIG_FILE = OUTPUT_DIR / "cenario.sumocfg"

# Arquivos de tráfego que serão salvos na subpasta 'traffic'
ROUTES_FILE = TRAFFIC_DIR / "api.rou.xml"
TRIPS_FILE = TRAFFIC_DIR / "trips.trips.xml"


def run_command(command):
    """Executa um comando no shell e captura a saída para os logs."""
    logger.debug(f"Executando comando: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    if result.stdout:
        logger.info(result.stdout)
    if result.stderr:
        logger.info(f"Saída (stderr) do comando '{command[0]}':\n{result.stderr}")

def create_sumo_files_from_api():
    """Lê dados da API, valida e cria os arquivos de nós e arestas do SUMO."""
    if not API_DATA_FILE.is_file():
        raise FileNotFoundError(f"Arquivo de dados da API '{API_DATA_FILE.name}' não encontrado.")
    
    logger.info(f"Lendo dados da API de: {API_DATA_FILE}")
    with open(API_DATA_FILE, "r", encoding='utf-8') as f:
        api_data = json.load(f)
    
    nodes = api_data.get('nodes', [])
    relationships = api_data.get('relationships', [])
    
    valid_nodes = [
        node for node in nodes 
        if 'id' in node and node.get('properties', {}).get('lon') is not None and node.get('properties', {}).get('lat') is not None
    ]
    existing_node_ids = {str(node['id']) for node in valid_nodes}
    logger.info(f"Encontrados {len(existing_node_ids)} nós válidos de um total de {len(nodes)}.")
    
    with open(NODES_FILE, "w", encoding='utf-8') as f:
        f.write("<nodes>\n")
        for node in valid_nodes:
            prop = node.get('properties', {})
            node_type = "traffic_light" if prop.get("highway") == "traffic_signals" else "priority"
            f.write(f'    <node id="{node["id"]}" x="{prop["lon"]}" y="{prop["lat"]}" type="{node_type}"/>\n')
        f.write("</nodes>")

    with open(EDGES_FILE, "w", encoding='utf-8') as f:
        f.write("<edges>\n")
        edges_written = sum(
            1 for edge in relationships 
            if str(edge.get('startNodeId')) in existing_node_ids and str(edge.get('endNodeId')) in existing_node_ids
            and f.write(f'    <edge id="{edge["id"]}" from="{edge["startNodeId"]}" to="{edge["endNodeId"]}" numLanes="1" speed="13.89"/>\n')
        )
        f.write("</edges>")
    logger.info(f"{edges_written} arestas válidas foram escritas em {EDGES_FILE.name}.")


def validate_and_move_files(target_files: list):
    """
    Valida se os arquivos foram criados na raiz do projeto por engano e os move
    para o diretório de destino correto.
    """
    print("  >> Validando localização dos arquivos gerados...")
    moved_count = 0
    for target_path in target_files:
        fallback_path = PROJECT_ROOT / target_path.name
        if fallback_path.is_file():
            logger.warning(f"Arquivo '{fallback_path.name}' encontrado na raiz. Movendo para o destino correto.")
            shutil.move(str(fallback_path), str(target_path))
            moved_count += 1
    
    if moved_count > 0:
        print(f"  >> Auto-correção: {moved_count} arquivo(s) foram movidos para a pasta de destino correta.")
    else:
        print("  >> Validação concluída: Todos os arquivos estão no local correto.")


def main():
    """Função principal para gerar o cenário completo e otimizado."""
    print("\n  Iniciando geração de cenário a partir de dados da API...")
    try:
        ensure_sumo_home()
        sumo_bin_path = Path(os.environ['SUMO_HOME']) / 'bin'
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        TRAFFIC_DIR.mkdir(parents=True, exist_ok=True)
        
        create_sumo_files_from_api()
        print("  >> Arquivos de nós e arestas criados com sucesso.")

        print("  >> Construindo e refinando a malha de tráfego...")
        run_command([
            str(sumo_bin_path / 'netconvert'), '--node-files', str(NODES_FILE),
            '--edge-files', str(EDGES_FILE), '-o', str(NET_FILE), '--proj.utm',
            '--geometry.remove', '--roundabouts.guess', '--junctions.join',
            '--junctions.join-dist', '15', '--verbose'
        ])
        print("  >> Malha de tráfego construída com sucesso.")

        print("  >> Gerando rotas de veículos...")
        run_command([
            "python3", str(Path(os.environ['SUMO_HOME']) / 'tools' / 'randomTrips.py'),
            "-n", str(NET_FILE), "-r", str(ROUTES_FILE), "-o", str(TRIPS_FILE),
            "-e", "500", "--period", "1", "--validate"
        ])
        print("  >> Rotas de veículos geradas com sucesso.")
        
        print("  >> Criando arquivo de configuração final...")
        relative_route_path = Path(TRAFFIC_DIR.name) / ROUTES_FILE.name
        config_content = f"""<configuration>
    <input>
        <net-file value="{NET_FILE.name}"/>
        <route-files value="{relative_route_path}"/>
    </input>
</configuration>"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"  >> Cenário gerado com sucesso em: '{CONFIG_FILE}'")

        # --- CHAMADA DA FUNÇÃO DE VALIDAÇÃO E AUTO-CORREÇÃO ---
        files_to_validate = [NODES_FILE, EDGES_FILE, NET_FILE, ROUTES_FILE, TRIPS_FILE, CONFIG_FILE]
        validate_and_move_files(files_to_validate)

    except (subprocess.CalledProcessError, Exception) as e:
        print(f"\n  !! OCORREU UM ERRO DURANTE A GERAÇÃO !!")
        print(f"     Consulte 'logs/simulation.log' para detalhes técnicos.")
        logger.critical(f"Falha na geração do cenário: {e}", exc_info=True)

if __name__ == "__main__":
    main()
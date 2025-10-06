import os
import sys
import json
import subprocess
from pathlib import Path
import argparse
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tcc_sumo.utils.helpers import get_logger, setup_logging, ensure_sumo_home, PROJECT_ROOT

setup_logging()
logger = get_logger("ScenarioGenerator")

def run_command(command):
    """Executa um comando no shell, garantindo a execução no diretório raiz do projeto."""
    cmd_str_list = [str(item) for item in command]
    logger.info(f"Executando comando: {' '.join(cmd_str_list)}")
    try:
        result = subprocess.run(
            cmd_str_list, capture_output=True, text=True, check=True, 
            encoding='utf-8', cwd=PROJECT_ROOT
        )
        if result.stderr: logger.warning(f"Saída de aviso do comando '{command[0]}':\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Comando falhou: {e.stderr}")
        raise

def generate_api_scenario(base_file_path: Path):
    """Gera o cenário completo a partir do JSON da API."""
    print("\n--- INICIANDO GERAÇÃO DO CENÁRIO 'API' ---")
    
    output_dir = PROJECT_ROOT / "scenarios" / "from_api"
    if output_dir.exists(): shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    print("  [✓] Diretório de saída limpo e recriado.")

    nodes_file = output_dir / "api.nod.xml"
    edges_file = output_dir / "api.edg.xml"
    net_file = output_dir / "api.net.xml"

    print("  [ ] Lendo arquivo JSON base e criando arquivos de rede...")
    with open(base_file_path, "r", encoding='utf-8') as f: data = json.load(f)
    valid_node_ids = set()
    with open(nodes_file, "w", encoding='utf-8') as f:
        f.write("<nodes>\n")
        for node in data["nodes"]:
            prop = node.get('properties', {})
            if "lon" in prop and "lat" in prop:
                node_type = "traffic_light" if prop.get("highway") == "traffic_signals" else "priority"
                f.write(f'    <node id="{node["id"]}" x="{prop["lon"]}" y="{prop["lat"]}" type="{node_type}"/>\n')
                valid_node_ids.add(str(node["id"]))
        f.write("</nodes>")
    with open(edges_file, "w", encoding='utf-8') as f:
        f.write("<edges>\n")
        for edge in data.get("relationships", []):
            if str(edge.get('startNodeId')) in valid_node_ids and str(edge.get('endNodeId')) in valid_node_ids:
                f.write(f'    <edge id="{edge["id"]}" from="{edge["startNodeId"]}" to="{edge["endNodeId"]}" numLanes="1" speed="13.89"/>\n')
        f.write("</edges>")
    print("  [✓] Arquivos de nós e arestas criados.")

    print("  [ ] Gerando malha viária final...")
    run_command([
        Path(os.environ["SUMO_HOME"]) / 'bin' / 'netconvert', 
        '--node-files', nodes_file.relative_to(PROJECT_ROOT), 
        '--edge-files', edges_file.relative_to(PROJECT_ROOT), 
        '-o', net_file.relative_to(PROJECT_ROOT)
    ])
    print("  [✓] Malha viária gerada.")
    
    generate_common_files(output_dir, net_file, "api")
    print("--- GERAÇÃO DO CENÁRIO 'API' CONCLUÍDA ---")


def generate_osm_scenario(base_file_path: Path):
    """Gera o cenário completo a partir de um arquivo .osm.xml."""
    print("\n--- INICIANDO GERAÇÃO DO CENÁRIO 'OSM' ---")
    
    output_dir = PROJECT_ROOT / "scenarios" / "from_osm"
    if output_dir.exists(): shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    print("  [✓] Diretório de saída limpo e recriado.")

    net_file = output_dir / "osm.net.xml"

    print("  [ ] Gerando malha viária a partir do arquivo OSM...")
    run_command([
        Path(os.environ["SUMO_HOME"]) / 'bin' / 'netconvert', 
        '--osm-files', base_file_path.relative_to(PROJECT_ROOT), 
        '-o', net_file.relative_to(PROJECT_ROOT)
    ])
    print("  [✓] Malha viária gerada.")

    generate_common_files(output_dir, net_file, "osm")
    print("--- GERAÇÃO DO CENÁRIO 'OSM' CONCLUÍDA ---")


def generate_common_files(output_dir: Path, net_file: Path, scenario_name: str):
    """Gera arquivos comuns a ambos os cenários, com autovalidação e autocorreção."""
    routes_file = output_dir / f"{scenario_name}.rou.xml"
    trips_file = output_dir / f"{scenario_name}.trips.xml"
    emergency_routes_file = output_dir / "emergency.rou.xml"
    emergency_trips_file = output_dir / "emergency.trips.xml"
    emergency_vtype_file = output_dir / "emergency_vtype.add.xml"
    config_file = output_dir / f"{scenario_name}.sumocfg"
    sumo_tools_path = Path(os.environ["SUMO_HOME"]) / "tools"

    print("  [ ] Gerando rotas de tráfego normal...")
    num_vehicles, period = ("5000", "1.8") if scenario_name == 'osm' else ("2500", "2.0")
    run_command([
        "python3", sumo_tools_path/'randomTrips.py', "-n", net_file.relative_to(PROJECT_ROOT),
        "-r", routes_file.relative_to(PROJECT_ROOT), "-o", trips_file.relative_to(PROJECT_ROOT),
        "-e", num_vehicles, "--period", period, "--validate"
    ])
    print("  [✓] Rotas normais geradas.")

    print("  [ ] Criando arquivos adicionais...")
    vtype_content = f"""<additional><vType id="emergency" vClass="emergency" guiShape="emergency" color="1,0,0" speedFactor="2.0"><param key="has.bluelight.device" value="true"/></vType></additional>"""
    with open(emergency_vtype_file, 'w', encoding='utf-8') as f: f.write(vtype_content)
    print("  [✓] Definição de veículo de emergência criada.")

    print("  [ ] Gerando rotas de emergência...")
    num_vehicles_em, period_em = ("15", "600") if scenario_name == 'osm' else ("8", "800")
    run_command([
        "python3", sumo_tools_path/'randomTrips.py', "-n", net_file.relative_to(PROJECT_ROOT),
        "-r", emergency_routes_file.relative_to(PROJECT_ROOT), "-o", emergency_trips_file.relative_to(PROJECT_ROOT),
        "-e", num_vehicles_em, "--period", period_em, "--validate",
        "--prefix", "em", "--vtype", "emergency"
    ])
    print("  [✓] Rotas de emergência geradas.")

    print("  [ ] Validando e corrigindo caminhos dos arquivos gerados...")
    rogue_emergency_file = PROJECT_ROOT / "emergency"

    if not emergency_routes_file.exists() and rogue_emergency_file.exists():
        logger.warning(f"Arquivo problemático '{rogue_emergency_file.name}' encontrado na raiz. Movendo e renomeando para o destino correto: '{emergency_routes_file}'")
        shutil.move(str(rogue_emergency_file), str(emergency_routes_file))
        print(f"  [✓] Arquivo '{rogue_emergency_file.name}' foi corrigido.")
    elif not emergency_routes_file.exists():
        logger.critical(f"VALIDAÇÃO FALHOU: O arquivo de rotas de emergência não foi gerado em '{emergency_routes_file}'. A geração falhou.")
        raise FileNotFoundError(f"Geração de rotas de emergência falhou.")
    elif rogue_emergency_file.exists():
         logger.warning(f"Arquivo problemático '{rogue_emergency_file.name}' encontrado na raiz, mas o arquivo de destino já existe. Removendo arquivo problemático.")
         os.remove(rogue_emergency_file)
         print(f"  [✓] Arquivo '{rogue_emergency_file.name}' duplicado foi removido.")
    else:
        print("  [✓] Arquivos validados com sucesso.")

    print("  [ ] Criando arquivo de configuração final...")
    config_content = f"""<configuration>
    <input><net-file value="{net_file.name}"/><route-files value="{routes_file.name},{emergency_routes_file.name}"/><additional-files value="{emergency_vtype_file.name}"/></input>
    <output><tripinfo-output value="tripinfo.xml"/><emission-output value="emissions.xml"/><queue-output value="queueinfo.xml"/></output>
</configuration>"""
    with open(config_file, 'w', encoding='utf-8') as f: f.write(config_content)
    print("  [✓] Arquivo de configuração final criado.")

    print("  [ ] Removendo arquivos de 'trips' intermediários...")
    try:
        if trips_file.exists(): os.remove(trips_file)
        if emergency_trips_file.exists(): os.remove(emergency_trips_file)
        print("  [✓] Arquivos intermediários removidos.")
    except OSError as e:
        logger.warning(f"Não foi possível remover arquivos de trips intermediários: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerenciador de Cenários para Simulação de Tráfego SUMO.")
    parser.add_argument("--type", type=str, required=True, choices=['osm', 'api'], help="Tipo de cenário a ser gerado.")
    parser.add_argument("--input", type=str, required=True, help="Nome do arquivo base (ex: 'osm_bbox.osm.xml' ou 'dados_api.json').")
    args = parser.parse_args()

    try:
        ensure_sumo_home()
        base_file = PROJECT_ROOT / "scenarios" / "base_files" / args.input
        
        if args.type == 'osm':
            generate_osm_scenario(base_file)
        elif args.type == 'api':
            generate_api_scenario(base_file)

    except Exception as e:
        logger.critical(f"Erro crítico no pipeline de geração: {e}", exc_info=True)
        print(f"\n[✗] FALHA INESPERADA. Verifique 'logs/simulation.log' para detalhes.")
        sys.exit(1)
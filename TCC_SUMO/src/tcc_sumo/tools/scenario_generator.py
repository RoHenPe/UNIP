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

def run_simple_command(command):
    # PILAR DE QUALIDADE: Diagnósticabilidade
    # DESCRIÇÃO: Centraliza a execução de comandos externos, capturando as suas
    # saídas para facilitar a depuração de ferramentas como o SUMO.
    cmd_str_list = [str(item) for item in command]
    cmd_str = ' '.join(cmd_str_list)
    logger.info(f"Executando sub-comando: {cmd_str}")
    
    try:
        result = subprocess.run(cmd_str_list, 
                                cwd=PROJECT_ROOT, 
                                check=True, 
                                capture_output=True, 
                                text=True,
                                encoding='utf-8')
        
        if result.stdout and result.stdout.strip():
            logger.debug(f"Saída STDOUT do comando:\n{result.stdout.strip()}")
        if result.stderr and result.stderr.strip():
            logger.debug(f"Saída STDERR do comando:\n{result.stderr.strip()}")
            
        logger.info("Comando externo concluído com sucesso.")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Comando falhou com código {e.returncode}: {e.cmd}")
        if e.stdout and e.stdout.strip():
            logger.error(f"Saída STDOUT do erro:\n{e.stdout.strip()}")
        if e.stderr and e.stderr.strip():
            logger.error(f"Saída STDERR do erro:\n{e.stderr.strip()}")
        raise 

def generate_scenario(scenario_type: str, base_file_path: Path):
    # PILAR DE QUALIDADE: Manutenibilidade
    # DESCRIÇÃO: Orquestra a geração do cenário de forma modular, separando a
    # lógica de criação da malha da geração dos ficheiros de simulação.
    output_dir = PROJECT_ROOT / "scenarios" / f"from_{scenario_type}"
    if output_dir.exists(): shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    logger.info(f"Diretório de saída para {scenario_type.upper()} limpo e recriado em '{output_dir}'.")
    
    net_file = output_dir / f"{scenario_type}.net.xml"
    
    if scenario_type == 'osm':
        run_simple_command([
            Path(os.environ["SUMO_HOME"]) / 'bin' / 'netconvert',
            '--osm-files', base_file_path.relative_to(PROJECT_ROOT),
            '-o', net_file.relative_to(PROJECT_ROOT), 
            '--geometry.remove'
        ])
    elif scenario_type == 'api':
        nodes_file, edges_file = output_dir/"api.nod.xml", output_dir/"api.edg.xml"
        
        logger.info(f"Lendo dados da API de: {base_file_path.name}")
        with open(base_file_path, "r", encoding='utf-8') as f: data = json.load(f)
        
        valid_node_ids = set()
        with open(nodes_file, "w", encoding='utf-8') as f:
            f.write('<nodes>\n')
            for node in data.get("nodes",[]):
                prop = node.get('properties',{})
                if "lon" in prop and "lat" in prop:
                    node_type = "traffic_light" if prop.get("highway")=="traffic_signals" else "priority"
                    f.write(f'    <node id="{node["id"]}" x="{prop["lon"]}" y="{prop["lat"]}" type="{node_type}"/>\n')
                    valid_node_ids.add(str(node["id"]))
            f.write('</nodes>')
        logger.debug(f"Ficheiro 'nod.xml' criado com {len(valid_node_ids)} nós.")
        
        with open(edges_file, "w", encoding='utf-8') as f:
            f.write('<edges>\n')
            for edge in data.get("relationships",[]):
                if str(edge.get('startNodeId')) in valid_node_ids and str(edge.get('endNodeId')) in valid_node_ids:
                    f.write(f'    <edge id="{edge["id"]}" from="{edge["startNodeId"]}" to="{edge["endNodeId"]}" numLanes="1" speed="13.89"/>\n')
            f.write('</edges>')
        logger.debug(f"Ficheiro 'edg.xml' criado.")
        
        run_simple_command([
            Path(os.environ["SUMO_HOME"]) / 'bin' / 'netconvert',
            '--node-files', nodes_file.relative_to(PROJECT_ROOT),
            '--edge-files', edges_file.relative_to(PROJECT_ROOT),
            '-o', net_file.relative_to(PROJECT_ROOT), 
            '--geometry.remove',
            '--proj.utm',
            '--roundabouts.guess', 
            '--junctions.join', 
            '--no-turnarounds' 
        ])

    generate_common_files(output_dir, net_file, scenario_type)

def generate_common_files(output_dir: Path, net_file: Path, scenario_name: str):
    # PILAR DE QUALIDADE: Flexibilidade
    # DESCRIÇÃO: A lógica adapta-se à densidade de veículos configurada,
    # permitindo simular cenários de baixo fluxo ou de tráfego intenso.
    routes_file, trips_file, config_file = (output_dir/f"{scenario_name}.rou.xml", output_dir/f"{scenario_name}.trips.xml", output_dir/f"{scenario_name}.sumocfg")
    
    num_vehicles = os.environ.get('VEHICLE_COUNT', '50000')
    
    insertion_duration = 3600 
    if int(num_vehicles) > 100000:
        insertion_duration = 7200 
    
    period = insertion_duration / int(num_vehicles) if int(num_vehicles) > 0 else 1
    period = max(0.05, period) 

    logger.info(f"Gerando {num_vehicles} veículos para o cenário '{scenario_name}' com período de inserção ~{period:.3f}s.")
    
    run_simple_command([
        "python3", Path(os.environ["SUMO_HOME"])/"tools"/'randomTrips.py',
        "-n", net_file.relative_to(PROJECT_ROOT),
        "-r", routes_file.relative_to(PROJECT_ROOT),
        "-o", trips_file.relative_to(PROJECT_ROOT),
        "-e", str(num_vehicles),
        "--period", f"{period:.3f}",
        "--fringe-factor", "10", 
        "--validate",
    ])
    
    if trips_file.exists():
        os.remove(trips_file); logger.debug(f"Ficheiro de trips intermediário '{trips_file}' removido.")

    config_content = f"""<configuration>
    <input><net-file value="{net_file.name}"/><route-files value="{routes_file.name}"/></input>
    <output><tripinfo-output value="tripinfo.xml"/><emission-output value="emissions.xml"/><queue-output value="queueinfo.xml"/></output>
</configuration>"""
    with open(config_file, 'w', encoding='utf-8') as f: f.write(config_content)
    logger.info(f"Ficheiro de configuração '{config_file}' criado.")

if __name__ == "__main__":
    # PILAR DE QUALIDADE: Usabilidade
    # DESCRIÇÃO: A interface de linha de comando `argparse` permite que o script
    # seja executado com diferentes parâmetros de forma controlada.
    parser = argparse.ArgumentParser(description="Gerador de Cenários para Simulação de Tráfego SUMO.")
    parser.add_argument("--type", type=str, required=True, choices=['osm', 'api'])
    parser.add_argument("--input", type=str, required=True)
    args = parser.parse_args()
    try:
        ensure_sumo_home()
        base_file_name = Path(args.input).name
        base_file = PROJECT_ROOT / "scenarios" / "base_files" / base_file_name
        logger.info(f"Iniciando geração de cenário do tipo '{args.type}' com o ficheiro de entrada '{args.input}'.")
        if not base_file.exists():
            logger.critical(f"O ficheiro de entrada '{base_file}' não foi encontrado."); sys.exit(1)
        generate_scenario(args.type, base_file)
        logger.info(f"Geração do cenário '{args.type}' concluída com sucesso.")
    except Exception as e:
        logger.critical(f"Erro no pipeline de geração: {e}", exc_info=True); sys.exit(1)
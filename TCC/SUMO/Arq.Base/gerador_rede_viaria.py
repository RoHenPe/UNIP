import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime

def get_user_input():
    """Obtém as configurações da malha do usuário de forma simplificada"""
    print("=" * 50)
    print("CONFIGURAÇÃO DA MALHA VIÁRIA")
    print("=" * 50)
    
    print("\n1. DEFINIÇÃO DAS VIAS PRINCIPAIS (eixo X)")
    vias_principais = int(input("Quantas vias principais (eixo X)? "))
    comprimento_vias = float(input("Comprimento de cada via (metros)? "))
    
    print("\n2. DEFINIÇÃO DAS VIAS TRANSVERSAIS (eixo Y)")
    vias_transversais = int(input("Quantas vias transversais (eixo Y)? "))
    largura_vias = float(input("Largura de cada via (metros)? "))
    
    print("\n3. CONFIGURAÇÃO DO SOLO (eixo Z)")
    altura_solo = float(input("Altura do solo (metros)? [Padrão: 0] ") or "0")
    
    return {
        'vias_principais': vias_principais,
        'vias_transversais': vias_transversais,
        'comprimento': comprimento_vias,
        'largura': largura_vias,
        'altura': altura_solo
    }

def generate_network_file(config, caminho_completo):
    """Gera arquivo de rede para o SUMO"""
    root = ET.Element("net")
    root.set("version", "1.0")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", "http://sumo.dlr.de/xsd/net_file.xsd")
    
    # Configuração de localização
    location = ET.SubElement(root, "location")
    location.set("netOffset", "0,0")
    total_x = config['vias_principais'] * config['comprimento']
    total_y = config['vias_transversais'] * config['largura']
    location.set("convBoundary", f"0,0,{total_x},{total_y}")
    location.set("origBoundary", f"0,0,{total_x},{total_y}")
    
    # Gera nós (cruzamentos)
    node_id = 0
    for x in range(config['vias_principais'] + 1):
        for y in range(config['vias_transversais'] + 1):
            node = ET.SubElement(root, "node")
            node.set("id", f"n{node_id}")
            node.set("x", str(x * config['comprimento']))
            node.set("y", str(y * config['largura']))
            node.set("type", "priority" if x == 0 or y == 0 or 
                                      x == config['vias_principais'] or 
                                      y == config['vias_transversais'] else "internal")
            node_id += 1
    
    # Gera arestas (vias)
    edge_id = 0
    
    # Vias principais (horizontais)
    for y in range(config['vias_transversais'] + 1):
        for x in range(config['vias_principais']):
            from_node = y * (config['vias_principais'] + 1) + x
            to_node = from_node + 1
            
            edge = ET.SubElement(root, "edge")
            edge.set("id", f"e{edge_id}")
            edge.set("from", f"n{from_node}")
            edge.set("to", f"n{to_node}")
            edge.set("priority", "3")
            
            lane = ET.SubElement(edge, "lane")
            lane.set("index", "0")
            lane.set("speed", "13.89")
            lane.set("length", str(config['comprimento']))
            lane.set("width", "3.5")
            
            edge_id += 1
    
    # Vias transversais (verticais)
    for x in range(config['vias_principais'] + 1):
        for y in range(config['vias_transversais']):
            from_node = y * (config['vias_principais'] + 1) + x
            to_node = from_node + (config['vias_principais'] + 1)
            
            edge = ET.SubElement(root, "edge")
            edge.set("id", f"e{edge_id}")
            edge.set("from", f"n{from_node}")
            edge.set("to", f"n{to_node}")
            edge.set("priority", "3")
            
            lane = ET.SubElement(edge, "lane")
            lane.set("index", "0")
            lane.set("speed", "13.89")
            lane.set("length", str(config['largura']))
            lane.set("width", "3.5")
            
            edge_id += 1
    
    # Salva arquivo
    tree = ET.ElementTree(root)
    network_path = os.path.join(caminho_completo, 'network.net.xml')
    tree.write(network_path, encoding='utf-8', xml_declaration=True)
    print(f"Arquivo de rede SUMO criado: {network_path}")
    
    return total_x, total_y

def generate_blender_obj(config, total_x, total_y, caminho_completo):
    """Gera arquivo OBJ para o Blender com a malha viária"""
    obj_path = os.path.join(caminho_completo, 'malha_viaria.obj')
    
    with open(obj_path, 'w') as f:
        f.write("# Malha viária gerada automaticamente\n")
        f.write(f"# Vias principais: {config['vias_principais']}\n")
        f.write(f"# Vias transversais: {config['vias_transversais']}\n")
        f.write(f"# Dimensões: {total_x}x{total_y}m\n\n")
        
        # Vértices do plano do solo
        f.write(f"v 0 0 {config['altura']}\n")
        f.write(f"v {total_x} 0 {config['altura']}\n")
        f.write(f"v {total_x} {total_y} {config['altura']}\n")
        f.write(f"v 0 {total_y} {config['altura']}\n\n")
        
        # Face do plano do solo
        f.write("f 1 2 3 4\n\n")
        
        # Adiciona marcadores para as vias (linhas simples)
        vertex_count = 5
        
        # Marcadores para vias principais (eixo X)
        for y in range(config['vias_transversais'] + 1):
            y_pos = y * config['largura']
            f.write(f"v 0 {y_pos} {config['altura'] + 0.01}\n")
            f.write(f"v {total_x} {y_pos} {config['altura'] + 0.01}\n")
            f.write(f"l {vertex_count} {vertex_count + 1}\n")
            vertex_count += 2
        
        # Marcadores para vias transversais (eixo Y)
        for x in range(config['vias_principais'] + 1):
            x_pos = x * config['comprimento']
            f.write(f"v {x_pos} 0 {config['altura'] + 0.01}\n")
            f.write(f"v {x_pos} {total_y} {config['altura'] + 0.01}\n")
            f.write(f"l {vertex_count} {vertex_count + 1}\n")
            vertex_count += 2
    
    print(f"Arquivo OBJ para Blender criado: {obj_path}")

def generate_unity_files(config, total_x, total_y, caminho_completo):
    """Gera arquivos de configuração para Unity"""
    
    # Gera arquivo JSON com informações da malha
    unity_config = {
        "vias_principais": config['vias_principais'],
        "vias_transversais": config['vias_transversais'],
        "comprimento_vias": config['comprimento'],
        "largura_vias": config['largura'],
        "altura_solo": config['altura'],
        "dimensoes_totais": {
            "x": total_x,
            "y": total_y,
            "z": config['altura']
        }
    }
    
    json_path = os.path.join(caminho_completo, 'malha_config.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(unity_config, f, indent=4, ensure_ascii=False)
    print(f"Arquivo de configuração para Unity criado: {json_path}")
    
    # Gera script C# básico para Unity
    unity_script_path = os.path.join(caminho_completo, 'MalhaViaria.cs')
    with open(unity_script_path, 'w', encoding='utf-8') as f:
        f.write(f'''using UnityEngine;
using System.Collections;

public class MalhaViaria : MonoBehaviour
{{
    public int viasPrincipais = {config['vias_principais']};
    public int viasTransversais = {config['vias_transversais']};
    public float comprimentoVia = {config['comprimento']}f;
    public float larguraVia = {config['largura']}f;
    public float alturaSolo = {config['altura']}f;

    void Start()
    {{
        CriarMalhaViaria();
    }}

    void CriarMalhaViaria()
    {{
        // Cria o solo
        GameObject solo = GameObject.CreatePrimitive(PrimitiveType.Plane);
        solo.transform.localScale = new Vector3({total_x}/10f, 1, {total_y}/10f);
        solo.transform.position = new Vector3({total_x}/2f, {config['altura']}, {total_y}/2f);
        solo.name = "Solo";

        // Adiciona aqui a lógica para criar as vias
        Debug.Log("Malha viária criada com " + viasPrincipais + " vias principais e " + 
                 viasTransversais + " vias transversais");
    }}
}}
''')
    print(f"Script C# para Unity criado: {unity_script_path}")

def generate_simulation_output():
    """Gera todos os arquivos de saída para simulação"""
    # Obtém configurações do usuário
    config = get_user_input()
    
    # Cria diretório de saída
    caminho_base = r'I:\UNIP\TCC\SUMO\simulation_output'
    nome_pasta = "Malha_UNITY"  
    caminho_completo = os.path.join(caminho_base, nome_pasta)
    os.makedirs(caminho_completo, exist_ok=True)
    
    print(f"\nCriando diretório de saída em: {caminho_completo}")
    print("Executando script de geração de malha...")
    
    # Gera arquivos
    total_x, total_y = generate_network_file(config, caminho_completo)
    generate_blender_obj(config, total_x, total_y, caminho_completo)
    generate_unity_files(config, total_x, total_y, caminho_completo)
    
    # Gera arquivo README
    readme_path = os.path.join(caminho_completo, 'README.txt')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f'''Arquivos de malha viária gerados em: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Configuração da malha:
- Vias principais (eixo X): {config['vias_principais']}
- Vias transversais (eixo Y): {config['vias_transversais']}
- Comprimento de cada via: {config['comprimento']} metros
- Largura de cada via: {config['largura']} metros
- Altura do solo: {config['altura']} metros

Arquivos incluídos:
1. network.net.xml - Rede viária para o SUMO
2. malha_viaria.obj - Malha 3D para importar no Blender
3. malha_config.json - Configurações da malha para Unity
4. MalhaViaria.cs - Script C# básico para Unity

Instruções:
1. Para o SUMO: Use o arquivo network.net.xml como rede viária
2. Para o Blender: Importe o arquivo malha_viaria.obj
3. Para a Unity: 
   - Copie o arquivo MalhaViaria.cs para a pasta Assets/Scripts
   - Use os valores em malha_config.json para configurar sua cena
''')
    print(f"Arquivo README criado: {readme_path}")
    print(f"\nTodos os arquivos foram gerados com sucesso em: {caminho_completo}")

# Executa a geração
if __name__ == "__main__":
    generate_simulation_output()
import json
import os

# --- CONFIGURAÇÕES DA REDE VIÁRIA ---
GRID_X = 1
GRID_Y = 2
DISTANCIA_ENTRE_CRUZAMENTOS = 150.0
EXTENSAO_EXTERNA = 100.0
LARGURA_RUA = 200.0
ESPESSURA_RUA = 5.0
LARGURA_FAIXA_VIA = LARGURA_RUA / 2.0
LARGURA_FAIXA_PEDESTRE = 0.5
COMPRIMENTO_FAIXA_PEDESTRE = 8.0  # Comprimento da faixa na direcao do fluxo
ESPACO_FAIXA_PEDESTRE = 2.0  # Espaco entre as faixas

# --- CONFIGURAÇÕES DE TEXTURA ---
TEXTURE_ASPHALT = "tl_straight_road_2x_diff.jpg"
TEXTURE_CROSSWALK = "tl_straight_road_2x_crosswalk_diff.jpg"
TEXTURE_CROSS_ASPHALT = "tl_cross_road_2x_diff.jpg"

def gerar_arquivos():
    # Define o caminho de saída
    output_path = r'I:\UNIP\TCC\SUMO\malha_unity'
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    obj_file = os.path.join(output_path, "rede_viaria.obj")
    mtl_file = os.path.join(output_path, "rede_viaria.mtl")
    json_file = os.path.join(output_path, "rede_viaria.json")

    # --- Geração do .mtl ---
    mtl_content = f"""
newmtl AsphaltMaterial
Kd 0.2 0.2 0.2
map_Kd {TEXTURE_ASPHALT}

newmtl CrosswalkMaterial
Kd 1.0 1.0 1.0
map_Kd {TEXTURE_CROSSWALK}

newmtl CrossMaterial
Kd 0.2 0.2 0.2
map_Kd {TEXTURE_CROSS_ASPHALT}
"""
    with open(mtl_file, "w") as f:
        f.write(mtl_content)

    # --- Geração do .obj ---
    obj_content = f"# Gerado por gerador_rede_viaria.py\n"
    obj_content += f"mtllib {os.path.basename(mtl_file)}\n"
    
    vertices = []
    uvs = []
    faces = []
    
    vertex_count = 1
    
    scene_layout = {
        "cruzamentos": [],
        "spawners_veiculos": [],
        "waypoints": {}
    }

    # Adiciona os waypoints de cada cruzamento e spawners de veículos
    def add_waypoints(start, end, name):
        scene_layout["waypoints"][name] = {
            "start": {"x": start[0], "y": start[1], "z": start[2]},
            "end": {"x": end[0], "y": end[1], "z": end[2]}
        }

    # Funcao para gerar uma placa (quadrado) com UVs e adicionar aos dados do OBJ
    def add_plate(center_x, center_z, width, length, material, rotation=0, is_crosswalk=False):
        nonlocal vertex_count
        
        half_width = width / 2.0
        half_length = length / 2.0
        
        # Vertices (rotacionados se necessario)
        p1 = (-half_width, 0, -half_length)
        p2 = (half_width, 0, -half_length)
        p3 = (half_width, 0, half_length)
        p4 = (-half_width, 0, half_length)
        
        points = [p1, p2, p3, p4]
        
        # Coordenadas UV (ajustadas para a textura)
        uv_scale_x = 1 if is_crosswalk else width / 10.0 # Escala para nao repetir muito a textura
        uv_scale_y = 1 if is_crosswalk else length / 10.0
        
        uv1 = (0, uv_scale_y)
        uv2 = (uv_scale_x, uv_scale_y)
        uv3 = (uv_scale_x, 0)
        uv4 = (0, 0)

        for p in points:
            vertices.append((p[0] + center_x, ESPESSURA_RUA, p[2] + center_z))
        
        uvs.extend([uv1, uv2, uv3, uv4])
        
        faces.append({
            "vertices": [vertex_count, vertex_count + 1, vertex_count + 2, vertex_count + 3],
            "uvs": [vertex_count, vertex_count + 1, vertex_count + 2, vertex_count + 3],
            "material": material
        })
        
        vertex_count += 4


    for y in range(GRID_Y):
        for x in range(GRID_X):
            cruzamento_id = f"{x}_{y}"
            center_x = x * DISTANCIA_ENTRE_CRUZAMENTOS
            center_z = y * DISTANCIA_ENTRE_CRUZAMENTOS
            
            # Adiciona o cruzamento aos dados da cena
            scene_layout["cruzamentos"].append({
                "id": cruzamento_id,
                "posicao": {"x": center_x, "y": 0, "z": center_z}
            })
            
            # --- Geração do asfalto do cruzamento ---
            add_plate(center_x, center_z, LARGURA_RUA, LARGURA_RUA, "CrossMaterial")

            # --- Geração das ruas e faixas de pedestres ---
            # Vias Norte-Sul
            street_length = (DISTANCIA_ENTRE_CRUZAMENTOS - LARGURA_RUA) / 2.0 + EXTENSAO_EXTERNA
            street_pos_z_norte = center_z + LARGURA_RUA/2 + street_length / 2.0
            street_pos_z_sul = center_z - LARGURA_RUA/2 - street_length / 2.0
            
            add_plate(center_x, street_pos_z_norte, LARGURA_RUA, street_length, "AsphaltMaterial")
            add_plate(center_x, street_pos_z_sul, LARGURA_RUA, street_length, "AsphaltMaterial")
            
            # Faixas de pedestre - Norte
            ped_start_z = center_z + LARGURA_RUA / 2.0
            for i in range(2):
                pos_z = ped_start_z + (i * (COMPRIMENTO_FAIXA_PEDESTRE + ESPACO_FAIXA_PEDESTRE))
                add_plate(center_x, pos_z, LARGURA_RUA, COMPRIMENTO_FAIXA_PEDESTRE, "CrosswalkMaterial", is_crosswalk=True)

            # Faixas de pedestre - Sul
            ped_start_z = center_z - LARGURA_RUA / 2.0
            for i in range(2):
                pos_z = ped_start_z - (i * (COMPRIMENTO_FAIXA_PEDESTRE + ESPACO_FAIXA_PEDESTRE))
                add_plate(center_x, pos_z, LARGURA_RUA, COMPRIMENTO_FAIXA_PEDESTRE, "CrosswalkMaterial", is_crosswalk=True)

            # Vias Leste-Oeste
            street_length = (DISTANCIA_ENTRE_CRUZAMENTOS - LARGURA_RUA) / 2.0 + EXTENSAO_EXTERNA
            street_pos_x_leste = center_x + LARGURA_RUA/2 + street_length / 2.0
            street_pos_x_oeste = center_x - LARGURA_RUA/2 - street_length / 2.0
            
            add_plate(street_pos_x_leste, center_z, street_length, LARGURA_RUA, "AsphaltMaterial")
            add_plate(street_pos_x_oeste, center_z, street_length, LARGURA_RUA, "AsphaltMaterial")
            
            # Faixas de pedestre - Leste
            ped_start_x = center_x + LARGURA_RUA / 2.0
            for i in range(2):
                pos_x = ped_start_x + (i * (COMPRIMENTO_FAIXA_PEDESTRE + ESPACO_FAIXA_PEDESTRE))
                add_plate(pos_x, center_z, COMPRIMENTO_FAIXA_PEDESTRE, LARGURA_RUA, "CrosswalkMaterial", is_crosswalk=True)
            
            # Faixas de pedestre - Oeste
            ped_start_x = center_x - LARGURA_RUA / 2.0
            for i in range(2):
                pos_x = ped_start_x - (i * (COMPRIMENTO_FAIXA_PEDESTRE + ESPACO_FAIXA_PEDESTRE))
                add_plate(pos_x, center_z, COMPRIMENTO_FAIXA_PEDESTRE, LARGURA_RUA, "CrosswalkMaterial", is_crosswalk=True)

            # Adiciona os waypoints (para veículos)
            lane_offset = LARGURA_RUA/4.0 # Offset para o centro da faixa
            # Nort - Sul
            start_n_s = (center_x - lane_offset, 0, center_z + LARGURA_RUA/2 + EXTENSAO_EXTERNA)
            end_n_s = (center_x - lane_offset, 0, center_z - LARGURA_RUA/2 - EXTENSAO_EXTERNA)
            add_waypoints(start_n_s, end_n_s, f"waypoint_{cruzamento_id}_N_S")
            # Sul - Norte
            start_s_n = (center_x + lane_offset, 0, center_z - LARGURA_RUA/2 - EXTENSAO_EXTERNA)
            end_s_n = (center_x + lane_offset, 0, center_z + LARGURA_RUA/2 + EXTENSAO_EXTERNA)
            add_waypoints(start_s_n, end_s_n, f"waypoint_{cruzamento_id}_S_N")

            # Leste - Oeste
            start_l_o = (center_x + LARGURA_RUA/2 + EXTENSAO_EXTERNA, 0, center_z + lane_offset)
            end_l_o = (center_x - LARGURA_RUA/2 - EXTENSAO_EXTERNA, 0, center_z + lane_offset)
            add_waypoints(start_l_o, end_l_o, f"waypoint_{cruzamento_id}_L_O")
            # Oeste - Leste
            start_o_l = (center_x - LARGURA_RUA/2 - EXTENSAO_EXTERNA, 0, center_z - lane_offset)
            end_o_l = (center_x + LARGURA_RUA/2 + EXTENSAO_EXTERNA, 0, center_z - lane_offset)
            add_waypoints(start_o_l, end_o_l, f"waypoint_{cruzamento_id}_O_L")
            
            # Spawners de veículos
            scene_layout["spawners_veiculos"].extend([
                {"id": f"spawner_N_{cruzamento_id}", "posicao": {"x": start_n_s[0], "y": 0, "z": start_n_s[2]}, "rotacao": {"x": 0, "y": 0, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_N_S"},
                {"id": f"spawner_S_{cruzamento_id}", "posicao": {"x": start_s_n[0], "y": 0, "z": start_s_n[2]}, "rotacao": {"x": 0, "y": 180, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_S_N"},
                {"id": f"spawner_L_{cruzamento_id}", "posicao": {"x": start_l_o[0], "y": 0, "z": start_l_o[2]}, "rotacao": {"x": 0, "y": -90, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_L_O"},
                {"id": f"spawner_O_{cruzamento_id}", "posicao": {"x": start_o_l[0], "y": 0, "z": start_o_l[2]}, "rotacao": {"x": 0, "y": 90, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_O_L"}
            ])

    # Adiciona os vertices e UVs ao conteudo do OBJ
    for v in vertices:
        obj_content += f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n"
    for uv in uvs:
        obj_content += f"vt {uv[0]:.4f} {uv[1]:.4f}\n"

    # Adiciona as faces ao conteudo do OBJ
    current_material = None
    for face in faces:
        if face["material"] != current_material:
            obj_content += f"\nusemtl {face['material']}\n"
            current_material = face["material"]
        
        v_indices = face["vertices"]
        vt_indices = face["uvs"]
        
        # Formato OBJ: v/vt v/vt v/vt ...
        obj_content += f"f {v_indices[0]}/{vt_indices[0]} {v_indices[1]}/{vt_indices[1]} {v_indices[2]}/{vt_indices[2]} {v_indices[3]}/{vt_indices[3]}\n"

    with open(obj_file, "w") as f:
        f.write(obj_content)
    
    with open(json_file, "w") as f:
        json.dump(scene_layout, f, indent=4)

    print(f"Arquivos gerados com sucesso em {output_path}")

# Executa a geração
gerar_arquivos()
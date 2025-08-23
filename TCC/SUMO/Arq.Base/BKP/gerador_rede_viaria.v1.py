import json

# --- CONFIGURAÇÕES DA REDE VIÁRIA ---
GRID_X = 1
GRID_Y = 1
DISTANCIA_ENTRE_CRUZAMENTOS = 150.0
EXTENSAO_EXTERNA = 100.0  # Extensão adicional para as vias externas
LARGURA_RUA = 20.0
ESPESSURA_RUA = 0.5
LARGURA_FAIXA = 0.5
COMPRIMENTO_FAIXA = 5.0
ESPACO_FAIXA = 4.0
LARGURA_FAIXA_PEDESTRE = 0.5
ESPACO_FAIXA_PEDESTRE = 1.0
NUMERO_FAIXAS_PEDESTRE = 8
LARGURA_FAIXA_VIA = LARGURA_RUA / 2.0  # Largura da faixa de rodagem em cada sentido

# --- CONFIGURAÇÕES DE TEXTURA ---
TEXTURE_ASPHALT = "tl_straight_road_2x_diff.jpg"
TEXTURE_CROSSWALK = "tl_cross_road_2x_crosswalk_diff.jpg"
TEXTURE_CROSS_ASPHALT = "tl_cross_road_2x_diff.jpg"

def gerar_arquivos():
    # --- Geração do .mtl ---
    mtl_content = f"""
newmtl AsphaltMaterial
Kd 0.2 0.2 0.2
map_Kd {TEXTURE_ASPHALT}

newmtl WhiteLineMaterial
Kd 1.0 1.0 1.0

newmtl CrosswalkMaterial
Kd 1.0 1.0 1.0
map_Kd {TEXTURE_CROSSWALK}

newmtl CrossAsphaltMaterial
Kd 0.2 0.2 0.2
map_Kd {TEXTURE_CROSS_ASPHALT}
"""
    with open("rede_viaria.mtl", "w") as f:
        f.write(mtl_content)
    print("Arquivo 'rede_viaria.mtl' gerado.")

    scene_layout = {"semaforos": [], "spawners_veiculos": [], "cameras": []}
    waypoints_data = {"waypoints": {}}
    
    vertex_offset = 0
    uv_offset = 0
    
    # --- Funções Auxiliares para Geração de OBJ e Waypoints ---
    def create_plane(obj_file, width, length, position, material, uv_coords=[(0, 0), (1, 0), (1, 1), (0, 1)]):
        nonlocal vertex_offset, uv_offset
        x, y, z = position
        w, l = width / 2, length / 2
        v = [(x - w, y, z - l), (x + w, y, z - l), (x + w, y, z + l), (x - w, y, z + l)]
        
        for p in v:
            obj_file.write(f"v {p[0]} {p[1]} {p[2]}\n")
        
        for uv in uv_coords:
            obj_file.write(f"vt {uv[0]} {uv[1]}\n")

        obj_file.write(f"usemtl {material}\n")
        obj_file.write(f"f {vertex_offset + 1}/{uv_offset + 1} {vertex_offset + 2}/{uv_offset + 2} {vertex_offset + 3}/{uv_offset + 3}\n")
        obj_file.write(f"f {vertex_offset + 1}/{uv_offset + 1} {vertex_offset + 3}/{uv_offset + 3} {vertex_offset + 4}/{uv_offset + 4}\n")
        vertex_offset += 4
        uv_offset += 4
        
    def add_waypoints(start_pos, end_pos, lane_id):
        waypoints_data["waypoints"][lane_id] = [
            {"x": start_pos[0], "y": start_pos[1], "z": start_pos[2]},
            {"x": end_pos[0], "y": end_pos[1], "z": end_pos[2]},
        ]

    # --- Geração dos Blocos de Rua e Waypoints ---
    for gx in range(GRID_X):
        for gy in range(GRID_Y):
            center_x = gx * DISTANCIA_ENTRE_CRUZAMENTOS
            center_z = gy * DISTANCIA_ENTRE_CRUZAMENTOS
            cruzamento_id = f"{gx}_{gy}"
            
            # --- Cruzamento (Bloco Central) ---
            with open(f"cruzamento_{cruzamento_id}.obj", "w") as f:
                f.write("mtllib rede_viaria.mtl\n\n")
                
                # Asfalto do cruzamento
                create_plane(f, LARGURA_RUA, LARGURA_RUA, (center_x, 0, center_z), "CrossAsphaltMaterial")
                
                # Faixas de pedestre
                crosswalk_len = (LARGURA_FAIXA_PEDESTRE * NUMERO_FAIXAS_PEDESTRE) + (ESPACO_FAIXA_PEDESTRE * (NUMERO_FAIXAS_PEDESTRE - 1))
                pos_z_n = center_z + LARGURA_RUA / 2 + crosswalk_len / 2
                create_plane(f, LARGURA_RUA, crosswalk_len, (center_x, ESPESSURA_RUA, pos_z_n), "CrosswalkMaterial", uv_coords=[(0,1),(1,1),(1,0),(0,0)])
                pos_z_s = center_z - LARGURA_RUA / 2 - crosswalk_len / 2
                create_plane(f, LARGURA_RUA, crosswalk_len, (center_x, ESPESSURA_RUA, pos_z_s), "CrosswalkMaterial", uv_coords=[(0,1),(1,1),(1,0),(0,0)])
                pos_x_l = center_x + LARGURA_RUA / 2 + crosswalk_len / 2
                create_plane(f, crosswalk_len, LARGURA_RUA, (pos_x_l, ESPESSURA_RUA, center_z), "CrosswalkMaterial", uv_coords=[(0,1),(1,1),(1,0),(0,0)])
                pos_x_o = center_x - LARGURA_RUA / 2 - crosswalk_len / 2
                create_plane(f, crosswalk_len, LARGURA_RUA, (pos_x_o, ESPESSURA_RUA, center_z), "CrosswalkMaterial", uv_coords=[(0,1),(1,1),(1,0),(0,0)])
            
            print(f"Malha 'cruzamento_{cruzamento_id}.obj' gerada.")
            
            # --- Vias Horizontais ---
            with open(f"via_horizontal_{cruzamento_id}.obj", "w") as f:
                f.write("mtllib rede_viaria.mtl\n\n")
                
                # Via Leste
                create_plane(f, DISTANCIA_ENTRE_CRUZAMENTOS, LARGURA_RUA, (center_x + DISTANCIA_ENTRE_CRUZAMENTOS/2, 0, center_z), "AsphaltMaterial")
                
                # Via Oeste
                create_plane(f, DISTANCIA_ENTRE_CRUZAMENTOS, LARGURA_RUA, (center_x - DISTANCIA_ENTRE_CRUZAMENTOS/2, 0, center_z), "AsphaltMaterial")
                
            print(f"Malha 'via_horizontal_{cruzamento_id}.obj' gerada.")

            # --- Vias Verticais ---
            with open(f"via_vertical_{cruzamento_id}.obj", "w") as f:
                f.write("mtllib rede_viaria.mtl\n\n")

                # Via Norte
                create_plane(f, LARGURA_RUA, DISTANCIA_ENTRE_CRUZAMENTOS, (center_x, 0, center_z + DISTANCIA_ENTRE_CRUZAMENTOS/2), "AsphaltMaterial")
                
                # Via Sul
                create_plane(f, LARGURA_RUA, DISTANCIA_ENTRE_CRUZAMENTOS, (center_x, 0, center_z - DISTANCIA_ENTRE_CRUZAMENTOS/2), "AsphaltMaterial")
            
            print(f"Malha 'via_vertical_{cruzamento_id}.obj' gerada.")

            # --- Waypoints para cada sentido de via ---
            lane_offset = LARGURA_RUA / 4
            
            # Waypoints Via Norte (Sentido Sul)
            start_n_s = (center_x - lane_offset, 0, center_z + DISTANCIA_ENTRE_CRUZAMENTOS/2 + EXTENSAO_EXTERNA)
            end_n_s = (center_x - lane_offset, 0, center_z + LARGURA_RUA/2)
            add_waypoints(start_n_s, end_n_s, f"waypoint_{cruzamento_id}_N_S")
            
            # Waypoints Via Sul (Sentido Norte)
            start_s_n = (center_x + lane_offset, 0, center_z - DISTANCIA_ENTRE_CRUZAMENTOS/2 - EXTENSAO_EXTERNA)
            end_s_n = (center_x + lane_offset, 0, center_z - LARGURA_RUA/2)
            add_waypoints(start_s_n, end_s_n, f"waypoint_{cruzamento_id}_S_N")

            # Waypoints Via Leste (Sentido Oeste)
            start_l_o = (center_x + DISTANCIA_ENTRE_CRUZAMENTOS/2 + EXTENSAO_EXTERNA, 0, center_z + lane_offset)
            end_l_o = (center_x + LARGURA_RUA/2, 0, center_z + lane_offset)
            add_waypoints(start_l_o, end_l_o, f"waypoint_{cruzamento_id}_L_O")

            # Waypoints Via Oeste (Sentido Leste)
            start_o_l = (center_x - DISTANCIA_ENTRE_CRUZAMENTOS/2 - EXTENSAO_EXTERNA, 0, center_z - lane_offset)
            end_o_l = (center_x - LARGURA_RUA/2, 0, center_z - lane_offset)
            add_waypoints(start_o_l, end_o_l, f"waypoint_{cruzamento_id}_O_L")


            # Spawners de veículos
            scene_layout["spawners_veiculos"].extend([
                {"id": f"spawner_N_{cruzamento_id}", "posicao": {"x": start_n_s[0], "y": 0, "z": start_n_s[2]}, "rotacao": {"x": 0, "y": 0, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_N_S"},
                {"id": f"spawner_S_{cruzamento_id}", "posicao": {"x": start_s_n[0], "y": 0, "z": start_s_n[2]}, "rotacao": {"x": 0, "y": 180, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_S_N"},
                {"id": f"spawner_L_{cruzamento_id}", "posicao": {"x": start_l_o[0], "y": 0, "z": start_l_o[2]}, "rotacao": {"x": 0, "y": -90, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_L_O"},
                {"id": f"spawner_O_{cruzamento_id}", "posicao": {"x": start_o_l[0], "y": 0, "z": start_o_l[2]}, "rotacao": {"x": 0, "y": 90, "z": 0}, "caminho": f"waypoint_{cruzamento_id}_O_L"}
            ])

    with open("scene_layout.json", "w") as f:
        json.dump(scene_layout, f, indent=4)
    print("Arquivo 'scene_layout.json' gerado.")

    with open("waypoints.json", "w") as f:
        json.dump(waypoints_data, f, indent=4)
    print("Arquivo 'waypoints.json' gerado.")

if __name__ == "__main__":
    gerar_arquivos()
# arquivo: TCC_SUMO/src/tcc_sumo/tools/log_analyzer.py
# Ferramenta para analisar arquivos de log gerados pela simulação SUMO e outras partes do sistema.
# Gera uma Dashboard em HTML que consolida e apresenta os logs de forma organizada.
# A Dashboard é salva na pasta 'logs/dashboard_output/' e aberta automaticamente no navegador padrão.

import os
import re
import webbrowser
from datetime import datetime
from collections import Counter
from jinja2 import Environment, FileSystemLoader

# --- Configurações de Caminho ---
# BASE_DIR aponta para a raiz do projeto (TCC_SUMO/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Pasta de saída dentro de 'logs', conforme solicitado
OUTPUT_SUB_DIR_NAME = 'dashboard_output'
OUTPUT_DIR = os.path.join(LOG_DIR, OUTPUT_SUB_DIR_NAME) 

# O template deve estar em TCC_SUMO/templates/
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

def parse_log_line(line):
    """Tenta extrair timestamp, nível, fonte e mensagem de uma linha de log."""
    # Regex para logs com timestamp e nível (e.g., de bibliotecas Python)
    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| (\w+) \| (.*)', line)
    
    if match:
        timestamp_str, level, message = match.groups()
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
        except ValueError:
            timestamp = timestamp_str
        return {'timestamp': timestamp, 'level': level, 'message': message.strip(), 'raw_line': line.strip()}
    
    # Tentativa de inferir o nível para logs não padronizados (e.g., saída direta do SUMO)
    if line.strip():
        upper_line = line.upper()
        level = 'UNKNOWN'
        if 'ERROR' in upper_line:
            level = 'ERROR'
        elif 'WARNING' in upper_line or 'AVISO' in upper_line:
            level = 'WARNING'
        elif 'INFO' in upper_line:
            level = 'INFO'
        return {'timestamp': 'N/A', 'level': level, 'message': line.strip(), 'raw_line': line.strip()}
    return None

def find_all_logs():
    """Retorna uma lista de todos os arquivos de log que devem ser incluídos na Dash."""
    # CORREÇÃO: Incluir todos os arquivos .log, exceto se for o .pyc ou report.json
    logs = [f for f in os.listdir(LOG_DIR) if f.endswith('.log') and 'report_' not in f]
    return logs

def analyze_logs(log_files):
    """Lê e analisa múltiplos arquivos de log do diretório LOG_DIR."""
    all_logs = []
    
    for filename in log_files:
        filepath = os.path.join(LOG_DIR, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                parsed = parse_log_line(line)
                if parsed:
                    parsed['source_file'] = filename
                    all_logs.append(parsed)

    log_levels = [log['level'] for log in all_logs if log['level'] != 'UNKNOWN']
    level_counts = Counter(log_levels)
    
    # Prepara os dados para o template
    logs_for_template = [
        {
            'timestamp': log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(log['timestamp'], datetime) else log['timestamp'],
            'level': log['level'],
            'message': log['message'],
            'source_file': log['source_file']
        }
        for log in all_logs
    ]
    
    return logs_for_template, dict(level_counts)

def generate_log_dashboard(logs_data, stats_data, all_source_logs, output_filename='log_dashboard.html', template_filename='log_dashboard.html'):
    """Gera a Dashboard de Logs em HTML."""
    
    # 1. Cria diretórios (Garante que as pastas existam)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMPLATE_DIR, exist_ok=True)

    # 2. Configura o ambiente Jinja2
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    try:
        template = env.get_template(template_filename)
    except Exception as e:
        print(f"ERRO: Não foi possível carregar o template {template_filename}. Erro: {e}")
        return None

    # 3. Renderiza o template com a lista de todos os arquivos de log
    rendered_html = template.render(
        timestamp_geracao=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        logs=logs_data,
        stats=stats_data,
        total_logs=len(logs_data),
        # Passa a lista de todos os arquivos de log para o menu da Dash
        all_source_logs=all_source_logs 
    )

    # 4. Salva o arquivo HTML
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    return output_path


def generate_and_open_log_dashboard():
    """
    Função principal que executa a análise, checklist, geração e abertura do Dashboard.
    """
    print("\n--- Analisador de Logs SUMO ---")
    
    # Passo 1: Encontrar logs
    print(" [ ] Passo 1: Localizando arquivos de Log relevantes...")
    all_source_logs = find_all_logs()
    
    if not all_source_logs:
        print(" [X] FALHA: Nenhum arquivo de log (.log) encontrado na pasta 'logs/'.")
        print("            Execute a Opção 1 antes de gerar a Dashboard.")
        return
    print(f" [✓] Passo 1: {len(all_source_logs)} arquivo(s) de log encontrado(s).")
    
    # Passo 2: Analisar Logs
    print(" [ ] Passo 2: Analisando e consolidando dados de Log...")
    logs_data, stats_data = analyze_logs(all_source_logs)
    
    if not logs_data:
        print(" [X] FALHA: Nenhum dado de log válido para processamento.")
        return
    print(f" [✓] Passo 2: Análise concluída. {len(logs_data)} entradas consolidadas.")

    # Passo 3: Gerar e salvar a Dashboard
    print(" [ ] Passo 3: Gerando e salvando o arquivo HTML da Dashboard...")
    output_path = generate_log_dashboard(logs_data, stats_data, all_source_logs)
    
    if not output_path:
        print(" [X] FALHA: Não foi possível gerar o arquivo HTML. Verifique o template.")
        return
    
    # Confirma a padronização na estrutura de saída
    print(f" [✓] Passo 3: Arquivo salvo em: {os.path.join('logs', OUTPUT_SUB_DIR_NAME, os.path.basename(output_path))}")
    
    # Passo 4: Abrir no Navegador
    print(" [ ] Passo 4: Abrindo Dashboard no navegador padrão...")
    url = 'file://' + os.path.abspath(output_path)
    webbrowser.open(url)
    print(" [✓] Passo 4: Dashboard Aberta com Sucesso.")
    print("\n--- Processo Concluído ---")
    

if __name__ == '__main__':
    generate_and_open_log_dashboard()
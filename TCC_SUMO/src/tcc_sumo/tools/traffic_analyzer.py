# -*- coding: utf-8 -*-
"""Módulo para análise de dados e geração de dashboards."""

import argparse
import json
import logging
import os
import re
from collections import Counter

logger = logging.getLogger(__name__)


def generate_traffic_dashboard(data_file: str, output_file: str):
    # TODO: Implementação futura do dashboard de tráfego.
    print(f"Lendo arquivo de dados: {data_file}")
    if not os.path.exists(data_file):
        print(f"ERRO: Arquivo de dados '{data_file}' não encontrado.")
        return
    print(f"Dashboard de Tráfego (em desenvolvimento) salvo em: {output_file}")


def generate_log_dashboard(log_file: str, output_file: str):
    """Lê o simulation.log e gera um dashboard HTML interativo e estilizado."""
    print(f"Lendo arquivo de log: {log_file}")
    if not os.path.exists(log_file):
        print(f"ERRO: Arquivo de log '{log_file}' não encontrado.")
        return

    log_entries = []
    log_pattern = re.compile(r'\[(.*?)\]\s+\[(.*?)\s*\]\s+\[(.*?)\s*\]\s+:\s+(.*)')
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = log_pattern.match(line)
            if match:
                log_entries.append({
                    "timestamp": match.group(1), "level": match.group(2),
                    "module": match.group(3).strip(), "message": match.group(4)
                })

    level_counts = Counter(entry['level'] for entry in log_entries)
    table_rows_html = ""
    for entry in log_entries:
        level = entry['level']
        controller_class = "controller-log" if "controller" in entry['module'].lower() else ""
        table_rows_html += f"""
        <tr data-level="{level}" class="log-row {controller_class}">
            <td class="ps-3">{entry['timestamp']}</td>
            <td class="log-level-{level}">{level}</td>
            <td>{entry['module']}</td>
            <td>{entry['message']}</td>
        </tr>
        """
    
    html_template = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Logs - TCC SUMO</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        body {{ background-color: #f8f9fa; }}
        .log-level-INFO {{ color: #0d6efd; }}
        .log-level-WARNING {{ color: #ffc107; font-weight: bold; }}
        .log-level-ERROR, .log-level-CRITICAL {{ color: #dc3545; font-weight: bold; }}
        .log-level-DEBUG {{ color: #6c757d; }}
        .controller-log {{ border-left: 3px solid #0d6efd; }}
        .stat-card {{ cursor: pointer; transition: all 0.2s ease-in-out; }}
        .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        .stat-card.active {{
            transform: translateY(-5px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            border-width: 2px;
        }}
    </style>
</head>
<body>
    <div class="container mt-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1 class="mb-0">Dashboard de Logs</h1>
                <p class="lead mb-0">Análise do arquivo: <strong>{os.path.basename(log_file)}</strong></p>
            </div>
            <i class="bi bi-terminal-fill text-muted" style="font-size: 3rem;"></i>
        </div>

        <div class="row text-center mb-4 g-3">
            <div class="col"><div id="card-INFO" class="card stat-card border-info" onclick="filterLogs('INFO')"><div class="card-body"><h5 class="card-title text-info">INFO</h5><p class="card-text fs-2 text-info">{level_counts.get('INFO', 0)}</p></div></div></div>
            <div class="col"><div id="card-WARNING" class="card stat-card border-warning" onclick="filterLogs('WARNING')"><div class="card-body"><h5 class="card-title text-warning">WARNING</h5><p class="card-text fs-2 text-warning">{level_counts.get('WARNING', 0)}</p></div></div></div>
            <div class="col"><div id="card-ERROR" class="card stat-card border-danger" onclick="filterLogs('ERROR')"><div class="card-body"><h5 class="card-title text-danger">ERROR</h5><p class="card-text fs-2 text-danger">{level_counts.get('ERROR', 0)}</p></div></div></div>
            <div class="col"><div id="card-CRITICAL" class="card stat-card border-dark" onclick="filterLogs('CRITICAL')"><div class="card-body"><h5 class="card-title text-dark">CRITICAL</h5><p class="card-text fs-2 text-dark">{level_counts.get('CRITICAL', 0)}</p></div></div></div>
        </div>

        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">Registros de Log Detalhados<button class="btn btn-secondary btn-sm" onclick="filterLogs('ALL')">Mostrar Todos</button></div>
            <div class="card-body p-0"><div class="table-responsive"><table class="table table-striped table-hover table-sm mb-0"><thead class="table-light"><tr><th scope="col" class="ps-3">Timestamp</th><th scope="col">Nível</th><th scope="col">Módulo</th><th scope="col">Mensagem</th></tr></thead><tbody id="log-table-body">{table_rows_html}</tbody></table></div></div>
        </div>
    </div>
    <script>
        let currentFilter = 'ALL';
        function filterLogs(level) {{
            const tableRows = document.querySelectorAll('#log-table-body .log-row');
            const cards = document.querySelectorAll('.stat-card');
            if (level === currentFilter) {{ level = 'ALL'; }}
            currentFilter = level;
            cards.forEach(card => {{ card.classList.toggle('active', card.id === 'card-' + level); }});
            tableRows.forEach(row => {{
                if (level === 'ALL' || row.dataset.level === level) {{ row.style.display = ''; }} 
                else {{ row.style.display = 'none'; }}
            }});
        }}
    </script>
</body>
</html>
    """

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print(f"Dashboard de Logs gerado com sucesso em: {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Gerador de Dashboards de Análise")
    parser.add_argument('--source', type=str, required=True, choices=['logs', 'traffic'])
    args = parser.parse_args()

    if args.source == 'logs':
        generate_log_dashboard('logs/simulation.log', 'output/log_dashboard.html')
    elif args.source == 'traffic':
        generate_traffic_dashboard('output/consolidated_data.json', 'output/traffic_dashboard.html')
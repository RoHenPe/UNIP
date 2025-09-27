```markdown
# Projeto de Simulação de Tráfego Inteligente com SUMO (TCC)

## 1. Visão Geral

Este projeto implementa e valida um sistema de controle de tráfego adaptativo. A missão é comparar empiricamente a eficiência de um controlador de semáforos de tempo fixo (`CONSERVATIVE`) com um agente de controle dinâmico (`DYNAMIC`) que utiliza dados da simulação em tempo real para tomar decisões.

O objetivo final é criar um sistema que não apenas funcione, mas que também sirva como uma plataforma educacional clara e bem documentada para o estudo de sistemas inteligentes, teoria de filas e otimização de fluxo em redes complexas.

## 2. Funcionalidades Principais

-   **Dois Modos de Operação**: Execute simulações no modo `CONSERVATIVE` (tempos fixos) ou `DYNAMIC` (IA adaptativa).
-   **Controle Inteligente**: A lógica dinâmica monitora as filas de veículos e estende o tempo do sinal verde para otimizar o fluxo e reduzir congestionamentos.
-   **Estrutura Profissional**: O código é organizado em um pacote Python, separando configurações, lógica e execução para fácil manutenção.
-   **Configuração Centralizada**: Todos os parâmetros da simulação (semáforos, cenários, portas) são gerenciados no arquivo `config/config.yaml`.
-   **Logging Detalhado**: Geração de logs completos para análise de performance e depuração, com dados de cada viagem (duração, tempo perdido, etc.).

## 3. Arquitetura do Projeto

A estrutura foi desenhada para ser modular e escalável, seguindo as melhores práticas de desenvolvimento em Python.

```

TCC\_SUMO/
│
├── config/
│   ├── config.yaml
│   └── logging\_config.json
│
├── logs/
│   └── (Gerado automaticamente)
│
├── scenarios/
│   ├── from\_api/
│   └── from\_osm/
│
├── scripts/
│   └── run\_simulation.sh
│
└── src/
├── main.py
└── tcc\_sumo/
├── **init**.py
├── simulation/
│   ├── **init**.py
│   ├── manager.py
│   └── traci\_connection.py
├── tools/
│   ├── **init**.py
│   ├── reporter.py
│   └── scenario\_generator.py
├── traffic\_logic/
│   ├── **init**.py
│   └── controllers.py
└── utils/
├── **init**.py
└── helpers.py

````

-   **/config**: Centraliza todas as configurações. `config.yaml` para parâmetros da simulação e `logging_config.json` para o formato dos logs.
-   **/scripts**: Contém o orquestrador `run_simulation.sh`, a interface de linha de comando para o usuário final.
-   **/src**: Abriga todo o código-fonte Python.
    -   `main.py`: Ponto de entrada que inicializa a simulação com os argumentos fornecidos.
    -   **/tcc_sumo**: O coração do projeto, estruturado como um pacote Python.
        -   **/simulation**: Módulos que gerenciam a interação com o SUMO.
        -   **/traffic_logic**: Onde reside a inteligência artificial do sistema. `controllers.py` contém a lógica que diferencia o modo `DYNAMIC` do `CONSERVATIVE`.
        -   **/utils**: Funções de suporte para tarefas como carregar configurações.
        -   **/tools**: Ferramentas adicionais, como o gerador de cenários e relatórios.

### O Papel do `__init__.py`

Você notará que cada subdiretório dentro de `src/tcc_sumo` contém um arquivo `__init__.py`. Este arquivo é fundamental: ele diz ao Python que a pasta deve ser tratada como um "pacote" (ou "módulo"). Isso permite a importação estruturada de módulos (`from tcc_sumo.simulation.manager import SimulationManager`), tornando o código organizado, modular e reutilizável.

## 4. Princípios de Operação do Controle Adaptativo (IA)

O núcleo da inovação deste projeto reside no arquivo `src/tcc_sumo/traffic_logic/controllers.py`. A lógica do modo `DYNAMIC` opera sob os seguintes princípios:

1.  **Segurança em Primeiro Lugar (Safety-First Principle)**: O ciclo de fases (`VERDE -> AMARELO -> VERMELHO`) é inviolável. A IA nunca tentará pular a fase amarela ou criar um estado inseguro. As durações das fases amarela e vermelha são fixas.
2.  **Otimização Baseada em Evidências (Data-Driven Decisions)**: A decisão de estender um sinal verde é baseada em dados. O controlador monitora as `lanes` associadas a uma fase verde ativa, utilizando a função `traci.lane.getLastStepHaltingNumber()` para obter o número de veículos parados.
3.  **Extensão Adaptativa (Adaptive Extension)**: Se uma fase verde está prestes a terminar, mas a telemetria indica veículos em fila (`getLastStepHaltingNumber > 0`), a IA concede uma pequena "extensão de tempo" à fase verde, adiando a transição para permitir que a fila se dissipe.
4.  **Eficiência de Recursos (Resource Efficiency)**: Se não há veículos esperando, estender a fase verde seria um desperdício. Nesse caso, a IA permite que a transição para a fase amarela ocorra normalmente, liberando o cruzamento para o próximo fluxo de tráfego.

## 5. Pré-requisitos

1.  **SUMO**: A plataforma de simulação de tráfego. Garanta que o executável esteja no `PATH` do sistema ou que a variável de ambiente `$SUMO_HOME` esteja configurada.
    -   *Verificação*: `sumo-gui`
2.  **Python**: Versão 3.8 ou superior.
    -   *Verificação*: `python3 --version`
3.  **PyYAML**: Biblioteca para ler arquivos `.yaml`.
    -   *Instalação*: `pip install pyyaml`

## 6. Instalação

1.  Clone o repositório ou descompacte os arquivos.
2.  Verifique o arquivo `config/config.yaml` e ajuste os parâmetros (especialmente as `lanes` de cada semáforo) para corresponder ao seu cenário.
3.  Dê permissão de execução ao script principal:
    ```bash
    chmod +x scripts/run_simulation.sh
    ```

## 7. Como Executar

A execução é gerenciada pelo script `run_simulation.sh`.

1.  Abra um terminal na pasta raiz do projeto (`TCC_SUMO/`).
2.  Execute o script:
    ```bash
    ./scripts/run_simulation.sh
    ```
3.  O script irá guiá-lo com um menu interativo:
    -   **Passo 1**: Escolha o modo de controle (`DYNAMIC` ou `CONSERVATIVE`).
    -   **Passo 2**: Escolha o cenário (`from_osm` ou `from_api`).
    -   **Passo 3**: Digite o número de passos da simulação (ex: `3600` para 1 hora).

A janela do `sumo-gui` será aberta, e a simulação começará. Os logs serão exibidos no terminal e salvos em `logs/simulation.log`.

## 8. Análise de Resultados

A eficácia da IA é medida pela análise dos dados de viagem no arquivo `logs/simulation.log`. Cada linha relevante segue o formato:

`TRIP_DATA;ID=[ID_VEICULO];duration=[DURACAO];timeLoss=[TEMPO_PERDIDO];waitingTime=[TEMPO_PARADO]`

Para comparar os modos, execute a simulação uma vez em cada modo (com o mesmo número de passos) e compare as médias das métricas `timeLoss` e `waitingTime`. Uma redução significativa nesses valores no modo `DYNAMIC` comprova a eficiência do controle adaptativo.
````
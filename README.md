# ALWABP Solver

O projeto apresenta uma implementação para o problema **ALWABP** (Assembly Line Worker Assignment and Balancing Problem), que consiste na alocação e balanceamento de tarefas em linhas de produção considerando as características individuais dos trabalhadores. 

O trabalho foi desenvolvido como parte das atividades das disciplinas **GCC118 – Programação Matemática** e **PCC540 – Linear and Integer Programming**, oferecidas pela Universidade Federal de Lavras (UFLA). 

Grupo responsável pelo desenvolvimento:
- Marcos Carvalho Ferreira
- Luiz Otávio Andrade Soares
- Douglas Giovani de Paiva Mosca Leite.

Para informações detalhadas sobre a metodologia, fundamentação teórica e contextualização do problema, encontra-se disponível o relatório técnico em `Relatório_Programação_Matemática/Relatório_Programação_Matemática.pdf`.

## Estrutura do Projeto

```
.
├── README.md                         # Este arquivo
├── .gitignore                        # Arquivo para evitar rastreio do git
├── requirements.txt                  # Arquivo com as dependências do projeto
├── gurobi_model.py                   # Modelo exato usando Gurobi
├── ils_model.py                      # Implementação do ILS
├── optimize_params.py                # Otimização de hiperparâmetros (Optuna)
├── run_experiments.py                # Execução em lote de experimentos
├── instances.csv                     # Metadados das instâncias
├── instancias_teste_relatorio.txt    # Instâncias selecionadas para o relatório
├── initial_params.yaml               # Parâmetros do ILS iniciais
├── best_params.yaml                  # Parâmetros do ILS otimizados encontrados
├── alwabp/                           # Diretório com arquivos de instâncias
├── solutions/                        # Diretório de saídas
│   ├── gurobi/                       # Soluções do Gurobi
│   └── ils/                          # Soluções do ILS
├── documets/                         # Diretório com o enunciado do trabalho e outros documentos
│   └── ...                          
├── Relatório_Programação_Matemática/ # Diretório do relatório em latex                   
│   └── ... 
├── results.csv                      # Resultados agregados
└── results_ils_single_results.csv   # Resultados individuais de cada replicação do ILS
```

## Requisitos

**1. Python 3.8+**

**2. GurobiPy:** É necessário ter uma licença válida do Gurobi instalada. Acadêmicos podem obter licenças gratuitas em [gurobi.com](https://www.gurobi.com/academia/academic-program-and-licenses/).

**3. PyYAML**

**4. Optuna**

## Instalação

### 1. Criar e ativar o ambiente virtual do Python

No Windows:

```powershell
python -m venv venv
Set-ExecutionPolicy Unrestricted -Scope Process
.\venv\Scripts\activate
```

No Linux/Mac:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar as dependências

```bash
python -m pip install -r requirements.txt
```

### Ativação do ambiente virtual

Sempre que for usar o script Python, ative o ambiente virtual:

No Windows:

```powershell
Set-ExecutionPolicy Unrestricted -Scope Process
.\venv\Scripts\activate
```

No Linux/Mac:

```bash
source venv/bin/activate
```

## Utilização dos Scripts

### 1. Executar o Modelo Gurobi

```bash
# Solução básica
python3 gurobi_model.py < alwabp/20_hes

# Com limite de tempo e salvamento de solução
python3 gurobi_model.py solution.txt --max-time 300 --verbose < alwabp/20_hes
```

**Parâmetros:**
- `output_file`: Arquivo para salvar a solução (opcional)
- `--max-time T`: Tempo máximo em segundos (default: 300)
- `--verbose`: Exibe informações detalhadas

**Saída:**
- Tempo de ciclo ótimo
- Atribuição de trabalhadores às estações
- Detalhamento de tarefas por estação
- Estatísticas de utilização e balanceamento

### 2. Executar o ILS (Iterated Local Search)

```bash
# Execução básica
python3 ils_model.py < alwabp/20_hes

# Com todos os parâmetros
python3 ils_model.py solution_ils.txt \
    --seed 42 \
    --max-time 500 \
    --optimal-value 316 \
    --adaptive-timeout \
    --initial-temp-factor 0.1 \
    --cooling-rate 0.95 \
    --perturbation-initial 2 \
    --perturbation-max 5 \
    --improvement-threshold 50 \
    --stagnation-threshold 1000 \
    --verbose \
    < alwabp/20_hes
```

**Parâmetros principais:**
- `output_file`: Arquivo de saída (opcional)
- `--seed S`: Seed para reprodutibilidade
- `--max-time T`: Tempo máximo em segundos (default: 300)
- `--optimal-value V`: Valor ótimo conhecido (ativa early stopping)
- `--adaptive-timeout`: Ativa ajuste automático de timeout
- `--verbose`: Modo verboso com progresso detalhado

**Parâmetros do ILS:**
- `--initial-temp-factor F`: Fator de temperatura inicial (default: 0.1)
- `--cooling-rate R`: Taxa de resfriamento (default: 0.95)
- `--perturbation-initial P`: Força inicial de perturbação (default: 2)
- `--perturbation-max M`: Força máxima de perturbação (default: 5)
- `--improvement-threshold I`: Iterações sem melhoria antes de aumentar perturbação (default: 50)
- `--stagnation-threshold S`: Iterações de estagnação antes de restart (default: 1000)

#### Componentes do ILS:
1. **Solução Inicial**: Heurística RPW (Ranked Positional Weight)
2. **Busca Local**: VND (Variable Neighborhood Descent)
   - Movimentação de tarefas entre estações
   - Troca de tarefas entre estações
3. **Perturbação**: Força adaptativa baseada em estagnação
4. **Aceitação**: Simulated Annealing

#### Fluxo Principal

```
1. Gerar solução inicial (RPW + VND)
2. Enquanto não atingir critério de parada:
   a. Perturbar solução atual
   b. Aplicar busca local (VND)
   c. Aceitar ou rejeitar (Simulated Annealing)
   d. Atualizar melhor solução se necessário
   e. Adaptar parâmetros (temperatura, perturbação)
   f. Restart se estagnado
3. Retornar melhor solução encontrada
```

#### Estratégias Adaptativas

1. **Perturbação Dinâmica**: Aumenta a força quando estagnado
2. **Restart Automático**: Gera nova solução inicial após estagnação prolongada
3. **Early Stopping**: Para quando atinge o ótimo conhecido (dentro de tolerância)
4. **Timeout Adaptativo**: Aumenta tempo se está melhorando consistentemente

### 3. Otimizar Hiperparâmetros

```bash
# Otimização automática usando Optuna
python3 optimize_params.py \
    --instance alwabp/72_ton \
    --optimal-value 57 \
    --n-trials 20 \
    --time-limit 300 \
    --output best_params.yaml \
    --n-jobs 4
```

**Parâmetros:**
- `--instance`: Arquivo de instância para otimização
- `--optimal-value`: Valor ótimo conhecido (opcional, mas recomendado)
- `--n-trials`: Número de combinações a testar (default: 20)
- `--time-limit`: Tempo limite por trial em segundos (default: 300)
- `--output`: Arquivo YAML de saída (default: best_params.yaml)
- `--n-jobs`: Número de processos paralelos (default: 1)

**Saída:**
- Arquivo YAML com os melhores parâmetros encontrados
- Relatório de otimização com estatísticas

### 4. Executar Experimentos

```bash
python3 run_experiments.py
```

Este script executa automaticamente:
1. Carrega instâncias de `instancias_teste_relatorio.txt`
2. Executa Gurobi em cada instância (timeout: 700s)
3. Executa ILS com 5 replicações diferentes (timeout: 700s)
4. Salva todas as soluções em `solutions/`
5. Gera relatórios CSV:
   - `results.csv`: Resultados agregados
   - `results_ils_single_results.csv`: Resultados individuais de cada replicação

**Configuração do batch:**
Editar variáveis no início de `run_experiments.py`:
```python
num_replications = 5        # Número de execuções do ILS por instância
ils_timeout = 700          # Timeout do ILS
gurobi_timeout = 700       # Timeout do Gurobi
config_file = 'best_params.yaml'  # Arquivo de parâmetros
```

## Formato dos Arquivos

### Formato de Instância

```
n k
t_11 t_12 ... t_1k
t_21 t_22 ... t_2k
...
t_n1 t_n2 ... t_nk
m
w1 i1 i2 ... iq
w2 j1 j2 ... jr
...
p
i1 j1
i2 j2
...
```

Onde:
- `n`: número de tarefas
- `k`: número de trabalhadores/estações
- `t_ij`: tempo para trabalhador j executar tarefa i
- `m`: número de linhas de incapacidades
- `w_x i_1 ... i_q`: trabalhador w não pode executar tarefas i_1, ..., i_q
- `p`: número de precedências
- `i j`: tarefa i deve preceder tarefa j

### Formato de Seleção de Instâncias

Arquivo `instancias_teste_relatorio.txt`:
```
heskia    20
heskia    28
roszieg   25
tonge     20
wee-mag   28
```

### Arquivo CSV de Resultados Agregados

`results.csv` contém estatísticas consolidadas de todas as replicações:

| Coluna | Descrição |
|--------|-----------|
| `instance` | Nome da instância (ex: "20_hes") |
| `name` | Nome da família (ex: "heskia") |
| `num` | Número da instância |
| `n_tasks` | Número de tarefas |
| `n_workers` | Número de trabalhadores |
| `UB` | Upper bound conhecido |
| `gurobi_ct` | Tempo de ciclo Gurobi |
| `gurobi_time` | Tempo de execução Gurobi (segundos) |
| `ils_replications` | Número de replicações ILS |
| `ils_avg_initial_ct` | Tempo de ciclo inicial médio |
| `ils_avg_final_ct` | Tempo de ciclo final médio |
| `ils_best_ct` | Melhor tempo de ciclo encontrado |
| `ils_worst_ct` | Pior tempo de ciclo encontrado |
| `ils_avg_time` | Tempo médio de execução (segundos) |
| `ils_improvement_pct` | Melhoria percentual (inicial -> final) |

### Arquivo CSV de Resultados Individuais do ILS

`results_ils_single_results.csv` contém os resultados detalhados de cada replicação individual do ILS:

| Coluna | Descrição |
|--------|-----------|
| `instance` | Nome da instância (ex: "20_hes") |
| `name` | Nome da família (ex: "heskia") |
| `num` | Número da instância |
| `seed` | Seed utilizada na replicação (ex: 10, 11, 12, 13, 14) |
| `initial_ct` | Tempo de ciclo da solução inicial (RPW) |
| `final_ct` | Tempo de ciclo da solução final (após ILS) |
| `time` | Tempo de execução em segundos |
| `solution_file` | Caminho para o arquivo de solução detalhada |

"""
Iterated Local Search (ILS) para ALWABP
Assembly Line Worker Assignment and Balancing Problem
(Problema de Atribuição de Trabalhadores e Balanceamento de Linha de Montagem)

Componentes do ILS:
1. Solução Inicial: Heurística construtiva gulosa (RPW)
2. Busca Local: Variable Neighborhood Descent (VND)
3. Perturbação: Realocação de tarefas e troca de trabalhadores
4. Critério de Aceitação: Baseado em Simulated Annealing
"""

import sys
import random
import math
import time
from copy import deepcopy

class ALWABPInstance:
    def __init__(self, n, k, times, incapabilities, precedences):
        self.n = n  # Número de tarefas
        self.k = k  # Número de trabalhadores/estações
        self.times = times  # times[i][w] = tempo para trabalhador w fazer tarefa i
        self.incapabilities = incapabilities  # Tarefas que cada trabalhador não pode fazer
        self.precedences = precedences  # Lista de tuplas (i, j) indicando precedências
        
        # Pré-computar relacionamentos de precedência para acesso rápido
        self.successors = {i: [] for i in range(n)} # sucessores de cada tarefa
        self.predecessors = {i: [] for i in range(n)} # predecessores de cada tarefa
        for i, j in precedences:
            self.successors[i].append(j)
            self.predecessors[j].append(i)
        
        # Calcular pesos posicionais para a heurística RPW
        self.positional_weights = self._calculate_positional_weights()
    
    def _calculate_positional_weights(self):
        """
        Calcula o Ranked Positional Weight (RPW) para cada tarefa.
        RPW = duração da tarefa + soma das durações de todos os seus sucessores
        
        Este método ajuda a priorizar tarefas que têm impacto maior no fluxo de produção.
        Tarefas com maior RPW são mais "críticas" e devem ser alocadas primeiro.
        """
        weights = {}
        
        # Calcular tempo médio para cada tarefa (considerando apenas trabalhadores capazes)
        avg_times = []
        for i in range(self.n):
            valid_times = [t for t in self.times[i] if t != float('inf')]
            avg_time = sum(valid_times) / len(valid_times) if valid_times else 0
            avg_times.append(avg_time)
        
        # Calcular peso posicional usando ordem topológica
        def calculate_weight(task, memo):
            # Função recursiva com memoização para calcular o peso
            if task in memo:
                return memo[task]
            
            # Peso = tempo da tarefa + soma dos pesos de todos os sucessores
            weight = avg_times[task]
            for succ in self.successors[task]:
                weight += calculate_weight(succ, memo)
            
            memo[task] = weight
            return weight
        
        memo = {}
        for i in range(self.n):
            weights[i] = calculate_weight(i, memo)
        
        return weights
    
    def can_assign(self, task, worker):
        # Verifica se um trabalhador pode executar uma tarefa
        return worker not in self.incapabilities or task not in self.incapabilities[worker]
    
    def get_task_time(self, task, worker):
        # Retorna o tempo necessário para um trabalhador executar uma tarefa
        if not self.can_assign(task, worker):
            return float('inf')
        return self.times[task][worker]

class Solution:

    def __init__(self, instance):
        self.instance = instance
        self.task_assignment = {}  # tarefa -> (estação, trabalhador)
        self.station_worker = {}   # estação -> trabalhador alocado
        self.station_tasks = {s: [] for s in range(instance.k)} # estação -> lista de tarefas
        self.cycle_time = float('inf') # tempo de ciclo (objetivo a minimizar)
    
    def copy(self):
        new_sol = Solution(self.instance)
        new_sol.task_assignment = self.task_assignment.copy()
        new_sol.station_worker = self.station_worker.copy()
        new_sol.station_tasks = {s: tasks[:] for s, tasks in self.station_tasks.items()}
        new_sol.cycle_time = self.cycle_time
        return new_sol
    
    def calculate_cycle_time(self):
        """
        Calcula o tempo de ciclo da solução.
        O tempo de ciclo é o tempo máximo gasto em qualquer estação,
        pois determina a velocidade da linha de produção.
        """
        max_time = 0
        for station in range(self.instance.k):
            worker = self.station_worker.get(station)
            if worker is None:
                continue
            station_time = sum(
                self.instance.get_task_time(task, worker)
                for task in self.station_tasks[station]
            )
            max_time = max(max_time, station_time)
        self.cycle_time = max_time
        return max_time
    
    def is_feasible(self):
        """
        Verifica se a solução satisfaz todas as restrições:
        1. Todas as tarefas foram atribuídas
        2. Precedências são respeitadas
        3. Trabalhadores são capazes de executar suas tarefas
        """
        # Verificar se todas as tarefas foram atribuídas
        if len(self.task_assignment) != self.instance.n:
            return False
        
        # Verificar restrições de precedência
        for i, j in self.instance.precedences:
            if i not in self.task_assignment or j not in self.task_assignment:
                return False
            station_i, _ = self.task_assignment[i]
            station_j, _ = self.task_assignment[j]
            if station_i > station_j:
                return False
        
        # Verificar capacidades dos trabalhadores
        for task, (station, worker) in self.task_assignment.items():
            if not self.instance.can_assign(task, worker):
                return False
        
        return True
    
    def get_station_time(self, station):
        worker = self.station_worker.get(station)
        if worker is None:
            return 0
        return sum(
            self.instance.get_task_time(task, worker)
            for task in self.station_tasks[station]
        )
    
    def print_solution(self):
        n = self.instance.n
        k = self.instance.k
        cycle_time = self.cycle_time
        times = self.instance.times
        
        print("=" * 70)
        print("ALWABP SOLUTION - ILS")
        print("=" * 70)
        print(f"\n✓ BEST CYCLE TIME FOUND: {cycle_time:.2f}")
        print(f"  Number of tasks: {n}")
        print(f"  Number of workers/stations: {k}")
        print()
        
        stations_data = {}
        for station in range(k):
            worker = self.station_worker[station]
            tasks = self.station_tasks[station]
            
            stations_data[station] = {
                'worker': worker,
                'tasks': []
            }
            
            for task_id in tasks:
                task_time = self.instance.get_task_time(task_id, worker)
                stations_data[station]['tasks'].append((task_id, task_time))
        
        print("-" * 70)
        print("STATION ASSIGNMENTS")
        print("-" * 70)
        
        for station in sorted(stations_data.keys()):
            data = stations_data[station]
            worker = data['worker']
            tasks = sorted(data['tasks'], key=lambda x: x[0])
            
            station_time = sum(t for _, t in tasks)
            utilization = (station_time / cycle_time) * 100 if cycle_time > 0 else 0
            idle_time = cycle_time - station_time
            
            print(f"\n┌─ STATION {station} (Worker {worker}) " + "─" * (70 - len(f"STATION {station} (Worker {worker}) ") - 3))
            print(f"│")
            print(f"│  Tasks assigned: {len(tasks)}")
            print(f"│  Total time:     {station_time:.2f}")
            print(f"│  Idle time:      {idle_time:.2f}")
            print(f"│  Utilization:    {utilization:.1f}%")
            print(f"│")
            print(f"│  Task Details:")
            
            for task_id, task_time in tasks:
                print(f"│    • Task {task_id:3d}  →  Time: {task_time:6.2f}")
            
            bar_length = 50
            filled = int((station_time / cycle_time) * bar_length) if cycle_time > 0 else 0
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"│")
            print(f"│  [{bar}] {utilization:.1f}%")
            print(f"└" + "─" * 69)

        print("\n" + "=" * 70)
        print("SUMMARY STATISTICS")
        print("=" * 70)
        
        total_task_time = sum(sum(t for _, t in data['tasks']) for data in stations_data.values())
        total_available_time = cycle_time * k
        overall_utilization = (total_task_time / total_available_time) * 100 if total_available_time > 0 else 0
        total_idle = total_available_time - total_task_time
        
        print(f"\n  Total task time:       {total_task_time:.2f}")
        print(f"  Total available time:  {total_available_time:.2f}")
        print(f"  Total idle time:       {total_idle:.2f}")
        print(f"  Overall utilization:   {overall_utilization:.1f}%")
        print(f"  Line efficiency:       {overall_utilization:.1f}%")
        
        station_times = [sum(t for _, t in data['tasks']) for data in stations_data.values()]
        if station_times:
            min_time = min(station_times)
            max_time = max(station_times)
            balance_index = (max_time - min_time) / cycle_time * 100 if cycle_time > 0 else 0
            print(f"  Balance index:         {balance_index:.1f}% (lower is better)")
        
        print("\n" + "=" * 70)
        
        print(f"\nCYCLE_TIME: {int(round(cycle_time))}")

def construct_rpw_solution(instance):
    """
    SOLUÇÃO INICIAL
    
    Heurística RPW (Ranked Positional Weight) - Helgeson & Birnie (1961)
    
    Processo:
    1. Ordena as tarefas por peso posicional (maior primeiro)
    2. Atribui trabalhadores aleatoriamente às estações
    3. Para cada tarefa (em ordem de prioridade):
       - Verifica precedências
       - Encontra a melhor estação disponível
       - Atribui a tarefa minimizando o tempo de ciclo
    """
    solution = Solution(instance)
    
    # Atribuir trabalhadores às estações (embaralhamento aleatório inicial)
    workers = list(range(instance.k))
    random.shuffle(workers)
    for station, worker in enumerate(workers):
        solution.station_worker[station] = worker
    
   # Ordenar tarefas por peso posicional (ordem decrescente - maior prioridade primeiro)
    sorted_tasks = sorted(
        range(instance.n),
        key=lambda t: instance.positional_weights[t],
        reverse=True
    )
    
    # Atribuir tarefas seguindo a ordem RPW
    assigned = set()
    for task in sorted_tasks:
        if task in assigned:
            continue
        
        # Verificar se todos os predecessores já foram atribuídos
        if not all(pred in assigned for pred in instance.predecessors[task]):
            continue
        
        # Encontrar a melhor estação para esta tarefa
        best_station = None
        best_score = float('inf')
        
        for station in range(instance.k):
            worker = solution.station_worker[station]
            
            # Verificar se o trabalhador pode executar esta tarefa
            if not instance.can_assign(task, worker):
                continue
            
            # Verificar precedência: todos os predecessores devem estar em estação anterior ou igual
            valid = True
            for pred in instance.predecessors[task]:
                if pred in solution.task_assignment:
                    pred_station, _ = solution.task_assignment[pred]
                    if pred_station > station:
                        valid = False
                        break
            
            if not valid:
                continue
            
            # Calcular novo tempo da estação se adicionarmos esta tarefa
            task_time = instance.get_task_time(task, worker)
            current_time = solution.get_station_time(station)
            new_time = current_time + task_time
            
            # Preferir estações com menor carga (balanceamento de carga)
            if new_time < best_score:
                best_score = new_time
                best_station = station
        
        if best_station is None:
            # Se nenhuma atribuição viável foi encontrada, tentar reatribuir trabalhadores
            for station in range(instance.k):
                for worker in range(instance.k):
                    if worker == solution.station_worker[station]:
                        continue
                    
                    # Verificar se este trabalhador pode fazer todas as tarefas da estação
                    can_do_all = all(
                        instance.can_assign(t, worker)
                        for t in solution.station_tasks[station]
                    )
                    
                    if can_do_all and instance.can_assign(task, worker):
                        # Verificar precedência novamente
                        valid = True
                        for pred in instance.predecessors[task]:
                            if pred in solution.task_assignment:
                                pred_station, _ = solution.task_assignment[pred]
                                if pred_station > station:
                                    valid = False
                                    break
                        
                        if valid:
                            solution.station_worker[station] = worker
                            # Atualizar atribuições de tarefas para esta estação
                            for t in solution.station_tasks[station]:
                                solution.task_assignment[t] = (station, worker)
                            best_station = station
                            break
                
                if best_station is not None:
                    break

        # Atribuir a tarefa à melhor estação encontrada
        if best_station is not None:
            worker = solution.station_worker[best_station]
            solution.station_tasks[best_station].append(task)
            solution.task_assignment[task] = (best_station, worker)
            assigned.add(task)
    
    # Atribuir tarefas restantes usando uma abordagem gulosa
    remaining = set(range(instance.n)) - assigned
    while remaining:
        for task in sorted(remaining, key=lambda t: instance.positional_weights[t], reverse=True):
            if not all(pred in assigned for pred in instance.predecessors[task]):
                continue
            
            for station in range(instance.k):
                worker = solution.station_worker[station]
                if not instance.can_assign(task, worker):
                    continue
                
                valid = True
                for pred in instance.predecessors[task]:
                    if pred in solution.task_assignment:
                        pred_station, _ = solution.task_assignment[pred]
                        if pred_station > station:
                            valid = False
                            break
                
                if valid:
                    solution.station_tasks[station].append(task)
                    solution.task_assignment[task] = (station, worker)
                    assigned.add(task)
                    remaining.remove(task)
                    break
            
            if task in assigned:
                break
    
    solution.calculate_cycle_time()
    return solution

def local_search_swap_tasks(solution):
    """
    BUSCA LOCAL: TROCA DE TAREFAS ENTRE ESTAÇÕES
    
    Explora a vizinhança trocando pares de tarefas entre diferentes estações.
    Aceita apenas movimentos que melhoram o tempo de ciclo.
    
    Processo:
    1. Para cada par de estações (s1, s2)
    2. Para cada par de tarefas (t1 em s1, t2 em s2)
    3. Verifica se a troca é viável (precedências e capacidades)
    4. Calcula a mudança no tempo de ciclo
    5. Aplica a melhor troca se houver melhoria
    """
    improved = True
    while improved:
        improved = False
        best_delta = 0
        best_move = None
        
        # Tentar trocar tarefas entre diferentes estações
        for s1 in range(solution.instance.k):
            for task1 in solution.station_tasks[s1]:
                for s2 in range(s1 + 1, solution.instance.k):
                    for task2 in solution.station_tasks[s2]:
                        # Verificar viabilidade de precedência
                        station1, worker1 = solution.task_assignment[task1]
                        station2, worker2 = solution.task_assignment[task2]
                        
                        # Verificar se a troca viola precedências
                        violates = False

                        # Verificar predecessores de task1 (irá para s2)
                        for pred in solution.instance.predecessors[task1]:
                            if pred in solution.task_assignment:
                                pred_station, _ = solution.task_assignment[pred]
                                if pred_station > s2:
                                    violates = True
                                    break
                        
                        # Verificar sucessores de task1 (irá para s2)
                        if not violates:
                            for succ in solution.instance.successors[task1]:
                                if succ in solution.task_assignment:
                                    succ_station, _ = solution.task_assignment[succ]
                                    if succ_station < s2:
                                        violates = True
                                        break
                        
                        # Verificar predecessores de task2 (irá para s1)
                        if not violates:
                            for pred in solution.instance.predecessors[task2]:
                                if pred in solution.task_assignment:
                                    pred_station, _ = solution.task_assignment[pred]
                                    if pred_station > s1:
                                        violates = True
                                        break
                        
                        # Verificar sucessores de task2 (irá para s1)
                        if not violates:
                            for succ in solution.instance.successors[task2]:
                                if succ in solution.task_assignment:
                                    succ_station, _ = solution.task_assignment[succ]
                                    if succ_station < s1:
                                        violates = True
                                        break
                        
                        if violates:
                            continue
                        
                        # Verificar capacidade dos trabalhadores
                        if not solution.instance.can_assign(task1, worker2):
                            continue
                        if not solution.instance.can_assign(task2, worker1):
                            continue
                        
                        # Calcular variação no tempo de ciclo (delta)
                        old_time1 = solution.get_station_time(s1)
                        old_time2 = solution.get_station_time(s2)
                        old_max = max(old_time1, old_time2)
                        
                        time1_task1 = solution.instance.get_task_time(task1, worker1)
                        time1_task2 = solution.instance.get_task_time(task2, worker1)
                        time2_task1 = solution.instance.get_task_time(task1, worker2)
                        time2_task2 = solution.instance.get_task_time(task2, worker2)
                        
                        new_time1 = old_time1 - time1_task1 + time1_task2
                        new_time2 = old_time2 - time2_task2 + time2_task1
                        new_max = max(new_time1, new_time2)
                        
                        delta = new_max - old_max
                        
                        # Salvar a melhor troca encontrada
                        if delta < best_delta:
                            best_delta = delta
                            best_move = (s1, task1, s2, task2)
        
        # Aplicar a melhor troca se houver melhoria
        if best_move and best_delta < 0:
            s1, task1, s2, task2 = best_move
            
            solution.station_tasks[s1].remove(task1)
            solution.station_tasks[s2].remove(task2)
            solution.station_tasks[s1].append(task2)
            solution.station_tasks[s2].append(task1)
            
            solution.task_assignment[task1] = (s2, solution.station_worker[s2])
            solution.task_assignment[task2] = (s1, solution.station_worker[s1])
            
            solution.calculate_cycle_time()
            improved = True

def local_search_move_task(solution):
    """
    BUSCA LOCAL: MOVER TAREFA PARA OUTRA ESTAÇÃO
    
    Explora a vizinhança movendo tarefas individuais entre estações.
    Aceita apenas movimentos que melhoram o tempo de ciclo.
    
    Processo:
    1. Para cada tarefa em cada estação
    2. Tenta mover para todas as outras estações possíveis
    3. Verifica viabilidade (precedências e capacidades)
    4. Calcula o impacto no tempo de ciclo
    5. Aplica o melhor movimento se houver melhoria
    """
    improved = True
    while improved:
        improved = False
        best_delta = 0
        best_move = None
        
        for s_from in range(solution.instance.k):
            for task in solution.station_tasks[s_from][:]:
                for s_to in range(solution.instance.k):
                    if s_from == s_to:
                        continue
                    
                    # Verificar restrições de precedência
                    can_move = True

                    # Todos os predecessores devem estar em estações anteriores ou iguais a s_to
                    for pred in solution.instance.predecessors[task]:
                        if pred in solution.task_assignment:
                            pred_station, _ = solution.task_assignment[pred]
                            if pred_station > s_to:
                                can_move = False
                                break
                    
                    # Todos os sucessores devem estar em estações posteriores ou iguais a s_to
                    if can_move:
                        for succ in solution.instance.successors[task]:
                            if succ in solution.task_assignment:
                                succ_station, _ = solution.task_assignment[succ]
                                if succ_station < s_to:
                                    can_move = False
                                    break
                    
                    if not can_move:
                        continue
                    
                    # Verificar se o trabalhador da estação destino pode executar a tarefa
                    worker_to = solution.station_worker[s_to]
                    if not solution.instance.can_assign(task, worker_to):
                        continue
                    
                    # Calcular variação no tempo de ciclo
                    worker_from = solution.station_worker[s_from]
                    old_time_from = solution.get_station_time(s_from)
                    old_time_to = solution.get_station_time(s_to)
                    old_max = max(old_time_from, old_time_to)
                    
                    task_time_from = solution.instance.get_task_time(task, worker_from)
                    task_time_to = solution.instance.get_task_time(task, worker_to)
                    
                    new_time_from = old_time_from - task_time_from
                    new_time_to = old_time_to + task_time_to
                    new_max = max(new_time_from, new_time_to)
                    
                    delta = new_max - old_max
                    
                    # Salvar o melhor movimento
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (s_from, s_to, task)
        
        # Aplicar o melhor movimento se houver melhoria
        if best_move and best_delta < 0:
            s_from, s_to, task = best_move
            
            solution.station_tasks[s_from].remove(task)
            solution.station_tasks[s_to].append(task)
            solution.task_assignment[task] = (s_to, solution.station_worker[s_to])
            
            solution.calculate_cycle_time()
            improved = True

def variable_neighborhood_descent(solution):
    """
    BUSCA LOCAL INTENSIVA (VND)
    
    Variable Neighborhood Descent - Explora sistematicamente diferentes estruturas de vizinhança.
    
    Estratégia:
    1. Define múltiplas vizinhanças (movimentação e troca de tarefas)
    2. Aplica cada vizinhança sequencialmente
    3. Se encontrar melhoria, reinicia do início
    4. Se não houver melhoria, passa para próxima vizinhança
    5. Termina quando todas as vizinhanças foram exploradas sem melhoria
    
    Vantagem: Evita mínimos locais ao alternar entre diferentes tipos de movimentos
    """
    neighborhoods = [local_search_move_task, local_search_swap_tasks]
    
    k = 0
    while k < len(neighborhoods):
        old_cycle_time = solution.cycle_time
        neighborhoods[k](solution)
        
        if solution.cycle_time < old_cycle_time:
            k = 0  # Melhoria encontrada: reiniciar da primeira vizinhança
        else:
            k += 1 # Sem melhoria: tentar próxima vizinhança

def perturbation(solution, strength=2):
    """
    PERTURBAÇÃO
    
    Aplica mudanças aleatórias na solução para escapar de mínimos locais.
    A perturbação deve ser forte o suficiente para explorar novas regiões,
    mas não tão forte que destrua a qualidade da solução.
    
    Operações de perturbação:
    1. Mover tarefas aleatoriamente entre estações (70% de chance)
    2. Trocar trabalhadores entre estações (30% de chance)
    
    O parâmetro 'strength' controla quantas perturbações são aplicadas.
    """
    new_solution = solution.copy()
    
    # Aplicar múltiplas perturbações
    for _ in range(strength):
        if random.random() < 0.7:  # 70% de chance: Mover tarefa
            # Selecionar estação com tarefas
            stations_with_tasks = [s for s in range(new_solution.instance.k) 
                                  if new_solution.station_tasks[s]]
            if not stations_with_tasks:
                continue
            
            s_from = random.choice(stations_with_tasks)
            if not new_solution.station_tasks[s_from]:
                continue
            
            task = random.choice(new_solution.station_tasks[s_from])
            
            # Encontrar estações válidas para mover a tarefa
            valid_stations = []
            for s_to in range(new_solution.instance.k):
                if s_from == s_to:
                    continue
                
                # Verificar precedências
                can_move = True
                for pred in new_solution.instance.predecessors[task]:
                    if pred in new_solution.task_assignment:
                        pred_station, _ = new_solution.task_assignment[pred]
                        if pred_station > s_to:
                            can_move = False
                            break
                
                if can_move:
                    for succ in new_solution.instance.successors[task]:
                        if succ in new_solution.task_assignment:
                            succ_station, _ = new_solution.task_assignment[succ]
                            if succ_station < s_to:
                                can_move = False
                                break
                
                worker_to = new_solution.station_worker[s_to]
                if can_move and new_solution.instance.can_assign(task, worker_to):
                    valid_stations.append(s_to)
            
            # Mover para uma estação válida aleatória
            if valid_stations:
                s_to = random.choice(valid_stations)
                new_solution.station_tasks[s_from].remove(task)
                new_solution.station_tasks[s_to].append(task)
                new_solution.task_assignment[task] = (s_to, new_solution.station_worker[s_to])
        
        else:  # 30% de chance: Trocar trabalhadores
            # Selecionar duas estações aleatórias
            s1, s2 = random.sample(range(new_solution.instance.k), 2)
            w1 = new_solution.station_worker[s1]
            w2 = new_solution.station_worker[s2]
            
            # Verificar se a troca é viável (todos os trabalhadores podem fazer suas novas tarefas)
            feasible = True
            for task in new_solution.station_tasks[s1]:
                if not new_solution.instance.can_assign(task, w2):
                    feasible = False
                    break
            
            if feasible:
                for task in new_solution.station_tasks[s2]:
                    if not new_solution.instance.can_assign(task, w1):
                        feasible = False
                        break
            
            # Executar a troca se viável
            if feasible:
                new_solution.station_worker[s1] = w2
                new_solution.station_worker[s2] = w1
                
                for task in new_solution.station_tasks[s1]:
                    new_solution.task_assignment[task] = (s1, w2)
                for task in new_solution.station_tasks[s2]:
                    new_solution.task_assignment[task] = (s2, w1)
    
    new_solution.calculate_cycle_time()
    return new_solution

def acceptance_criterion(current, candidate, temperature):
    """
    CRITÉRIO DE ACEITAÇÃO
    
    Decide se aceita a nova solução candidata baseado em Simulated Annealing.
    
    Regras:
    1. Se a candidata é melhor: SEMPRE aceita
    2. Se a candidata é pior: aceita com probabilidade exp(-delta/T)
       - Delta grande (solução muito pior): baixa probabilidade
       - Delta pequeno (solução pouco pior): maior probabilidade
       - Temperatura alta: mais exploração (aceita mais soluções piores)
       - Temperatura baixa: mais exploitação (aceita menos soluções piores)
    
    Isso permite escapar de mínimos locais aceitando ocasionalmente soluções piores.
    """
    if candidate.cycle_time < current.cycle_time:
        return True # Sempre aceita melhoria
    
    # Calcular probabilidade de aceitação para soluções piores
    delta = candidate.cycle_time - current.cycle_time
    probability = math.exp(-delta / temperature)
    return random.random() < probability

def iterated_local_search(instance, max_iterations=1000, max_time=300):
    """
    ITERATED LOCAL SEARCH (ILS)

    FLUXO DO ALGORITMO:
    ┌─────────────────────────────────────────┐
    │ 1. Gerar solução inicial (RPW)          │
    │ 2. Aplicar busca local (VND)            │
    │ 3. Guardar como melhor solução          │
    └──────────────┬──────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────┐
    │         LOOP PRINCIPAL (ILS)             │
    ├──────────────────────────────────────────┤
    │ 4. Perturbar solução atual               │
    │ 5. Aplicar busca local (VND)             │
    │ 6. Avaliar critério de aceitação         │
    │    - Se aceita: atualizar solução atual  │
    │    - Se melhor: atualizar melhor global  │
    │ 7. Ajustar parâmetros (temperatura, etc) │
    │ 8. Repetir até critério de parada        │
    └──────────────────────────────────────────┘
    
    PARÂMETROS ADAPTATIVOS:
    - Temperatura: resfriamento gradual (exploração → exploitação)
    - Força de perturbação: aumenta se ficar preso em mínimo local
    """
    start_time = time.time()
    
    # ETAPA 1: GERAR SOLUÇÃO INICIAL
    print("Gerando solução inicial...", file=sys.stderr)
    current = construct_rpw_solution(instance)
    variable_neighborhood_descent(current)
    
    best = current.copy()
    print(f"Tempo de ciclo inicial: {best.cycle_time:.2f}", file=sys.stderr)
    
    # PARÂMETROS DO ILS
    temperature = best.cycle_time * 0.1  # Temperatura inicial (10% do tempo de ciclo)
    cooling_rate = 0.95  # Taxa de resfriamento (95% a cada iteração)
    perturbation_strength = 2  # Força inicial da perturbação
    iterations_without_improvement = 0  # Contador para adaptação
    
    # LOOP PRINCIPAL DO ILS
    iteration = 0
    while iteration < max_iterations and time.time() - start_time < max_time:
        # ETAPA 2: PERTURBAÇÃO
        # Aplicar mudanças aleatórias para escapar do mínimo local atual
        candidate = perturbation(current, perturbation_strength)
        
        # ETAPA 3: BUSCA LOCAL (VND)
        # Intensificar a busca na região perturbada
        variable_neighborhood_descent(candidate)
        
        # ETAPA 4: CRITÉRIO DE ACEITAÇÃO
        # Decidir se aceita a nova solução (Simulated Annealing)
        if acceptance_criterion(current, candidate, temperature):
            current = candidate
            
            # Verificar se encontrou novo melhor global
            if current.cycle_time < best.cycle_time and current.is_feasible():
                best = current.copy()
                print(f"Iteração {iteration}: Novo melhor = {best.cycle_time:.2f}", file=sys.stderr)
                iterations_without_improvement = 0
                perturbation_strength = 2  # Resetar força de perturbação
            else:
                iterations_without_improvement += 1
        
        # ETAPA 5: ADAPTAÇÃO DE PARÂMETROS
        
        # Aumentar força de perturbação se estagnado
        # Isso ajuda a escapar de mínimos locais difíceis
        if iterations_without_improvement > 50:
            perturbation_strength = min(5, perturbation_strength + 1)
            iterations_without_improvement = 0
        
        # Resfriamento da temperatura (Simulated Annealing)
        # Temperatura alta no início: mais exploração
        # Temperatura baixa no final: mais exploitação
        temperature *= cooling_rate
        if temperature < 0.01:
            # Reiniciar temperatura se muito baixa (diversificação)
            temperature = best.cycle_time * 0.1
        
        iteration += 1

        if iteration % 100 == 0:
            elapsed = time.time() - start_time
            print(f"Iteração {iteration}, Atual: {current.cycle_time:.2f} - {'Viável' if current.is_feasible() else 'Inviável'}, Melhor: {best.cycle_time:.2f}, Tempo: {elapsed:.1f}s", file=sys.stderr)

    elapsed = time.time() - start_time
    print(f"\nILS finalizado em {elapsed:.2f}s após {iteration} iterações", file=sys.stderr)
    print(f"Melhor tempo de ciclo final: {best.cycle_time:.2f}", file=sys.stderr)
    
    return best

def read_instance():
    n = int(sys.stdin.readline().strip())
    
    k = None
    times = []
    incapabilities = {}

    # Lê matriz de tempos
    for i in range(n):
        line = sys.stdin.readline().strip().split()
        task_times = []
        for w, time_str in enumerate(line):
            if time_str == 'Inf' or time_str == 'inf':
                # Registrar incapacidade
                if w not in incapabilities:
                    incapabilities[w] = []
                incapabilities[w].append(i)
                task_times.append(float('inf'))
            else:
                task_times.append(float(time_str))
        times.append(task_times)
        if k is None:
            k = len(line)
    
    # Lê precedências
    precedences = []
    while True:
        line = sys.stdin.readline().strip().split()
        if not line:
            continue
        i, j = int(line[0]), int(line[1])
        if i == -1 and j == -1:
            break
        precedences.append((i-1, j-1))
    
    return n, k, times, incapabilities, precedences

if __name__ == "__main__":
    n, k, times, incapabilities, precedences = read_instance()
    instance = ALWABPInstance(n, k, times, incapabilities, precedences)
    
    solution = iterated_local_search(instance, max_iterations=10000, max_time=300)
    
    if solution and solution.is_feasible():
        solution.print_solution()
    else:
        print("No feasible solution found", file=sys.stderr)
        sys.exit(1)
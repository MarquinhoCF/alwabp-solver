"""
ALWABP - Assembly Line Worker Assignment and Balancing Problem
Mathematical Formulation using GurobiPy

Variables:
- v_sw ∈ {0,1}: binary variable indicating if worker w is assigned to station s
- z_siw ∈ {0,1}: binary variable indicating if task i is executed at station s by worker w
- C ∈ R+: continuous variable representing the cycle time

Objective:
min C

Constraints:
(1) Each task assigned exactly once: Σ_s∈S Σ_w∈W z_siw = 1, ∀i ∈ N
(2) One worker per station: Σ_w∈W v_sw = 1, ∀s ∈ S
(3) Each worker in exactly one station: Σ_s∈S v_sw = 1, ∀w ∈ W
(4) Task-station-worker linkage: z_siw ≤ v_sw, ∀s ∈ S, ∀i ∈ N, ∀w ∈ W
(5) Incapacity constraints: z_siw = 0, ∀s ∈ S, ∀w ∈ W, ∀i ∈ I_w
(6) Cycle time definition: Σ_i∈N Σ_w∈W t_wi * z_siw ≤ C, ∀s ∈ S
(7) Precedence constraints: Σ_s∈S Σ_w∈W s * z_siw ≤ Σ_s∈S Σ_w∈W s * z_sjw, ∀(i,j) ∈ E
"""

import sys
import gurobipy as gp
from gurobipy import GRB

def read_instance():
    n = int(sys.stdin.readline().strip())
    
    k = None
    times = []
    incapabilities = {}
    
    for i in range(n):
        line = sys.stdin.readline().strip().split()
        task_times = []
        for w, time_str in enumerate(line):
            if time_str == 'Inf' or time_str == 'inf':
                if w not in incapabilities:
                    incapabilities[w] = []
                incapabilities[w].append(i)
                task_times.append(float('inf'))
            else:
                task_times.append(float(time_str))
        times.append(task_times)
        if k is None:
            k = len(line)
    
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

def solve_alwabp(n, k, times, incapabilities, precedences):
    """
    Solve ALWABP using Gurobi
    
    Parameters:
    - n: number of tasks
    - k: number of workers (and stations, since |S| = |W|)
    - times: matrix t_wi where times[i][w] is the time for worker w to execute task i
    - incapabilities: dict mapping worker w to list of tasks they cannot execute (I_w)
    - precedences: list of tuples (i, j) meaning task i must precede task j
    """
    m = k
    
    model = gp.Model("ALWABP")
    model.setParam('OutputFlag', 0)
    
    S = range(m)
    W = range(k)
    N = range(n)
    
    v = model.addVars([(s, w) for s in S for w in W], vtype=GRB.BINARY, name="v")
    
    z = model.addVars([(s, i, w) for s in S for i in N for w in W], vtype=GRB.BINARY, name="z")
    
    C = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="C")
    
    model.setObjective(C, GRB.MINIMIZE)
    
    for i in N:
        model.addConstr(
            gp.quicksum(z[s, i, w] for s in S for w in W) == 1,
            name=f"task_assignment_{i}"
        )
    
    for s in S:
        model.addConstr(
            gp.quicksum(v[s, w] for w in W) == 1,
            name=f"one_worker_per_station_{s}"
        )
    
    for w in W:
        model.addConstr(
            gp.quicksum(v[s, w] for s in S) == 1,
            name=f"worker_one_station_{w}"
        )
    
    for s in S:
        for i in N:
            for w in W:
                model.addConstr(
                    z[s, i, w] <= v[s, w],
                    name=f"linkage_{s}_{i}_{w}"
                )
    
    for w in W:
        if w in incapabilities:
            for i in incapabilities[w]:
                for s in S:
                    model.addConstr(
                        z[s, i, w] == 0,
                        name=f"incapacity_{s}_{i}_{w}"
                    )
    
    for s in S:
        model.addConstr(
            gp.quicksum(times[i][w] * z[s, i, w] for i in N for w in W if times[i][w] != float('inf')) <= C,
            name=f"cycle_time_{s}"
        )
    
    for i, j in precedences:
        model.addConstr(
            gp.quicksum(s * z[s, i, w] for s in S for w in W) <=
            gp.quicksum(s * z[s, j, w] for s in S for w in W),
            name=f"precedence_{i}_{j}"
        )
    
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {}
        for s in S:
            for w in W:
                if v[s, w].x > 0.5:
                    solution[s] = w
                    break
        
        task_assignments = {}
        for s in S:
            for i in N:
                for w in W:
                    if z[s, i, w].x > 0.5:
                        task_assignments[i] = (s, w)
                        break
        
        return int(round(C.x)), solution, task_assignments
    else:
        return None, None, None

if __name__ == "__main__":
    n, k, times, incapabilities, precedences = read_instance()
    cycle_time, worker_assignments, task_assignments = solve_alwabp(n, k, times, incapabilities, precedences)
    
    if cycle_time is not None:
        print(cycle_time)
    else:
        print("No solution found", file=sys.stderr)
        sys.exit(1)


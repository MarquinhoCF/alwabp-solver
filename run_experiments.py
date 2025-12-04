import csv
import os
import subprocess
import sys
import time
import yaml

name_abbrev = {
    'heskia': 'hes',
    'roszieg': 'ros',
    'tonge': 'ton',
    'wee-mag': 'wee'
}

def load_ils_config(config_file='ils_config.yaml'):
    try:
        with open(config_file, 'r') as f:
            if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                raise ValueError("Formato de arquivo não suportado. Use .yaml ou .yml")
        
        print(f"✓ Configuração carregada de {config_file}")
        return config
    
    except Exception as e:
        print(f"✗ Erro ao carregar configuração: {e}", file=sys.stderr)
        sys.exit(1)

def get_instance_filename(name, num):
    abbrev = name_abbrev.get(name, name[:3])
    return f"alwabp/{num}_{abbrev}"

def create_solution_directories():
    base_dir = 'solutions'
    gurobi_dir = os.path.join(base_dir, 'gurobi')
    ils_dir = os.path.join(base_dir, 'ils')
    
    os.makedirs(gurobi_dir, exist_ok=True)
    os.makedirs(ils_dir, exist_ok=True)
    
    return base_dir, gurobi_dir, ils_dir

def load_selected_instances(selection_file):
    selected = []
    try:
        with open(selection_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    num = parts[1].strip()
                    selected.append((name, num))
        print(f"✓ {len(selected)} instâncias selecionadas de {selection_file}")
        return selected
    except FileNotFoundError:
        print(f"✗ Arquivo {selection_file} não encontrado!", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Erro ao ler {selection_file}: {e}", file=sys.stderr)
        sys.exit(1)

def load_instances_data(csv_file, selected_instances):
    instances_dict = {}
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['name'].strip('"')
                num = row['num']
                key = (name, num)
                instances_dict[key] = row
    except FileNotFoundError:
        print(f"✗ Arquivo {csv_file} não encontrado!", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Erro ao ler {csv_file}: {e}", file=sys.stderr)
        sys.exit(1)
    
    filtered_instances = []
    missing_instances = []
    
    for name, num in selected_instances:
        key = (name, num)
        if key in instances_dict:
            filtered_instances.append(instances_dict[key])
        else:
            missing_instances.append(f"{name} {num}")
    
    if missing_instances:
        print(f"Aviso: {len(missing_instances)} instâncias não encontradas no CSV:")
        for inst in missing_instances[:5]:  # Mostra apenas as 5 primeiras
            print(f"  - {inst}")
        if len(missing_instances) > 5:
            print(f"  ... e mais {len(missing_instances) - 5}")
    
    return filtered_instances

def run_gurobi(instance_file, instance_name, gurobi_dir, timeout=300):
    try:
        solution_file = os.path.join(gurobi_dir, f"{instance_name}_gurobi.txt")
        
        cmd = [
            'python3', 'gurobi_model.py',
            solution_file,
            '--max-time', str(timeout)
        ]

        start_time = time.time()
        with open(instance_file, 'r') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            output_lines = result.stdout.strip().split('\n')
            for line in reversed(output_lines):
                if line.startswith('CYCLE_TIME:'):
                    cycle_time = int(line.split(':')[1].strip())
                    return cycle_time, elapsed, solution_file
            return None, elapsed, None
        else:
            return None, elapsed
    except subprocess.TimeoutExpired:
        return None, timeout, None
    except Exception as e:
        print(f"Error running Gurobi on {instance_file}: {e}", file=sys.stderr)
        return None, 0, None

def run_ils_single(instance_file, instance_name, ils_dir, seed, ils_config, optimal_value=None, timeout=300):
    try:
        solution_file = os.path.join(ils_dir, f"{instance_name}_ils_seed{seed}.txt")

        cmd = [
            'python3', 'ils_model.py',
            solution_file,
            '--seed', str(seed),
            '--max-time', str(timeout),
            '--adaptive-timeout',
            '--initial-temp-factor', str(ils_config['initial_temp_factor']),
            '--cooling-rate', str(ils_config['cooling_rate']),
            '--perturbation-initial', str(ils_config['perturbation_initial']),
            '--perturbation-max', str(ils_config['perturbation_max']),
            '--improvement-threshold', str(ils_config['improvement_threshold']),
            '--stagnation-threshold', str(ils_config['stagnation_threshold']),
            '--optimal-tolerance', str(ils_config['optimal_tolerance'])
        ]
        
        if optimal_value is not None:
            cmd.extend(['--optimal-value', str(optimal_value)])
        
        start_time = time.time()
        with open(instance_file, 'r') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            print(f"ILS error (seed {seed}): {result.stderr}", file=sys.stderr)
            return None
        
        initial_ct = None
        final_ct = None
        
        stdout_lines = result.stdout.strip().split('\n')
        for line in reversed(stdout_lines):
            if "INITIAL_CYCLE_TIME:" in line:
                initial_ct = float(line.split(":", 1)[1].strip())

            elif "FINAL_CYCLE_TIME:" in line:
                final_ct = int(line.split(":", 1)[1].strip())

            if initial_ct is not None and final_ct is not None:
                break
        
        if initial_ct is None or final_ct is None:
            raise ValueError("INITIAL_CYCLE_TIME or FINAL_CYCLE_TIME not found in ILS output")
        
        return {
            'seed': seed,
            'initial_ct': initial_ct,
            'final_ct': final_ct,
            'time': elapsed,
            'solution_file': solution_file
        }
    
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"Exception running ILS (seed {seed}): {e}", file=sys.stderr)
        return None

def run_ils_replications(instance_file, instance_name, ils_dir, ils_config, optimal_value=None, num_replications=5, timeout=300):
    results = []
    
    for i in range(num_replications):
        seed = 10 + i  # Sementes: 10, 11, 12, 13, 14
        
        print(f"  Replicação {i+1}/{num_replications} (seed={seed})...", end=' ', flush=True)
        
        result = run_ils_single(instance_file, instance_name, ils_dir, seed, ils_config, optimal_value, timeout)
        
        if result:
            results.append(result)
            print(f"✓ CT={result['final_ct']:.0f} ({result['time']:.1f}s)")
        else:
            print("✗ ERRO")
    
    return results

def calculate_statistics(results):
    if not results:
        return None
    
    initial_cts = [r['initial_ct'] for r in results if r['initial_ct'] is not None]
    final_cts = [r['final_ct'] for r in results]
    times = [r['time'] for r in results]
    
    avg_initial = sum(initial_cts) / len(initial_cts) if initial_cts else None
    avg_final = sum(final_cts) / len(final_cts)
    avg_time = sum(times) / len(times)
    
    best_final = min(final_cts)
    worst_final = max(final_cts)
    
    # Desvio percentual da solução final em relação à inicial
    if avg_initial:
        improvement_pct = 100 * (avg_initial - avg_final) / avg_initial
    else:
        improvement_pct = None
    
    return {
        'avg_initial_ct': avg_initial,
        'avg_final_ct': avg_final,
        'best_final_ct': best_final,
        'worst_final_ct': worst_final,
        'avg_time': avg_time,
        'improvement_pct': improvement_pct,
        'num_replications': len(results)
    }

def main():
    input_csv = 'instances.csv'
    selection_file = 'instancias_teste_relatorio.txt'
    output_csv = 'results.csv'
    ils_single_output_csv = 'results_ils_single_results.csv'
    config_file = 'best_params.yaml'
    
    num_replications = 5
    ils_timeout = 500
    gurobi_timeout = 300
    
    print("=" * 80)
    print("EXPERIMENTOS ALWABP - Gurobi e ILS")
    print("=" * 80)
    print(f"Replicações por instância: {num_replications}")
    print(f"Timeout ILS: {ils_timeout}s")
    print(f"Timeout Gurobi: {gurobi_timeout}s")
    print("=" * 80)
    print()

    # Cria diretórios para salvar soluções
    base_dir, gurobi_dir, ils_dir = create_solution_directories()
    print(f"✓ Diretórios criados: {gurobi_dir}, {ils_dir}")
    print()

    # Carregar configurações do ILS
    ils_config = load_ils_config(config_file)
    print("\nParâmetros ILS:")
    for key, value in ils_config.items():
        print(f"  {key}: {value}")
    print()

    # Carrega instâncias selecionadas
    selected_instances = load_selected_instances(selection_file)
    
    # Carrega dados do CSV apenas para instâncias selecionadas
    instances = load_instances_data(input_csv, selected_instances)
    
    if not instances:
        print("✗ Nenhuma instância válida encontrada!")
        sys.exit(1)
    
    rows = []
    individual_rows = []
    total = len(instances)
    
    for idx, row in enumerate(instances, 1):
        name = row['name'].strip('"')
        num = row['num']
        ub = float(row['UB']) if row.get('UB') else None
        
        instance_file = get_instance_filename(name, num)
        instance_name = f"{num}_{name_abbrev.get(name, name[:3])}"
        
        print(f"\n[{idx}/{total}] Instância: {instance_name}")
        print("-" * 80)
        
        print("Executando Gurobi...", end=' ', flush=True)
        gurobi_ct, gurobi_time, gurobi_sol_file = run_gurobi(instance_file, instance_name, gurobi_dir, gurobi_timeout)
        if gurobi_ct:
            print(f"✓ CT={gurobi_ct} ({gurobi_time:.2f}s)")
            print(f"  Solução salva em: {gurobi_sol_file}")
        else:
            print("✗ ERRO ou TIMEOUT")
        
        # Usa valor ótimo conhecido para realizar early stopping no ILS
        # Usar UB como optimal value se Gurobi não encontrou
        optimal_value = gurobi_ct if gurobi_ct else ub

        print(f"Executando ILS ({num_replications} replicações):")
        
        ils_results = run_ils_replications(
            instance_file, instance_name, ils_dir, ils_config,
            optimal_value, num_replications, ils_timeout
        )

        for r in ils_results:
            individual_rows.append({
                'instance': instance_name,
                'name': name,
                'num': num,
                'seed': r['seed'],
                'initial_ct': r['initial_ct'],
                'final_ct': r['final_ct'],
                'time': r['time'],
                'solution_file': r['solution_file']
            })

        ils_stats = calculate_statistics(ils_results)
        
        result_row = {
            'instance': instance_name,
            'name': name,
            'num': num,
            'n_tasks': row.get('tasks', ''),
            'n_workers': row.get('workers', ''),
            'UB': ub if ub else '',
            'gurobi_ct': gurobi_ct if gurobi_ct else '',
            'gurobi_time': f"{gurobi_time:.2f}" if gurobi_time else '',
            'ils_replications': ils_stats['num_replications'] if ils_stats else 0,
            'ils_avg_initial_ct': f"{ils_stats['avg_initial_ct']:.2f}" if ils_stats and ils_stats['avg_initial_ct'] else '',
            'ils_avg_final_ct': f"{ils_stats['avg_final_ct']:.2f}" if ils_stats else '',
            'ils_best_ct': ils_stats['best_final_ct'] if ils_stats else '',
            'ils_worst_ct': ils_stats['worst_final_ct'] if ils_stats else '',
            'ils_avg_time': f"{ils_stats['avg_time']:.2f}" if ils_stats else '',
            'ils_improvement_pct': f"{ils_stats['improvement_pct']:.2f}" if ils_stats and ils_stats['improvement_pct'] else ''
        }
        
        rows.append(result_row)
        
        print("\nResumo:")
        if gurobi_ct:
            print(f"  Gurobi: {gurobi_ct} ({gurobi_time:.2f}s)")
        if ils_stats:
            print(f"  ILS (média): {ils_stats['avg_final_ct']:.2f} ({ils_stats['avg_time']:.2f}s)")
            print(f"  ILS (melhor): {ils_stats['best_final_ct']}")
            print(f"  Melhoria SI -> SF: {ils_stats['improvement_pct']:.2f}%")
    
    with open(output_csv, 'w', newline='') as f:
        fieldnames = [
            'instance', 'name', 'num', 'n_tasks', 'n_workers', 'UB',
            'gurobi_ct', 'gurobi_time',
            'ils_replications', 'ils_avg_initial_ct', 'ils_avg_final_ct',
            'ils_best_ct', 'ils_worst_ct', 'ils_avg_time',
            'ils_improvement_pct'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    with open(ils_single_output_csv, 'w', newline='') as f:
        fieldnames = [
            'instance', 'name', 'num', 'seed',
            'initial_ct', 'final_ct', 'time', 'solution_file'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(individual_rows)
    
    print("\n" + "=" * 80)
    print(f"✓ Experimentos concluídos! Resultados salvos em {output_csv} e {ils_single_output_csv}")
    print("=" * 80)

if __name__ == "__main__":
    main()
"""
Otimização de Parâmetros para ILS-ALWABP usando Optuna

Este script realiza otimização automática dos parâmetros do algoritmo ILS
usando Optuna (Tree-structured Parzen Estimator - TPE).
"""

import argparse
import sys
import subprocess
import re
import yaml
import time
from pathlib import Path
import optuna
from optuna.samplers import TPESampler

class ILSParameterOptimizer:
    def __init__(self, instance_file, optimal_value=None, time_limit=120):
        self.instance_file = instance_file
        self.optimal_value = optimal_value
        self.time_limit = time_limit
        self.ils_script = "ils_model.py"
        
        # Verificar se o arquivo de instância existe
        if not Path(instance_file).exists():
            raise FileNotFoundError(f"Arquivo de instância não encontrado: {instance_file}")
    
    def objective(self, trial):
        params = {
            'cooling_rate': trial.suggest_float('cooling_rate', 0.85, 0.99),
            'improvement_threshold': trial.suggest_int('improvement_threshold', 20, 200),
            'initial_temp_factor': trial.suggest_float('initial_temp_factor', 0.05, 0.3),
            'perturbation_initial': trial.suggest_int('perturbation_initial', 1, 4),
            'perturbation_max': trial.suggest_int('perturbation_max', 3, 8),
            'stagnation_threshold': trial.suggest_int('stagnation_threshold', 500, 2000)
        }
        
        if params['perturbation_max'] < params['perturbation_initial']:
            params['perturbation_max'] = params['perturbation_initial'] + 1
        
        # Construir comando para executar o ILS
        cmd = [
            'python3', self.ils_script,
            '--max-time', str(self.time_limit),
            '--cooling-rate', str(params['cooling_rate']),
            '--improvement-threshold', str(params['improvement_threshold']),
            '--initial-temp-factor', str(params['initial_temp_factor']),
            '--perturbation-initial', str(params['perturbation_initial']),
            '--perturbation-max', str(params['perturbation_max']),
            '--stagnation-threshold', str(params['stagnation_threshold'])
        ]
        
        if self.optimal_value is not None:
            cmd.extend(['--optimal-value', str(self.optimal_value)])
        
        try:
            with open(self.instance_file, 'r') as f_in:
                result = subprocess.run(
                    cmd,
                    stdin=f_in,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.time_limit + 30
                )
            
            output = result.stdout
            
            # Procurar por "FINAL_CYCLE_TIME: XXX"
            match = re.search(r'FINAL_CYCLE_TIME:\s*(\d+(?:\.\d+)?)', output)
            if match:
                cycle_time = float(match.group(1))
                
                match_initial = re.search(r'INITIAL_CYCLE_TIME:\s*(\d+(?:\.\d+)?)', output)
                if match_initial:
                    initial_cycle_time = float(match_initial.group(1))
                    improvement = ((initial_cycle_time - cycle_time) / initial_cycle_time) * 100
                    
                    trial.set_user_attr('initial_cycle_time', initial_cycle_time)
                    trial.set_user_attr('improvement_pct', improvement)
                
                if self.optimal_value is not None:
                    gap = ((cycle_time - self.optimal_value) / self.optimal_value) * 100
                    trial.set_user_attr('gap_to_optimal', gap)
                
                return cycle_time
            else:
                print(f"AVISO: Não foi possível extrair cycle time do trial {trial.number}", 
                      file=sys.stderr)
                return float('inf')
        
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT no trial {trial.number}", file=sys.stderr)
            return float('inf')
        except Exception as e:
            print(f"ERRO no trial {trial.number}: {e}", file=sys.stderr)
            return float('inf')
    
    def optimize(self, n_trials=20, n_jobs=1):
        print("=" * 70)
        print("OTIMIZAÇÃO DE PARÂMETROS - ILS ALWABP")
        print("=" * 70)
        print(f"Instância: {self.instance_file}")
        print(f"Tempo limite por trial: {self.time_limit}s")
        print(f"Número de trials: {n_trials}")
        if self.optimal_value:
            print(f"Valor ótimo conhecido: {self.optimal_value}")
        print("=" * 70)
        print()
        
        study = optuna.create_study(
            direction='minimize',
            sampler=TPESampler(seed=42),
            study_name='ILS_ALWABP_Optimization'
        )
        
        start_time = time.time()
        
        study.optimize(
            self.objective,
            n_trials=n_trials,
            n_jobs=n_jobs,
            show_progress_bar=True
        )
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("OTIMIZAÇÃO CONCLUÍDA")
        print("=" * 70)
        print(f"Tempo total: {elapsed:.2f}s ({elapsed/60:.1f} min)")
        print(f"Trials completados: {len(study.trials)}")
        print(f"\nMelhor cycle time: {study.best_value:.2f}")
        
        if self.optimal_value:
            gap = ((study.best_value - self.optimal_value) / self.optimal_value) * 100
            print(f"Gap para ótimo: {gap:.2f}%")
        
        print("\nMelhores parâmetros encontrados:")
        print("-" * 70)
        for param, value in study.best_params.items():
            print(f"  {param:25s}: {value}")
        
        if 'improvement_pct' in study.best_trial.user_attrs:
            print(f"\nMelhoria sobre solução inicial: "
                  f"{study.best_trial.user_attrs['improvement_pct']:.2f}%")
        
        print("=" * 70)
        
        return study
    
    def save_best_params(self, study, output_file='best_params.yml'):
        params = study.best_params.copy()
        
        with open(output_file, 'w') as f:
            yaml.dump(params, f, default_flow_style=False, sort_keys=False)
        
        print(f"\nParâmetros salvos em: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Otimização de parâmetros para ILS-ALWABP',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--instance', type=str, required=True,
                       help='Arquivo de instância do problema')
    
    parser.add_argument('--optimal-value', type=float, default=None,
                       help='Valor ótimo conhecido (opcional)')
    
    parser.add_argument('--n-trials', type=int, default=20,
                       help='Número de trials (default: 20)')
    
    parser.add_argument('--time-limit', type=int, default=300,
                       help='Tempo limite por trial em segundos (default: 300)')
    
    parser.add_argument('--output', type=str, default='best_params.yml',
                       help='Arquivo de saída YAML (default: best_params.yml)')
    
    parser.add_argument('--n-jobs', type=int, default=1,
                       help='Número de jobs paralelos (default: 1)')
    
    args = parser.parse_args()
    
    try:
        # Criar otimizador
        optimizer = ILSParameterOptimizer(
            instance_file=args.instance,
            optimal_value=args.optimal_value,
            time_limit=args.time_limit
        )
        
        # Executar otimização
        study = optimizer.optimize(
            n_trials=args.n_trials,
            n_jobs=args.n_jobs
        )
        
        # Salvar melhores parâmetros
        optimizer.save_best_params(study, args.output)
        
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
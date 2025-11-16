import csv
import subprocess
import sys
import os

name_abbrev = {
    'heskia': 'hes',
    'roszieg': 'ros',
    'tonge': 'ton',
    'wee-mag': 'wee'
}

def get_instance_filename(name, num):
    abbrev = name_abbrev.get(name, name[:3])
    return f"alwabp/{num}_{abbrev}"

def run_model(instance_file):
    try:
        with open(instance_file, 'r') as f:
            result = subprocess.run(
                ['python3', 'model.py'],
                stdin=f,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                output_lines = result.stdout.strip().split('\n')
                for line in reversed(output_lines):
                    line = line.strip()
                    if line and not line.startswith('Set parameter') and 'license' not in line.lower() and 'Academic' not in line:
                        try:
                            int(line)
                            return line
                        except ValueError:
                            continue
                return None
            else:
                print(f"Error running {instance_file}: {result.stderr}", file=sys.stderr)
                return None
    except FileNotFoundError:
        print(f"Instance file not found: {instance_file}", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"Timeout running {instance_file}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Exception running {instance_file}: {e}", file=sys.stderr)
        return None

def main():
    input_csv = 'instances.csv'
    output_csv = 'instances.csv'
    
    rows = []
    total = 0
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        if 'gurobi' not in fieldnames:
            fieldnames.append('gurobi')
        
        rows_list = list(reader)
        total = len(rows_list)
        
        for idx, row in enumerate(rows_list, 1):
            name = row['name'].strip('"')
            num = row['num']
            instance_file = get_instance_filename(name, num)
            
            print(f"[{idx}/{total}] Running {instance_file}...", end=' ', flush=True)
            result = run_model(instance_file)
            if result:
                row['gurobi'] = result
                print(f"✓ Result: {result}")
            else:
                row['gurobi'] = 'ERROR'
                print("✗ ERROR")
            
            rows.append(row)
    
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n✓ All {total} instances processed. Results written to {output_csv}")

if __name__ == "__main__":
    main()


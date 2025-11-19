import sys


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
        line = sys.stdin.readline()
        
        # Verificar se chegou ao fim do arquivo
        if not line:
            break
            
        line = line.strip()
        
        # Ignorar linhas vazias
        if not line:
            continue
            
        parts = line.split()
        
        if len(parts) < 2:
            raise ValueError("Linha de precedência inválida: menos de 2 elementos.")
            
        try:
            i, j = int(parts[0]), int(parts[1])
            if i == -1 and j == -1:
                break
            precedences.append((i-1, j-1))
        except (ValueError, IndexError):
            raise ValueError("Erro ao ler precedências da instância.")
    
    return n, k, times, incapabilities, precedences

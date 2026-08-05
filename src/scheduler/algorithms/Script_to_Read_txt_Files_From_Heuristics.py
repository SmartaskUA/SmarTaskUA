import re
from collections import defaultdict

def processar_grasp_history(nome_ficheiro):
    dados_por_spacing = defaultdict(lambda: {'mins': [], 'ideals': []})
    spacing_atual = None

    regex_spacing = re.compile(r'Spacing\s*=\s*(\d+)')
    regex_run = re.compile(r'missed_mins=(\d+),\s*missed_ideals=(\d+)')

    with open(nome_ficheiro, 'r') as f:
        for linha in f:
            match_spacing = regex_spacing.search(linha)
            if match_spacing:
                spacing_atual = match_spacing.group(1)
                continue

            if spacing_atual:
                match_run = regex_run.search(linha)
                if match_run:
                    mins = int(match_run.group(1))
                    ideals = int(match_run.group(2))
                    
                    dados_por_spacing[spacing_atual]['mins'].append(mins)
                    dados_por_spacing[spacing_atual]['ideals'].append(ideals)

    # Exibir resultados
    header = f"{'Spacing':<8} | {'Médias (Mins/Ideals)':<22} | {'Melhores (Mins/Ideals)':<22}"
    print(header)
    print("-" * len(header))
    
    for spacing in sorted(dados_por_spacing.keys(), key=lambda x: int(x)):
        vals = dados_por_spacing[spacing]
        
        # Cálculos
        avg_mins = sum(vals['mins']) / len(vals['mins'])
        avg_ideals = sum(vals['ideals']) / len(vals['ideals'])
        best_mins = min(vals['mins'])
        best_ideals = min(vals['ideals'])
        
        print(f"{spacing:<8} | {avg_mins:<10.2f} / {avg_ideals:<9.2f} | {best_mins:<10} / {best_ideals:<9}")

if __name__ == "__main__":
    processar_grasp_history('history.txt')
import numpy as np
import time
import csv
import io

# Preferências dos trabalhadores (0 = manhã, 1 = tarde)
Prefs = [
    [0], [0], [1], [1], [0, 1], [0, 1], [1], [0], [1], [0],
    [1], [1], [0, 1], [0, 1], [0, 1]
]

# Parâmetros globais
nTrabs = len(Prefs)
nDias = 365
nDiasFerias = 30
nDiasTrabalho = 223
nDiasTrabalhoFDS = 22
nDiasSeguidos = 5
nMinTrabs = 2
nMaxFolga = 142
nTurnos = 2
feriados = [31, 60, 120, 150, 200, 240, 300, 330]

# Férias otimizadas
def definir_ferias(nTrabs, nDias, nDiasFerias, nMaxSimultaneos=3):
    Ferias = np.zeros((nTrabs, nDias), dtype=bool)
    contagem_diaria = np.zeros(nDias, dtype=int)

    for trab in range(nTrabs):
        dias_restantes = nDiasFerias
        tentativas = 0
        while dias_restantes >= 3 and tentativas < 1000:
            max_bloco = min(10, dias_restantes)
            bloco = np.random.randint(3, max_bloco + 1)
            inicio = np.random.randint(0, nDias - bloco)
            periodo = np.arange(inicio, inicio + bloco)

            if np.all(contagem_diaria[periodo] < nMaxSimultaneos) and not np.any(Ferias[trab, periodo]):
                Ferias[trab, periodo] = True
                contagem_diaria[periodo] += 1
                dias_restantes -= bloco
            else:
                tentativas += 1

        if tentativas == 1000:
            print(f"⚠️ Não foi possível alocar todas as férias para o trabalhador {trab}.")

    return Ferias

# Critérios de verificação
def criterio1(horario, nDiasSeguidos):
    f1 = np.zeros(horario.shape[0], dtype=int)
    dias_trabalhados = np.sum(horario, axis=2) > 0 
    janela = np.ones(nDiasSeguidos, dtype=int)
    for i in range(horario.shape[0]):
        sequencia = np.convolve(dias_trabalhados[i].astype(int), janela, mode='valid')
        f1[i] = np.sum(sequencia == nDiasSeguidos)  
    return f1

def criterio2(horario, fds, nDiasTrabalhoFDS, feriados):
    feriados = np.array(feriados)
    dias_fds_feriados = np.isin(np.arange(horario.shape[1]), feriados) 
    dias_trabalhados = np.sum(horario * (fds[:, :, None] | dias_fds_feriados[:, None]), axis=(1, 2))
    excedente = np.maximum(dias_trabalhados - nDiasTrabalhoFDS, 0)
    return excedente

def criterio3(horario, nMinTrabs):
    total_turnos = np.sum(horario, axis=(1, 2))
    return np.sum(total_turnos < nMinTrabs)

def criterio4(horario, nMaxFolga):
    folgas = nDias - np.sum(horario, axis=(1, 2))
    return np.abs(folgas - nMaxFolga)

def criterio5(horario, Prefs):
    f5 = np.zeros(horario.shape[0], dtype=int)
    for i, pref in enumerate(Prefs):
        if any(p in pref for p in [0, 1]):
            for d in range(nDias - 1):
                if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                    f5[i] += 1
    return f5

def calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados):
    f1 = criterio1(horario, nDiasSeguidos)
    f2 = criterio2(horario, fds, nDiasTrabalhoFDS, feriados)
    f3 = criterio3(horario, nMinTrabs)
    f4 = criterio4(horario, nMaxFolga)
    f5 = criterio5(horario, Prefs)
    return f1, f2, f3, f4, f5

def identificar_equipes(Prefs):
    equipe_A, equipe_B, ambas = [], [], []
    for i, pref in enumerate(Prefs):
        if 0 in pref and 1 in pref:
            ambas.append(i)
        elif 0 in pref:
            equipe_A.append(i)
        elif 1 in pref:
            equipe_B.append(i)
    return equipe_A, equipe_B, ambas

# Geração do CSV (em memória)
def salvar_csv(horario, Ferias, nTurnos, nDias, Prefs):
    output = io.StringIO()
    csvwriter = csv.writer(output)
    
    header = ["Trabalhador"] + [f"Dia {d+1}" for d in range(nDias)] + ["Dias Trabalhados", "Dias de Férias"]
    csvwriter.writerow(header)

    for e in range(nTrabs):
        employee_schedule = []
        equipe = 'A' if 0 in Prefs[e] else 'B' if 1 in Prefs[e] else 'Ambas'
        dias_trabalhados = np.sum(np.sum(horario[e], axis=1))
        dias_ferias = np.sum(Ferias[e])

        for d in range(nDias):
            shift = "Fe" if Ferias[e, d] else "0"
            if not Ferias[e, d]:
                if horario[e, d, 0] == 1:
                    shift = f"M_{equipe}"
                elif horario[e, d, 1] == 1:
                    shift = f"T_{equipe}"
            employee_schedule.append(shift)

        csvwriter.writerow([f"Empregado{e + 1}"] + employee_schedule + [dias_trabalhados, dias_ferias])

    # Escreve o CSV em arquivo
    with open("calendario.csv", "w", encoding="utf-8", newline="") as f:
        f.write(output.getvalue())

    return output.getvalue()

# Função principal de resolução
def solve():
    Ferias = definir_ferias(nTrabs, nDias, nDiasFerias)

    fds = np.zeros((nTrabs, nDias), dtype=bool)
    fds[:, 3::7] = fds[:, 4::7] = True
    dias = np.where(~Ferias)

    horario = np.zeros((nTrabs, nDias, nTurnos), dtype=int)
    for i in range(nTrabs):
        dias_disponiveis = np.where(~Ferias[i])[0]
        trabalho_indices = np.random.choice(dias_disponiveis, nDiasTrabalho, replace=False)
        turnos = np.random.choice(nTurnos, len(trabalho_indices))
        horario[i, trabalho_indices, turnos] = 1

    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados)
    
    t, cont = 0, 0
    while t < 400000 and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt)):
        cont += 1
        i = np.random.randint(nTrabs)
        aux = np.random.choice(len(dias[1][dias[0] == i]), 2, replace=False)
        dia1, dia2 = dias[1][dias[0] == i][aux]
        turno1, turno2 = np.random.choice(nTurnos, 2, replace=False)

        pode_trabalhar_A = 0 in Prefs[i]
        pode_trabalhar_B = 1 in Prefs[i]

        if horario[i, dia1, turno1] != horario[i, dia2, turno2]:
            hor = horario.copy()
            if pode_trabalhar_A and pode_trabalhar_B:
                hor[i, dia1, turno1], hor[i, dia2, turno2] = hor[i, dia2, turno2], hor[i, dia1, turno1]
            elif pode_trabalhar_A:
                hor[i, dia1, turno1] = 1
                hor[i, dia2, turno2] = 0
            elif pode_trabalhar_B:
                hor[i, dia1, turno1] = 0
                hor[i, dia2, turno2] = 1

            f1, f2, f3, f4, f5 = calcular_criterios(hor, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados)
            if np.all(f1 == 0) and np.all(f2 == 0) and f3 == 0 and np.all(f4 == 0) and np.all(f5 == 0):
                f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, horario = f1, f2, f3, f4, f5, hor
                break
            if f1[i] + f2[i] + f3 + f4[i] + f5[i] < f1_opt[i] + f2_opt[i] + f3_opt + f4_opt[i] + f5_opt[i]:
                f1_opt[i], f2_opt[i], f3_opt, f4_opt[i], f5_opt[i], horario = f1[i], f2[i], f3, f4[i], f5[i], hor
        t += 1

    salvar_csv(horario, Ferias, nTurnos, nDias, Prefs)

    schedule = []
    with open('calendario.csv', mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, dialect='excel')
        for row in reader:
            schedule.append(row)

    return schedule

# Execução do script
if __name__ == "__main__":
    resultado = solve()

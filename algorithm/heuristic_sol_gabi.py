import numpy as np
import time
import csv

# Definindo as preferências dos trabalhadores
Prefs = [
    [0], [0], [1], [1], [0, 1], [0, 1], [1], [0], [1], [0], [1], [1], [0, 1], [0, 1], [0, 1]
]

nTrabs = len(Prefs)             # Número de trabalhadores (baseado no número de preferências)
nDias = 365                     # Número de dias no ano
nDiasFerias = 30                # Número de dias de férias por trabalhador
nDiasTrabalho = 223             # Número de dias de trabalho no ano
nDiasTrabalhoFDS = 22           # Número máximo de dias trabalhados nos finais de semana
nDiasSeguidos = 5               # Número máximo de dias seguidos de trabalho
nMinTrabs = 2                   # Número mínimo de turnos que um trabalhador deve fazer
nMaxFolga = 142                 # Número máximo de dias de folga
nTurnos = 2                     # Número de turnos por dia (Manhã e Tarde)

# Definindo os feriados
feriados = [31, 60, 120, 150, 200, 240, 300, 330]  # Por exemplo, dias do ano (em números de 1 a 365)

# Função para definir férias de forma otimizada
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

def criterio1(horario, nDiasSeguidos):
    f1 = np.zeros(horario.shape[0], dtype=int)
    dias_trabalhados = np.sum(horario, axis=2) > 0  # True se trabalhou em pelo menos um turno

    janela = np.ones(nDiasSeguidos, dtype=int)

    for i in range(horario.shape[0]):
        # Aplica convolução para contar quantos dias seguidos foram trabalhados em blocos de 5
        sequencia = np.convolve(dias_trabalhados[i].astype(int), janela, mode='valid')
        f1[i] = np.sum(sequencia == nDiasSeguidos)  # Conta quantas sequências completas de 5 existem

    return f1

# Dias de trabalho em fins de semana e feriados
def criterio2(horario, fds, nDiasTrabalhoFDS, feriados):
    f2 = np.sum(np.sum(horario * fds[:, :, None], axis=1), axis=1)
    for feriado in feriados:
        f2 -= horario[:, feriado - 1, :].sum(axis=1)  # Exclui os feriados
    return np.maximum(f2 - nDiasTrabalhoFDS, 0)

# Turnos abaixo do mínimo necessário
def criterio3(horario, nMinTrabs):
    total_turnos = np.sum(horario, axis=(0, 2))
    return np.sum(total_turnos < nMinTrabs)

# Diferença entre folgas reais e limite máximo permitido
def criterio4(horario, nMaxFolga):
    folgas = nDias - np.sum(horario, axis=(1, 2))
    return np.abs(folgas - nMaxFolga)


# Violação da sequência proibida: Tarde seguida de Manhã no mesmo turno
def criterio5(horario, Prefs):
    f5 = np.zeros(horario.shape[0], dtype=int)
    
    # Loop apenas pelos trabalhadores com preferências (0 ou 1)
    for i, pref in enumerate(Prefs):
        # Verifica se o trabalhador tem a preferência de trabalhar à tarde ou manhã
        if any(p in pref for p in [0, 1]):
            # Loop sobre os dias
            for d in range(nDias - 1):
                # Verifica se houve a sequência Tarde seguida de Manhã
                if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                    f5[i] += 1
    return f5


# Função para calcular os critérios
def calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados):
    f1 = criterio1(horario, nDiasSeguidos)
    f2 = criterio2(horario, fds, nDiasTrabalhoFDS, feriados)
    f3 = criterio3(horario, nMinTrabs)
    f4 = criterio4(horario, nMaxFolga)
    f5 = criterio5(horario, Prefs)
    return f1, f2, f3, f4, f5

# Função para identificar as equipes
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

# Função para salvar os resultados em um arquivo CSV
def salvar_csv(horario, Ferias, nTurnos, nDias, Prefs):
    with open("calendario.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
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

# Início
start_time = time.time()

f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados)
equipe_A, equipe_B, ambas = identificar_equipes(Prefs)

def print_result(label, data):
    print(f"{label}:\n{data}\n")

# Exibição dos resultados
print("Critério 1 - Dias seguidos de trabalho excedendo o limite (máx. 5 dias seguidos):                    ", f1_opt)
print("Critério 2 - Dias trabalhados em fins de semana além do permitido (máx. 22):                         ", f2_opt)
print("Critério 3 - Quantidade de turnos abaixo do mínimo necessário (mín. 2 por trabalhador):              ", f3_opt)
print("Critério 4 - Diferença entre folgas reais e limite máximo permitido (máx. 142 dias de folga) :       ", f4_opt)
print("Critério 5 - Violação da sequência proibida: Tarde seguida de Manhã no mesmo turno (preferência):    ", f5_opt)
print("\nTrabalhadores na equipe A:", equipe_A)
print("Trabalhadores na equipe B:", equipe_B)
print("Trabalhadores nas equipes A e B:", ambas)

t, cont = 0, 0
while t < 240000 and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt)):
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
            print("\nSolução perfeita encontrada!")
            break

        if f1[i] + f2[i] + f3 + f4[i] + f5[i] < f1_opt[i] + f2_opt[i] + f3_opt + f4_opt[i] + f5_opt[i]:
            f1_opt[i], f2_opt[i], f3_opt, f4_opt[i], f5_opt[i], horario = f1[i], f2[i], f3, f4[i], f5[i], hor

    t += 1

execution_time = time.time() - start_time

print("======= RESULTADOS =======\n")
print_result("Critério 1 - Dias seguidos de trabalho excedendo o limite (máx. 5 dias seguidos)", f1_opt)
print_result("Critério 2 - Dias trabalhados nos finais de semana além do limite (máx. 22)     ", f2_opt)
print_result("Critério 3 - Turnos abaixo do mínimo necessário (mín. 2 por trabalhador)        ", f3_opt)
print_result("Critério 4 - Folgas excedendo o limite (máx. 142 dias de folga)                 ", f4_opt)
print_result("Critério 5 - Violação das preferências de turno                                 ", f5_opt)

print(f"\nTempo de execução: {execution_time:.2f} segundos")
print(f"Número de iterações realizadas: {cont}")

salvar_csv(horario, Ferias, nTurnos, nDias, Prefs)

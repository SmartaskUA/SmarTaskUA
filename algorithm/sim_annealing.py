import numpy as np
import csv
import random

# Parâmetros principais
nFuncionarios = 15
nDias = 365
temperatura_inicial = 1000
temperatura_final = 1
taxa_resfriamento = 0.95
feriados = [i for i in range(nDias) if i % 30 == 0]  # Exemplo simples: feriados a cada 30 dias
alarmes = []  # Ignorar por agora

# --- Gerar férias (30 dias aleatórios por funcionário) ---
ferias = np.zeros((nFuncionarios, nDias), dtype=bool)
for i in range(nFuncionarios):
    ferias_dias = np.random.choice(nDias, size=30, replace=False)
    ferias[i, ferias_dias] = True

# Preferências de turnos (manhã = 1, tarde = 2)
preferencias = []
for _ in range(nFuncionarios):
    preferencias.append(random.sample([1, 2], k=random.randint(1, 2)))

# Geração da solução inicial
def gerar_solucao_inicial():
    solucao = np.zeros((nFuncionarios, nDias), dtype=int)
    for i in range(nFuncionarios):
        j = 0
        while j < nDias:
            if ferias[i][j]:
                solucao[i][j] = 0  # férias
                j += 1
                continue

            if j + 5 <= nDias and np.sum(ferias[i][j:j+5]) == 0:
                turno = random.choice(preferencias[i])
                for k in range(5):
                    solucao[i][j + k] = turno
                j += 5
                if j < nDias:
                    solucao[i][j] = 0  # folga após sequência
                    j += 1
            else:
                solucao[i][j] = 0
                j += 1
    return solucao

# Custo da solução
def calcular_custo(horario, feriados):
    custo = 0
    for i in range(nFuncionarios):
        dias_trabalhados = np.sum((horario[i] != 0) & (~ferias[i]))
        domingos_feriados = sum(
            1 for d in range(nDias)
            if (d % 7 == 6 or d in feriados) and horario[i][d] != 0 and not ferias[i][d]
        )
        custo += abs(dias_trabalhados - 223) * 10
        if domingos_feriados > 22:
            custo += (domingos_feriados - 22) * 20

        dias_consecutivos = 0
        for d in range(nDias):
            if horario[i][d] != 0:
                dias_consecutivos += 1
                if dias_consecutivos > 5:
                    custo += 50
            else:
                dias_consecutivos = 0

        for d in range(1, nDias):
            if horario[i][d - 1] == 2 and horario[i][d] == 1:
                custo += 100

    return custo

# Vizinhança (troca aleatória de dois dias se não forem férias)
def gerar_vizinho(horario):
    vizinho = horario.copy()
    i = random.randint(0, nFuncionarios - 1)
    d1 = random.randint(0, nDias - 1)
    d2 = random.randint(0, nDias - 1)
    while ferias[i][d1] or ferias[i][d2]:
        d1 = random.randint(0, nDias - 1)
        d2 = random.randint(0, nDias - 1)
    vizinho[i][d1], vizinho[i][d2] = vizinho[i][d2], vizinho[i][d1]
    return vizinho

# Algoritmo Simulated Annealing
def simulated_annealing(horario, funcionarios, feriados, preferencias, alarmes):
    temperatura = temperatura_inicial
    solucao_atual = horario
    custo_atual = calcular_custo(solucao_atual, feriados)
    melhor_solucao = solucao_atual
    melhor_custo = custo_atual

    while temperatura > temperatura_final:
        for _ in range(100):
            vizinho = gerar_vizinho(solucao_atual)
            custo_vizinho = calcular_custo(vizinho, feriados)
            delta = custo_vizinho - custo_atual
            if delta < 0 or random.uniform(0, 1) < np.exp(-delta / temperatura):
                solucao_atual = vizinho
                custo_atual = custo_vizinho
                if custo_atual < melhor_custo:
                    melhor_solucao = solucao_atual
                    melhor_custo = custo_atual
        temperatura *= taxa_resfriamento
    return melhor_solucao, melhor_custo

# Exportação CSV
def salvar_csv(horario, ferias, nDias, preferencias):
    with open("calendario2.csv", "w", newline="") as csvfile:
        nTrabs = horario.shape[0]
        csvwriter = csv.writer(csvfile)
        header = ["Funcionário"] + [f"Dia {d + 1}" for d in range(nDias)] + ["Dias Trabalhados", "Dias de Férias"]
        csvwriter.writerow(header)

        for e in range(nTrabs):
            employee_schedule = []
            equipe = None
            if 0 in preferencias[e] and 1 not in preferencias[e]:
                equipe = 'A'
            elif 1 in preferencias[e] and 0 not in preferencias[e]:
                equipe = 'B'

            dias_trabalhados = np.sum(horario[e] != 0)
            dias_ferias = np.sum(ferias[e])

            for d in range(nDias):
                if ferias[e][d]:
                    shift = "F"
                elif horario[e][d] == 1:
                    shift = f"M_{equipe}" if equipe else "M"
                elif horario[e][d] == 2:
                    shift = f"T_{equipe}" if equipe else "T"
                else:
                    shift = "0"
                employee_schedule.append(shift)

            csvwriter.writerow([f"Funcionário {e + 1}"] + employee_schedule + [dias_trabalhados, dias_ferias])

# Execução principal
if __name__ == "__main__":
    funcionarios = [f"Funcionario_{i+1}" for i in range(nFuncionarios)]
    solucao_inicial = gerar_solucao_inicial()
    melhor_agenda, melhor_custo = simulated_annealing(solucao_inicial, funcionarios, feriados, preferencias, alarmes)
    print("Custo final:", melhor_custo)
    salvar_csv(melhor_agenda, ferias, nDias, preferencias)
    print("Calendário exportado para calendario2.csv")

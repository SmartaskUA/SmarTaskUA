import numpy as np
import random
import csv

# --- Configurações principais ---
nFuncionarios = 15
nDias = 365
turnos = [0, 1, 2]  # 0 = folga, 1 = manhã, 2 = tarde

# --- Gerar feriados aleatórios (por enquanto 13 dias como em Portugal) ---
feriados = np.zeros(nDias, dtype=bool)
feriados[np.random.choice(nDias, size=13, replace=False)] = True

# --- Gerar alarmes aleatórios (10% dos dias com alarme) ---
alarmes = np.zeros(nDias, dtype=bool)
alarmes[np.random.choice(nDias, size=int(nDias * 0.1), replace=False)] = True

# --- Gerar preferências aleatórias (0 = indiferente, 1 = manhã, 2 = tarde) ---
preferencias = np.random.randint(0, 3, size=(nFuncionarios, nDias))

# --- Gerar funcionários (lista de nomes fictícios) ---
funcionarios = [f"Funcionário {i+1}" for i in range(nFuncionarios)]

# --- Função para gerar uma solução inicial válida ---
def gerar_solucao_inicial():
    solucao = np.zeros((nFuncionarios, nDias), dtype=int)

    for i in range(nFuncionarios):
        dias_trabalhados = 0
        dias_consecutivos = 0
        ultima_entrada = -1
        domingos_feriados = 0

        j = 0
        while j < nDias:
            if dias_trabalhados >= 223:
                solucao[i][j:] = 0
                break

            dia_semana = j % 7
            eh_feriado = feriados[j]

            # Verifica se precisa folgar
            if dias_consecutivos >= 5:
                solucao[i][j] = 0
                dias_consecutivos = 0
                ultima_entrada = -1
                j += 1
                continue

            if random.random() < 0.7:
                turno = random.choice([1, 2])

                # Impede sequência T→M
                if ultima_entrada == 2 and turno == 1:
                    turno = 2  # força tarde ou folga
                    if random.random() < 0.5:
                        turno = 0

                if turno != 0:
                    if (dia_semana == 6 or eh_feriado) and domingos_feriados >= 22:
                        turno = 0  # já excedeu domingos/feriados

                solucao[i][j] = turno

                if turno == 0:
                    dias_consecutivos = 0
                    ultima_entrada = -1
                else:
                    dias_trabalhados += 1
                    dias_consecutivos += 1
                    ultima_entrada = turno
                    if (dia_semana == 6 or eh_feriado):
                        domingos_feriados += 1
            else:
                solucao[i][j] = 0
                dias_consecutivos = 0
                ultima_entrada = -1

            j += 1

    return solucao


# --- Função objetivo ---
def funcao_objetivo(agenda, funcionarios, feriados, preferencias, alarmes):
    penalidade = 0
    n_funcionarios, n_dias = agenda.shape

    for i in range(n_funcionarios):
        dias_trabalhados = 0
        domingos_feriados = 0
        dias_consecutivos = 0
        max_consecutivos = 0
        folgas = 0
        ultima_entrada = -1

        for j in range(n_dias):
            turno = agenda[i][j]
            dia_semana = j % 7
            feriado = feriados[j]

            if turno != 0:
                dias_trabalhados += 1
                dias_consecutivos += 1
                if (dia_semana == 6 or feriado):
                    domingos_feriados += 1
                if ultima_entrada != -1:
                    if ultima_entrada == 2 and turno == 1:
                        penalidade += 150  # Tarde → Manhã
                ultima_entrada = turno
            else:
                if dias_consecutivos > max_consecutivos:
                    max_consecutivos = dias_consecutivos
                dias_consecutivos = 0
                folgas += 1
                ultima_entrada = -1

            preferencia = preferencias[i][j]
            if turno != 0 and preferencia != 0 and turno != preferencia:
                penalidade += 5

        if max_consecutivos > 5:
            penalidade += (max_consecutivos - 5) * 100
        if domingos_feriados > 22:
            penalidade += (domingos_feriados - 22) * 80
        if dias_trabalhados != 223:
            penalidade += abs(dias_trabalhados - 223) * 60

    # Penalidade por falta de cobertura em dias com alarme
    for j in range(n_dias):
        if alarmes[j] == 1:
            cobertura = sum(agenda[i][j] != 0 for i in range(n_funcionarios))
            if cobertura == 0:
                penalidade += 20

    return penalidade

# --- Função para gerar vizinho ---
def gerar_vizinho(agenda):
    novo = agenda.copy()
    i = random.randint(0, novo.shape[0] - 1)
    j = random.randint(0, novo.shape[1] - 1)
    novo[i][j] = random.choice(turnos)
    return novo

# --- Simulated Annealing ---
def simulated_annealing(solucao_inicial, funcionarios, feriados, preferencias, alarmes, temp_inicial=1000, temp_final=1, alpha=0.98, max_iter=5000):
    atual = solucao_inicial
    melhor = atual
    temp = temp_inicial
    custo_atual = funcao_objetivo(atual, funcionarios, feriados, preferencias, alarmes)
    melhor_custo = custo_atual

    for i in range(max_iter):
        vizinho = gerar_vizinho(atual)
        custo_vizinho = funcao_objetivo(vizinho, funcionarios, feriados, preferencias, alarmes)
        delta = custo_vizinho - custo_atual

        if delta < 0 or random.uniform(0, 1) < np.exp(-delta / temp):
            atual = vizinho
            custo_atual = custo_vizinho
            if custo_vizinho < melhor_custo:
                melhor = vizinho
                melhor_custo = custo_vizinho

        temp *= alpha
        if temp < temp_final:
            break

    return melhor, melhor_custo

# --- Exportar solução final para CSV ---
def salvar_csv(horario, nDias, preferencias, funcionarios):
    with open("calendario2.csv", "w", newline="") as csvfile:
        nTrabs = horario.shape[0]
        csvwriter = csv.writer(csvfile)
        header = ["Trabalhador"] + [f"Dia {d + 1}" for d in range(nDias)] + ["Dias Trabalhados", "Dias de Férias"]
        csvwriter.writerow(header)

        for e in range(nTrabs):
            employee_schedule = []
            equipe = None
            prefs = preferencias[e]

            # Simples heurística para equipe baseada em preferências
            if np.all((prefs == 1) | (prefs == 0)):
                equipe = "A"
            elif np.all((prefs == 2) | (prefs == 0)):
                equipe = "B"

            dias_trabalhados = 0
            dias_ferias = 0

            for d in range(nDias):
                turno = horario[e][d]
                if turno == 0:
                    shift = "0"
                elif turno == 1:
                    shift = f"M_{equipe}" if equipe else "M"
                    dias_trabalhados += 1
                elif turno == 2:
                    shift = f"T_{equipe}" if equipe else "T"
                    dias_trabalhados += 1
                elif turno == 9:  # se no futuro decidir usar 9 pra férias
                    shift = "F"
                    dias_ferias += 1
                else:
                    shift = "?"
                employee_schedule.append(shift)

            csvwriter.writerow([funcionarios[e]] + employee_schedule + [dias_trabalhados, dias_ferias])


# --- Execução principal ---
solucao_inicial = gerar_solucao_inicial()
melhor_agenda, melhor_custo = simulated_annealing(solucao_inicial, funcionarios, feriados, preferencias, alarmes)
print("Custo final:", melhor_custo)

# Exporta resultado para CSV
salvar_csv(melhor_agenda, nDias, preferencias, funcionarios)
print("Calendário exportado para calendario2.csv")



import random
import numpy as np
import csv
from deap import base, creator, tools, algorithms

# --- Parâmetros gerais ---
nFuncionarios = 12
nDias = 365
feriados = [i for i in range(nDias) if i % 30 == 0]
alarmes = []  # Ignorar por agora

# --- Gerar férias (30 dias por funcionário, bem distribuídas) ---
ferias = np.zeros((nFuncionarios, nDias), dtype=bool)

for i in range(nFuncionarios):
    ferias_dias = []
    blocos = list(range(0, nDias, nDias // 30))
    random.shuffle(blocos)
    for bloco in blocos[:30]:
        inicio = bloco
        fim = min(bloco + (nDias // 30), nDias)
        dia = random.randint(inicio, fim - 1)
        ferias_dias.append(dia)
    ferias[i, ferias_dias] = True

# --- Preferências de turnos ---
preferencias = []
for _ in range(nFuncionarios):
    preferencias.append(random.sample([1, 2], k=random.randint(1, 2)))

# --- DEAP Setup ---
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", np.ndarray, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

# Gera indivíduo: matriz (funcionários x dias) com 0 (folga) ou 1 (M) ou 2 (T)
def gerar_individuo():
    individuo = np.zeros((nFuncionarios, nDias), dtype=int)
    for i in range(nFuncionarios):
        dias_trabalho = 0
        j = 0
        while j < nDias and dias_trabalho < 223:
            if ferias[i][j]:
                j += 1
                continue

            dias_lote = random.randint(1, min(5, 223 - dias_trabalho))
            turno = random.choice(preferencias[i])
            valid = True

            # Verifica se haverá violação ao inserir esse bloco
            for k in range(dias_lote):
                dia = j + k
                if dia >= nDias or ferias[i][dia]:
                    valid = False
                    break

                # Verifica dias antes e depois para evitar ultrapassar 5
                antes = sum(1 for d in range(dia - 5, dia) if 0 <= d < nDias and individuo[i][d] != 0)
                depois = sum(1 for d in range(dia + 1, dia + 6) if d < nDias and individuo[i][d] != 0)
                if antes + 1 + depois > 5:
                    valid = False
                    break

            if not valid:
                j += 1
                continue

            for k in range(dias_lote):
                dia = j + k
                if dia >= nDias:
                    break
                individuo[i][dia] = turno
                dias_trabalho += 1

            j += dias_lote
            if j < nDias:
                individuo[i][j] = 0  # folga obrigatória
                j += 1
    return individuo

def mutacao(individuo):
    i = random.randint(0, nFuncionarios - 1)
    dias_validos = [d for d in range(nDias) if not ferias[i][d]]

    if len(dias_validos) < 2:
        return individuo,

    d1, d2 = random.sample(dias_validos, 2)

    novo_ind = np.copy(individuo)
    novo_ind[i][d1], novo_ind[i][d2] = novo_ind[i][d2], novo_ind[i][d1]

    dias_consec = 0
    for d in range(nDias):
        if novo_ind[i][d] != 0:
            dias_consec += 1
            if dias_consec > 5:
                return individuo,
        else:
            dias_consec = 0

    return creator.Individual(novo_ind),


def cruzamento(ind1, ind2):
    i = random.randint(0, nFuncionarios - 1)
    ponto = random.randint(1, nDias - 2)

    child1 = np.copy(ind1)
    child2 = np.copy(ind2)

    child1[i, ponto:], child2[i, ponto:] = np.copy(ind2[i, ponto:]), np.copy(ind1[i, ponto:])

    def verifica_consecutivos(ind):
        for d in range(1, nDias):
            if sum(ind[i, max(0, d - 5):d + 1] != 0) > 5:
                return False
        return True

    if verifica_consecutivos(child1) and verifica_consecutivos(child2):
        return creator.Individual(child1), creator.Individual(child2)
    else:
        return ind1, ind2


# Avaliação (fitness)
def avaliar(individuo):
    custo = 0
    for i in range(nFuncionarios):
        dias_trabalhados = np.sum((individuo[i] != 0) & (~ferias[i]))
        domingos_feriados = sum(
            1 for d in range(nDias)
            if (d % 7 == 6 or d in feriados) and individuo[i][d] != 0 and not ferias[i][d]
        )
        if dias_trabalhados > 223:
            custo += (dias_trabalhados - 223) * 50
        elif dias_trabalhados < 223:
            custo += (223 - dias_trabalhados) * 10

        if domingos_feriados > 22:
            custo += (domingos_feriados - 22) * 20

        dias_consecutivos = 0
        for d in range(nDias):
            if individuo[i][d] != 0:
                dias_consecutivos += 1
                if dias_consecutivos > 5:
                    custo += 50
            else:
                dias_consecutivos = 0

        for d in range(1, nDias):
            if individuo[i][d - 1] == 2 and individuo[i][d] == 1:
                custo += 100

    return custo,

toolbox.register("individual", tools.initIterate, creator.Individual, gerar_individuo)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("mate", cruzamento)
toolbox.register("mutate", mutacao)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("evaluate", avaliar)

# Exportação CSV
def salvar_csv(horario, ferias, nDias, preferencias):
    with open("calendario3.csv", "w", newline="") as csvfile:
        nTrabs = horario.shape[0]
        csvwriter = csv.writer(csvfile)
        header = ["Funcionário"] + [f"Dia {d + 1}" for d in range(nDias)] + ["Dias Trabalhados", "Dias de Férias"]
        csvwriter.writerow(header)

        for e in range(nTrabs):
            employee_schedule = []
            equipe = None
            if 1 in preferencias[e] and 2 not in preferencias[e]:
                equipe = 'A'
            elif 2 in preferencias[e] and 1 not in preferencias[e]:
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
    random.seed(42)
    populacao = toolbox.population(n=30)
    NGEN = 30
    for gen in range(NGEN):
        filhos = algorithms.varAnd(populacao, toolbox, cxpb=0.5, mutpb=0.2)
        fits = toolbox.map(toolbox.evaluate, filhos)
        for fit, ind in zip(fits, filhos):
            ind.fitness.values = fit
        populacao = toolbox.select(filhos, k=len(populacao))
        melhor = tools.selBest(populacao, 1)[0]
        print(f"Geração {gen}, Custo: {melhor.fitness.values[0]}")

    salvar_csv(melhor, ferias, nDias, preferencias)
    print("Calendário exportado para calendario3.csv")
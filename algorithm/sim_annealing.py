import numpy as np
import time
import csv

# Definindo as preferências dos trabalhadores
Prefs = [
    [0], [0], [1], [1], [0, 1], [0, 1], [1], [0], [1], [0], [1], [1], [0, 1], [0, 1], [0, 1]
]

nTrabs = len(Prefs)  # Número de trabalhadores (baseado no número de preferências)
nDias = 365  # Número de dias no ano
nDiasFerias = 30  # Número de dias de férias por trabalhador
nDiasTrabalho = 223  # Número de dias de trabalho no ano
nDiasTrabalhoFDS = 22  # Número máximo de dias trabalhados nos finais de semana
nDiasSeguidos = 5  # Número máximo de dias seguidos de trabalho
nMinTrabs = 2  # Número mínimo de turnos que um trabalhador deve fazer
nMaxFolga = 142  # Número máximo de dias de folga
nTurnos = 2  # Número de turnos por dia (Manhã e Tarde)


# Função para definir férias em blocos de no mínimo 3 dias
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


# Função para o critério 1 (Limite de dias seguidos de trabalho)
def criterio1(horario, nDiasSeguidos):
    f1 = np.zeros(horario.shape[0], dtype=int)
    for i in range(horario.shape[0]):
        seq = np.sum(horario[i], axis=1)
        count = 0
        for day in seq:
            if day == 1:
                count += 1
                if count >= nDiasSeguidos:
                    f1[i] += 1
            else:
                count = 0
    return f1


# Função para o critério 2 (Limite de dias de trabalho nos finais de semana)
def criterio2(horario, fds, nDiasTrabalhoFDS):
    return np.maximum(np.sum(np.sum(horario * fds[:, :, None], axis=1), axis=1) - nDiasTrabalhoFDS, 0)


# Função para o critério 3 (Número mínimo de turnos de trabalho)
def criterio3(horario, nMinTrabs):
    return np.sum(np.sum(horario, axis=(0, 2)) < nMinTrabs)


# Função para o critério 4 (Limite de folgas)
def criterio4(horario, nMaxFolga):
    folgas = nDias - np.sum(horario, axis=(1, 2))
    return np.abs(folgas - nMaxFolga)


# Função otimizada para o critério 5 (Proibição de "T_A" seguido de "M_A" ou "T_B" seguido de "M_B")
def criterio5(horario, Prefs):
    f5 = np.zeros(horario.shape[0], dtype=int)
    for i in range(horario.shape[0]):
        if 0 in Prefs[i] or 1 in Prefs[i]:
            for d in range(nDias - 1):
                if 0 in Prefs[i]:
                    if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                        f5[i] += 1
                if 1 in Prefs[i]:
                    if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                        f5[i] += 1
    return f5


def calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga):
    f1 = criterio1(horario, nDiasSeguidos)
    f2 = criterio2(horario, fds, nDiasTrabalhoFDS)
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


def salvar_csv(horario, Ferias, nTurnos, nDias, Prefs):
    with open("calendario2.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        header = ["Trabalhador"] + [f"Dia {d + 1}" for d in range(nDias)] + ["Dias Trabalhados", "Dias de Férias"]
        csvwriter.writerow(header)

        for e in range(nTrabs):
            employee_schedule = []
            equipe = 'A' if 0 in Prefs[e] else 'B' if 1 in Prefs[e] else 'Ambas'
            dias_trabalhados = np.sum(np.sum(horario[e], axis=1))  # Total working days
            dias_ferias = np.sum(Ferias[e])  # Total vacation days

            for d in range(nDias):
                shift = "Fe" if Ferias[e, d] else "0"
                if not Ferias[e, d]:
                    if horario[e, d, 0] == 1:
                        shift = f"M_{equipe}"
                    elif horario[e, d, 1] == 1:
                        shift = f"T_{equipe}"
                employee_schedule.append(shift)

            # Writing worker data to CSV
            csvwriter.writerow([f"Empregado{e + 1}"] + employee_schedule + [dias_trabalhados, dias_ferias])


# Início
start_time = time.time()

f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs,
                                                            nMaxFolga)
equipe_A, equipe_B, ambas = identificar_equipes(Prefs)


# Função objetivo: soma ponderada das penalizações
def funcao_objetivo(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga):
    f1, f2, f3, f4, f5 = calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga)
    return (
            np.sum(f1) * 10 +
            np.sum(f2) * 10 +
            f3 * 5 +
            np.sum(f4) * 2 +
            np.sum(f5) * 10
    )


# Gera um vizinho: altera um turno aleatório de um trabalhador num dia válido
def gerar_vizinho(horario, Ferias):
    novo_horario = horario.copy()
    i = np.random.randint(0, horario.shape[0])  # trabalhador
    d = np.random.randint(0, horario.shape[1])  # dia

    if not Ferias[i, d]:  # só altera se não estiver de férias
        turno_atual = np.argmax(novo_horario[i, d])
        novo_horario[i, d] = 0  # limpa os turnos
        novo_turno = np.random.choice([0, 1])
        novo_horario[i, d, novo_turno] = 1

    return novo_horario


# Algoritmo de Simulated Annealing
def simulated_annealing(horario_inicial, Ferias, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga,
                        temp_inicial=1000, temp_final=0.1, alpha=0.95, max_iter=1000):
    atual = horario_inicial
    melhor = atual
    custo_atual = funcao_objetivo(atual, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga)
    melhor_custo = custo_atual
    temp = temp_inicial

    for iter in range(max_iter):
        vizinho = gerar_vizinho(atual, Ferias)
        custo_vizinho = funcao_objetivo(vizinho, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga)

        if custo_vizinho < custo_atual or np.random.rand() < np.exp(-(custo_vizinho - custo_atual) / temp):
            atual = vizinho
            custo_atual = custo_vizinho
            if custo_vizinho < melhor_custo:
                melhor = vizinho
                melhor_custo = custo_vizinho

        temp *= alpha
        if temp < temp_final:
            break

    return melhor


# Início do processo
start_time = time.time()

# Otimização com Simulated Annealing
print("🔄 Otimizando com Simulated Annealing...")
horario_otimizado = simulated_annealing(horario, Ferias, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga)

# Avaliação final
f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = calcular_criterios(horario_otimizado, fds, nDiasSeguidos, nDiasTrabalhoFDS,
                                                            nMinTrabs, nMaxFolga)
print("✅ Otimização concluída.")
print("Critérios finais:", sum(f1_opt), sum(f2_opt), f3_opt, sum(f4_opt), sum(f5_opt))

# Salvar o horário otimizado
salvar_csv(horario_otimizado, Ferias, nTurnos, nDias, Prefs)
print(f"📁 Arquivo 'calendario.csv' salvo. Tempo total: {time.time() - start_time:.2f} segundos")

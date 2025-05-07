import pandas as pd
import numpy as np
import time
import csv
import io

# Definindo as preferências dos trabalhadores
Prefs = [
    [0], [0], [1], [1], [0, 1], [0, 1], [1], [0], [1], [0], [1], [1]
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

# Definindo os feriados
feriados = [31, 60, 120, 150, 200, 240, 300, 330]

minimos_equipa_A_manha = [2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2,
                          2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2,
                          2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2,
                          2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1,
                          2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2,
                          2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2,
                          1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2,
                          2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2,
                          2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2,
                          2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2,
                          2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1,
                          2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2]
minimos_equipa_A_tarde = [2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2,
                          2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2,
                          2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2,
                          2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1,
                          2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2,
                          2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2,
                          1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2,
                          2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2,
                          2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2,
                          2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2,
                          2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1,
                          2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2]

minimos_equipa_B_manha = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
minimos_equipa_B_tarde = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]


# Função para definir férias lendo um csv
def ler_ferias_csv(caminho_csv, nDias):
    df = pd.read_csv(caminho_csv, header=None)

    nTrabs = len(df)  # Número de trabalhadores
    Ferias = np.zeros((nTrabs, nDias), dtype=bool)

    # Preenche a matriz de férias com base no CSV
    for trab, row in df.iterrows():
        # Ignora o nome do trabalhador (primeira coluna) e usa o restante para os dias de férias
        Ferias[trab] = row[1:].values == 1  # Transforma 1 em True (férias) e 0 em False (não férias)

    return Ferias


# Ferias = ler_ferias_csv("../feriasR.csv", nDias)

# fds = np.zeros((nTrabs, nDias), dtype=bool)
# fds[:, 4::7] = True     #domingos

# dias = np.where(~Ferias)

# horario = np.zeros((nTrabs, nDias, nTurnos), dtype=int)
# # Assumindo que você tenha 'nTrabs' como número de trabalhadores
# nTrabs = Ferias.shape[0]  # Número de trabalhadores (linhas de Ferias)


def atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos):
    for i in range(nTrabs):
        dias_disponiveis = np.where(~Ferias[i])[0]
        np.random.shuffle(dias_disponiveis)

        turnos_assigned = 0
        d = 0

        while turnos_assigned < nDiasTrabalho and d < len(dias_disponiveis):
            dia = dias_disponiveis[d]
            turnos_possiveis = []

            for turno in Prefs[i]:
                if turno == 1:  # Tarde
                    if dia + 1 >= nDias or horario[i, dia + 1, 0] == 0:
                        turnos_possiveis.append(turno)
                elif turno == 0:  # Manhã
                    if dia - 1 < 0 or horario[i, dia - 1, 1] == 0:
                        turnos_possiveis.append(turno)
                else:
                    turnos_possiveis.append(turno)

            if turnos_possiveis:
                turno = np.random.choice(turnos_possiveis)
                horario[i, dia, turno] = 1
                turnos_assigned += 1
                d += 2 if turno == 1 else 1
            else:
                d += 1

        if turnos_assigned < nDiasTrabalho:
            for dia in dias_disponiveis:
                if turnos_assigned >= nDiasTrabalho:
                    break
                for turno in Prefs[i]:
                    if horario[i, dia, turno] == 0:
                        horario[i, dia, turno] = 1
                        turnos_assigned += 1
                        break


# atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos)

# Função para calcular o número de dias seguidos trabalhados 5 máximo
def criterio1(horario, nDiasSeguidos):
    f1 = np.zeros(horario.shape[0], dtype=int)  # Armazenar o número de sequências válidas
    dias_trabalhados = np.sum(horario, axis=2) > 0  # matriz trabalhor x dia , pelo menos 1 turno - true

    janela = np.ones(nDiasSeguidos, dtype=int)  # cria um vetor 5 dias

    for i in range(horario.shape[0]):
        # convolução contar quantos dias seguidos foram trabalhados em blocos
        sequencia = np.convolve(dias_trabalhados[i].astype(int), janela,
                                mode='valid')  # deslisa a janela e multiplica (deteta sequencias)
        f1[i] = np.sum(sequencia == nDiasSeguidos)  # [1, 1, 1, 1, 1, 1, 0, 1]   -- [5,5,4,4]

    return f1


# um limite de 22 dias de trabalho no total durante fins de semana (domingos) e feriados
def criterio2(horario, fds, nDiasTrabalhoFDS, feriados):
    # Criação do vetor booleana para marcar finais de semana e feriados
    dias_ano = np.arange(horario.shape[1])

    dias_fds = fds.sum(axis=0) > 0  # domingos
    dias_feriados = np.isin(dias_ano, feriados)  # feriados
    dias_fds_feriados = dias_fds | dias_feriados
    dias_fds_feriados = dias_fds_feriados[None, :, None]  # ajustar array para Forma (1, 365, 1)

    dias_trabalhados = np.sum(horario * dias_fds_feriados,
                              axis=(1, 2))  # soma de turnos trabalhados em finais de semana e feriados

    excedente = np.maximum(dias_trabalhados - nDiasTrabalhoFDS,
                           0)  # calcula o excedente de dias trabalhados em relação ao limite permitido

    return excedente


# vereficar numero de trabalhadores  abaixo do mínimo necessário
def criterio3(horario, nMinTrabs):
    trabalhadores_por_dia = np.sum(horario, axis=1)  # Soma de trabalhadores por dia em coluna
    dias_com_menos_trabalhadores = np.sum(trabalhadores_por_dia < nMinTrabs,
                                          axis=1)  # Para cada trabalhador, contamos quantos dias têm menos trabalhadores que o mínimo necessário.

    return np.sum(dias_com_menos_trabalhadores)


# Diferença entre folgas e limite máximo permitido

def criterio4(horario, nMaxFolga):
    Ferias = ler_ferias_csv("../feriasR.csv", nDias)
    dias_trabalhados_por_trabalhador = []

    for i in range(horario.shape[0]):  # Iterar por cada trabalhador
        dias_trabalhados = 0

        # Contar os dias trabalhados
        dias_trabalhados = np.sum(np.sum(horario[i, :] > 0, axis=1) & ~Ferias[i, :])

        dias_trabalhados_por_trabalhador.append(dias_trabalhados)

    dias_diferenca = np.abs(np.array(dias_trabalhados_por_trabalhador) - nDiasTrabalho)

    return dias_diferenca


# def criterio5(horario, Prefs):
#     f5 = np.zeros(horario.shape[0], dtype=int)

#     for i, pref in enumerate(Prefs):  # trabalhor e preferencias
#         if any(p in pref for p in [0, 1]):  # ve se é M ou T
#             # Loop sobre os dias
#             for d in range(nDias - 1):
#                 # Verifica se houve a sequência Tarde seguida de Manhã
#                 if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
#                     f5[i] += 1
#     return f5

def criterio5(horario):
    f5 = np.zeros(horario.shape[0], dtype=int)  # Vetor para contar as sequências

    # Verifica os turnos de cada trabalhador
    for i in range(horario.shape[0]):  # Para cada trabalhador
        for d in range(horario.shape[1] - 1):  # Para cada dia (exceto o último)
            # Verifica se houve Tarde (1) no dia `d` e Manhã (0) no dia `d+1`
            if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                f5[i] += 1  # Incrementa a contagem para esse trabalhador

    return f5


def criterio6(horario, minimos_equipa_A_manha, minimos_equipa_A_tarde, minimos_equipa_B_manha, minimos_equipa_B_tarde,
              Prefs):
    nTrabs, nDias, _ = horario.shape
    violacoes_por_trab = np.zeros(nTrabs, dtype=int)

    equipe_A, equipe_B, ambas = identificar_equipes(
        Prefs)  # A função identificar_equipes deve estar definida em algum lugar

    equipe_A_set = set(equipe_A)
    equipe_B_set = set(equipe_B)
    ambas_set = set(ambas)

    # Totais de trabalhadores por turno para cada equipe
    A_manha_totais = np.sum(horario[equipe_A, :, 0], axis=0) + np.sum(horario[ambas, :, 0], axis=0)
    A_tarde_totais = np.sum(horario[equipe_A, :, 1], axis=0) + np.sum(horario[ambas, :, 1], axis=0)
    B_manha_totais = np.sum(horario[equipe_B, :, 0], axis=0) + np.sum(horario[ambas, :, 0], axis=0)
    B_tarde_totais = np.sum(horario[equipe_B, :, 1], axis=0) + np.sum(horario[ambas, :, 1], axis=0)

    for d in range(nDias):
        for i in range(nTrabs):
            prefs = Prefs[i]

            # Verificando se o trabalhador deve trabalhar no turno da manhã
            if 0 in prefs:
                if i in equipe_A_set or i in ambas_set:
                    if horario[i, d, 0] == 1 and A_manha_totais[d] < minimos_equipa_A_manha[d]:
                        violacoes_por_trab[i] += 1
                if i in equipe_B_set or i in ambas_set:
                    if horario[i, d, 0] == 1 and B_manha_totais[d] < minimos_equipa_B_manha[d]:
                        violacoes_por_trab[i] += 1

            # Verificando se o trabalhador deve trabalhar no turno da tarde
            if 1 in prefs:
                if i in equipe_A_set or i in ambas_set:
                    if horario[i, d, 1] == 1 and A_tarde_totais[d] < minimos_equipa_A_tarde[d]:
                        violacoes_por_trab[i] += 1
                if i in equipe_B_set or i in ambas_set:
                    if horario[i, d, 1] == 1 and B_tarde_totais[d] < minimos_equipa_B_tarde[d]:
                        violacoes_por_trab[i] += 1

    return violacoes_por_trab


# Função para calcular os critérios
def calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados):
    f1 = criterio1(horario, nDiasSeguidos)
    f2 = criterio2(horario, fds, nDiasTrabalhoFDS, feriados)
    f3 = criterio3(horario, nMinTrabs)
    f4 = criterio4(horario, nMaxFolga)
    f5 = criterio5(horario)
    f6 = criterio6(horario, minimos_equipa_A_manha, minimos_equipa_A_tarde, minimos_equipa_B_manha,
                   minimos_equipa_B_tarde, Prefs)
    return f1, f2, f3, f4, f5, f6


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


def salvar_csv(horario, Ferias, nTurnos, nDias, Prefs):
    output = io.StringIO()
    csvwriter = csv.writer(output)

    header = ["funcionario"] + [f"Dia {d + 1}" for d in range(nDias)]
    csvwriter.writerow(header)

    for e in range(nTrabs):
        employee_schedule = []
        equipe = 'A' if 0 in Prefs[e] else 'B' if 1 in Prefs[e] else 'Ambas'
        dias_trabalhados = np.sum(np.sum(horario[e], axis=1))
        dias_ferias = np.sum(Ferias[e])

        for d in range(nDias):
            shift = "F" if Ferias[e, d] else "0"
            if not Ferias[e, d]:
                if horario[e, d, 0] == 1:
                    shift = f"M_{equipe}"
                elif horario[e, d, 1] == 1:
                    shift = f"T_{equipe}"
            employee_schedule.append(shift)

        csvwriter.writerow([f"Empregado{e + 1}"] + employee_schedule)

    with open("calendario.csv", "w", encoding="utf-8", newline="") as f:
        f.write(output.getvalue())

    return output.getvalue()


def solve():
    start_time = time.time()
    Ferias = ler_ferias_csv("../feriasR.csv", nDias)
    dias = np.where(~Ferias)
    global horario
    fds = np.zeros((nTrabs, nDias), dtype=bool)
    fds[:, 4::7] = True  # domingos
    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, f6_opt = calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS,
                                                                        nMinTrabs, nMaxFolga, feriados)
    equipe_A, equipe_B, ambas = identificar_equipes(Prefs)

    t, cont = 0, 0
    max_iter = 400000

    while t < max_iter and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt) or np.any(f6_opt)):
        cont += 1
        i = np.random.randint(nTrabs)  # Seleciona aleatoriamente um trabalhador
        dias_trabalhados = dias[1][dias[0] == i]

        if len(dias_trabalhados) < 2:
            t += 1
            continue  # Pula se não houver dias suficientes para trocar

        aux = np.random.choice(len(dias_trabalhados), 2, replace=False)
        dia1, dia2 = dias_trabalhados[aux[0]], dias_trabalhados[aux[1]]
        turno1, turno2 = np.random.choice(nTurnos, 2, replace=False)

        pode_trabalhar_A = 0 in Prefs[i]
        pode_trabalhar_B = 1 in Prefs[i]

        if horario[i, dia1, turno1] != horario[i, dia2, turno2]:
            hor = horario.copy()

            # Troca os turnos de acordo com preferências
            if pode_trabalhar_A and pode_trabalhar_B:
                hor[i, dia1, turno1], hor[i, dia2, turno2] = hor[i, dia2, turno2], hor[i, dia1, turno1]
            elif pode_trabalhar_A:
                hor[i, dia1, turno1] = 1
                hor[i, dia2, turno2] = 0
            elif pode_trabalhar_B:
                hor[i, dia1, turno1] = 0
                hor[i, dia2, turno2] = 1

            # Recalcula critérios
            f1, f2, f3, f4, f5, f6 = calcular_criterios(hor, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga,
                                                        feriados)

            # Verifica se é uma solução perfeita
            if np.all(f1 == 0) and np.all(f2 == 0) and f3 == 0 and np.all(f4 == 0) and np.all(f5 == 0):
                f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, horario = f1, f2, f3, f4, f5, hor
                print("\nSolução perfeita encontrada!")
                break

            # Atualiza se a solução for melhor
            if f1[i] + f2[i] + f3 + f4[i] + f5[i] < f1_opt[i] + f2_opt[i] + f3_opt + f4_opt[i] + f5_opt[i]:
                f1_opt[i], f2_opt[i], f3_opt, f4_opt[i], f5_opt[i], horario = f1[i], f2[i], f3, f4[i], f5[i], hor

        t += 1

    execution_time = time.time() - start_time

    print(f"\nTempo de execução: {execution_time:.2f} segundos")
    print(f"Número de iterações realizadas: {cont}")

    salvar_csv(horario, Ferias, nTurnos, nDias, Prefs)

    # Adiciona a leitura do arquivo CSV gerado
    schedule = []
    with open('calendario.csv', mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, dialect='excel')
        for row in reader:
            schedule.append(row)

    return schedule


if __name__ == "__main__":
    solve()
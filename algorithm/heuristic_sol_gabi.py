import pandas as pd
import numpy as np
import time
import csv
import io
import random

# Definindo as preferências dos trabalhadores
Prefs = [
    [0], [0], [1], [1], [0, 1], [0, 1], [1], [0], [1], [0], [1], [1]
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
feriados = [1, 108, 110, 115, 121, 161, 170, 227, 278, 305, 335, 342, 359] 

#miminos das equipas
minimos_equipa_A_manha = [2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2]
minimos_equipa_A_tarde = [2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2,2,2,2,1,2,2,2]

minimos_equipa_B_manha = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
minimos_equipa_B_tarde = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]


# Função para ferias
def ler_ferias_csv(caminho_csv, nDias):

    df = pd.read_csv(caminho_csv, header=None) 
    nTrabs = len(df)  
    Ferias = np.zeros((nTrabs, nDias), dtype=bool)
    
    for trab, row in df.iterrows():
        Ferias[trab] = row[1:].values == 1 
    return Ferias

Ferias = ler_ferias_csv("algorithm/feriasA.csv", nDias)

# marcar domingos
fds = np.zeros((nTrabs, nDias), dtype=bool)
fds[:, 4::7] = True    

dias = np.where(~Ferias)    

# Criar matriz de horários
horario = np.zeros((nTrabs, nDias, nTurnos), dtype=int)
nTrabs = Ferias.shape[0]  

#atribuir turnos aos trabalhadores de maneira eficiente, respeitando as preferências dos turnos e garantindo que a sequência Tarde seguida de Manhã (T->M) seja evitada
def atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos):
    nTrabs, nDias, _ = horario.shape 

    for i in range(nTrabs): 
        dias_disponiveis = np.where(~Ferias[i])[0]
        np.random.shuffle(dias_disponiveis)
        
        turnos_assigned = 0
        d = 0

        while turnos_assigned < nDiasTrabalho and d < len(dias_disponiveis):
            dia = dias_disponiveis[d]
            turnos_possiveis = []

            for turno in Prefs[i]:
                # Verifica violação Tarde -> Manhã
                if turno == 1:  # Tarde
                    if dia + 1 >= nDias or horario[i, dia + 1, 0] == 0:  # Verifica se o dia seguinte é válido e não está ocupado
                        turnos_possiveis.append(turno)
                elif turno == 0:  # Manhã
                    if dia - 1 < 0 or horario[i, dia - 1, 1] == 0:  # Verifica se o dia anterior é válido e não está ocupado
                        turnos_possiveis.append(turno)

            if turnos_possiveis:
                turno = np.random.choice(turnos_possiveis)
                horario[i, dia, turno] = 1   
                turnos_assigned += 1    
                d += 2 if turno == 1 else 1  # Aumenta o índice de dias disponíveis para evitar T->M
            else:
                d += 1
        # Segunda chance: repetição controlada, ainda evitando T->M
        d = 0
        while turnos_assigned < nDiasTrabalho and d < len(dias_disponiveis):
            dia = dias_disponiveis[d]
            for turno in Prefs[i]:
                # Verificar violação aqui também
                if turno == 1:
                    if dia + 1 >= nDias or horario[i, dia + 1, 0] == 0:  
                        if horario[i, dia, turno] == 0:
                            horario[i, dia, turno] = 1
                            turnos_assigned += 1
                            break
                elif turno == 0:
                    if dia - 1 < 0 or horario[i, dia - 1, 1] == 0:
                        if horario[i, dia, turno] == 0:
                            horario[i, dia, turno] = 1
                            turnos_assigned += 1
                            break
            d += 1

atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos)

# Função para calcular o número de dias seguidos trabalhados 5 máximo
def criterio1(horario, nDiasSeguidos):
    f1 = np.zeros(horario.shape[0], dtype=int)                                               #Armazenar o número de sequências válidas
    dias_trabalhados = np.sum(horario, axis=2) > 0                                           #matriz trabalhor x dia , pelo menos 1 turno - true

    janela = np.ones(nDiasSeguidos, dtype=int)                                               #cria um vetor 5 dias

    for i in range(horario.shape[0]):
                                                                                             # convolução contar quantos dias seguidos foram trabalhados em blocos 
        sequencia = np.convolve(dias_trabalhados[i].astype(int), janela, mode='valid')       # deslisa a janela e multiplica (deteta sequencias)
        f1[i] = np.sum(sequencia == nDiasSeguidos)                                           # [1, 1, 1, 1, 1, 1, 0, 1]   -- [5,5,4,4]

    return f1


# um limite de 22 dias de trabalho no total durante fins de semana (domingos) e feriados 
def criterio2(horario, fds, nDiasTrabalhoFDS, feriados):
    
    dias_ano = np.arange(horario.shape[1])                                      # Criação do vetor booleana para marcar finais de semana e feriados
    
    dias_fds = fds.sum(axis=0) > 0                                              # domingos
    dias_feriados = np.isin(dias_ano, feriados)                                 # feriados
    dias_fds_feriados = dias_fds | dias_feriados                                
    dias_fds_feriados = dias_fds_feriados[None, :, None]                        # ajustar array para Forma (1, 365, 1)
    dias_trabalhados = np.sum(horario * dias_fds_feriados, axis=(1, 2))         # soma de turnos trabalhados em finais de semana e feriados
    excedente = np.maximum(dias_trabalhados - nDiasTrabalhoFDS, 0)              # calcula o excedente de dias trabalhados em relação ao limite permitido
    
    return excedente

# vereficar numero de trabalhadores  abaixo do mínimo necessário
def criterio3(horario, nMinTrabs): #

    trabalhadores_por_dia = np.sum(horario, axis=1)                                   # Soma de trabalhadores por dia em coluna 
    dias_com_menos_trabalhadores = np.sum(trabalhadores_por_dia < nMinTrabs, axis=1)  # Para cada trabalhador, contamos quantos dias têm menos trabalhadores que o mínimo necessário.
    
    return np.sum(dias_com_menos_trabalhadores)

# Diferença entre folgas e limite máximo permitido
def criterio4(horario, nMaxFolga):

    folgas = nDias - np.sum(horario, axis=(1, 2))                                   #A soma ao longo dos eixos (1, 2) soma o número de turnos trabalhados em cada dia para cada trabalhador.   
    return np.abs(folgas - nMaxFolga)


# Violação da sequência proibida: Tarde seguida de Manhã no mesmo turno
def criterio5(horario, Prefs):
    f5 = np.zeros(horario.shape[0], dtype=int)
    
    for i, pref in enumerate(Prefs):                    
        if any(p in pref for p in [0, 1]):                           # ve se é M ou T
            for d in range(nDias - 1):
                                                                     # Verifica se houve a sequência Tarde seguida de Manhã
                if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                    f5[i] += 1
    return f5


def criterio6(horario, minimos_equipa_A_manha, minimos_equipa_A_tarde, minimos_equipa_B_manha, minimos_equipa_B_tarde, Prefs):
    nTrabs, nDias, _ = horario.shape
    violacoes_por_trab = np.zeros(nTrabs, dtype=int)

    equipe_A, equipe_B, ambas = identificar_equipes(Prefs)

    equipe_A_set = set(equipe_A)
    equipe_B_set = set(equipe_B)
    ambas_set = set(ambas)

    # Calculando totais por turno e equipe de forma vetorizada
    A_manha_totais = np.sum(horario[equipe_A, :, 0], axis=0) + np.sum(horario[ambas, :, 0], axis=0)
    A_tarde_totais = np.sum(horario[equipe_A, :, 1], axis=0) + np.sum(horario[ambas, :, 1], axis=0)
    B_manha_totais = np.sum(horario[equipe_B, :, 0], axis=0) + np.sum(horario[ambas, :, 0], axis=0)
    B_tarde_totais = np.sum(horario[equipe_B, :, 1], axis=0) + np.sum(horario[ambas, :, 1], axis=0)

    for d in range(nDias):
        # Verificando violacoes para cada trabalhador de forma vetorizada
        for i in range(nTrabs):
            prefs = Prefs[i]
            
            # Verificando manhã
            if 0 in prefs:
                if i in equipe_A_set or i in ambas_set:
                    if horario[i, d, 0] == 1 and A_manha_totais[d] < minimos_equipa_A_manha[d]:
                        violacoes_por_trab[i] += 1
                if i in equipe_B_set or i in ambas_set:
                    if horario[i, d, 0] == 1 and B_manha_totais[d] < minimos_equipa_B_manha[d]:
                        violacoes_por_trab[i] += 1

            # Verificando tarde
            if 1 in prefs:
                if i in equipe_A_set or i in ambas_set:
                    if horario[i, d, 1] == 1 and A_tarde_totais[d] < minimos_equipa_A_tarde[d]:  
                        violacoes_por_trab[i] += 1
                if i in equipe_B_set or i in ambas_set:
                    if horario[i, d, 1] == 1 and B_tarde_totais[d] < minimos_equipa_B_tarde[d]:
                        violacoes_por_trab[i] += 1 

    return violacoes_por_trab

def calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados):
    f1 = criterio1(horario, nDiasSeguidos)
    f2 = criterio2(horario, fds, nDiasTrabalhoFDS, feriados)
    f3 = criterio3(horario, nMinTrabs)
    f4 = criterio4(horario, nMaxFolga)
    f5 = criterio5(horario, Prefs)
    f6 = criterio6(horario, minimos_equipa_A_manha, minimos_equipa_A_tarde, minimos_equipa_B_manha, minimos_equipa_B_tarde, Prefs)
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

    with open("calendario.csv", "w", encoding="utf-8", newline="") as f:
        f.write(output.getvalue())

    return output.getvalue() 


def solve():
    atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos)
    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, f6_opt = calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados)
    equipe_A, equipe_B, ambas = identificar_equipes(Prefs)
    salvar_csv(horario, Ferias, nTurnos, nDias, Prefs)

    schedule = []
    with open('calendario.csv', mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, dialect='excel')
        for row in reader:
            schedule.append(row)

    return schedule

# Início
start_time = time.time()

f1_opt, f2_opt, f3_opt, f4_opt, f5_opt ,f6_opt= calcular_criterios(horario, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados)
equipe_A, equipe_B, ambas = identificar_equipes(Prefs)

def print_result(label, data):
    print(f"{label}:\n{data}\n")

# Exibição dos resultados
print("Critério 1 - Dias seguidos de trabalho excedendo o limite (máx. 5 dias seguidos):                    ", f1_opt)
print("Critério 2 - Dias trabalhados em fins de semana além do permitido (máx. 22):                         ", f2_opt)
print("Critério 3 - Quantidade de turnos abaixo do mínimo necessário (mín. 2 por trabalhador):              ", f3_opt)
print("Critério 4 - Diferença entre folgas reais e limite máximo permitido (máx. 142 dias de folga) :       ", f4_opt)
print("Critério 5 - Violação da sequência proibida: Tarde seguida de Manhã no mesmo turno (preferência):    ", f5_opt)
print("Critério 6 - Violação dos mínimos diários de trabalhadores por turno:                               ", f6_opt)
print("\nTrabalhadores na equipe A:", equipe_A)
print("Trabalhadores na equipe B:", equipe_B)
print("Trabalhadores nas equipes A e B:", ambas)

t, cont = 0, 0
while t < 300000 and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt) or np.any(f6_opt)):
    cont += 1   
    i = np.random.randint(nTrabs)                                           # Seleciona aleatoriamente um trabalhador
    aux = np.random.choice(len(dias[1][dias[0] == i]), 2, replace=False)    # Seleciona aleatoriamente 2 dias para o trabalhador i
    dia1, dia2 = dias[1][dias[0] == i][aux]                                 # Define os dois dias selecionados
    turno1, turno2 = np.random.choice(nTurnos, 2, replace=False)            # Seleciona aleatoriamente 2 turnos

    pode_trabalhar_A = 0 in Prefs[i] 
    pode_trabalhar_B = 1 in Prefs[i]

    # Verifica se os turnos são diferentes, o que significa que haverá uma troca
    if horario[i, dia1, turno1] != horario[i, dia2, turno2]:
        hor = horario.copy()  # Cria uma cópia do horário atual
        if pode_trabalhar_A and pode_trabalhar_B:
            hor[i, dia1, turno1], hor[i, dia2, turno2] = hor[i, dia2, turno2], hor[i, dia1, turno1]  # Troca de turnos
        elif pode_trabalhar_A:  
            hor[i, dia1, turno1] = 1 
            hor[i, dia2, turno2] = 0
        elif pode_trabalhar_B:
            hor[i, dia1, turno1] = 0
            hor[i, dia2, turno2] = 1

        # Verifica se a troca de turnos resultou em Tarde seguida de Manhã (T -> M)
        violacao_T_M = False
        for d in range(nDias - 1):
            if hor[i, d, 1] == 1 and hor[i, d + 1, 0] == 1:  # Tarde no dia d e Manhã no dia d+1
                violacao_T_M = True
                break

        # Se não houver violação, calcula os critérios
        if not violacao_T_M:
            f1, f2, f3, f4, f5, f6 = calcular_criterios(hor, fds, nDiasSeguidos, nDiasTrabalhoFDS, nMinTrabs, nMaxFolga, feriados)

            # Verifica se a solução encontrada é perfeita
            if np.all(f1 == 0) and np.all(f2 == 0) and f3 == 0 and np.all(f4 == 0) and np.all(f5 == 0) and np.all(f6 == 0):
                f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, f6_opt, horario = f1, f2, f3, f4, f5, f6, hor
                print("\nSolução perfeita encontrada!")
                break

            # Compara a solução atual com a solução ótima
            if (f1[i] + f2[i] + f3 + f4[i] + f5[i] + f6 < f1_opt[i] + f2_opt[i] + f3_opt + f4_opt[i] + f5_opt[i] + f6_opt).any():
                f1_opt[i], f2_opt[i], f3_opt, f4_opt[i], f5_opt[i], f6_opt, horario = f1[i], f2[i], f3, f4[i], f5[i], f6, hor

    t += 1

execution_time = time.time() - start_time

print("======= RESULTADOS =======\n")
print_result("Critério 1 - Dias seguidos de trabalho excedendo o limite (máx. 5 dias seguidos)", f1_opt)
print_result("Critério 2 - Dias trabalhados nos finais de semana além do limite (máx. 22)     ", f2_opt)
print_result("Critério 3 - Turnos abaixo do mínimo necessário (mín. 2 por trabalhador)        ", f3_opt)
print_result("Critério 4 - Folgas excedendo o limite (máx. 142 dias de folga)                 ", f4_opt)
print_result("Critério 5 - Violação das preferências de turno                                 ", f5_opt)
print("Critério 6 - Violação dos mínimos diários de trabalhadores por turno:                               ", f6_opt)

print(f"\nTempo de execução: {execution_time:.2f} segundos")
print(f"Número de iterações realizadas: {cont}")


def print_tabela_completa(horario, Ferias, fds, nTrabs, nDiasSeguidos, nDiasTrabalhoFDS, Prefs, feriados, nMinTrabs):

    tabela = []

    for e in range(nTrabs):

        dias_trabalhados = np.sum(np.sum(horario[e], axis=1))                                    # Total de dias trabalhados
        dias_fds_feriados_trabalhados = np.sum(fds[e] & (np.sum(horario[e], axis=1) > 0))        # Fins de semana ou feriados trabalhados
        max_seq_trabalho = criterio1(horario, nDiasSeguidos)[e]                                  # Máximo de sequência de trabalho excedido
        transicoes_tm = criterio5(horario, Prefs)[e]                                             # Transições T -> M
        ferias_como_folga = np.sum(Ferias[e])                                                    # Dias de férias
        falhas_criterio3 = criterio3(horario, nMinTrabs)                                         # Falhas de número de trabalhadores abaixo do mínimo

        tabela.append([
            f"Funcionário {e + 1}",
            dias_fds_feriados_trabalhados,
            dias_trabalhados,
            max_seq_trabalho,
            transicoes_tm,
            ferias_como_folga,
            falhas_criterio3,
        ])
    
    print("\nTabela Completa")
    print(f"{'Funcionário':<15}{'Dom/Feriado Trabalhados':<25}{'Dias Trabalhados':<20}{'Máx Seq. Trabalho':<20}{'Transições T->M':<20}{'Férias':<20}{'nª trab minimo':<20}")

    print("=" * 160)
    
    for linha in tabela:
        print(f"{linha[0]:<15}{linha[1]:<25}{linha[2]:<20}{linha[3]:<20}{linha[4]:<20}{linha[5]:<20}{linha[6]:<20}")

print_tabela_completa(horario, Ferias, fds, nTrabs, nDiasSeguidos, nDiasTrabalhoFDS, Prefs , feriados, nMinTrabs)
salvar_csv(horario, Ferias, nTurnos, nDias, Prefs)


if __name__ == "__main__":
    print(solve())

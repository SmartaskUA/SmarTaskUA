import pandas as pd
import numpy as np
import time
import csv
import io
import datetime

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

def gerar_preferencias_automatica(employees):
    print("employes",employees)
    Prefs = []
    for emp in employees:
        equipes = emp.get('teams', [])
        
        if not isinstance(equipes, list):
            raise ValueError(f"'teams' não é uma lista válida no empregado: {emp}")
        
        if 'Equipa A' in equipes and 'Equipa B' in equipes:
            Prefs.append([0, 1]) 
        elif 'Equipa A' in equipes:
            Prefs.append([0])  
        elif 'Equipa B' in equipes:
            Prefs.append([1])  
        else:
            raise ValueError(f"O empregado não pertence a nenhuma equipa conhecida: {emp}")
    
    return Prefs


def ler_minimos_csv(minimuns, nDias):
    n_dias_totais = len(minimuns[0]) - 3
    colunas = ['equipa', 'tipo', 'turno'] + [f'dia_{i+1}' for i in range(n_dias_totais)]

    df = pd.DataFrame(minimuns, columns=colunas)

    # Normaliza strings
    df['equipa'] = df['equipa'].str.strip()
    df['tipo'] = df['tipo'].str.strip()
    df['turno'] = df['turno'].str.strip()

    # Filtros
    A_manha = df[(df['equipa'] == 'Equipa A') & (df['tipo'] == 'Minimo') & (df['turno'] == 'M')]
    A_tarde = df[(df['equipa'] == 'Equipa A') & (df['tipo'] == 'Minimo') & (df['turno'] == 'T')]
    B_manha = df[(df['equipa'] == 'Equipa B') & (df['tipo'] == 'Minimo') & (df['turno'] == 'M')]
    B_tarde = df[(df['equipa'] == 'Equipa B') & (df['tipo'] == 'Minimo') & (df['turno'] == 'T')]

    def extrair_minimos(linha):
        if linha.empty:
            return [0] * nDias
        return linha.iloc[0, 3:3 + nDias].astype(int).values

    return (
        extrair_minimos(A_manha),
        extrair_minimos(A_tarde),
        extrair_minimos(B_manha),
        extrair_minimos(B_tarde),
    )

def ler_ferias_csv(vacations, nDias):
    nTrabs = len(vacations) 
    Ferias = np.zeros((nTrabs, nDias), dtype=bool) 
    
    for trab in range(nTrabs):
        for dia in range(nDias):
            Ferias[trab, dia] = vacations[trab][dia + 1] == '1' 
    
    return Ferias

# Função para validar o número max de dias seguidos trabalhados (5 máximo)
def criterio1(horario, nDiasSeguidos):
    dias_trabalhados = np.sum(horario, axis=2) > 0
    janela = np.ones(nDiasSeguidos, dtype=int)
    sequencias = np.apply_along_axis(lambda x: np.convolve(x.astype(int), janela, mode='valid'), 1, dias_trabalhados)
    return np.sum(sequencias == nDiasSeguidos, axis=1)

# Função por validar nº de dias de trabalho em domingos e Feriados (maximo 22)

def criterio2(horario, fds, nDiasTrabalhoFDS, feriados):
    
    nTrabs, nDias, _ = horario.shape

    # Criar vetor booleano de dias proibidos (fds ou feriados)
    dias_fds_feriados = np.zeros(nDias, dtype=bool)
    dias_fds_feriados[fds] = True
    dias_fds_feriados[feriados] = True
    total_trabalhado = np.sum(horario[:, dias_fds_feriados, :], axis=(1, 2))
    
    # Cálculo de dias trabalhados em domingos e feriados
    total_trabalhado = np.sum(horario[:, fds, :], axis=(1, 2)) + np.sum(horario[:, feriados, :], axis=(1, 2))


    # Cálculo de violações: excedentes ao limite permitido
    violacoes = np.maximum(0, total_trabalhado - nDiasTrabalhoFDS)

    return violacoes



# Função para vereficar nº de trabalhadores abaixo do mínimo necessário 
def criterio3(horario, nMinTrabs):

    trabalhadores_por_dia = np.sum(horario, axis=1)                                   
    dias_com_menos_trabalhadores = np.sum(trabalhadores_por_dia < nMinTrabs, axis=1)  

    return np.sum(dias_com_menos_trabalhadores)

# Função para verificar o número máximo de folgas (máximo 142)
def criterio4(horario, Ferias, nMaxFolga):

    dias_trabalhados = np.sum(horario > 0, axis=2)
    dias_ativos = dias_trabalhados & ~Ferias
    dias_trabalhados_por_trabalhador = np.sum(dias_ativos, axis=1)
    folgas = nDias - dias_trabalhados_por_trabalhador
    excesso_folga = np.maximum(folgas - nMaxFolga, 0)

    return excesso_folga

# Função para verificar se o trabalhador não pode trabalhar em turnos consecutivos (Proibição -> T_A,M_A ou T_B,M_B)
def criterio5(horario):
    f5 = np.zeros(horario.shape[0], dtype=int)  

    for i in range(horario.shape[0]):  
        for d in range(horario.shape[1] - 1):  
            if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                f5[i] += 1  

    return f5

# Função para verificar o número mínimo de trabalhadores por turno
def criterio6(horario, minimuns, Prefs):

    nTrabs, nDias, _ = horario.shape
    violacoes_por_trab = np.zeros(nTrabs, dtype=int)
    equipe_A, equipe_B, ambas = identificar_equipes(Prefs)

    # Converte as listas de equipes em conjuntos para busca mais rápida
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
                    if horario[i, d, 0] == 1 and A_manha_totais[d] < minimuns[0][d]:
                        violacoes_por_trab[i] += 1
                if i in equipe_B_set or i in ambas_set:
                    if horario[i, d, 0] == 1 and B_manha_totais[d] < minimuns[2][d]:
                        violacoes_por_trab[i] += 1

            # Verificando se o trabalhador deve trabalhar no turno da tarde
            if 1 in prefs:
                if i in equipe_A_set or i in ambas_set:
                    if horario[i, d, 1] == 1 and A_tarde_totais[d] < minimuns[1][d]:
                        violacoes_por_trab[i] += 1
                if i in equipe_B_set or i in ambas_set:
                    if horario[i, d, 1] == 1 and B_tarde_totais[d] < minimuns[3][d]:
                        violacoes_por_trab[i] += 1

    return violacoes_por_trab


# esta bem isso 42 ferias e feriasdos
def atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos, nDias, fds_feriados, maxFDS=22):
    nTrabs = len(Prefs)
    horario = np.zeros((nTrabs, nDias, nTurnos), dtype=int)

    for i in range(nTrabs): 
        dias_disponiveis = np.where(~Ferias[i])[0]  
        np.random.shuffle(dias_disponiveis)

        turnos_assigned = 0
        dias_fds_usados = 0
        dias_usados = set()
        d = 0

        while turnos_assigned < nDiasTrabalho and d < len(dias_disponiveis):
            dia = dias_disponiveis[d]
            if dia in dias_usados:
                d += 1
                continue
            
            eh_fds = dia in fds_feriados
            if eh_fds and dias_fds_usados >= maxFDS:
                d += 1
                continue

            turnos_possiveis = []
            for turno in Prefs[i]:
                if turno == 1:  # Tarde
                    if dia + 1 >= nDias or horario[i, dia + 1, 0] == 0:
                        turnos_possiveis.append(turno)
                elif turno == 0:  # Manhã
                    if dia - 1 < 0 or horario[i, dia - 1, 1] == 0:
                        turnos_possiveis.append(turno)

            if turnos_possiveis:
                turno = np.random.choice(turnos_possiveis)
                horario[i, dia, turno] = 1
                dias_usados.add(dia)
                turnos_assigned += 1
                if eh_fds:
                    dias_fds_usados += 1
                d += 2 if turno == 1 else 1
            else:
                d += 1

        # Segunda etapa: mais flexível, mas pula fds de forma definitiva
        for dia in dias_disponiveis:
            if turnos_assigned >= nDiasTrabalho:
                break
            if dia in dias_usados:
                continue
            if dia in fds_feriados:
                continue  # Não permite mais turnos em feriados nessa etapa

            for turno in Prefs[i]:
                if horario[i, dia, turno] == 0:
                    horario[i, dia, turno] = 1
                    dias_usados.add(dia)
                    turnos_assigned += 1
                    break

    return horario



# Função para calcular os critérios

def calcular_criterios(
        horario, fds, nDiasSeguidos, nDiasTrabalhoFDS,
        nMinTrabs, nMaxFolga, feriados,
        vacations, minimuns, Prefs, nDias
    ):

    Ferias = ler_ferias_csv(vacations, nDias)

    f1 = criterio1(horario, nDiasSeguidos)
    f2 = criterio2(horario, fds, nDiasTrabalhoFDS, feriados)
    f3 = criterio3(horario, nMinTrabs)
    f4 = criterio4(horario, Ferias, nMaxFolga)
    f5 = criterio5(horario)
    #f6 = criterio6(horario, minimuns, Prefs)

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

# Função para salvar o calendário em CSV
def salvar_csv(horario, Ferias, nTurnos, nDias, Prefs):

    output = io.StringIO()
    csvwriter = csv.writer(output)
    nTrabs = len(Prefs)
    header = ["funcionario"] + [f"Dia {d+1}" for d in range(nDias)]
    csvwriter.writerow(header)

    for e in range(nTrabs):
        employee_schedule = []
        equipe = 'A' if 0 in Prefs[e] else 'B' if 1 in Prefs[e] else 'Ambas'

        for d in range(nDias):
            if Ferias[e, d]:  
                shift = "F"
            elif horario[e, d, 0] == 1:  
                shift = f"M_{equipe}"
            elif horario[e, d, 1] == 1:  
                shift = f"T_{equipe}"
            else:  
                shift = "0"
            employee_schedule.append(shift)

        csvwriter.writerow([f"Empregado{e + 1}"] + employee_schedule)

    with open("calendario.csv", "w", encoding="utf-8", newline="") as f:
        f.write(output.getvalue())

    return output.getvalue()
def identificar_domingos(nDias, ano=2025):
    domingos = []
    for d in range(nDias):
        dia = datetime.date(ano, 1, 1) + datetime.timedelta(days=d)
        if dia.weekday() == 6:  # 6 = Domingo
            domingos.append(d)
    return domingos
# Função principal para resolver o problema
def solve(vacations, minimuns, employees, maxTime):
    maxTime = int(maxTime)  * 60 

    start_time = time.time()

    # Ferias
    Ferias = ler_ferias_csv(vacations, nDias)
    dias = np.where(~Ferias) 

    # Preferências
    Prefs = gerar_preferencias_automatica(employees)
    nTrabs = len(Prefs) 
    
    # Feriados (exemplo para domingos)
    fds = np.zeros(nDias, dtype=bool)
    domingos = identificar_domingos(nDias, ano=2025)
    fds[domingos] = True


    Prefs = [np.array([0, 1]) for _ in range(nTrabs)]

    # Vetor de férias por trabalhador: Ferias[i][d] == True se o trabalhador i está de férias no dia d

    # Junta fds + feriados
    fds_feriados = list(set(fds) | set(feriados))
    fds_feriados = np.array(fds_feriados)
    fds_feriados = np.sort(fds_feriados)
    
    global horario

    horario = atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos, nDias, fds_feriados)

    minimuns = ler_minimos_csv(minimuns, nDias)
      
    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = calcular_criterios(
        horario, fds, nDiasSeguidos, nDiasTrabalhoFDS,
        nMinTrabs, nMaxFolga, feriados,
        vacations, minimuns, Prefs, nDias
    )

    t, cont = 0, 0
    max_iter = 400000
    nTrabs = len(Prefs)

    while t < max_iter and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt)):
        cont += 1

        if time.time() - start_time > maxTime:
            print("Tempo máximo atingido, parando a otimização.")
            break

        i = np.random.randint(nTrabs)
        dias_trabalhados = dias[1][dias[0] == i]    

        if len(dias_trabalhados) < 2:
            t += 1
            continue

        dia1, dia2 = np.random.choice(dias_trabalhados, 2, replace=False)
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

            f1, f2, f3, f4, f5 = calcular_criterios(
                hor, fds, nDiasSeguidos, nDiasTrabalhoFDS,
                nMinTrabs, nMaxFolga, feriados,
                vacations, minimuns, Prefs, nDias
            )

            if np.all(f1 == 0) and np.all(f2 == 0) and f3 == 0 and np.all(f4 == 0) and np.all(f5 == 0):

                f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, horario = f1, f2, f3, f4, f5, hor
                print("\nSolução perfeita encontrada!")
                break

            if np.sum(f1) + np.sum(f2) + f3 + np.sum(f4) + np.sum(f5)  < np.sum(f1_opt) + np.sum(f2_opt) + f3_opt + np.sum(f4_opt) + np.sum(f5_opt):
                f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, horario = f1, f2, f3, f4, f5, hor
        t += 1

    execution_time = time.time() - start_time
    
    print(f"\nTempo de execução: {execution_time:.2f} segundos")
    print(f"Número de iterações realizadas: {cont}")

    salvar_csv(horario, Ferias, nTurnos, nDias, Prefs)

    schedule = []
    with open('calendario.csv', mode='r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, dialect='excel')
        for row in reader:
            schedule.append(row)

    return schedule


    
if __name__ == "__main__":
    
   solve()

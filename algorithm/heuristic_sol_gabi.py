import pandas as pd
import numpy as np
import time
import csv
import io


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

def atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos, feriados):
    nTrabs = len(Prefs)
    nDias = Ferias.shape[1]
    horario = np.zeros((nTrabs, nDias, nTurnos), dtype=int)
    
    turnos_cobertura = np.zeros((nDias, nTurnos), dtype=int)
    carga_trabalho = np.zeros(nTrabs, dtype=int)
    
    for i in range(nTrabs):
        dias_disponiveis = np.where(~Ferias[i])[0]
        dias_disponiveis = sorted(dias_disponiveis, key=lambda d: sum(turnos_cobertura[d]))
        
        turnos_assigned = 0
        d = 0
        
        while turnos_assigned < nDiasTrabalho and d < len(dias_disponiveis):
            dia = dias_disponiveis[d]
            turnos_possiveis = []
            
            preferencia = Prefs[i]
            for turno in preferencia:
                if turno == 1:
                    if dia + 1 >= nDias or horario[i, dia + 1, 0] == 0:
                        turnos_possiveis.append(turno)
                elif turno == 0:
                    if dia - 1 < 0 or horario[i, dia - 1, 1] == 0:
                        turnos_possiveis.append(turno)
                else:
                    turnos_possiveis.append(turno)
            
            if turnos_possiveis:
                chance_pular = 0.3
                if len(preferencia) == 1:
                    chance_pular = 0.1  # menos chance de pular dia
                if dia in feriados or dia % 7 in [5, 6]:
                    if np.random.rand() < chance_pular:
                        d += 1
                        continue
                
                turno = np.random.choice(turnos_possiveis)
                horario[i, dia, turno] = 1
                turnos_assigned += 1
                carga_trabalho[i] += 1
                turnos_cobertura[dia, turno] += 1
                
                d += 2 if turno == 1 else 1
            else:
                d += 1
        
        # Preencher forçando se necessário, mas sempre priorizando turnos preferidos
        if turnos_assigned < nDiasTrabalho:
            for dia in dias_disponiveis:
                if turnos_assigned >= nDiasTrabalho:
                    break
                for turno in preferencia:
                    if horario[i, dia, turno] == 0:
                        horario[i, dia, turno] = 1
                        turnos_assigned += 1
                        carga_trabalho[i] += 1
                        turnos_cobertura[dia, turno] += 1
                        break
    
    return horario

# def atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos):

#     nTrabs = len(Prefs)
#     nDias = Ferias.shape[1] 
#     horario = np.zeros((nTrabs, nDias, nTurnos), dtype=int) 

#     for i in range(nTrabs): 
#         dias_disponiveis = np.where(~Ferias[i])[0]
#         np.random.shuffle(dias_disponiveis)  

#         turnos_assigned = 0
#         d = 0

#         while turnos_assigned < nDiasTrabalho and d < len(dias_disponiveis):
#             dia = dias_disponiveis[d]
#             turnos_possiveis = []

#             for turno in Prefs[i]: 
#                 if turno == 1:  # Tarde
#                     if dia + 1 >= nDias or horario[i, dia + 1, 0] == 0:
#                         turnos_possiveis.append(turno)
#                 elif turno == 0:  # Manhã
#                     if dia - 1 < 0 or horario[i, dia - 1, 1] == 0:
#                         turnos_possiveis.append(turno)
#                 else: 
#                     turnos_possiveis.append(turno)

#             if turnos_possiveis:
#                 turno = np.random.choice(turnos_possiveis)
#                 horario[i, dia, turno] = 1
#                 turnos_assigned += 1
#                 d += 2 if turno == 1 else 1  # Pula dia extra se for tarde
#             else:
#                 d += 1  

#         # Caso não tenha conseguido atingir a meta, tenta preencher à força
#         if turnos_assigned < nDiasTrabalho:
#             for dia in dias_disponiveis:
#                 if turnos_assigned >= nDiasTrabalho:
#                     break
#                 for turno in Prefs[i]:
#                     if horario[i, dia, turno] == 0:
#                         horario[i, dia, turno] = 1
#                         turnos_assigned += 1
#                         break

#     return horario
def criterio1(horario, nDiasSeguidos):
    nTrabs, nDias, _ = horario.shape
    f1 = np.zeros(nTrabs, dtype=int)  

    for i in range(nTrabs):
        dias_trabalhados = np.sum(horario[i, :, :] > 0, axis=1)  
        dias_seguidos = 0

        for j in range(nDias):
            if dias_trabalhados[j] > 0:
                dias_seguidos += 1
            else:
                if dias_seguidos > nDiasSeguidos:
                    f1[i] += dias_seguidos - nDiasSeguidos
                dias_seguidos = 0

        if dias_seguidos > nDiasSeguidos:
            f1[i] += dias_seguidos - nDiasSeguidos

    return f1

def criterio2(horario, fds_mask, nDiasTrabalhoFDS, feriados_idx):

    nTrabs, nDias, _ = horario.shape

    mascara_fds_feriados = fds_mask.copy()  
    mascara_fds_feriados[:, feriados_idx] = True  

    trabalhou_nesse_dia = (horario.sum(axis=2) > 0)  
    trabalhos_em_fds_feriados = trabalhou_nesse_dia & mascara_fds_feriados

    dias_fds_por_trab = trabalhos_em_fds_feriados.sum(axis=1)

    excesso = np.maximum(dias_fds_por_trab - nDiasTrabalhoFDS, 0)

    return excesso

# Função para verificar o número máximo de folgas (máximo 142)
def criterio3(horario, nMinTrabs):

    trabalhadores_por_dia = np.sum(horario, axis=1)                                   
    dias_com_menos_trabalhadores = np.sum(trabalhadores_por_dia < nMinTrabs, axis=1)  

    return np.sum(dias_com_menos_trabalhadores)


def criterio4(horario, nMaxFolga, Ferias):
    dias_trabalhados_por_trabalhador = []

    for i in range(horario.shape[0]): 
        dias_trabalhados = 0
        
        # Contar os dias trabalhados
        dias_trabalhados = np.sum(np.sum(horario[i, :] > 0, axis=1) & ~Ferias[i, :])
        
        dias_trabalhados_por_trabalhador.append(dias_trabalhados)

    dias_diferenca = np.abs(np.array(dias_trabalhados_por_trabalhador) - nDiasTrabalho)
    
    return dias_diferenca

# Função para verificar se o trabalhador não pode trabalhar em turnos consecutivos (Proibição -> T_A,M_A ou T_B,M_B)
def criterio5(horario):
    f5 = np.zeros(horario.shape[0], dtype=int)  
    for i in range(horario.shape[0]):  
        for d in range(horario.shape[1] - 1):  
            if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                f5[i] += 1  

    return f5

# Função para verificar se o número mínimo de trabalhadores por turno é respeitado
def criterio6(horario, minimuns, Prefs):
    nTrabs, nDias, _ = horario.shape
    violacoes = 0

    equipe_A, equipe_B, ambas = identificar_equipes(Prefs)

    # Totais de trabalhadores por turno para cada equipe
    A_manha_totais = np.sum(horario[equipe_A + ambas, :, 0], axis=0)
    A_tarde_totais = np.sum(horario[equipe_A + ambas, :, 1], axis=0)
    B_manha_totais = np.sum(horario[equipe_B + ambas, :, 0], axis=0)
    B_tarde_totais = np.sum(horario[equipe_B + ambas, :, 1], axis=0)

    # Comparar com os mínimos
    for d in range(nDias):
        if A_manha_totais[d] < minimuns[0][d]:
            violacoes += minimuns[0][d] - A_manha_totais[d]
        if A_tarde_totais[d] < minimuns[1][d]:
            violacoes += minimuns[1][d] - A_tarde_totais[d]
        if B_manha_totais[d] < minimuns[2][d]:
            violacoes += minimuns[2][d] - B_manha_totais[d]
        if B_tarde_totais[d] < minimuns[3][d]:
            violacoes += minimuns[3][d] - B_tarde_totais[d]

    return violacoes


# Função para calcular os critérios
def calcular_criterios(
        horario, fds, nDiasSeguidos, nDiasTrabalhoFDS,
        nMinTrabs, nMaxFolga, feriados,
        vacations, minimuns, Prefs, nDias
    ):

    Ferias = ler_ferias_csv(vacations, nDias)

    f1 = criterio1(horario, nDiasSeguidos)
    f2 = criterio2(horario, fds, nDiasTrabalhoFDS, feriados)
    f3 = criterio3(horario, nMinTrabs )
    f4 = criterio4(horario, nMaxFolga, Ferias)
    f5 = criterio5(horario)
    f6 = criterio6(horario, minimuns, Prefs)

    return f1, f2, f3, f4, f5, f6

# Função principal para resolver o problema
def solve(vacations, minimuns, employees, maxTime):
    maxTime = int(maxTime) * 60  
    start_time = time.time()

    # Ferias
    Ferias = ler_ferias_csv(vacations, nDias)
    dias = np.where(~Ferias)  

    # Preferências
    Prefs = gerar_preferencias_automatica(employees)
    nTrabs = len(Prefs) 

    # Feriados e finais de semana
    fds = np.zeros((nTrabs, nDias), dtype=bool)
    fds[:, 4::7] = True  # domingos

    fds_mask = np.zeros((nTrabs, nDias), dtype=bool)
    fds_mask[:, 6::7] = True  # sábados #fds[:, 4::7]

    # Leitura dos mínimos
    minimuns = ler_minimos_csv(minimuns, nDias)

    # Criação inicial do horário
    horario = atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos, feriados)

    # Cálculo dos critérios
    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, f6_opt = calcular_criterios(
        horario, fds, nDiasSeguidos, nDiasTrabalhoFDS,
        nMinTrabs, nMaxFolga, feriados,
        vacations, minimuns, Prefs, nDias
    )

    t, cont = 0, 0
    max_iter = 400000

    while t < max_iter and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt) or f6_opt > 0):
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

        if horario[i, dia1, turno1] != horario[i, dia2, turno2]:
            hor = horario.copy()
            hor[i, dia1, turno1], hor[i, dia2, turno2] = hor[i, dia2, turno2], hor[i, dia1, turno1]

            f1, f2, f3, f4, f5, f6 = calcular_criterios(
                hor, fds, nDiasSeguidos, nDiasTrabalhoFDS,
                nMinTrabs, nMaxFolga, feriados,
                vacations, minimuns, Prefs, nDias
            )

            peso = lambda f1, f2, f3, f4, f5, f6: (
                2*np.sum(f1) + 3*np.sum(f2) + 2*f3 + 1*np.sum(f4) + 3*np.sum(f5) + 4*f6
            )
            if peso(f1, f2, f3, f4, f5, f6) < peso(f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, f6_opt):

                horario = hor
                f1_opt, f2_opt, f3_opt, f4_opt, f5_opt, f6_opt = f1, f2, f3, f4, f5, f6

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
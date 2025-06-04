import pandas as pd
import numpy as np
import time
import csv
import io

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
feriados = [31, 60, 120, 150, 200, 240, 300, 330]

# Função para definir férias lendo um csv
def ler_ferias_csv(caminho_csv, nDias):

    df = pd.read_csv(caminho_csv, header=None)
    
    nTrabs = len(df)  
    Ferias = np.zeros((nTrabs, nDias), dtype=bool)
    
    for trab, row in df.iterrows():
        Ferias[trab] = row[1:].values == 1  

    return Ferias
Ferias = ler_ferias_csv("../feriasR.csv", nDias)

fds = np.zeros((nTrabs, nDias), dtype=bool)
fds[:, 4::7] = True     #domingos

dias = np.where(~Ferias)    

horario = np.zeros((nTrabs, nDias, nTurnos), dtype=int)

nTrabs = Ferias.shape[0]  


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

atribuir_turnos_eficiente(Prefs, nDiasTrabalho, Ferias, nTurnos)

# Função para calcular o número de dias seguidos trabalhados 5 máximo
def criterio1(horario, nDiasSeguidos):
    f1 = np.zeros(horario.shape[0], dtype=int)                                               
    dias_trabalhados = np.sum(horario, axis=2) > 0                                           

    janela = np.ones(nDiasSeguidos, dtype=int)                                               

    for i in range(horario.shape[0]):
                                                                                             
        sequencia = np.convolve(dias_trabalhados[i].astype(int), janela, mode='valid')       
        f1[i] = np.sum(sequencia == nDiasSeguidos)                                           

    return f1


def criterio2(horario, fds, nDiasTrabalhoFDS, feriados):
    
    dias_ano = np.arange(horario.shape[1])     
    
    dias_fds = fds.sum(axis=0) > 0                                              
    dias_feriados = np.isin(dias_ano, feriados)                                 
    dias_fds_feriados = dias_fds | dias_feriados                                
    dias_fds_feriados = dias_fds_feriados[None, :, None]                        
    
    dias_trabalhados = np.sum(horario * dias_fds_feriados, axis=(1, 2))       
    
    excedente = np.maximum(dias_trabalhados - nDiasTrabalhoFDS, 0)              
    
    return excedente

# vereficar numero de trabalhadores  abaixo do mínimo necessário
def criterio3(horario, nMinTrabs):

    trabalhadores_por_dia = np.sum(horario, axis=1)                                    
    dias_com_menos_trabalhadores = np.sum(trabalhadores_por_dia < nMinTrabs, axis=1)  
    
    return np.sum(dias_com_menos_trabalhadores)

def criterio4(horario, nMaxFolga):
    dias_trabalhados_por_trabalhador = []

    for i in range(horario.shape[0]): 
        dias_trabalhados = 0
        
        # Contar os dias trabalhados
        dias_trabalhados = np.sum(np.sum(horario[i, :] > 0, axis=1) & ~Ferias[i, :])
        
        dias_trabalhados_por_trabalhador.append(dias_trabalhados)

    dias_diferenca = np.abs(np.array(dias_trabalhados_por_trabalhador) - nDiasTrabalho)
    
    return dias_diferenca

# Violação da sequência proibida: Tarde seguida de Manhã no mesmo turno
def criterio5(horario, Prefs):
    f5 = np.zeros(horario.shape[0], dtype=int)
    
    for i, pref in enumerate(Prefs):  
        if any(p in pref for p in [0, 1]):  

            for d in range(nDias - 1):
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

def salvar_csv(horario, Ferias, nTurnos, nDias, Prefs):
    output = io.StringIO()
    csvwriter = csv.writer(output)
    
    header = ["funcionario"] + [f"Dia {d+1}" for d in range(nDias)] 
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

        csvwriter.writerow([f"Empregado{e + 1}"] + employee_schedule )

    with open("calendario.csv", "w", encoding="utf-8", newline="") as f:
        f.write(output.getvalue())

    return output.getvalue() 

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
while t < 400000 and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt)):
    cont += 1   
    i = np.random.randint(nTrabs)                                           # # Seleciona aleatoriamente um trabalhador
    aux = np.random.choice(len(dias[1][dias[0] == i]), 2, replace=False)    # Seleciona aleatoriamente 2 dias para o trabalhador i
    dia1, dia2 = dias[1][dias[0] == i][aux]                                 # Define os dois dias selecionados
    turno1, turno2 = np.random.choice(nTurnos, 2, replace=False)            # Seleciona aleatoriamente 2 turnos

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
            falhas_criterio3  
        ])
    
    print("\nTabela Completa")
    print(f"{'Funcionário':<15}{'Dom/Feriado Trabalhados':<25}{'Dias Trabalhados':<20}{'Máx Seq. Trabalho':<20}{'Transições T->M':<20}{'Férias':<20}{'nª trab minimo':<20}")
    print("=" * 160)
    
    for linha in tabela:
        print(f"{linha[0]:<15}{linha[1]:<25}{linha[2]:<20}{linha[3]:<20}{linha[4]:<20}{linha[5]:<20}{linha[6]:<20}")

print_tabela_completa(horario, Ferias, fds, nTrabs, nDiasSeguidos, nDiasTrabalhoFDS, Prefs, feriados, nMinTrabs=2)
salvar_csv(horario, Ferias, nTurnos, nDias, Prefs)
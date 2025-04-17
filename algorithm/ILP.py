import pandas as pd
import pulp
from datetime import datetime, timedelta
import holidays
import random

# --- Dados iniciais ---
ano = 2025
inicio = datetime(ano, 1, 1)
fim = datetime(ano, 12, 31)
datas = [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]
dias_uteis = len(datas)

# Feriados e domingos
feriados = holidays.country_holidays('PT', years=[ano])
feriados_set = set(feriados.keys())
domingos = {d for d in datas if d.weekday() == 6}
domingos_feriados = domingos.union(feriados_set)

# Funcionários
funcionarios = [f'F{i + 1}' for i in range(12)]
equipe_b = set(funcionarios[-3:])
equipe_a = set(funcionarios) - equipe_b

# Gerar férias aleatórias (30 dias por funcionário)
ferias = {}
for f in funcionarios:
    while True:
        inicio_ferias = random.choice(datas[:-30])
        dias_ferias = [inicio_ferias + timedelta(days=i) for i in range(30)]
        if all(d <= fim for d in dias_ferias):
            ferias[f] = dias_ferias
            break

# Modelo ILP
model = pulp.LpProblem("Escala_de_Trabalho", pulp.LpMinimize)

# Variáveis de decisão: 0 = folga, 1 = manhã, 2 = tarde
turnos = [0, 1, 2]
x = pulp.LpVariable.dicts("Turno", (funcionarios, datas, turnos), cat='Binary')

# Cada funcionário só pode estar em um turno por dia
for f in funcionarios:
    for d in datas:
        model += pulp.lpSum(x[f][d][t] for t in turnos) == 1

# Férias = folga
for f in funcionarios:
    for d in ferias[f]:
        model += x[f][d][0] == 1  # Folga
        model += x[f][d][1] == 0
        model += x[f][d][2] == 0

# Verificação mais rigorosa do limite de dias trabalhados
for f in funcionarios:
    model += pulp.lpSum(x[f][d][1] + x[f][d][2] for d in datas) <= 223

# Restrições reforçadas de sequência de turnos
for f in funcionarios:
    for i in range(len(datas) - 1):
        d1, d2 = datas[i], datas[i + 1]
        # Impedir transições inválidas
        model += x[f][d1][2] + x[f][d2][1] <= 1  # Tarde -> Manhã
        model += x[f][d1][1] + x[f][d2][0] <= 1  # Manhã -> Folga
        model += x[f][d1][2] + x[f][d2][0] <= 1  # Tarde -> Folga

# Cobertura mínima reforçada por turno
for d in datas:
    # Equipe A precisa ter pelo menos um funcionário em cada turno
    model += pulp.lpSum(x[f][d][1] for f in equipe_a) >= 1  # Manhã
    model += pulp.lpSum(x[f][d][2] for f in equipe_a) >= 1  # Tarde

    # Equipe B precisa ter pelo menos dois funcionários em cada turno
    model += pulp.lpSum(x[f][d][1] for f in equipe_b) >= 2  # Manhã
    model += pulp.lpSum(x[f][d][2] for f in equipe_b) >= 2  # Tarde

# Penalização para trabalho em domingos
model += pulp.lpSum(100 * (x[f][d][1] + x[f][d][2]) for f in funcionarios
                    for d in datas if d.weekday() == 6)

# Função objetivo final
model += pulp.lpSum(x[f][d][1] + x[f][d][2] for f in funcionarios for d in datas)

# Resolver com maior tolerância
model.solve(pulp.PULP_CBC_CMD(msg=True, options=['sec', '3600']))

# Modificar a função objetivo para maximizar dias trabalhados
# Remover a penalização por dias extras
model += pulp.lpSum(x[f][d][1] + x[f][d][2] for f in funcionarios for d in datas)

# Adicionar restrição mínima de dias trabalhados por funcionário
for f in funcionarios:
    model += pulp.lpSum(x[f][d][1] + x[f][d][2] for d in datas) >= 220, f"MinimoDias_{f}"

# Reduzir penalização para trabalho em domingos
model += pulp.lpSum(10 * (x[f][d][1] + x[f][d][2]) for f in funcionarios
                    for d in datas if d.weekday() == 6)

# Aumentar o tempo limite do solver
model.solve(pulp.PULP_CBC_CMD(msg=True, options=['sec', '7200']))  # 2 horas


def verificar_distribuicao():
    print("\nAnálise da Distribuição de Dias Trabalhados:")

    total_turnos_por_dia = {}
    for d in datas[:7]:  # Analisar os primeiros 7 dias como exemplo
        manha_total = sum(pulp.value(x[f][d][1]) for f in funcionarios)
        tarde_total = sum(pulp.value(x[f][d][2]) for f in funcionarios)

        print(f"\nDia {d.date()}:")
        print(f"- Turno Manhã: {manha_total} funcionários")
        print(f"- Turno Tarde: {tarde_total} funcionários")

    print("\nTotal de dias trabalhados por funcionário:")
    for f in funcionarios:
        dias_trabalho = sum(pulp.value(x[f][d][1]) + pulp.value(x[f][d][2])
                            for d in datas)
        print(f"{f}: {dias_trabalho} dias")




def verificar_restricoes():
    print("\nVerificação de Restrições:")

    # Verificar dias trabalhados
    for f in funcionarios:
        dias_trabalho = sum(pulp.value(x[f][d][1]) + pulp.value(x[f][d][2])
                            for d in datas)
        print(f"{f}: {dias_trabalho} dias trabalhados")

    # Verificar cobertura mínima por dia
    for d in datas[:7]:  # Verifica os primeiros 7 dias como exemplo
        manha_a = sum(pulp.value(x[f][d][1]) for f in equipe_a)
        tarde_a = sum(pulp.value(x[f][d][2]) for f in equipe_a)
        manha_b = sum(pulp.value(x[f][d][1]) for f in equipe_b)
        tarde_b = sum(pulp.value(x[f][d][2]) for f in equipe_b)

        print(f"\nDia {d.date()}:")
        print(f"Cobertura Manhã - Equipe A: {manha_a}, Equipe B: {manha_b}")
        print(f"Cobertura Tarde - Equipe A: {tarde_a}, Equipe B: {tarde_b}")


# Verificar restrições após resolver
verificar_restricoes()
verificar_distribuicao()

# Gerar CSV com calendário final no formato desejado
calendario_formatado = []

for f in funcionarios:
    linha = [f]
    dias_trabalhados = 0
    dias_ferias = 0

    for d in datas:
        if d in ferias[f]:
            turno = 'F'
            dias_ferias += 1
        elif pulp.value(x[f][d][1]) == 1:
            turno = 'M'
            dias_trabalhados += 1
        elif pulp.value(x[f][d][2]) == 1:
            turno = 'T'
            dias_trabalhados += 1
        else:
            turno = 'F'
        linha.append(turno)

    linha.append(dias_trabalhados)
    linha.append(dias_ferias)
    calendario_formatado.append(linha)

# Criar nomes das colunas
colunas = ['Funcionário'] + [f'Dia {i + 1}' for i in range(len(datas))] + ['Dias Trabalhados', 'Dias de Férias']
df_formatado = pd.DataFrame(calendario_formatado, columns=colunas)

# Salvar CSV
csv_path = "calendario4.csv"
df_formatado.to_csv(csv_path, index=False)

print(f"\nArquivo salvo em: {csv_path}")
import pulp
import pandas as pd
from datetime import date, timedelta
import holidays

# ==== PARÂMETROS BÁSICOS ====
ano = 2025
num_funcionarios = 12
dias_ano = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31').to_list()
funcionarios = list(range(num_funcionarios))
turnos = [0, 1, 2]  # 0 = folga, 1 = manhã, 2 = tarde

# ==== FERIADOS NACIONAIS + DOMINGOS ====
feriados = holidays.country_holidays("PT", years=[ano])
domingos_feriados = [
    d for d in dias_ano
    if d.weekday() == 6 or d in feriados
]

# ==== VARIÁVEIS DE DECISÃO ====
x = {
    f: {
        d: {
            t: pulp.LpVariable(f"x_{f}_{d.strftime('%Y%m%d')}_{t}", cat="Binary")
            for t in turnos
        }
        for d in dias_ano
    }
    for f in funcionarios
}

# ==== MODELO ====
model = pulp.LpProblem("Escala_Trabalho", pulp.LpMinimize)

# ==== OBJETIVO (penalizações para transições e domingos/feriados) ====
# ==== VARIÁVEIS AUXILIARES PARA TRANSIÇÕES T->M ====
z_tm = {}  # z[f,d] = 1 se houve transição T->M entre dia d e d+1
for f in funcionarios:
    for i in range(len(dias_ano) - 1):
        d = dias_ano[i]
        z_tm[f, d] = pulp.LpVariable(f"z_tm_{f}_{d.strftime('%Y%m%d')}", cat="Binary")

        # z_tm[f,d] >= x[f][d][2] + x[f][d+1][1] - 1  --> só será 1 se ambos forem 1
        model += (
            z_tm[f, d] >= x[f][d][2] + x[f][d + timedelta(days=1)][1] - 1,
            f"def_z_tm_{f}_{d}"
        )

# ==== FUNÇÃO OBJETIVO ====
penalizacao_domingo = pulp.lpSum(
    x[f][d][1] + x[f][d][2]
    for f in funcionarios
    for d in domingos_feriados
    if d in x[f]
)

penalizacao_transicao_TM = pulp.lpSum(
    z_tm[f, d] for (f, d) in z_tm
)

model += 10 * penalizacao_domingo + 50 * penalizacao_transicao_TM, "Funcao_objetivo"

# ==== RESTRIÇÕES ====

# 1. Um turno por dia por funcionário
for f in funcionarios:
    for d in dias_ano:
        model += (
            pulp.lpSum(x[f][d][t] for t in turnos) == 1,
            f"um_turno_por_dia_{f}_{d}"
        )

# 2. Exatamente 223 dias de trabalho por funcionário
for f in funcionarios:
    model += (
        pulp.lpSum(x[f][d][1] + x[f][d][2] for d in dias_ano) == 223,
        f"total_dias_trabalho_{f}"
    )

# 3. Máximo de 22 domingos/feriados por funcionário
for f in funcionarios:
    model += (
        pulp.lpSum(x[f][d][1] + x[f][d][2] for d in domingos_feriados if d in x[f]) <= 22,
        f"limite_domingo_feriado_{f}"
    )

# 4. No máximo 5 dias consecutivos de trabalho
for f in funcionarios:
    for i in range(len(dias_ano) - 5):
        dias_seq = dias_ano[i:i + 6]
        model += (
            pulp.lpSum(x[f][d][1] + x[f][d][2] for d in dias_seq) <= 5,
            f"limite_5_dias_seguidos_{f}_{dias_ano[i]}"
        )

# 5. Transição Tarde -> Manhã é proibida
for f in funcionarios:
    for i in range(len(dias_ano) - 1):
        d = dias_ano[i]
        d_next = dias_ano[i + 1]
        model += (
            x[f][d][2] + x[f][d_next][1] <= 1,
            f"proibe_TM_{f}_{d}"
        )

# ==== RESOLUÇÃO ====
solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=14400)
status = model.solve(solver)

# ==== EXPORTAÇÃO EM FORMATO LARGO ====
escala = {
    f: {
        d.strftime("%Y-%m-%d"): {0: "F", 1: "M", 2: "T"}[
            max((t for t in turnos if pulp.value(x[f][d][t]) == 1), default=0)
        ]
        for d in dias_ano
    }
    for f in funcionarios
}

df = pd.DataFrame.from_dict(escala, orient="index")
df.index.name = "funcionario"
df.reset_index(inplace=True)

df.to_csv("calendario4.csv", index=False)
print("Escala exportada para calendario4.csv")

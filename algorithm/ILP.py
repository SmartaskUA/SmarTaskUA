import pulp
import pandas as pd
from datetime import date, timedelta
import holidays
import random
from tabulate import tabulate

# ==== PARÂMETROS BÁSICOS ====
ano = 2025
num_funcionarios = 12
dias_ano = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31').to_list()
funcionarios = list(range(num_funcionarios))
turnos = [0, 1, 2]  # 0 = folga, 1 = manhã, 2 = tarde

# ==== FERIADOS NACIONAIS + DOMINGOS ====
feriados = holidays.country_holidays("PT", years=[ano])
domingos_feriados = [d for d in dias_ano if d.weekday() == 6 or d in feriados]

# ==== FÉRIAS ====
ferias = {
    f: set(random.sample(dias_ano, 30))
    for f in funcionarios
}

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

# ==== OBJETIVO ====
z_tm = {}
for f in funcionarios:
    for i in range(len(dias_ano) - 1):
        d = dias_ano[i]
        z_tm[f, d] = pulp.LpVariable(f"z_tm_{f}_{d.strftime('%Y%m%d')}", cat="Binary")
        model += (
            z_tm[f, d] >= x[f][d][2] + x[f][d + timedelta(days=1)][1] - 1,
            f"def_z_tm_{f}_{d}"
        )

penalizacao_domingo = pulp.lpSum(
    x[f][d][1] + x[f][d][2]
    for f in funcionarios
    for d in domingos_feriados
    if d in x[f]
)

penalizacao_transicao_TM = pulp.lpSum(
    z_tm[f, d] for (f, d) in z_tm
)

# Cobertura adicional por turno (opcional e suave)
bonus_manha = pulp.lpSum(
    pulp.lpSum(x[f][d][1] for f in funcionarios) for d in dias_ano
)

bonus_tarde = pulp.lpSum(
    pulp.lpSum(x[f][d][2] for f in funcionarios) for d in dias_ano
)

# Nova função objetivo com pesos equilibrados
model += (
    5 * penalizacao_domingo +        # Penalizar suavemente domingos/feriados
    30 * penalizacao_transicao_TM -  # Penalizar transições T→M
    0.01 * bonus_manha -             # Leve incentivo a mais manhãs
    0.01 * bonus_tarde               # Leve incentivo a mais tardes
), "Funcao_objetivo"


# ==== RESTRIÇÕES ====

for f in funcionarios:
    for d in dias_ano:
        model += (pulp.lpSum(x[f][d][t] for t in turnos) == 1, f"um_turno_por_dia_{f}_{d}")

for f in funcionarios:
    model += (pulp.lpSum(x[f][d][1] + x[f][d][2] for d in dias_ano) == 223, f"total_dias_trabalho_{f}")

for f in funcionarios:
    model += (
        pulp.lpSum(x[f][d][1] + x[f][d][2] for d in domingos_feriados if d in x[f]) <= 22,
        f"limite_domingo_feriado_{f}"
    )

for f in funcionarios:
    for i in range(len(dias_ano) - 5):
        dias_seq = dias_ano[i:i + 6]
        model += (
            pulp.lpSum(x[f][d][1] + x[f][d][2] for d in dias_seq) <= 5,
            f"limite_5_dias_seguidos_{f}_{dias_ano[i]}"
        )


for f in funcionarios:
    for i in range(len(dias_ano) - 1):
        d = dias_ano[i]
        d_next = dias_ano[i + 1]
        model += (x[f][d][2] + x[f][d_next][1] <= 1, f"proibe_TM_{f}_{d}")

for f in funcionarios:
    for d in ferias[f]:
        model += (x[f][d][0] == 1, f"ferias_folga_{f}_{d}")

for d in dias_ano:
    model += (
        pulp.lpSum(x[f][d][1] + x[f][d][2] for f in funcionarios) >= 2,
        f"cobertura_minima_{d}"
    )
for d in dias_ano:
    # Pelo menos 2 turnos de manhã no dia
    model += (
        pulp.lpSum(x[f][d][1] for f in funcionarios) >= 2,
        f"minimo_manha_{d}"
    )
    # Pelo menos 2 turnos de tarde no dia
    model += (
        pulp.lpSum(x[f][d][2] for f in funcionarios) >= 2,
        f"minimo_tarde_{d}"
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

# ==== VERIFICAÇÕES DE RESTRIÇÕES ====

verificacoes = []

for f in funcionarios:
    escalaf = df[df["funcionario"] == f].drop(columns="funcionario").T
    escalaf.columns = ["turno"]
    escalaf["data"] = pd.to_datetime(escalaf.index)
    escalaf["trabalho"] = escalaf["turno"].isin(["M", "T"])
    escalaf["domingo_feriado"] = escalaf["data"].apply(lambda d: d in domingos_feriados)

    # 1. Domingos e feriados trabalhados
    dom_fer = escalaf.query("trabalho & domingo_feriado").shape[0]

    # 2. Total de dias trabalhados
    total_trabalho = escalaf["trabalho"].sum()

    # 3. Maior sequência de trabalho
    escalaf["grupo"] = (escalaf["trabalho"] != escalaf["trabalho"].shift()).cumsum()
    grupos = escalaf.groupby("grupo")["trabalho"].agg(["first", "size"])
    max_consec = grupos.query("first == True")["size"].max()

    # 4. Transições T->M
    turnos_seq = escalaf["turno"].tolist()
    transicoes_TM = sum(
        1 for i in range(len(turnos_seq) - 1)
        if turnos_seq[i] == "T" and turnos_seq[i + 1] == "M"
    )

    # 5. Férias como folga
    dias_ferias_folga = sum(
        1 for d in ferias[f]
        if df.at[f, d.strftime("%Y-%m-%d")] == "F"
    )

    verificacoes.append([
        f,
        dom_fer,
        total_trabalho,
        max_consec,
        transicoes_TM,
        dias_ferias_folga
    ])

# ==== TABELA NO TERMINAL ====
headers = [
    "Funcionário",
    "Dom/Feriado Trabalhados",
    "Dias Trabalhados",
    "Máx Seq. Trabalho",
    "Transições T->M",
    "Férias como Folga"
]

print("\nResumo das verificações de restrições por funcionário:\n")
print(tabulate(verificacoes, headers=headers, tablefmt="grid"))

# ==== VERIFICAÇÃO DE COBERTURA POR EQUIPE E TURNO (DETALHADO) ====

# Equipes
equipe_A = list(range(9))       # Funcionários 0 a 8
equipe_B = list(range(9, 12))   # Funcionários 9 a 11

falhas_cobertura_detalhadas = {
    "manha_A": [],
    "tarde_A": [],
    "manha_B": [],
    "tarde_B": []
}

for d in dias_ano:
    data_str = d.strftime("%Y-%m-%d")
    dia_data = df.set_index("funcionario")[data_str]

    turnos_A = dia_data.loc[equipe_A]
    turnos_B = dia_data.loc[equipe_B]

    manha_A = (turnos_A == "M").sum()
    tarde_A = (turnos_A == "T").sum()
    manha_B = (turnos_B == "M").sum()
    tarde_B = (turnos_B == "T").sum()

    if manha_A < 2:
        falhas_cobertura_detalhadas["manha_A"].append((data_str, manha_A))
    if tarde_A < 2:
        falhas_cobertura_detalhadas["tarde_A"].append((data_str, tarde_A))
    if manha_B < 1:
        falhas_cobertura_detalhadas["manha_B"].append((data_str, manha_B))
    if tarde_B < 1:
        falhas_cobertura_detalhadas["tarde_B"].append((data_str, tarde_B))

# ==== RESUMO DAS FALHAS POR CATEGORIA ====

print("\n🔍 Falhas específicas de cobertura mínima por equipe e turno:\n")

for categoria, falhas in falhas_cobertura_detalhadas.items():
    print(f"{categoria}: {len(falhas)} dias")
    for data, valor in falhas[:5]:  # Exibe apenas os 5 primeiros casos como exemplo
        print(f"  - {data}: apenas {valor} turno(s)")
    if len(falhas) > 5:
        print("  ...")
    print()



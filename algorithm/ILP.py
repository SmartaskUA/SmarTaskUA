import csv
import pulp
import pandas as pd
import holidays
import random
from tabulate import tabulate
import json


def solve():
    # ==== PARÂMETROS BÁSICOS ====
    ano = 2025
    num_funcionarios = 12
    dias_ano = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31').to_list()
    funcionarios = list(range(num_funcionarios))
    turnos = [0, 1, 2]  # 0 = folga, 1 = manhã, 2 = tarde

    equipe_A = set(range(9))
    equipe_B = set(range(9, 12))

    # ==== FERIADOS NACIONAIS + DOMINGOS ====
    feriados = holidays.country_holidays("PT", years=[ano])
    domingos_feriados = [d for d in dias_ano if d.weekday() == 6 or d in feriados]
    is_domingos_feriados = {d: (d in domingos_feriados) for d in dias_ano}

    # ==== FÉRIAS ====
    # ==== FÉRIAS (a partir do CSV sem cabeçalho, com dias 1 a 365) ====
    ferias_raw = pd.read_csv("horarioReferencia.csv", header=None)

    # Constrói a lista de datas do ano correspondente às colunas 1 a 365
    datas_do_ano = pd.date_range(start="2025-01-01", periods=365)

    # Cria o dicionário de férias a partir do DataFrame
    ferias = {
        f: {
            datas_do_ano[i]
            for i in range(365)
            if ferias_raw.iloc[f, i + 1] == 1  # +1 para ignorar coluna de funcionário
        }
        for f in range(len(ferias_raw))
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

    y = {
        d: {
            t: {
                e: pulp.LpVariable(f"y_{d.strftime('%Y%m%d')}_{t}_{e}", lowBound=0, cat="Integer")
                for e in ["A", "B"]
            } for t in [1, 2]  # turnos válidos
        } for d in dias_ano
    }

    # ==== MODELO ====
    model = pulp.LpProblem("Escala_Trabalho", pulp.LpMinimize)

    # ==== FUNÇÃO OBJETIVO ====
    penalizacoes = []

    for d in dias_ano:
        for t in [1, 2]:
            for e in ["A", "B"]:
                ideal = 3 if e == "A" else 2
                excesso = pulp.LpVariable(f"penal_{d.strftime('%Y%m%d')}_{t}_{e}", lowBound=0, cat="Continuous")
                model += excesso >= ideal - y[d][t][e], f"restr_penal_{d}_{t}_{e}"
                penalizacoes.append(excesso)

    model += pulp.lpSum(penalizacoes), "Minimizar_desvios_da_cobertura_ideal"

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

        model += (
            pulp.lpSum(x[f][d][1] for f in funcionarios) >= 2,
            f"minimo_manha_{d}"
        )
        model += (
            pulp.lpSum(x[f][d][2] for f in funcionarios) >= 2,
            f"minimo_tarde_{d}"
        )

    for d in dias_ano:
        for t in [1, 2]:
            model += (
                y[d][t]["A"] == pulp.lpSum(x[f][d][t] for f in equipe_A),
                f"def_y_{d}_{t}_A"
            )
            model += (
                y[d][t]["B"] == pulp.lpSum(x[f][d][t] for f in equipe_B),
                f"def_y_{d}_{t}_B"
            )

    # ==== RESOLUÇÃO ====
    solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=28800, gapRel=0.01)

    status = model.solve(solver)
    print(f"\nstatus : {status} ")

    # ==== EXPORTAÇÃO EM FORMATO LARGO ====

    def get_turno_com_equipa(f, d, turno_str):
        if turno_str == "F":
            if d in ferias[f]:
                return "F"
            else:
                return "0"

        if f in equipe_A:
            return f"{turno_str}_A"
        elif f in equipe_B:
            return f"{turno_str}_B"
        return turno_str

    escala = {
        f: {
            d.strftime("%Y-%m-%d"): get_turno_com_equipa(
                f,
                d,
                {0: "F", 1: "M", 2: "T"}[max((t for t in turnos if pulp.value(x[f][d][t]) == 1), default=0)]
            )
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
    # Equipes (use listas, não sets)
    equipe_A = list(range(9))       # Funcionários 0 a 8
    equipe_B = list(range(9, 12))   # Funcionários 9 a 11

    verificacoes = []

    for f in funcionarios:
        escalaf = df[df["funcionario"] == f].drop(columns="funcionario").T
        escalaf.columns = ["turno"]
        escalaf["data"] = pd.to_datetime(escalaf.index)

        escalaf["trabalho"] = escalaf["turno"].str.startswith("M") | escalaf["turno"].str.startswith("T")
        escalaf["domingo_feriado"] = escalaf["data"].isin(domingos_feriados)

        # 1. Domingos e feriados trabalhados
        dom_fer = escalaf.query("trabalho & domingo_feriado").shape[0]

        # 2. Total de dias trabalhados
        total_trabalho = escalaf["trabalho"].sum()

        # 3. Maior sequência de trabalho
        escalaf["grupo"] = (escalaf["trabalho"] != escalaf["trabalho"].shift()).cumsum()
        grupos = escalaf.groupby("grupo")["trabalho"].agg(["first", "size"])
        max_consec = grupos.query("first == True")["size"].max()

        # 4. Transições T->M (qualquer equipe)
        turnos_seq = escalaf["turno"].tolist()
        transicoes_TM = sum(
            1 for i in range(len(turnos_seq) - 1)
            if turnos_seq[i].startswith("T") and turnos_seq[i + 1].startswith("M")
        )



        verificacoes.append([
            f,
            dom_fer,
            total_trabalho,
            max_consec,
            transicoes_TM
        ])

    # ==== TABELA NO TERMINAL ====
    headers = [
        "Funcionário",
        "Dom/Feriado Trabalhados",
        "Dias Trabalhados",
        "Máx Seq. Trabalho",
        "Transições T->M"
    ]

    print("\nResumo das verificações de restrições por funcionário:\n")
    print(tabulate(verificacoes, headers=headers, tablefmt="grid"))

    # ==== VERIFICAÇÃO FINAL: DIAS SEM NENHUMA COBERTURA (0 turnos) ====

    dias_sem_cobertura_total = []

    for d in dias_ano:
        data_str = d.strftime("%Y-%m-%d")
        dia_data = df.set_index("funcionario")[data_str]

        total_manha = dia_data.str.startswith("M").sum()
        total_tarde = dia_data.str.startswith("T").sum()

        if total_manha + total_tarde == 0:
            dias_sem_cobertura_total.append(data_str)

    print("\n🚨 Dias sem nenhuma cobertura (0 turnos manhã e tarde):\n")
    if dias_sem_cobertura_total:
        for dia in dias_sem_cobertura_total:
            print(f"  - {dia}")
    else:
        print("✅ Nenhum dia sem cobertura total.")


    # ==== VERIFICAÇÃO DE COBERTURA POR EQUIPE E TURNO (DETALHADO) ====

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

        manha_A = turnos_A.str.startswith("M").sum()
        tarde_A = turnos_A.str.startswith("T").sum()
        manha_B = turnos_B.str.startswith("M").sum()
        tarde_B = turnos_B.str.startswith("T").sum()

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

    schedule = []
    with open('calendario4.csv', mode='r') as csvfile:
        reader = csv.reader(csvfile, dialect='excel')
        for row in reader:
            schedule.append(row)
            # print(row)
    return schedule


if __name__ == "__main__":
    print(solve())



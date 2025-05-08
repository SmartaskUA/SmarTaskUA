import csv
import pulp
import pandas as pd
from datetime import date, timedelta
import holidays
from tabulate import tabulate
import pandas as pd
import pulp
import holidays

def solve(vacations, minimuns):
    print(f"[ILP] Minimuns '{minimuns}' ")

    ano = 2025
    num_funcionarios = 12
    dias_ano = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31').to_list()
    funcionarios = list(range(num_funcionarios))
    turnos = [0, 1, 2]  # 0 = folga, 1 = manhã, 2 = tarde

    equipe_A = set(range(9))
    equipe_B = set(range(9, 12))

    # Feriados nacionais + domingos
    feriados = holidays.country_holidays("PT", years=[ano])
    domingos_feriados = [d for d in dias_ano if d.weekday() == 6 or d in feriados]

    # Férias do CSV
    datas_do_ano = pd.date_range(start="2025-01-01", periods=365)
    ferias = {
        f_idx: {
            datas_do_ano[i]
            for i, val in enumerate(vacations[f_idx][1:])
            if int(val) == 1
        }
        for f_idx in range(len(vacations))
    }

    # === Extrair minimos aqui ===
    if isinstance(minimuns, list):
        num_days = len(minimuns[0]) - 3
        columns = ['team', 'type', 'shift'] + [f'day_{i + 1}' for i in range(num_days)]
        minimuns = pd.DataFrame(minimuns, columns=columns)

    minimos_por_equipa_turno = {}
    equipa_atual = None
    for _, row in minimuns.iterrows():
        if pd.notna(row['team']) and row['team'] != '':
            equipa_atual = row['team']
        if row['type'] == 'Minimo':
            turno = row['shift']
            valores_minimos = [int(v) for v in row[3:]]
            minimos_por_equipa_turno[(equipa_atual, turno)] = valores_minimos

    # Criar o dicionário `minimos[(d, e, t)]` como esperado
    minimos = {}
    for i, d in enumerate(dias_ano):
        for e in ['A', 'B']:
            for t in [1, 2]:
                key = (e, 'M' if t == 1 else 'T')
                valores = minimos_por_equipa_turno.get(key, [0] * len(dias_ano))
                valor = valores[i] if i < len(valores) else 0
                minimos[(d, e, t)] = valor

    # Variáveis de decisão
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
            } for t in [1, 2]
        } for d in dias_ano
    }

    # Modelo
    model = pulp.LpProblem("Escala_Trabalho", pulp.LpMinimize)

    # Ligação entre x e y
    for d in dias_ano:
        for t in [1, 2]:
            model += (
                y[d][t]['A'] == pulp.lpSum(x[f][d][t] for f in equipe_A),
                f"count_A_{d}_{t}"
            )
            model += (
                y[d][t]['B'] == pulp.lpSum(x[f][d][t] for f in equipe_B),
                f"count_B_{d}_{t}"
            )

    # Penalizações por descumprimento dos mínimos
    coverage_factor = []

    for d in dias_ano:
        for t in [1, 2]:
            for e in ["A", "B"]:
                minimo = minimos[(d, e, t)]
                penal = pulp.LpVariable(f"penal_{d.strftime('%Y%m%d')}_{t}_{e}", lowBound=0, cat="Continuous")
                model += penal >= minimo - y[d][t][e], f"restr_penal_{d}_{t}_{e}"
                coverage_factor.append(penal)

    # Função objetivo
    model += pulp.lpSum(coverage_factor), "Minimizar_descumprimentos_minimos"

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
    solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=28800, gapRel=0.005)

    status = model.solve(solver)
    print(f"\nstatus : {status} ")

    # ==== EXPORTAÇÃO EM FORMATO LARGO ====

    # Converte datas para "Dia X"
    dias_str = {d: f"Dia {i + 1}" for i, d in enumerate(dias_ano)}

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

    # Cria a escala com chaves "Dia X"
    escala = {
        f: {
            dias_str[d]: get_turno_com_equipa(
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



    schedule = []
    with open('calendario4.csv', mode='r') as csvfile:
        reader = csv.reader(csvfile, dialect='excel')
        for row in reader:
            schedule.append(row)
            # print(row)
    return schedule


if __name__ == "__main__":
    print(solve())



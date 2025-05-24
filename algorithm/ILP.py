import csv
import pulp
import pandas as pd
from datetime import date, timedelta
import holidays
from tabulate import tabulate
import pandas as pd
import pulp
import holidays

def solve(vacations, minimuns, employees, maxTime, year=2025):
    #print(f"[ILP] Minimuns '{minimuns}' ")
    print(f"[ILP] MaxTime '{maxTime}' ")

    # year = 2025
    num_funcionarios = len(employees)
    dias_ano = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31').to_list()
    funcionarios = list(range(num_funcionarios))
    turnos = [0, 1, 2]  # 0 = folga, 1 = manhã, 2 = tarde

    # === Processar equipes dinamicamente ===
    equipas = {}
    funcionario_equipa = {}

    for idx, emp in enumerate(employees):
        teams = emp.get('teams', [])
        if not teams:
            print(f"[WARNING] Funcionário {emp.get('name')} (índice {idx}) sem equipa atribuída")
            continue

        first_team = teams[0]
        funcionario_equipa[idx] = first_team

        if first_team not in equipas:
            equipas[first_team] = set()
        equipas[first_team].add(idx)

    print(f"[ILP] Equipas identificadas: {list(equipas.keys())}")

    # Feriados nacionais + domingos
    feriados = holidays.country_holidays("PT", years=[year])
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

    # === Extrair mínimos ===
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

    minimos = {}
    for i, d in enumerate(dias_ano):
        for e in equipas.keys():
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
                for e in equipas.keys()
            } for t in [1, 2]
        } for d in dias_ano
    }

    # Modelo
    model = pulp.LpProblem("Escala_Trabalho", pulp.LpMinimize)

    # Ligação entre x e y
    for d in dias_ano:
        for t in [1, 2]:
            for e, members in equipas.items():
                model += (
                    y[d][t][e] == pulp.lpSum(x[f][d][t] for f in members),
                    f"count_{e}_{d}_{t}"
                )

    # Penalizações por descumprimento dos mínimos
    coverage_factor = []
    for d in dias_ano:
        for t in [1, 2]:
            for e in equipas.keys():
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

    # ==== RESOLUÇÃO ====
    solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=28800, gapRel=0.005)

    status = model.solve(solver)
    print(f"\nstatus : {status} ")

    # ==== EXPORTAÇÃO EM FORMATO LARGO ====

    dias_str = {d: f"Dia {i + 1}" for i, d in enumerate(dias_ano)}

    def get_turno_com_equipa(f, d, turno_str):
        if turno_str == "F":
            if d in ferias[f]:
                return "F"
            else:
                return "0"
        equipe = funcionario_equipa.get(f, '')
        equipe_suffix = equipe[-1] if equipe else ''
        return f"{turno_str}_{equipe_suffix}"

    escala = {
        f"Empregado{f + 1}": {
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



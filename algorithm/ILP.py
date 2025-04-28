import csv
import pulp
import pandas as pd
from datetime import date, timedelta
import holidays
from tabulate import tabulate

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

    # ==== FÉRIAS A PARTIR DO CSV DE REFERÊNCIA ====
    ferias_raw = pd.read_csv("horarioReferencia.csv", header=None)
    datas_do_ano = pd.date_range(start="2025-01-01", periods=365)
    ferias = {
        f: {
            datas_do_ano[i]
            for i in range(365)
            if ferias_raw.iloc[f, i + 1] == 1
        }
        for f in range(len(ferias_raw))
    }

    # ==== MINIMOS A PARTIR DO CSV minimuns.csv ====
    minimos_raw = pd.read_csv("minimuns.csv", header=None)

    dias_colunas = minimos_raw.iloc[0, 3:].tolist()
    dias_colunas = pd.date_range(start="2025-01-01", periods=len(dias_colunas))

    minimos = {}

    linhas_minimos = {
        ("A", 1): 1,  # Linha 2: Equipe A, Manhã
        ("A", 2): 3,  # Linha 4: Equipe A, Tarde
        ("B", 1): 5,  # Linha 6: Equipe B, Manhã
        ("B", 2): 7   # Linha 8: Equipe B, Tarde
    }

    for (equipe, turno), linha_idx in linhas_minimos.items():
        valores = minimos_raw.iloc[linha_idx, 3:].tolist()
        for dia, minimo in zip(dias_colunas, valores):
            minimos[(dia, equipe, turno)] = int(minimo)

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
            } for t in [1, 2]
        } for d in dias_ano
    }

    # ==== MODELO ====
    model = pulp.LpProblem("Escala_Trabalho", pulp.LpMinimize)

    # ==== FUNÇÃO OBJETIVO ====
    coverage_factor = []

    for d in dias_ano:
        for t in [1, 2]:
            for e in ["A", "B"]:
                minimo = minimos[(d, e, t)]
                penal = pulp.LpVariable(f"penal_{d.strftime('%Y%m%d')}_{t}_{e}", lowBound=0, cat="Continuous")
                model += penal >= minimo - y[d][t][e], f"restr_penal_{d}_{t}_{e}"
                coverage_factor.append(penal)

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

    # ==== LEITURA DOS MÍNIMOS DE COBERTURA A PARTIR DO CSV ====

    minimuns_raw = pd.read_csv("minimuns.csv", header=None)

    # Corrige meses de português para inglês
    meses_pt_en = {
        "jan": "Jan", "fev": "Feb", "mar": "Mar", "abr": "Apr",
        "mai": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
        "set": "Sep", "out": "Oct", "nov": "Nov", "dez": "Dec"
    }

    dias_min = minimuns_raw.iloc[0, 3:].tolist()
    dias_min_corrigidos = []
    for d in dias_min:
        if isinstance(d, str):
            dia, mes_pt = d.strip().split(" ")
            mes_en = meses_pt_en.get(mes_pt.lower())
            dias_min_corrigidos.append(f"2025-{mes_en}-{dia.zfill(2)}")

    dias_min = pd.to_datetime(dias_min_corrigidos, format="%Y-%b-%d")

    # Construir o dicionário de mínimos
    minimos_por_dia_turno_equipe = {}

    for idx, linha in minimuns_raw.iterrows():
        if isinstance(linha[0], str) and linha[0].strip().startswith("quipa"):
            equipe = "A" if "A" in linha[0] else "B"
        if isinstance(linha[1], str) and linha[1].strip() == "Minimo":
            turno = 1 if linha[2].strip() == "M" else 2
            for i, dia in enumerate(dias_min):
                key = (dia, turno, equipe)
                valor = linha[i + 3]
                if not pd.isna(valor):
                    minimos_por_dia_turno_equipe[key] = int(valor)
    # ==== VERIFICAÇÃO FINAL USANDO OS MÍNIMOS DO CSV ====

    print("\n🔍 Verificando cobertura real contra os mínimos do CSV:\n")

    falhas_minimos = []

    for (dia, turno, equipe), minimo in minimos_por_dia_turno_equipe.items():
        data_str = dia.strftime("%Y-%m-%d")
        if data_str not in df.columns:
            continue

        dia_data = df.set_index("funcionario")[data_str]

        if equipe == "A":
            turnos = dia_data.loc[equipe_A]
        else:
            turnos = dia_data.loc[equipe_B]

        if turno == 1:
            qtd_turnos = turnos.str.startswith("M").sum()
        else:
            qtd_turnos = turnos.str.startswith("T").sum()

        if qtd_turnos < minimo:
            falhas_minimos.append((data_str, turno, equipe, qtd_turnos, minimo))

    print(f"Total de falhas: {len(falhas_minimos)} dias\n")
    for data_str, turno, equipe, real, minimo in falhas_minimos[:10]:  # mostra apenas 10 primeiros
        turno_nome = "Manhã" if turno == 1 else "Tarde"
        print(f"  - {data_str} [{turno_nome} Equipe {equipe}]: {real} (mínimo exigido {minimo})")
    if len(falhas_minimos) > 10:
        print("  ...")

    schedule = []
    with open('calendario4.csv', mode='r') as csvfile:
        reader = csv.reader(csvfile, dialect='excel')
        for row in reader:
            schedule.append(row)
            # print(row)
    return schedule


if __name__ == "__main__":
    print(solve())



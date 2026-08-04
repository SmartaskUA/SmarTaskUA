"""
csv_to_schedule_json_v2.py

Converte o CSV de escalas (schedule_input real: uma linha por colaborador,
uma coluna por dia, celulas "HH:MM-HH:MM@Team | ...") para a estrutura JSON
de importacao do schedule generator (OutRosterTeamDays + OutScheduleUseds).

v2: corrigido apos analise de problem.json / demand.csv / schedule_input.csv:
  - o que antes assumiamos como "TaskID por categoria" e na verdade o TeamCode
    real do sistema (Storage / Checkout / Management), confirmado em
    problem.json -> demand.organizationalUnits.teams
  - os tokens especiais (DO/FDO/VAC/NOT/Med) tem semantica confirmada em
    problem.json -> scheduleInput.markingTypes
  - o ScheduleWeight (minutos trabalhados) foi validado contra as horas
    contratuais/alvo em schedule_input.csv

>>> Continuam por confirmar (ver CONFIG): codigos numericos reais de
    TeamCode/ScheduleCode se o vosso sistema já os tiver definidos. <<<
"""

import csv
import json
from datetime import datetime

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------

ROSTER_CSV_PATH = "/mnt/user-data/uploads/6a6084e19b6c851c5aba96df.csv"
PROBLEM_JSON_PATH = "/mnt/user-data/uploads/problem.json"
OUTPUT_PATH = "/mnt/user-data/outputs/schedule_import_v2.json"

# RosterCode: nao ha codigo explicito no problema -> usamos o problemId como
# referencia legivel. Troca por um codigo numerico real se existir no vosso sistema.
ROSTER_CODE = "SISQUAL_OCTOBER_2025"

# TeamCode: o CSV usa o nome da equipa (Storage/Checkout/Management) tal como
# definido em problem.json. Se o vosso sistema exigir codigo numerico em vez
# do nome, preenche este mapeamento (deixamos o nome como fallback).
TEAM_NAME_TO_CODE = {
    "Storage": "Storage",
    "Checkout": "Checkout",
    "Management": "Management",
}

# Tokens especiais (dias sem horario normal) -> (ScheduleCode, DayType)
# Semantica confirmada em problem.json -> scheduleInput.markingTypes
SPECIAL_TOKENS = {
    "DO":  {"schedule_code": 2, "day_type": 1, "label": "Day Off (pode ser trocado com penalizacao)"},
    "FDO": {"schedule_code": 5, "day_type": 4, "label": "Forced Day Off (nao pode ser trocado)"},
    "VAC": {"schedule_code": 4, "day_type": 3, "label": "Ferias / Vacation (nao pode trabalhar)"},
    "NOT": {"schedule_code": 6, "day_type": 5, "label": "Indisponivel / Unavailable"},
    "Med": {"schedule_code": 7, "day_type": 6, "label": "Baixa medica / Medical Reason"},
}

WORK_DAY_TYPE = 0  # DayType dos dias efetivamente trabalhados

# Data de referencia fixa para os horarios em OutScheduleUseds (ver nota no
# script anterior: as datas nesse bloco sao apenas um "molde" horario,
# independente do dia real em que o horario e usado).
SCHEDULE_TEMPLATE_DATE = "2026-01-01"

# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------

def parse_segment(seg):
    """'14:00-22:00@Management' -> (time(14,00), time(22,00), 'Management')"""
    seg = seg.strip()
    time_part, team = seg.split("@")
    start_str, end_str = time_part.split("-")
    start = datetime.strptime(start_str.strip(), "%H:%M").time()
    end = datetime.strptime(end_str.strip(), "%H:%M").time()
    return start, end, team.strip()


def group_by_team_into_periods(segments):
    """
    Agrupa segmentos do dia por equipa (TeamCode), e dentro de cada equipa
    junta segmentos consecutivos e contiguos num mesmo periodo. Se a mesma
    equipa reaparecer mais tarde no dia com um intervalo, cria um 2o periodo
    (equivalente a StartDate2/EndDate2). Devolve dict: team -> lista de periodos.
    """
    segs_sorted = sorted(segments, key=lambda s: s[0])
    by_team = {}
    for seg in segs_sorted:
        start, end, team = seg
        periods = by_team.setdefault(team, [])
        if periods and periods[-1][-1][1] == start:
            periods[-1].append(seg)
        else:
            periods.append([seg])
    return by_team


def build_schedule_code(team, periods):
    signature = team + "_" + "_".join(
        f"{p[0][0].strftime('%H%M')}-{p[-1][1].strftime('%H%M')}" for p in periods
    )
    return 9000 + (abs(hash(signature)) % 900)


def minutes_between(t1, t2):
    d1 = datetime.combine(datetime.min, t1)
    d2 = datetime.combine(datetime.min, t2)
    return int((d2 - d1).total_seconds() // 60)


# ----------------------------------------------------------------------
# Conversao principal
# ----------------------------------------------------------------------

def convert(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        dates = header[1:]
        rows = list(reader)

    roster_team_days = []
    schedule_used_map = {}

    for row in rows:
        employee_code = row[0].strip()
        for date_str, cell in zip(dates, row[1:]):
            cell = cell.strip()
            if not cell:
                continue

            if cell in SPECIAL_TOKENS:
                info = SPECIAL_TOKENS[cell]
                schedule_code = info["schedule_code"]
                roster_team_days.append({
                    "RosterCode": ROSTER_CODE,
                    "TeamCode": None,  # sem equipa associada num dia de ausencia
                    "EmployeeCode": employee_code,
                    "Date": date_str,
                    "ScheduleCode": schedule_code,
                    "OutRosterTeamDayTasks": [],
                    "OutRosterTeamDayResponsibilities": [],
                })
                if schedule_code not in schedule_used_map:
                    schedule_used_map[schedule_code] = {
                        "ScheduleCode": schedule_code,
                        "DayType": info["day_type"],
                        "ScheduleWeight": 0,
                    }
                continue

            # dia trabalhado: pode ter varios blocos de equipas diferentes
            segments = [parse_segment(s) for s in cell.split("|")]
            by_team = group_by_team_into_periods(segments)

            for team, periods in by_team.items():
                team_code = TEAM_NAME_TO_CODE.get(team, team)
                schedule_code = build_schedule_code(team, periods)

                roster_team_days.append({
                    "RosterCode": ROSTER_CODE,
                    "TeamCode": team_code,
                    "EmployeeCode": employee_code,
                    "Date": date_str,
                    "ScheduleCode": schedule_code,
                    "OutRosterTeamDayTasks": [],  # sem conceito de "tarefa" distinto de equipa nestes dados
                    "OutRosterTeamDayResponsibilities": [],
                })

                if schedule_code not in schedule_used_map:
                    total_minutes = sum(
                        minutes_between(s, e) for period in periods for (s, e, _t) in period
                    )
                    sched = {
                        "ScheduleCode": schedule_code,
                        "DayType": WORK_DAY_TYPE,
                        "ScheduleWeight": total_minutes,
                    }
                    for i, period in enumerate(periods[:2], start=1):
                        p_start = period[0][0]
                        p_end = period[-1][1]
                        sched[f"StartDate{i}"] = f"{SCHEDULE_TEMPLATE_DATE}T{p_start.strftime('%H:%M:%S')}"
                        sched[f"EndDate{i}"] = f"{SCHEDULE_TEMPLATE_DATE}T{p_end.strftime('%H:%M:%S')}"
                    schedule_used_map[schedule_code] = sched

    result = {
        "OutRosterTeamDays": roster_team_days,
        "OutScheduleUseds": list(schedule_used_map.values()),
    }
    return result


def validate_against_problem(data, problem_path, roster_csv_path):
    """Cross-check: soma de minutos trabalhados por colaborador/dia deve bater
    certo com as horas-alvo em schedule_input.csv / contractType em problem.json."""
    with open(problem_path, encoding="utf-8") as f:
        problem = json.load(f)
    contract_hours = {
        c["id"]: c["workHoursPerDay"] for c in problem["contracts"]["definitions"]
    }
    emp_contract = {
        e["id"]: e["contractType"] for e in problem["employees"]["competency"]
    }

    by_emp_date_minutes = {}
    for entry in data["OutRosterTeamDays"]:
        sc = entry["ScheduleCode"]
        weight = next(s["ScheduleWeight"] for s in data["OutScheduleUseds"] if s["ScheduleCode"] == sc)
        key = (entry["EmployeeCode"], entry["Date"])
        by_emp_date_minutes[key] = by_emp_date_minutes.get(key, 0) + weight

    mismatches = 0
    checked = 0
    for (emp, date), minutes in by_emp_date_minutes.items():
        if minutes == 0:
            continue
        expected_h = contract_hours.get(emp_contract.get(emp))
        if expected_h is None:
            continue
        checked += 1
        if minutes != expected_h * 60:
            mismatches += 1
    print(f"Validacao: {checked} dias trabalhados verificados, {mismatches} incoerencias com horas contratuais.")


if __name__ == "__main__":
    data = convert(ROSTER_CSV_PATH)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"OK: {len(data['OutRosterTeamDays'])} registos (dia x equipa), "
          f"{len(data['OutScheduleUseds'])} horarios distintos.")
    validate_against_problem(data, PROBLEM_JSON_PATH, ROSTER_CSV_PATH)
    print(f"Ficheiro gerado em: {OUTPUT_PATH}")

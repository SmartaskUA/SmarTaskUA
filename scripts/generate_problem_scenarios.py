#!/usr/bin/env python3

import csv
import datetime
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VACATION_DIR = REPO_ROOT / "api/src/main/resources/vacationData"
MINIMUNS_DIR = REPO_ROOT / "api/src/main/resources/minimuns"
OUT_DIR = REPO_ROOT / "data/problems"

# (numTeams, numEmployees) — 2-shift scaling axis
SCENARIOS = [(2, 12), (4, 24), (8, 48), (16, 96)]
NUM_CASES = 1
CROSS_RATIO = 0.20
YEAR = 2025

MONTH_ABBR_PT = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
SHIFT_ORDER = {"M": 0, "T": 1, "N": 2}


def team_letter(idx):
    return chr(ord("A") + idx)


def build_employee_teams(num_teams, num_employees, cross_ratio=CROSS_RATIO):
    """Replicate ScenarioSeeder.createScenarioWithCrossing primary + cross logic."""
    primary = [[] for _ in range(num_teams)]
    for i in range(num_employees):
        primary[i % num_teams].append(i)

    emp_teams = [set() for _ in range(num_employees)]
    for t, members in enumerate(primary):
        for emp_idx in members:
            emp_teams[emp_idx].add(team_letter(t))

    # Each team borrows from the NEXT team (wrap). round() matches Java's Math.round.
    for t in range(num_teams):
        donors = primary[(t + 1) % num_teams]
        to_share = max(1, round(len(primary[t]) * cross_ratio))
        for emp_idx in donors[:min(to_share, len(donors))]:
            emp_teams[emp_idx].add(team_letter(t))

    return emp_teams


def build_problem_json(num_teams, num_employees, case_num, emp_teams):
    teams_list = [team_letter(t) for t in range(num_teams)]
    employees = [
        {
            "id": f"Employee {i + 1}",
            "name": f"Employee {i + 1}",
            "teams": sorted(emp_teams[i]),
            "contractType": "fullTime_8h",
        }
        for i in range(num_employees)
    ]

    problem_id = f"SMARTASK_{num_teams}TEAMS_{num_employees}EMP"
    return {
        "schemaVersion": "2.2",
        "problemType": "employee_scheduling",
        "metadata": {
            "problemId": problem_id,
            "createdAt": "2026-05-25T00:00:00Z",
            "description": (
                f"{num_teams}-team / {num_employees}-employee scheduling scenario "
                f"(2 shifts: M/T), vacation Case {case_num}. Round-robin primary "
                f"assignment with 20% cross-membership from the next team (wrap). "
                f"Generated from ScenarioSeeder.createScenarioWithCrossing."
            ),
            "source": "scripts/generate_problem_scenarios.py",
        },
        "features": {
            "useShiftBasedScheduling": True,
            "useAdvancedConstraints": False,
            "usePriorityHierarchy": False,
        },
        "temporalScope": {
            "year": YEAR,
            "numDays": 365,
            "targetPeriod": {
                "start": f"{YEAR}-01-01",
                "end": f"{YEAR}-12-31",
                "includeBufferWeeks": False,
            },
        },
        "contracts": {
            "definitions": [
                {"id": "fullTime_8h", "name": "Full-time 8h", "workHoursPerDay": 8}
            ]
        },
        "employees": {"model": "team", "simple": employees},
        "demand": {
            "shiftModel": "fixed",
            "dataFile": "demand.csv",
            "organizationalUnits": {"teams": teams_list},
            "shifts": [
                {"code": "M", "name": "Morning", "order": 1,
                 "timeRange": {"start": "08:00", "end": "16:00"}},
                {"code": "T", "name": "Afternoon", "order": 2,
                 "timeRange": {"start": "14:00", "end": "22:00"}},
            ],
        },
        "constraints": {
            "hard": [
                {"id": "max-consecutive-days", "type": "max_consecutive_days",
                 "params": {"window": 6, "max_worked": 5}, "enabled": True},
                {"id": "total-workdays", "type": "total_workdays",
                 "params": {"min": 223, "max": 223}, "enabled": True},
                {"id": "max-special-days", "type": "max_special_days",
                 "params": {"cap": 22}, "enabled": True},
                {"id": "no-backward-shift-transitions",
                 "type": "no_earlier_shift_next_day", "params": {}, "enabled": True},
                {"id": "vacation-days", "type": "vacation_block",
                 "params": {}, "enabled": True},
            ],
            "soft": [
                {"id": "min-coverage", "type": "min_coverage",
                 "params": {"penalty_per_missing": 100}, "weight": 100, "enabled": True},
                {"id": "ideal-coverage", "type": "ideal_coverage",
                 "params": {"penalty_per_missing": 1}, "weight": 1, "enabled": True},
            ],
        },
        "vacations": {"dataFile": "vacations.csv"},
    }


def parse_pt_header(header_cell, year):
    """'1 jan' -> datetime.date(year, 1, 1)."""
    day_str, month_str = header_cell.strip().split(" ", 1)
    return datetime.date(year, MONTH_ABBR_PT[month_str.lower()], int(day_str))


def convert_minimums_to_demand(minimums_path, out_path, year=YEAR):
    """Wide (Equipa,Tipo,Turno + 365 date cols) -> long (date,shift,team,minimum,ideal)."""
    with open(minimums_path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        dates = [parse_pt_header(c, year) for c in header[3:]]

        per_key = {}  # (team, shift, tipo) -> [int per day]
        for row in reader:
            if not row or not row[0].strip():
                continue
            team = row[0].strip().replace("Equipa ", "")
            tipo, shift = row[1].strip(), row[2].strip()
            per_key[(team, shift, tipo)] = [int(v) for v in row[3:]]

    team_shift_pairs = sorted({(t, s) for (t, s, _) in per_key},
                              key=lambda p: (p[0], SHIFT_ORDER.get(p[1], 99)))

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "shift", "team", "minimum", "ideal"])
        for day_idx, date in enumerate(dates):
            for team, shift in team_shift_pairs:
                mins = per_key.get((team, shift, "Minimo"))
                ideals = per_key.get((team, shift, "Ideal"))
                if mins is None:
                    continue
                m_val = mins[day_idx]
                i_val = ideals[day_idx] if ideals is not None else m_val
                writer.writerow([date.isoformat(), shift, team, m_val, i_val])


def generate_all():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for num_teams, num_employees in SCENARIOS:
        emp_teams = build_employee_teams(num_teams, num_employees)
        minimums_path = MINIMUNS_DIR / f"minimuns_{num_teams}teams_{num_employees}emp.csv"
        if not minimums_path.exists():
            print(f"[skip] missing minimums: {minimums_path}")
            continue
        vac_template_dir = VACATION_DIR / f"{num_employees}_employees/templates"

        for case_num in range(1, NUM_CASES + 1):
            vac_path = vac_template_dir / f"VacationTemplate_Case{case_num}_{num_employees}.csv"
            if not vac_path.exists():
                print(f"[skip] missing vacation template: {vac_path}")
                continue

            scenario_dir = OUT_DIR / f"SMARTASK_{num_teams}TEAMS_{num_employees}EMP"
            scenario_dir.mkdir(parents=True, exist_ok=True)

            problem = build_problem_json(num_teams, num_employees, case_num, emp_teams)
            with open(scenario_dir / "problem.json", "w") as f:
                json.dump(problem, f, indent=2)

            shutil.copy(vac_path, scenario_dir / "vacations.csv")
            convert_minimums_to_demand(minimums_path, scenario_dir / "demand.csv")

            written.append(scenario_dir.name)
            print(f"[ok] {scenario_dir.name}")

    print(f"\nGenerated {len(written)} scenario folder(s) under {OUT_DIR}")


if __name__ == "__main__":
    generate_all()

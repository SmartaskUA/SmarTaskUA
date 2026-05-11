"""
create_3shift_scenarios.py — Generate 3-shift scenario folders.

Creates SMARTASK_3SHIFTS_{N}TEAMS_2025 for N in [4, 8, 16, 32]:
  - demand.csv    (via convert_minimuns.py)
  - vacations.csv (copied from vacationData_3shifts/Case 1)
  - problem.json  (3-shift version of the existing 2-shift structure)

Run from data/problems/:
    python create_3shift_scenarios.py
"""

import os
import json
import shutil
import subprocess
import sys

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
MINS_DIR     = os.path.join(BASE_DIR, "..", "..", "src", "scheduler", "algorithms",
                             "generators", "data", "minimunsData")
VAC_DIR      = os.path.join(BASE_DIR, "..", "..", "src", "scheduler", "algorithms",
                             "generators", "data", "vacationData_3shifts")
CONVERT_SCRIPT = os.path.join(BASE_DIR, "convert_minimuns.py")

TEAMS_2  = ["A", "B"]
TEAMS_4  = ["A", "B", "C", "D"]
TEAMS_8  = ["A", "B", "C", "D", "E", "F", "G", "H"]
TEAMS_16 = ["A", "B", "C", "D", "E", "F", "G", "H",
            "I", "J", "K", "L", "M", "N", "O", "P"]
TEAMS_32 = ["A", "B", "C", "D", "E", "F", "G", "H",
            "I", "J", "K", "L", "M", "N", "O", "P",
            "Q", "R", "S", "T", "U", "V", "W", "X",
            "Y", "Z", "AA", "AB", "AC", "AD", "AE", "AF"]

SCENARIOS = [
    {
        "id":       "SMARTASK_3SHIFTS_2TEAMS_2025",
        "teams":    TEAMS_2,
        "n_emp":    24,
        "mins_file": "minimuns_3shifts_2teams_24emp.csv",
        "vac_file":  "VacationTemplate_Case1_24.csv",
        "vac_emp":   "24_employees",
        "desc":     ("2-team 3-shift scheduling problem. 24 unique employees: "
                     "11 primary per team (round-robin), 2 dual-team members "
                     "(1 per adjacent team pair A-B, B-A)."),
    },
    {
        "id":       "SMARTASK_3SHIFTS_4TEAMS_2025",
        "teams":    TEAMS_4,
        "n_emp":    48,
        "mins_file": "minimuns_3shifts_4teams_48emp.csv",
        "vac_file":  "VacationTemplate_Case1_48.csv",
        "vac_emp":   "48_employees",
        "desc":     ("4-team 3-shift scheduling problem. 48 unique employees: "
                     "11 primary per team (round-robin), 4 dual-team members "
                     "(1 per adjacent team pair A-B, B-C, C-D, D-A)."),
    },
    {
        "id":       "SMARTASK_3SHIFTS_8TEAMS_2025",
        "teams":    TEAMS_8,
        "n_emp":    96,
        "mins_file": "minimuns_3shifts_8teams_96emp.csv",
        "vac_file":  "VacationTemplate_Case1_96.csv",
        "vac_emp":   "96_employees",
        "desc":     ("8-team 3-shift scheduling problem. 96 unique employees: "
                     "11 primary per team (round-robin), 8 dual-team members "
                     "(1 per adjacent team pair A-B, ..., H-A)."),
    },
    {
        "id":       "SMARTASK_3SHIFTS_16TEAMS_2025",
        "teams":    TEAMS_16,
        "n_emp":    192,
        "mins_file": "minimuns_3shifts_16teams_192emp.csv",
        "vac_file":  "VacationTemplate_Case1_192.csv",
        "vac_emp":   "192_employees",
        "desc":     ("16-team 3-shift scheduling problem. 192 unique employees: "
                     "11 primary per team (round-robin), 16 dual-team members "
                     "(1 per adjacent team pair A-B, ..., P-A)."),
    },
    {
        "id":       "SMARTASK_3SHIFTS_32TEAMS_2025",
        "teams":    TEAMS_32,
        "n_emp":    384,
        "mins_file": "minimuns_3shifts_32teams_384emp.csv",
        "vac_file":  "VacationTemplate_Case1_384.csv",
        "vac_emp":   "384_employees",
        "desc":     ("32-team 3-shift scheduling problem. 384 unique employees: "
                     "11 primary per team (round-robin), 32 dual-team members "
                     "(1 per adjacent team pair A-B, ..., AF-A)."),
    },
]


def build_employees(teams, n_emp):
    """
    Mirrors ScenarioSeeder.java createScenarioWithCrossing exactly:

    1. Round-robin primary: employee with 0-based index i → primary team i % n_teams
    2. Cross-memberships: each team t borrows the first `to_share` employees from
       team (t+1) % n_teams, where to_share = max(1, round(per_team * 0.20)).
       The borrowed employee also appears in team t (the borrowing team).
    """
    n_teams  = len(teams)
    per_team = n_emp // n_teams
    assert n_emp % n_teams == 0, f"n_emp={n_emp} not divisible by n_teams={n_teams}"
    to_share = max(1, round(per_team * 0.20))

    employees = []
    for idx in range(n_emp):
        primary_t = idx % n_teams         # primary team index (round-robin)
        position  = idx // n_teams        # position within that team (0-based)

        primary_team = teams[primary_t]

        if position < to_share:
            # this employee is borrowed by team (primary_t - 1) % n_teams
            borrowing_t = (primary_t - 1) % n_teams
            emp_teams = [primary_team, teams[borrowing_t]]
        else:
            emp_teams = [primary_team]

        employees.append({
            "id":           f"Employee {idx + 1}",
            "name":         f"Employee {idx + 1}",
            "teams":        emp_teams,
            "contractType": "fullTime_8h",
        })

    return employees


def build_problem_json(sc):
    return {
        "schemaVersion": "2.2",
        "problemType":   "employee_scheduling",

        "metadata": {
            "problemId":   sc["id"],
            "createdAt":   "2026-05-09T00:00:00Z",
            "description": sc["desc"],
            "source":      f"Derived from ScenarioSeeder.java createScenarioWithCrossing("
                           f"{len(sc['teams'])}, {sc['n_emp']}, 0.20) — 3-shift variant",
        },

        "features": {
            "useShiftBasedScheduling": True,
            "useAdvancedConstraints":  False,
            "usePriorityHierarchy":    False,
        },

        "temporalScope": {
            "year":    2025,
            "numDays": 365,
            "targetPeriod": {
                "start":               "2025-01-01",
                "end":                 "2025-12-31",
                "includeBufferWeeks":  False,
            },
        },

        "contracts": {
            "definitions": [
                {
                    "id":              "fullTime_8h",
                    "name":            "Full-time 8h",
                    "workHoursPerDay": 8,
                }
            ]
        },

        "employees": {
            "model":  "team",
            "simple": build_employees(sc["teams"], sc["n_emp"]),
        },

        "demand": {
            "shiftModel": "fixed",
            "dataFile":   "demand.csv",
            "organizationalUnits": {
                "teams": sc["teams"],
            },
            "shifts": [
                {
                    "code":  "M",
                    "name":  "Morning",
                    "order": 1,
                    "timeRange": {"start": "08:00", "end": "16:00"},
                },
                {
                    "code":  "T",
                    "name":  "Afternoon",
                    "order": 2,
                    "timeRange": {"start": "14:00", "end": "22:00"},
                },
                {
                    "code":  "N",
                    "name":  "Night",
                    "order": 3,
                    "timeRange": {"start": "22:00", "end": "06:00"},
                },
            ],
        },

        "constraints": {
            "hard": [
                {
                    "id":      "max-consecutive-days",
                    "type":    "max_consecutive_days",
                    "params":  {"window": 6, "max_worked": 5},
                    "enabled": True,
                },
                {
                    "id":      "total-workdays",
                    "type":    "total_workdays",
                    "params":  {"min": 223, "max": 223},
                    "enabled": True,
                },
                {
                    "id":      "max-special-days",
                    "type":    "max_special_days",
                    "params":  {"cap": 22},
                    "enabled": True,
                },
                {
                    "id":      "no-backward-shift-transitions",
                    "type":    "no_earlier_shift_next_day",
                    "params":  {},
                    "enabled": True,
                },
                {
                    "id":      "vacation-days",
                    "type":    "vacation_block",
                    "params":  {},
                    "enabled": True,
                },
            ],
            "soft": [
                {
                    "id":      "min-coverage",
                    "type":    "min_coverage",
                    "params":  {"penalty_per_missing": 100},
                    "weight":  100,
                    "enabled": True,
                },
                {
                    "id":      "ideal-coverage",
                    "type":    "ideal_coverage",
                    "params":  {"penalty_per_missing": 1},
                    "weight":  1,
                    "enabled": True,
                },
            ],
        },

        "vacations": {
            "dataFile": "vacations.csv",
        },
    }


def main():
    for sc in SCENARIOS:
        out_dir = os.path.join(BASE_DIR, sc["id"])
        os.makedirs(out_dir, exist_ok=True)
        print(f"\n{'='*55}")
        print(f"  {sc['id']}")
        print(f"{'='*55}")

        # 1 — demand.csv via convert_minimuns.py
        mins_src = os.path.join(MINS_DIR, sc["mins_file"])
        demand_dst = os.path.join(out_dir, "demand.csv")
        print(f"  Converting {sc['mins_file']} → demand.csv ...", flush=True)
        result = subprocess.run(
            [sys.executable, CONVERT_SCRIPT, mins_src, demand_dst],
            capture_output=True, text=True, cwd=BASE_DIR,
        )
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr}")
            sys.exit(1)
        print(f"  demand.csv written ({os.path.getsize(demand_dst):,} bytes)")

        # 2 — vacations.csv
        vac_src = os.path.join(VAC_DIR, sc["vac_emp"], "templates", sc["vac_file"])
        vac_dst = os.path.join(out_dir, "vacations.csv")
        shutil.copy2(vac_src, vac_dst)
        print(f"  vacations.csv copied ({os.path.getsize(vac_dst):,} bytes)")

        # 3 — problem.json
        problem = build_problem_json(sc)
        json_path = os.path.join(out_dir, "problem.json")
        with open(json_path, "w") as f:
            json.dump(problem, f, indent=2)
        n_emp = len(problem["employees"]["simple"])
        print(f"  problem.json written ({n_emp} employees, "
              f"{len(sc['teams'])} teams, 3 shifts)")

    print(f"\nDone. Created {len(SCENARIOS)} scenarios.")


if __name__ == "__main__":
    main()

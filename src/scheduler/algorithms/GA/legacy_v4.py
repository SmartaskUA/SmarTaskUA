"""
legacy_v4.py — the original shift GA (ga.py / ga3.py) on a schema v4 package.

The v4 package is only a new spelling of the v2.2 SMARTASK problems
(data/problems/convert_legacy_to_v4.py writes it): the rules are the GA's own,
so nothing in ga.py, ga3.py, problem.py or problem3.py changes. This module
reads the package into exactly the dict `load_problem` builds from the old
folder, runs the unchanged GA, and writes the best schedule as a v4 result.

How the package says what the GA hardcodes (json_generation/schema_v4/
next_meeting.md item 33):

  AVL (dayOffCodes kind "optional")    a day the GA decides
  an "unavailable" code (VAC)          a vacation: vac_mask
  totalYearMinutes / workMinutesPerDay TARGET_WORKDAYS (exact)
  MaxConsecutiveWorkDays               WINDOW_MAX in any WINDOW_SIZE = WINDOW_MAX + 1
  MaxSpecialDays                       SPECIAL_DAYS_CAP (Sundays + calendar.holidays)
  MinDistanceBetweenShiftsInMinutes    no earlier shift the next day
  shifts_demand.csv workPeriod M/T/N   the shifts, so ga.py (M/T) or ga3.py (M/T/N)

The GA cannot take other values for these, so a package that states different
ones is refused rather than solved under the wrong rules. A --strict-v4 package
(AVL declared "preferable", no contract constraints) reads the same: AVL is
whatever kind it is declared, and an absent totalYearMinutes is not checked.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from problem_v4 import schema_core as core
from problem_v4.instance import V4Instance, make_shift
from problem_v4.runtime import finish, load_for_solver, validation_error
from problem_v4.rows import format_worked_cell, rest_cell
from problem_v4 import SolveDirectives

ALGORITHM = "Genetic Algorithm Legacy v4"
SOLVER_DECIDES = "AVL"
TEAM_AXIS = "Team"

#: the GA module pair for each set of shifts the package can state
GA_MODULES = {("M", "T"): ("ga", "problem"), ("M", "T", "N"): ("ga3", "problem3")}

#: what MinDistanceBetweenShiftsInMinutes must be for "no earlier shift the next
#: day" on the M 08-16 / T 14-22 / N 22-06 menu: it forbids exactly T->M (600),
#: N->T (480) and N->M (120), and allows every forward or equal transition (>= 960)
NO_BACKWARD_MIN_REST = 660


class LegacyPackageError(ValueError):
    """A v4 package the legacy GA cannot solve without changing its rules."""

    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def _shift_windows(problem: dict, base: Path) -> Dict[str, core.Interval]:
    """{workPeriod: window} from shifts_demand.csv, one window per shift code."""
    name = problem.get("demand", {}).get("dataFileShifts", "")
    _, rows, problems = core.read_demand(base / name, "shifts")
    if problems:
        raise LegacyPackageError([f"{name}: {p}" for p in problems])
    windows: Dict[str, core.Interval] = {}
    for row in rows:
        seen = windows.setdefault(row.work_period, row.window)
        if seen != row.window:
            raise LegacyPackageError([f"{name}: shift {row.work_period} has two windows, "
                                      f"{seen} and {row.window}"])
    return windows


def _read_rules(problem: dict, gp, n_days: int) -> List[str]:
    """Mismatches between the package's rules and the constants the GA hardcodes."""
    out: List[str] = []
    limits = core.legislation_limits(problem)

    def expect(label, found, wanted):
        if found != wanted:
            out.append(f"{label} is {found!r}; the legacy GA only enforces {wanted!r}")

    expect("MaxConsecutiveWorkDays", limits.get("MaxConsecutiveWorkDays"), gp.WINDOW_MAX)
    if gp.WINDOW_SIZE != gp.WINDOW_MAX + 1:
        out.append(f"the GA's window {gp.WINDOW_MAX}-in-{gp.WINDOW_SIZE} is not a run cap")
    expect("MaxSpecialDays", limits.get("MaxSpecialDays"), gp.SPECIAL_DAYS_CAP)
    expect("MinDistanceBetweenShiftsInMinutes", limits.get("MinDistanceBetweenShiftsInMinutes"),
           NO_BACKWARD_MIN_REST)

    for contract in problem.get("contracts", {}).get("definitions", []):
        year = (contract.get("constraints") or {}).get("totalYearMinutes")
        per_day = contract.get("workMinutesPerDay")
        if year is None:
            continue
        if not per_day or year % per_day:
            out.append(f"contract {contract.get('id')}: totalYearMinutes {year} is not a whole "
                       f"number of {per_day}-minute days")
        else:
            expect(f"contract {contract.get('id')}: totalYearMinutes / workMinutesPerDay",
                   year // per_day, gp.TARGET_WORKDAYS)

    weights = {s.get("id"): s.get("weight") for s in problem.get("constraints", {}).get("soft", [])}
    for sid, wanted in (("min-coverage", gp.W_MIN_COVER), ("ideal-coverage", gp.W_IDEAL_COVER)):
        if sid in weights:
            expect(f"constraints.soft {sid} weight", weights[sid], wanted)
    return out


def load_problem_v4(package) -> Tuple[dict, object, object]:
    """(problem_data, ga module, problem module) for a v4 package of a legacy problem.

    problem_data is what problem.load_problem / problem3.load_problem return
    for the v2.2 folder the package was converted from - same keys, same arrays.
    """
    path = Path(package)
    problem_path = path / "problem.json" if path.is_dir() else path
    base = problem_path.parent
    with problem_path.open(encoding="utf-8") as fh:
        problem = json.load(fh)

    errors: List[str] = []
    dates = core.horizon(problem)
    n_days = len(dates)
    days = [d.isoformat() for d in dates]

    windows = _shift_windows(problem, base)
    shifts = tuple(sorted(windows, key=lambda s: (windows[s].start, windows[s].end)))
    if shifts not in GA_MODULES:
        raise LegacyPackageError([f"shifts {', '.join(shifts) or '(none)'}: the legacy GA "
                                  f"solves M/T or M/T/N only"])
    ga_name, problem_name = GA_MODULES[shifts]
    gp = importlib.import_module(problem_name)
    ga = importlib.import_module(ga_name)
    errors.extend(_read_rules(problem, gp, n_days))

    # Teams in the order the package declares them: the gene encoding follows it.
    teams = [d["tableValue"] for d in problem["demand"]["dimensions"] if d["tableName"] == TEAM_AXIS]
    others = sorted({d["tableName"] for d in problem["demand"]["dimensions"]} - {TEAM_AXIS})
    if others:
        errors.append(f"dimensions {', '.join(others)}: the legacy GA covers {TEAM_AXIS} only")
    enc = gp._build_encoding(teams)
    team_idx = enc["team_idx"]

    employees, allowed_genes = [], []
    for emp in problem["employees"]["list"]:
        held = [a["tableValue"] for a in emp.get("competencyAssignments", [])
                if a.get("tableName") == TEAM_AXIS]
        contract = (emp.get("contractAssignments") or [{}])[0].get("contractType")
        employees.append({"id": emp["id"], "name": emp.get("name", emp["id"]),
                          "teams": held, "contractType": contract})
        genes = {gp.GENE_OFF}
        for shift in gp.SHIFTS:
            for team in held:
                gene = enc["shift_team_to_gene"].get((shift, team))
                if gene is not None:
                    genes.add(gene)
        allowed_genes.append(sorted(genes))

    # Vacations: every unavailable cell. Every other cell must be the GA's to decide.
    section = problem["scheduleInput"]
    _, unavailable = core.day_off_sets(section)
    cells, _, problems = core.read_schedule_input(base / section["dataFile"])
    errors.extend(problems)
    vac_mask = np.zeros((len(employees), n_days), dtype=bool)
    for i, emp in enumerate(employees):
        row = cells.get(emp["id"], {})
        for d, day in enumerate(days):
            cell = row.get(day, "")
            if cell in unavailable:
                vac_mask[i, d] = True
            elif cell != SOLVER_DECIDES:
                errors.append(f"{emp['id']} on {day}: cell {cell!r}; the legacy GA reads only "
                              f"{SOLVER_DECIDES} and unavailable codes")
                break

    _, rows, problems = core.read_demand(base / problem["demand"]["dataFileShifts"], "shifts")
    shape = (n_days, len(gp.SHIFTS), len(teams))
    min_demand, ideal_demand = np.zeros(shape, dtype=int), np.zeros(shape, dtype=int)
    index = {d: i for i, d in enumerate(dates)}
    for row in rows:
        d, s, t = index[row.date], gp.SHIFT_IDX[row.work_period], team_idx[row.table_value]
        min_demand[d, s, t] = int(row.minimum)
        ideal_demand[d, s, t] = int(row.ideal)

    if errors:
        raise LegacyPackageError(errors)

    origin = dates[0]
    special_days = {(d - origin).days for d in core.special_days(problem)}

    gene_to_shift_team = enc["gene_to_shift_team"]
    max_gene = max(gene_to_shift_team) if gene_to_shift_team else 0
    gene_shift_arr = np.zeros(max_gene + 1, dtype=np.int32)
    gene_team_arr = np.zeros(max_gene + 1, dtype=np.int32)
    for g, (s_code, t_code) in gene_to_shift_team.items():
        gene_shift_arr[g] = gp.SHIFT_IDX[s_code]
        gene_team_arr[g] = team_idx[t_code]

    problem_data = {
        "n_employees": len(employees),
        "n_days": n_days,
        "year": origin.year,
        "teams": teams,
        "employees": employees,
        "allowed_genes": allowed_genes,
        "vac_mask": vac_mask,
        "min_demand": min_demand,
        "ideal_demand": ideal_demand,
        "special_days": special_days,
        "gene_shift_arr": gene_shift_arr,
        "gene_team_arr": gene_team_arr,
        **enc,
        # not in load_problem's dict: the windows, for writing the result back
        "shift_windows": windows,
    }
    return problem_data, ga, gp


def schedule_rows(inst: V4Instance, problem_data: dict, schedule: np.ndarray, gp) -> List[List[str]]:
    """The GA's (employee, day) genes as the v4 rows every result writer reads."""
    windows = problem_data["shift_windows"]
    # From the menu, not inst.candidates: a --strict-v4 package declares AVL
    # preferable, and the v4 loader offers no shift on a day off unless swapping.
    menu = {(s.interval.start, s.interval.end): s for s in inst.menu.values()
            if s.interval is not None and not s.is_sentinel}
    out = [["employee_id", *inst.days]]
    for i, emp in enumerate(problem_data["employees"]):
        row = [emp["id"]]
        for d, day in enumerate(inst.days):
            gene = int(schedule[i, d])
            if gene == gp.GENE_OFF:
                row.append(rest_cell(inst, emp["id"], day))
                continue
            shift_code, team = problem_data["gene_to_shift_team"][gene]
            window = windows[shift_code]
            shift = make_shift(emp["id"], day, menu[(window.start, window.end)], inst.slot_minutes)
            skills = {t: [f"{TEAM_AXIS}/{team}"] for t in shift.slot_indices}
            row.append(format_worked_cell(shift, skills, inst.slot_minutes))
        out.append(row)
    return out


def solve(problem_path=None, maxTime=None, **kwargs):
    """TaskManager / CLI entry. kwargs: result_dir, seed, and any key of the GA's
    _GA_PARAMS (pop_size, num_generations, early_stop_patience, ...). maxTime is
    ignored, as in ga.py: the GA stops early instead."""
    task_id = str(kwargs.get("task_id", "manual"))
    inst = load_for_solver(problem_path, SolveDirectives(), task_id, ALGORITHM)
    try:
        problem_data, ga, gp = load_problem_v4(inst.problem_path)
    except LegacyPackageError as exc:
        raise validation_error(problem_path, task_id, ALGORITHM, "INVALID_V4_PACKAGE",
                               exc.problems, "Not a legacy shift problem") from exc

    params = dict(ga._GA_PARAMS)
    params.update({k: type(v)(kwargs[k]) for k, v in ga._GA_PARAMS.items() if kwargs.get(k) is not None})
    if kwargs.get("seed") is not None:
        ga.random.seed(int(kwargs["seed"]))
        np.random.seed(int(kwargs["seed"]))
    best, best_fitness, _, _ = ga.run_ga(problem_data, params)
    schedule = np.array(best["genes"], dtype=int).reshape(problem_data["n_employees"], problem_data["n_days"])
    print(f"[{ALGORITHM}] best fitness {best_fitness:.0f}")
    return finish(inst, schedule_rows(inst, problem_data, schedule, gp), kwargs)

"""
convert_legacy_to_v4.py — Describe a v2.2 shift problem (SMARTASK_*) in schema v4.

The problem does not change, only its spelling: the solver still chooses every
working day, and vacations are the only days fixed in advance. The three things
v4.0 cannot say about that are proposed in json_generation/schema_v4/
next_meeting.md item 33 ("solver chooses the days off"):

    legacy (v2.2)                       v4 package
    vacations.csv 1                     VAC   (dayOffCodes kind "unavailable")
    vacations.csv 0                     AVL   (dayOffCodes kind "optional")
    total_workdays {min = max = N}      contract constraints.totalYearMinutes = N x 480
    max_special_days {cap}              constraints.hard MaxSpecialDays
    max_consecutive_days {k + 1, k}     constraints.hard MaxConsecutiveWorkDays = k
    no_earlier_shift_next_day           constraints.hard MinDistanceBetweenShiftsInMinutes
    demand.shifts M / T / N             schedules.csv codes, and shifts_demand.csv workPeriod
    demand.csv                          shifts_demand.csv, values copied verbatim
    teams                               demand.dimensions Team/<t>, competency level 1
    Sundays + PT holidays               calendar.holidays (the GA's own `holidays` source)

With --strict-v4 the package uses none of the three additions, for a validator
that refuses them: AVL is declared "preferable" and totalYearMinutes is left out.
That loses the meaning - a v4 solver penalises working a preferable day - so the
script says so. The legacy GA (`-a ga-legacy`) reads both variants the same way.

A problem whose rules have no v4 spelling (SMARTASK_SIMPLE_2025_FIXED_DAYS_OFF's
weekly/monthly counts) is refused, not approximated.

Usage:
    python convert_legacy_to_v4.py <legacy folder> [<out folder>] [--strict-v4]
    python convert_legacy_to_v4.py --all [--strict-v4]

    <out folder> defaults to V4_<legacy folder name> beside it. --all converts
    every SMARTASK_* folder here that it can, and reports the ones it cannot.

Examples:
    python convert_legacy_to_v4.py SMARTASK_SIMPLE_2025
    python convert_legacy_to_v4.py SMARTASK_3SHIFTS_4TEAMS_2025 /tmp/strict --strict-v4
"""

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

SLOT_MINUTES = 120
#: our own numbering, as the v4 menu allows; 1, 3 and 4 are WFM's rest codes
SHIFT_CODES = {"M": 8001, "T": 8002, "N": 8003}
REST_SENTINELS = [(1, "Espaço"), (3, "Day off"), (4, "Vazio")]
VACATION, SOLVER_DECIDES = "VAC", "AVL"
DEMAND_HEADER = "date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
KNOWN_RULES = {"max_consecutive_days", "total_workdays", "max_special_days",
               "no_earlier_shift_next_day", "vacation_block"}

MENU_NOTE = """\
# schedules.csv -- the shift menu this roster may pick from.
# Written by data/problems/convert_legacy_to_v4.py from the legacy problem's
# demand.shifts. Codes 8001.. are ours and arbitrary; the window is what they mean.
# Codes 1, 3 and 4 carry WFM's own rest semantics on import.
"""


class ConversionError(ValueError):
    pass


def hhmm(minutes: int) -> str:
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def minutes(text: str) -> int:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def shift_windows(prob: dict) -> dict:
    """{code: (startMin, endMin)} in the legacy order; endMin passes 1440 overnight."""
    out = {}
    for s in sorted(prob["demand"]["shifts"], key=lambda s: s["order"]):
        start, end = minutes(s["timeRange"]["start"]), minutes(s["timeRange"]["end"])
        out[s["code"]] = (start, end if end > start else end + 1440)
    return out


def no_backward_rest(windows: dict) -> int:
    """The MinDistanceBetweenShiftsInMinutes that forbids exactly the backward moves.

    'No earlier shift the next day' forbids b after a when b comes before a in
    the legacy order. On a fixed menu that is a rest threshold: every backward
    move rests less than every forward one, and the first whole hour above the
    longest backward rest separates them (660 on M/T and on M/T/N).
    """
    order = list(windows)
    backward, forward = [], []
    for i, a in enumerate(order):
        for j, b in enumerate(order):
            rest = windows[b][0] + 1440 - windows[a][1]
            (backward if j < i else forward).append(rest)
    threshold = (max(backward) // 60 + 1) * 60 if backward else 0
    if forward and threshold > min(forward):
        raise ConversionError("no rest threshold separates the backward shift moves from the "
                              "forward ones on this menu")
    return threshold


def read_rules(prob: dict, windows: dict) -> tuple:
    """(hard parameters, workdays per year) from the legacy constraints.hard."""
    params, workdays = {}, None
    for rule in prob["constraints"]["hard"]:
        if rule.get("enabled") is False:
            continue
        kind, p = rule["type"], rule.get("params", {})
        if kind not in KNOWN_RULES:
            raise ConversionError(f"rule {kind!r} has no v4 spelling")
        if kind == "max_consecutive_days":
            if p["window"] != p["max_worked"] + 1:
                raise ConversionError(f"max_consecutive_days {p}: only 'k in any k+1' is a run cap")
            params["MaxConsecutiveWorkDays"] = p["max_worked"]
        elif kind == "total_workdays":
            if p["min"] != p["max"]:
                raise ConversionError(f"total_workdays {p}: v4 states one exact target")
            workdays = p["min"]
        elif kind == "max_special_days":
            params["MaxSpecialDays"] = p["cap"]
        elif kind == "no_earlier_shift_next_day":
            params["MinDistanceBetweenShiftsInMinutes"] = no_backward_rest(windows)
    return params, workdays


def pt_holidays(start: date, end: date) -> list:
    """The PT public holidays the GA itself reads (problem._build_special_days)."""
    import holidays as hl
    years = list(range(start.year, end.year + 1))
    found = sorted((d, name) for d, name in hl.country_holidays("PT", years=years).items()
                   if start <= d <= end)
    return [{"date": d.isoformat(), "code": f"PT{n}", "name": name, "hasEve": False}
            for n, (d, name) in enumerate(found, start=1)]


def convert(src: Path, out: Path, strict: bool) -> list:
    """Write the v4 package for `src` into `out`. Returns warnings."""
    with (src / "problem.json").open(encoding="utf-8") as fh:
        prob = json.load(fh)
    if str(prob.get("schemaVersion")) != "2.2" or prob["employees"].get("model") != "team":
        raise ConversionError("not a v2.2 team-model problem")
    if not (src / "vacations.csv").is_file():
        raise ConversionError("no vacations.csv")

    scope = prob["temporalScope"]
    start = date.fromisoformat(scope["targetPeriod"]["start"])
    days = [start + timedelta(days=i) for i in range(scope["numDays"])]
    end = days[-1]
    teams = prob["demand"]["organizationalUnits"]["teams"]
    windows = shift_windows(prob)
    params, workdays = read_rules(prob, windows)
    warnings = []

    contracts = []
    for c in prob["contracts"]["definitions"]:
        per_day = int(round(c["workHoursPerDay"] * 60))
        entry = {"id": c["id"], "name": c.get("name", c["id"]), "workMinutesPerDay": per_day}
        if workdays is not None and not strict:
            entry["constraints"] = {"totalYearMinutes": workdays * per_day}
        contracts.append(entry)

    employees = []
    for e in prob["employees"]["simple"]:
        employees.append({
            "id": e["id"], "name": e.get("name", e["id"]),
            "contractAssignments": [{"contractType": e["contractType"], "start": start.isoformat(),
                                     "end": None}],
            "competencyAssignments": [{"tableName": "Team", "tableValue": t, "level": 1,
                                       "start": start.isoformat(), "end": end.isoformat()}
                                      for t in e["teams"]],
        })

    # vacations.csv: no header, one row per employee in problem.json order.
    with (src / "vacations.csv").open(encoding="utf-8") as fh:
        vac_rows = [r for r in csv.reader(fh) if r]
    by_name = {r[0]: r[1:] for r in vac_rows}
    cells = {}
    for e in employees:
        flags = by_name.get(e["id"])
        if flags is None or len(flags) != len(days):
            raise ConversionError(f"vacations.csv has no {len(days)}-day row for {e['id']!r}")
        cells[e["id"]] = [VACATION if f.strip() == "1" else SOLVER_DECIDES for f in flags]
    if [r[0] for r in vac_rows] != [e["id"] for e in employees]:
        raise ConversionError("vacations.csv rows are not in problem.json's employee order, "
                              "which the legacy GA relies on")

    day_off_codes = {
        VACATION: {"kind": "unavailable", "name": "Vacation", "description": "Vacation - cannot work"},
        SOLVER_DECIDES: {"kind": "preferable" if strict else "optional", "name": "Available",
                         "description": "The solver decides whether this day is worked"},
    }
    used = {c for row in cells.values() for c in row}
    day_off_codes = {k: v for k, v in day_off_codes.items() if k in used}

    soft = [{"id": s["id"], "type": s["type"], "weight": s["weight"],
             "parameters": s.get("params", {}), "enabled": s.get("enabled", True)}
            for s in prob["constraints"].get("soft", [])]

    v4 = {
        "schemaVersion": "4.0",
        "form": "input",
        "problemType": "employee_scheduling",
        "metadata": {
            "problemId": out.name,
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "description": prob["metadata"].get("description", ""),
            "source": f"{src.name} (schema 2.2), by data/problems/convert_legacy_to_v4.py"
                      + (" --strict-v4" if strict else ""),
            "rosterCode": src.name,
        },
        "timeGrid": {"slotMinutes": SLOT_MINUTES},
        "temporalScope": {"start": start.isoformat(), "end": end.isoformat()},
        "calendar": {"weekStart": "monday", "holidays": pt_holidays(start, end)},
        "contracts": {"definitions": contracts},
        "employees": {"list": employees},
        "demand": {
            "dimensions": [{"tableName": "Team", "tableValue": t, "name": f"Team {t}"} for t in teams],
            "dataFileDays": "days_demand.csv",
            "dataFilePeriods": "periods_demand.csv",
            "dataFileShifts": "shifts_demand.csv",
        },
        "scheduleInput": {"dataFile": "schedule_input.csv", "dayOffCodes": day_off_codes},
        "schedules": {"dataFile": "schedules.csv"},
        "constraints": {
            "hard": [{"id": "legacy-rules", "type": "RosterLegislation", "parameters": params,
                      "startDate": f"{start.isoformat()}T00:00:00", "enabled": True}],
            "soft": soft,
        },
    }

    out.mkdir(parents=True, exist_ok=True)
    with (out / "problem.json").open("w", encoding="utf-8") as fh:
        json.dump(v4, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    with (out / "schedules.csv").open("w", encoding="utf-8", newline="") as fh:
        fh.write(MENU_NOTE)
        fh.write("code,description,scheduleWeightMinutes,startMin,endMin\n")
        for code, label in REST_SENTINELS:
            fh.write(f"{code},{label},0,,\n")
        for s, (a, b) in windows.items():
            fh.write(f"{SHIFT_CODES[s]},{hhmm(a)}-{hhmm(b)},{b - a},{a},{b}\n")

    with (src / "demand.csv").open(encoding="utf-8") as fh:
        demand = list(csv.DictReader(fh))
    with (out / "shifts_demand.csv").open("w", encoding="utf-8", newline="") as fh:
        fh.write("date,workPeriod," + DEMAND_HEADER.split(",", 1)[1])
        for r in demand:
            a, b = windows[r["shift"]]
            fh.write(f"{r['date']},{r['shift']},Team,{r['team']},{r['minimum']},{r['ideal']},"
                     f"{r.get('estimated') or 0},{hhmm(a)},{hhmm(b)}\n")
    for name in ("periods_demand.csv", "days_demand.csv"):
        (out / name).write_text(DEMAND_HEADER, encoding="utf-8")

    with (out / "schedule_input.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["employee_id", *(d.isoformat() for d in days)])
        for eid, row in cells.items():
            w.writerow([eid, *row])

    if strict:
        warnings.append(f"--strict-v4: {SOLVER_DECIDES} is declared 'preferable', so a v4 solver "
                        f"penalises working it, and the {workdays}-day target is not stated. "
                        f"Only the legacy GA reads this package as the original problem.")
    return warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("legacy", nargs="?", help="legacy v2.2 problem folder")
    ap.add_argument("out", nargs="?", help="output folder (default: V4_<legacy name> beside it)")
    ap.add_argument("--all", action="store_true", help="convert every SMARTASK_* folder here")
    ap.add_argument("--strict-v4", action="store_true",
                    help="plain v4.0: no 'optional' kind, no contract constraints")
    args = ap.parse_args()

    if args.all == bool(args.legacy):
        ap.error("give one legacy folder, or --all")
    sources = sorted(HERE.glob("SMARTASK_*")) if args.all else [Path(args.legacy).resolve()]

    failed = 0
    for src in sources:
        out = Path(args.out).resolve() if args.out else src.parent / f"V4_{src.name}"
        try:
            warnings = convert(src, out, args.strict_v4)
        except ConversionError as exc:
            failed += 1
            print(f"skipped {src.name}: {exc}", file=sys.stderr)
            continue
        print(f"wrote   {out}")
        for w in warnings:
            print(f"  warning: {w}")
    return 1 if failed and not args.all else 0


if __name__ == "__main__":
    sys.exit(main())

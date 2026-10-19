#!/usr/bin/env python3
"""Compile a v3.0 declarative problem into the v3.0 expanded form.

The declarative form states each worker's workable time implicitly: a contract,
a catalogue of work periods, and a per-day cell that may narrow things further.
The expanded form states it explicitly -- for every worker and day, the set of
daily working assignments they may take.  That set is the mathematical model's
H_wd, and the timeslots each assignment covers is delta_wdht
(MathematicalDefinition7, "Final formulation").

The domain -- what a cell means, which blocks a day could take, why a day came
out empty -- lives in core.py, shared with the validator.  This file is just the
expansion on top of it: pick the candidates, apply the T_d filter, dedup into a
catalogue, emit.

Usage:
    python3 transform.py problem.json                 # writes problem.expanded.json
    python3 transform.py problem.json -o out.json
    python3 transform.py problem.json --stats
    python3 transform.py problem.json --strict        # exit 1 on impossible cells
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import core  # sibling module in this package
from core import WEEKDAY_NAMES, Candidate, Diagnostic, DomainError

TRANSFORMER_VERSION = "3.0.0"


class TransformError(DomainError):
    """Raised when the declarative problem cannot be compiled.

    A subclass of core.DomainError so callers can catch either, but distinct so
    the transformer can add expansion-specific failures.
    """


def transform(problem: dict, base: Path) -> tuple[dict, dict, list[Diagnostic]]:
    if problem.get("form") != "declarative":
        raise TransformError(f"expected form 'declarative', got {problem.get('form')!r}")

    slot = problem["timeGrid"]["slotMinutes"]
    periods = core.period_ranges(problem)
    window = core.operating_window(periods, slot)
    t_d, _ = core.read_demand(problem, base, periods)
    cells, date_columns = core.read_schedule_input(problem, base)

    contracts = {c["id"]: c for c in problem["contracts"]["definitions"]}

    catalog: dict[tuple, str] = {}
    catalog_rows: list[dict] = []
    stats = {
        "workerDays": 0,
        "openWorkerDays": 0,
        "unavailable": 0,
        "preferable": 0,
        "excludedByTd": 0,
        "emptyOnOpenDay": 0,
    }

    def intern(cand: Candidate) -> str:
        key = cand.key()
        if key not in catalog:
            ident = f"A{len(catalog) + 1:04d}"
            catalog[key] = ident
            row = {
                "id": ident,
                "intervals": [
                    {"startMin": iv.start, "endMin": iv.end} for iv in cand.intervals
                ],
            }
            catalog_rows.append(row)
        return catalog[key]

    availability = []
    for emp in problem["employees"]["list"]:
        emp_id = emp["id"]
        if emp_id not in cells:
            raise TransformError(f"employee {emp_id!r} has no row in schedule_input.csv")

        days_out = []
        for iso_d in date_columns:
            day = date.fromisoformat(iso_d)
            weekday = WEEKDAY_NAMES[day.weekday()]
            demanded = t_d.get(iso_d, set())
            is_open = bool(demanded)
            stats["workerDays"] += 1
            if is_open:
                stats["openWorkerDays"] += 1

            entry: dict = {"date": iso_d}

            rule = core.classify_cell(cells[emp_id].get(iso_d, ""), problem)
            contract_id = core.active_period(emp["contractAssignments"], day, "contractType")
            contract = contracts.get(contract_id) if contract_id else None
            competencies = core.active_competencies(emp["competencyAssignments"], day)

            # Hard unavailability, in precedence order.  Each of these puts the day
            # in U_wk, which matters beyond this day: n_wk is derived by subtracting
            # |U_wk| and |D_wk| from the week's open days, so a day that cannot be
            # worked must be recorded as unavailable rather than merely left empty.
            #
            # A calendar holiday is deliberately NOT one of these.  Marking a day as
            # a holiday exists so the enterprise can give it its own demand; it does
            # not decide who works.  Shops open on holidays, and whether a given
            # worker is entitled to take it off depends on the workplace-vs-residence
            # entitlement rule, which is per-employee and deferred (see FUTURE.md).
            # Until then a holiday reaches U_wk only the same way any other day does: via
            # that worker's schedule-input cell.
            reason = None
            if rule.kind == "dayoff" and rule.day_off == "unavailable":
                reason = rule.reason or "other"
            elif contract_id is None:
                reason = "contract_inactive"
            elif not competencies:
                reason = "other"  # no competency held on this date -> cannot cover anything

            if reason is not None:
                entry["assignmentIds"] = []
                entry["dayOff"] = "unavailable"
                entry["unavailableReason"] = reason
                stats["unavailable"] += 1
                days_out.append(entry)
                continue

            allowed = core.day_allowed(contract, weekday)
            eligible = core.build_day_candidates(rule, contract, window, slot) if allowed else []

            # MathematicalDefinition7, stated in bold: "H_wd does not include
            # assignments with timeslots t not belonging to T_d".  An assignment
            # reaching outside the demanded window is dropped whole -- trimming it
            # would invent an assignment the enterprise never defined.
            kept = []
            for cand in eligible:
                if core.slots_of(cand.intervals, slot) <= demanded:
                    kept.append(cand)
                else:
                    stats["excludedByTd"] += 1

            entry["assignmentIds"] = sorted({intern(c) for c in kept})

            if rule.kind == "dayoff" and rule.day_off == "preferable":
                # Soft: the worker would rather be off but may be scheduled at a
                # penalty, so the options stay on the table.
                entry["dayOff"] = "preferable"
                stats["preferable"] += 1

            if is_open and not entry["assignmentIds"] and "dayOff" not in entry:
                # An open day with no options would make constraint (6),
                # sum over D_k of x_wdh = n_wk, unsatisfiable: n_wk counts this day
                # as workable while H_wd offers nothing.  Record it as unavailable
                # so the count and the options agree.  Whether this silently
                # rewrote a work request is reported separately via
                # core.scan_feasibility below -- the one place that decision lives.
                entry["dayOff"] = "unavailable"
                entry["unavailableReason"] = "other"
                stats["emptyOnOpenDay"] += 1
                stats["unavailable"] += 1

            if entry.get("dayOff") == "preferable" and not entry["assignmentIds"]:
                entry["dayOff"] = "unavailable"
                entry["unavailableReason"] = "other"
                stats["preferable"] -= 1
                stats["unavailable"] += 1

            # Record the INCLUDE/WITHIN/EXCEPT windows so the constraint survives into
            # the expanded form and the validator can re-check it against this file
            # alone.  Only on a workable day: an unavailable day offers no
            # assignments, so there is nothing to cover, contain or avoid.
            if entry["assignmentIds"] and entry.get("dayOff") != "unavailable":
                if rule.kind == "include":
                    entry["mustCover"] = [
                        {"startMin": w.start, "endMin": w.end} for w in rule.windows
                    ]
                elif rule.kind == "within":
                    entry["mustBeWithin"] = [
                        {"startMin": w.start, "endMin": w.end} for w in rule.windows
                    ]
                elif rule.kind == "except":
                    entry["mustAvoid"] = [
                        {"startMin": w.start, "endMin": w.end} for w in rule.windows
                    ]

            days_out.append(entry)

        availability.append({"employeeId": emp_id, "days": days_out})

    expanded = {
        "schemaVersion": "3.0",
        "form": "expanded",
        "problemType": problem["problemType"],
        "metadata": problem["metadata"],
        "generatedFrom": {
            "declarativeProblemId": problem["metadata"]["problemId"],
            "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
            "transformerVersion": TRANSFORMER_VERSION,
        },
        "timeGrid": problem["timeGrid"],
        "temporalScope": problem["temporalScope"],
        "contracts": problem["contracts"],
        "employees": problem["employees"],
        # demand carries through untouched, work periods included: expanding a
        # problem changes how each worker's workable time is expressed, never what
        # coverage is asked for.  The periods have to travel with it -- demand.csv
        # keys its rows on their codes, so without them nothing downstream could
        # rebuild T_d.
        "demand": problem["demand"],
        "assignmentCatalog": catalog_rows,
        "availability": availability,
    }
    if "calendar" in problem:
        expanded["calendar"] = problem["calendar"]

    # Diagnostics come from the one shared scan, so the transformer and the
    # validator can never disagree about which cells are impossible.
    diagnostics = core.scan_feasibility(problem, base)

    stats["assignments"] = len(catalog_rows)
    stats["openDays"] = len(t_d)
    stats["diagnostics"] = len(diagnostics)
    # H_wd size is the practical signal for model blow-up: it is the number of
    # x_wdh variables the solver gets per worker-day.
    sizes = [len(d["assignmentIds"]) for a in availability for d in a["days"] if d.get("assignmentIds")]
    stats["hwdMax"] = max(sizes) if sizes else 0
    stats["hwdMean"] = round(sum(sizes) / len(sizes), 1) if sizes else 0
    return expanded, stats, diagnostics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("problem", type=Path, help="v3.0 declarative problem.json")
    ap.add_argument("-o", "--output", type=Path, help="output path (default: <problem>.expanded.json)")
    ap.add_argument("--stats", action="store_true", help="print expansion statistics")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if any cell asks for work that can never happen",
    )
    args = ap.parse_args()

    try:
        problem = json.loads(args.problem.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {args.problem}: {exc}", file=sys.stderr)
        return 1

    try:
        expanded, stats, diagnostics = transform(problem, args.problem.parent)
    except DomainError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out = args.output or args.problem.with_suffix(".expanded.json")
    out.write_text(json.dumps(expanded, indent=2) + "\n")
    print(f"wrote {out}")

    if diagnostics:
        stream = sys.stderr if args.strict else sys.stdout
        label = "ERROR" if args.strict else "WARN"
        print(f"\n{len(diagnostics)} impossible cell(s) -- each became a day off in the output, "
              f"which is NOT what the input asked for:", file=stream)
        for d in diagnostics:
            print(f"  {label} {d}", file=stream)

    if args.stats:
        print("\nexpansion statistics")
        for key, value in stats.items():
            print(f"  {key:20s} {value}")

    return 1 if (args.strict and diagnostics) else 0


if __name__ == "__main__":
    sys.exit(main())

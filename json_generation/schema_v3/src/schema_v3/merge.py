#!/usr/bin/env python3
"""Fold a solution seed's hard decisions into an expanded problem.

A v3.0 solution doubles as a partial warm-start seed: each worker-day it states
may be SEEDED (a non-null assignmentId) and, if `locked`, a HARD pre-commitment.
This tool applies those locks to the problem, producing a SEEDED EXPANDED --
an ordinary expanded problem in which the locked worker-days carry the existing
`forced` pin.  The output conforms to schema-v3-expanded.json unchanged: no new
fields, so every existing consumer and the validator honour it as-is.

Locks only, by design.  A SOFT (unlocked) seed is a starting point, not a problem
constraint, and the expanded form has no field for one -- it stays in the seed
file for the solver to read alongside this output (see docs/FUTURE.md 7).

Two input modes, both yielding an expanded package:
    expanded    + solution -> locks applied directly
    declarative + solution -> transformed first (transform.py), then locks applied

The demand CSV the expanded references travels with the output, so the result is
a complete, validatable package.

Usage:
    python3 merge.py problem.expanded.json solution.json
    python3 merge.py problem.json solution.json -o seeded/problem.merged.expanded.json
    python3 merge.py problem.expanded.json solution.json --stats
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

import transform  # merge orchestrates above the transformer
from core import DomainError


class MergeError(DomainError):
    """Raised when a seed cannot be coherently folded into a problem.

    A subclass of core.DomainError so callers can catch either. Unlike the
    transformer's soft diagnostics, every merge failure is fatal: a lock that
    cannot be applied would silently produce a problem that is not the one the
    seed described.
    """


def _resolve_expanded(problem: dict, base: Path) -> tuple[dict, str]:
    """The expanded problem to seed, plus the form it came from."""
    form = problem.get("form")
    if form == "expanded":
        return problem, "expanded"
    if form == "declarative":
        # Expansion is deterministic, so the A#### ids a seed names line up with
        # the ones produced here from the same declarative source.
        expanded, _stats, _diagnostics = transform.transform(problem, base)
        return expanded, "declarative"
    raise MergeError(
        f"expected a problem of form 'declarative' or 'expanded', got {form!r}"
    )


def merge(problem: dict, seed: dict, base: Path) -> tuple[dict, dict]:
    """Apply a seed's locked days to a problem as `forced` pins.

    `problem` may be declarative (transformed first) or expanded. Returns the
    seeded expanded and stats. Raises MergeError listing every incoherence, so a
    caller sees all of them at once rather than one per run.
    """
    expanded, source_form = _resolve_expanded(problem, base)

    prob_id = expanded.get("metadata", {}).get("problemId")
    if seed.get("problemId") != prob_id:
        raise MergeError(
            f"seed problemId {seed.get('problemId')!r} does not match the problem's "
            f"metadata.problemId {prob_id!r}"
        )

    merged = copy.deepcopy(expanded)

    # index the worker-days of the copy: the pins are written straight into it
    days_by_key: dict[tuple[str, str], dict] = {}
    for entry in merged.get("availability", []):
        for day in entry.get("days", []):
            days_by_key[(entry["employeeId"], day["date"])] = day

    problems: list[str] = []
    locks = 0
    soft = 0

    for assignment in seed.get("assignments", []):
        eid = assignment.get("employeeId")
        for day in assignment.get("days", []):
            iso_d = day.get("date")
            aid = day.get("assignmentId")

            if not day.get("locked"):
                # A soft seed constrains nothing here; it stays in the seed file.
                if aid is not None:
                    soft += 1
                continue

            if aid is None:
                problems.append(
                    f"{eid} {iso_d}: locked is true but assignmentId is null; a locked "
                    "day must name an assignment"
                )
                continue

            target = days_by_key.get((eid, iso_d))
            if target is None:
                problems.append(
                    f"{eid} {iso_d}: locked day has no such worker-day in the problem"
                )
                continue

            if aid not in target.get("assignmentIds", []):
                problems.append(
                    f"{eid} {iso_d}: cannot lock {aid!r}; it is not one of this "
                    "worker-day's options [H_wd]"
                )
                continue

            existing = target.get("forced")
            if existing is not None and existing != aid:
                problems.append(
                    f"{eid} {iso_d}: cannot lock {aid!r}; the problem already forces "
                    f"{existing!r} on this worker-day"
                )
                continue

            target["forced"] = aid
            locks += 1

    if problems:
        raise MergeError(
            f"{len(problems)} lock(s) could not be applied:\n  " + "\n  ".join(problems)
        )

    stats = {
        "sourceForm": source_form,
        "locksApplied": locks,
        "softSeedsSkipped": soft,
        "workerDays": len(days_by_key),
    }
    return merged, stats


def _default_output(problem_path: Path) -> Path:
    """<name>.json / <name>.expanded.json -> <name>.merged.expanded.json."""
    name = problem_path.name
    for suffix in (".expanded.json", ".json"):
        if name.endswith(suffix):
            return problem_path.with_name(name[: -len(suffix)] + ".merged.expanded.json")
    return problem_path.with_name(name + ".merged.expanded.json")


def _carry_demand_csv(merged: dict, source_dir: Path, out: Path) -> str | None:
    """Copy the demand CSV the expanded references next to the output.

    The expanded names it by a path relative to itself, so an output written
    elsewhere would dangle without this. Returns the copied name, or None.
    """
    data_file = merged.get("demand", {}).get("dataFile")
    if not data_file:
        return None
    src = (source_dir / data_file).resolve()
    dst = (out.parent / data_file).resolve()
    if src == dst or not src.exists():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    return data_file


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("problem", type=Path, help="v3.0 problem, declarative or expanded")
    ap.add_argument("seed", type=Path, help="v3.0 solution used as a warm-start seed")
    ap.add_argument(
        "-o", "--output", type=Path,
        help="output path (default: <problem>.merged.expanded.json)",
    )
    ap.add_argument("--stats", action="store_true", help="print merge statistics")
    args = ap.parse_args()

    try:
        problem = json.loads(args.problem.read_text())
        seed = json.loads(args.seed.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read input: {exc}", file=sys.stderr)
        return 1

    if seed.get("form") != "solution":
        print(f"ERROR: {args.seed} is not a solution (form={seed.get('form')!r})", file=sys.stderr)
        return 1

    try:
        merged, stats = merge(problem, seed, args.problem.parent)
    except DomainError as exc:
        # Nothing is written: a partially applied seed is not the problem the
        # seed described.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out = args.output or _default_output(args.problem)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, indent=2) + "\n")
    print(f"wrote {out}")

    carried = _carry_demand_csv(merged, args.problem.parent, out)
    stats["demandCsvCopied"] = carried or "(same directory)"
    if carried:
        print(f"copied {carried} alongside it")

    if args.stats:
        print("\nmerge statistics")
        for key, value in stats.items():
            print(f"  {key:20s} {value}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

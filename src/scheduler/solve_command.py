"""`python -m scheduler solve PACKAGE`: solve a schema v4 package in one command.

Runs one or all v4 solvers, writes each result next to a copy of the package,
scores every result with the same `problem_v4.evaluate`, checks it with the v4
validator when the repo's json_generation/ tree is present, and prints one line
per algorithm. See docs/how-to-solve.md.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_V4_SRC = REPO_ROOT / "json_generation" / "schema_v4" / "src"

#: alias -> (TaskManager registry name, module holding its `solve`)
V4_SOLVERS: Dict[str, Tuple[str, str]] = {
    "ilp": ("ILP_Sisqual_Hours_MathematicalDefinition7", "algorithms.ILP_Sisqual_Hours_MathematicalDefinition7"),
    "csp": ("CSP_Sisqual_Hours_MathematicalDefinition7", "algorithms.CSP_Sisqual_Hours_MathematicalDefinition7"),
    "hybrid": ("Hybrid_Heuristic_Sisqual_3", "algorithms.Hybrid_Heuristic_Sisqual_No_Levels_Included"),
    "hybrid-levels": ("Hybrid_Heuristic_Sisqual_Levels_Included", "algorithms.Hybrid_Heuristic_Sisqual_Levels_Included"),
    "ga": ("Genetic Algorithm v4", "algorithms.GA.ga_v4"),
}


def add_solve_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "solve",
        help="Solve a schema v4 package with one or all v4 solvers",
        description="Solve a schema v4 package; results go to exports/<package>/<algorithm>/.",
    )
    parser.add_argument("package", help="v4 package folder (or its problem.json)")
    parser.add_argument("-a", "--algorithm", default="ilp",
                        help=f"{'|'.join(V4_SOLVERS)}|all, or a full v4 algorithm name (default: ilp)")
    parser.add_argument("-t", "--time", type=float, default=1.0, help="time limit per solver, minutes (default: 1)")
    parser.add_argument("-o", "--out", help="output folder (default: <repo>/exports/<package folder name>)")
    parser.add_argument("--param", action="append", default=[],
                        help="KEY=VALUE passed to the solver, e.g. w2=1 or allow_day_off_swap=true. Repeatable.")


def resolve_algorithms(choice: str) -> List[Tuple[str, str, str]]:
    """[(alias, registry name, module)] for an alias, `all`, or a full v4 algorithm name."""
    choice = choice.strip()
    if choice.lower() == "all":
        return [(alias, name, module) for alias, (name, module) in V4_SOLVERS.items()]
    if choice.lower() in V4_SOLVERS:
        name, module = V4_SOLVERS[choice.lower()]
        return [(choice.lower(), name, module)]
    for alias, (name, module) in V4_SOLVERS.items():
        if choice == name:
            return [(alias, name, module)]
    raise SystemExit(f"unknown v4 algorithm {choice!r}; use one of: {', '.join(V4_SOLVERS)}, all")


def _validator() -> Optional[Callable]:
    """The v4 validator's validate_package, when the repo's json_generation/ tree is here."""
    if not SCHEMA_V4_SRC.is_dir():
        return None
    if str(SCHEMA_V4_SRC) not in sys.path:
        sys.path.insert(0, str(SCHEMA_V4_SRC))
    try:
        from schema_v4.validator import validate_package
    except ImportError:
        return None
    return validate_package


def _shown(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_solve(args: argparse.Namespace, parse_params: Callable) -> int:
    # Top-level names on purpose: the solvers raise validators.sisqual_feasibility's
    # class, and a relatively imported copy would be a different class.
    from problem_v4 import ParseError, evaluate, load_package
    from validators.sisqual_feasibility import SisqualValidationError

    package = Path(args.package).expanduser().resolve()
    folder = package if package.is_dir() else package.parent
    algorithms = resolve_algorithms(args.algorithm)
    out_root = Path(args.out).expanduser().resolve() if args.out else REPO_ROOT / "exports" / folder.name
    params = parse_params(args.param)

    try:
        inst = load_package(folder)
    except ParseError as exc:
        print(f"{_shown(folder)} is not a usable v4 package:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    validate = _validator()

    lines, failures, notes = [], 0, []
    for alias, name, module in algorithms:
        out = out_root / alias
        kwargs = {"problem_path": str(folder), "maxTime": args.time, "task_id": "cli", "verbose": False,
                  "result_dir": str(out), "results_log_file": str(out_root / f"{alias}_restarts.csv"), **params}
        started = time.perf_counter()
        try:
            rows = importlib.import_module(module).solve(**kwargs)
        except SisqualValidationError as exc:
            failures += 1
            lines.append(f"{alias:<14} failed: {exc.summary}")
            notes.extend(f"  {alias}: {issue['message']}" for issue in exc.report.get("issues", [])[1:])
            continue
        elapsed = time.perf_counter() - started
        kpis = evaluate(inst, rows)
        verdict = "validator not available"
        if validate is not None:
            errors = [f"{doc}: {e}" for doc, report in validate(out).items() for e in report.errors]
            verdict = "valid" if not errors else f"INVALID ({len(errors)} errors)"
            notes.extend(f"  {alias}: {e}" for e in errors[:5])
            failures += bool(errors)
        lines.append(f"{alias:<14} shortage {kpis['total_shortage']:>5}/{kpis['total_demand']:<6} "
                     f"priority {kpis['priority_cost']:>7}   unassigned {kpis['unassigned']:>3}   "
                     f"{elapsed:6.1f}s   {_shown(out / 'result.json')}   {verdict}")

    print(f"\n{inst.problem_id} ({len(inst.employees)} employees, {inst.days[0]}..{inst.days[-1]}, "
          f"{len(inst.fixed)} of {len(inst.employees) * len(inst.days)} employee-days fixed)")
    for line in lines:
        print(line)
    for note in notes:
        print(note)
    return 1 if failures else 0

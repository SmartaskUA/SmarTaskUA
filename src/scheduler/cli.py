from __future__ import annotations

import argparse
import ast
import csv
import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .export_utils import (
    build_export_filename as _build_export_filename,
    default_export_dir as _default_export_dir,
    export_table_to_csv as _export_table_to_csv,
    is_table as _is_table,
)

from .layout_generator import build_team_layout_employees, write_json_file


def _bootstrap_import_paths() -> None:
    current_file = Path(__file__).resolve()
    scheduler_dir = current_file.parent
    src_dir = scheduler_dir.parent
    repo_root = src_dir.parent

    for candidate in (repo_root, src_dir, scheduler_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_import_paths()


def _get_task_manager():
    try:
        from .TaskManager import TaskManager
    except ImportError:  # pragma: no cover - direct execution fallback
        from TaskManager import TaskManager

    return TaskManager()


_HEURISTIC_SISQUAL_ALGORITHMS = {
    "Hybrid_Heuristic_Sisqual_Levels_Included",
    "Hybrid_Heuristic_Sisqual_2",
    "Hybrid_Heuristic_Sisqual_3",
    "Hybrid_Heuristic_Sisqual_No_Levels_Included",
}

_RAW_CSV_INPUT_ALGORITHMS = {
    "Hybrid_Heuristic",
    "Heuristica1",
    "Heuristica_Half_Intervals",
    "linear programming 2",
    "ILP_3",
    "ILP_3_Half_Intervals",
    "ILP_4",
    "ILP_4_Half_Intervals",
    "COP_1",
    "COP_1_Half_Intervals",
    "COP_2",
    "COP_2_Half_Intervals",
    "Swap",
    "R2_Heuristic",
    "Puzzle_Heuristic",
}


def _load_file_value(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    return path.read_text(encoding="utf-8")


def _load_csv_rows(path: Path) -> List[List[str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def _parse_value(raw_value: str) -> Any:
    candidate = raw_value.strip()

    if candidate.startswith("@"):
        return _load_file_value(Path(candidate[1:]).expanduser())

    path_candidate = Path(candidate).expanduser()
    if path_candidate.exists() and path_candidate.is_file():
        return _load_file_value(path_candidate)

    lowered = candidate.lower()
    if lowered == "none":
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(candidate)
        except Exception:
            pass

    return candidate


def _parse_key_value_pairs(items: Iterable[str]) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Expected KEY=VALUE, got: {item!r}")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty key in: {item!r}")
        parsed[key] = _parse_value(raw_value)
    return parsed


def _parse_algorithm_key_value_pairs(items: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    parsed: Dict[str, Dict[str, Any]] = {}
    for item in items:
        if "=" not in item or "." not in item:
            raise ValueError(f"Expected ALGORITHM.KEY=VALUE, got: {item!r}")
        left_side, raw_value = item.split("=", 1)
        algorithm_name, key = left_side.split(".", 1)
        algorithm_name = algorithm_name.strip()
        key = key.strip()
        if not algorithm_name or not key:
            raise ValueError(f"Invalid ALGORITHM.KEY=VALUE pair: {item!r}")
        parsed.setdefault(algorithm_name, {})[key] = _parse_value(raw_value)
    return parsed


def _load_config_file(path: str | None) -> tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    if not path:
        return {}, {}

    config_path = Path(path).expanduser()
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    if not isinstance(config, dict):
        raise ValueError("Configuration file must contain a JSON object.")

    if "defaults" in config or "algorithms" in config:
        defaults = config.get("defaults", {})
        algorithms = config.get("algorithms", {})
    else:
        defaults = config
        algorithms = {}

    if not isinstance(defaults, dict):
        raise ValueError("config.defaults must be a JSON object.")
    if not isinstance(algorithms, dict):
        raise ValueError("config.algorithms must be a JSON object.")

    normalized_algorithms: Dict[str, Dict[str, Any]] = {}
    for algorithm_name, algorithm_config in algorithms.items():
        if not isinstance(algorithm_config, dict):
            raise ValueError(f"Config for algorithm {algorithm_name!r} must be a JSON object.")
        normalized_algorithms[str(algorithm_name)] = algorithm_config

    return defaults, normalized_algorithms


def _resolve_problem_path(problem_path: str | None) -> str | None:
    if not problem_path:
        return None

    path = Path(problem_path).expanduser().resolve()
    if path.is_dir():
        candidate = path / "problem.json"
        if candidate.exists():
            return str(candidate)
    return str(path)


def _normalize_day_order_mode(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        normalized_list = []
        for item in value:
            normalized_list.append(int(item) if isinstance(item, str) and item.strip().isdigit() else item)
        return normalized_list

    if isinstance(value, str):
        if "," in value:
            parts = [part.strip() for part in value.split(",") if part.strip()]
            if len(parts) > 1:
                return [int(part) for part in parts]
        if value.strip().isdigit():
            return int(value.strip())

    return value


def _apply_common_normalizations(algorithm_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(kwargs)
    normalized["problem_path"] = _resolve_problem_path(normalized.get("problem_path"))
    normalized["day_order_mode"] = _normalize_day_order_mode(normalized.get("day_order_mode"))

    if algorithm_name in _HEURISTIC_SISQUAL_ALGORITHMS:
        day_order_mode = normalized.get("day_order_mode")
        if isinstance(day_order_mode, int):
            normalized["day_order_mode"] = [day_order_mode]

    return normalized


def _load_algorithm_inputs(algorithm_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    loaded = dict(kwargs)

    for key in ("vacations", "minimuns"):
        value = loaded.get(key)
        if isinstance(value, str):
            path = Path(value).expanduser()
            if algorithm_name in _RAW_CSV_INPUT_ALGORITHMS:
                loaded[key] = _load_csv_rows(path)
            else:
                loaded[key] = _parse_value(value)

    employees_value = loaded.get("employees")
    if isinstance(employees_value, str):
        loaded["employees"] = _parse_value(employees_value)

    return loaded


def _filter_kwargs(function: Any, kwargs: Mapping[str, Any]) -> Dict[str, Any]:
    signature = inspect.signature(function)
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
        return dict(kwargs)
    return {name: value for name, value in kwargs.items() if name in signature.parameters}


def _summarize_result(result: Any) -> str:
    if isinstance(result, dict):
        keys = ", ".join(sorted(str(key) for key in result.keys())[:8])
        return f"dict(keys=[{keys}])"

    if isinstance(result, list):
        if result and all(isinstance(row, list) for row in result):
            column_count = len(result[0]) if result[0] else 0
            return f"table(rows={len(result)}, columns={column_count})"
        return f"list(len={len(result)})"

    if isinstance(result, tuple):
        return f"tuple(len={len(result)})"

    return type(result).__name__


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scheduler",
        description="Run any scheduler algorithm registered in TaskManager.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available algorithms")
    list_parser.add_argument("--json", action="store_true", help="Print the registry as JSON")

    generate_parser = subparsers.add_parser(
        "generate-employees",
        help="Generate a team-layout employees file that can be fed back into the solver",
    )
    generate_parser.add_argument("--layout", required=True, help="Layout like A=6,B=6,AB=6")
    generate_parser.add_argument("--output", required=True, help="Output JSON file")
    # generate_parser.add_argument("--prefix", default="Employee", help="Employee name prefix")
    # generate_parser.add_argument("--contract-type", default="fullTime_8h", help="Contract type to write")
    generate_parser.add_argument(
        "--wrap-problem",
        action="store_true",
        help="Wrap output as {'employees': {'model': 'team', 'simple': [...]}}",
    )
    generate_parser.add_argument("--json", action="store_true", help="Print the generated payload as JSON")

    run_parser = subparsers.add_parser("run", help="Run one or more algorithms")
    run_parser.add_argument("--algorithm", action="append", default=[], help="Algorithm name to run. Repeatable.")
    # run_parser.add_argument("--all", action="store_true", help="Run every registered algorithm")
    # run_parser.add_argument("--config", help="JSON file with defaults and per-algorithm overrides")
    run_parser.add_argument("--param", action="append", default=[], help="Shared KEY=VALUE pair passed to the solver. Repeatable.")
    # run_parser.add_argument("--algo-param", action="append", default=[], help="Per-algorithm ALGORITHM.KEY=VALUE override. Repeatable.")
    run_parser.add_argument("--problem-path", help="Problem bundle directory or problem.json file")
    run_parser.add_argument("--max-time", type=float, help="Maximum solver time in minutes")
    run_parser.add_argument("--restarts", type=int, help="Number of restarts for restart-based algorithms")
    run_parser.add_argument("--runs-grasp", type=int, help="Number of GRASP runs for Puzzle_Heuristic")
    run_parser.add_argument("--day-order-mode", help="Day-order mode; use a single value or comma-separated list")
    run_parser.add_argument("--task-id", default="cli", help="Task identifier used by some algorithms")
    run_parser.add_argument("--title", default="CLI", help="Title/roster code used by some algorithms")
    run_parser.add_argument("--vacations", "--vacation", dest="vacations", help="Vacations input as JSON, @file, or direct value")
    run_parser.add_argument("--minimuns", help="Minimums input as JSON, @file, or direct value")
    run_parser.add_argument("--employees", help="Employees input as JSON, @file, or direct value")
    run_parser.add_argument("--rules", help="Rules input as JSON, @file, or direct value")
    run_parser.add_argument("--year", type=int, help="Year parameter for year-based algorithms")
    run_parser.add_argument("--shifts", type=int, help="Shifts parameter for shift-based algorithms")
    run_parser.add_argument("--hours", type=int, help="Hours parameter for hour-based algorithms")
    run_parser.add_argument("--solver", default="CBC", help="Solver name for algorithms that support it")
    run_parser.add_argument("--continue-on-error", action="store_true", help="Continue running other algorithms if one fails")
    run_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    run_parser.add_argument("--output", help="Write the aggregated result JSON to this file")

    param_parser = subparsers.add_parser(
        "param",
        help="List the parameters accepted by one or all registered algorithms",
    )
    param_parser.add_argument(
        "--algorithm",
        help="Show parameters for this algorithm only. Omit to list every registered algorithm.",
    )
    param_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    
    return parser


def _algorithm_parameters(algorithm: Any) -> List[Dict[str, Any]]:
    """Introspect one algorithm callable and return its declared parameters,
    in declaration order, each as {name, cli_name, required, default}."""
    signature = inspect.signature(algorithm)
    parameters: List[Dict[str, Any]] = []

    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        has_default = parameter.default is not inspect.Parameter.empty
        parameters.append(
            {
                "name": name,
                "cli_name": name.replace("_", "-"),
                "required": not has_default,
                "default": parameter.default if has_default else None,
            }
        )

    return parameters


def _accepts_arbitrary_kwargs(algorithm: Any) -> bool:
    signature = inspect.signature(algorithm)
    return any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def _build_shared_kwargs(args: argparse.Namespace, defaults: Mapping[str, Any]) -> Dict[str, Any]:
    shared_kwargs: Dict[str, Any] = dict(defaults)

    cli_shared = {
        "problem_path": args.problem_path,
        "maxTime": args.max_time,
        "restarts": args.restarts,
        "runs_grasp": args.runs_grasp,
        "day_order_mode": args.day_order_mode,
        "task_id": args.task_id,
        "title": args.title,
        "vacations": args.vacations,
        "minimuns": args.minimuns,
        "employees": args.employees,
        "rules": args.rules,
        "year": args.year,
        "shifts": args.shifts,
        "hours": args.hours,
        "solver": args.solver,
    }

    for key, value in cli_shared.items():
        if value is None:
            continue
        if key in {"employees", "rules", "day_order_mode"} and isinstance(value, str):
            shared_kwargs[key] = _parse_value(value)
        else:
            shared_kwargs[key] = value

    shared_kwargs.update(_parse_key_value_pairs(args.param))
    return shared_kwargs


def _build_algorithm_overrides(args: argparse.Namespace, config_overrides: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    overrides = {name: dict(values) for name, values in config_overrides.items()}
    for algorithm_name, value in _parse_algorithm_key_value_pairs([]).items():
        overrides.setdefault(algorithm_name, {}).update(value)
    return overrides


def _print_human_summary(results: List[Dict[str, Any]]) -> None:
    for entry in results:
        algorithm_name = entry["algorithm"]
        elapsed = entry["elapsed_seconds"]
        if entry["ok"]:
            print(f"[{algorithm_name}] ok in {elapsed:.2f}s -> {entry['summary']}")
        else:
            print(f"[{algorithm_name}] failed in {elapsed:.2f}s -> {entry['error']}")


def run_selected_algorithms(args: argparse.Namespace) -> List[Dict[str, Any]]:
    task_manager = _get_task_manager()
    registry = task_manager.algorithms


    selected_algorithms = []
    for item in args.algorithm:
        selected_algorithms.extend(part.strip() for part in item.split(",") if part.strip())

    if not selected_algorithms:
        raise ValueError("Select at least one algorithm with --algorithm or use --all.")

    defaults, config_overrides = _load_config_file(None)
    shared_kwargs = _build_shared_kwargs(args, defaults)
    algorithm_overrides = _build_algorithm_overrides(args, config_overrides)

    results: List[Dict[str, Any]] = []

    for algorithm_name in selected_algorithms:
        if algorithm_name not in registry:
            available = ", ".join(sorted(registry.keys()))
            raise ValueError(f"Algorithm {algorithm_name!r} not found. Available algorithms: {available}")

        algorithm = registry[algorithm_name]
        kwargs = dict(shared_kwargs)
        kwargs.update(algorithm_overrides.get(algorithm_name, {}))
        kwargs = _load_algorithm_inputs(algorithm_name, kwargs)
        kwargs = _apply_common_normalizations(algorithm_name, kwargs)
        call_kwargs = _filter_kwargs(algorithm, kwargs)

        start_time = time.perf_counter()
        try:
            result = algorithm(**call_kwargs)
            elapsed_seconds = time.perf_counter() - start_time

            csv_export_path = None
            if _is_table(result): 
                try:
                    export_dir = Path(args.export_dir) if getattr(args, "export_dir", None) else _default_export_dir()
                    filename = _build_export_filename(algorithm_name, args.task_id)
                    csv_export_path = str(_export_table_to_csv(result, export_dir, filename))
                    print(f"[{algorithm_name}] Schedule exported to CSV: {csv_export_path}")
                except Exception as export_error:
                    print(f"[{algorithm_name}] CSV export failed: {export_error}")

            results.append(
                {
                    "algorithm": algorithm_name,
                    "ok": True,
                    "elapsed_seconds": elapsed_seconds,
                    "summary": _summarize_result(result),
                    "result": result,
                    "csv_export_path": csv_export_path,
                }
            )
        except Exception as exc:
            elapsed_seconds = time.perf_counter() - start_time
            results.append(
                {
                    "algorithm": algorithm_name,
                    "ok": False,
                    "elapsed_seconds": elapsed_seconds,
                    "error": repr(exc),
                }
            )
            if not args.continue_on_error:
                raise

    return results


def _json_safe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [dict(entry) for entry in results]


def main(argv: List[str] | None = None) -> int:
    parser = _make_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        # Chama o task manager via import para obter a lista de algoritmos registrados
        task_manager = _get_task_manager()
        algorithm_names = list(task_manager.algorithms.keys())
        if args.json:
            print(json.dumps(algorithm_names, indent=2))
        else:
            for algorithm_name in algorithm_names:
                print(algorithm_name)
        return 0

    if args.command == "generate-employees":
        payload = build_team_layout_employees(
            layout_spec=args.layout,
            # prefix=args.prefix,
            # contract_type=args.contract_type,
            include_wrapper=args.wrap_problem,
        )
        write_json_file(args.output, payload)
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"Generated employees file: {Path(args.output).expanduser()}")
        return 0

    if args.command == "param":
        task_manager = _get_task_manager()
        registry = task_manager.algorithms
    
        if args.algorithm:
            if args.algorithm not in registry:
                available = ", ".join(sorted(registry.keys()))
                raise ValueError(f"Algorithm {args.algorithm!r} not found. Available algorithms: {available}")
            target_algorithms = {args.algorithm: registry[args.algorithm]}
        else:
            target_algorithms = registry
    
        report = {
            name: {
                "parameters": _algorithm_parameters(algorithm),
                "accepts_extra_kwargs": _accepts_arbitrary_kwargs(algorithm),
            }
            for name, algorithm in target_algorithms.items()
        }
    
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            for name, info in report.items():
                if args.algorithm is None:
                    print(f"[{name}]")
                for parameter in info["parameters"]:
                    print(parameter["cli_name"])
                if info["accepts_extra_kwargs"]:
                    print("... (accepts additional keyword arguments)")
                if args.algorithm is None:
                    print()
    
        return 0

    results = run_selected_algorithms(args)

    if args.json:
        print(json.dumps(_json_safe_results(results), indent=2, default=str))
    else:
        _print_human_summary(results)

    if args.output:
        output_path = Path(args.output).expanduser()
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(_json_safe_results(results), handle, indent=2, default=str)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
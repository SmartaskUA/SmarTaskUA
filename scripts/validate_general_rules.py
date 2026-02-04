#!/usr/bin/env python3
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

# Capabilities for "general" algorithms.
GENERAL_CAPABILITIES = {
    "ilp_general": {
        "team_eligibility",
        "max_consecutive_days",
        "max_special_days",
        "total_workdays",
        "no_earlier_shift_next_day",
        "vacation_block",
        "min_coverage",
        "ideal_coverage",
    },
    "csp_general": {
        "team_eligibility",
        "max_consecutive_days",
        "max_special_days",
        "total_workdays",
        "no_earlier_shift_next_day",
        "vacation_block",
        "min_coverage",
        "ideal_coverage",
    },
    "heuristic_general": {
        "team_eligibility",
        "max_consecutive_days",
        "max_special_days",
        "total_workdays",
        "no_earlier_shift_next_day",
        "vacation_block",
        "min_coverage",
        "ideal_coverage",
    },
}


def _load_problem_json(path: Path):
    if not path.is_file():
        print(f"[ERROR] problem.json not found at: {path}")
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[ERROR] Failed to parse problem.json: {exc}")
        return None


def _collect_rule_types(problem_obj):
    types = []
    if isinstance(problem_obj, dict):
        constraints = problem_obj.get("constraints", {})
        if isinstance(constraints, dict):
            for bucket in ("hard", "soft"):
                rules = constraints.get(bucket, [])
                if not isinstance(rules, list):
                    continue
                for r in rules:
                    if not isinstance(r, dict):
                        continue
                    if r.get("enabled", True) is False:
                        continue
                    rule_type = r.get("type") or r.get("id")
                    if rule_type:
                        types.append(str(rule_type))
    return sorted(set(types))


def main() -> int:
    problem_paths = [Path(p) for p in sys.argv[1:]]
    if not problem_paths:
        default_path = REPO_ROOT / "data" / "problems" / "SMARTASK_SIMPLE_2025" / "problem.json"
        problem_paths = [default_path]

    failed = False
    for problem_path in problem_paths:
        problem_obj = _load_problem_json(problem_path)
        if problem_obj is None:
            failed = True
            continue
        rule_types = _collect_rule_types(problem_obj)
        if not rule_types:
            print(f"[ERROR] No rule types found in {problem_path}")
            failed = True
            continue

        for algo, supported in GENERAL_CAPABILITIES.items():
            missing = [t for t in rule_types if t not in supported]
            if missing:
                failed = True
                print(f"[FAIL] {algo} missing support for: {', '.join(missing)} (from {problem_path})")
            else:
                print(f"[OK] {algo} supports all rule types in {problem_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

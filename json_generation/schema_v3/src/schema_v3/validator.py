#!/usr/bin/env python3
"""Validate a v3.0 scheduling problem (declarative or expanded), a solution, a
whole package, or a folder of packages.

Three validation layers, each in its own module, composed here:
  1. JSON Schema, against the form named by the instance's `form` field.
  2. Cross-references the schema cannot express (common.py, shared by both forms).
  3. Per-form conformance: declarative CSVs (validate_declarative.py),
     MathematicalDefinition7 for expanded (validate_expanded.py), and a solution
     against its expanded problem (validate_solution.py).

This file is the orchestrator + CLI only. It imports core and those layers; it
never imports transform (the decoupling invariant).

Usage:
    python3 validator.py problem.json            # one file (form-aware)
    python3 validator.py solution.json --against problem.expanded.json
    python3 validator.py examples/               # a folder -> every package
    python3 validator.py problem.json -v --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import CommonChecksMixin, Report
from validate_declarative import DeclarativeChecksMixin
from validate_expanded import ExpandedChecksMixin
from validate_solution import SolutionChecksMixin

# The domain (time maths, cell semantics) lives in core; the validation layers in
# their own modules. This file adds only the JSON Schema layer, form dispatch, the
# package/folder orchestration, and the CLI.

SCHEMA_FILES = {
    "declarative": "schema-v3-declarative.json",
    "expanded": "schema-v3-expanded.json",
    "solution": "schema-v3-solution.json",
}


class SchemaValidator(
    CommonChecksMixin,
    DeclarativeChecksMixin,
    ExpandedChecksMixin,
    SolutionChecksMixin,
):
    """Validates one file. The per-layer logic lives in the mixins above; this
    class holds the loaded state they read (`self.problem`/`base`/`against`/
    `report`), the JSON Schema layer, and the form dispatch."""

    def __init__(self, path: Path, against: Path | None = None):
        self.path = path
        self.base = path.parent
        # The expanded problem a solution is cross-checked against (form 'solution'
        # only). None means "auto-locate a sibling *.expanded.json".
        self.against = against
        self.report = Report()
        self.problem: dict = {}

    # -- layer 1 ---------------------------------------------------------
    def load(self) -> bool:
        try:
            self.problem = json.loads(self.path.read_text())
        except FileNotFoundError:
            self.report.error(f"file not found: {self.path}")
            return False
        except json.JSONDecodeError as exc:
            self.report.error(f"invalid JSON: {exc}")
            return False
        return True

    def validate_schema(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.report.warn("jsonschema not installed; skipped schema layer")
            return

        form = self.problem.get("form")
        if form not in SCHEMA_FILES:
            self.report.error(
                f"form must be one of {sorted(SCHEMA_FILES)}, got {form!r}"
            )
            return

        # this file: <root>/src/schema_v3/validator.py -> schemas at <root>/schemas
        schema_dir = Path(__file__).resolve().parents[2] / "schemas"
        try:
            # Each form schema is standalone, so it loads and validates on its own --
            # no registry, and no resolution order to get wrong.
            schema = json.loads((schema_dir / SCHEMA_FILES[form]).read_text())
        except FileNotFoundError as exc:
            self.report.warn(f"schema file not found ({exc}); skipped schema layer")
            return

        validator = Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(self.problem), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.path) or "(root)"
            self.report.error(f"schema: {where}: {err.message}")

    def run(self) -> Report:
        if not self.load():
            return self.report
        self.validate_schema()
        form = self.problem.get("form")
        if form in ("declarative", "expanded"):
            self.validate_common()
        if form == "declarative":
            self.validate_declarative()
        elif form == "expanded":
            self.validate_expanded()
        elif form == "solution":
            self.validate_solution()
        return self.report


# --------------------------------------------------------------------------
# public API: file, package, folder
# --------------------------------------------------------------------------

def validate(path: Path, against: Path | None = None) -> Report:
    """Validate a single file as its `form` dictates. The one entry the tests and
    other tools call in-process."""
    return SchemaValidator(path, against=against).run()


def _form_of(path: Path) -> str | None:
    """The `form` field of a JSON file, or None if it isn't a v3 form-bearing file."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return doc.get("form") if isinstance(doc, dict) else None


def _problem_id(path: Path, form: str) -> str | None:
    doc = json.loads(path.read_text())
    if form == "solution":
        return doc.get("problemId")
    return doc.get("metadata", {}).get("problemId")


def validate_package(directory: Path) -> dict[str, Report]:
    """Validate every form-bearing JSON in one directory as a package.

    Each file is validated for its own form (a solution auto-locates the sibling
    expanded here). Then the package-level cross-check that needs no transform:
    all present forms must name the same problem id. Returns {filename: Report},
    with a "(package)" entry only when the package-level check has something to say.
    """
    reports: dict[str, Report] = {}
    forms: dict[str, Path] = {}
    for jf in sorted(directory.glob("*.json")):
        form = _form_of(jf)
        if form in SCHEMA_FILES:
            reports[jf.name] = validate(jf)
            forms.setdefault(form, jf)

    if len(forms) >= 2:
        ids = {form: _problem_id(path, form) for form, path in forms.items()}
        distinct = {v for v in ids.values() if v is not None}
        pkg = Report()
        if len(distinct) > 1:
            pkg.error(
                f"the forms in {directory.name}/ name different problems: "
                + ", ".join(f"{form}={id!r}" for form, id in ids.items())
            )
        pkg.stats["forms"] = sorted(forms)
        pkg.stats["problemId"] = next(iter(distinct), None) if len(distinct) == 1 else dict(ids)
        reports["(package)"] = pkg
    return reports


def validate_tree(directory: Path) -> dict[str, dict[str, Report]]:
    """Group every form-bearing JSON under `directory` by its parent directory and
    validate each such directory as a package."""
    package_dirs = set()
    for jf in directory.rglob("*.json"):
        if _form_of(jf) in SCHEMA_FILES:
            package_dirs.add(jf.parent)
    out: dict[str, dict[str, Report]] = {}
    for d in sorted(package_dirs):
        label = str(d.relative_to(directory)) if d != directory else "."
        out[label] = validate_package(d)
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _report_dict(report: Report) -> dict:
    return {
        "valid": report.ok,
        "errors": report.errors,
        "warnings": report.warnings,
        "stats": report.stats,
    }


def _print_report(report: Report, label, verbose: bool) -> None:
    for w in report.warnings:
        print(f"WARN  {w}")
    for e in report.errors:
        print(f"ERROR {e}")
    if verbose and report.stats:
        print("stats")
        for k, v in report.stats.items():
            print(f"  {k:20s} {v}")
    if report.ok:
        print(f"VALID  {label}" + (f"  ({len(report.warnings)} warning(s))" if report.warnings else ""))
    else:
        print(f"INVALID  {label}  ({len(report.errors)} error(s))")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("problem", type=Path, help="a v3 JSON file, or a folder of packages")
    ap.add_argument("-v", "--verbose", action="store_true", help="print stats")
    ap.add_argument("-j", "--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--against",
        type=Path,
        help="expanded problem to cross-check a solution against "
        "(default: a sibling *.expanded.json)",
    )
    args = ap.parse_args()

    # -- folder mode: validate every package under the directory --
    if args.problem.is_dir():
        tree = validate_tree(args.problem)
        all_ok = all(rep.ok for pkg in tree.values() for rep in pkg.values())
        if args.json:
            print(json.dumps(
                {pkg: {name: _report_dict(rep) for name, rep in reps.items()}
                 for pkg, reps in tree.items()},
                indent=2,
            ))
            return 0 if all_ok else 1
        for pkg, reps in tree.items():
            print(f"\n=== {pkg} ===")
            for name, rep in reps.items():
                _print_report(rep, name, args.verbose)
        print(f"\n{'ALL VALID' if all_ok else 'SOME INVALID'} "
              f"({sum(len(r) for r in tree.values())} file(s) across {len(tree)} package(s))")
        return 0 if all_ok else 1

    # -- single-file mode --
    report = validate(args.problem, against=args.against)
    if args.json:
        print(json.dumps(_report_dict(report), indent=2))
        return 0 if report.ok else 1
    _print_report(report, args.problem, args.verbose)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

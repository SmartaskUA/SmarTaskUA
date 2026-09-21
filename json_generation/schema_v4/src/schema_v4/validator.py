"""Orchestrator and CLI.

Holds only the JSON Schema layer, form dispatch, package/folder orchestration and
the command line. Every per-form check lives in a mixin, so this file stays the
composition root and nothing else.

    PYTHONPATH=src python3 -m schema_v4.validator <file-or-folder> [-v] [-j] [--against P]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .common import CommonChecksMixin, Report
from .validate_declarative import DeclarativeChecksMixin
from .validate_result import ResultChecksMixin

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

SCHEMA_FILES = {
    "declarative": "schema-v4-declarative.json",
    "result": "schema-v4-result.json",
}


class SchemaValidator(CommonChecksMixin, DeclarativeChecksMixin, ResultChecksMixin):
    def __init__(self, path: Path, against: Path | None = None):
        self.path = Path(path)
        self.base = self.path.parent
        self.against = Path(against) if against else None
        self.problem: dict = {}
        self.form: str | None = None
        self.report = Report()

    # -- loading -----------------------------------------------------------

    def load(self) -> bool:
        try:
            with self.path.open(encoding="utf-8") as fh:
                self.problem = json.load(fh)
        except OSError as exc:
            self.report.error(f"cannot read {self.path.name}: {exc}")
            return False
        except ValueError as exc:
            self.report.error(f"{self.path.name} is not valid JSON: {exc}")
            return False
        if not isinstance(self.problem, dict):
            self.report.error(f"{self.path.name}: top level must be an object")
            return False
        self.form = _form_of_doc(self.problem)
        if self.form is None:
            self.report.error(
                f"{self.path.name}: cannot tell which form this is. A problem carries "
                f"form: \"declarative\"; a result carries an OutRosterTeamDays array."
            )
            return False
        return True

    # -- layer 1: JSON Schema ---------------------------------------------

    def validate_schema(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.report.warn("jsonschema is not installed, so the JSON Schema layer was "
                             "skipped; the cross-reference layers still ran "
                             "(pip install -r requirements.txt)")
            return
        schema_path = SCHEMA_DIR / SCHEMA_FILES[self.form]
        with schema_path.open(encoding="utf-8") as fh:
            schema = json.load(fh)
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(self.problem), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.path) or "(root)"
            self.report.error(f"schema: {where}: {err.message}")

    # -- dispatch ----------------------------------------------------------

    def run(self) -> Report:
        if not self.load():
            return self.report
        self.report.stats["form"] = self.form
        self.validate_schema()
        if self.form == "declarative":
            self.validate_common()
            self.validate_declarative()
        else:
            self.validate_result()
        return self.report


def _form_of_doc(doc: dict) -> str | None:
    if doc.get("form") == "declarative":
        return "declarative"
    if "OutRosterTeamDays" in doc:
        return "result"
    return None


def _form_of(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8") as fh:
            return _form_of_doc(json.load(fh))
    except (ValueError, OSError):
        return None


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------

def validate(path, against=None) -> Report:
    """Validate one file. Form-aware; a result is cross-checked against its problem."""
    return SchemaValidator(Path(path), against).run()


def validate_package(directory) -> dict[str, Report]:
    """Validate a directory as one package: its problem, its result, and their agreement."""
    directory = Path(directory)
    reports: dict[str, Report] = {}
    forms: dict[str, Path] = {}
    for path in sorted(directory.glob("*.json")):
        form = _form_of(path)
        if form is None:
            continue
        forms.setdefault(form, path)
        reports[path.name] = validate(path)

    package = Report()
    package.stats["forms"] = sorted(forms)
    if "declarative" in forms:
        with forms["declarative"].open(encoding="utf-8") as fh:
            package.stats["problemId"] = json.load(fh).get("metadata", {}).get("problemId")
    if "result" in forms and "declarative" not in forms:
        package.warn("a result sits here with no declarative problem to check it against")
    reports["(package)"] = package
    return reports


def validate_tree(directory) -> dict[str, dict[str, Report]]:
    """Validate every package under a directory."""
    directory = Path(directory)
    out: dict[str, dict[str, Report]] = {}
    for sub in sorted(p for p in directory.rglob("*") if p.is_dir()):
        if any(sub.glob("*.json")):
            out[str(sub.relative_to(directory))] = validate_package(sub)
    if any(directory.glob("*.json")):
        out["."] = validate_package(directory)
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print(label: str, report: Report, verbose: bool) -> None:
    mark = "OK  " if report.ok else "FAIL"
    print(f"{mark}  {label}")
    for e in report.errors:
        print(f"      ERROR  {e}")
    for w in report.warnings:
        print(f"      WARN   {w}")
    if verbose and report.stats:
        for k, v in report.stats.items():
            print(f"      .      {k}: {v}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m schema_v4.validator",
        description="Validate a v4.0 problem or result, a package directory, or a tree of them.")
    ap.add_argument("target", help="a .json file, or a directory")
    ap.add_argument("-v", "--verbose", action="store_true", help="also print stats")
    ap.add_argument("-j", "--json", action="store_true", help="machine-readable output")
    ap.add_argument("--against", help="the declarative problem to cross-check a result against")
    args = ap.parse_args(argv)

    target = Path(args.target)
    if not target.exists():
        print(f"no such file or directory: {target}", file=sys.stderr)
        return 1

    if target.is_file():
        results = {str(target): {target.name: validate(target, args.against)}}
    elif any(target.glob("*.json")):
        results = {str(target): validate_package(target)}
    else:
        results = {str(target / k): v for k, v in validate_tree(target).items()}

    if not results:
        print(f"no JSON documents found under {target}")
        return 1

    if args.json:
        print(json.dumps(
            {pkg: {name: {"ok": r.ok, "errors": r.errors, "warnings": r.warnings,
                          "stats": r.stats}
                   for name, r in reports.items()}
             for pkg, reports in results.items()},
            indent=2, ensure_ascii=False))
    else:
        for pkg, reports in results.items():
            if len(results) > 1:
                print(f"\n{pkg}")
            for name, report in reports.items():
                _print(name, report, args.verbose)

    failed = any(not r.ok for reports in results.values() for r in reports.values())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

"""SISQUAL's dialect -> canonical v4.0.

SISQUAL's exporter stamps ``schemaVersion: "3.0"`` on a payload that is neither
v3.0 nor canonical v4.0: three keys are misspelled, three enums are capitalised,
open-ended dates use a sentinel, the competency dimension is named in Portuguese
in one block and English in two others, and the demand catalogue their own spec
defines is not exported at all.

This module converts a raw bundle directory into a canonical package and reports
every change it made. That report is the evidence behind docs/next_meeting.md -
run it, and the output is the list to hand Sisqual.

    PYTHONPATH=src python3 -m schema_v4.sisqual_adapt <raw-bundle-dir> -o <out> [--stats]

What it deliberately does NOT do: invent data. A bundle whose contracts list is
empty while employees reference contracts comes out the other side still broken,
and the validator says so. An adapter that papers over that would hide the defect
we most need Sisqual to see.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from . import core

#: Portuguese dimension names used in employees[].competencyAssignments, against
#: the English ones used in priorityHierachy and the demand CSVs. Only tableValue
#: joins across the three, so the mapping is stated here rather than guessed.
TABLE_NAME_ALIASES = {
    "Equipa": "Team",
    "Piso": "Responsibility",
}

#: The sentinel SISQUAL writes for an open-ended assignment.
OPEN_ENDED = "9999-12-31"

#: Canonical CSV names. The raw names carry a generation timestamp that does not
#: match the JSON's own, so deriving one from the other is a trap; renaming to
#: fixed names removes it.
CSV_NAMES = {
    "dataFileDays": "days_demand.csv",
    "dataFilePeriods": "periods_demand.csv",
    "dataFileShifts": "shifts_demand.csv",
}
SCHEDULE_INPUT_NAME = "schedule_input.csv"


class AdaptError(Exception):
    """The input is not a bundle this adapter can read."""


class Fixes:
    """An ordered tally of what the adapter changed."""

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._order: list[str] = []

    def add(self, label: str, n: int = 1) -> None:
        if n <= 0:
            return
        if label not in self._counts:
            self._order.append(label)
        self._counts[label] += n

    def __iter__(self):
        for label in self._order:
            yield label, self._counts[label]

    def __len__(self) -> int:
        return len(self._order)

    def render(self) -> str:
        if not self._order:
            return "  (nothing to fix - this bundle is already canonical)"
        width = max(len(l) for l in self._order)
        return "\n".join(
            f"  {label:<{width}}  {'x' + str(n) if n > 1 else ''}".rstrip()
            for label, n in self)


# --------------------------------------------------------------------------
# locating the bundle
# --------------------------------------------------------------------------

def find_problem(directory: Path) -> Path:
    """The one JSON in `directory` that looks like a SISQUAL problem export."""
    candidates = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            with path.open(encoding="utf-8-sig") as fh:
                doc = json.load(fh)
        except (ValueError, OSError):
            continue
        if isinstance(doc, dict) and doc.get("form") == "declarative":
            candidates.append(path)
    if not candidates:
        raise AdaptError(f"no declarative problem JSON found in {directory}")
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        raise AdaptError(f"{directory} holds several problem JSONs ({names}); name one directly")
    return candidates[0]


# --------------------------------------------------------------------------
# the JSON
# --------------------------------------------------------------------------

def adapt_problem(raw: dict, fixes: Fixes) -> dict:
    """Return a canonical v4.0 problem document."""
    out: dict = {}

    version = raw.get("schemaVersion")
    if version != "4.0":
        fixes.add(f'schemaVersion "{version}" -> "4.0"')
    out["schemaVersion"] = "4.0"
    out["form"] = "declarative"
    out["problemType"] = raw.get("problemType", "employee_scheduling")

    out["metadata"] = _metadata(raw.get("metadata", {}), fixes)
    out["timeGrid"] = dict(raw.get("timeGrid", {}))
    out["temporalScope"] = dict(raw.get("temporalScope", {}))

    calendar = _calendar(raw.get("calendar", {}), fixes)
    if calendar:
        out["calendar"] = calendar

    out["contracts"] = {"definitions": [dict(c) for c in
                                        raw.get("contracts", {}).get("definitions", [])]}
    out["employees"] = {"list": [_employee(e, fixes)
                                 for e in raw.get("employees", {}).get("list", [])]}

    priority = [_priority(e, fixes) for e in
                (raw.get("priorityHierarchy") or raw.get("priorityHierachy") or [])]
    if "priorityHierachy" in raw:
        fixes.add("priorityHierachy -> priorityHierarchy")

    out["demand"] = _demand(raw.get("demand", {}), out["employees"]["list"], priority, fixes)
    out["scheduleInput"] = _schedule_input(raw.get("scheduleInput", {}), fixes)

    if priority:
        out["priorityHierarchy"] = priority
    if "constraints" in raw:
        out["constraints"] = raw["constraints"]
    return out


def _metadata(raw: dict, fixes: Fixes) -> dict:
    md = {k: v for k, v in raw.items() if k in ("problemId", "createdAt", "description", "source")}
    problem_id = md.get("problemId", "")
    if problem_id and "rosterCode" not in raw:
        # SISQUAL's problemId is <RosterCode>_<Month>_<Year>; the result payload
        # carries RosterCode alone, so make the join explicit rather than
        # re-splitting the string in three places later.
        md["rosterCode"] = problem_id.split("_", 1)[0]
        fixes.add(f'metadata.rosterCode "{md["rosterCode"]}" derived from problemId')
    elif "rosterCode" in raw:
        md["rosterCode"] = raw["rosterCode"]
    return md


def _calendar(raw: dict, fixes: Fixes) -> dict:
    if not raw:
        return {}
    out: dict = {}
    week_start = raw.get("weekStart")
    if isinstance(week_start, str):
        if week_start != week_start.lower():
            fixes.add(f'calendar.weekStart "{week_start}" -> "{week_start.lower()}"')
        out["weekStart"] = week_start.lower()

    holidays = raw.get("holidays")
    if holidays is None and "inpUAHolidaysCollection" in raw:
        holidays = raw["inpUAHolidaysCollection"]
        fixes.add("calendar.inpUAHolidaysCollection -> calendar.holidays")
    if holidays is not None:
        out["holidays"] = [dict(h) for h in holidays]
    return out


def _date_or_null(value, fixes: Fixes, label: str):
    if value == OPEN_ENDED:
        fixes.add(f'{label} end "{OPEN_ENDED}" -> null')
        return None
    return value


def _employee(raw: dict, fixes: Fixes) -> dict:
    out = {"id": str(raw.get("id", ""))}
    if "name" in raw:
        out["name"] = raw["name"]

    contracts = raw.get("contractAssignments")
    if contracts is None and "contractAssigments" in raw:
        contracts = raw["contractAssigments"]
        fixes.add("employees[].contractAssigments -> contractAssignments")
    out["contractAssignments"] = [
        {"contractType": a.get("contractType"),
         "start": a.get("start"),
         "end": _date_or_null(a.get("end"), fixes, "contractAssignments")}
        for a in (contracts or [])
    ]

    out["competencyAssignments"] = [
        {"tableName": _alias(a.get("tableName"), fixes),
         "tableValue": a.get("tableValue"),
         "level": a.get("level"),
         "start": a.get("start"),
         "end": _date_or_null(a.get("end"), fixes, "competencyAssignments")}
        for a in raw.get("competencyAssignments", [])
    ]
    return out


def _alias(name, fixes: Fixes):
    if name in TABLE_NAME_ALIASES:
        canonical = TABLE_NAME_ALIASES[name]
        fixes.add(f'tableName "{name}" -> "{canonical}"')
        return canonical
    return name


def _priority(raw: dict, fixes: Fixes) -> dict:
    out = dict(raw)
    out["tableName"] = _alias(raw.get("tableName"), fixes)
    return out


def _schedule_input(raw: dict, fixes: Fixes) -> dict:
    codes = {}
    for code, entry in raw.get("dayOffCodes", {}).items():
        kind = entry.get("kind")
        if isinstance(kind, str) and kind != kind.lower():
            fixes.add(f'dayOffCodes[].kind "{kind}" -> "{kind.lower()}"')
            kind = kind.lower()
        codes[code] = {k: v for k, v in
                       (("kind", kind), ("name", entry.get("name")),
                        ("description", entry.get("description")))
                       if v is not None}
    return {"dataFile": SCHEDULE_INPUT_NAME, "dayOffCodes": codes}


def _demand(raw: dict, employees: list[dict], priority: list[dict], fixes: Fixes) -> dict:
    out = {"dimensions": []}
    for key, canonical in CSV_NAMES.items():
        if key in raw and raw[key] != canonical:
            fixes.add(f"demand.{key} -> {canonical}")
        out[key] = canonical
    return out


def synthesise_dimensions(problem: dict, demand_rows: list, fixes: Fixes) -> None:
    """Fill demand.dimensions[] from every place a coordinate appears.

    SISQUAL exports no catalogue - their own InpTaskAbilityCollection and
    InResponsabilityCollection never reach the bundle - so the set has to be
    recovered from the three places that use it.
    """
    pairs: set[tuple[str, str]] = set()
    for e in problem.get("employees", {}).get("list", []):
        for a in e.get("competencyAssignments", []):
            if a.get("tableName") and a.get("tableValue"):
                pairs.add((a["tableName"], a["tableValue"]))
    for e in problem.get("priorityHierarchy", []):
        if e.get("tableName") and e.get("tableValue"):
            pairs.add((e["tableName"], e["tableValue"]))
    for row in demand_rows:
        if row.table_name and row.table_value:
            pairs.add((row.table_name, row.table_value))

    problem["demand"]["dimensions"] = [
        {"tableName": tn, "tableValue": tv} for tn, tv in sorted(pairs)
    ]
    if pairs:
        fixes.add(f"synthesised demand.dimensions[] from {len(pairs)} coordinate(s)")
    else:
        fixes.add("demand.dimensions[] is EMPTY - this bundle names no coordinate anywhere")


# --------------------------------------------------------------------------
# the CSVs
# --------------------------------------------------------------------------

def copy_csv(src: Path, dst: Path, fixes: Fixes, normalise_cells: bool = False) -> None:
    """Rewrite a CSV as plain UTF-8 with LF endings, optionally de-localising numbers."""
    raw = src.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    had_crlf = "\r\n" in text
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if normalise_cells:
        import csv as _csv
        import io as _io
        rows = list(_csv.reader(_io.StringIO(text)))
        changed = 0
        for r in rows[1:]:
            for i, cell in enumerate(r[1:], start=1):
                if "," in cell:
                    value = core.try_number(cell)
                    if value is not None:
                        r[i] = core.format_number(value)
                        changed += 1
        if changed:
            fixes.add(f"{dst.name}: decimal comma -> dot", changed)
        buf = _io.StringIO()
        _csv.writer(buf, lineterminator="\n").writerows(rows)
        text = buf.getvalue()

    if had_bom:
        fixes.add("CSV: stripped UTF-8 BOM")
    if had_crlf:
        fixes.add("CSV: CRLF -> LF")
    dst.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# the whole bundle
# --------------------------------------------------------------------------

def adapt(bundle: Path, out_dir: Path, schedules: Path | None = None) -> tuple[dict, Fixes]:
    """Convert a raw SISQUAL bundle into a canonical package. Returns (problem, fixes)."""
    bundle = Path(bundle)
    source = bundle if bundle.is_file() else find_problem(bundle)
    base = source.parent
    with source.open(encoding="utf-8-sig") as fh:
        raw = json.load(fh)

    fixes = Fixes()
    problem = adapt_problem(raw, fixes)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # demand CSVs, then the dimensions they imply
    all_rows = []
    for grain, key in (("days", "dataFileDays"), ("periods", "dataFilePeriods"),
                       ("shifts", "dataFileShifts")):
        src_name = raw.get("demand", {}).get(key)
        if not src_name:
            raise AdaptError(f"the bundle's demand block has no {key}")
        src = base / src_name
        if not src.is_file():
            raise AdaptError(f"demand.{key} points at {src_name}, which is not beside the JSON")
        copy_csv(src, out_dir / CSV_NAMES[key], fixes)
        _, rows, _ = core.read_demand(out_dir / CSV_NAMES[key], grain)
        all_rows.extend(rows)

    for row in all_rows:
        if row.table_name in TABLE_NAME_ALIASES:
            raise AdaptError(
                f"a demand CSV uses the Portuguese dimension name {row.table_name!r}; the "
                f"alias table assumed only employees[] did. Update TABLE_NAME_ALIASES.")

    synthesise_dimensions(problem, all_rows, fixes)

    # schedule_input.csv
    si_name = raw.get("scheduleInput", {}).get("dataFile")
    if not si_name:
        raise AdaptError("the bundle's scheduleInput block has no dataFile")
    src = base / si_name
    if not src.is_file():
        raise AdaptError(f"scheduleInput.dataFile points at {si_name}, which is not beside the JSON")
    if si_name != SCHEDULE_INPUT_NAME:
        fixes.add(f"scheduleInput.dataFile -> {SCHEDULE_INPUT_NAME}")
    copy_csv(src, out_dir / SCHEDULE_INPUT_NAME, fixes, normalise_cells=True)

    # the optional ScheduleCode catalogue
    if schedules:
        schedules = Path(schedules)
        shutil.copyfile(schedules, out_dir / schedules.name)
        problem["schedules"] = {"dataFile": schedules.name}
        fixes.add(f"attached the ScheduleCode catalogue ({schedules.name})")

    with (out_dir / "problem.json").open("w", encoding="utf-8") as fh:
        json.dump(problem, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return problem, fixes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m schema_v4.sisqual_adapt",
        description="Convert a raw SISQUAL bundle into a canonical v4.0 package, "
                    "reporting every change made.")
    ap.add_argument("bundle", help="the raw bundle directory (or its problem JSON)")
    ap.add_argument("-o", "--output", required=True, help="directory to write the package into")
    ap.add_argument("--schedules", help="a ScheduleCode catalogue CSV to attach")
    ap.add_argument("--stats", action="store_true", help="also print a short summary")
    args = ap.parse_args(argv)

    try:
        problem, fixes = adapt(Path(args.bundle), Path(args.output),
                               Path(args.schedules) if args.schedules else None)
    except AdaptError as exc:
        print(f"cannot adapt: {exc}", file=sys.stderr)
        return 1

    print(f"{args.bundle} -> {args.output}")
    print(fixes.render())
    if args.stats:
        print(f"\n  {len(problem['employees']['list'])} employees, "
              f"{len(problem['contracts']['definitions'])} contracts, "
              f"{len(problem['demand']['dimensions'])} dimensions, "
              f"{len(problem.get('priorityHierarchy', []))} priority ranks, "
              f"{len(fixes)} distinct fixes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Conformance suite for schema v3.0.

Checks the schemas compile, the examples validate in both forms, the transformer
preserves demand, and the rules from MathematicalDefinition7 that a JSON Schema
cannot express actually hold: H_wd within T_d, D_wk vs U_wk, n_wk >= 0, and the
competence-level polarity.

    python3 tests/test_v3_conformance.py
"""
import csv, json, shutil, subprocess, sys, tempfile
from pathlib import Path

V3 = Path(__file__).resolve().parent.parent
SRC = V3 / "src" / "schema_v3"          # the Python package
SCHEMAS = V3 / "schemas"                # the three schema JSONs
PY = sys.executable
sys.path.insert(0, str(SRC))            # so `import core` finds the package modules

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not cond else ""))


def run_validator(path):
    r = subprocess.run([PY, str(SRC / "validator.py"), str(path), "--json"],
                       capture_output=True, text=True)
    return json.loads(r.stdout)


# 1. schemas compile + refs resolve
from jsonschema import Draft202012Validator
files = ["schema-v3-declarative.json", "schema-v3-expanded.json", "schema-v3-solution.json"]
docs = {}
ok = True
for f in files:
    try:
        d = json.loads((SCHEMAS / f).read_text())
        Draft202012Validator.check_schema(d)
        docs[f] = d
    except Exception as e:
        ok = False
        print("   ", f, e)
check("1. all 3 schemas compile (Draft 2020-12)", ok)

# Each schema is standalone; no registry needed.
check("1c. no schema references another file",
      not any("common.json" in json.dumps(d) for d in docs.values()))

# 2. validator on all 4 example bundles
bundles = {
    "sisqual declarative": V3 / "examples/sisqual_example/problem.json",
    "sisqual expanded": V3 / "examples/sisqual_example/problem.expanded.json",
    "timeconstr declarative": V3 / "examples/time_constraints_example/problem.json",
    "timeconstr expanded": V3 / "examples/time_constraints_example/problem.expanded.json",
}
for label, p in bundles.items():
    res = run_validator(p)
    check(f"2. validator PASS: {label}", res["valid"], str(res["errors"][:2]))

# 2t. the template is a valid, self-consistent bundle -- catches drift between
# problem_template.json and its CSVs, and exercises CSV '#'-comment skipping (the
# template CSVs carry documentation lines the example CSVs do not).
_tmpl = run_validator(V3 / "templates/problem_template.json")
check("2t. template validates with no errors or warnings",
      _tmpl["valid"] and not _tmpl["warnings"], str(_tmpl["errors"][:2] + _tmpl["warnings"][:2]))

# deep ref resolution against real instances
for form, f in [("declarative", "schema-v3-declarative.json"), ("expanded", "schema-v3-expanded.json")]:
    inst = json.loads(bundles[f"sisqual {form}"].read_text())
    errs = list(Draft202012Validator(docs[f]).iter_errors(inst))
    check(f"1b. standalone schema validates {form} instance", not errs, str(errs[:1]))

# 3. demand carried through untouched
for ex in ["sisqual_example", "time_constraints_example"]:
    a = json.loads((V3 / f"examples/{ex}/problem.json").read_text())["demand"]
    b = json.loads((V3 / f"examples/{ex}/problem.expanded.json").read_text())["demand"]
    check(f"3. demand identical A->B: {ex}", a == b)

# 4. every employee-day has >=1 assignment or a dayOff
for ex in ["sisqual_example", "time_constraints_example"]:
    exp = json.loads((V3 / f"examples/{ex}/problem.expanded.json").read_text())
    bad = [(e["employeeId"], d["date"]) for e in exp["availability"] for d in e["days"]
           if not d.get("assignmentIds") and "dayOff" not in d]
    check(f"4. no empty open worker-day: {ex}", not bad, str(bad[:3]))

# 5. spot-check exact minute boundaries on the 15-min grid
exp = json.loads((V3 / "examples/sisqual_example/problem.expanded.json").read_text())
cat = {a["id"]: a for a in exp["assignmentCatalog"]}
spans = {(iv["startMin"], iv["endMin"]) for a in cat.values() for iv in a["intervals"]}
check("5a. Storage 08:30-15:30 -> block 510-930 exists", (510, 930) in spans)
texp = json.loads((V3 / "examples/time_constraints_example/problem.expanded.json").read_text())
tspans = {(iv["startMin"], iv["endMin"]) for a in texp["assignmentCatalog"] for iv in a["intervals"]}
check("5b. night EQUALS:22:00-06:00 -> 1320-1800 (past midnight, unrolled)", (1320, 1800) in tspans)
check("5c. every boundary lands on the 15-min grid",
      all(s % 15 == 0 and e % 15 == 0 for s, e in spans | tspans))

# 6. demand invariant: 0 = unset passes, real inversion fails
def demand_case(rows, label, expect_valid):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        src = V3 / "examples/time_constraints_example"
        for f in ["problem.json", "schedule_input.csv"]:
            shutil.copy(src / f, td / f)
        with open(td / "demand.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "workPeriod", "team", "minimum", "empiric", "maximum", "start", "end"])
            w.writerows(rows)
        res = run_validator(td / "problem.json")
        bound_errs = [e for e in res["errors"] if "minimum" in e or "empiric" in e or "maximum" in e]
        check(label, (not bound_errs) == expect_valid, str(bound_errs[:1]))

base = [[f"2030-10-0{d}", wp, "TeamA", 1, 2, 2, "", ""]
        for d in range(1, 8) for wp in ["MORNING", "AFTERNOON", "NIGHT"]]
demand_case(base, "6a. minimum<=empiric<=maximum accepted", True)
zeroed = [r[:3] + [1, 0, 0, "", ""] for r in base]  # empiric/maximum unset
demand_case(zeroed, "6b. zero bounds treated as unset, not as 0 <= 1 violation", True)
inverted = [r[:3] + [2, 1, 3, "", ""] for r in base]
demand_case(inverted, "6c. minimum=2 > empiric=1 rejected", False)

# 7. v2.6 hours-in-cells guard
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    src = V3 / "examples/time_constraints_example"
    for f in ["problem.json", "demand.csv"]:
        shutil.copy(src / f, td / f)
    rows = list(csv.reader(open(src / "schedule_input.csv")))
    rows[1][3] = "8"  # unmigrated v2.6 hours value
    with open(td / "schedule_input.csv", "w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    res = run_validator(td / "problem.json")
    check("7. unmigrated hours cell '8' rejected (would mean 8 minutes)",
          any("MINUTES" in e for e in res["errors"]), str(res["errors"][:1]))

# 8. D_wk vs U_wk semantics
si = {r[0]: r[1:] for r in list(csv.reader(open(V3 / "examples/sisqual_example/schedule_input.csv")))[1:]}
hdr = list(csv.reader(open(V3 / "examples/sisqual_example/schedule_input.csv")))[0][1:]
avail = {e["employeeId"]: {d["date"]: d for d in e["days"]} for e in exp["availability"]}
do_ok = vac_ok = True
for eid, cells in si.items():
    for i, c in enumerate(cells):
        day = avail[eid][hdr[i]]
        if c == "DO":
            do_ok &= day.get("dayOff") == "preferable" and bool(day.get("assignmentIds"))
        if c in ("VAC", "FDO", "NOT", "Med"):
            vac_ok &= day.get("dayOff") == "unavailable" and not day.get("assignmentIds")
check("8a. DO -> dayOff=preferable AND keeps options (soft, D_wk)", do_ok)
check("8b. VAC/FDO/NOT/Med -> dayOff=unavailable AND no options (hard, U_wk)", vac_ok)
pref = sum(1 for e in exp["availability"] for d in e["days"] if d.get("dayOff") == "preferable")
raw_do = sum(r.count("DO") for r in si.values())
check(f"8c. every DO cell survives as preferable ({pref} == {raw_do})", pref == raw_do)

# 9. n_wk >= 0 (validator computes it; assert it reported none negative)
res = run_validator(V3 / "examples/sisqual_example/problem.expanded.json")
check("9. derived n_wk non-negative for every (worker, week)", res["stats"]["negative_n_wk"] == 0)

# 10. H_wd subset of T_d -- excluded, not truncated (domain logic lives in core)
import core as C
prob = json.loads((V3 / "examples/time_constraints_example/problem.json").read_text())
periods = C.period_ranges(prob)
window = C.operating_window(periods, 15)
# T_d covering only 08:30-16:30; a block reaching past 16:30 must be dropped whole
t_d = set(range(510 // 15, 990 // 15))
cands = C.build_day_candidates(C.CellRule(kind="auto"),
                               {"workMinutesPerDay": 480}, window, 15)
kept = [c for c in cands if C.slots_of(c.intervals, 15) <= t_d]
dropped = [c for c in cands if not C.slots_of(c.intervals, 15) <= t_d]
check("10a. blocks outside T_d are dropped", len(dropped) > 0, f"{len(dropped)} dropped")
check("10b. surviving blocks lie entirely inside T_d",
      all(C.slots_of(c.intervals, 15) <= t_d for c in kept))
check("10c. no block was truncated to fit (all keep full 480 min)",
      all(c.intervals[0].end - c.intervals[0].start == 480 for c in kept))
check("10d. the single exact fit 510-990 survives",
      any(c.intervals[0].start == 510 and c.intervals[0].end == 990 for c in kept))

# 10e. csv_lines drops '#' comments and blank lines, keeps data (incl. indented rows)
_lines = list(C.csv_lines(iter([
    "# a comment\n", "\n", "date,team\n", "  # indented comment\n",
    "2025-10-01,TeamA\n", "   \n",
])))
check("10e. csv_lines strips comments and blanks", _lines == ["date,team\n", "2025-10-01,TeamA\n"],
      str(_lines))

# 11. level polarity: 1 = highest, data NOT inverted from v2.6
v26 = json.loads((V3.parent / "schema_v2.6/examples/sisqual_example/problem.json").read_text())
old = {e["id"]: {t["code"]: t["level"] for t in e["teams"]} for e in v26["employees"]["competency"]}
new = json.loads((V3 / "examples/sisqual_example/problem.json").read_text())
newlv = {e["id"]: {t["team"]: t["level"] for t in e["teamAssignments"]} for e in new["employees"]["list"]}
check("11a. competency levels preserved from v2.6 (not inverted)", old == newlv)
# Both schemas carry their own copy of competenceLevel; assert the polarity in each
# so the standalone copies cannot drift apart, and assert it by meaning rather than
# by one exact sentence.
def states_one_is_highest(schema):
    d = schema["$defs"]["competenceLevel"]["description"].lower()
    return ("1 is the highest" in d) and ("junior" not in d)
check("11b. BOTH schemas document level 1 as highest",
      all(states_one_is_highest(docs[f]) for f in
          ("schema-v3-declarative.json", "schema-v3-expanded.json")))
check("11b2. the two competenceLevel copies are identical",
      docs["schema-v3-declarative.json"]["$defs"]["competenceLevel"]
      == docs["schema-v3-expanded.json"]["$defs"]["competenceLevel"])
fulltimers = [e for e in new["employees"]["list"]
              if e["contractAssignments"][0]["contractType"] == "fullTime_8h"]
check("11c. full-timers hold the top level (1 or 2) in Management",
      all(min(t["level"] for t in e["teamAssignments"]) <= 2 for e in fulltimers))


# ---------------------------------------------------------------- new checks
# Fixtures copy an example, break exactly one thing, and assert the right complaint.

TC = V3 / "examples/time_constraints_example"


def fixture(mutate_problem=None, schedule_rows=None, demand_rows=None):
    """Copy time_constraints_example into a temp dir, optionally breaking one thing."""
    td = Path(tempfile.mkdtemp())
    for f in ["problem.json", "demand.csv", "schedule_input.csv"]:
        shutil.copy(TC / f, td / f)
    if mutate_problem:
        d = json.loads((td / "problem.json").read_text())
        mutate_problem(d)
        (td / "problem.json").write_text(json.dumps(d, indent=2))
    if schedule_rows:
        rows = list(csv.reader(open(TC / "schedule_input.csv")))
        hdr = rows[0]
        for r in rows[1:]:
            for i, _ in enumerate(r[1:]):
                if (r[0], hdr[i + 1]) in schedule_rows:
                    r[i + 1] = schedule_rows[(r[0], hdr[i + 1])]
        csv.writer(open(td / "schedule_input.csv", "w", newline="")).writerows(rows)
    if demand_rows is not None:
        with open(td / "demand.csv", "w", newline="") as fh:
            csv.writer(fh).writerows(demand_rows)
    return td


# CONTROL: an unmutated fixture must validate clean. Without this, a fixture that
# silently broke would make every expect() below pass for the wrong reason -- the
# needle would match collateral damage, not the thing under test.
_control = fixture()
_cres = run_validator(_control / "problem.json")
check("11d. CONTROL: unmutated fixture is clean (0 errors, 0 warnings)",
      not _cres["errors"] and not _cres["warnings"],
      f"errors={_cres['errors'][:2]} warnings={_cres['warnings'][:2]}")
shutil.rmtree(_control, ignore_errors=True)


def expect(label, td, needle, want_error=True):
    """Assert the fixture raises EXACTLY ONE finding, and it matches `needle`.

    Isolation, not mere presence: the control above is clean, so a well-formed
    fixture that breaks one thing must raise one finding. More than one means the
    mutation had collateral effects and the test is no longer about what it claims.
    """
    res = run_validator(td / "problem.json")
    pool = res["errors"] if want_error else res["warnings"]
    other = res["warnings"] if want_error else res["errors"]
    isolated = len(pool) == 1 and not other
    hit = bool(pool) and needle.lower() in pool[0].lower()
    check(label, isolated and hit,
          f"pool={pool} other={other}")
    shutil.rmtree(td, ignore_errors=True)


# 12. THE REGRESSION: the three original v2.6 cells must now be caught
td = fixture(schedule_rows={
    ("EMP001", "2030-10-04"): "EQUALS:08:00-16:00",
    ("EMP008", "2030-10-02"): "EQUALS:08:00-16:00",
    ("EMP005", "2030-10-06"): "INCLUDE:08:00-20:00",
})
res = run_validator(td / "problem.json")
impossible = [e for e in res["errors"] if "can never be satisfied" in e]
check(f"12a. the 3 original v2.6 cells are all caught ({len(impossible)} found)", len(impossible) == 3,
      str(res["errors"][:2]))
check("12b. EQUALS:08:00-16:00 diagnosed as outside the operating window",
      any("outside the operating window" in e and "EQUALS:08:00-16:00" in e for e in impossible))
check("12c. INCLUDE:08:00-20:00 diagnosed as wider than the worked duration",
      any("no single block can contain them" in e and "INCLUDE:08:00-20:00" in e for e in impossible))
r = subprocess.run([PY, str(SRC / "transform.py"), str(td / "problem.json"),
                    "--strict", "-o", str(td / "out.json")], capture_output=True, text=True)
check("12d. transform --strict exits non-zero on them", r.returncode != 0)
shutil.rmtree(td, ignore_errors=True)

r = subprocess.run([PY, str(SRC / "transform.py"),
                    str(V3 / "examples/sisqual_example/problem.json"), "--strict",
                    "-o", str(Path(tempfile.mkdtemp()) / "o.json")], capture_output=True, text=True)
check("12e. transform --strict exits 0 on the shipped example", r.returncode == 0, r.stderr[:200])

# 13. Tier 1 diagnoses
expect("13a. EXCEPT swallowing the window", fixture(schedule_rows={("EMP003", "2030-10-01"): "EXCEPT:08:00-23:59"}),
       "leaves no room")
expect("13b. duration exceeding the operating window",
       fixture(schedule_rows={("EMP003", "2030-10-01"): "1500"}), "exceeds the operating window")
expect("13c. off-grid numeric cell", fixture(schedule_rows={("EMP003", "2030-10-01"): "470"}),
       "not a multiple of the 15-minute grid")

# 14. Tier 2 structural
td = fixture(schedule_rows={("EMP001", d): "A" for d in
                            ["2030-10-01", "2030-10-02", "2030-10-03", "2030-10-04",
                             "2030-10-05", "2030-10-06", "2030-10-07"]})
expect("14a. compelled to work six consecutive open days", td, "6 consecutive open days")
# These target a NEW contract (unused, or held by one employee) so the break is
# isolated -- mutating the shared fullTime_8h would fault every employee at once.
expect("14b. contract minutes off-grid",
       fixture(lambda d: d["contracts"]["definitions"].append(
           {"id": "odd", "name": "odd", "workMinutesPerDay": 475})),
       "no assignment block can ever align")


def _one_capped(constraint):
    def m(d):
        d["contracts"]["definitions"].append(
            {"id": "capped", "name": "capped", "workMinutesPerDay": 480, "constraints": constraint})
        d["employees"]["list"][0]["contractAssignments"] = [
            {"contractType": "capped", "start": "2025-01-01", "end": None}]
    return m


expect("14c. contract weekly cap unsatisfiable",
       fixture(_one_capped({"maxMinutesPerWeek": 600})), "maxMinutesPerWeek")
expect("14d. minRestDaysPerWeek unsatisfiable",
       fixture(_one_capped({"minRestDaysPerWeek": 5})), "rest days")

# 15. Tier 3 integrity
expect("15a. VAC classified as preferable is rejected",
       fixture(lambda d: d["scheduleInput"]["dayOffCodes"]["VAC"].__setitem__("kind", "preferable")),
       "unavailable by definition")
expect("15b. a CSV code absent from dayOffCodes is undeclared",
       fixture(schedule_rows={("EMP001", "2030-10-01"): "XYZ"}),
       "undeclared code")
# a dayOffCodes entry without `kind` is a schema violation (used in a cell so it is not
# also flagged as unused, keeping the finding isolated)
expect("15d. dayOffCodes entry missing kind is a schema error",
       fixture(lambda d: d["scheduleInput"]["dayOffCodes"].__setitem__("BAD", {}),
               schedule_rows={("EMP001", "2030-10-01"): "BAD"}),
       "schema", want_error=True)
v26 = [["date", "workPeriod", "team", "minimum", "ideal", "estimated", "start", "end"]] + \
      [[f"2030-10-0{i}", wp, "TeamA", 1, 2, 2, "", ""] for i in range(1, 8)
       for wp in ["MORNING", "AFTERNOON", "NIGHT"]]
expect("15c. unmigrated v2.6 demand header is rejected by name", fixture(demand_rows=v26),
       "v2.6 header")
# removed v2.6 fields inside closed objects are now caught by additionalProperties:false
# at the schema layer -- no dedicated guard needed (the silent-ignore is gone).
expect("15e. a leftover v2.6 restrictions block is rejected",
       fixture(lambda d: d["employees"]["list"][0].__setitem__(
           "restrictions", {"blackoutDates": ["2030-10-01"]})),
       "restrictions")
expect("15f. a leftover breaks block on a work period is rejected",
       fixture(lambda d: d["demand"]["workPeriods"][0].__setitem__(
           "breaks", [{"type": "meal", "durationMinutes": 30}])),
       "breaks")

# 16. priorityOrder (honored by presence -- no feature flag)
def po(entries):
    def m(d):
        d["demand"]["priorityOrder"] = entries
    return m
# distinct levels at the same order: duplicate-order error, but neither shadows the
# other (different levels), so no unreachable warning -- an isolated single finding
expect("16a. duplicate order values",
       fixture(po([{"order": 1, "team": "TeamA", "level": 1},
                   {"order": 1, "team": "TeamA", "level": 2}])),
       "order must be unique")
expect("16b. unknown team in priorityOrder", fixture(po([{"order": 1, "team": "Nope"}])),
       "unknown team")
expect("16c. bare team shadows a later level entry (unreachable)",
       fixture(po([{"order": 1, "team": "TeamA"}, {"order": 2, "team": "TeamA", "level": 1}])),
       "unreachable", want_error=False)
expect("16d. order drives evaluation, not array position",
       fixture(po([{"order": 2, "team": "TeamA", "level": 1}, {"order": 1, "team": "TeamA"}])),
       "unreachable", want_error=False)

# 17. the shipped examples stay clean
for label, path in [("sisqual", V3 / "examples/sisqual_example/problem.json"),
                    ("timeconstr", V3 / "examples/time_constraints_example/problem.json")]:
    res = run_validator(path)
    check(f"17. {label} declarative has no errors", res["valid"], str(res["errors"][:2]))
res = run_validator(V3 / "examples/time_constraints_example/problem.json")
check("17b. time_constraints raises no warnings at all", not res["warnings"], str(res["warnings"][:2]))
res = run_validator(V3 / "examples/sisqual_example/problem.json")
check("17c. sisqual raises exactly the one known tight-week warning",
      len(res["warnings"]) == 1 and "20067696" in res["warnings"][0], str(res["warnings"]))

# 18. priorityOrder carried 1:1 from v2.6, nothing invented
v26p = json.loads((V3.parent / "schema_v2.6/examples/sisqual_example/problem.json").read_text())
old_ranks = {h["team"]: h["rank"] for h in v26p["demand"]["priorityHierarchy"]}
new_order = {e["team"]: e["order"] for e in
             json.loads((V3 / "examples/sisqual_example/problem.json").read_text())
             ["demand"]["priorityOrder"]}
check("18a. priorityOrder is a 1:1 carry-over of v2.6 team ranks", old_ranks == new_order)
check("18b. no level was invented (v2.6 ranked teams only)",
      all("level" not in e for e in
          json.loads((V3 / "examples/sisqual_example/problem.json").read_text())
          ["demand"]["priorityOrder"]))

# 19. solve directives were cut (optimization/constraints connect to no solver);
# a leftover block validates clean at the root, so a guard must reject it.
expect("19a. a leftover optimization block is rejected",
       fixture(lambda d: d.__setitem__("optimization", {"algorithm": "CSPv2"})),
       "'optimization' was removed")
expect("19b. a leftover constraints block is rejected",
       fixture(lambda d: d.__setitem__(
           "constraints", {"hard": [{"id": "min-rest", "type": "min_rest_minutes",
                                     "params": {"minutes": 660}}]})),
       "'constraints' was removed")
# additionalProperties:false catches a field-name typo in a closed object...
expect("19c. a mistyped field in a closed object is rejected",
       fixture(lambda d: d["contracts"]["definitions"][0].__setitem__("workMinutsPerDay", 480)),
       "not allowed", want_error=True)
# ...but a stray key at the (open) root is still accepted -- that is where _comment_ lives
_rootok = fixture(lambda d: d.__setitem__("_comment_note", "kept"))
check("19d. a stray key at the open root is accepted",
      run_validator(_rootok / "problem.json")["valid"], "root should stay open")
shutil.rmtree(_rootok, ignore_errors=True)
# a reversed temporalScope (start after end) must not validate as an empty schedule
expect("19e. a reversed temporalScope is rejected",
       fixture(lambda d: d.__setitem__("temporalScope", {"start": "2030-10-07", "end": "2030-10-01"})),
       "after end")

# 20. decoupling: core is standalone; neither tool imports the other
import importlib
check("20a. core imports standalone", importlib.import_module("core") is not None)
transform_src = (SRC / "transform.py").read_text()
validator_src = (SRC / "validator.py").read_text()
check("20b. transform.py does not import validator",
      "import validator" not in transform_src and "from validator" not in transform_src)
check("20c. validator.py does not import transform",
      "import transform" not in validator_src and "from transform" not in validator_src)
check("20d. core.py imports neither tool",
      not any(s in (SRC / "core.py").read_text()
              for s in ("import transform", "import validator")))
# the transformer's diagnostics and the validator's feasibility errors come from the
# one shared scan, so they cannot disagree
import core as _core
_tc = json.loads((V3 / "examples/time_constraints_example/problem.json").read_text())
_diags = _core.scan_feasibility(_tc, V3 / "examples/time_constraints_example")
check("20e. core.scan_feasibility is the single diagnostics source", _diags == [])

# 21. multi-window cells: split shift (EQUALS), cover-all (INCLUDE), avoid-all (EXCEPT),
# coalescing, and the mustCover/mustAvoid re-check in the expanded form.
_stub = {"scheduleInput": {"dayOffCodes": {}}}

r_split = C.classify_cell("EQUALS:07:30-14:00,18:15-21:15", _stub)
check("21a. EQUALS with a gap keeps two windows",
      [(w.start, w.end) for w in r_split.windows] == [(450, 840), (1095, 1275)],
      str(r_split.windows))
cand = C.build_day_candidates(r_split, {"workMinutesPerDay": 480}, C.Interval(450, 1320), 15)
check("21b. a split EQUALS builds ONE assignment with two intervals",
      len(cand) == 1 and len(cand[0].intervals) == 2, str(cand))
check("21c. split EQUALS required_duration sums both blocks (390+180)",
      C.required_duration(r_split, None) == 570)
check("21d. overlapping EQUALS coalesces to one interval (08:00-12:00,10:00-14:00 -> 480-840)",
      [(w.start, w.end) for w in C.classify_cell("EQUALS:08:00-12:00,10:00-14:00", _stub).windows]
      == [(480, 840)])
check("21e. touching EQUALS coalesces (08:00-12:00,12:00-16:00 -> 480-960)",
      [(w.start, w.end) for w in C.classify_cell("EQUALS:08:00-12:00,12:00-16:00", _stub).windows]
      == [(480, 960)])

_win = C.Interval(480, 1320)  # 08:00-22:00
inc = C.classify_cell("INCLUDE:09:00-10:00,15:00-16:00", _stub)
inc_blocks = C.build_day_candidates(inc, {"workMinutesPerDay": 480}, _win, 15)
check("21f. multi-window INCLUDE: every built block covers BOTH windows",
      inc_blocks and all(b.contains(C.Interval(540, 600)) and b.contains(C.Interval(900, 960))
                         for c in inc_blocks for b in c.intervals), f"{len(inc_blocks)} blocks")
# two edge windows an 8h block can actually leave free (one before, one after)
exc = C.classify_cell("EXCEPT:08:00-08:30,21:30-22:00", _stub)
exc_blocks = C.build_day_candidates(exc, {"workMinutesPerDay": 480}, _win, 15)
check("21g. multi-window EXCEPT: every built block avoids BOTH windows",
      exc_blocks and all(not b.overlaps(C.Interval(480, 510)) and not b.overlaps(C.Interval(1290, 1320))
                         for c in exc_blocks for b in c.intervals), f"{len(exc_blocks)} blocks")

# transform -> expanded: mustCover / mustAvoid recorded and satisfied, and it validates
td = fixture(schedule_rows={("EMP002", "2030-10-02"): "INCLUDE:09:00-10:00,15:00-16:00",
                            ("EMP003", "2030-10-02"): "EXCEPT:12:00-13:00"})
subprocess.run([PY, str(SRC / "transform.py"), str(td / "problem.json"), "-o", str(td / "e.json")],
               check=True, capture_output=True)
_e = json.loads((td / "e.json").read_text())
_cat = {a["id"]: a for a in _e["assignmentCatalog"]}
def _covered(aid):
    s = set()
    for iv in _cat[aid]["intervals"]:
        s |= set(range(iv["startMin"] // 15, iv["endMin"] // 15))
    return s
_d2 = {(e["employeeId"], d["date"]): d for e in _e["availability"] for d in e["days"]}
inc_day = _d2[("EMP002", "2030-10-02")]
check("21h. INCLUDE records mustCover with both windows",
      [(w["startMin"], w["endMin"]) for w in inc_day.get("mustCover", [])] == [(540, 600), (900, 960)],
      str(inc_day.get("mustCover")))
check("21i. every offered assignment covers each mustCover window",
      inc_day["assignmentIds"] and all(
          set(range(540 // 15, 600 // 15)) <= _covered(a) and set(range(900 // 15, 960 // 15)) <= _covered(a)
          for a in inc_day["assignmentIds"]))
exc_day = _d2[("EMP003", "2030-10-02")]
check("21j. EXCEPT records mustAvoid",
      [(w["startMin"], w["endMin"]) for w in exc_day.get("mustAvoid", [])] == [(720, 780)],
      str(exc_day.get("mustAvoid")))
check("21k. the untampered expansion validates", run_validator(td / "e.json")["valid"])

# independent re-check: tamper the expansion and the validator must catch it
_bad = json.loads((td / "e.json").read_text())
for e in _bad["availability"]:
    for d in e["days"]:
        if (e["employeeId"], d["date"]) == ("EMP002", "2030-10-02"):
            d["mustCover"] = [{"startMin": 480, "endMin": 510}]  # 08:00-08:30, which no block need cover
(td / "bad.json").write_text(json.dumps(_bad))
_bres = run_validator(td / "bad.json")
check("21l. validator catches an assignment that fails a mustCover window",
      not _bres["valid"] and any("does not cover required window" in e for e in _bres["errors"]),
      str(_bres["errors"][:2]))
_bad2 = json.loads((td / "e.json").read_text())
for e in _bad2["availability"]:
    for d in e["days"]:
        if (e["employeeId"], d["date"]) == ("EMP003", "2030-10-02") and d.get("assignmentIds"):
            first = _cat[d["assignmentIds"][0]]["intervals"][0]
            d["mustAvoid"] = [{"startMin": first["startMin"], "endMin": first["startMin"] + 15}]
(td / "bad2.json").write_text(json.dumps(_bad2))
_b2 = run_validator(td / "bad2.json")
check("21m. validator catches an assignment that hits a mustAvoid window",
      not _b2["valid"] and any("overlaps forbidden window" in e for e in _b2["errors"]),
      str(_b2["errors"][:2]))
shutil.rmtree(td, ignore_errors=True)

# forced (pre-existing expanded feature): valid pin accepted, dangling pin rejected
_sx = json.loads((V3 / "examples/sisqual_example/problem.expanded.json").read_text())
_pinned = False
for e in _sx["availability"]:
    for d in e["days"]:
        if not _pinned and d.get("assignmentIds"):
            d["forced"] = d["assignmentIds"][0]
            _pinned = True
_ftd = Path(tempfile.mkdtemp())
shutil.copy(V3 / "examples/sisqual_example/demand.csv", _ftd / "demand.csv")
(_ftd / "e.json").write_text(json.dumps(_sx))
check("21n. a forced pin equal to an offered assignment validates", run_validator(_ftd / "e.json")["valid"])
for e in _sx["availability"]:
    for d in e["days"]:
        if d.get("forced"):
            d["forced"] = "A9999"
(_ftd / "bad.json").write_text(json.dumps(_sx))
_fr = run_validator(_ftd / "bad.json")
check("21o. a forced pin not in assignmentIds is rejected",
      not _fr["valid"] and any("forced assignment" in e for e in _fr["errors"]), str(_fr["errors"][:2]))
shutil.rmtree(_ftd, ignore_errors=True)


print(f"\n{'='*60}\n{len(passed)} passed, {len(failed)} failed")
if failed:
    for f in failed:
        print("  FAILED:", f)
sys.exit(1 if failed else 0)

"""Transformer behaviour on the shipped examples and fixtures: demand is carried
through untouched, the expansion has the expected shape, D_wk/U_wk semantics hold,
INCLUDE/EXCEPT record mustCover/mustAvoid, and --strict exits on impossible cells."""
import csv
import subprocess

import pytest

from helpers import PY, SIS, SRC, TC, V3, load, validate


@pytest.mark.parametrize("ex", ["sisqual_example", "time_constraints_example"])
def test_demand_carried_through_untouched(ex):
    a = load(V3 / f"examples/{ex}/problem.json")["demand"]
    b = load(V3 / f"examples/{ex}/problem.expanded.json")["demand"]
    assert a == b


@pytest.mark.parametrize("ex", ["sisqual_example", "time_constraints_example"])
def test_no_empty_open_worker_day(ex):
    exp = load(V3 / f"examples/{ex}/problem.expanded.json")
    bad = [(e["employeeId"], d["date"]) for e in exp["availability"] for d in e["days"]
           if not d.get("assignmentIds") and "dayOff" not in d]
    assert not bad, str(bad[:3])


def test_grid_boundaries_exact():
    exp = load(SIS / "problem.expanded.json")
    spans = {(iv["startMin"], iv["endMin"]) for a in exp["assignmentCatalog"] for iv in a["intervals"]}
    assert (510, 930) in spans                                    # Storage 08:30-15:30
    texp = load(V3 / "examples/time_constraints_example/problem.expanded.json")
    tspans = {(iv["startMin"], iv["endMin"]) for a in texp["assignmentCatalog"] for iv in a["intervals"]}
    assert (1320, 1800) in tspans                                 # night EQUALS:22:00-06:00 unrolled
    assert all(s % 15 == 0 and e % 15 == 0 for s, e in spans | tspans)


def test_d_wk_vs_u_wk_semantics():
    exp = load(SIS / "problem.expanded.json")
    rows = list(csv.reader(open(SIS / "schedule_input.csv")))
    hdr = rows[0][1:]
    si = {r[0]: r[1:] for r in rows[1:]}
    avail = {e["employeeId"]: {d["date"]: d for d in e["days"]} for e in exp["availability"]}
    for eid, cells in si.items():
        for i, c in enumerate(cells):
            day = avail[eid][hdr[i]]
            if c == "DO":
                assert day.get("dayOff") == "preferable" and day.get("assignmentIds")
            if c in ("VAC", "FDO", "NOT", "Med"):
                assert day.get("dayOff") == "unavailable" and not day.get("assignmentIds")
    pref = sum(1 for e in exp["availability"] for d in e["days"] if d.get("dayOff") == "preferable")
    assert pref == sum(r.count("DO") for r in si.values())


def test_include_except_record_mustcover_mustavoid(make_fixture):
    d = make_fixture(schedule_rows={
        ("EMP002", "2030-10-02"): "INCLUDE:09:00-10:00,15:00-16:00",
        ("EMP003", "2030-10-02"): "EXCEPT:12:00-13:00",
    })
    subprocess.run([PY, str(SRC / "transform.py"), str(d / "problem.json"), "-o", str(d / "e.json")],
                   check=True, capture_output=True)
    e = load(d / "e.json")
    cat = {a["id"]: a for a in e["assignmentCatalog"]}

    def covered(aid):
        s = set()
        for iv in cat[aid]["intervals"]:
            s |= set(range(iv["startMin"] // 15, iv["endMin"] // 15))
        return s

    d2 = {(x["employeeId"], dd["date"]): dd for x in e["availability"] for dd in x["days"]}
    inc = d2[("EMP002", "2030-10-02")]
    assert [(w["startMin"], w["endMin"]) for w in inc.get("mustCover", [])] == [(540, 600), (900, 960)]
    assert inc["assignmentIds"] and all(
        set(range(540 // 15, 600 // 15)) <= covered(a) and set(range(900 // 15, 960 // 15)) <= covered(a)
        for a in inc["assignmentIds"])
    exc = d2[("EMP003", "2030-10-02")]
    assert [(w["startMin"], w["endMin"]) for w in exc.get("mustAvoid", [])] == [(720, 780)]
    assert validate(d / "e.json").ok                             # the untampered expansion validates


def test_within_records_mustbewithin_and_blocks_sit_inside(make_fixture):
    d = make_fixture(schedule_rows={("EMP002", "2030-10-02"): "WITHIN:08:00-20:00"})
    subprocess.run([PY, str(SRC / "transform.py"), str(d / "problem.json"), "-o", str(d / "e.json")],
                   check=True, capture_output=True)
    e = load(d / "e.json")
    cat = {a["id"]: a for a in e["assignmentCatalog"]}
    d2 = {(x["employeeId"], dd["date"]): dd for x in e["availability"] for dd in x["days"]}
    day = d2[("EMP002", "2030-10-02")]
    assert [(w["startMin"], w["endMin"]) for w in day.get("mustBeWithin", [])] == [(480, 1200)]
    # every offered assignment fits entirely inside 08:00-20:00 (480-1200 min)
    assert day["assignmentIds"] and all(
        all(480 <= iv["startMin"] and iv["endMin"] <= 1200 for iv in cat[a]["intervals"])
        for a in day["assignmentIds"])
    assert validate(d / "e.json").ok


def test_transform_strict_exits_nonzero_on_impossible_cell(make_fixture):
    d = make_fixture(schedule_rows={("EMP001", "2030-10-04"): "EQUALS:08:00-16:00"})
    r = subprocess.run([PY, str(SRC / "transform.py"), str(d / "problem.json"), "--strict",
                        "-o", str(d / "out.json")], capture_output=True, text=True)
    assert r.returncode != 0


def test_transform_strict_exits_zero_on_shipped_example(tmp_path):
    r = subprocess.run([PY, str(SRC / "transform.py"), str(SIS / "problem.json"), "--strict",
                        "-o", str(tmp_path / "o.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:200]

"""Merge: a solution seed's locked days fold into the problem as `forced` pins.

Both input modes (expanded + solution, declarative + solution) produce the same
plain expanded, soft seeds are ignored, the demand CSV travels with the output,
and every incoherent lock is fatal (nothing written).
"""
import json
import subprocess

import pytest
from helpers import PY, SIS, SRC, load, validate

import merge as M
from core import DomainError


def _pins(expanded: dict) -> dict:
    return {(x["employeeId"], d["date"]): d["forced"]
            for x in expanded["availability"] for d in x["days"] if "forced" in d}


def _seed(mutate=None) -> dict:
    s = load(SIS / "solution.json")
    if mutate:
        mutate(s)
    return s


# -- the two input modes agree --------------------------------------------
def test_expanded_plus_seed_applies_the_lock():
    merged, stats = M.merge(load(SIS / "problem.expanded.json"), _seed(), SIS)
    assert stats["sourceForm"] == "expanded" and stats["locksApplied"] == 1
    assert _pins(merged) == {("20072412", "2025-10-01"): "A0001"}


def test_declarative_plus_seed_transforms_then_applies_the_same_lock():
    merged, stats = M.merge(load(SIS / "problem.json"), _seed(), SIS)
    assert stats["sourceForm"] == "declarative"
    expanded_pins, _ = M.merge(load(SIS / "problem.expanded.json"), _seed(), SIS)
    assert _pins(merged) == _pins(expanded_pins)


def test_merged_output_is_still_a_valid_expanded(tmp_path):
    merged, _ = M.merge(load(SIS / "problem.expanded.json"), _seed(), SIS)
    (tmp_path / "demand.csv").write_text((SIS / "demand.csv").read_text())
    (tmp_path / "m.expanded.json").write_text(json.dumps(merged))
    assert validate(tmp_path / "m.expanded.json").ok


def test_merge_changes_only_the_locked_worker_day():
    src = load(SIS / "problem.expanded.json")
    merged, _ = M.merge(load(SIS / "problem.expanded.json"), _seed(), SIS)
    changed = [(x["employeeId"], d["date"])
               for xs, x in zip(src["availability"], merged["availability"])
               for ds, d in zip(xs["days"], x["days"]) if ds != d]
    assert changed == [("20072412", "2025-10-01")]
    assert all(src[k] == merged[k] for k in src if k != "availability")


# -- locks only: a soft seed is not a constraint ---------------------------
def test_soft_seed_adds_no_pin():
    def unlock(s):
        for a in s["assignments"]:
            for d in a["days"]:
                d.pop("locked", None)
    merged, stats = M.merge(load(SIS / "problem.expanded.json"), _seed(unlock), SIS)
    assert stats["locksApplied"] == 0 and stats["softSeedsSkipped"] >= 1
    assert _pins(merged) == {}


# -- coherence guards: each is fatal ---------------------------------------
def _lock_a_rest(s):
    """A locked day that names no assignment -- you cannot pin a rest."""
    day = s["assignments"][0]["days"][0]
    day["assignmentId"] = None
    day.pop("competencyPerSlot", None)


@pytest.mark.parametrize("mutate, needle", [
    (lambda s: s["assignments"][0]["days"][0].__setitem__("assignmentId", "A9999"),
     "not one of this worker-day's options"),
    (_lock_a_rest, "locked is true but assignmentId is null"),
    (lambda s: s.__setitem__("problemId", "WRONG"), "does not match"),
    (lambda s: s["assignments"].append(
        {"employeeId": "GHOST", "days": [{"date": "2025-10-01", "assignmentId": "A0001", "locked": True}]}),
     "no such worker-day"),
])
def test_incoherent_seed_is_fatal(mutate, needle):
    with pytest.raises(DomainError) as exc:
        M.merge(load(SIS / "problem.expanded.json"), _seed(mutate), SIS)
    assert needle in str(exc.value)


def test_lock_conflicting_with_existing_forced_is_fatal():
    exp = load(SIS / "problem.expanded.json")
    for x in exp["availability"]:
        if x["employeeId"] == "20072412":
            for d in x["days"]:
                if d["date"] == "2025-10-01":
                    d["forced"] = next(a for a in d["assignmentIds"] if a != "A0001")
    with pytest.raises(DomainError) as exc:
        M.merge(exp, _seed(), SIS)
    assert "already forces" in str(exc.value)


def test_lock_agreeing_with_existing_forced_is_fine():
    exp = load(SIS / "problem.expanded.json")
    for x in exp["availability"]:
        if x["employeeId"] == "20072412":
            for d in x["days"]:
                if d["date"] == "2025-10-01":
                    d["forced"] = "A0001"
    _merged, stats = M.merge(exp, _seed(), SIS)
    assert stats["locksApplied"] == 1


# -- CLI: carries the demand CSV, writes nothing on failure ----------------
def _cli(problem, seed, out):
    return subprocess.run([PY, str(SRC / "merge.py"), str(problem), str(seed), "-o", str(out)],
                          capture_output=True, text=True)


def test_cli_copies_demand_csv_next_to_the_output(tmp_path):
    out = tmp_path / "seeded" / "problem.merged.expanded.json"
    r = _cli(SIS / "problem.expanded.json", SIS / "solution.json", out)
    assert r.returncode == 0, r.stderr
    assert out.exists() and (out.parent / "demand.csv").exists()
    assert validate(out).ok            # demand resolves -> the package is complete


def test_cli_writes_nothing_when_a_lock_cannot_be_applied(tmp_path):
    bad = tmp_path / "bad.solution.json"
    bad.write_text(json.dumps(_seed(
        lambda s: s["assignments"][0]["days"][0].__setitem__("assignmentId", "A9999"))))
    out = tmp_path / "out.json"
    r = _cli(SIS / "problem.expanded.json", bad, out)
    assert r.returncode != 0 and not out.exists()

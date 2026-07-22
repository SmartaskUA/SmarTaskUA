"""Expanded-form validation: n_wk is non-negative on the shipped example, the
mustCover/mustAvoid windows are re-checked against every offered assignment, and a
forced pin must be one of the day's options."""
import json
import shutil
import subprocess

from helpers import PY, SIS, SRC, load, validate


def test_n_wk_non_negative_on_shipped_example():
    assert validate(SIS / "problem.expanded.json").stats["negative_n_wk"] == 0


def _tampered_expansion(make_fixture, mutate):
    """Transform a fixture with an INCLUDE + EXCEPT, then mutate the expansion."""
    d = make_fixture(schedule_rows={
        ("EMP002", "2030-10-02"): "INCLUDE:09:00-10:00,15:00-16:00",
        ("EMP003", "2030-10-02"): "EXCEPT:12:00-13:00",
    })
    subprocess.run([PY, str(SRC / "transform.py"), str(d / "problem.json"), "-o", str(d / "e.json")],
                   check=True, capture_output=True)
    e = load(d / "e.json")
    mutate(e, {a["id"]: a for a in e["assignmentCatalog"]})
    (d / "bad.json").write_text(json.dumps(e))
    return d / "bad.json"


def test_mustcover_violation_is_caught(make_fixture):
    def mutate(e, _cat):
        for x in e["availability"]:
            for day in x["days"]:
                if (x["employeeId"], day["date"]) == ("EMP002", "2030-10-02"):
                    day["mustCover"] = [{"startMin": 480, "endMin": 510}]  # 08:00-08:30, uncovered
    rep = validate(_tampered_expansion(make_fixture, mutate))
    assert not rep.ok and any("does not cover required window" in e for e in rep.errors), rep.errors[:2]


def test_mustavoid_violation_is_caught(make_fixture):
    def mutate(e, cat):
        for x in e["availability"]:
            for day in x["days"]:
                if (x["employeeId"], day["date"]) == ("EMP003", "2030-10-02") and day.get("assignmentIds"):
                    first = cat[day["assignmentIds"][0]]["intervals"][0]
                    day["mustAvoid"] = [{"startMin": first["startMin"], "endMin": first["startMin"] + 15}]
    rep = validate(_tampered_expansion(make_fixture, mutate))
    assert not rep.ok and any("overlaps forbidden window" in e for e in rep.errors), rep.errors[:2]


def _sisqual_expanded_with_forced(tmp_path, forced_value):
    exp = load(SIS / "problem.expanded.json")
    pinned = False
    for e in exp["availability"]:
        for d in e["days"]:
            if not pinned and d.get("assignmentIds"):
                d["forced"] = forced_value(d["assignmentIds"][0])
                pinned = True
    shutil.copy(SIS / "demand.csv", tmp_path / "demand.csv")
    (tmp_path / "e.json").write_text(json.dumps(exp))
    return tmp_path / "e.json"


def test_forced_pin_equal_to_an_option_validates(tmp_path):
    assert validate(_sisqual_expanded_with_forced(tmp_path, lambda first: first)).ok


def test_forced_pin_not_in_options_rejected(tmp_path):
    rep = validate(_sisqual_expanded_with_forced(tmp_path, lambda first: "A9999"))
    assert not rep.ok and any("forced assignment" in e for e in rep.errors), rep.errors[:2]

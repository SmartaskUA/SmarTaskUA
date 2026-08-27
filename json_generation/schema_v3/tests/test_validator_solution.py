"""Solution validation: the example schema-validates and cross-checks against its
expanded problem; each tampered solution is caught; a lone solution with no expanded
sibling warns and skips the cross-checks (rather than erroring)."""
import json
import shutil

from helpers import SIS, validate
from jsonschema import Draft202012Validator


def test_solution_example_schema_validates(schemas):
    sol = json.loads((SIS / "solution.json").read_text())
    errs = list(Draft202012Validator(schemas["schema-v3-solution.json"]).iter_errors(sol))
    assert not errs, str(errs[:1])


def test_solution_cross_validates_against_sibling_expanded():
    rep = validate(SIS / "solution.json")           # auto-locates problem.expanded.json
    assert rep.ok and rep.stats.get("crossCheckedAgainst") == "problem.expanded.json", \
        (rep.errors[:2], rep.warnings[:2])


def _sol_error(make_sol_fixture, mutate, needle):
    rep = validate(make_sol_fixture(mutate) / "solution.json")
    assert not rep.ok and any(needle.lower() in e.lower() for e in rep.errors), rep.errors[:2]


def test_assignment_outside_hwd_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture,
               lambda s: s["assignments"][0]["days"][0].__setitem__("assignmentId", "A9999"), "H_wd")


def test_date_outside_horizon_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture,
               lambda s: s["assignments"][0]["days"][0].__setitem__("date", "2099-01-01"),
               "outside the problem's horizon")


def test_worked_preferable_on_normal_day_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture,
               lambda s: s["assignments"][0]["days"][0].__setitem__("workedPreferableDayOff", True),
               "not a preferable day off")


def test_competencyperslot_unheld_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture,
               lambda s: s["assignments"][0]["days"][0]["competencyPerSlot"][0].__setitem__("competency", "Checkout"),
               "does not hold")


def test_problem_id_mismatch_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture, lambda s: s.__setitem__("problemId", "WRONG"), "does not match")


def test_infeasible_status_carrying_assignments_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture,
               lambda s: s["producedBy"].__setitem__("status", "infeasible"), "carries no assignments")


def test_lone_solution_warns_and_skips(tmp_path):
    (tmp_path / "solution.json").write_text((SIS / "solution.json").read_text())
    rep = validate(tmp_path / "solution.json")
    assert rep.ok and any("no expanded problem" in w for w in rep.warnings), \
        (rep.errors[:2], rep.warnings[:1])


# -- partial seed: locked / merge coherence --
def test_shipped_solution_is_a_partial_seed_with_a_locked_day():
    rep = validate(SIS / "solution.json")
    assert rep.ok and rep.stats["lockedDays"] == 1 and rep.stats["seededDays"] >= 1, \
        (rep.stats, rep.errors[:2])


def _locked_null(s):
    day = s["assignments"][0]["days"][0]
    day["assignmentId"] = None
    day["locked"] = True
    day.pop("competencyPerSlot", None)  # avoid unrelated noise


def test_locked_day_without_assignment_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture, _locked_null, "locked is true but assignmentId is null")


def _forced_fixture(tmp_path, forced_id):
    """sisqual expanded with a forced pin on 20072412 / 2025-10-01 (which the shipped
    solution seeds as A0001), plus the shipped solution -- so forced vs seed can clash."""
    d = tmp_path / "f"
    d.mkdir()
    exp = json.loads((SIS / "problem.expanded.json").read_text())
    for x in exp["availability"]:
        if x["employeeId"] == "20072412":
            for day in x["days"]:
                if day["date"] == "2025-10-01":
                    day["forced"] = forced_id            # must be one of its assignmentIds
    (d / "problem.expanded.json").write_text(json.dumps(exp))
    shutil.copy(SIS / "demand.csv", d / "demand.csv")
    (d / "solution.json").write_text((SIS / "solution.json").read_text())
    return d / "solution.json"


def test_seed_agreeing_with_forced_validates(tmp_path):
    # force the same assignment the solution seeds (A0001) -> coherent
    assert validate(_forced_fixture(tmp_path, "A0001")).ok


def test_seed_contradicting_forced_rejected(tmp_path):
    # a different in-H_wd option so it clears the H_wd check but clashes with the pin
    exp = json.loads((SIS / "problem.expanded.json").read_text())
    hwd = next(day["assignmentIds"] for x in exp["availability"] if x["employeeId"] == "20072412"
               for day in x["days"] if day["date"] == "2025-10-01")
    other = next(a for a in hwd if a != "A0001")
    rep = validate(_forced_fixture(tmp_path, other))
    assert not rep.ok and any("contradicts the expanded problem's forced pin" in e for e in rep.errors), \
        rep.errors[:2]

"""Solution validation: the example schema-validates and cross-checks against its
expanded problem; each tampered solution is caught; a lone solution with no expanded
sibling warns and skips the cross-checks (rather than erroring)."""
import json

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


def test_skillperslot_unheld_team_rejected(make_sol_fixture):
    _sol_error(make_sol_fixture,
               lambda s: s["assignments"][0]["days"][0]["skillPerSlot"][0].__setitem__("team", "Checkout"),
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

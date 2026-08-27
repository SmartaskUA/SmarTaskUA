"""The shipped bundles stay clean, and the v2.6 -> v3.0 data carried over faithfully
(competence levels not inverted, priorityOrder a 1:1 rank carry-over)."""
import json

import pytest

from helpers import SIS, V3, validate


@pytest.mark.parametrize("rel", [
    "examples/sisqual_example/problem.json",
    "examples/sisqual_example/problem.expanded.json",
    "examples/time_constraints_example/problem.json",
    "examples/time_constraints_example/problem.expanded.json",
])
def test_example_bundles_validate(rel):
    rep = validate(V3 / rel)
    assert rep.ok, str(rep.errors[:2])


def test_template_validates_with_no_warnings():
    rep = validate(V3 / "templates/problem_template.json")
    assert rep.ok and not rep.warnings, (rep.errors[:2], rep.warnings[:2])


def test_time_constraints_has_no_warnings():
    assert not validate(V3 / "examples/time_constraints_example/problem.json").warnings


def test_sisqual_has_exactly_the_one_known_tight_week_warning():
    rep = validate(SIS / "problem.json")
    assert len(rep.warnings) == 1 and "20067696" in rep.warnings[0], str(rep.warnings)


def test_competency_levels_preserved_from_v26():
    v26 = json.loads((V3.parent / "schema_v2.6/examples/sisqual_example/problem.json").read_text())
    old = {e["id"]: {t["code"]: t["level"] for t in e["teams"]} for e in v26["employees"]["competency"]}
    new = json.loads((SIS / "problem.json").read_text())
    newlv = {e["id"]: {t["competency"]: t["level"] for t in e["competencyAssignments"]} for e in new["employees"]["list"]}
    assert old == newlv


def test_fulltimers_hold_top_level_management():
    new = json.loads((SIS / "problem.json").read_text())
    fulltimers = [e for e in new["employees"]["list"]
                  if e["contractAssignments"][0]["contractType"] == "fullTime_8h"]
    assert all(min(t["level"] for t in e["competencyAssignments"]) <= 2 for e in fulltimers)


def test_priority_order_is_1to1_carryover_of_v26_ranks():
    v26 = json.loads((V3.parent / "schema_v2.6/examples/sisqual_example/problem.json").read_text())
    old_ranks = {h["team"]: h["rank"] for h in v26["demand"]["priorityHierarchy"]}
    new = json.loads((SIS / "problem.json").read_text())
    new_order = {e["competency"]: e["order"] for e in new["demand"]["priorityOrder"]}
    assert old_ranks == new_order
    assert all("level" not in e for e in new["demand"]["priorityOrder"])

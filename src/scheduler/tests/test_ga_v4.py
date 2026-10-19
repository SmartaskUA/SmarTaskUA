"""The GA on schema v4 packages: frozen cells, a shared yardstick, a valid result."""

import numpy as np
import pytest

from conftest import EXAMPLES, assert_valid_complete, read_result
from problem_v4 import evaluate, load_package

from algorithms.GA.ga_v4 import run_ga_v4, solve
from algorithms.GA.v4_encoding import V4Encoding

QUICK = {"pop_size": 20, "num_generations": 15}


def test_partial_result_days_are_frozen_genes():
    inst = load_package(EXAMPLES / "cenario2_partial")
    enc = V4Encoding(inst)
    for e, employee in enumerate(inst.employees):
        for d, day in enumerate(inst.days):
            if (employee.id, day) in inst.fixed:
                assert enc.frozen[e, d]
    # an open work cell has a choice, and never the rest gene
    e = [x.id for x in inst.employees].index("20072412")
    d = inst.days.index("2026-01-08")
    assert not enc.frozen[e, d] and 0 not in enc.domain[e][d]


def test_frozen_cells_never_move_during_evolution():
    inst = load_package(EXAMPLES / "cenario2_partial")
    enc = V4Encoding(inst)
    reference = enc.random_genes(np.random.default_rng(0))
    best = run_ga_v4(enc, QUICK, None, seed=3)
    assert (best["genes"][enc.frozen] == reference[enc.frozen]).all()


@pytest.mark.parametrize("name", ["cenario2_partial", "cenario2_input_only"])
def test_the_ga_scores_itself_exactly_as_the_shared_evaluator_does(name):
    inst = load_package(EXAMPLES / name)
    enc = V4Encoding(inst)
    best = run_ga_v4(enc, QUICK, None, seed=5)
    parts = enc.components(best["genes"])
    kpis = evaluate(inst, enc.rows(best["genes"]))
    assert (parts["shortage"], parts["priority_cost"]) == (kpis["total_shortage"], kpis["priority_cost"])
    assert parts["violations"] == 0 and kpis["unassigned"] == 0 and kpis["foreign_skill_slots"] == 0


def test_solve_writes_a_valid_result_that_keeps_the_fixed_days(tmp_path):
    solve(problem_path=str(EXAMPLES / "cenario2_partial"), maxTime=1, seed=7, result_dir=str(tmp_path / "out"),
          **QUICK)
    assert_valid_complete(tmp_path / "out")
    written = {(e["EmployeeCode"], e["Date"][:10]): e["ScheduleCode"]
               for e in read_result(tmp_path / "out")["OutRosterTeamDays"]}
    for entry in read_result(EXAMPLES / "cenario2_partial")["OutRosterTeamDays"]:
        assert written[(str(entry["EmployeeCode"]), entry["Date"][:10])] == entry["ScheduleCode"]

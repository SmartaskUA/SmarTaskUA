"""Both Hybrid Sisqual heuristics on schema v4 packages."""

import pytest

from conftest import EXAMPLES, add_code, assert_valid_complete, read_result
from problem_v4 import evaluate, load_package

from algorithms import Hybrid_Heuristic_Sisqual_Levels_Included as levels
from algorithms import Hybrid_Heuristic_Sisqual_No_Levels_Included as no_levels

VARIANTS = {"levels": levels, "no_levels": no_levels}
EMPLOYEE = "20072412"   # cells "8" from Jan 7 to Jan 10


def fixed_codes(package):
    return {(str(e["EmployeeCode"]), e["Date"][:10]): e["ScheduleCode"]
            for e in read_result(package)["OutRosterTeamDays"]}


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_partial_result_days_come_back_unchanged_and_the_result_validates(name, tmp_path):
    module = VARIANTS[name]
    out = tmp_path / "out"
    rows = module.solve(problem_path=str(EXAMPLES / "cenario2_partial"), restarts=1, day_order_mode=[1, 3],
                        result_dir=str(out), results_log_file=str(tmp_path / "log.csv"))
    assert_valid_complete(out)
    written = fixed_codes(out)
    for key, code in fixed_codes(EXAMPLES / "cenario2_partial").items():
        assert written[key] == code
    inst = load_package(EXAMPLES / "cenario2_partial")
    kpis = evaluate(inst, rows)
    assert kpis["unassigned"] == 0 and kpis["foreign_skill_slots"] == 0
    assert (tmp_path / "log.csv").is_file()


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_without_a_partial_result_every_day_is_open(name, tmp_path):
    module = VARIANTS[name]
    rows = module.solve(problem_path=str(EXAMPLES / "cenario2_input_only"), restarts=1, day_order_mode=2,
                        result_dir=str(tmp_path / "out"), results_log_file=str(tmp_path / "log.csv"))
    assert_valid_complete(tmp_path / "out")
    assert evaluate(load_package(EXAMPLES / "cenario2_input_only"), rows)["unassigned"] == 0


def test_the_levels_variant_prefers_the_higher_priority_skill_on_ties():
    inst = load_package(EXAMPLES / "cenario2_input_only")
    scheduler = levels.Hybrid_Heuristic_Sisqual(inst)
    employee = inst.employee(EMPLOYEE)
    # with nothing covered yet and equal remaining need, A (tier 2) beats C and G
    day, slot = "2026-01-02", 26     # 13:00, demanded on every Responsibility value that day
    demanded = scheduler.demanded_by_axis(employee, day, slot)["Responsibility"]
    needs = {s: scheduler.remaining(day, slot, s) for s in demanded}
    top = max(needs.values())
    tied = [s for s in demanded if needs[s] == top]
    chosen = scheduler.choose_skill(employee, day, slot, demanded)
    assert chosen == min(tied, key=lambda s: inst.priority(s, inst.level(EMPLOYEE, day, s)))


def test_a_rest_conflict_is_repaired_by_re_picking_the_neighbour(example_copy):
    package = example_copy("cenario2_partial")
    add_code(package, "9904,19:00-03:00,480,1140,1620", sidecar=False)   # a late menu shift
    inst = load_package(package)
    scheduler = no_levels.Hybrid_Heuristic_Sisqual(inst)
    scheduler.reset()
    scheduler.seed_fixed_days()
    employee = inst.employee(EMPLOYEE)
    by_code = lambda day, code: next(s for s in inst.candidates[(EMPLOYEE, day)] if s.code == code)  # noqa: E731
    scheduler._apply_block(employee, "2026-01-08", by_code("2026-01-08", 9904))     # ends 03:00 on the 9th
    scheduler._apply_block(employee, "2026-01-10", by_code("2026-01-10", 9016))     # starts 09:00 on the 10th
    # every 480-minute shift on the 9th breaks 660 min of rest against one side...
    assert not any(scheduler._rest_ok(EMPLOYEE, "2026-01-09", b) for b in inst.candidates[(EMPLOYEE, "2026-01-09")])
    # ...so the heuristic re-picks the 8th instead of leaving the 9th unassigned
    assert scheduler.assign_employee_day(employee, "2026-01-09")
    assert scheduler.employee_day_block[(EMPLOYEE, "2026-01-08")].code != 9904
    assert scheduler.unassigned == []

"""load_package: the one v4 parser, with and without a partial result."""

import pytest

from conftest import EXAMPLES, add_code, set_fixed_code
from problem_v4 import ParseError, SolveDirectives, load_package
from problem_v4.loader import SYNTHESISED_CODE_BASE

EMPLOYEE = "20072412"   # HOL,8,8,DO,8,DO,8,8,8,8,DO,... on contract PT_40 (480 min)


@pytest.mark.parametrize("name", ["cenario2_input_only", "cenario2_retail", "cenario2_partial"])
def test_every_example_reads_the_same_problem(name):
    inst = load_package(EXAMPLES / name)
    assert len(inst.employees) == 15
    assert len(inst.days) == 31 and inst.days[0] == "2026-01-01" and inst.days[-1] == "2026-01-31"
    assert inst.axes == {"Responsibility": ("A", "C", "G"), "Team": ("T1",)}
    assert inst.skill_axis["Team/T1"] == "Team"
    assert (inst.legislation.max_consecutive, inst.legislation.max_week_days,
            inst.legislation.min_rest_minutes) == (5, 5, 660)
    assert [len(w) for w in inst.weeks] == [4, 7, 7, 7, 6]     # 2026-01-01 is a Thursday
    assert [t["skill"] for t in inst.priority_tiers] == [
        "Team/T1", "Responsibility/A", "Responsibility/C", "Responsibility/G"]
    # the time grid is absolute: slot i starts at i * 30 minutes
    assert all(s.index == i and s.start_min == 30 * i for i, s in enumerate(inst.time_slots))


def test_cells_decide_the_day_modes():
    inst = load_package(EXAMPLES / "cenario2_input_only")
    assert inst.day_modes[(EMPLOYEE, "2026-01-01")] == "unavailable"          # HOL
    assert inst.day_modes[(EMPLOYEE, "2026-01-02")] == "work_template"        # 8
    assert inst.day_modes[(EMPLOYEE, "2026-01-04")] == "preferred_day_off"    # DO
    assert inst.candidates[(EMPLOYEE, "2026-01-04")] == []                    # no swap by default
    assert all(s.end_min - s.start_min == 480 for s in inst.candidates[(EMPLOYEE, "2026-01-02")])


def test_duplicated_competency_takes_the_higher_level():
    inst = load_package(EXAMPLES / "cenario2_input_only")
    # 20067009 holds each pair at levels 1 and 3 over the same dates (next_meeting.md item 18)
    assert inst.level("20067009", "2026-01-10", "Team/T1") == 1


def test_without_a_menu_blocks_are_synthesised_and_nothing_is_fixed():
    inst = load_package(EXAMPLES / "cenario2_input_only")
    assert inst.menu_synthesised
    assert inst.fixed == {} and inst.fixed_workday == {}
    assert len(inst.open_cells) == 15 * 31
    assert all(code >= SYNTHESISED_CODE_BASE for code in inst.menu)


def test_with_a_menu_candidates_are_menu_shifts_of_the_cell_length():
    inst = load_package(EXAMPLES / "cenario2_retail")
    assert not inst.menu_synthesised
    menu_codes = set(inst.menu)
    assert 9001 in menu_codes and 3 in menu_codes


def test_a_complete_result_fixes_every_day():
    inst = load_package(EXAMPLES / "cenario2_retail")
    assert len(inst.fixed) == 465 and inst.open_cells == []
    for key, fixed in inst.fixed.items():
        assert inst.candidates[key] == ([fixed.shift] if fixed.shift else [])
        assert inst.fixed_workday[key] == (1 if fixed.shift else 0)


def test_a_partial_result_fixes_the_first_week_and_leaves_the_rest_open():
    inst = load_package(EXAMPLES / "cenario2_partial")
    assert len(inst.fixed) == 105 and len(inst.open_cells) == 360
    assert {day for _, day in inst.fixed} == {f"2026-01-0{i}" for i in range(1, 8)}
    fixed = inst.fixed[(EMPLOYEE, "2026-01-02")]
    assert fixed.code == 9016 and fixed.shift is not None
    assert inst.fixed[(EMPLOYEE, "2026-01-04")].shift is None           # DO fixed as a rest
    # open days keep their full candidate set
    assert len(inst.candidates[(EMPLOYEE, "2026-01-08")]) > 1


def test_swap_directive_gives_do_cells_contract_length_candidates():
    inst = load_package(EXAMPLES / "cenario2_retail", SolveDirectives(allow_day_off_swap=True))
    # fixed days win over the swap: the retail result fixes every day
    assert inst.candidates[(EMPLOYEE, "2026-01-04")] == []
    inst = load_package(EXAMPLES / "cenario2_input_only", SolveDirectives(allow_day_off_swap=True))
    options = inst.candidates[(EMPLOYEE, "2026-01-04")]
    assert options and all(s.end_min - s.start_min == 480 for s in options)


# -- rejections: the parser fails before any solver runs ------------------------

def _problems(package):
    with pytest.raises(ParseError) as caught:
        load_package(package)
    return " | ".join(caught.value.problems)


def test_a_fixed_rest_on_a_work_cell_is_rejected(example_copy):
    package = example_copy("cenario2_partial")
    set_fixed_code(package, EMPLOYEE, "2026-01-02", 3)      # cell "8", fixed as Day off
    assert "asks for work, but the day is a rest" in _problems(package)


def test_an_unknown_schedule_code_is_rejected(example_copy):
    package = example_copy("cenario2_partial")
    set_fixed_code(package, EMPLOYEE, "2026-01-02", 777)
    assert "defined by neither the sidecar nor the menu" in _problems(package)


def test_a_fixed_run_that_forced_open_days_extend_past_the_cap_is_rejected(example_copy):
    package = example_copy("cenario2_partial")
    # Jan 6 is a DO; fixing it worked makes Jan 5..10 six work days in a row
    # (Jan 8-10 are open, but their cells are "8", so they are certainly worked).
    set_fixed_code(package, EMPLOYEE, "2026-01-06", 9016)
    problems = _problems(package)
    assert "MaxConsecutiveWorkDays of 5" in problems
    assert "MaxConsecutiveWorkDaysInWeek of 5" in problems


def test_rest_pruning_drops_early_shifts_after_a_late_fixed_one(example_copy):
    package = example_copy("cenario2_partial")
    add_code(package, "9901,15:00-23:00,480,900,1380", menu=False)
    set_fixed_code(package, EMPLOYEE, "2026-01-07", 9901)
    before = load_package(EXAMPLES / "cenario2_partial").candidates[(EMPLOYEE, "2026-01-08")]
    after = load_package(package).candidates[(EMPLOYEE, "2026-01-08")]
    assert len(after) < len(before)
    assert all(1440 - 1380 + s.start_min >= 660 for s in after)


def test_a_work_day_emptied_by_rest_pruning_is_rejected(example_copy):
    package = example_copy("cenario2_partial")
    add_code(package, "9902,22:00-06:00,480,1320,1800", menu=False)    # next start >= 17:00
    set_fixed_code(package, EMPLOYEE, "2026-01-07", 9902)
    assert "breaks the 660-minute rest" in _problems(package)


def test_a_folder_with_two_problems_is_rejected(example_copy):
    package = example_copy("cenario2_input_only")
    (package / "other.json").write_text((package / "problem.json").read_text())
    assert "exactly one problem" in _problems(package)

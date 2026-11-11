"""The original shift GA on a converted SMARTASK problem: same data, valid result."""

import importlib.util
from collections import Counter

import numpy as np
import pytest

from conftest import REPO, assert_valid_complete, read_result
from scheduler.solve_command import V4_SOLVERS, resolve_algorithms

from algorithms.GA.legacy_v4 import LegacyPackageError, load_problem_v4, solve

PROBLEMS = REPO / "data" / "problems"
QUICK = {"pop_size": 20, "num_generations": 10}


def _converter():
    spec = importlib.util.spec_from_file_location("convert_legacy_to_v4",
                                                  PROBLEMS / "convert_legacy_to_v4.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def converted(tmp_path):
    """Convert a legacy folder into tmp_path; skipped when the folder is absent."""
    def _convert(name: str, strict: bool = False):
        if not (PROBLEMS / name).is_dir():
            pytest.skip(f"{name} is not in data/problems")
        out = tmp_path / f"V4_{name}"
        _converter().convert(PROBLEMS / name, out, strict)
        return out
    return _convert


@pytest.mark.parametrize("name, strict", [
    ("SMARTASK_SIMPLE_2025", False),
    ("SMARTASK_SIMPLE_2025", True),
    ("SMARTASK_3SHIFTS_2TEAMS_2025", False),
])
def test_the_package_gives_the_ga_exactly_the_legacy_data(converted, name, strict):
    new, _, gp = load_problem_v4(converted(name, strict))
    old = gp.load_problem(str(PROBLEMS / name))
    for key, value in old.items():
        same = np.array_equal(value, new[key]) if isinstance(value, np.ndarray) else value == new[key]
        assert same, key


def test_rules_the_ga_cannot_take_are_refused(converted):
    package = converted("SMARTASK_SIMPLE_2025")
    problem = package / "problem.json"
    problem.write_text(problem.read_text(encoding="utf-8").replace('"MaxSpecialDays": 22',
                                                                   '"MaxSpecialDays": 30'),
                       encoding="utf-8")
    with pytest.raises(LegacyPackageError, match="MaxSpecialDays is 30"):
        load_problem_v4(package)


def test_a_rule_with_no_v4_spelling_is_not_converted(tmp_path):
    name = "SMARTASK_SIMPLE_2025_FIXED_DAYS_OFF"
    if not (PROBLEMS / name).is_dir():
        pytest.skip(f"{name} is not in data/problems")
    converter = _converter()
    with pytest.raises(converter.ConversionError, match="fixed_days_off_per_week"):
        converter.convert(PROBLEMS / name, tmp_path / "out", False)


def test_solve_writes_a_valid_result_with_the_legacy_targets(converted, tmp_path):
    package, out = converted("SMARTASK_SIMPLE_2025"), tmp_path / "solved"
    solve(problem_path=str(package), result_dir=str(out), seed=1, **QUICK)
    assert_valid_complete(out)
    worked = Counter(e["EmployeeCode"] for e in read_result(out)["OutRosterTeamDays"]
                     if e["ScheduleCode"] not in (1, 3, 4))
    assert set(worked.values()) == {223}


def test_ga_legacy_is_an_alias_but_not_part_of_all():
    assert resolve_algorithms("ga-legacy")[0][0] == "ga-legacy"
    assert "ga-legacy" not in [a for a, _, _ in resolve_algorithms("all")]
    assert "ga-legacy" not in V4_SOLVERS

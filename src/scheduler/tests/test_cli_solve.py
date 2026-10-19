"""`python -m scheduler solve`: one command from a v4 package to a validated result."""

import json

import pytest

from conftest import EXAMPLES
from scheduler.cli import main
from scheduler.solve_command import V4_SOLVERS, resolve_algorithms


def test_every_alias_names_a_registered_v4_solver():
    from TaskManager import V4_ALGORITHMS

    assert {name for name, _ in V4_SOLVERS.values()} <= V4_ALGORITHMS
    assert [a for a, _, _ in resolve_algorithms("all")] == list(V4_SOLVERS)
    assert resolve_algorithms("Genetic Algorithm v4") == [("ga", *V4_SOLVERS["ga"])]
    with pytest.raises(SystemExit):
        resolve_algorithms("ILP General")       # a legacy solver is not a v4 one


def test_solve_writes_a_valid_result_and_prints_one_line(tmp_path, capsys):
    code = main(["solve", str(EXAMPLES / "cenario2_partial"), "-a", "hybrid", "-t", "0.2",
                 "-o", str(tmp_path), "--param", "restarts=1"])
    out = capsys.readouterr().out
    assert code == 0, out
    line = next(ln for ln in out.splitlines() if ln.startswith("hybrid "))
    assert "shortage" in line and line.endswith("valid")
    result = json.loads((tmp_path / "hybrid" / "result.json").read_text())
    assert len(result["OutRosterTeamDays"]) == 15 * 31


def test_solve_all_runs_every_v4_solver(tmp_path, capsys):
    code = main(["solve", str(EXAMPLES / "cenario2_partial"), "-a", "all", "-t", "0.1", "-o", str(tmp_path),
                 "--param", "restarts=1", "--param", "num_generations=10"])
    out = capsys.readouterr().out
    assert code == 0, out
    for alias in V4_SOLVERS:
        assert any(ln.startswith(f"{alias} ") and ln.endswith("valid") for ln in out.splitlines()), alias


def test_an_invalid_package_exits_1_with_its_reasons(example_copy, tmp_path, capsys):
    package = example_copy("cenario2_partial")
    doc = json.loads((package / "result.json").read_text())
    doc["OutRosterTeamDays"][1]["ScheduleCode"] = 777
    (package / "result.json").write_text(json.dumps(doc))
    code = main(["solve", str(package), "-o", str(tmp_path / "out")])
    err = capsys.readouterr().err
    assert code == 1
    assert "777" in err and "not a usable v4 package" in err

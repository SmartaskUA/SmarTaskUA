"""ILP and CP-SAT MathematicalDefinition7 on schema v4 packages, with and without a partial result."""

import pytest

from conftest import EXAMPLES, assert_valid_complete, read_result
from problem_v4 import SolveDirectives, evaluate, load_package, objective, write_package

pulp = pytest.importorskip("pulp")
pytest.importorskip("ortools")

from algorithms.CSP_Sisqual_Hours_MathematicalDefinition7 import SisqualProblem5CSP  # noqa: E402
from algorithms.CSP_Sisqual_Hours_MathematicalDefinition7 import solve as csp_solve  # noqa: E402
from algorithms.ILP_Sisqual_Hours_MathematicalDefinition7 import SisqualProblem5ILP  # noqa: E402
from algorithms.ILP_Sisqual_Hours_MathematicalDefinition7 import solve as ilp_solve  # noqa: E402

MODELS = {"ilp": SisqualProblem5ILP, "csp": SisqualProblem5CSP}


def solve_rows(model_cls, inst, minutes=2):
    scheduler = model_cls(inst, SolveDirectives(), max_time_minutes=minutes)
    scheduler.build_model()
    scheduler.solve(verbose=False)
    assert scheduler.has_solution(), scheduler.solution_status()
    return scheduler, scheduler.build_output_rows()


def fixed_codes(package):
    return {(str(e["EmployeeCode"]), e["Date"][:10]): e["ScheduleCode"]
            for e in read_result(package)["OutRosterTeamDays"]}


@pytest.mark.parametrize("kind", sorted(MODELS))
def test_partial_result_days_come_back_unchanged_and_the_result_validates(kind, tmp_path):
    inst = load_package(EXAMPLES / "cenario2_partial")
    _, rows = solve_rows(MODELS[kind], inst)
    out = tmp_path / "out"
    write_package(inst, rows, out)
    assert_valid_complete(out)
    written = fixed_codes(out)
    for key, code in fixed_codes(EXAMPLES / "cenario2_partial").items():
        assert written[key] == code
    kpis = evaluate(inst, rows)
    assert kpis["unassigned"] == 0 and kpis["foreign_skill_slots"] == 0


@pytest.mark.parametrize("kind", sorted(MODELS))
def test_a_complete_result_is_reproduced(kind, tmp_path):
    inst = load_package(EXAMPLES / "cenario2_retail")
    _, rows = solve_rows(MODELS[kind], inst)
    write_package(inst, rows, tmp_path / "out")
    assert fixed_codes(tmp_path / "out") == fixed_codes(EXAMPLES / "cenario2_retail")


def test_without_a_menu_the_ilp_picks_synthesised_blocks(tmp_path):
    inst = load_package(EXAMPLES / "cenario2_input_only")
    _, rows = solve_rows(SisqualProblem5ILP, inst)
    write_package(inst, rows, tmp_path / "out")
    assert_valid_complete(tmp_path / "out")


def test_the_shared_evaluator_scores_exactly_the_ilp_objective():
    inst = load_package(EXAMPLES / "cenario2_partial")
    scheduler, rows = solve_rows(SisqualProblem5ILP, inst)
    if scheduler.model.sol_status != pulp.LpSolutionOptimal:
        pytest.skip("only an optimal solution has z_dts tight against its coverage")
    assert objective(evaluate(inst, rows), SolveDirectives()) == round(scheduler.objective_value)


def test_solve_entry_writes_the_result_package_on_request(tmp_path):
    rows = ilp_solve(problem_path=str(EXAMPLES / "cenario2_partial" / "problem.json"), maxTime=2,
                     verbose=False, result_dir=str(tmp_path / "pkg"))
    assert rows[0][0] == "employee_id"
    assert_valid_complete(tmp_path / "pkg")


def test_a_rejected_package_is_reported_as_a_validation_failure(example_copy):
    from validators.sisqual_feasibility import SisqualValidationError

    package = example_copy("cenario2_partial")
    doc = read_result(package)
    doc["OutRosterTeamDays"][1]["ScheduleCode"] = 777
    (package / "result.json").write_text(__import__("json").dumps(doc))
    with pytest.raises(SisqualValidationError) as caught:
        csp_solve(problem_path=str(package), maxTime=1, verbose=False)
    assert caught.value.failure_type == "INVALID_V4_PACKAGE"
    assert "777" in caught.value.summary

"""Package & folder validation: a directory of related forms is validated as a unit
(with a cross-form problem-id check), and a folder is validated package by package."""
import json
import shutil

from helpers import EX, SIS, V3, run_cli

import validator


def test_package_validates_all_forms_and_agrees_on_problem_id():
    reports = validator.validate_package(SIS)
    # the sisqual package has all three forms, each valid
    assert {"problem.json", "problem.expanded.json", "solution.json"} <= set(reports)
    assert all(r.ok for r in reports.values())
    pkg = reports["(package)"]
    assert pkg.ok and pkg.stats["forms"] == ["declarative", "expanded", "solution"]
    assert pkg.stats["problemId"] == "SISQUAL_OCTOBER_2025"


def test_package_flags_forms_that_name_different_problems(tmp_path):
    shutil.copy(SIS / "problem.expanded.json", tmp_path / "problem.expanded.json")
    sol = json.loads((SIS / "solution.json").read_text())
    sol["problemId"] = "SOMETHING_ELSE"
    (tmp_path / "solution.json").write_text(json.dumps(sol))
    pkg = validator.validate_package(tmp_path)["(package)"]
    assert not pkg.ok and any("name different problems" in e for e in pkg.errors), pkg.errors


def test_validate_tree_covers_every_example_package():
    tree = validator.validate_tree(EX)
    assert set(tree) == {"sisqual_example", "time_constraints_example"}
    assert all(r.ok for pkg in tree.values() for r in pkg.values())


def test_folder_cli_reports_all_valid_and_exits_zero():
    out = run_cli(EX)   # --json map of {package: {file: report}}
    assert set(out) == {"sisqual_example", "time_constraints_example"}
    assert all(rep["valid"] for pkg in out.values() for rep in pkg.values())


def test_templates_folder_is_a_full_three_form_package():
    reports = validator.validate_package(V3 / "templates")
    assert {"problem_template.json", "problem_template.expanded.json",
            "problem_template.solution.json"} <= set(reports)
    assert all(r.ok for r in reports.values())
    assert reports["(package)"].stats["forms"] == ["declarative", "expanded", "solution"]

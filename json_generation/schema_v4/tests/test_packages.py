"""Folder-level orchestration and the CLI."""

from helpers import C1, C2, EXAMPLES, TEMPLATES, run_cli

from schema_v4 import validator


def test_package_reports_the_forms_it_found():
    reports = validator.validate_package(C1)
    assert reports["(package)"].stats["forms"] == ["declarative", "result"]
    assert reports["(package)"].stats["problemId"] == "C1_January_2026"


def test_a_problem_only_package_is_still_a_package():
    reports = validator.validate_package(C2)
    assert reports["(package)"].stats["forms"] == ["declarative"]


def test_a_result_with_no_problem_warns(tmp_path):
    import shutil
    shutil.copyfile(C1 / "result.json", tmp_path / "result.json")
    reports = validator.validate_package(tmp_path)
    assert any("no declarative problem" in w
               for w in reports["(package)"].warnings)


def test_tree_walks_every_package():
    tree = validator.validate_tree(EXAMPLES)
    assert set(tree) >= {"cenario1_nlm", "cenario2_retail"}


def test_templates_are_a_full_package():
    reports = validator.validate_package(TEMPLATES)
    assert all(r.ok for r in reports.values()), \
        {k: v.errors for k, v in reports.items() if not v.ok}


def test_cli_returns_machine_readable_output():
    out = run_cli("templates")
    inner = next(iter(out.values()))
    assert inner["problem_template.json"]["ok"] is True


def test_cli_exits_nonzero_on_a_failing_package():
    import subprocess
    import sys
    from helpers import SRC, V4
    proc = subprocess.run(
        [sys.executable, "-m", "schema_v4.validator", "examples/cenario1_nlm"],
        capture_output=True, text=True, cwd=V4,
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"})
    assert proc.returncode == 1

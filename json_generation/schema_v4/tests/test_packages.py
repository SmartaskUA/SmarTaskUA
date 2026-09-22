"""Folder-level orchestration and the CLI."""

from helpers import C2, EXAMPLES, TEMPLATES, run_cli

from schema_v4 import validator


def test_package_reports_the_forms_it_found():
    reports = validator.validate_package(C2)
    assert reports["(package)"].stats["forms"] == ["declarative", "result"]
    assert reports["(package)"].stats["problemId"] == "C2_January_2026"


def test_a_result_with_no_problem_warns(tmp_path):
    import shutil
    shutil.copyfile(C2 / "result.json", tmp_path / "result.json")
    reports = validator.validate_package(tmp_path)
    assert any("no declarative problem" in w
               for w in reports["(package)"].warnings)


def test_tree_walks_every_package():
    tree = validator.validate_tree(EXAMPLES)
    assert set(tree) == {"cenario2_retail"}


def test_templates_are_a_full_package():
    reports = validator.validate_package(TEMPLATES)
    assert all(r.ok for r in reports.values()), \
        {k: v.errors for k, v in reports.items() if not v.ok}


def test_cli_returns_machine_readable_output():
    out = run_cli("templates")
    inner = next(iter(out.values()))
    assert inner["problem_template.json"]["ok"] is True


def test_cli_exits_nonzero_on_a_failing_package(tmp_path):
    """A raw SISQUAL bundle, which is meant not to validate until adapted."""
    import subprocess
    import sys
    from helpers import RAW_C2, SRC, V4
    proc = subprocess.run(
        [sys.executable, "-m", "schema_v4.validator", str(RAW_C2)],
        capture_output=True, text=True, cwd=V4,
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"})
    assert proc.returncode == 1

"""Folder-level orchestration and the command line."""


import shutil

from helpers import C2, EXAMPLES, TEMPLATES, assert_isolated, run_cli

from schema_v4 import validator


# -- packages ----------------------------------------------------------------

def test_package_reports_the_forms_it_found():
    reports = validator.validate_package(C2)
    assert reports["(package)"].stats["forms"] == ["input", "result"]
    assert reports["(package)"].stats["problemId"] == "C2_January_2026"


def test_a_result_with_no_problem_warns(lone_result):
    reports = validator.validate_package(lone_result.parent)
    assert any("no input problem" in w for w in reports["(package)"].warnings)


def test_a_file_that_is_neither_form_is_skipped(tmp_path, make_result_fixture):
    make_result_fixture()
    (tmp_path / "notes.json").write_text('{"hello": "world"}', encoding="utf-8")
    reports = validator.validate_package(tmp_path)
    assert "notes.json" not in reports


def test_tree_walks_every_package():
    tree = validator.validate_tree(EXAMPLES)
    assert set(tree) == {"cenario2_retail", "cenario2_input_only", "cenario2_partial"}


def test_tree_reports_a_top_level_package_under_its_own_key(tmp_path, make_fixture):
    make_fixture()
    tree = validator.validate_tree(tmp_path)
    assert "." in tree


def test_templates_are_a_full_package():
    reports = validator.validate_package(TEMPLATES)
    assert all(r.ok for r in reports.values()), \
        {k: v.errors for k, v in reports.items() if not v.ok}
    assert reports["(package)"].stats["menu"] is True
    assert reports["(package)"].stats["result"] == "result_template.json"


# -- package shapes ----------------------------------------------------------

def test_the_smallest_package_is_the_problem_and_its_four_csvs(make_fixture):
    """No menu, no result: still a complete package, with nothing to say about it."""
    path = make_fixture(mutate_problem=lambda d: d.pop("schedules"))
    for name in ("result_template.json", "result_template_schedules.csv",
                 "schedules_template.csv"):
        (path.parent / name).unlink()
    reports = validator.validate_package(path.parent)
    assert set(reports) == {"problem_template.json", "(package)"}
    for name, r in reports.items():
        assert r.ok and not r.warnings, (name, r.errors, r.warnings)
    stats = reports["(package)"].stats
    assert stats["forms"] == ["input"]
    assert stats["menu"] is False and stats["result"] is None


def test_two_problems_in_one_package(make_fixture):
    path = make_fixture()
    shutil.copyfile(path, path.parent / "problem_copy.json")
    assert_isolated(validator.validate_package(path.parent)["(package)"],
                    "a package carries one input problem, but this one has 2")


def test_two_results_in_one_package(make_fixture):
    path = make_fixture()
    shutil.copyfile(path.parent / "result_template.json", path.parent / "result_copy.json")
    assert_isolated(validator.validate_package(path.parent)["(package)"],
                    "a package carries at most one result, but this one has 2")


def test_a_csv_nothing_refers_to_warns(make_fixture):
    path = make_fixture()
    (path.parent / "notes.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    assert_isolated(validator.validate_package(path.parent)["(package)"],
                    "notes.csv sits in the package but nothing refers to it",
                    want_error=False)


def test_a_menu_the_problem_forgot_to_name_warns(make_fixture):
    """The case the check exists for: without it the menu is silently ignored."""
    path = make_fixture(mutate_problem=lambda d: d.pop("schedules"))
    assert_isolated(validator.validate_package(path.parent)["(package)"],
                    "schedules_template.csv sits in the package", want_error=False)


# -- the CLI -----------------------------------------------------------------

def test_cli_exits_zero_on_a_clean_package():
    rc, out, err = run_cli("templates", json_output=False)
    assert rc == 0, (out, err)
    assert "OK" in out


def test_cli_exits_one_on_a_package_that_really_fails(make_fixture):
    """Not on a missing path -- that also returns 1, from argument handling."""
    path = make_fixture(mutate_problem=lambda d: d.update(schemaVersion="3.0"))
    rc, out, err = run_cli(path.parent, json_output=False)
    assert rc == 1, (out, err)
    assert "FAIL" in out and "ERROR" in out


def test_cli_reports_a_missing_path_on_stderr():
    rc, out, err = run_cli("no/such/place", json_output=False)
    assert rc == 1
    assert "no such file or directory" in err
    assert "FAIL" not in out, "a bad argument must not look like a failed validation"


def test_cli_json_carries_the_whole_report(make_fixture):
    path = make_fixture(mutate_problem=lambda d: d.update(schemaVersion="3.0"))
    rc, out, _ = run_cli(path.parent)
    import json
    payload = json.loads(out)
    entry = next(iter(payload.values()))["problem_template.json"]
    assert entry["ok"] is False
    assert entry["errors"] and "stats" in entry and "warnings" in entry


def test_cli_verbose_prints_stats():
    rc, out, _ = run_cli("templates", "-v", json_output=False)
    assert "employees:" in out and "openDays:" in out


def test_cli_against_names_the_problem(lone_result):
    rc, out, _ = run_cli(lone_result, "--against", C2 / "problem.json", json_output=False)
    assert rc == 0, out
    assert "cross-checks were skipped" not in out


def test_cli_on_a_directory_with_no_documents(tmp_path):
    rc, out, _ = run_cli(tmp_path, json_output=False)
    assert rc == 1
    assert "no JSON documents found" in out

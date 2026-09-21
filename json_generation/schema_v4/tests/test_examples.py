"""The shipped bundles, and the facts about them the docs assert."""

from helpers import C1, C2, CATALOGUE, EXAMPLES, TEMPLATES, load, validate


def test_cenario2_validates():
    r = validate(C2 / "problem.json")
    assert r.ok, r.errors


def test_templates_validate_with_no_warnings():
    r = validate(TEMPLATES / "problem_template.json")
    assert r.ok and not r.warnings, (r.errors, r.warnings)


def test_cenario2_only_warns_about_things_the_readme_names():
    r = validate(C2 / "problem.json")
    for w in r.warnings:
        assert ("competence level is ambiguous" in w
                or "which no cell uses" in w), f"undocumented warning: {w}"


def test_cenario1_fails_for_the_three_documented_reasons():
    """Its README claims three independent defects; this is the claim, checked."""
    r = validate(C1 / "problem.json")
    assert not r.ok
    assert any("432 is not a multiple of the 30-minute grid" in e for e in r.errors)
    assert any("holds no competencies" in w for w in r.warnings)
    assert any("every day is closed" in w for w in r.warnings)


def test_cenario1_grid_clash_does_not_flood_the_report():
    r = validate(C1 / "problem.json")
    assert len(r.errors) < 10, f"{len(r.errors)} errors; repeats should collapse"
    assert r.stats["diagnostics"] == 335


def test_both_examples_declare_version_four():
    for path in (C1 / "problem.json", C2 / "problem.json"):
        assert load(path)["schemaVersion"] == "4.0"


def test_no_example_carries_a_sisqual_misspelling():
    for path in EXAMPLES.rglob("problem.json"):
        blob = path.read_text(encoding="utf-8")
        for bad in ("contractAssigments", "priorityHierachy", "inpUAHolidaysCollection"):
            assert bad not in blob, f"{bad} in {path}"


def test_the_catalogue_is_on_a_finer_grid_than_the_bundles_declare():
    """The finding behind next_meeting.md item 6: 914 codes are unreachable."""
    from schema_v4 import core
    catalogue, _ = core.read_schedules(CATALOGUE)
    off = [s for s in catalogue.values()
           if s.interval and not (core.on_grid(s.interval.start, 30)
                                  and core.on_grid(s.interval.end, 30))]
    assert len(off) == 914


def test_the_with_meal_code_is_absent_from_the_catalogue():
    """next_meeting.md item 5, as a test rather than a claim."""
    from schema_v4 import core
    catalogue, _ = core.read_schedules(CATALOGUE)
    assert 100154 not in catalogue

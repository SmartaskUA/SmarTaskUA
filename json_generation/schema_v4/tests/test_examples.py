"""The shipped bundles, and the facts about them the docs assert."""

from helpers import C2, CATALOGUE, EXAMPLES, TEMPLATES, load, validate


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
                or "which no cell uses" in w
                or "do not land on the 30-minute grid" in w), f"undocumented warning: {w}"


def test_the_example_declares_version_four():
    assert load(C2 / "problem.json")["schemaVersion"] == "4.0"


def test_cenario2_is_the_only_shipped_example():
    """Cenario 1 was dropped: it fails three independent ways. See next_meeting.md 20."""
    assert sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir()) == ["cenario2_retail"]


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

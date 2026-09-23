"""The shipped example, and the claims its README and the docs make about it."""

from helpers import C2, EXAMPLES, TEMPLATES, load, validate

DOCUMENTED_WARNINGS = (
    "competence level is ambiguous",     # three employees hold a coordinate twice
    "which no cell uses",                # NOT is declared but unused
)


def test_the_example_validates():
    r = validate(C2 / "problem.json")
    assert r.ok, r.errors


def test_the_result_validates():
    r = validate(C2 / "result.json")
    assert r.ok, r.errors


def test_templates_validate_with_no_warnings():
    """The control the whole suite leans on. If this goes, every isolation
    assertion elsewhere is measuring noise. Both forms, because a result template
    that drifted from its problem would be a broken starting point."""
    for name in ("problem_template.json", "result_template.json"):
        r = validate(TEMPLATES / name)
        assert r.ok and not r.warnings, (name, r.errors, r.warnings)


def test_the_templates_ship_both_forms():
    from schema_v4 import validator
    forms = validator.validate_package(TEMPLATES)["(package)"].stats["forms"]
    assert forms == ["input", "result"]


def test_the_result_template_sidecar_is_exactly_what_it_uses():
    from schema_v4 import core
    used = {e["ScheduleCode"] for e in load(TEMPLATES / "result_template.json")
            ["OutRosterTeamDays"]}
    sidecar, _ = core.read_schedules(TEMPLATES / "result_template_schedules.csv")
    assert set(sidecar) == used


def test_every_example_warning_is_one_the_readme_names():
    r = validate(C2 / "problem.json")
    assert r.warnings, "if this ever empties, tighten the allow-list below"
    for w in r.warnings:
        assert any(known in w for known in DOCUMENTED_WARNINGS), f"undocumented: {w}"


def test_the_example_declares_version_four():
    assert load(C2 / "problem.json")["schemaVersion"] == "4.0"


def test_cenario1_is_not_shipped():
    """It fails three independent ways; see next_meeting.md item 21 ("the scenario we had to drop")."""
    names = [p.name for p in EXAMPLES.iterdir() if p.is_dir()]
    assert "cenario1_nlm" not in names


def test_no_example_carries_a_sisqual_misspelling():
    for path in EXAMPLES.rglob("problem.json"):
        blob = path.read_text(encoding="utf-8")
        for bad in ("contractAssigments", "priorityHierachy", "inpUAHolidaysCollection"):
            assert bad not in blob, f"{bad} in {path}"


def test_the_result_needs_no_substitutions():
    """Our own menu carries every contracted length, so nothing is approximated."""
    doc = load(C2 / "result.json")
    assert doc["_comment_substitutions"] == [
        "none - every worked day got a shift of exactly the contracted length"]


def test_the_menu_covers_every_contract_length():
    from schema_v4 import core
    problem = load(C2 / "problem.json")
    catalogue, _ = core.read_schedules(C2 / problem["schedules"]["dataFile"])
    offered = {s.weight_minutes for s in catalogue.values() if s.interval}
    needed = {c["workMinutesPerDay"] for c in problem["contracts"]["definitions"]}
    assert needed <= offered, f"no shift for {sorted(needed - offered)} min"


def test_every_menu_shift_lands_on_the_problems_grid():
    from schema_v4 import core
    problem = load(C2 / "problem.json")
    slot = problem["timeGrid"]["slotMinutes"]
    catalogue, _ = core.read_schedules(C2 / problem["schedules"]["dataFile"])
    off = [s.code for s in catalogue.values()
           if s.interval and not (core.on_grid(s.interval.start, slot)
                                  and core.on_grid(s.interval.end, slot))]
    assert not off, f"codes a solver on this grid could not emit: {off}"

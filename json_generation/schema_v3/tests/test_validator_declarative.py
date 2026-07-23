"""Declarative validation: the control fixture is clean, and each broken fixture
raises exactly the right complaint -- feasibility diagnoses, structural infeasibility,
tier-3 integrity, priorityOrder, and the removed-block / typo guards."""
from helpers import SIS, assert_isolated, validate

DEMAND_HEADER = ["date", "workPeriod", "competency", "minimum", "empiric", "maximum", "start", "end"]
_BASE = [[f"2030-10-0{d}", wp, "TeamA", 1, 2, 2, "", ""]
         for d in range(1, 8) for wp in ["MORNING", "AFTERNOON", "NIGHT"]]


def test_control_fixture_is_clean(make_fixture):
    rep = validate(make_fixture() / "problem.json")
    assert not rep.errors and not rep.warnings, (rep.errors[:2], rep.warnings[:2])


# -- demand invariant (0 = unset; real inversion fails) --
def _demand_bound_errors(make_fixture, rows):
    rep = validate(make_fixture(demand_rows=[DEMAND_HEADER] + rows) / "problem.json")
    return [e for e in rep.errors if any(w in e for w in ("minimum", "empiric", "maximum"))]


def test_demand_min_le_emp_le_max_accepted(make_fixture):
    assert not _demand_bound_errors(make_fixture, _BASE)


def test_demand_zero_bounds_are_unset(make_fixture):
    assert not _demand_bound_errors(make_fixture, [r[:3] + [1, 0, 0, "", ""] for r in _BASE])


def test_demand_real_inversion_rejected(make_fixture):
    assert _demand_bound_errors(make_fixture, [r[:3] + [2, 1, 3, "", ""] for r in _BASE])


# -- v2.6 hours-in-cells guard --
def test_unmigrated_hours_cell_rejected(make_fixture):
    rep = validate(make_fixture(schedule_rows={("EMP001", "2030-10-01"): "8"}) / "problem.json")
    assert any("MINUTES" in e for e in rep.errors), rep.errors[:1]


# -- the regression: the three original v2.6 cells are caught --
def test_three_original_v26_cells_all_caught(make_fixture):
    d = make_fixture(schedule_rows={
        ("EMP001", "2030-10-04"): "EQUALS:08:00-16:00",
        ("EMP008", "2030-10-02"): "EQUALS:08:00-16:00",
        ("EMP005", "2030-10-06"): "INCLUDE:08:00-20:00",
    })
    impossible = [e for e in validate(d / "problem.json").errors if "can never be satisfied" in e]
    assert len(impossible) == 3
    assert any("outside the operating window" in e and "EQUALS:08:00-16:00" in e for e in impossible)
    assert any("no single block can contain them" in e and "INCLUDE:08:00-20:00" in e for e in impossible)


# -- Tier 1 diagnoses --
def test_except_swallows_window(make_fixture):
    assert_isolated(validate(make_fixture(schedule_rows={("EMP003", "2030-10-01"): "EXCEPT:08:00-23:59"}) / "problem.json"),
                    "leaves no room")


def test_within_window_too_short_is_infeasible(make_fixture):
    # a 3h window can't hold an 8h block -> the opposite failure to INCLUDE:08:00-20:00
    assert_isolated(validate(make_fixture(schedule_rows={("EMP003", "2030-10-01"): "WITHIN:08:00-11:00"}) / "problem.json"),
                    "no window leaves room")


def test_within_wide_window_is_feasible(make_fixture):
    # an 8h block fits inside a 12h window -> clean (contrast INCLUDE:08:00-20:00, which is not)
    rep = validate(make_fixture(schedule_rows={("EMP003", "2030-10-01"): "WITHIN:08:00-20:00"}) / "problem.json")
    assert not any("can never be satisfied" in e for e in rep.errors), rep.errors[:2]


def test_duration_exceeds_window(make_fixture):
    assert_isolated(validate(make_fixture(schedule_rows={("EMP003", "2030-10-01"): "1500"}) / "problem.json"),
                    "exceeds the operating window")


def test_off_grid_numeric_cell(make_fixture):
    assert_isolated(validate(make_fixture(schedule_rows={("EMP003", "2030-10-01"): "470"}) / "problem.json"),
                    "not a multiple of the 15-minute grid")


# -- Tier 2 structural --
def test_compelled_six_consecutive_open_days(make_fixture):
    d = make_fixture(schedule_rows={("EMP001", day): "A" for day in
                                    ["2030-10-01", "2030-10-02", "2030-10-03", "2030-10-04",
                                     "2030-10-05", "2030-10-06", "2030-10-07"]})
    assert_isolated(validate(d / "problem.json"), "6 consecutive open days")


def test_contract_minutes_off_grid(make_fixture):
    d = make_fixture(lambda p: p["contracts"]["definitions"].append(
        {"id": "odd", "name": "odd", "workMinutesPerDay": 475}))
    assert_isolated(validate(d / "problem.json"), "no assignment block can ever align")


def _one_capped(constraint):
    def m(p):
        p["contracts"]["definitions"].append(
            {"id": "capped", "name": "capped", "workMinutesPerDay": 480, "constraints": constraint})
        p["employees"]["list"][0]["contractAssignments"] = [
            {"contractType": "capped", "start": "2025-01-01", "end": None}]
    return m


def test_weekly_cap_unsatisfiable(make_fixture):
    assert_isolated(validate(make_fixture(_one_capped({"maxMinutesPerWeek": 600})) / "problem.json"),
                    "maxMinutesPerWeek")


def test_min_rest_days_unsatisfiable(make_fixture):
    assert_isolated(validate(make_fixture(_one_capped({"minRestDaysPerWeek": 5})) / "problem.json"),
                    "rest days")


# -- Tier 3 integrity --
def test_vac_as_preferable_rejected(make_fixture):
    d = make_fixture(lambda p: p["scheduleInput"]["dayOffCodes"]["VAC"].__setitem__("kind", "preferable"))
    assert_isolated(validate(d / "problem.json"), "unavailable by definition")


def test_undeclared_code_rejected(make_fixture):
    assert_isolated(validate(make_fixture(schedule_rows={("EMP001", "2030-10-01"): "XYZ"}) / "problem.json"),
                    "undeclared code")


def test_dayoffcode_missing_kind_is_schema_error(make_fixture):
    d = make_fixture(lambda p: p["scheduleInput"]["dayOffCodes"].__setitem__("BAD", {}),
                     schedule_rows={("EMP001", "2030-10-01"): "BAD"})
    assert_isolated(validate(d / "problem.json"), "schema")


def test_unmigrated_v26_demand_header_rejected(make_fixture):
    v26 = [["date", "workPeriod", "team", "minimum", "ideal", "estimated", "start", "end"]] + \
          [[f"2030-10-0{i}", wp, "TeamA", 1, 2, 2, "", ""] for i in range(1, 8)
           for wp in ["MORNING", "AFTERNOON", "NIGHT"]]
    assert_isolated(validate(make_fixture(demand_rows=v26) / "problem.json"), "v2.6 header")


def test_leftover_restrictions_block_rejected(make_fixture):
    d = make_fixture(lambda p: p["employees"]["list"][0].__setitem__(
        "restrictions", {"blackoutDates": ["2030-10-01"]}))
    assert_isolated(validate(d / "problem.json"), "restrictions")


def test_leftover_breaks_block_rejected(make_fixture):
    d = make_fixture(lambda p: p["demand"]["workPeriods"][0].__setitem__(
        "breaks", [{"type": "meal", "durationMinutes": 30}]))
    assert_isolated(validate(d / "problem.json"), "breaks")


# -- priorityOrder --
def _po(entries):
    return lambda p: p["demand"].__setitem__("priorityOrder", entries)


def test_priority_duplicate_order(make_fixture):
    # both entries name a level the fixture's employees actually hold (all are level 1),
    # so the duplicate order is the only finding
    d = make_fixture(_po([{"order": 1, "competency": "TeamA", "level": 1},
                          {"order": 1, "competency": "TeamA"}]))
    assert_isolated(validate(d / "problem.json"), "order must be unique")


def test_priority_unknown_competency(make_fixture):
    assert_isolated(validate(make_fixture(_po([{"order": 1, "competency": "Nope"}])) / "problem.json"),
                    "unknown competency")


def test_priority_bare_competency_shadows_later(make_fixture):
    d = make_fixture(_po([{"order": 1, "competency": "TeamA"}, {"order": 2, "competency": "TeamA", "level": 1}]))
    assert_isolated(validate(d / "problem.json"), "unreachable", want_error=False)


def test_priority_order_drives_not_array_position(make_fixture):
    d = make_fixture(_po([{"order": 2, "competency": "TeamA", "level": 1}, {"order": 1, "competency": "TeamA"}]))
    assert_isolated(validate(d / "problem.json"), "unreachable", want_error=False)


# -- removed solve-directive blocks / typo guard --
def test_leftover_optimization_rejected(make_fixture):
    d = make_fixture(lambda p: p.__setitem__("optimization", {"algorithm": "CSPv2"}))
    assert_isolated(validate(d / "problem.json"), "'optimization' was removed")


def test_leftover_constraints_rejected(make_fixture):
    d = make_fixture(lambda p: p.__setitem__(
        "constraints", {"hard": [{"id": "min-rest", "type": "min_rest_minutes", "params": {"minutes": 660}}]}))
    assert_isolated(validate(d / "problem.json"), "'constraints' was removed")


def test_typo_in_closed_object_rejected(make_fixture):
    d = make_fixture(lambda p: p["contracts"]["definitions"][0].__setitem__("workMinutsPerDay", 480))
    assert_isolated(validate(d / "problem.json"), "not allowed")


def test_stray_key_at_open_root_accepted(make_fixture):
    assert validate(make_fixture(lambda p: p.__setitem__("_comment_note", "kept")) / "problem.json").ok


def test_reversed_temporal_scope_rejected(make_fixture):
    d = make_fixture(lambda p: p.__setitem__("temporalScope", {"start": "2030-10-07", "end": "2030-10-01"}))
    assert_isolated(validate(d / "problem.json"), "after end")

"""One broken fixture per finding. The templates package is the control."""

import pytest
from helpers import TEMPLATES, assert_isolated, assert_reports, validate

HEADER = "date,tableName,tableValue,minimum,ideal,estimated,start,end\n"


def test_the_control_is_clean():
    """If this fails, every isolation assertion below is measuring noise."""
    r = validate(TEMPLATES / "problem_template.json")
    assert r.ok, r.errors
    assert not r.warnings, r.warnings


# -- the demand CSVs ---------------------------------------------------------
#
# Each case appends a single row to the control, so open_days, the week buckets
# and the reachability sets stay exactly as they were and the report stays
# isolated. Replacing the whole file would collapse the horizon to one date and
# silently disable most of the structural pass.

@pytest.mark.parametrize("row, needle, want_error", [
    ("2026-03-02,Piso,T1,1,0,0,17:00,21:00",
     "Piso/T1 is not in demand.dimensions", True),
    ("2026-03-02,Team,T1,1,0,0,,",
     "start/end are mandatory", True),
    ("2026-03-02,Team,T1,1,0,0,17:10,21:00",
     "does not land on the 30-minute grid", True),
    ("2026-04-02,Team,T1,1,0,0,09:00,13:00",
     "lies outside temporalScope", True),
    ("2026-03-02,Team,T1,-1,0,0,17:00,21:00",
     "minimum is negative", True),
    ("2026-03-02,Team,T1,1,0,0,09:00,13:00",
     "duplicate row", True),
    ("2026-03-02,Team,T1,1,0,0,12:00,13:00",
     "counts toward both", False),
])
def test_one_bad_demand_row(make_fixture, row, needle, want_error):
    """Exactly one finding of the expected kind. A second, unrelated finding is
    tolerated -- an out-of-dimension row is also un-staffable, for instance -- but
    the named one must fire once and only once."""
    assert_reports(validate(make_fixture(add_demand=[row])), needle, want_error)


def test_no_ordering_is_enforced_between_the_three_values(make_fixture):
    """Deliberate: v3.0 was ascending, v2.6 was not, and the data cannot settle it."""
    r = validate(make_fixture(add_demand=["2026-03-02,Team,T1,3,1,2,17:00,21:00"]))
    assert r.ok, r.errors
    assert not any("ideal" in f or "estimated" in f
                   for f in r.errors + r.warnings), (r.errors, r.warnings)


def test_a_missing_demand_file(make_fixture):
    def mutate(d):
        d["demand"]["dataFileDays"] = "absent.csv"
    assert_isolated(validate(make_fixture(mutate_problem=mutate)), "file not found")


def test_a_demand_header_that_is_missing_a_column(make_fixture):
    r = validate(make_fixture(demand_rows="date,tableName,minimum\n2026-03-02,Team,1\n"))
    assert any("missing column(s)" in e for e in r.errors), r.errors


def test_the_workload_grain_is_not_counted_as_heads(make_fixture):
    """days states MINUTES. 960 of them must not read as 960 people."""
    r = validate(TEMPLATES / "problem_template.json")
    assert r.stats["demandRows.days"] == 5, "the rows must actually be read"
    assert not any("960" in w for w in r.warnings), r.warnings


def test_a_day_with_no_windowed_row_anywhere_is_closed(make_fixture):
    """All three grains empty, not just periods -- shifts also opens days."""
    def mutate(d):
        for key in ("dataFileDays", "dataFilePeriods", "dataFileShifts"):
            d["demand"][key] = "periods_demand_template.csv"
    r = validate(make_fixture(mutate_problem=mutate, demand_rows=HEADER))
    assert any("every day is closed" in w for w in r.warnings), r.warnings


# -- schedule_input.csv ------------------------------------------------------

def test_a_v3_minute_cell_is_rejected_as_unconverted(make_fixture):
    r = validate(make_fixture(schedule_rows={("EMP001", "2026-03-02"): "480"}))
    assert_reports(r, "never converted")


def test_undeclared_cell_code_is_rejected(make_fixture):
    r = validate(make_fixture(schedule_rows={("EMP001", "2026-03-02"): "FDO"}))
    assert_reports(r, "not declared in scheduleInput.dayOffCodes")


def test_a_bad_cell_is_reported_once_not_twice(make_fixture):
    """Two readers see every cell. Only the preflight reports it."""
    r = validate(make_fixture(schedule_rows={("EMP001", "2026-03-02"): "480"}))
    assert len(r.errors) == 1, r.errors


def test_hours_that_contradict_the_contract_warn_and_do_not_error(make_fixture):
    """A numeric cell overrides the contract length; that is an instruction,
    not an impossibility."""
    r = validate(make_fixture(schedule_rows={("EMP001", "2026-03-02"): "6"}))
    assert r.ok, r.errors
    assert_isolated(r, "360 min but contract FT_8h states 480", want_error=False)


def test_a_schedule_input_with_the_wrong_number_of_columns(make_fixture):
    def mutate(d):
        d["temporalScope"]["end"] = "2026-03-09"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("date columns but temporalScope spans" in e for e in r.errors), r.errors


def test_an_employee_with_no_row(make_fixture):
    def mutate(d):
        d["employees"]["list"].append({
            "id": "EMP099", "name": "Ghost",
            "contractAssignments": [{"contractType": "FT_8h", "start": "2024-01-01",
                                     "end": None}],
            "competencyAssignments": [{"tableName": "Team", "tableValue": "T1",
                                       "level": 1, "start": "2024-01-01", "end": None}]})
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("EMP099 has no row" in e for e in r.errors), r.errors


# -- day-off codes -----------------------------------------------------------

def test_an_empty_day_off_palette(make_fixture):
    def mutate(d):
        d["scheduleInput"]["dayOffCodes"] = {}
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("dayOffCodes is empty" in e for e in r.errors), r.errors


def test_an_unclassified_day_off_code(make_fixture):
    def mutate(d):
        d["scheduleInput"]["dayOffCodes"]["DO"]["kind"] = "maybe"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("must be 'preferable' or 'unavailable'" in e for e in r.errors), r.errors


def test_a_blank_day_off_code(make_fixture):
    def mutate(d):
        d["scheduleInput"]["dayOffCodes"][" "] = {"kind": "preferable"}
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("a code is blank" in e for e in r.errors), r.errors


# -- feasibility -------------------------------------------------------------

def test_contract_off_the_grid_is_reported_once_then_collapsed(make_fixture):
    """432 minutes on a 30-minute grid: nothing can be placed on any day."""
    def mutate(d):
        d["contracts"]["definitions"][0]["workMinutesPerDay"] = 432
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("432 is not a multiple of the 30-minute grid" in e for e in r.errors), r.errors
    # Only `A` and `EQUALS` cells take their length from the contract, so the
    # diagnostics stay under the collapse threshold; the per-cell hours mismatch
    # does not, and that is where the grouping shows.
    assert any("with the same cause" in w for w in r.warnings), \
        "repeats of one cause must collapse, not flood the report"


def test_work_on_a_day_no_contract_covers(make_fixture):
    def mutate(d):
        d["employees"]["list"][0]["contractAssignments"][0]["end"] = "2026-03-03"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("no contract covers" in e for e in r.errors), r.errors


def test_dangling_contract_reference(make_fixture):
    def mutate(d):
        d["contracts"]["definitions"] = [c for c in d["contracts"]["definitions"]
                                         if c["id"] != "FT_8h"]
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("unknown contract 'FT_8h'" in e for e in r.errors), r.errors
    assert any("is not in contracts.definitions" in e for e in r.errors), r.errors


def test_an_operator_window_off_the_grid(make_fixture):
    r = validate(make_fixture(
        schedule_rows={("EMP001", "2026-03-04"): "EQUALS:09:10-17:10"}))
    assert any("does not land on the 30-minute grid" in e for e in r.errors), r.errors


# -- structural --------------------------------------------------------------

def test_max_consecutive_work_days_is_enforced_per_employee(make_fixture):
    """The walk breaks after the first run, so one finding per tripping employee.
    With the control at cap 2 that is EMP001, EMP002 and EMP004 -- EMP003 never
    reaches three in a row."""
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"]["MaxConsecutiveWorkDays"] = 2
    r = validate(make_fixture(mutate_problem=mutate))
    assert_reports(r, "days in a row", count=3)


def test_a_disabled_constraint_is_not_enforced(make_fixture):
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"]["MaxConsecutiveWorkDays"] = 2
        d["constraints"]["hard"][0]["enabled"] = False
    r = validate(make_fixture(mutate_problem=mutate))
    assert not any("days in a row" in e for e in r.errors), r.errors


def test_a_closed_day_breaks_a_run(make_fixture):
    """A day with no demand is not worked, so it resets the streak."""
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"]["MaxConsecutiveWorkDays"] = 3
    rows = HEADER + "".join(
        f"2026-03-0{n},Team,T1,1,0,0,09:00,13:00\n" for n in (2, 3, 5, 6))
    r = validate(make_fixture(mutate_problem=mutate, demand_rows=rows))
    assert not any("days in a row" in e for e in r.errors), r.errors


def test_a_blank_cell_counts_as_working(make_fixture):
    """It is in neither day-off set, so the consecutive walk treats it as work.
    Stated here because it is surprising and nothing else records it."""
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"]["MaxConsecutiveWorkDays"] = 6
    r = validate(make_fixture(
        mutate_problem=mutate,
        schedule_rows={("EMP001", "2026-03-06"): "", ("EMP001", "2026-03-07"): ""}))
    assert any("7 days in a row" in e for e in r.errors), r.errors


def test_more_working_days_in_a_week_than_the_cap(make_fixture):
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"]["MaxConsecutiveWorkDaysInWeek"] = 3
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("exceeds MaxConsecutiveWorkDaysInWeek" in e for e in r.errors), r.errors


# -- priorityHierarchy -------------------------------------------------------

def test_duplicate_rank_is_rejected(make_fixture):
    def mutate(d):
        d["priorityHierarchy"][1]["rank"] = 1
    assert_isolated(validate(make_fixture(mutate_problem=mutate)), "duplicate rank 1")


def test_inverted_ability_range_is_rejected(make_fixture):
    """min is the SMALLER number, because level 1 is the highest."""
    def mutate(d):
        d["priorityHierarchy"][0]["minAbilityLevel"] = 9
        d["priorityHierarchy"][0]["maxAbilityLevel"] = 1
    assert_isolated(validate(make_fixture(mutate_problem=mutate)),
                    "minAbilityLevel 9 is above maxAbilityLevel 1")


def test_a_rank_naming_an_undeclared_coordinate(make_fixture):
    def mutate(d):
        d["priorityHierarchy"][0]["tableValue"] = "T9"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("Team/T9 is not in demand.dimensions" in e for e in r.errors), r.errors


def test_a_rank_that_fills_nothing(make_fixture):
    def mutate(d):
        d["demand"]["dimensions"].append({"tableName": "Team", "tableValue": "T9"})
        d["priorityHierarchy"][0]["tableValue"] = "T9"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("never demanded, so this rank fills nothing" in w
               for w in r.warnings), r.warnings


# -- reachability ------------------------------------------------------------

def test_unused_day_off_code_warns(make_fixture):
    def mutate(d):
        d["scheduleInput"]["dayOffCodes"]["ZZZ"] = {"kind": "unavailable"}
    assert_isolated(validate(make_fixture(mutate_problem=mutate)),
                    "declares 'ZZZ', which no cell uses", want_error=False)


def test_a_dimension_nobody_holds(make_fixture):
    def mutate(d):
        d["demand"]["dimensions"].append({"tableName": "Team", "tableValue": "T9"})
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("Team/T9 is declared but nobody holds it" in w for w in r.warnings), r.warnings
    assert any("Team/T9 is declared but never demanded" in w for w in r.warnings), r.warnings


def test_demand_above_the_available_headcount_warns(make_fixture):
    r = validate(make_fixture(add_demand=["2026-03-02,Team,T1,9,0,0,17:00,21:00"]))
    assert_isolated(r, "asks for up to 9 workers but only 4 hold it", want_error=False)


# -- the menu ----------------------------------------------------------------

def test_a_missing_menu_file(make_fixture):
    def mutate(d):
        d["schedules"]["dataFile"] = "absent.csv"
    assert_isolated(validate(make_fixture(mutate_problem=mutate)), "file not found")


def test_menu_codes_off_the_grid_warn(make_fixture):
    rows = ("code,description,scheduleWeightMinutes,startMin,endMin\n"
            "9001,09:10-13:10,240,550,790\n")
    assert_isolated(validate(make_fixture(schedules_rows=rows)),
                    "do not land on the 30-minute grid", want_error=False)


def test_a_menu_weight_that_contradicts_its_window(make_fixture):
    rows = ("code,description,scheduleWeightMinutes,startMin,endMin\n"
            "9001,09:00-13:00,999,540,780\n")
    assert_isolated(validate(make_fixture(schedules_rows=rows)),
                    "differs from scheduleWeightMinutes", want_error=False)

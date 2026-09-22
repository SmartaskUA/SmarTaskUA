"""One broken fixture per finding. The templates package is the control."""

from helpers import TEMPLATES, assert_isolated, validate


def test_the_control_is_clean():
    """If this ever fails, every isolation assertion below is meaningless."""
    r = validate(TEMPLATES / "problem_template.json")
    assert r.ok, r.errors
    assert not r.warnings, r.warnings


# -- version and the adapter hand-off ---------------------------------------

def test_a_sisqual_stamped_file_points_at_the_adapter(make_fixture):
    def mutate(d):
        d["schemaVersion"] = "3.0"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("sisqual_adapt" in e for e in r.errors), r.errors


# -- Tier 3: the coordinate catalogue ---------------------------------------

def test_empty_dimensions_is_an_error(make_fixture):
    def mutate(d):
        d["demand"]["dimensions"] = []
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("demand.dimensions is empty" in e for e in r.errors), r.errors


def test_undeclared_coordinate_on_an_employee(make_fixture):
    def mutate(d):
        d["employees"]["list"][0]["competencyAssignments"][0]["tableName"] = "Equipa"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("Equipa/T1 is not in demand.dimensions" in e for e in r.errors), r.errors


def test_undeclared_coordinate_in_the_demand_csv(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Piso,T1,1,0,0,09:00,13:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("Piso/T1 is not in demand.dimensions" in e for e in r.errors), r.errors


# -- Tier 3: the demand CSVs ------------------------------------------------

def test_window_is_mandatory_on_the_periods_grain(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Team,T1,1,0,0,,\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("start/end are mandatory" in e for e in r.errors), r.errors


def test_off_grid_window_is_rejected(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Team,T1,1,0,0,09:10,13:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("does not land on the 30-minute grid" in e for e in r.errors), r.errors


def test_date_outside_the_horizon_is_rejected(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-04-02,Team,T1,1,0,0,09:00,13:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("lies outside temporalScope" in e for e in r.errors), r.errors


def test_duplicate_demand_row_is_rejected(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Team,T1,1,0,0,09:00,13:00\n"
            "2026-03-02,Team,T1,2,0,0,09:00,13:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("duplicate row" in e for e in r.errors), r.errors


def test_overlapping_windows_warn_about_double_counting(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Team,T1,1,0,0,09:00,13:00\n"
            "2026-03-02,Team,T1,1,0,0,12:00,17:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("counts toward both" in w for w in r.warnings), r.warnings


def test_no_ordering_is_enforced_between_the_three_values(make_fixture):
    """Deliberate: v3.0 was ascending, v2.6 was not, and the data cannot settle it."""
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Team,T1,3,1,2,09:00,13:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert not any("ideal" in e or "estimated" in e for e in r.errors), r.errors


def test_negative_demand_is_rejected(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Team,T1,-1,0,0,09:00,13:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("minimum is negative" in e for e in r.errors), r.errors


def test_workload_minutes_are_not_read_as_a_headcount(make_fixture):
    """The days grain is minutes; 960 of them must not read as 960 people."""
    r = validate(TEMPLATES / "problem_template.json")
    assert not any("960 workers" in w for w in r.warnings), r.warnings


# -- Tier 3: schedule_input -------------------------------------------------

def test_a_v3_minute_cell_is_rejected_as_unconverted(make_fixture):
    r = validate(make_fixture(schedule_rows={("EMP001", "2026-03-02"): "480"}))
    assert any("never converted" in e for e in r.errors), r.errors


def test_undeclared_cell_code_is_rejected(make_fixture):
    r = validate(make_fixture(schedule_rows={("EMP001", "2026-03-02"): "FDO"}))
    assert any("not declared in scheduleInput.dayOffCodes" in e for e in r.errors), r.errors


def test_hours_that_contradict_the_contract_warn(make_fixture):
    r = validate(make_fixture(schedule_rows={("EMP001", "2026-03-02"): "6"}))
    assert any("360 min but contract FT_8h states 480" in w for w in r.warnings), r.warnings


# -- Tier 1: feasibility, and the grid --------------------------------------

def test_contract_off_the_grid_is_reported_once_then_collapsed(make_fixture):
    """The cenario1_nlm failure, reproduced: 432 minutes on a 30-minute grid."""
    def mutate(d):
        d["contracts"]["definitions"][0]["workMinutesPerDay"] = 432
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("432 is not a multiple of the 30-minute grid" in e for e in r.errors), r.errors
    assert any("with the same cause" in e for e in r.errors), \
        "repeats of one cause should collapse, not flood the report"


def test_work_on_a_day_no_contract_covers(make_fixture):
    def mutate(d):
        d["employees"]["list"][0]["contractAssignments"][0]["end"] = "2026-03-03"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("no contract covers" in e for e in r.errors), r.errors


def test_dangling_contract_reference(make_fixture):
    """The July bundle's defect: an empty catalogue with live references."""
    def mutate(d):
        d["contracts"]["definitions"] = [c for c in d["contracts"]["definitions"]
                                         if c["id"] != "FT_8h"]
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("unknown contract 'FT_8h'" in e for e in r.errors), r.errors


# -- Tier 2: structural -----------------------------------------------------

def test_negative_n_wk_is_impossible(make_fixture):
    def mutate(d):
        d["scheduleInput"]["dayOffCodes"]["DO"]["kind"] = "unavailable"
    rows = {("EMP001", day): "VAC" for day in
            ("2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05",
             "2026-03-06", "2026-03-07", "2026-03-08")}
    r = validate(make_fixture(schedule_rows=rows))
    assert r.stats.get("negative_n_wk", 0) == 0     # 7 unavailable is exactly 0, not negative


def test_max_consecutive_work_days_is_enforced(make_fixture):
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"]["MaxConsecutiveWorkDays"] = 2
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("days in a row" in e for e in r.errors), r.errors


def test_a_disabled_constraint_is_not_enforced(make_fixture):
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"]["MaxConsecutiveWorkDays"] = 2
        d["constraints"]["hard"][0]["enabled"] = False
    r = validate(make_fixture(mutate_problem=mutate))
    assert not any("days in a row" in e for e in r.errors), r.errors


# -- Tier 3: priorityHierarchy ----------------------------------------------

def test_duplicate_rank_is_rejected(make_fixture):
    def mutate(d):
        d["priorityHierarchy"][1]["rank"] = 1
    r = validate(make_fixture(mutate_problem=mutate))
    assert_isolated(r, "duplicate rank 1")


def test_inverted_ability_range_is_rejected(make_fixture):
    """min is the SMALLER number, because level 1 is the highest."""
    def mutate(d):
        d["priorityHierarchy"][0]["minAbilityLevel"] = 9
        d["priorityHierarchy"][0]["maxAbilityLevel"] = 1
    r = validate(make_fixture(mutate_problem=mutate))
    assert_isolated(r, "minAbilityLevel 9 is above maxAbilityLevel 1")


# -- Tier 4: reachability ---------------------------------------------------

def test_unused_day_off_code_warns(make_fixture):
    def mutate(d):
        d["scheduleInput"]["dayOffCodes"]["ZZZ"] = {"kind": "unavailable"}
    r = validate(make_fixture(mutate_problem=mutate))
    assert_isolated(r, "declares 'ZZZ', which no cell uses", want_error=False)


def test_demand_above_the_available_headcount_warns(make_fixture):
    rows = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
            "2026-03-02,Team,T1,9,0,0,09:00,13:00\n"
            "2026-03-02,Responsibility,A,1,0,0,09:00,13:00\n")
    r = validate(make_fixture(demand_rows=rows))
    assert any("asks for up to 9 workers but only 4 hold it" in w
               for w in r.warnings), r.warnings


# -- the catalogue ----------------------------------------------------------

def test_catalogue_off_grid_warns(make_fixture):
    rows = ("code,description,scheduleWeightMinutes,startMin,endMin\n"
            "9001,09:10-13:10,240,550,790\n")
    r = validate(make_fixture(schedules_rows=rows))
    assert any("do not land on the 30-minute grid" in w for w in r.warnings), r.warnings


def test_catalogue_weight_mismatch_warns(make_fixture):
    rows = ("code,description,scheduleWeightMinutes,startMin,endMin\n"
            "9001,09:00-13:00,999,540,780\n")
    r = validate(make_fixture(schedules_rows=rows))
    assert any("differs from scheduleWeightMinutes" in w for w in r.warnings), r.warnings

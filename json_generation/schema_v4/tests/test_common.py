"""The shared layer: Report, report_grouped, and the checks both forms run."""

from helpers import assert_isolated, assert_reports, validate

from schema_v4.common import Report, _overlapping_pairs, report_grouped


# -- report_grouped ----------------------------------------------------------

def collect(items, keep=3):
    out = []
    report_grouped(out.append, items, keep=keep)
    return out


def test_grouping_is_a_no_op_below_the_threshold():
    items = [(f"c{i}", f"m{i}") for i in range(3)]
    assert collect(items) == ["m0", "m1", "m2"]


def test_exactly_keep_items_of_one_cause_do_not_collapse():
    items = [("same", f"m{i}") for i in range(3)]
    assert collect(items) == ["m0", "m1", "m2"]


def test_one_over_the_threshold_collapses_the_remainder():
    items = [("same", f"m{i}") for i in range(4)]
    assert collect(items) == ["m0", "m1", "m2",
                              "... and 1 more with the same cause (4 in total)"]


def test_the_total_counts_every_item_not_just_the_hidden_ones():
    items = [("same", f"m{i}") for i in range(21)]
    assert collect(items)[-1] == "... and 18 more with the same cause (21 in total)"


def test_causes_are_grouped_independently_and_keep_first_appearance_order():
    items = [("a", "a1"), ("b", "b1"), ("a", "a2"), ("a", "a3"), ("a", "a4")]
    assert collect(items, keep=2) == [
        "a1", "a2", "... and 2 more with the same cause (4 in total)", "b1"]


def test_nothing_in_nothing_out():
    assert collect([]) == []


def test_report_ok_tracks_errors_only():
    r = Report()
    assert r.ok
    r.warn("a warning")
    assert r.ok
    r.error("an error")
    assert not r.ok


# -- the overlap walk --------------------------------------------------------

def test_a_long_span_is_compared_against_every_later_one():
    """zip(spans, spans[1:]) would report only the first pair and miss the rest."""
    spans = [(0, 100), (10, 20), (30, 40), (50, 60)]
    pairs = list(_overlapping_pairs(spans))
    assert pairs == [((0, 100), (10, 20)), ((0, 100), (30, 40)), ((0, 100), (50, 60))]
    # zip(spans, spans[1:]) would have yielded only the first of those three.


def test_touching_spans_overlap_only_when_closed():
    assert list(_overlapping_pairs([(0, 10), (10, 20)], closed=True))
    assert not list(_overlapping_pairs([(0, 10), (10, 20)], closed=False))


def test_disjoint_spans_yield_nothing():
    assert not list(_overlapping_pairs([(0, 10), (20, 30), (40, 50)]))


# -- calendar ----------------------------------------------------------------

def test_a_malformed_holiday_date(make_fixture):
    """Reported twice on purpose: the schema's date pattern, then our own check."""
    r = validate(make_fixture(mutate_problem=lambda d:
                              d["calendar"]["holidays"][0].update(date="not-a-date")))
    assert_reports(r, "calendar.holidays: 'not-a-date' is not a date")
    assert_reports(r, "schema: calendar/holidays/0/date")


def test_a_repeated_holiday(make_fixture):
    def mutate(d):
        d["calendar"]["holidays"].append(dict(d["calendar"]["holidays"][0]))
    assert_isolated(validate(make_fixture(mutate_problem=mutate)), "appears twice")


def test_a_holiday_outside_the_horizon(make_fixture):
    def mutate(d):
        d["calendar"]["holidays"][0]["date"] = "2026-06-01"
        d["calendar"]["holidays"][0]["hasEve"] = False
    assert_isolated(validate(make_fixture(mutate_problem=mutate)),
                    "lies outside temporalScope", want_error=False)


def test_an_eve_outside_the_horizon(make_fixture):
    """The horizon opens on 2026-03-02, so its eve falls off the front."""
    def mutate(d):
        d["calendar"]["holidays"][0]["date"] = "2026-03-02"
    assert_isolated(validate(make_fixture(mutate_problem=mutate)),
                    "its eve lies outside temporalScope", want_error=False)


# -- version, grid, scope ----------------------------------------------------

def test_a_v3_document_is_pointed_at_the_migration_guide(make_fixture):
    def mutate(d):
        d["schemaVersion"] = "3.0"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("MIGRATION-3.0-to-4.0" in e for e in r.errors), r.errors
    assert not any("sisqual_adapt" in e for e in r.errors), "the adapter is gone"


def test_an_unknown_version(make_fixture):
    def mutate(d):
        d["schemaVersion"] = "9.9"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("must be '4.0'" in e for e in r.errors), r.errors


def test_a_slot_that_does_not_divide_the_day(make_fixture):
    def mutate(d):
        d["timeGrid"]["slotMinutes"] = 7
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("does not divide 1440" in e for e in r.errors), r.errors


def test_a_reversed_temporal_scope(make_fixture):
    def mutate(d):
        d["temporalScope"]["start"], d["temporalScope"]["end"] = \
            d["temporalScope"]["end"], d["temporalScope"]["start"]
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("is empty or reversed" in e for e in r.errors), r.errors


def test_an_unknown_week_start(make_fixture):
    def mutate(d):
        d["calendar"]["weekStart"] = "caturday"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("is not one of" in e for e in r.errors), r.errors


# -- contracts and employees -------------------------------------------------

def test_a_duplicate_contract_id(make_fixture):
    def mutate(d):
        d["contracts"]["definitions"].append(dict(d["contracts"]["definitions"][0]))
    assert_isolated(validate(make_fixture(mutate_problem=mutate)), "duplicate id 'FT_8h'")


def test_an_empty_contract_catalogue_warns_and_dangles(make_fixture):
    def mutate(d):
        d["contracts"]["definitions"] = []
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("contracts.definitions is empty" in w for w in r.warnings), r.warnings
    assert any("unknown contract" in e for e in r.errors), r.errors


def test_a_duplicate_employee_id(make_fixture):
    def mutate(d):
        d["employees"]["list"].append(dict(d["employees"]["list"][0]))
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("duplicate id 'EMP001'" in e for e in r.errors), r.errors


def test_overlapping_contract_assignments(make_fixture):
    def mutate(d):
        d["employees"]["list"][0]["contractAssignments"] = [
            {"contractType": "FT_8h", "start": "2024-01-01", "end": "2027-01-01"},
            {"contractType": "PT_4h", "start": "2025-01-01", "end": None},
        ]
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("overlaps" in e for e in r.errors), r.errors


def test_a_gap_in_contract_coverage(make_fixture):
    def mutate(d):
        d["employees"]["list"][0]["contractAssignments"][0]["start"] = "2026-03-05"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("coverage has a gap" in w for w in r.warnings), r.warnings


def test_an_employee_with_no_competencies(make_fixture):
    def mutate(d):
        d["employees"]["list"][0]["competencyAssignments"] = []
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("holds no competencies" in w for w in r.warnings), r.warnings


def test_the_same_competency_twice_at_the_same_level(make_fixture):
    def mutate(d):
        comps = d["employees"]["list"][0]["competencyAssignments"]
        comps.append(dict(comps[0]))
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("the same level 1 twice" in w for w in r.warnings), r.warnings


def test_the_same_competency_at_two_levels_says_which_to_take(make_fixture):
    def mutate(d):
        comps = d["employees"]["list"][0]["competencyAssignments"]
        twin = dict(comps[0])
        twin["level"] = 4
        comps.append(twin)
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("levels 1 and 4 at once" in w and "take 1" in w
               for w in r.warnings), r.warnings


# -- dimensions --------------------------------------------------------------

def test_a_duplicate_coordinate(make_fixture):
    def mutate(d):
        d["demand"]["dimensions"].append(dict(d["demand"]["dimensions"][0]))
    assert_isolated(validate(make_fixture(mutate_problem=mutate)), "duplicate coordinate")


def test_an_empty_dimension_catalogue_is_an_error(make_fixture):
    def mutate(d):
        d["demand"]["dimensions"] = []
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("demand.dimensions is empty" in e for e in r.errors), r.errors

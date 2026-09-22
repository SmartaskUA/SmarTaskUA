"""The domain layer: pure functions and the CSV readers. No shipped-data assertions."""

import pytest

from schema_v4 import core
from schema_v4.core import DomainError, Interval

DAY_OFF = {"scheduleInput": {"dayOffCodes": {"DO": {"kind": "preferable"},
                                             "VAC": {"kind": "unavailable"}}}}


# -- numbers -----------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("8", 8), ("7.2", 7.2), ("7,2", 7.2), ("  7,2  ", 7.2),
    ("", None), ("abc", None), (None, None),
])
def test_try_number(text, expected):
    assert core.try_number(text) == expected


def test_a_lone_comma_is_always_a_decimal_point():
    """'1,234' is 1.234 here. Stated so nobody reads it as a thousands separator."""
    assert core.try_number("1,234") == 1.234


def test_number_raises_where_try_number_returns_none():
    with pytest.raises(DomainError):
        core.number("abc")


@pytest.mark.parametrize("value, text", [(8, "8"), (7.2, "7.2"), (432.0, "432")])
def test_format_number_drops_a_trailing_zero(value, text):
    assert core.format_number(value) == text


# -- time --------------------------------------------------------------------

@pytest.mark.parametrize("start, end, expected", [
    ("09:00", "17:00", (540, 1020)),
    ("22:00", "06:00", (1320, 1800)),     # crosses midnight, resolved not inferred
    ("00:00", "00:00", (0, 1440)),        # a whole day, not an empty one
])
def test_parse_range(start, end, expected):
    assert core.try_parse_range(start, end) == expected


def test_parse_range_rejects_a_malformed_boundary():
    assert core.try_parse_range("9am", "17:00") is None
    with pytest.raises(DomainError):
        core.parse_range("9am", "17:00")


@pytest.mark.parametrize("minutes, text", [(540, "09:00"), (1800, "06:00"), (1440, "00:00")])
def test_min_to_hhmm_wraps_past_midnight(minutes, text):
    assert core.min_to_hhmm(minutes) == text


def test_coalesce_merges_overlapping_and_touching():
    assert core.coalesce([Interval(480, 720), Interval(600, 840)]) == (Interval(480, 840),)
    assert core.coalesce([Interval(480, 720), Interval(720, 960)]) == (Interval(480, 960),)
    assert len(core.coalesce([Interval(450, 840), Interval(1095, 1275)])) == 2
    assert core.coalesce([]) == ()


def test_interval_overlap_is_half_open():
    """20:00-21:00 and 21:00-22:00 touch; they do not overlap."""
    assert not Interval(1200, 1260).overlaps(Interval(1260, 1320))
    assert Interval(1200, 1260).overlaps(Interval(1230, 1320))


def test_hours_to_minutes_is_exact_for_a_fractional_contract():
    assert core.hours_to_minutes(7.2) == 432
    assert core.hours_to_minutes(8) == 480
    assert core.hours_to_minutes(0.001) is None


# -- the cell grammar --------------------------------------------------------

def test_a_plain_A_means_the_contract_length():
    assert core.classify_cell("A", DAY_OFF).kind == "auto"
    assert core.classify_cell("a", DAY_OFF).kind == "auto"


@pytest.mark.parametrize("hours, minutes", [("8", 480), ("7.2", 432), ("4", 240)])
def test_numeric_cells_are_hours(hours, minutes):
    assert core.classify_cell(hours, DAY_OFF).minutes == minutes


def test_the_v3_minutes_guard_is_inverted():
    """v3.0 rejected 1-24 as unmigrated hours; v4.0 rejects >24 as unconverted minutes."""
    with pytest.raises(DomainError) as exc:
        core.classify_cell("480", DAY_OFF)
    assert "never converted" in str(exc.value)


@pytest.mark.parametrize("cell", ["0", "-3"])
def test_a_working_day_of_no_hours_is_refused(cell):
    with pytest.raises(DomainError):
        core.classify_cell(cell, DAY_OFF)


def test_fractional_hours_that_are_not_whole_minutes_are_refused():
    with pytest.raises(DomainError) as exc:
        core.classify_cell("7.001", DAY_OFF)
    assert "whole number of minutes" in str(exc.value)


@pytest.mark.parametrize("op", core.OPERATORS)
def test_every_operator_parses(op):
    """Parametrized over OPERATORS so a new one cannot be added untested."""
    rule = core.classify_cell(f"{op}:09:00-13:00", DAY_OFF)
    assert rule.kind == op.lower()
    assert rule.windows == (Interval(540, 780),)


@pytest.mark.parametrize("op", core.OPERATORS)
def test_operators_are_case_insensitive(op):
    assert core.classify_cell(f"{op.lower()}:09:00-13:00", DAY_OFF).kind == op.lower()


def test_multiple_windows_coalesce():
    rule = core.classify_cell("EQUALS:08:00-12:00,10:00-14:00", DAY_OFF)
    assert rule.windows == (Interval(480, 840),)


def test_a_real_gap_survives_as_two_windows():
    rule = core.classify_cell("EQUALS:07:30-14:00,18:15-21:15", DAY_OFF)
    assert len(rule.windows) == 2


@pytest.mark.parametrize("cell", ["EQUALS:nonsense", "EQUALS:09:00", "EQUALS:25:00-26:00"])
def test_a_malformed_window_is_refused(cell):
    with pytest.raises(DomainError):
        core.classify_cell(cell, DAY_OFF)


def test_declared_codes_classify_and_undeclared_ones_do_not():
    assert core.classify_cell("DO", DAY_OFF).day_off == "preferable"
    assert core.classify_cell("VAC", DAY_OFF).day_off == "unavailable"
    with pytest.raises(DomainError):
        core.classify_cell("FDO", DAY_OFF)


def test_non_ascii_day_off_code_works():
    problem = {"scheduleInput": {"dayOffCodes": {"Fér": {"kind": "unavailable"}}}}
    assert core.classify_cell("Fér", problem).day_off == "unavailable"


def test_blank_cell_is_empty_not_unconstrained():
    assert core.classify_cell("", DAY_OFF).kind == "empty"


# -- CSV reading -------------------------------------------------------------

def test_the_reader_strips_a_bom_and_tolerates_crlf(bom_csv):
    """Read naively, column one comes back named BOM+'date' and every lookup fails."""
    assert bom_csv.read_bytes().startswith(b"\xef\xbb\xbf")
    header, rows = core.read_rows(bom_csv)
    assert header[0] == "date"
    assert len(rows) == 1


def test_comment_and_blank_lines_are_skipped(tmp_path):
    path = tmp_path / "d.csv"
    path.write_text("# a note\n\ndate,tableName,tableValue,minimum,ideal,estimated,start,end\n"
                    "# another\n2026-03-02,Team,T1,1,0,0,09:00,13:00\n", encoding="utf-8")
    header, rows = core.read_rows(path)
    assert header[0] == "date" and len(rows) == 1


def test_read_demand_uses_the_grain_it_is_given(tmp_path):
    """days and periods share a header, so the caller must say which it is -- and
    asking for shifts against a periods file must notice the missing column."""
    path = tmp_path / "d.csv"
    path.write_text("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
                    "2026-03-02,Team,T1,1,0,0,09:00,13:00\n", encoding="utf-8")
    _, rows, problems = core.read_demand(path, "periods")
    assert len(rows) == 1 and not problems
    _, rows, problems = core.read_demand(path, "shifts")
    assert not rows
    assert any("workPeriod" in p for p in problems)


@pytest.mark.parametrize("row, needle", [
    ("not-a-date,Team,T1,1,0,0,09:00,13:00", "bad date"),
    ("2026-03-02,Team,T1,x,0,0,09:00,13:00", "minimum is not a number"),
    ("2026-03-02,Team,T1,1,0,0,9am,13:00", "bad window"),
])
def test_read_demand_reports_a_bad_row_and_keeps_going(tmp_path, row, needle):
    path = tmp_path / "d.csv"
    path.write_text("date,tableName,tableValue,minimum,ideal,estimated,start,end\n"
                    f"{row}\n2026-03-03,Team,T1,1,0,0,09:00,13:00\n", encoding="utf-8")
    _, rows, problems = core.read_demand(path, "periods")
    assert any(needle in p for p in problems), problems
    assert rows, "a single bad row must not hide the rest of the file"


def test_read_schedule_input_requires_the_id_column(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text("emp,2026-03-02\nEMP001,8\n", encoding="utf-8")
    cells, dates, problems = core.read_schedule_input(path)
    assert any("employee_id" in p for p in problems)
    assert not cells and not dates


def test_read_schedule_input_flags_a_non_date_column_and_a_repeated_row(tmp_path):
    path = tmp_path / "s.csv"
    path.write_text("employee_id,2026-03-02,monday\nEMP001,8,8\nEMP001,4,4\n", encoding="utf-8")
    _, _, problems = core.read_schedule_input(path)
    assert any("not a YYYY-MM-DD date" in p for p in problems), problems
    assert any("appears twice" in p for p in problems), problems


def test_read_schedules_reports_a_bad_code_and_a_duplicate(tmp_path):
    path = tmp_path / "c.csv"
    path.write_text("code,description,scheduleWeightMinutes,startMin,endMin\n"
                    "nine,09:00-13:00,240,540,780\n"
                    "9001,09:00-13:00,240,540,780\n"
                    "9001,10:00-14:00,240,600,840\n", encoding="utf-8")
    catalogue, problems = core.read_schedules(path)
    assert any("not an integer" in p for p in problems), problems
    assert any("appears twice" in p for p in problems), problems
    assert set(catalogue) == {9001}


def test_a_row_with_no_window_and_no_weight_is_a_sentinel(tmp_path):
    path = tmp_path / "c.csv"
    path.write_text("code,description,scheduleWeightMinutes,startMin,endMin\n"
                    "3,Day off,0,,\n9001,09:00-13:00,240,540,780\n", encoding="utf-8")
    catalogue, _ = core.read_schedules(path)
    assert catalogue[3].is_sentinel
    assert not catalogue[9001].is_sentinel


# -- dates -------------------------------------------------------------------

def test_open_ended_assignment_covers_any_later_day():
    from datetime import date
    entry = {"start": "2024-01-01", "end": None}
    assert core.covers(entry, date(2030, 6, 1))
    assert not core.covers(entry, date(2023, 1, 1))


@pytest.mark.parametrize("text", ["2026-01-05", "2026-01-05T00:00:00", "2026-01-05T09:00:00Z"])
def test_iso_accepts_all_three_datetime_spellings(text):
    from datetime import date
    assert core.iso(text) == date(2026, 1, 5)


def test_week_index_is_case_insensitive_and_honours_week_start():
    from datetime import date
    origin = date(2026, 1, 1)            # a Thursday
    assert core.week_index(date(2026, 1, 4), origin, "Monday") == 0     # the Sunday
    assert core.week_index(date(2026, 1, 5), origin, "monday") == 1     # the Monday
    with pytest.raises(DomainError):
        core.week_index(origin, origin, "caturday")


def test_horizon_is_empty_when_the_scope_is_reversed():
    assert core.horizon({"temporalScope": {"start": "2026-03-08", "end": "2026-03-02"}}) == []
    assert len(core.horizon({"temporalScope": {"start": "2026-03-02", "end": "2026-03-08"}})) == 7

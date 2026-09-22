"""The domain layer: no I/O beyond the fixtures, no policy."""

import pytest
from helpers import CATALOGUE, C2, RAW_C2

from schema_v4 import core
from schema_v4.core import DomainError, Interval


def test_decimal_comma_and_dot_both_parse():
    assert core.try_number("7,2") == 7.2
    assert core.try_number("7.2") == 7.2
    assert core.try_number("8") == 8
    assert core.try_number("") is None
    assert core.try_number("not a number") is None


def test_thousands_style_input_is_not_silently_accepted():
    """'1,234' is ambiguous; treating it as 1.234 would be a guess either way."""
    assert core.try_number("1,234") == 1.234      # documented: comma is a decimal point


def test_midnight_crossing_is_resolved_not_inferred():
    assert core.try_parse_range("22:00", "06:00") == (1320, 1800)
    assert core.try_parse_range("09:00", "17:00") == (540, 1020)


def test_coalesce_merges_overlapping_and_touching():
    assert core.coalesce([Interval(480, 720), Interval(600, 840)]) == (Interval(480, 840),)
    assert core.coalesce([Interval(480, 720), Interval(720, 960)]) == (Interval(480, 960),)
    assert len(core.coalesce([Interval(450, 840), Interval(1095, 1275)])) == 2


def test_hours_to_minutes_is_exact_for_the_nl_contract():
    """7.2 h is exactly 432 min -- the value that cannot survive as a float."""
    assert core.hours_to_minutes(7.2) == 432
    assert core.hours_to_minutes(8) == 480
    assert core.hours_to_minutes(0.001) is None


def test_numeric_cells_are_hours_and_the_v3_guard_is_inverted():
    problem = {"scheduleInput": {"dayOffCodes": {"DO": {"kind": "preferable"}}}}
    assert core.classify_cell("8", problem).minutes == 480
    assert core.classify_cell("7.2", problem).minutes == 432
    with pytest.raises(DomainError) as exc:
        core.classify_cell("480", problem)
    assert "never converted" in str(exc.value)


def test_undeclared_code_is_refused():
    problem = {"scheduleInput": {"dayOffCodes": {"DO": {"kind": "preferable"}}}}
    assert core.classify_cell("DO", problem).day_off == "preferable"
    with pytest.raises(DomainError):
        core.classify_cell("VAC", problem)


def test_non_ascii_day_off_code_works():
    problem = {"scheduleInput": {"dayOffCodes": {"Fér": {"kind": "unavailable"}}}}
    assert core.classify_cell("Fér", problem).day_off == "unavailable"


def test_blank_cell_is_empty_not_unconstrained():
    assert core.classify_cell("", {}).kind == "empty"


def test_operators_parse_and_coalesce():
    rule = core.classify_cell("EQUALS:08:00-12:00,10:00-14:00", {})
    assert rule.kind == "equals"
    assert rule.windows == (Interval(480, 840),)


def test_csv_reader_strips_bom_and_comments():
    """SISQUAL's files are UTF-8 with a BOM; a naive reader names column 1 BOM+'date'."""
    raw = next(RAW_C2.glob("*_periods_demand.csv"))
    assert raw.read_bytes().startswith(b"\xef\xbb\xbf"), "fixture must really carry a BOM"
    header, _ = core.read_rows(raw)
    assert header and not header[0].startswith("\ufeff")
    assert header[0] == "date"


def test_read_demand_takes_the_grain_rather_than_sniffing():
    """days and periods have identical headers, so the caller must say which it is."""
    days_header, _, _ = core.read_demand(C2 / "days_demand.csv", "days")
    periods_header, _, _ = core.read_demand(C2 / "periods_demand.csv", "periods")
    assert days_header == periods_header


def test_catalogue_spans_match_their_stated_weights():
    catalogue, problems = core.read_schedules(CATALOGUE)
    assert not problems
    assert len(catalogue) == 1277
    windowed = [s for s in catalogue.values() if s.interval]
    assert windowed
    assert all(s.interval.length == s.weight_minutes for s in windowed)


def test_catalogue_has_four_codes_with_no_window():
    catalogue, _ = core.read_schedules(CATALOGUE)
    bare = sorted(s.code for s in catalogue.values() if s.interval is None)
    assert bare == [1, 3, 4, 1020]        # Espaço, Day off, Vazio, and Flexible


def test_open_ended_assignment_covers_any_later_day():
    from datetime import date
    entry = {"start": "2024-01-01", "end": None}
    assert core.covers(entry, date(2030, 6, 1))
    assert not core.covers(entry, date(2023, 1, 1))

"""Core domain unit tests (no I/O): cell parsing + coalescing, candidate building,
the T_d filter, and csv comment-stripping."""
from helpers import TC, load

import core as C

STUB = {"scheduleInput": {"dayOffCodes": {}}}


def test_equals_split_keeps_two_windows():
    r = C.classify_cell("EQUALS:07:30-14:00,18:15-21:15", STUB)
    assert [(w.start, w.end) for w in r.windows] == [(450, 840), (1095, 1275)]


def test_split_equals_builds_one_two_interval_assignment():
    r = C.classify_cell("EQUALS:07:30-14:00,18:15-21:15", STUB)
    cand = C.build_day_candidates(r, {"workMinutesPerDay": 480}, C.Interval(450, 1320), 15)
    assert len(cand) == 1 and len(cand[0].intervals) == 2


def test_split_equals_required_duration_sums_blocks():
    r = C.classify_cell("EQUALS:07:30-14:00,18:15-21:15", STUB)
    assert C.required_duration(r, None) == 570


def test_overlapping_equals_coalesces():
    ws = C.classify_cell("EQUALS:08:00-12:00,10:00-14:00", STUB).windows
    assert [(w.start, w.end) for w in ws] == [(480, 840)]


def test_touching_equals_coalesces():
    ws = C.classify_cell("EQUALS:08:00-12:00,12:00-16:00", STUB).windows
    assert [(w.start, w.end) for w in ws] == [(480, 960)]


def test_multi_window_include_every_block_covers_all():
    win = C.Interval(480, 1320)  # 08:00-22:00
    inc = C.classify_cell("INCLUDE:09:00-10:00,15:00-16:00", STUB)
    blocks = C.build_day_candidates(inc, {"workMinutesPerDay": 480}, win, 15)
    assert blocks and all(
        b.contains(C.Interval(540, 600)) and b.contains(C.Interval(900, 960))
        for c in blocks for b in c.intervals
    )


def test_multi_window_except_every_block_avoids_all():
    win = C.Interval(480, 1320)
    exc = C.classify_cell("EXCEPT:08:00-08:30,21:30-22:00", STUB)
    blocks = C.build_day_candidates(exc, {"workMinutesPerDay": 480}, win, 15)
    assert blocks and all(
        not b.overlaps(C.Interval(480, 510)) and not b.overlaps(C.Interval(1290, 1320))
        for c in blocks for b in c.intervals
    )


def test_within_every_block_sits_inside_one_window():
    win = C.Interval(480, 1320)  # 08:00-22:00 operating window
    wit = C.classify_cell("WITHIN:08:00-20:00", STUB)  # 480-1200
    assert wit.kind == "within"
    blocks = C.build_day_candidates(wit, {"workMinutesPerDay": 480}, win, 15)
    assert blocks and all(
        C.Interval(480, 1200).contains(b) for c in blocks for b in c.intervals
    )


def test_within_window_shorter_than_contract_has_no_block():
    win = C.Interval(480, 1320)
    wit = C.classify_cell("WITHIN:08:00-11:00", STUB)  # 180 min < 480 contract
    blocks = C.build_day_candidates(wit, {"workMinutesPerDay": 480}, win, 15)
    assert blocks == []
    why = C.diagnose(wit, {"workMinutesPerDay": 480}, win, 15, set(range(32, 88)), False)
    assert "no window leaves room" in why


def test_hwd_subset_of_t_d_dropped_not_truncated():
    prob = load(TC / "problem.json")
    periods = C.period_ranges(prob)
    window = C.operating_window(periods, 15)
    t_d = set(range(510 // 15, 990 // 15))  # only 08:30-16:30 demanded
    cands = C.build_day_candidates(C.CellRule(kind="auto"), {"workMinutesPerDay": 480}, window, 15)
    kept = [c for c in cands if C.slots_of(c.intervals, 15) <= t_d]
    dropped = [c for c in cands if not C.slots_of(c.intervals, 15) <= t_d]
    assert dropped                                              # some are dropped
    assert all(C.slots_of(c.intervals, 15) <= t_d for c in kept)
    assert all(c.intervals[0].end - c.intervals[0].start == 480 for c in kept)  # not truncated
    assert any(c.intervals[0].start == 510 and c.intervals[0].end == 990 for c in kept)


def test_csv_lines_strips_comments_and_blanks():
    lines = list(C.csv_lines(iter([
        "# a comment\n", "\n", "date,team\n", "  # indented comment\n",
        "2025-10-01,TeamA\n", "   \n",
    ])))
    assert lines == ["date,team\n", "2025-10-01,TeamA\n"]

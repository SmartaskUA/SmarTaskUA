"""
KpiEvaluator_Sisqual
====================
Evaluates hard-constraint alarms and performance KPIs for the Sisqual
scheduling problem using three input sources:

  1. schedule_data   — rows returned by build_output_rows()
                       [['employee_id','2025-10-01',...], ['20072412','10:00-18:00@Management',...], ...]
  2. demand_csv_path — path to demand.csv  (date, workPeriod, team, minimum, ideal, estimated)
  3. input_csv_path  — path to schedule_input.csv (employee_id, 2025-10-01, ...)
  4. problem_json    — dict already loaded from problem.json  (or path string)
"""

import re
import json
import csv
from datetime import datetime, date, timedelta
from collections import defaultdict
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

UNAVAILABLE_MARKERS = {"VAC", "NOT", "MED", "ENFD", "DC-E"}
OFF_MARKERS = {"DO", "FDO"} | UNAVAILABLE_MARKERS

MIN_REST_MINUTES = 11 * 60
MAX_CONSECUTIVE  = 5


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_off(cell: str) -> bool:
    return cell.strip().upper() in OFF_MARKERS or cell.strip() == ""


def _is_unavailable(cell: str) -> bool:
    return cell.strip().upper() in UNAVAILABLE_MARKERS


def _parse_shift(cell: str):
    """
    Returns (start_min, end_min, skills) or None.
    Handles single and multi-segment cells joined with ' | '.
    """
    cell = cell.strip()
    if _is_off(cell):
        return None

    segments  = [s.strip() for s in cell.split("|")]
    skills    = []
    start_min = None
    end_min   = None

    for seg in segments:
        m = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})@(\S+)", seg)
        if not m:
            continue
        sh, sm = int(m.group(1)), int(m.group(2))
        eh, em = int(m.group(3)), int(m.group(4))
        skill  = m.group(5)
        s_s    = sh * 60 + sm
        s_e    = eh * 60 + em
        start_min = s_s if start_min is None else min(start_min, s_s)
        end_min   = s_e if end_min   is None else max(end_min,   s_e)
        if skill not in skills:
            skills.append(skill)

    return (start_min, end_min, skills) if start_min is not None else None


def _parse_date(s: str):
    s = s.strip().lstrip("_")
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Input loaders
# ─────────────────────────────────────────────────────────────────────────────

def _load_schedule_data(schedule_data: list):
    if not schedule_data:
        return [], []
    header = schedule_data[0]
    dates  = [_parse_date(d) for d in header[1:]]
    rows   = [{"emp_id": str(r[0]), "days": list(r[1:])} for r in schedule_data[1:]]
    return dates, rows


def _load_demand_csv(path: str) -> dict:
    """
    Returns demand[(date_str, team)] = [(start_min, end_min, minimum, ideal, estimated), ...]
    Work period format in CSV: TEAM_HHMM_HHMM  e.g. CHECKOUT_1000_1100
    """
    demand = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str    = row["date"].strip()
            work_period = row["workPeriod"].strip()
            team        = row["team"].strip()
            minimum     = int(row["minimum"])
            ideal       = int(row["ideal"])
            estimated   = int(row["estimated"])

            parts = work_period.split("_")
            try:
                start_str = parts[-2]
                end_str   = parts[-1]
                start_min = int(start_str[:2]) * 60 + int(start_str[2:])
                end_min   = int(end_str[:2])   * 60 + int(end_str[2:])
            except (IndexError, ValueError):
                continue

            demand[(date_str, team)].append((start_min, end_min, minimum, ideal, estimated))

    for key in demand:
        demand[key].sort(key=lambda x: x[0])

    return dict(demand)


def _load_schedule_input_csv(path: str) -> dict:
    """
    Returns input_data[emp_id][date_str] = marker

    Strips leading '__' from column headers (weekend visual markers in the CSV).
    """
    input_data = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as f:
        reader    = csv.reader(f)
        header    = next(reader)
        date_cols = [col.strip().lstrip("_") for col in header[1:]]

        for row in reader:
            if not row:
                continue
            emp_id = str(row[0]).strip()
            for i, val in enumerate(row[1:]):
                if i < len(date_cols):
                    input_data[emp_id][date_cols[i]] = val.strip().lstrip("_")

    return dict(input_data)


def _load_problem_json(problem_json) -> dict:
    if isinstance(problem_json, dict):
        return problem_json
    with open(problem_json, encoding="utf-8") as f:
        return json.load(f)


def _build_contract_map(problem: dict) -> dict:
    """Returns {emp_id: workHoursPerDay}"""
    hours_by_type = {
        c["id"]: float(c.get("workHoursPerDay", 8))
        for c in problem.get("contracts", {}).get("definitions", [])
    }
    return {
        str(emp["id"]): hours_by_type.get(emp.get("contractType", "fullTime_8h"), 8.0)
        for emp in problem.get("employees", {}).get("competency", [])
    }


# ─────────────────────────────────────────────────────────────────────────────
# Evaluator
# ─────────────────────────────────────────────────────────────────────────────

class KpiEvaluator_Sisqual:

    def __init__(
        self,
        schedule_data:   list,
        demand_csv_path: str   = None,
        input_csv_path:  str   = None,
        problem_json           = None,
        total_shortage:  float = None,
    ):
        self.schedule_data  = schedule_data
        self.total_shortage = total_shortage
        self.kpis: dict     = {}

        self._dates, self._rows = _load_schedule_data(schedule_data)
        self._date_to_idx = {
            str(d): i for i, d in enumerate(self._dates) if d is not None
        }

        self._demand     = _load_demand_csv(demand_csv_path)        if demand_csv_path else {}
        self._input_data = _load_schedule_input_csv(input_csv_path) if input_csv_path  else {}
        self._problem    = _load_problem_json(problem_json)          if problem_json    else {}
        self._contracts  = _build_contract_map(self._problem)        if self._problem   else {}

    # ── ALM-1 ────────────────────────────────────────────────────────────────
    def Duplicated_assignments_per_day(self) -> dict:
        violations, details = 0, []
        for row in self._rows:
            for i, cell in enumerate(row["days"]):
                if _is_off(cell.strip()):
                    continue
                times = []
                for seg in [s.strip() for s in cell.split("|")]:
                    m = re.match(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})@", seg)
                    if m:
                        times.append((
                            int(m.group(1)) * 60 + int(m.group(2)),
                            int(m.group(3)) * 60 + int(m.group(4)),
                        ))
                times.sort()
                for j in range(1, len(times)):
                    if times[j][0] > times[j - 1][1]:          # gap → two shifts
                        violations += 1
                        day_label = str(self._dates[i]) if i < len(self._dates) else f"day_{i}"
                        details.append({"emp_id": row["emp_id"], "day": day_label})
                        break

        result = {"violations": violations, "pass": violations == 0, "details": details}
        self.kpis["Duplicated_assignments_per_day"] = result
        return result

    # ── ALM-2 ────────────────────────────────────────────────────────────────
    def Uncovered_slots_without_Skill(self) -> dict:
        violations, details = 0, []
        for row in self._rows:
            for i, cell in enumerate(row["days"]):
                cell = cell.strip()
                if _is_off(cell):
                    continue
                if "@" not in cell:
                    violations += 1
                    day_label = str(self._dates[i]) if i < len(self._dates) else f"day_{i}"
                    details.append({"emp_id": row["emp_id"], "day": day_label, "cell": cell})

        result = {"violations": violations, "pass": violations == 0, "details": details}
        self.kpis["Uncovered_slots_without_Skill"] = result
        return result

    # ── ALM-3 ────────────────────────────────────────────────────────────────
    def Maximum_Consecutive_Days(self) -> dict:
        violations, details = 0, []
        for row in self._rows:
            streak = max_streak = 0
            for c in row["days"]:
                if not _is_off(c.strip()):
                    streak    += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            if max_streak > MAX_CONSECUTIVE:
                violations += 1
                details.append({"emp_id": row["emp_id"], "max_streak": max_streak})

        result = {"violations": violations, "pass": violations == 0, "details": details}
        self.kpis["Maximum_Consecutive_Days"] = result
        return result

    # ── ALM-4 ────────────────────────────────────────────────────────────────
    def Minimum_Rest_Time_Between_Shifts(self) -> dict:
        violations, details = 0, []
        for row in self._rows:
            prev_shift = prev_date = None
            for i, cell in enumerate(row["days"]):
                shift        = _parse_shift(cell.strip())
                current_date = self._dates[i] if i < len(self._dates) else None

                if shift:
                    if prev_shift and prev_date and current_date:
                        if (current_date - prev_date).days == 1:
                            rest = (24 * 60 - prev_shift[1]) + shift[0]
                            if rest < MIN_REST_MINUTES:
                                violations += 1
                                details.append({
                                    "emp_id":       row["emp_id"],
                                    "day1":         str(prev_date),
                                    "day2":         str(current_date),
                                    "rest_minutes": rest,
                                    "rest_hours":   round(rest / 60, 1),
                                })
                    prev_shift = shift
                    prev_date  = current_date
                else:
                    prev_shift = prev_date = None

        result = {"violations": violations, "pass": violations == 0, "details": details}
        self.kpis["Minimum_Rest_Time_Between_Shifts"] = result
        return result

    # ── ALM-5  Uses schedule_input.csv as source of truth ────────────────────
    def Work_On_Unavailable_Days(self) -> dict:
        """
        Violation: schedule_input says VAC / NOT / Med (or similar) for a
        given (employee, day) but the schedule_output has a real shift there.
        Falls back to reading the output cell if no input file was loaded.
        """
        violations, details = 0, []
        for row in self._rows:
            emp_id    = row["emp_id"]
            input_row = self._input_data.get(emp_id, {})

            for i, out_cell in enumerate(row["days"]):
                d = self._dates[i]
                if d is None:
                    continue
                date_str = str(d)

                # Source of truth: schedule_input when available, else output cell
                if input_row:
                    in_marker = input_row.get(date_str, "").strip().upper()
                else:
                    in_marker = out_cell.strip().upper()

                if in_marker not in UNAVAILABLE_MARKERS:
                    continue

                # Unavailable day — should not have a shift
                if _parse_shift(out_cell.strip()) is not None:
                    violations += 1
                    details.append({
                        "emp_id":       emp_id,
                        "day":          date_str,
                        "input_marker": in_marker,
                        "output":       out_cell.strip(),
                    })

        result = {"violations": violations, "pass": violations == 0, "details": details}
        self.kpis["Work_On_Unavailable_Days"] = result
        return result

    # ── ALM-6 ────────────────────────────────────────────────────────────────
    def Sunday_Rest_Per_Month(self) -> dict:
        sunday_indices = [
            i for i, d in enumerate(self._dates)
            if d is not None and d.weekday() == 6
        ]
        if not sunday_indices:
            result = {"violations": 0, "pass": True, "details": [],
                      "note": "No Sundays in scheduling period"}
            self.kpis["Sunday_Rest_Per_Month"] = result
            return result

        violations, details = 0, []
        for row in self._rows:
            worked_all = all(
                not _is_off(row["days"][i].strip())
                for i in sunday_indices if i < len(row["days"])
            )
            if worked_all:
                violations += 1
                details.append(row["emp_id"])

        result = {"violations": violations, "pass": violations == 0, "details": details}
        self.kpis["Sunday_Rest_Per_Month"] = result
        return result

    # ── ALM-7  Uses problem.json (contract hours) + schedule_input (working days) ──
    def Weekly_Contracted_Hours(self) -> dict:
        """
        expected_hours = working_days_in_input × workHoursPerDay
        actual_hours   = sum of shift durations in output
        violation if |actual - expected| > 0.5h

        A day counts as "working" in the input when the marker is numeric
        (4, 5, 7, 8) or starts with EQUALS (fixed-time shift).
        """
        TOLERANCE_H = 0.5
        violations  = 0
        employees   = []

        for row in self._rows:
            emp_id     = row["emp_id"]
            contract_h = self._contracts.get(emp_id)
            input_row  = self._input_data.get(emp_id, {})

            # Actual hours from output
            actual_min = sum(
                (s[1] - s[0])
                for c in row["days"]
                if (s := _parse_shift(c.strip())) is not None
            )
            actual_h = round(actual_min / 60, 2)

            # Expected hours from input + contract
            expected_h = None
            if input_row and contract_h is not None:
                working_days = sum(
                    1 for m in input_row.values()
                    if re.match(r"^\d+$", m.strip()) or m.strip().upper().startswith("EQUALS")
                )
                expected_h = round(working_days * contract_h, 2)

            entry = {
                "emp_id":               emp_id,
                "actual_hours":         actual_h,
                "expected_hours":       expected_h,
                "contract_h_per_day":   contract_h,
            }
            if expected_h is not None:
                diff          = abs(actual_h - expected_h)
                entry["diff"] = round(diff, 2)
                entry["pass"] = diff <= TOLERANCE_H
                if not entry["pass"]:
                    violations += 1
            else:
                entry["pass"] = None   # cannot evaluate

            employees.append(entry)

        result = {"violations": violations, "pass": violations == 0, "employees": employees}
        self.kpis["Weekly_Contracted_Hours"] = result
        return result

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_employee_coverage_cache(self):
        """
        Pre-build coverage indexes used by all shortage computations.

        Key insight: _parse_shift returns the AGGREGATE span of a cell — the
        minimum start and maximum end across all segments. This is wrong for
        skill-specific coverage because an employee doing
          10:00-14:00@Checkout | 14:00-18:00@Management
        does NOT cover a Checkout slot at 15:00, even though the aggregate span
        runs to 18:00.

        This cache parses each '|'-separated segment individually, storing
        per-skill per-employee intervals as lists of (seg_start, seg_end).

        Indexes built:
          _cov_cache[(date_str, skill)] = [(seg_start, seg_end), ...]
            — one entry per skill-segment for any employee on that day.
            Multiple entries for the same employee are fine (they accumulate).

          _emp_cov_cache[date_str] = {emp_id: [(seg_start, seg_end), ...]}
            — all segments of a given employee on a day, across all skills.
            Used for the "Employees" aggregate: an employee covers a slot if
            ANY of their segments overlaps it, and we count each employee once.
        """
        import re as _re

        cov_cache: dict = {}      # (date_str, skill) → [(seg_start, seg_end)]
        emp_cache: dict = {}      # date_str → {emp_id: [(seg_start, seg_end)]}

        for row in self._rows:
            emp_id = row["emp_id"]
            for i, cell in enumerate(row["days"]):
                cell = cell.strip()
                if _is_off(cell):
                    continue
                d = self._dates[i]
                if d is None:
                    continue
                date_str = str(d)

                # Parse EACH '|'-separated segment individually
                for seg in cell.split("|"):
                    seg = seg.strip()
                    m = _re.match(
                        r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})@(\S+)", seg
                    )
                    if not m:
                        continue
                    sh, sm = int(m.group(1)), int(m.group(2))
                    eh, em = int(m.group(3)), int(m.group(4))
                    skill  = m.group(5)
                    s_min  = sh * 60 + sm
                    e_min  = eh * 60 + em

                    # Skill-specific index
                    key = (date_str, skill)
                    if key not in cov_cache:
                        cov_cache[key] = []
                    cov_cache[key].append((s_min, e_min))

                    # Employees aggregate index
                    if date_str not in emp_cache:
                        emp_cache[date_str] = {}
                    if emp_id not in emp_cache[date_str]:
                        emp_cache[date_str][emp_id] = []
                    emp_cache[date_str][emp_id].append((s_min, e_min))

        self._cov_cache     = cov_cache
        self._emp_cov_cache = emp_cache

    def _coverage_at_slot(self, date_str: str, team: str,
                          slot_start: int, slot_end: int) -> int:
        """
        Count employees covering the 30-min slot [slot_start, slot_end).

        An employee covers a slot if ANY of their skill-matching segments
        overlaps the slot:  seg_start < slot_end  AND  seg_end > slot_start

        For the "Employees" aggregate: counts unique employees where at least
        one of their segments (any skill) overlaps the slot.
        """
        if not hasattr(self, "_cov_cache"):
            self._build_employee_coverage_cache()

        if team == "Employees":
            date_emps = self._emp_cov_cache.get(date_str, {})
            count = 0
            for segs in date_emps.values():
                if any(s < slot_end and e > slot_start for s, e in segs):
                    count += 1
            return count
        else:
            segments = self._cov_cache.get((date_str, team), [])
            return sum(
                1 for (s, e) in segments
                if s < slot_end and e > slot_start
            )

    def _coverage_for(self, date_str: str, team: str,
                      p_start: int, p_end: int) -> int:
        """
        Full-containment check used by Staffing_Ideals / Staffing_Estimated.
        An employee covers the period if their segment FULLY contains [p_start, p_end).
        Uses the per-skill segment index for accuracy.
        """
        if not hasattr(self, "_cov_cache"):
            self._build_employee_coverage_cache()

        if team == "Employees":
            date_emps = self._emp_cov_cache.get(date_str, {})
            count = 0
            for segs in date_emps.values():
                if any(s <= p_start and e >= p_end for s, e in segs):
                    count += 1
            return count
        else:
            segments = self._cov_cache.get((date_str, team), [])
            return sum(
                1 for (s, e) in segments
                if s <= p_start and e >= p_end
            )

    def _build_slot_stats(self) -> dict:
        """
        Decomposes each demand work_period into 30-minute slots and computes
        coverage using partial overlap (an employee covers a slot if their
        shift overlaps it at all — not necessarily fully contains it).

        For each 30-min slot within a work_period:
          coverage = number of employees whose shift overlaps this slot
          gap      = max(0, minimum - coverage)

        The 'minimum' demand applies uniformly across all 30-min slots of the
        work_period (the demand CSV specifies a minimum per work_period, not
        per 30-min sub-slot).

        Returns a list of slot-level records used by Total_Shortage,
        Slots_With_Failure, Max_Shortage_Single_Slot and Mean_Shortage_Per_Slot.
        """
        if not hasattr(self, "_cov_cache"):
            self._build_employee_coverage_cache()

        SLOT_MIN = 30   # granularity in minutes

        slots          = []
        total          = 0
        total_slots    = 0
        total_demanded = 0
        total_covered  = 0
        failing        = 0
        max_gap        = 0
        by_skill       = defaultdict(int)

        for (date_str, team), periods in self._demand.items():
            for (p_start, p_end, minimum, ideal, estimated) in periods:
                if minimum <= 0:
                    continue

                # Decompose the work_period into 30-min sub-slots
                cursor = p_start
                while cursor < p_end:
                    slot_end = min(cursor + SLOT_MIN, p_end)
                    total_slots    += 1
                    total_demanded += minimum

                    coverage = self._coverage_at_slot(
                        date_str, team, cursor, slot_end
                    )
                    gap     = max(0, minimum - coverage)
                    covered = minimum - gap

                    total_covered += covered

                    slots.append({
                        "date":     date_str,
                        "team":     team,
                        "p_start":  cursor,
                        "p_end":    slot_end,
                        "minimum":  minimum,
                        "coverage": coverage,
                        "gap":      gap,
                    })

                    if gap > 0:
                        total           += gap
                        by_skill[team]  += gap
                        failing         += 1
                        max_gap          = max(max_gap, gap)

                    cursor = slot_end

        return {
            "slots":           slots,
            "total_shortage":  total,
            "total_slots":     total_slots,
            "total_demanded":  total_demanded,
            "total_covered":   total_covered,
            "failing_slots":   failing,
            "max_gap":         max_gap,
            "by_skill":        dict(by_skill),
        }

    # ── PERF-1  Total shortage vs demand minimums ─────────────────────────────
    def compute_Total_Shortage(self) -> dict:
        """
        Uses solver objective_value when available (exact).
        Otherwise recomputes from demand.csv via _build_slot_stats().
        coverage_rate is based on worker-slots covered vs demanded (not slot count).
        """
        def _build_failing_details(stats: dict) -> dict:
            """Group failing slots by skill, sorted by date then period."""
            details: dict = {}
            for s in stats["slots"]:
                if s["gap"] <= 0:
                    continue
                skill = s["team"]
                if skill not in details:
                    details[skill] = []
                details[skill].append({
                    "date":     s["date"],
                    "period":   f"{s['p_start'] // 60:02d}:{s['p_start'] % 60:02d}"
                                f"-{s['p_end'] // 60:02d}:{s['p_end'] % 60:02d}",
                    "required": s["minimum"],
                    "covered":  s["coverage"],
                    "gap":      s["gap"],
                })
            # Sort each skill's list by date then period
            for skill in details:
                details[skill].sort(key=lambda x: (x["date"], x["period"]))
            return details

        # Ensure coverage cache is built before any slot computation
        if not hasattr(self, "_cov_cache"):
            self._build_employee_coverage_cache()

        if self.total_shortage is not None:
            if not self._demand:
                result = {
                    "value":         int(self.total_shortage),
                    "source":        "solver_objective",
                    "coverage_rate": None,
                }
                self.kpis["Total_Shortage"] = result
                self._slot_stats = None
                return result

            stats = self._build_slot_stats()
            self._slot_stats = stats
            coverage_rate = (
                round(stats["total_covered"] / stats["total_demanded"] * 100, 1)
                if stats["total_demanded"] > 0 else 100.0
            )
            result = {
                "value":                   int(self.total_shortage),
                "source":                  "solver_objective",
                "coverage_rate":           coverage_rate,
                "minimums_covered":        stats["total_covered"],
                "minimums_demanded":       stats["total_demanded"],
                "failing_slots":           stats["failing_slots"],
                "shortage_by_skill":       stats["by_skill"],
                "failing_details_by_skill": _build_failing_details(stats),
            }
            self.kpis["Total_Shortage"] = result
            return result

        if not self._demand:
            result = {"value": 0, "source": "no_demand_data", "coverage_rate": 100.0}
            self.kpis["Total_Shortage"] = result
            self._slot_stats = None
            return result

        stats = self._build_slot_stats()
        self._slot_stats = stats

        coverage_rate = (
            round(stats["total_covered"] / stats["total_demanded"] * 100, 1)
            if stats["total_demanded"] > 0 else 100.0
        )

        result = {
            "value":                   stats["total_shortage"],
            "source":                  "computed_from_demand_csv",
            "coverage_rate":           coverage_rate,
            "minimums_covered":        stats["total_covered"],
            "minimums_demanded":       stats["total_demanded"],
            "failing_slots":           stats["failing_slots"],
            "shortage_by_skill":       stats["by_skill"],
            "failing_details_by_skill": _build_failing_details(stats),
        }
        self.kpis["Total_Shortage"] = result
        return result

    # ── PERF-7  Number of slots with at least one failure ─────────────────────
    def Slots_With_Failure(self) -> dict:
        """
        Count of (date, team, work_period) triples where the minimum staffing
        was not met by at least 1 worker. Measures the breadth of coverage
        failures independently of their magnitude.

        Returns:
          {
            "failing_slots":  46,
            "total_slots":    350,
            "failure_rate":   13.1,   # %
            "by_skill": {
              "Checkout":   {"failing": 31, "total": 120},
              ...
            }
          }
        """
        stats = getattr(self, "_slot_stats", None)
        if stats is None:
            self.compute_Total_Shortage()
            stats = self._slot_stats

        if stats is None:
            result = {"failing_slots": 0, "total_slots": 0, "failure_rate": 0.0, "by_skill": {}}
            self.kpis["Slots_With_Failure"] = result
            return result

        by_skill = defaultdict(lambda: {"failing": 0, "total": 0})
        for s in stats["slots"]:
            by_skill[s["team"]]["total"]  += 1
            if s["gap"] > 0:
                by_skill[s["team"]]["failing"] += 1

        failure_rate = (
            round(stats["failing_slots"] / stats["total_slots"] * 100, 1)
            if stats["total_slots"] > 0 else 0.0
        )

        result = {
            "failing_slots": stats["failing_slots"],
            "total_slots":   stats["total_slots"],
            "failure_rate":  failure_rate,
            "by_skill":      {k: dict(v) for k, v in by_skill.items()},
        }
        self.kpis["Slots_With_Failure"] = result
        return result

    # ── PERF-8  Maximum shortage in a single slot ─────────────────────────────
    def Max_Shortage_Single_Slot(self) -> dict:
        """
        The largest gap recorded in any single 30-min slot, plus a full
        distribution of all gap sizes and their locations.

        Returns:
          {
            "max_gap": 3,
            "gap_distribution": {          # how many slots have each gap size
              "1": 31,
              "2": 12,
              "3": 3
            },
            "details_by_gap": {            # up to 20 examples per gap size
              "3": [{"date","team","period","required","covered","gap"}, ...],
              "2": [...],
              "1": [...]
            }
          }
        """
        stats = getattr(self, "_slot_stats", None)
        if stats is None:
            self.compute_Total_Shortage()
            stats = self._slot_stats

        if stats is None or stats["max_gap"] == 0:
            result = {
                "max_gap":          0,
                "gap_distribution": {},
                "details_by_gap":   {},
            }
            self.kpis["Max_Shortage_Single_Slot"] = result
            return result

        # Build distribution and per-gap details in one pass
        gap_distribution: dict = {}
        details_by_gap: dict   = {}

        for s in stats["slots"]:
            g = s["gap"]
            if g <= 0:
                continue
            key = str(g)
            gap_distribution[key] = gap_distribution.get(key, 0) + 1
            if key not in details_by_gap:
                details_by_gap[key] = []
            if len(details_by_gap[key]) < 20:
                details_by_gap[key].append({
                    "date":     s["date"],
                    "team":     s["team"],
                    "period":   f"{s['p_start'] // 60:02d}:{s['p_start'] % 60:02d}"
                                f"-{s['p_end'] // 60:02d}:{s['p_end'] % 60:02d}",
                    "required": s["minimum"],
                    "covered":  s["coverage"],
                    "gap":      g,
                })

        # Sort details per gap by date then period
        for key in details_by_gap:
            details_by_gap[key].sort(key=lambda x: (x["date"], x["period"]))

        result = {
            "max_gap":          stats["max_gap"],
            "gap_distribution": gap_distribution,
            "details_by_gap":   details_by_gap,
        }
        self.kpis["Max_Shortage_Single_Slot"] = result
        return result


    # ── Priority Hierarchy ────────────────────────────────────────────────────
    def Priority_Hierarchy(self) -> dict:
        """
        Evaluates the alarm priority hierarchy against the demand minimums.

        Without competency levels implemented yet, the 9 original levels
        collapse into 4 skill groups ordered by priority:

          Priority 1 — Storage    (RESP ALMACEN N≥1)
          Priority 2 — Management (RESP EG N=1..4)
          Priority 3 — Checkout   (CAJA N=1..3)
          Priority 4 — Employees  (EQUIPA Empleados N≥1)

        For each (date, work_period, skill_group):
          - count how many employees in the output are covering that window
            with the required skill
          - compare against the demand minimum
          - if coverage < minimum → failing slots for that priority level

        Returns a list of priority entries, each with:
          {
            "priority":     1,
            "label":        "RESP ALMACEN N≥1 — Warehouse supervisor",
            "skill":        "Storage",
            "pass":         True,
            "failing_slots": 0,
            "total_slots":   31,
            "failing_dates": [...]   # up to 10 examples
          }
        """
        if not self._demand:
            result = {
                "pass": True,
                "note": "No demand data loaded — cannot evaluate priority hierarchy",
                "priorities": [],
            }
            self.kpis["Priority_Hierarchy"] = result
            return result

        # Priority levels without competency levels.
        # Skills with multiple ranks (Management: 2,4,6,7 / Checkout: 3,5,8)
        # cannot be distinguished without level data.
        # Strategy: evaluate each skill ONCE (at its first/highest rank), then
        # re-use those results for subsequent ranks of the same skill — marking
        # them as "pending levels" so the frontend can show the right state.
        PRIORITY_LEVELS = [
            (1, "RESP ALMACEN N≥1 — Warehouse supervisor",   "Storage"),
            (2, "RESP EG N=1 — Management supervisor",       "Management"),
            (3, "CAJA N=1 — Cashier",                        "Checkout"),
            (4, "RESP EG N=2 — Management supervisor",       "Management"),
            (5, "CAJA N=2 — Cashier",                        "Checkout"),
            (6, "RESP EG N=3 — Management supervisor",       "Management"),
            (7, "RESP EG N≥4 — Management supervisor",       "Management"),
            (8, "CAJA N=3 — Cashier",                        "Checkout"),
            (9, "EQUIPA Empleados N≥1 — General employee",   "Employees"),
        ]

        # Ensure coverage cache is built
        if not hasattr(self, "_cov_cache"):
            self._build_employee_coverage_cache()

        # Aggregate demand by (date_str, skill) → [(p_start, p_end, minimum), ...]
        demand_by_skill = defaultdict(list)
        for (date_str, team), periods in self._demand.items():
            for (p_start, p_end, minimum, ideal, estimated) in periods:
                if minimum > 0:
                    demand_by_skill[(date_str, team)].append((p_start, p_end, minimum))

        SLOT_MIN = 30

        # Evaluate each unique skill group exactly once, cache the result.
        # Uses 30-min slot decomposition with partial overlap (same as _build_slot_stats).
        skill_results: dict = {}

        def _evaluate_skill(skill: str) -> dict:
            if skill in skill_results:
                return skill_results[skill]

            f_slots = 0
            t_slots = 0
            f_dates = []

            relevant = [
                (date_str, p_start, p_end, minimum)
                for (date_str, team), periods in demand_by_skill.items()
                if team == skill
                for (p_start, p_end, minimum) in periods
            ]

            for (date_str, p_start, p_end, minimum) in relevant:
                # Decompose into 30-min sub-slots
                cursor = p_start
                while cursor < p_end:
                    slot_end = min(cursor + SLOT_MIN, p_end)
                    t_slots += 1

                    coverage = self._coverage_at_slot(date_str, skill, cursor, slot_end)

                    gap = minimum - coverage
                    if gap > 0:
                        f_slots += 1
                        if len(f_dates) < 10:
                            f_dates.append({
                                "date":     date_str,
                                "period":   f"{cursor // 60:02d}:{cursor % 60:02d}"
                                            f"-{slot_end // 60:02d}:{slot_end % 60:02d}",
                                "required": minimum,
                                "covered":  coverage,
                                "gap":      gap,
                            })
                    cursor = slot_end

            res = {
                "failing_slots": f_slots,
                "total_slots":   t_slots,
                "failing_dates": f_dates,
                "pass":          f_slots == 0,
            }
            skill_results[skill] = res
            return res

        priorities_result = []
        overall_pass      = True
        # Track which skills have already been fully evaluated and displayed
        first_rank_for_skill: dict = {}

        for (rank, label, skill) in PRIORITY_LEVELS:
            sr = _evaluate_skill(skill)

            is_first = skill not in first_rank_for_skill
            if is_first:
                first_rank_for_skill[skill] = rank

            if not sr["pass"]:
                overall_pass = False

            entry = {
                "priority":      rank,
                "label":         label,
                "skill":         skill,
                "pass":          sr["pass"],
                "failing_slots": sr["failing_slots"],
                "total_slots":   sr["total_slots"],
                "failing_dates": sr["failing_dates"] if is_first else [],
                # Flag repeated ranks so the frontend can render a note
                "levels_pending": not is_first,
            }
            priorities_result.append(entry)

        result = {
            "pass":       overall_pass,
            "priorities": priorities_result,
        }
        self.kpis["Priority_Hierarchy"] = result
        return result

    # ── Staffing Ideals ───────────────────────────────────────────────────────
    def Staffing_Ideals(self) -> dict:
        """
        PERF-4: Total number of worker-slots missing to reach the ideal
        staffing level, and coverage rate as a percentage.

        For each (date, team, work_period) with ideal > 0:
          gap = max(0, ideal - coverage)

        Returns:
          {
            "shortage":        12,          # total worker-slots below ideal
            "total_demanded":  350,         # total worker-slots demanded at ideal
            "coverage_rate":   96.6,        # % slots where ideal was met
            "slots_met":       338,         # slots where coverage >= ideal
            "slots_total":     350,         # total slots with ideal > 0
            "by_skill": {
              "Checkout":   {"shortage": 8, "slots_met": 60, "slots_total": 68},
              ...
            }
          }
        """
        if not self._demand:
            result = {"shortage": 0, "coverage_rate": 100.0, "note": "no demand data"}
            self.kpis["Staffing_Ideals"] = result
            return result

        if not hasattr(self, "_cov_cache"):
            self._build_employee_coverage_cache()

        SLOT_MIN = 30
        total_shortage = 0
        total_demanded = 0
        total_covered  = 0
        slots_met      = 0
        slots_total    = 0
        by_skill       = {}

        for (date_str, team), periods in self._demand.items():
            for (p_start, p_end, minimum, ideal, estimated) in periods:
                if ideal <= 0:
                    continue

                # Decompose into 30-min sub-slots
                cursor = p_start
                while cursor < p_end:
                    slot_end = min(cursor + SLOT_MIN, p_end)
                    slots_total    += 1
                    total_demanded += ideal

                    coverage = self._coverage_at_slot(date_str, team, cursor, slot_end)
                    gap      = max(0, ideal - coverage)
                    covered  = ideal - gap
                    met      = 1 if gap == 0 else 0

                    total_shortage += gap
                    total_covered  += covered
                    slots_met      += met

                    if team not in by_skill:
                        by_skill[team] = {"shortage": 0, "slots_met": 0, "slots_total": 0}
                    by_skill[team]["shortage"]    += gap
                    by_skill[team]["slots_met"]   += met
                    by_skill[team]["slots_total"] += 1

                    cursor = slot_end

        coverage_rate = round(total_covered / total_demanded * 100, 1) if total_demanded > 0 else 100.0

        result = {
            "shortage":           total_shortage,
            "coverage_rate":      coverage_rate,
            "minimums_covered":   total_covered,
            "minimums_demanded":  total_demanded,
            "slots_met":          slots_met,
            "slots_total":        slots_total,
            "by_skill":           by_skill,
        }
        self.kpis["Staffing_Ideals"] = result
        return result

    # ── Staffing Estimated ────────────────────────────────────────────────────
    def Staffing_Estimated(self) -> dict:
        """
        PERF-5: Same as Staffing_Ideals but compared against the estimated
        staffing level instead of the ideal.

        Returns the same structure as Staffing_Ideals.
        """
        if not self._demand:
            result = {"shortage": 0, "coverage_rate": 100.0, "note": "no demand data"}
            self.kpis["Staffing_Estimated"] = result
            return result

        if not hasattr(self, "_cov_cache"):
            self._build_employee_coverage_cache()

        SLOT_MIN = 30
        total_shortage = 0
        total_demanded = 0
        total_covered  = 0
        slots_met      = 0
        slots_total    = 0
        by_skill       = {}

        for (date_str, team), periods in self._demand.items():
            for (p_start, p_end, minimum, ideal, estimated) in periods:
                if estimated <= 0:
                    continue

                cursor = p_start
                while cursor < p_end:
                    slot_end = min(cursor + SLOT_MIN, p_end)
                    slots_total    += 1
                    total_demanded += estimated

                    coverage = self._coverage_at_slot(date_str, team, cursor, slot_end)
                    gap      = max(0, estimated - coverage)
                    covered  = estimated - gap
                    met      = 1 if gap == 0 else 0

                    total_shortage += gap
                    total_covered  += covered
                    slots_met      += met

                    if team not in by_skill:
                        by_skill[team] = {"shortage": 0, "slots_met": 0, "slots_total": 0}
                    by_skill[team]["shortage"]    += gap
                    by_skill[team]["slots_met"]   += met
                    by_skill[team]["slots_total"] += 1

                    cursor = slot_end

        coverage_rate = round(total_covered / total_demanded * 100, 1) if total_demanded > 0 else 100.0

        result = {
            "shortage":          total_shortage,
            "coverage_rate":     coverage_rate,
            "minimums_covered":  total_covered,
            "minimums_demanded": total_demanded,
            "slots_met":         slots_met,
            "slots_total":       slots_total,
            "by_skill":          by_skill,
        }
        self.kpis["Staffing_Estimated"] = result
        return result

    # ── Severity Index ────────────────────────────────────────────────────────
    def Severity_Index(self) -> dict:
        """
        PERF-2: Priority-weighted shortage. Uses _slot_stats if already computed.
        Weight formula: w(p) = 10 - p  (Storage=9, Management=8, Checkout=7, Employees=1)
        severity_index = Σ  w(skill) × gap(date, period, skill)
        """
        SKILL_PRIORITY = {
            "Storage":    (1, 9),
            "Management": (2, 8),
            "Checkout":   (3, 7),
            "Employees":  (9, 1),
        }

        if not self._demand:
            result = {"severity_index": 0, "total_shortage": 0, "by_priority": []}
            self.kpis["Severity_Index"] = result
            return result

        # Reuse slot stats if available to avoid recomputing coverage
        stats = getattr(self, "_slot_stats", None)
        if stats is None:
            self.compute_Total_Shortage()
            stats = self._slot_stats

        shortage_by_skill: dict = {}
        if stats:
            for s in stats["slots"]:
                if s["gap"] > 0 and s["team"] in SKILL_PRIORITY:
                    shortage_by_skill[s["team"]] = shortage_by_skill.get(s["team"], 0) + s["gap"]
        else:
            # Fallback: compute directly
            for (date_str, team), periods in self._demand.items():
                if team not in SKILL_PRIORITY:
                    continue
                for (p_start, p_end, minimum, ideal, estimated) in periods:
                    if minimum <= 0:
                        continue
                    coverage = self._coverage_for(date_str, team, p_start, p_end)
                    gap = max(0, minimum - coverage)
                    if gap > 0:
                        shortage_by_skill[team] = shortage_by_skill.get(team, 0) + gap

        severity_index = 0
        total_shortage = 0
        by_priority    = []

        for skill, (rank, weight) in sorted(SKILL_PRIORITY.items(), key=lambda x: x[1][0]):
            shortage = shortage_by_skill.get(skill, 0)
            weighted = shortage * weight
            severity_index += weighted
            total_shortage += shortage
            by_priority.append({
                "priority": rank,
                "skill":    skill,
                "weight":   weight,
                "shortage": shortage,
                "weighted": weighted,
            })

        result = {
            "severity_index": severity_index,
            "total_shortage": total_shortage,
            "by_priority":    by_priority,
        }
        self.kpis["Severity_Index"] = result
        return result

    # ── Employee KPIs ─────────────────────────────────────────────────────────
    def Employee_KPIs(self) -> dict:
        """
        Per-employee KPIs computed from the schedule output rows.

        For each employee returns:
          - total_worked_hours      : float
          - total_working_days      : int
          - max_consecutive_days    : int
          - skill_usage_pct         : {skill: pct}  — % of worked time per skill
          - daily_segments          : {date_str: int} — number of skill blocks per day
          - daily_detail            : {date_str: [{skill, start, end, duration_h}]}

        Result structure:
          {
            "employees": [
              {
                "emp_id": "20072412",
                "total_worked_hours":   168.0,
                "total_working_days":   21,
                "max_consecutive_days": 5,
                "skill_usage_pct":      {"Management": 100.0},
                "daily_segments":       {"2025-10-01": 1, "2025-10-02": 1, ...},
                "daily_detail":         {"2025-10-01": [{"skill":"Management","start":"10:00","end":"18:00","duration_h":8.0}], ...}
              },
              ...
            ]
          }
        """
        employees_out = []

        for row in self._rows:
            emp_id = row["emp_id"]

            total_minutes       = 0
            total_working_days  = 0
            streak              = 0
            max_streak          = 0
            skill_minutes: dict = {}
            daily_segments: dict = {}
            daily_detail: dict   = {}

            for i, cell in enumerate(row["days"]):
                cell     = cell.strip()
                d        = self._dates[i] if i < len(self._dates) else None
                date_str = str(d) if d else f"day_{i}"

                if _is_off(cell):
                    streak = 0
                    continue

                # Parse individual segments from the cell
                raw_segs = [s.strip() for s in cell.split("|")]
                day_segments = []

                for seg in raw_segs:
                    m = re.match(
                        r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})@(\S+)", seg
                    )
                    if not m:
                        continue
                    sh, sm = int(m.group(1)), int(m.group(2))
                    eh, em = int(m.group(3)), int(m.group(4))
                    skill  = m.group(5)
                    s_min  = sh * 60 + sm
                    e_min  = eh * 60 + em
                    dur    = e_min - s_min
                    day_segments.append({
                        "skill":      skill,
                        "start":      f"{sh:02d}:{sm:02d}",
                        "end":        f"{eh:02d}:{em:02d}",
                        "duration_h": round(dur / 60, 2),
                        "start_min":  s_min,
                    })
                    total_minutes += dur
                    skill_minutes[skill] = skill_minutes.get(skill, 0) + dur

                if not day_segments:
                    streak = 0
                    continue

                # Sort segments by start time and merge adjacent same-skill blocks
                day_segments.sort(key=lambda x: x["start_min"])
                merged = []
                for seg in day_segments:
                    if (
                        merged
                        and merged[-1]["skill"] == seg["skill"]
                        and merged[-1]["end"] == seg["start"]
                    ):
                        # extend the last block
                        merged[-1]["end"]        = seg["end"]
                        merged[-1]["duration_h"] = round(
                            merged[-1]["duration_h"] + seg["duration_h"], 2
                        )
                    else:
                        merged.append(dict(seg))

                # Remove helper key before storing
                for s in merged:
                    s.pop("start_min", None)

                total_working_days     += 1
                streak                 += 1
                max_streak              = max(max_streak, streak)
                daily_segments[date_str] = len(merged)
                daily_detail[date_str]   = merged

            # Skill usage percentages
            total_skill_min = sum(skill_minutes.values())
            skill_usage_pct = {
                skill: round(mins / total_skill_min * 100, 1)
                for skill, mins in skill_minutes.items()
            } if total_skill_min > 0 else {}

            employees_out.append({
                "emp_id":               emp_id,
                "total_worked_hours":   round(total_minutes / 60, 2),
                "total_working_days":   total_working_days,
                "max_consecutive_days": max_streak,
                "skill_usage_pct":      skill_usage_pct,
                "daily_segments":       daily_segments,
                "daily_detail":         daily_detail,
            })

        result = {"employees": employees_out}
        self.kpis["Employee_KPIs"] = result
        return result

    # ── STAT-A  Workload utilisation ──────────────────────────────────────────
    def Workload_Utilisation(self) -> dict:
        """
        General scheduling statistics — workload utilisation group.

        Requires Weekly_Contracted_Hours to have already been called so that
        actual_hours and expected_hours per employee are available.
        Falls back to computing them inline if not yet cached.

        STAT-A1  Mean utilisation            — avg(actual / expected) across employees
        STAT-A2  Variance of utilisation     — var of utilisation rates
        STAT-A3  Max-min workload gap        — max(actual_h) - min(actual_h)
        STAT-A4  Fairness index (Gini)       — 0 = perfect equality, 1 = all hours on one emp
        STAT-A5  Idle employees              — utilisation < 50% of contract
        STAT-A6  Overloaded employees        — actual > expected + tolerance
        STAT-A7  Assignments used            — count of active daily assignments + rate

        Returns:
          {
            "mean_utilisation":   87.4,       # %
            "variance":           0.034,       # normalised
            "max_min_gap_hours":  18.0,
            "fairness_index":     0.08,        # Gini, 0-1
            "idle_employees":     2,
            "idle_threshold_pct": 50,
            "overloaded_employees": 1,
            "assignments_used":   312,
            "assignments_possible": 350,
            "assignment_rate":    89.1,        # %
            "employees": [                     # per-employee breakdown
              {
                "emp_id":          "20072412",
                "actual_hours":    160.0,
                "expected_hours":  168.0,
                "utilisation_pct": 95.2,
                "status":          "normal",   # "normal" | "idle" | "overloaded"
              },
              ...
            ]
          }
        """
        IDLE_THRESHOLD  = 0.50   # below 50% of contract → idle
        OVER_TOLERANCE  = 0.5    # hours above contract → overloaded

        # ── Build per-employee utilisation data ──
        # Reuse Weekly_Contracted_Hours cache if available
        wch = self.kpis.get("Weekly_Contracted_Hours", {})
        cached_employees = wch.get("employees", [])
        cached_by_id = {e["emp_id"]: e for e in cached_employees}

        emp_stats = []
        for row in self._rows:
            emp_id = row["emp_id"]

            if emp_id in cached_by_id:
                c = cached_by_id[emp_id]
                actual_h   = c["actual_hours"]
                expected_h = c.get("expected_hours")
            else:
                # Compute inline
                actual_min = sum(
                    (s[1] - s[0])
                    for cell in row["days"]
                    if (s := _parse_shift(cell.strip())) is not None
                )
                actual_h   = round(actual_min / 60, 2)
                contract_h = self._contracts.get(emp_id)
                input_row  = self._input_data.get(emp_id, {})
                expected_h = None
                if input_row and contract_h is not None:
                    working_days = sum(
                        1 for m in input_row.values()
                        if re.match(r"^\d+$", m.strip()) or m.strip().upper().startswith("EQUALS")
                    )
                    expected_h = round(working_days * contract_h, 2)

            util_pct = (
                round(actual_h / expected_h * 100, 1)
                if expected_h and expected_h > 0 else None
            )

            if util_pct is None:
                status = "unknown"
            elif actual_h > (expected_h or 0) + OVER_TOLERANCE:
                status = "overloaded"
            elif expected_h and actual_h < expected_h * IDLE_THRESHOLD:
                status = "idle"
            else:
                status = "normal"

            emp_stats.append({
                "emp_id":          emp_id,
                "actual_hours":    actual_h,
                "expected_hours":  expected_h,
                "utilisation_pct": util_pct,
                "status":          status,
            })

        # Filter to employees where we can compute utilisation
        actual_hours_list = [e["actual_hours"] for e in emp_stats]

        # ── STAT-A3  Max-min gap ──
        max_min_gap = round(
            max(actual_hours_list) - min(actual_hours_list), 2
        ) if actual_hours_list else 0.0

        # ── STAT-A5  Idle employees ──
        idle_count = sum(1 for e in emp_stats if e["status"] == "idle")

        # ── STAT-A6  Overloaded employees ──
        overloaded_count = sum(1 for e in emp_stats if e["status"] == "overloaded")

        # ── STAT-A7  Assignments used ──
        assignments_used = sum(
            1
            for row in self._rows
            for cell in row["days"]
            if _parse_shift(cell.strip()) is not None
        )
        assignments_possible = len(self._rows) * len(self._dates)
        assignment_rate = round(
            assignments_used / assignments_possible * 100, 1
        ) if assignments_possible > 0 else 0.0

        result = {
            "max_min_gap_hours":    max_min_gap,
            "idle_employees":       idle_count,
            "idle_threshold_pct":   int(IDLE_THRESHOLD * 100),
            "overloaded_employees": overloaded_count,
            "assignments_used":     assignments_used,
            "assignments_possible": assignments_possible,
            "assignment_rate":      assignment_rate,
            "employees":            emp_stats,
        }
        self.kpis["Workload_Utilisation"] = result
        return result

    # ── STAT-B  Skill allocation analysis ────────────────────────────────────
    def Skill_Allocation_Stats(self) -> dict:
        """
        STAT-B3  Mean skill changes per day
        STAT-B4  Mean segment duration

        Reuses Employee_KPIs cache (daily_segments, daily_detail) when available.
        Falls back to computing inline if Employee_KPIs has not been called yet.

        A "skill change" on a given day = number of merged segments - 1.
        A segment is a contiguous block of the same skill.

        Now computed per employee, not globally.

        Returns:
          {
            "mean_segment_duration_hours": 2.8,    # STAT-B4 — global average
            "total_segments":              874,
            "total_active_employee_days":  312,
            "by_skill": {
              "Management": {"segments": 210, "total_hours": 1680.0},
              ...
            },
            "per_employee": [
              {
                "emp_id":                  "20072412",
                "num_skills":              2,         # distinct skills used
                "skills_used":             ["Management", "Checkout"],
                "mean_changes_per_day":    1.4,       # avg skill switches/day
                "total_active_days":       21,
                "total_changes":           29,
              },
              ...
            ]
          }
        """
        emp_kpis = self.kpis.get("Employee_KPIs", {}).get("employees", [])

        total_segments       = 0
        total_segment_hours  = 0.0
        total_active_days    = 0
        by_skill: dict       = {}
        per_employee         = []

        def _process_emp_days(emp_id, daily_detail):
            """Returns per-employee stats dict."""
            emp_changes   = 0
            emp_act_days  = 0
            emp_skills: set = set()
            nonlocal total_segments, total_segment_hours, total_active_days

            for date_str, segs in daily_detail.items():
                if not segs:
                    continue
                n = len(segs)
                total_active_days   += 1
                emp_act_days        += 1
                total_segments      += n
                emp_changes         += max(0, n - 1)

                for seg in segs:
                    dur   = seg.get("duration_h", 0.0)
                    skill = seg.get("skill", "Unknown")
                    total_segment_hours += dur
                    emp_skills.add(skill)
                    if skill not in by_skill:
                        by_skill[skill] = {"segments": 0, "total_hours": 0.0}
                    by_skill[skill]["segments"]    += 1
                    by_skill[skill]["total_hours"] += dur

            mean_chg = (
                round(emp_changes / emp_act_days, 2)
                if emp_act_days > 0 else 0.0
            )
            skills_list = sorted(emp_skills)
            return {
                "emp_id":               emp_id,
                "num_skills":           len(skills_list),
                "skills_used":          skills_list,
                "mean_changes_per_day": mean_chg,
                "total_active_days":    emp_act_days,
                "total_changes":        emp_changes,
            }

        if emp_kpis:
            for emp in emp_kpis:
                stat = _process_emp_days(emp["emp_id"], emp.get("daily_detail", {}))
                per_employee.append(stat)
        else:
            # Inline computation — build daily_detail on the fly
            for row in self._rows:
                emp_id       = row["emp_id"]
                daily_detail = {}

                for i, cell in enumerate(row["days"]):
                    cell = cell.strip()
                    if _is_off(cell):
                        continue
                    d = self._dates[i]
                    if d is None:
                        continue
                    date_str = str(d)

                    raw_segs = [s.strip() for s in cell.split("|")]
                    day_segs = []
                    for seg in raw_segs:
                        m = re.match(
                            r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})@(\S+)", seg
                        )
                        if not m:
                            continue
                        sh, sm = int(m.group(1)), int(m.group(2))
                        eh, em = int(m.group(3)), int(m.group(4))
                        skill  = m.group(5)
                        s_min  = sh * 60 + sm
                        e_min  = eh * 60 + em
                        day_segs.append((s_min, e_min, skill))

                    if not day_segs:
                        continue

                    day_segs.sort()
                    merged = [list(day_segs[0])]
                    for s_min, e_min, skill in day_segs[1:]:
                        if skill == merged[-1][2] and s_min == merged[-1][1]:
                            merged[-1][1] = e_min
                        else:
                            merged.append([s_min, e_min, skill])

                    daily_detail[date_str] = [
                        {
                            "skill":      sk,
                            "duration_h": round((e - s) / 60.0, 2),
                        }
                        for s, e, sk in merged
                    ]

                stat = _process_emp_days(emp_id, daily_detail)
                per_employee.append(stat)

        # Round by_skill hours
        for sk in by_skill:
            by_skill[sk]["total_hours"] = round(by_skill[sk]["total_hours"], 1)

        mean_seg_dur = (
            round(total_segment_hours / total_segments, 2)
            if total_segments > 0 else 0.0
        )

        # Sort per_employee by mean_changes desc so highest switchers appear first
        per_employee.sort(key=lambda e: e["mean_changes_per_day"], reverse=True)

        result = {
            "mean_segment_duration_hours": mean_seg_dur,
            "total_segments":              total_segments,
            "total_active_employee_days":  total_active_days,
            "by_skill":                    by_skill,
            "per_employee":                per_employee,
        }
        self.kpis["Skill_Allocation_Stats"] = result
        return result

    # ── Entry point ───────────────────────────────────────────────────────────
    def evaluate_kpis(self) -> dict:
        print(
            f"[KpiEvaluator_Sisqual] {len(self._rows)} employees, "
            f"{len(self._dates)} days, "
            f"demand_entries={len(self._demand)}, "
            f"input_loaded={bool(self._input_data)}, "
            f"contracts_loaded={bool(self._contracts)}"
        )
        # Hard constraints
        self.Duplicated_assignments_per_day()
        self.Uncovered_slots_without_Skill()
        self.Maximum_Consecutive_Days()
        self.Minimum_Rest_Time_Between_Shifts()
        self.Work_On_Unavailable_Days()
        self.Sunday_Rest_Per_Month()
        self.Weekly_Contracted_Hours()         # must run before Workload_Utilisation
        # Performance — compute_Total_Shortage first so _slot_stats is cached
        self.compute_Total_Shortage()
        self.Slots_With_Failure()
        self.Max_Shortage_Single_Slot()
        self.Staffing_Ideals()
        self.Staffing_Estimated()
        self.Severity_Index()
        # Priority hierarchy
        self.Priority_Hierarchy()
        # Per-employee (must run before Skill_Allocation_Stats)
        self.Employee_KPIs()
        # General statistics
        self.Workload_Utilisation()
        self.Skill_Allocation_Stats()
        return self.kpis
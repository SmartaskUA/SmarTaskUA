import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

OFF_MARKERS = {"", "0", "OFF", "DO", "FDO", "VAC", "NOT", "MED"}
HARD_UNAVAILABLE_MARKERS = {"VAC", "NOT", "MED", "FDO", "ENFD", "DC-E"}
EXACT_PATTERN = re.compile(r"^EQUALS:(\d{1,2}:\d{2})-(\d{1,2}:\d{2})$", re.IGNORECASE)
SEGMENT_PATTERN = re.compile(r"^(\d{1,2}:\d{2})-(\d{1,2}:\d{2})@(.+)$")
DEFAULT_MAX_CONSECUTIVE_DAYS = 5
DEFAULT_MIN_REST_HOURS = 11
STAFF_TEAM_CODE = "Employees"
DEFAULT_SISQUAL_COVERAGE_PRIORITY_TIERS = (
    ("Storage", 1, None, "RESP ALMACEN N>=1"),
    ("Management", 1, 1, "RESP - EQUIPO GESTION N=1"),
    ("Checkout", 1, 1, "CAJA N=1"),
    ("Management", 2, 2, "RESP - EQUIPO GESTION N=2"),
    ("Checkout", 2, 2, "CAJA N=2"),
    ("Management", 3, 3, "RESP - EQUIPO GESTION N=3"),
    ("Management", 4, None, "RESP - EQUIPO GESTION N>=4"),
    ("Checkout", 3, None, "CAJA N>=3"),
)


def analyze(file_path, problem_path, employees=None, year=None):
    bundle = load_problem_bundle(problem_path)
    schedule = load_schedule_csv(file_path)
    employees = employees if isinstance(employees, list) and employees else bundle["employees"]
    schedule_dates = set(schedule.get("dates") or [])

    employee_meta = build_employee_meta(employees)
    slot_coverage = build_slot_coverage(schedule)
    integrity_metrics = compute_schedule_integrity_metrics(schedule)

    coverage_metrics = compute_coverage_metrics(
        filter_rows_by_dates(bundle["demand_rows"], schedule_dates),
        bundle["work_periods"],
        slot_coverage,
    )
    assignment_metrics = compute_assignment_metrics(
        schedule,
        bundle["schedule_rules"],
        employee_meta,
        bundle["min_rest_hours"],
        bundle["max_consecutive_days"],
        bundle["coverage_priority_tiers"],
    )

    result = {
        "weightedMinimumCoverageRate": coverage_metrics["weightedMinimumCoverageRate"],
        "criticalUnderfilledPeriods": coverage_metrics["criticalUnderfilledPeriods"],
        "maxPeriodShortage": coverage_metrics["maxPeriodShortage"],
        "maxShortageSingleSlot": coverage_metrics["maxShortageSingleSlot"],
        "totalMinimumGap": coverage_metrics["totalMinimumGap"],
        "totalOverstaff": coverage_metrics["totalOverstaff"],
        "coverageByTeam": coverage_metrics["coverageByTeam"],
        "teamCoverageBreakdown": coverage_metrics["teamCoverageBreakdown"],
        "underfilledPeriods": coverage_metrics["underfilledPeriods"],
        "intraDayTeamSwitches": assignment_metrics["intraDayTeamSwitches"],
        "fragmentedWorkDays": assignment_metrics["fragmentedWorkDays"],
        "primaryTeamUtilizationRate": assignment_metrics["primaryTeamUtilizationRate"],
        "nonPrimaryTeamHours": assignment_metrics["nonPrimaryTeamHours"],
        "durationComplianceRate": assignment_metrics["durationComplianceRate"],
        "demandedHoursComplianceRate": assignment_metrics["demandedHoursComplianceRate"],
        "preferredDayOffWorkedDays": assignment_metrics["preferredDayOffWorkedDays"],
        "preferredDayOffPreservationRate": assignment_metrics["preferredDayOffPreservationRate"],
        "skillPriorityPenaltyScore": assignment_metrics["skillPriorityPenaltyScore"],
        "duplicatedAssignmentsPerDay": integrity_metrics["duplicatedAssignmentsPerDay"],
        "uncoveredSlotsWithoutSkill": integrity_metrics["uncoveredSlotsWithoutSkill"],
        "consecutiveDaysViolations": assignment_metrics["consecutiveDaysViolations"],
        "minRestViolations": assignment_metrics["minRestViolations"],
        "availabilityViolations": assignment_metrics["availabilityViolations"],
        "employeeAssignmentQuality": assignment_metrics["employeeAssignmentQuality"],
    }
    return result


def filter_rows_by_dates(rows, dates):
    if not dates:
        return list(rows or [])
    return [row for row in rows or [] if row.get("date") in dates]


def is_bundle_native_hour_problem(problem_path):
    try:
        bundle_path = resolve_bundle_path(problem_path)
        if not bundle_path.is_file():
            return False
        with bundle_path.open(encoding="utf-8") as fh:
            problem = json.load(fh)
        demand = problem.get("demand", {})
        return bool(demand.get("workPeriods"))
    except Exception:
        return False


def load_problem_bundle(problem_path):
    bundle_path = resolve_bundle_path(problem_path)
    with bundle_path.open(encoding="utf-8") as fh:
        problem = json.load(fh)

    demand = problem.get("demand", {})
    schedule_input = problem.get("scheduleInput", {})
    work_periods = {
        item.get("code"): {
            "code": item.get("code"),
            "name": item.get("name") or item.get("code"),
            "team": infer_team_from_work_period(item.get("code")),
            "start": parse_minutes(item.get("timeRange", {}).get("start")),
            "end": parse_minutes(item.get("timeRange", {}).get("end")),
        }
        for item in demand.get("workPeriods", [])
        if item.get("code")
    }

    demand_file = demand.get("dataFile", "demand.csv")
    demand_path = (bundle_path.parent / demand_file).resolve()
    with demand_path.open(newline="", encoding="utf-8") as fh:
        demand_rows = [normalize_demand_row(row) for row in csv.DictReader(fh)]

    schedule_input_file = schedule_input.get("dataFile", "schedule_input.csv")
    schedule_input_path = (bundle_path.parent / schedule_input_file).resolve()
    schedule_rules = load_schedule_rules(schedule_input_path)

    employees = extract_problem_employees(problem)
    skill_codes = extract_skill_codes(problem, employees)
    coverage_priority_tiers = parse_coverage_priority_tiers(problem, skill_codes, STAFF_TEAM_CODE)
    hard_constraints = problem.get("constraints", {}).get("hard", [])
    min_rest_hours = DEFAULT_MIN_REST_HOURS
    for constraint in hard_constraints:
        if constraint.get("type") == "min_rest_hours" and constraint.get("enabled", True):
            hours = constraint.get("params", {}).get("hours")
            if isinstance(hours, (int, float)):
                min_rest_hours = float(hours)
                break

    return {
        "problem": problem,
        "employees": employees,
        "demand_rows": demand_rows,
        "work_periods": work_periods,
        "schedule_rules": schedule_rules,
        "coverage_priority_tiers": coverage_priority_tiers,
        "min_rest_hours": min_rest_hours,
        "max_consecutive_days": DEFAULT_MAX_CONSECUTIVE_DAYS,
    }


def resolve_bundle_path(problem_path):
    candidate = Path(problem_path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (Path.cwd() / candidate).resolve()


def normalize_demand_row(row):
    normalized = dict(row)
    for key in ("minimum", "ideal", "estimated"):
        raw = row.get(key)
        normalized[key] = int(raw) if raw not in (None, "") else 0
    normalized["date"] = str(row.get("date", "")).strip()
    normalized["team"] = str(row.get("team", "")).strip()
    normalized["workPeriod"] = str(row.get("workPeriod", "")).strip()
    return normalized


def extract_problem_employees(problem):
    employees_node = problem.get("employees", {}) if isinstance(problem, dict) else {}
    simple = employees_node.get("simple")
    competency = employees_node.get("competency")
    source = simple if isinstance(simple, list) and simple else competency
    return source if isinstance(source, list) else []


def extract_skill_codes(problem, employees):
    skills = []
    for employee in employees or []:
        if not isinstance(employee, dict):
            continue
        for team in employee.get("teams") or []:
            if isinstance(team, str):
                code = str(team).strip()
            elif isinstance(team, dict):
                code = first_non_blank(team.get("code"), team.get("id"), team.get("name"))
            else:
                code = None
            if code:
                skills.append(code)

    for team in (((problem or {}).get("demand", {}).get("organizationalUnits", {}) or {}).get("teams", [])):
        if not isinstance(team, dict):
            continue
        code = first_non_blank(team.get("code"), team.get("id"), team.get("name"))
        if code:
            skills.append(code)

    deduped = []
    seen = set()
    for skill in skills:
        if skill in seen:
            continue
        seen.add(skill)
        deduped.append(skill)
    if STAFF_TEAM_CODE not in seen:
        deduped.append(STAFF_TEAM_CODE)
    return deduped


def parse_coverage_priority_tiers(problem, skills, staff_team_code="Employees"):
    raw_hierarchy = sorted(
        ((problem or {}).get("demand", {}) or {}).get("priorityHierarchy", []),
        key=lambda item: parse_int_value(item.get("rank")) or 10 ** 6,
    )

    if any(isinstance(entry, dict) and entry.get("minLevel") is not None for entry in raw_hierarchy):
        priority_tiers = []
        for index, entry in enumerate(raw_hierarchy):
            if not isinstance(entry, dict):
                continue
            skill = str(entry.get("team", "")).strip()
            if not skill:
                continue
            min_n = parse_int_value(entry.get("minLevel")) or 1
            max_n = parse_int_value(entry.get("maxLevel"))
            label = str(entry.get("label", f"{skill} N>={min_n}")).strip()
            priority_tiers.append(
                {
                    "priority": index + 1,
                    "skill": skill,
                    "min_n": min_n,
                    "max_n": max_n,
                    "label": label,
                }
            )
    else:
        priority_tiers = [
            {
                "priority": index + 1,
                "skill": skill,
                "min_n": min_n,
                "max_n": max_n,
                "label": label,
            }
            for index, (skill, min_n, max_n, label) in enumerate(DEFAULT_SISQUAL_COVERAGE_PRIORITY_TIERS)
        ]

    known_skill_levels = {(tier["skill"], tier["min_n"]) for tier in priority_tiers}
    if (staff_team_code, 1) not in known_skill_levels:
        priority_tiers.append(
            {
                "priority": len(priority_tiers) + 1,
                "skill": staff_team_code,
                "min_n": 1,
                "max_n": None,
                "label": "EQUIPA Empleados N>=1",
            }
        )

    known_skills = {tier["skill"] for tier in priority_tiers}
    for skill in skills:
        if not skill or skill in known_skills:
            continue
        priority_tiers.append(
            {
                "priority": len(priority_tiers) + 1,
                "skill": skill,
                "min_n": 1,
                "max_n": None,
                "label": f"{skill} N>=1",
            }
        )
        known_skills.add(skill)

    return priority_tiers


def match_coverage_priority_tier(skill, nth_worker, coverage_priority_tiers):
    for index, tier in enumerate(coverage_priority_tiers or []):
        if tier["skill"] != skill:
            continue
        if nth_worker < tier["min_n"]:
            continue
        max_n = tier["max_n"]
        if max_n is not None and nth_worker > max_n:
            continue
        return index
    raise ValueError(f"No priority tier matches skill '{skill}' worker #{nth_worker}")


def build_employee_priority_summary(meta, coverage_priority_tiers):
    best = None
    for team in meta.get("teams", []) or []:
        skill = team.get("code")
        level = parse_int_value(team.get("level"))
        if not skill or level is None:
            continue
        try:
            tier_index = match_coverage_priority_tier(skill, level, coverage_priority_tiers)
        except ValueError:
            continue
        tier = coverage_priority_tiers[tier_index]
        candidate = {
            "priorityRank": int(tier.get("priority", tier_index + 1)),
            "priorityLabel": str(tier.get("label") or f"{skill} priority {tier_index + 1}"),
            "priorityTeam": skill,
            "priorityLevel": level,
        }
        if best is None or candidate["priorityRank"] < best["priorityRank"]:
            best = candidate

    if best is not None:
        return best

    return {
        "priorityRank": len(coverage_priority_tiers or []) + 1,
        "priorityLabel": "Unmapped priority",
        "priorityTeam": meta.get("primary_team"),
        "priorityLevel": None,
    }


def load_schedule_rules(path):
    rules = {}
    if not path.is_file():
        return rules
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            employee_id = str(row.get("employee_id", "")).strip()
            if not employee_id:
                continue
            employee_rules = {}
            for key, value in row.items():
                if key == "employee_id":
                    continue
                employee_rules[str(key).strip()] = str(value or "").strip()
            rules[employee_id] = employee_rules
    return rules


def load_schedule_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    if not rows:
        return {"dates": [], "employees": {}, "rawEmployees": {}}

    header = rows[0]
    dates = [str(value).strip() for value in header[1:] if str(value).strip()]
    employees = {}
    raw_employees = {}
    for row in rows[1:]:
        if not row:
            continue
        employee_id = str(row[0]).strip()
        if not employee_id:
            continue
        day_map = {}
        raw_day_map = {}
        for index, day in enumerate(dates, start=1):
            cell = row[index] if index < len(row) else ""
            raw_day_map[day] = str(cell or "").strip()
            day_map[day] = parse_schedule_cell(cell)
        employees[employee_id] = day_map
        raw_employees[employee_id] = raw_day_map

    return {
        "dates": dates,
        "employees": employees,
        "rawEmployees": raw_employees,
    }


def parse_schedule_cell(cell):
    text = str(cell or "").strip()
    if not text:
        return []
    normalized = text.upper()
    if normalized in OFF_MARKERS:
        return []

    segments = []
    for part in text.split("|"):
        token = part.strip()
        if not token:
            continue
        match = SEGMENT_PATTERN.match(token)
        if not match:
            continue
        start_text, end_text, team = match.groups()
        start = parse_minutes(start_text)
        end = parse_minutes(end_text)
        if start is None or end is None or end <= start:
            continue
        segments.append(
            {
                "start": start,
                "end": end,
                "team": str(team).strip(),
            }
        )
    segments.sort(key=lambda item: (item["start"], item["end"], item["team"]))
    return segments


def compute_schedule_integrity_metrics(schedule):
    duplicated = 0
    duplicated_details = []
    uncovered = 0
    uncovered_details = []
    raw_employees = schedule.get("rawEmployees") or {}

    for employee_id, day_cells in raw_employees.items():
        for day, raw_cell in day_cells.items():
            cell = str(raw_cell or "").strip()
            if not cell or cell.upper() in OFF_MARKERS:
                continue

            if "@" not in cell:
                uncovered += 1
                uncovered_details.append(
                    {"employeeId": employee_id, "date": day, "cell": cell}
                )
                continue

            intervals = []
            for part in cell.split("|"):
                match = SEGMENT_PATTERN.match(part.strip())
                if not match:
                    continue
                start = parse_minutes(match.group(1))
                end = parse_minutes(match.group(2))
                if start is None or end is None:
                    continue
                intervals.append((start, end))

            intervals.sort()
            for index in range(1, len(intervals)):
                if intervals[index][0] < intervals[index - 1][1]:
                    duplicated += 1
                    duplicated_details.append(
                        {"employeeId": employee_id, "date": day, "cell": cell}
                    )
                    break

    return {
        "duplicatedAssignmentsPerDay": duplicated,
        "duplicatedAssignmentsPerDayDetails": duplicated_details,
        "uncoveredSlotsWithoutSkill": uncovered,
        "uncoveredSlotsWithoutSkillDetails": uncovered_details,
    }


def build_employee_meta(employees):
    meta = {}
    for raw in employees or []:
        if not isinstance(raw, dict):
            continue
        employee_id = first_non_blank(raw.get("id"), raw.get("_id"), raw.get("employee_id"), raw.get("employeeId"))
        if not employee_id:
            continue
        name = first_non_blank(raw.get("name"), employee_id)
        teams = []
        for index, team in enumerate(raw.get("teams") or []):
            if isinstance(team, str):
                teams.append({"code": team.strip(), "level": index + 1})
                continue
            if not isinstance(team, dict):
                continue
            code = first_non_blank(team.get("code"), team.get("id"), team.get("name"))
            if not code:
                continue
            level_raw = team.get("level")
            try:
                level = float(level_raw)
            except Exception:
                level = index + 1
            teams.append({"code": code, "level": level})

        teams.sort(key=lambda item: (item["level"], item["code"]))
        primary_team = teams[0]["code"] if teams else None
        skill_levels = {
            team["code"]: int(team["level"]) if float(team["level"]).is_integer() else team["level"]
            for team in teams
        }
        meta[str(employee_id).strip()] = {
            "id": str(employee_id).strip(),
            "name": str(name).strip(),
            "teams": teams,
            "primary_team": primary_team,
            "skill_levels": skill_levels,
        }
    return meta


def build_slot_coverage(schedule):
    slot_coverage = Counter()
    for day, by_employee in iter_schedule_days(schedule):
        for segments in by_employee:
            for segment in segments:
                for slot_start in build_half_hour_slots(segment["start"], segment["end"]):
                    slot_coverage[(day, segment["team"], slot_start)] += 1
                    if segment["team"] != STAFF_TEAM_CODE:
                        slot_coverage[(day, STAFF_TEAM_CODE, slot_start)] += 1
    return slot_coverage


def iter_schedule_days(schedule):
    dates = schedule.get("dates", [])
    employees = schedule.get("employees", {})
    for day in dates:
        yield day, [employee_days.get(day, []) for employee_days in employees.values()]


def compute_coverage_metrics(demand_rows, work_periods, slot_coverage):
    required_total = 0
    fulfilled_total = 0
    actual_total = 0
    overstaff_total = 0
    critical_underfilled_periods = 0
    max_period_shortage = 0
    max_slot_shortage = 0
    gap_distribution = Counter()
    details_by_gap = defaultdict(list)
    team_totals = defaultdict(lambda: {"required": 0, "fulfilled": 0, "actual": 0, "overstaff": 0})
    underfilled_periods = []

    for row in demand_rows:
        work_period = work_periods.get(row["workPeriod"])
        if not work_period:
            continue
        slots = build_half_hour_slots(work_period["start"], work_period["end"])
        if not slots:
            continue

        required = int(row.get("minimum", 0))
        date_key = row["date"]
        team = row["team"]

        slot_values = [slot_coverage.get((date_key, team, slot_start), 0) for slot_start in slots]
        period_actual = min(slot_values) if slot_values else 0
        period_shortage = max(required - period_actual, 0)
        underfilled_slot_count = sum(1 for actual in slot_values if actual < required)
        for slot_start, actual in zip(slots, slot_values):
            slot_shortage = max(required - actual, 0)
            if slot_shortage <= 0:
                continue
            max_slot_shortage = max(max_slot_shortage, slot_shortage)
            gap_distribution[slot_shortage] += 1
            gap_key = str(slot_shortage)
            if len(details_by_gap[gap_key]) < 20:
                details_by_gap[gap_key].append(
                    {
                        "date": date_key,
                        "team": team,
                        "period": f"{minutes_to_time(slot_start)}-{minutes_to_time(slot_start + 30)}",
                        "workPeriod": row["workPeriod"],
                        "covered": actual,
                        "required": required,
                    }
                )

        if period_shortage > 0:
            critical_underfilled_periods += underfilled_slot_count
            max_period_shortage = max(max_period_shortage, period_shortage)
            underfilled_periods.append(
                {
                    "date": date_key,
                    "team": team,
                    "workPeriod": row["workPeriod"],
                    "label": work_period["name"],
                    "start": minutes_to_time(work_period["start"]),
                    "end": minutes_to_time(work_period["end"]),
                    "required": required,
                    "actual": period_actual,
                    "shortage": period_shortage,
                }
            )

        team_bucket = team_totals[team]
        for actual in slot_values:
            required_total += required
            actual_total += actual
            fulfilled = min(actual, required)
            fulfilled_total += fulfilled
            team_bucket["required"] += required
            team_bucket["actual"] += actual
            team_bucket["fulfilled"] += fulfilled
            if actual > required:
                extra = actual - required
                overstaff_total += extra
                team_bucket["overstaff"] += extra

    total_minimum_gap = required_total - fulfilled_total
    weighted_coverage_rate = round((fulfilled_total / required_total) * 100, 2) if required_total else 100.0

    team_breakdown = []
    coverage_by_team = {}
    for team, totals in sorted(team_totals.items()):
        gap = totals["required"] - totals["fulfilled"]
        rate = round((totals["fulfilled"] / totals["required"]) * 100, 2) if totals["required"] else 100.0
        coverage_by_team[team] = rate
        team_breakdown.append(
            {
                "team": team,
                "required": totals["required"],
                "actual": totals["actual"],
                "filled": totals["fulfilled"],
                "gap": gap,
                "overstaff": totals["overstaff"],
                "weightedMinimumCoverageRate": rate,
            }
        )

    underfilled_periods.sort(
        key=lambda item: (-item["shortage"], item["date"], item["team"], item["start"])
    )

    return {
        "weightedMinimumCoverageRate": weighted_coverage_rate,
        "criticalUnderfilledPeriods": critical_underfilled_periods,
        "maxPeriodShortage": max_period_shortage,
        "maxShortageSingleSlot": {
            "max_gap": max_slot_shortage,
            "gap_distribution": {
                str(gap): count
                for gap, count in sorted(gap_distribution.items(), reverse=True)
            },
            "details_by_gap": dict(details_by_gap),
        },
        "totalMinimumGap": total_minimum_gap,
        "totalOverstaff": overstaff_total,
        "coverageByTeam": coverage_by_team,
        "teamCoverageBreakdown": team_breakdown,
        "underfilledPeriods": underfilled_periods,
    }


def compute_assignment_metrics(schedule, schedule_rules, employee_meta, min_rest_hours, max_consecutive_days, coverage_priority_tiers):
    dates = [parse_iso_date(value) for value in schedule.get("dates", [])]
    ordered_dates = [value for value in dates if value is not None]
    ordered_date_keys = [value.isoformat() for value in ordered_dates]

    total_team_switches = 0
    total_fragmented_days = 0
    total_primary_minutes = 0
    total_worked_minutes = 0
    total_compliant_days = 0
    total_evaluated_days = 0
    total_hours_match_days = 0
    total_hours_evaluated_days = 0
    total_preferred_day_off_worked_days = 0
    total_preferred_day_off_days = 0
    total_skill_priority_penalty = 0
    total_availability_violations = 0
    total_consecutive_violations = 0
    total_min_rest_violations = 0
    employee_rows = []

    schedule_employees = schedule.get("employees", {})
    all_employee_ids = sorted(set(schedule_employees.keys()) | set(schedule_rules.keys()) | set(employee_meta.keys()))

    for employee_id in all_employee_ids:
        meta = employee_meta.get(employee_id, {"id": employee_id, "name": employee_id, "primary_team": None, "teams": []})
        employee_schedule = schedule_employees.get(employee_id, {})
        employee_rules = schedule_rules.get(employee_id, {})
        priority_summary = build_employee_priority_summary(meta, coverage_priority_tiers)

        team_switches = 0
        fragmented_days = 0
        primary_minutes = 0
        worked_minutes = 0
        compliant_days = 0
        evaluated_days = 0
        hours_match_days = 0
        hours_evaluated_days = 0
        active_work_days = 0
        preferred_day_off_worked_days = 0
        preferred_day_off_days = 0
        skill_priority_penalty = 0
        availability_violations = 0
        consecutive_violations = 0
        min_rest_violations = 0
        streak = 0
        previous_day_end = None
        previous_day_date = None
        team_minutes = defaultdict(int)

        for date_key in ordered_date_keys:
            segments = sort_segments(employee_schedule.get(date_key, []))
            worked = bool(segments)
            if worked:
                active_work_days += 1
            day_minutes = total_segment_minutes(segments)
            worked_minutes += day_minutes
            primary_minutes += sum(
                max(segment["end"] - segment["start"], 0)
                for segment in segments
                if meta.get("primary_team") is None or segment["team"] == meta.get("primary_team")
            )

            if len(segments) > 1:
                fragmented_days += 1

            for previous, current in zip(segments, segments[1:]):
                if previous["team"] != current["team"]:
                    team_switches += 1

            for segment in segments:
                segment_minutes = max(segment["end"] - segment["start"], 0)
                team_minutes[segment["team"]] += segment_minutes
                level = meta.get("skill_levels", {}).get(segment["team"], 1)
                try:
                    tier_index = match_coverage_priority_tier(segment["team"], level, coverage_priority_tiers)
                except ValueError:
                    tier_index = len(coverage_priority_tiers or [])
                skill_priority_penalty += len(build_half_hour_slots(segment["start"], segment["end"])) * tier_index

            rule = employee_rules.get(date_key)
            if rule is not None:
                evaluated_days += 1
                rule_upper = str(rule).strip().upper()
                if rule_upper == "DO":
                    preferred_day_off_days += 1
                    if worked:
                        preferred_day_off_worked_days += 1
                if is_day_rule_compliant(rule, segments):
                    compliant_days += 1
                else:
                    availability_violations += 1
                demanded_minutes = get_demanded_minutes(rule)
                if demanded_minutes is not None:
                    hours_evaluated_days += 1
                    if day_minutes == demanded_minutes:
                        hours_match_days += 1

            if worked:
                streak += 1
                if streak > max_consecutive_days:
                    consecutive_violations += 1
            else:
                streak = 0

            if worked and previous_day_end is not None and previous_day_date is not None:
                current_date = parse_iso_date(date_key)
                if current_date == previous_day_date + timedelta(days=1):
                    rest_hours = ((24 * 60 - previous_day_end) + segments[0]["start"]) / 60.0
                    if rest_hours < min_rest_hours:
                        min_rest_violations += 1

            if worked:
                previous_day_end = max(segment["end"] for segment in segments)
                previous_day_date = parse_iso_date(date_key)
            else:
                previous_day_end = None
                previous_day_date = None

        non_primary_minutes = max(worked_minutes - primary_minutes, 0)
        duration_rate = round((compliant_days / evaluated_days) * 100, 2) if evaluated_days else 100.0
        demanded_hours_rate = round((hours_match_days / hours_evaluated_days) * 100, 2) if hours_evaluated_days else 100.0
        primary_rate = round((primary_minutes / worked_minutes) * 100, 2) if worked_minutes else 100.0
        mean_skill_changes_per_day = round(team_switches / active_work_days, 2) if active_work_days else 0.0
        team_work_breakdown = [
            {
                "team": team,
                "hours": round(minutes / 60.0, 2),
                "percentage": round((minutes / worked_minutes) * 100, 2) if worked_minutes else 0.0,
            }
            for team, minutes in sorted(team_minutes.items(), key=lambda item: (-item[1], item[0]))
        ]

        total_team_switches += team_switches
        total_fragmented_days += fragmented_days
        total_primary_minutes += primary_minutes
        total_worked_minutes += worked_minutes
        total_compliant_days += compliant_days
        total_evaluated_days += evaluated_days
        total_hours_match_days += hours_match_days
        total_hours_evaluated_days += hours_evaluated_days
        total_preferred_day_off_worked_days += preferred_day_off_worked_days
        total_preferred_day_off_days += preferred_day_off_days
        total_skill_priority_penalty += skill_priority_penalty
        total_availability_violations += availability_violations
        total_consecutive_violations += consecutive_violations
        total_min_rest_violations += min_rest_violations

        employee_rows.append(
            {
                "employeeId": employee_id,
                "name": meta.get("name") or employee_id,
                "priorityRank": priority_summary["priorityRank"],
                "priorityLabel": priority_summary["priorityLabel"],
                "priorityTeam": priority_summary["priorityTeam"],
                "priorityLevel": priority_summary["priorityLevel"],
                "workedHours": round(worked_minutes / 60.0, 2),
                "activeWorkDays": active_work_days,
                "primaryTeam": meta.get("primary_team"),
                "primaryTeamUtilizationRate": primary_rate,
                "nonPrimaryTeamHours": round(non_primary_minutes / 60.0, 2),
                "teamWorkBreakdown": team_work_breakdown,
                "teamWorkPercentages": {
                    item["team"]: item["percentage"]
                    for item in team_work_breakdown
                },
                "teamSwitches": team_switches,
                "meanSkillChangesPerDay": mean_skill_changes_per_day,
                "fragmentedWorkDays": fragmented_days,
                "durationComplianceRate": duration_rate,
                "demandedHoursComplianceRate": demanded_hours_rate,
                "preferredDayOffWorkedDays": preferred_day_off_worked_days,
                "preferredDayOffPreservationRate": round(
                    ((preferred_day_off_days - preferred_day_off_worked_days) / preferred_day_off_days) * 100,
                    2,
                ) if preferred_day_off_days else 100.0,
                "skillPriorityPenaltyScore": skill_priority_penalty,
                "availabilityViolations": availability_violations,
                "consecutiveDaysViolations": consecutive_violations,
                "minRestViolations": min_rest_violations,
            }
        )

    employee_rows.sort(
        key=lambda item: (
            item.get("priorityRank", 10 ** 6),
            -item["workedHours"],
            item.get("name") or item["employeeId"],
        )
    )
    primary_team_utilization_rate = round((total_primary_minutes / total_worked_minutes) * 100, 2) if total_worked_minutes else 100.0
    duration_compliance_rate = round((total_compliant_days / total_evaluated_days) * 100, 2) if total_evaluated_days else 100.0
    demanded_hours_compliance_rate = round((total_hours_match_days / total_hours_evaluated_days) * 100, 2) if total_hours_evaluated_days else 100.0
    preferred_day_off_preservation_rate = (
        round(((total_preferred_day_off_days - total_preferred_day_off_worked_days) / total_preferred_day_off_days) * 100, 2)
        if total_preferred_day_off_days
        else 100.0
    )

    return {
        "intraDayTeamSwitches": total_team_switches,
        "fragmentedWorkDays": total_fragmented_days,
        "primaryTeamUtilizationRate": primary_team_utilization_rate,
        "nonPrimaryTeamHours": round(max(total_worked_minutes - total_primary_minutes, 0) / 60.0, 2),
        "durationComplianceRate": duration_compliance_rate,
        "demandedHoursComplianceRate": demanded_hours_compliance_rate,
        "preferredDayOffWorkedDays": total_preferred_day_off_worked_days,
        "preferredDayOffPreservationRate": preferred_day_off_preservation_rate,
        "skillPriorityPenaltyScore": total_skill_priority_penalty,
        "availabilityViolations": total_availability_violations,
        "consecutiveDaysViolations": total_consecutive_violations,
        "minRestViolations": total_min_rest_violations,
        "employeeAssignmentQuality": employee_rows,
    }


def is_day_rule_compliant(rule, segments):
    text = str(rule or "").strip()
    if not text:
        return True

    normalized = text.upper()
    if normalized in OFF_MARKERS:
        return not segments

    exact_match = EXACT_PATTERN.match(text)
    if exact_match:
        if not segments:
            return False
        expected_start = parse_minutes(exact_match.group(1))
        expected_end = parse_minutes(exact_match.group(2))
        if expected_start is None or expected_end is None or expected_end <= expected_start:
            return False
        return covers_exact_window(segments, expected_start, expected_end)

    allowed_hours = parse_allowed_hours(text)
    if not allowed_hours:
        return not segments
    if not segments:
        return False

    assigned_hours = total_segment_minutes(segments) / 60.0
    return any(math.isclose(assigned_hours, allowed, abs_tol=1e-6) for allowed in allowed_hours)


def covers_exact_window(segments, expected_start, expected_end):
    merged = merge_segments(segments)
    if len(merged) != 1:
        return False
    interval = merged[0]
    return interval["start"] == expected_start and interval["end"] == expected_end


def merge_segments(segments):
    ordered = sort_segments(segments)
    if not ordered:
        return []
    merged = [{"start": ordered[0]["start"], "end": ordered[0]["end"]}]
    for segment in ordered[1:]:
        last = merged[-1]
        if segment["start"] <= last["end"]:
            last["end"] = max(last["end"], segment["end"])
        elif segment["start"] == last["end"]:
            last["end"] = segment["end"]
        else:
            merged.append({"start": segment["start"], "end": segment["end"]})
    return merged


def sort_segments(segments):
    return sorted(segments or [], key=lambda item: (item["start"], item["end"], item["team"]))


def parse_allowed_hours(text):
    allowed = []
    for token in str(text).split("/"):
        token = token.strip()
        if not token:
            continue
        try:
            allowed.append(float(token))
        except ValueError:
            continue
    return allowed


def get_demanded_minutes(rule):
    text = str(rule or "").strip()
    if not text:
        return None

    exact_match = EXACT_PATTERN.match(text)
    if exact_match:
        expected_start = parse_minutes(exact_match.group(1))
        expected_end = parse_minutes(exact_match.group(2))
        if expected_start is None or expected_end is None or expected_end <= expected_start:
            return None
        return expected_end - expected_start

    normalized = text.upper()
    if normalized in OFF_MARKERS:
        return None

    allowed_hours = parse_allowed_hours(text)
    if not allowed_hours:
        return None
    if len(allowed_hours) == 1:
        return int(round(allowed_hours[0] * 60))
    return None


def total_segment_minutes(segments):
    return sum(max(segment["end"] - segment["start"], 0) for segment in segments)


def infer_team_from_work_period(code):
    token = str(code or "").strip()
    if not token:
        return ""
    return token.split("_", 1)[0].title()


def build_half_hour_slots(start, end):
    if start is None or end is None or end <= start:
        return []
    return list(range(start, end, 30))


def parse_minutes(value):
    text = str(value or "").strip()
    if not text:
        return None
    if ":" not in text:
        try:
            return int(float(text) * 60)
        except ValueError:
            return None
    parts = text.split(":", 1)
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        return None
    return hours * 60 + minutes


def minutes_to_time(value):
    if value is None:
        return ""
    hours = value // 60
    minutes = value % 60
    return f"{hours:02d}:{minutes:02d}"


def parse_iso_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return None


def parse_int_value(value):
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def first_non_blank(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None

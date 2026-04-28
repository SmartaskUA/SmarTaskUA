import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


OFF_MARKERS = {"DO", "FDO", "VAC", "NOT", "MED"}
SISQUAL_UNAVAILABLE_MARKERS = OFF_MARKERS - {"DO"}
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
OBJECTIVE_SOFT_TYPES = {
    "coverage_shortage": {
        "min_coverage",
        "coverage_shortage",
        "objective1",
        "minimize_shortages",
        "minimize_total_shortage",
        "minimize_coverage_shortage",
    },
    "average_competence": {
        "average_competence",
        "average_competence_level",
        "minimize_average_competence_level",
        "objective3",
        "competence_score",
        "competency_score",
    },
    "preferred_day_off": {
        "day_off_swap_penalty",
        "preferred_day_off",
        "preferred_day_off_work",
        "minimize_preferred_day_off_work",
        "objective4",
        "minimize_day_off_changes",
    },
    "skill_priority_assignment": {
        "skill_priority_assignment",
        "priority_skill_assignment",
        "assign_higher_priority_skills",
        "minimize_lower_priority_skill_assignment",
        "objective5",
        "skill_priority",
    },
}
OBJECTIVE2_GOALS = {
    "objective2",
    "competence_level_shortage",
    "competency_level_shortage",
    "minimize_competence_level_shortage",
    "minimize_competency_level_shortage",
}


@dataclass(frozen=True)
class TimeSlot:
    index: int
    start_min: int
    end_min: int

    @property
    def label(self) -> str:
        return f"{minutes_to_hhmm(self.start_min)}-{minutes_to_hhmm(self.end_min)}"


@dataclass(frozen=True)
class Assignment:
    key: str
    start_min: int
    end_min: int
    slot_indices: Tuple[int, ...]

    @property
    def label(self) -> str:
        return f"{minutes_to_hhmm(self.start_min)}-{minutes_to_hhmm(self.end_min)}"


def load_problem_json(path: Path) -> Dict:
    with path.open() as f:
        return json.load(f)


def parse_contract_hours(problem: Dict) -> Dict[str, int]:
    definitions = problem.get("contracts", {}).get("definitions", [])
    result = {}
    for item in definitions:
        contract_id = str(item.get("id", "")).strip()
        hours = item.get("workHoursPerDay")
        if contract_id and hours is not None:
            result[contract_id] = int(hours)
    return result


def parse_work_periods(problem: Dict) -> Dict[str, Tuple[int, int]]:
    result = {}
    for period in problem.get("demand", {}).get("workPeriods", []):
        code = str(period.get("code", "")).strip()
        time_range = period.get("timeRange", {})
        start = parse_hhmm(str(time_range.get("start", "")))
        end = parse_hhmm(str(time_range.get("end", "")))
        if code:
            result[code] = (start, end)
    return result


def parse_employees(problem: Dict, contract_hours: Dict[str, int]) -> List[Dict]:
    raw_employees = problem.get("employees", {}).get("competency", [])
    employees = []
    for raw in raw_employees:
        employee_id = str(raw.get("id", "")).strip()
        contract_type = str(raw.get("contractType", "")).strip()
        skills = []
        for team in raw.get("teams", []):
            code = str(team.get("code", "")).strip()
            if code:
                skills.append(code)
        employees.append(
            {
                "id": employee_id,
                "name": raw.get("name", employee_id),
                "contract_type": contract_type,
                "contract_hours": contract_hours.get(contract_type),
                "skills": tuple(dict.fromkeys(skills)),
            }
        )
    return employees


def parse_employees_with_levels(
    problem: Dict,
    contract_hours: Dict[str, int],
    staff_team_code: str = "Employees",
) -> List[Dict]:
    raw_employees = problem.get("employees", {}).get("competency", [])
    employees = []
    for raw in raw_employees:
        employee_id = str(raw.get("id", "")).strip()
        contract_type = str(raw.get("contractType", "")).strip()
        skill_levels = {}
        for team in raw.get("teams", []):
            code = str(team.get("code", "")).strip()
            if not code:
                continue
            level = parse_level_value(team.get("level"))
            if level is None:
                raise ValueError(f"Missing or invalid level for {employee_id} skill '{code}'")
            skill_levels[code] = level
        if staff_team_code and staff_team_code not in skill_levels:
            raise ValueError(
                f"Employee '{employee_id}' is missing required '{staff_team_code}' competency"
            )
        employees.append(
            {
                "id": employee_id,
                "name": raw.get("name", employee_id),
                "contract_type": contract_type,
                "contract_hours": contract_hours.get(contract_type),
                "skills": tuple(skill_levels.keys()),
                "skill_levels": dict(skill_levels),
                "assignable_skills": tuple(skill_levels.keys()),
            }
        )
    return employees


def parse_days(problem: Dict) -> List[str]:
    target = problem.get("temporalScope", {}).get("targetPeriod", {})
    start = datetime.strptime(target["start"], "%Y-%m-%d").date()
    end = datetime.strptime(target["end"], "%Y-%m-%d").date()
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def parse_schedule_input(base_dir: Path, problem: Dict, days: List[str]) -> Dict[str, Dict[str, str]]:
    schedule_path = base_dir / problem.get("scheduleInput", {}).get("dataFile", "schedule_input.csv")
    with schedule_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing_days = [day for day in days if day not in fieldnames]
        if missing_days:
            preview = ", ".join(missing_days[:5])
            if len(missing_days) > 5:
                preview += ", ..."
            raise ValueError(
                f"Schedule input '{schedule_path.name}' is missing targetPeriod day columns: {preview}"
            )
        rows = {}
        for row in reader:
            employee_id = str(row.get("employee_id", "")).strip()
            rows[employee_id] = {day: str(row.get(day, "")).strip() for day in days}
    return rows


def parse_min_rest_hours(problem: Dict, default_hours: float = 11.0) -> float:
    constraints = problem.get("constraints", {}).get("hard", [])
    for constraint in constraints:
        if constraint.get("type") != "min_rest_hours" or not constraint.get("enabled", True):
            continue
        hours = constraint.get("params", {}).get("hours")
        if isinstance(hours, (int, float)):
            return float(hours)
    return default_hours


def parse_skill_codes(problem: Dict) -> List[str]:
    teams = problem.get("demand", {}).get("organizationalUnits", {}).get("teams", [])
    codes = []
    for item in teams:
        if isinstance(item, dict):
            code = item.get("code")
        else:
            code = item
        if code:
            codes.append(str(code).strip())
    return list(dict.fromkeys(codes))


def build_half_hour_slots(work_periods: Dict[str, Tuple[int, int]]) -> List[TimeSlot]:
    if not work_periods:
        raise ValueError("No work periods defined in problem.json")
    min_start = min(start for start, _ in work_periods.values())
    max_end = max(end for _, end in work_periods.values())
    slots = []
    idx = 0
    current = min_start
    while current < max_end:
        slots.append(TimeSlot(index=idx, start_min=current, end_min=current + 30))
        idx += 1
        current += 30
    return slots


def build_period_slot_map(work_periods: Dict[str, Tuple[int, int]], time_slots: List[TimeSlot]) -> Dict[str, Tuple[int, ...]]:
    result = {}
    for code, (start_min, end_min) in work_periods.items():
        covered = []
        for slot in time_slots:
            if slot.start_min >= start_min and slot.end_min <= end_min:
                covered.append(slot.index)
        result[code] = tuple(covered)
    return result


def parse_demand_minimums(base_dir: Path, problem: Dict, coverage_by_period: Dict[str, Tuple[int, ...]]) -> Dict[Tuple[str, int, str], int]:
    demand_path = base_dir / problem.get("demand", {}).get("dataFile", "demand.csv")
    alpha = defaultdict(int)
    with demand_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = str(row.get("date", "")).strip()
            period_code = str(row.get("workPeriod", "")).strip()
            skill = str(row.get("team", "")).strip()
            minimum_text = str(row.get("minimum", "")).strip()
            if not date_str or not period_code or not skill or not minimum_text:
                continue
            minimum = int(minimum_text)
            for slot_idx in coverage_by_period.get(period_code, ()):
                alpha[(date_str, slot_idx, skill)] += minimum
    return dict(alpha)


def build_assignments(
    employees: List[Dict],
    days: List[str],
    schedule_markers: Dict[str, Dict[str, str]],
    time_slots: List[TimeSlot],
) -> Dict[Tuple[str, str], List[Assignment]]:
    assignments = {}
    first_slot_start = time_slots[0].start_min
    last_slot_end = time_slots[-1].end_min
    num_slots = len(time_slots)

    for employee in employees:
        employee_id = employee["id"]
        for day in days:
            marker = schedule_markers.get(employee_id, {}).get(day, "")
            normalized = normalize_marker(marker)
            key = (employee_id, day)
            day_assignments = []

            if normalized in OFF_MARKERS or not normalized:
                assignments[key] = day_assignments
                continue

            if normalized.startswith("EQUALS:"):
                time_range = normalized.split(":", 1)[1]
                start_text, end_text = time_range.split("-", 1)
                start_min = parse_hhmm(start_text)
                end_min = parse_hhmm(end_text)
                slot_indices = tuple(
                    slot.index
                    for slot in time_slots
                    if slot.start_min >= start_min and slot.end_min <= end_min
                )
                if not slot_indices:
                    raise ValueError(f"No slots found for exact marker '{marker}' on {employee_id} {day}")
                day_assignments.append(
                    Assignment(
                        key=f"{employee_id}_{day}_exact_{start_min}_{end_min}",
                        start_min=start_min,
                        end_min=end_min,
                        slot_indices=slot_indices,
                    )
                )
                assignments[key] = day_assignments
                continue

            if not normalized.isdigit():
                raise ValueError(f"Unsupported schedule marker '{marker}' for {employee_id} on {day}")

            hours = int(normalized)
            required_slots = hours * 2
            if required_slots <= 0:
                assignments[key] = day_assignments
                continue
            for start_idx in range(0, num_slots - required_slots + 1):
                covered = tuple(range(start_idx, start_idx + required_slots))
                start_min = time_slots[start_idx].start_min
                end_min = time_slots[start_idx + required_slots - 1].end_min
                if start_min < first_slot_start or end_min > last_slot_end:
                    continue
                day_assignments.append(
                    Assignment(
                        key=f"{employee_id}_{day}_{start_idx}_{required_slots}",
                        start_min=start_min,
                        end_min=end_min,
                        slot_indices=covered,
                    )
                )
            if not day_assignments:
                raise ValueError(f"No feasible assignments generated for {employee_id} on {day} with marker '{marker}'")
            assignments[key] = day_assignments
    return assignments


def build_sisqual_day_modes(
    employees: List[Dict],
    days: List[str],
    schedule_markers: Dict[str, Dict[str, str]],
    closed_days,
) -> Dict[Tuple[str, str], str]:
    closed_days = set(closed_days)
    day_modes = {}
    for employee in employees:
        employee_id = employee["id"]
        for day in days:
            marker = normalize_marker(schedule_markers[employee_id][day])
            if day in closed_days:
                day_modes[(employee_id, day)] = "closed"
            elif marker in SISQUAL_UNAVAILABLE_MARKERS or not marker:
                day_modes[(employee_id, day)] = "unavailable"
            elif marker == "DO":
                day_modes[(employee_id, day)] = "preferred_day_off"
            elif marker.startswith("EQUALS:"):
                day_modes[(employee_id, day)] = "fixed_time_work"
            elif marker == "A" or marker.isdigit():
                day_modes[(employee_id, day)] = "work_template"
            else:
                raise ValueError(
                    f"Unsupported schedule marker '{schedule_markers[employee_id][day]}' "
                    f"for {employee_id} on {day}"
                )
    return day_modes


def build_sisqual_bundle_assignments(
    employees: List[Dict],
    days: List[str],
    schedule_markers: Dict[str, Dict[str, str]],
    time_slots: List[TimeSlot],
    day_modes: Dict[Tuple[str, str], str],
    variable_days_off_active: bool,
) -> Dict[Tuple[str, str], List[Assignment]]:
    assignments = {}
    num_slots = len(time_slots)

    for employee in employees:
        employee_id = employee["id"]
        contract_hours = employee["contract_hours"]
        for day in days:
            key = (employee_id, day)
            mode = day_modes[key]
            marker = normalize_marker(schedule_markers[employee_id][day])
            day_assignments = []

            if mode in {"closed", "unavailable"}:
                assignments[key] = day_assignments
                continue

            if mode == "preferred_day_off" and not variable_days_off_active:
                assignments[key] = day_assignments
                continue

            if marker.startswith("EQUALS:"):
                time_range = marker.split(":", 1)[1]
                start_text, end_text = time_range.split("-", 1)
                start_min = parse_hhmm(start_text)
                end_min = parse_hhmm(end_text)
                slot_indices = tuple(
                    slot.index
                    for slot in time_slots
                    if slot.start_min >= start_min and slot.end_min <= end_min
                )
                if not slot_indices:
                    raise ValueError(
                        f"No slots found for exact marker '{marker}' on {employee_id} {day}"
                    )
                day_assignments.append(
                    Assignment(
                        key=f"{employee_id}_{day}_exact_{start_min}_{end_min}",
                        start_min=start_min,
                        end_min=end_min,
                        slot_indices=slot_indices,
                    )
                )
                assignments[key] = day_assignments
                continue

            hours = None
            if marker == "A":
                hours = contract_hours
            elif marker == "DO":
                hours = contract_hours
            elif marker.isdigit():
                hours = int(marker)

            if hours is None or hours <= 0:
                raise ValueError(
                    f"Missing or invalid hours for swappable marker "
                    f"'{schedule_markers[employee_id][day]}' on {employee_id} {day}"
                )

            required_slots = hours * 2
            for start_idx in range(0, num_slots - required_slots + 1):
                covered = tuple(range(start_idx, start_idx + required_slots))
                start_min = time_slots[start_idx].start_min
                end_min = time_slots[start_idx + required_slots - 1].end_min
                day_assignments.append(
                    Assignment(
                        key=f"{employee_id}_{day}_{start_idx}_{required_slots}",
                        start_min=start_min,
                        end_min=end_min,
                        slot_indices=covered,
                    )
                )

            if not day_assignments:
                raise ValueError(
                    f"No feasible assignments generated for {employee_id} on {day} "
                    f"with marker '{schedule_markers[employee_id][day]}'"
                )

            assignments[key] = day_assignments

    return assignments


def group_open_days_by_week(problem: Dict, open_days: List[str], date_by_day: Dict[str, object]) -> List[List[str]]:
    if not open_days:
        return []

    day_off_cfg = (
        problem.get("constraints", {})
        .get("advanced", {})
        .get("dayOffSwapping", {})
    )
    week_definition = str(day_off_cfg.get("weekDefinition", "monday-sunday")).strip().lower()

    groups = defaultdict(list)
    for day in open_days:
        current = date_by_day[day]
        if week_definition == "sunday-saturday":
            offset = (current.weekday() + 1) % 7
        else:
            offset = current.weekday()
        week_start = current - timedelta(days=offset)
        groups[week_start].append(day)

    return [groups[key] for key in sorted(groups)]


def match_coverage_priority_tier(
    coverage_priority_tiers: List[Dict],
    skill: str,
    nth_worker: int,
) -> int:
    for index, tier in enumerate(coverage_priority_tiers):
        if tier["skill"] != skill:
            continue
        if nth_worker < tier["min_n"]:
            continue
        max_n = tier["max_n"]
        if max_n is not None and nth_worker > max_n:
            continue
        return index
    raise ValueError(f"No ObjectiveFunction1 priority tier matches skill '{skill}' worker #{nth_worker}")


def build_objective1_priority_index(
    alpha: Dict[Tuple[str, int, str], int],
    coverage_priority_tiers: List[Dict],
) -> Dict[Tuple[str, int, str, int], int]:
    priority_index = {}
    for (day, slot_idx, skill), minimum in alpha.items():
        for nth_worker in range(1, max(0, minimum) + 1):
            priority_index[(day, slot_idx, skill, nth_worker)] = match_coverage_priority_tier(
                coverage_priority_tiers,
                skill,
                nth_worker,
            )
    return priority_index


def build_objective1_priority_coefficients(
    coverage_priority_tiers: List[Dict],
) -> Dict[int, int]:
    num_tiers = len(coverage_priority_tiers)
    return {
        tier_index: 10 ** (num_tiers - tier_index - 1)
        for tier_index in range(num_tiers)
    }


def build_objective5_skill_priority(
    employees: List[Dict],
    coverage_priority_tiers: List[Dict],
) -> Dict[Tuple[str, str], int]:
    """Return {(employee_id, skill): tier_index} for the worker's actual competence level."""
    fallback = len(coverage_priority_tiers)
    skill_priority = {}
    for employee in employees:
        employee_id = employee["id"]
        for skill in employee["assignable_skills"]:
            level = employee["skill_levels"].get(skill, 1)
            try:
                tier_idx = match_coverage_priority_tier(coverage_priority_tiers, skill, level)
            except ValueError:
                tier_idx = fallback
            skill_priority[(employee_id, skill)] = tier_idx
    return skill_priority


def parse_hhmm(value: str) -> int:
    hour, minute = value.strip().split(":", 1)
    return int(hour) * 60 + int(minute)


def minutes_to_hhmm(value: int) -> str:
    hour = value // 60
    minute = value % 60
    return f"{hour:02d}:{minute:02d}"


def normalize_marker(value: str) -> str:
    text = str(value or "").strip()
    if text.upper().startswith("EQUALS:"):
        return "EQUALS:" + text.split(":", 1)[1]
    return text.upper()


def parse_max_time_seconds(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        minutes = float(value)
    except (TypeError, ValueError):
        return None
    if minutes <= 0:
        return None
    return int(minutes * 60)


def parse_int_value(value) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_level_value(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return int(digits)
    return None


def parse_open_days(days: List[str], alpha: Dict[Tuple[str, int, str], int]) -> List[str]:
    open_days = sorted({day for (day, _, _) in alpha.keys()})
    return open_days or list(days)


def parse_coverage_priority_tiers(
    problem: Dict,
    skills: List[str],
    staff_team_code: str = "Employees",
) -> List[Dict]:
    """Build the ordered list of (skill, level-range) priority tiers used by Objective 1.

    The tier list is driven by ``demand.priorityHierarchy`` in problem.json when every
    entry there carries ``minLevel`` (and optionally ``maxLevel``) fields.  This lets
    each problem define its own alarm priority order without touching the code.

    If the JSON hierarchy does not contain level fields the function falls back to
    ``DEFAULT_SISQUAL_COVERAGE_PRIORITY_TIERS``, which encodes the standard Sisqual
    9-tier order from the BFarias specification.
    """
    raw_hierarchy = sorted(
        problem.get("demand", {}).get("priorityHierarchy", []),
        key=lambda item: parse_int_value(item.get("rank")) or 10 ** 6,
    )

    # Use the JSON hierarchy as the full tier definition when it specifies levels.
    if any(entry.get("minLevel") is not None for entry in raw_hierarchy):
        priority_tiers = []
        for index, entry in enumerate(raw_hierarchy):
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
        # Fall back to the hardcoded Sisqual defaults.
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

    # Ensure the generic Employees team is always present as the lowest-priority tier.
    known_skill_levels = {(t["skill"], t["min_n"]) for t in priority_tiers}
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

    # Append any skills present in the problem but not covered by any tier.
    known_skills = {t["skill"] for t in priority_tiers}
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


def parse_soft_constraint_weight(constraint: Dict) -> float:
    params = constraint.get("params", {}) or {}
    for value in (
        constraint.get("weight"),
        params.get("weight"),
        params.get("penalty"),
        params.get("penalty_per_missing"),
        params.get("penalty_within_week"),
        params.get("penalty_outside_week"),
    ):
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def parse_soft_objectives(problem: Dict) -> Tuple[float, Dict[Tuple[str, int], float], float, float, float]:
    objective1_weight = 0.0
    objective2_weight_map = {}
    objective3_weight = 0.0
    objective4_weight = 0.0
    objective5_weight = 0.0

    for constraint in problem.get("constraints", {}).get("soft", []):
        if not constraint.get("enabled", True):
            continue
        type_name = str(
            constraint.get("type")
            or constraint.get("id")
            or ""
        ).strip().lower()
        params = constraint.get("params", {}) or {}
        weight = parse_soft_constraint_weight(constraint)
        if weight <= 0:
            continue

        if type_name in OBJECTIVE_SOFT_TYPES["coverage_shortage"]:
            objective1_weight = weight
        elif type_name in OBJECTIVE2_GOALS:
            skill = str(
                constraint.get("skill")
                or constraint.get("team")
                or constraint.get("competency")
                or params.get("skill")
                or params.get("team")
                or params.get("competency")
                or ""
            ).strip()
            level = parse_level_value(
                constraint.get("level", params.get("level"))
            )
            if not skill or level is None:
                continue
            objective2_weight_map[(skill, level)] = weight
        elif type_name in OBJECTIVE_SOFT_TYPES["average_competence"]:
            objective3_weight = weight
        elif type_name in OBJECTIVE_SOFT_TYPES["preferred_day_off"]:
            objective4_weight = weight
        elif type_name in OBJECTIVE_SOFT_TYPES["skill_priority_assignment"]:
            objective5_weight = weight

    return objective1_weight, objective2_weight_map, objective3_weight, objective4_weight, objective5_weight


def parse_json_mapping(value, label: str = "mapping") -> Dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError(f"Expected {label} to be a JSON object")
        return parsed
    raise ValueError(f"Expected {label} as dict or JSON object string")


def parse_objective2_weight_map(value) -> Dict[Tuple[str, int], float]:
    if value is None:
        return {}

    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, str):
        items = parse_json_mapping(value, "objective2_weights").items()
    else:
        raise ValueError("Objective 2 weights must be provided as dict or JSON object string")

    result = {}
    for key, weight in items:
        if isinstance(key, tuple) and len(key) == 2:
            skill = str(key[0]).strip()
            level = parse_level_value(key[1])
        else:
            text = str(key).strip()
            if ":" not in text:
                raise ValueError(
                    "Objective 2 weight keys must use 'skill:level', for example 'Checkout:1'"
                )
            skill, level_text = text.split(":", 1)
            skill = skill.strip()
            level = parse_level_value(level_text)
        if not skill or level is None:
            raise ValueError(f"Invalid Objective 2 weight key '{key}'")
        try:
            result[(skill, level)] = float(weight)
        except (TypeError, ValueError):
            result[(skill, level)] = 0.0
    return result


def resolve_beta_requirements_path(
    base_dir: Path,
    problem: Dict,
    beta_requirements_path,
) -> Path | None:
    candidate = beta_requirements_path
    if candidate is None:
        demand_cfg = problem.get("demand", {})
        candidate = (
            demand_cfg.get("betaRequirementsFile")
            or demand_cfg.get("levelRequirementsFile")
            or demand_cfg.get("competencyRequirementsFile")
        )
    if not candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def parse_beta_csv(
    path: Path,
    coverage_by_period: Dict[str, Tuple[int, ...]],
    time_slots: List[TimeSlot],
) -> Dict[Tuple[str, int, str, int], int]:
    beta = defaultdict(int)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = str(row.get("date", "")).strip()
            skill = str(
                row.get("team")
                or row.get("skill")
                or row.get("competency")
                or ""
            ).strip()
            level = parse_level_value(row.get("level"))
            minimum = parse_int_value(
                row.get("minimum")
                or row.get("minimo")
                or row.get("beta")
            )
            if not date_str or not skill or level is None or minimum is None:
                continue

            period_code = str(row.get("workPeriod", "")).strip()
            if period_code:
                for slot_idx in coverage_by_period.get(period_code, ()):
                    beta[(date_str, slot_idx, skill, level)] += minimum
                continue

            start_text = str(row.get("start", "")).strip()
            end_text = str(row.get("end", "")).strip()
            if not start_text or not end_text:
                continue
            start_min = parse_hhmm(start_text)
            end_min = parse_hhmm(end_text)
            for slot in time_slots:
                if slot.start_min >= start_min and slot.end_min <= end_min:
                    beta[(date_str, slot.index, skill, level)] += minimum

    return dict(beta)


def parse_inline_beta_requirements(
    requirements: Iterable[Dict],
    time_slots: List[TimeSlot],
    open_days: List[str],
) -> Dict[Tuple[str, int, str, int], int]:
    beta = defaultdict(int)
    for requirement in requirements:
        skill = str(
            requirement.get("competency")
            or requirement.get("team")
            or requirement.get("skill")
            or ""
        ).strip()
        level = parse_level_value(requirement.get("level"))
        minimum = parse_int_value(
            requirement.get("minimo")
            or requirement.get("minimum")
            or requirement.get("beta")
        )
        time_window = requirement.get("timeWindow", {})
        start_text = str(time_window.get("start", "")).strip()
        end_text = str(time_window.get("end", "")).strip()

        if not skill or level is None or minimum is None or not start_text or not end_text:
            continue

        start_min = parse_hhmm(start_text)
        end_min = parse_hhmm(end_text)
        applicable_days = _resolve_beta_requirement_days(requirement.get("applies", {}), open_days)

        for day in applicable_days:
            for slot in time_slots:
                if slot.start_min >= start_min and slot.end_min <= end_min:
                    beta[(day, slot.index, skill, level)] += minimum

    return dict(beta)


def parse_beta_requirements(
    base_dir: Path,
    problem: Dict,
    coverage_by_period: Dict[str, Tuple[int, ...]],
    time_slots: List[TimeSlot],
    open_days: List[str],
    objective2_weights: Dict[Tuple[str, int], float],
    beta_requirements_path=None,
) -> Dict[Tuple[str, int, str, int], int]:
    if not objective2_weights:
        return {}

    beta = defaultdict(int)
    csv_path = resolve_beta_requirements_path(base_dir, problem, beta_requirements_path)
    if csv_path is not None:
        beta.update(parse_beta_csv(csv_path, coverage_by_period, time_slots))

    inline_requirements = problem.get("demand", {}).get("multiLevel", {}).get("requirements", [])
    if inline_requirements:
        for key, value in parse_inline_beta_requirements(inline_requirements, time_slots, open_days).items():
            beta[key] += value

    if not beta:
        formatted_pairs = ", ".join(
            f"{skill}:{level}" for skill, level in sorted(objective2_weights)
        )
        raise ValueError(
            "ObjectiveFunction2 received weights but no beta requirements were found. "
            f"Expected CSV or inline requirements for: {formatted_pairs}"
        )

    missing_pairs = sorted(
        pair
        for pair in objective2_weights
        if not any(skill == pair[0] and level == pair[1] for (_, _, skill, level) in beta)
    )
    if missing_pairs:
        formatted_pairs = ", ".join(f"{skill}:{level}" for skill, level in missing_pairs)
        raise ValueError(
            "ObjectiveFunction2 received weights for pairs with no beta requirements: "
            f"{formatted_pairs}"
        )

    return dict(beta)


def _resolve_beta_requirement_days(applies: Dict, open_days: List[str]) -> List[str]:
    dates = applies.get("dates")
    if dates:
        open_days_set = set(open_days)
        return [day for day in dates if day in open_days_set]

    day_type = str(applies.get("dayType", "all")).strip().lower()
    if day_type == "weekday":
        return [day for day in open_days if datetime.strptime(day, "%Y-%m-%d").date().weekday() < 5]
    if day_type == "weekend":
        return [day for day in open_days if datetime.strptime(day, "%Y-%m-%d").date().weekday() >= 5]
    return list(open_days)

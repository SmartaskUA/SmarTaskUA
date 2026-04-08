import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


OFF_MARKERS = {"DO", "FDO", "VAC", "NOT", "MED"}
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
        employees.append(
            {
                "id": employee_id,
                "name": raw.get("name", employee_id),
                "contract_type": contract_type,
                "contract_hours": contract_hours.get(contract_type),
                "skills": tuple(skill_levels.keys()),
                "skill_levels": dict(skill_levels),
                "assignable_skills": tuple(
                    skill for skill in skill_levels.keys() if skill != staff_team_code
                ),
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


def parse_soft_objectives(problem: Dict) -> Tuple[float, Dict[Tuple[str, int], float], float, float]:
    objective1_weight = 0.0
    objective2_weight_map = {}
    objective3_weight = 0.0
    objective4_weight = 0.0

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

    return objective1_weight, objective2_weight_map, objective3_weight, objective4_weight


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

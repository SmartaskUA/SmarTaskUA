from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from validators.sisqual_report_pdf import write_pdf_report
except ModuleNotFoundError:
    from .sisqual_report_pdf import write_pdf_report


OFF_MARKERS = {"", "DO", "FDO", "VAC", "NOT", "MED", "ENFD", "DC-E"}
HARD_UNAVAILABLE_MARKERS = OFF_MARKERS - {"DO"}
REPORT_ROOT = None


@dataclass
class ValidationIssue:
    code: str
    severity: str
    title: str
    message: str
    employee_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    suggested_fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "employeeId": self.employee_id,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "suggestedFix": self.suggested_fix,
        }


class SisqualValidationError(Exception):
    def __init__(self, summary: str, report: dict[str, Any]):
        super().__init__(summary)
        self.summary = summary
        self.report = report
        self.failure_type = report.get("failureType", "INFEASIBLE_PRECHECK")
        self.report_artifacts = report.get("reportArtifacts", {})


def validate_sisqual_problem_or_raise(problem_path: str | None, task_id: str, algorithm_name: str | None = None) -> None:
    if not problem_path:
        return

    resolved = Path(problem_path)
    if not resolved.is_absolute():
        resolved = (Path.cwd() / resolved).resolve()
    if resolved.is_dir():
        resolved = resolved / "problem.json"
    if not resolved.is_file():
        return

    problem = _read_json(resolved)
    if not _is_sisqual_problem(problem):
        return

    report = validate_sisqual_problem(resolved, task_id, algorithm_name=algorithm_name)
    if report["errorCount"] > 0:
        raise SisqualValidationError(report["summary"], report)


def default_report_root() -> Path:
    shared_mount = Path("/shared_tmp")
    if shared_mount.exists():
        return shared_mount / "validation_reports"

    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent / "shared_tmp" / "validation_reports"

    return Path.cwd() / "shared_tmp" / "validation_reports"


def build_solver_infeasible_report(
    problem_path: str | None,
    task_id: str,
    algorithm_name: str,
    solver_status: str,
    model_stats: dict[str, Any] | None = None,
) -> SisqualValidationError:
    issue = ValidationIssue(
        code="SOLVER_INFEASIBLE",
        severity="error",
        title="Solver reported infeasible model",
        message=(
            f"{algorithm_name} returned status {solver_status}. The precheck did not find "
            "an obvious structural cause, so the infeasibility likely depends on the full model."
        ),
        suggested_fix="Review hard constraints and run the model on a smaller date range to isolate the conflict.",
    )
    report = _base_report(problem_path, task_id, algorithm_name, "SOLVER_INFEASIBLE", [issue])
    _write_report_artifacts(report, task_id)
    return SisqualValidationError(report["summary"], report)


def validate_sisqual_problem(problem_json_path: Path, task_id: str, algorithm_name: str | None = None) -> dict[str, Any]:
    problem = _read_json(problem_json_path)
    base_dir = problem_json_path.parent
    issues: list[ValidationIssue] = []

    days = _target_days(problem, issues)
    day_set = set(days)
    work_periods = _work_periods(problem, issues)
    employees = _employees(problem)
    employee_ids = set(employees)
    employee_skills = _employee_skills(problem)
    min_rest_hours = _min_rest_hours(problem)
    max_consecutive = 5

    demand_file = problem.get("demand", {}).get("dataFile", "demand.csv")
    schedule_file = problem.get("scheduleInput", {}).get("dataFile", "schedule_input.csv")
    demand_rows = _read_dict_rows(base_dir / demand_file, "demand.csv", issues)
    schedule_header, schedule_rows = _read_raw_rows(base_dir / schedule_file, "schedule_input.csv", issues)
    schedule_by_employee = {row[0]: row for row in schedule_rows if row}

    _validate_demand_dates_and_periods(demand_rows, day_set, work_periods, employee_skills, issues)
    _validate_schedule_shape(schedule_header, schedule_rows, days, employee_ids, issues)
    _validate_schedule_markers(schedule_header, schedule_rows, work_periods, issues)
    _validate_possible_coverage(demand_rows, schedule_header, schedule_rows, employees, employee_skills, problem, issues)
    _validate_consecutive_and_weekly(schedule_header, schedule_rows, max_consecutive, issues)
    _validate_fixed_rest(schedule_header, schedule_by_employee, min_rest_hours, issues)

    report = _base_report(str(problem_json_path), task_id, algorithm_name, "INFEASIBLE_PRECHECK", issues)
    if report["errorCount"] > 0:
        _write_report_artifacts(report, task_id)
    return report


def _base_report(
    problem_path: str | None,
    task_id: str,
    algorithm_name: str | None,
    failure_type: str,
    issues: list[ValidationIssue],
) -> dict[str, Any]:
    issue_dicts = [issue.to_dict() for issue in issues]
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity != "error"]
    summary = "Problem passed Sisqual feasibility precheck."
    if errors:
        first = errors[0]
        summary = f"{first.title}: {first.message}"
    elif warnings:
        summary = f"Problem passed Sisqual feasibility precheck with {len(warnings)} warning(s)."
    report = {
        "taskId": task_id,
        "status": "FAILED_VALIDATION" if errors else "PASSED",
        "failureType": failure_type if errors else None,
        "summary": summary,
        "problemPath": problem_path,
        "algorithm": algorithm_name,
        "issueCount": len(issues),
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "issues": issue_dicts,
        "generatedAt": datetime.now().isoformat(),
        "reportArtifacts": {},
    }
    return report


def _write_report_artifacts(report: dict[str, Any], task_id: str) -> None:
    report_dir = default_report_root() / str(task_id)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "report.json"
    md_path = report_dir / "report.md"
    pdf_path = report_dir / "report.pdf"

    report["reportArtifacts"] = {
        "json": str(json_path.resolve()),
        "markdown": str(md_path.resolve()),
        "pdf": str(pdf_path.resolve()),
    }
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_text = _render_markdown(report)
    md_path.write_text(md_text, encoding="utf-8")
    write_pdf_report(pdf_path, report)


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Sisqual Feasibility Report - {report.get('taskId')}",
        "",
        f"**Status:** {report.get('status')}",
        f"**Failure type:** {report.get('failureType') or 'N/A'}",
        f"**Problem:** `{report.get('problemPath') or 'N/A'}`",
        f"**Algorithm:** {report.get('algorithm') or 'N/A'}",
        f"**Generated at:** {report.get('generatedAt')}",
        "",
        "## Summary",
        report.get("summary", ""),
        "",
        "## Issues",
    ]
    if not report.get("issues"):
        lines.append("No blocking issues were detected.")
    elif report.get("errorCount", 0) == 0:
        lines.append("No blocking issues were detected. The items below are warnings.")
    for index, issue in enumerate(report.get("issues", []), start=1):
        lines.extend(
            [
                f"### {index}. {issue.get('title')}",
                f"- **Code:** `{issue.get('code')}`",
                f"- **Severity:** {issue.get('severity')}",
                f"- **Message:** {issue.get('message')}",
            ]
        )
        if issue.get("employeeId"):
            lines.append(f"- **Employee:** `{issue.get('employeeId')}`")
        if issue.get("startDate") or issue.get("endDate"):
            lines.append(f"- **Period:** {issue.get('startDate') or '?'} to {issue.get('endDate') or '?'}")
        if issue.get("suggestedFix"):
            lines.append(f"- **Suggested fix:** {issue.get('suggestedFix')}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _read_dict_rows(path: Path, label: str, issues: list[ValidationIssue]) -> list[dict[str, str]]:
    if not path.is_file():
        issues.append(ValidationIssue("MISSING_FILE", "error", "Missing data file", f"{label} was not found at {path}."))
        return []
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _read_raw_rows(path: Path, label: str, issues: list[ValidationIssue]) -> tuple[list[str], list[list[str]]]:
    if not path.is_file():
        issues.append(ValidationIssue("MISSING_FILE", "error", "Missing data file", f"{label} was not found at {path}."))
        return [], []
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if not rows:
        issues.append(ValidationIssue("EMPTY_FILE", "error", "Empty data file", f"{label} is empty."))
        return [], []
    return rows[0], rows[1:]


def _is_sisqual_problem(problem: dict[str, Any]) -> bool:
    demand = problem.get("demand", {})
    schedule = problem.get("scheduleInput", {})
    teams = demand.get("organizationalUnits", {}).get("teams", [])
    return bool(demand.get("workPeriods")) and bool(schedule.get("dataFile")) and bool(teams)


def _target_days(problem: dict[str, Any], issues: list[ValidationIssue]) -> list[str]:
    try:
        target = problem.get("temporalScope", {}).get("targetPeriod", {})
        start = datetime.strptime(target["start"], "%Y-%m-%d").date()
        end = datetime.strptime(target["end"], "%Y-%m-%d").date()
    except Exception as exc:
        issues.append(ValidationIssue("INVALID_TARGET_PERIOD", "error", "Invalid target period", str(exc)))
        return []
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _work_periods(problem: dict[str, Any], issues: list[ValidationIssue]) -> dict[str, tuple[int, int]]:
    periods = {}
    for period in problem.get("demand", {}).get("workPeriods", []):
        code = str(period.get("code", "")).strip()
        try:
            time_range = period.get("timeRange", {})
            periods[code] = (_parse_hhmm(time_range["start"]), _parse_hhmm(time_range["end"]))
        except Exception:
            issues.append(ValidationIssue("INVALID_WORK_PERIOD", "error", "Invalid work period", f"Work period {code} has invalid time range."))
    return periods


def _employees(problem: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(emp.get("id", "")).strip(): emp for emp in problem.get("employees", {}).get("competency", []) if emp.get("id")}


def _employee_skills(problem: dict[str, Any]) -> dict[str, set[str]]:
    result = {}
    for employee in problem.get("employees", {}).get("competency", []):
        employee_id = str(employee.get("id", "")).strip()
        result[employee_id] = {
            str(team.get("code", "")).strip()
            for team in employee.get("teams", [])
            if team.get("code")
        }
    return result


def _min_rest_hours(problem: dict[str, Any]) -> float:
    for rule in problem.get("constraints", {}).get("hard", []):
        if rule.get("enabled", True) and rule.get("type") == "min_rest_hours":
            return float(rule.get("params", {}).get("hours", 11))
    return 11.0


def _parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":", 1)
    return int(hours) * 60 + int(minutes)


def _validate_demand_dates_and_periods(
    demand_rows: list[dict[str, str]],
    day_set: set[str],
    work_periods: dict[str, tuple[int, int]],
    employee_skills: dict[str, set[str]],
    issues: list[ValidationIssue],
) -> None:
    all_skills = set().union(*employee_skills.values()) if employee_skills else set()
    reported_unknown_periods = set()
    reported_skills = set()
    for row in demand_rows:
        row_date = row.get("date", "")
        period = row.get("workPeriod", "")
        skill = row.get("team", "")
        if row_date not in day_set:
            issues.append(ValidationIssue("DEMAND_DATE_OUTSIDE_TARGET", "error", "Demand date outside target period", f"Demand contains date {row_date}.", start_date=row_date))
        if period not in work_periods and period not in reported_unknown_periods:
            reported_unknown_periods.add(period)
            issues.append(ValidationIssue("UNKNOWN_WORK_PERIOD", "error", "Demand references unknown work period", f"Demand references work period {period}."))
        if skill and skill not in all_skills and skill not in reported_skills:
            reported_skills.add(skill)
            issues.append(ValidationIssue("NO_EMPLOYEE_WITH_SKILL", "warning", "No employee can cover demanded skill", f"Demand requires skill {skill}, but no employee has that skill. The solver can still remain feasible by using shortage variables.", suggested_fix="Add an employee with this skill or remove the demand row."))


def _validate_schedule_shape(
    header: list[str],
    rows: list[list[str]],
    days: list[str],
    employee_ids: set[str],
    issues: list[ValidationIssue],
) -> None:
    if not header:
        return

    # The solver V1 supports only "before" context columns. The schedule may
    # contain up to 5 contiguous dates immediately before targetPeriod.start,
    # followed by the target period itself. Those before dates are used as fixed
    # history for boundary constraints and are not produced in solver output.
    expected = ["employee_id", *_allowed_schedule_dates_with_before_context(header, days, issues)]
    if header != expected:
        issues.append(
            ValidationIssue(
                "SCHEDULE_DATES_MISMATCH",
                "error",
                "Schedule dates do not match supported target period",
                "schedule_input.csv header must contain the target period dates and may include up to 5 contiguous dates immediately before targetPeriod.start. Dates after targetPeriod.end are not supported yet.",
            )
        )
    schedule_ids = {row[0] for row in rows if row}
    if schedule_ids != employee_ids:
        issues.append(ValidationIssue("EMPLOYEE_MISMATCH", "error", "Employee mismatch", f"problem.json and schedule_input.csv employee IDs differ. Missing={sorted(employee_ids - schedule_ids)}, extra={sorted(schedule_ids - employee_ids)}"))
    bad = [row[0] for row in rows if len(row) != len(header)]
    if bad:
        issues.append(ValidationIssue("SCHEDULE_ROW_LENGTH", "error", "Schedule row length mismatch", f"Rows with wrong column count: {bad[:5]}"))


def _allowed_schedule_dates_with_before_context(
    header: list[str],
    days: list[str],
    issues: list[ValidationIssue],
    max_before_days: int = 5,
) -> list[str]:
    """Return the only date-header layout currently accepted by Sisqual V1.

    Accepted:
      employee_id, [up to 5 contiguous dates before target start], target dates

    Not accepted yet:
      dates after targetPeriod.end, non-contiguous history, or arbitrary
      historical dates. This keeps the pre-solve validator aligned with what the
      ILP/CSP solvers can actually consume.
    """

    if not days:
        return []
    if not header or header[0] != "employee_id":
        issues.append(ValidationIssue("SCHEDULE_HEADER", "error", "Invalid schedule header", "schedule_input.csv first column must be employee_id."))
        return days

    date_columns = header[1:]
    target_start = datetime.strptime(days[0], "%Y-%m-%d").date()

    # Build a set of valid date columns first. Invalid header values still get a
    # validation issue, but we do not let them participate in context detection.
    date_set = set()
    for column in date_columns:
        try:
            date_set.add(datetime.strptime(column, "%Y-%m-%d").date())
        except ValueError:
            issues.append(ValidationIssue("SCHEDULE_HEADER_DATE", "error", "Invalid schedule date header", f"{column} is not a valid YYYY-MM-DD date."))

    # Only contiguous dates immediately before the target start count as
    # supported before-context. If 2025-09-30 is missing, then 2025-09-29 cannot
    # be used because the max-consecutive-day window would have a gap.
    before = []
    current = target_start - timedelta(days=1)
    while len(before) < max_before_days and current in date_set:
        before.append(current.isoformat())
        current -= timedelta(days=1)
    return [*reversed(before), *days]


def _validate_schedule_markers(
    header: list[str],
    rows: list[list[str]],
    work_periods: dict[str, tuple[int, int]],
    issues: list[ValidationIssue],
) -> None:
    if not header or not work_periods:
        return
    min_start = min(start for start, _ in work_periods.values())
    max_end = max(end for _, end in work_periods.values())
    for row in rows:
        if len(row) != len(header):
            continue
        employee_id = row[0]
        for idx, marker in enumerate(row[1:], start=1):
            normalized = marker.strip().upper()
            if normalized in OFF_MARKERS or normalized.isdigit() or normalized == "A":
                continue
            if normalized.startswith("EQUALS:"):
                parsed = _parse_equals(marker)
                if parsed is None:
                    issues.append(ValidationIssue("INVALID_EQUALS_MARKER", "error", "Invalid exact shift marker", f"{marker} is not a valid EQUALS marker.", employee_id=employee_id, start_date=header[idx]))
                    continue
                start, end = parsed
                if start < min_start or end > max_end:
                    issues.append(ValidationIssue("EQUALS_OUTSIDE_WORK_PERIODS", "error", "Exact shift outside available slots", f"{marker} is outside configured work periods.", employee_id=employee_id, start_date=header[idx]))
                continue
            issues.append(ValidationIssue("UNSUPPORTED_MARKER", "error", "Unsupported schedule marker", f"Unsupported marker {marker}.", employee_id=employee_id, start_date=header[idx]))


def _validate_possible_coverage(
    demand_rows: list[dict[str, str]],
    header: list[str],
    rows: list[list[str]],
    employees: dict[str, dict[str, Any]],
    employee_skills: dict[str, set[str]],
    problem: dict[str, Any],
    issues: list[ValidationIssue],
) -> None:
    if not header or not rows:
        return
    schedule = {row[0]: dict(zip(header[1:], row[1:])) for row in rows if len(row) == len(header)}
    do_can_be_swapped = _preferred_days_off_swappable(problem)
    reported = set()
    for row in demand_rows:
        day = row.get("date", "")
        skill = row.get("team", "")
        try:
            minimum = int(row.get("minimum", "0") or 0)
        except ValueError:
            minimum = 0
        if minimum <= 0:
            continue
        possible = 0
        for employee_id in employees:
            if skill not in employee_skills.get(employee_id, set()):
                continue
            marker = schedule.get(employee_id, {}).get(day, "")
            normalized = marker.strip().upper()
            if normalized not in HARD_UNAVAILABLE_MARKERS and (normalized != "DO" or do_can_be_swapped):
                possible += 1
        key = (day, skill)
        if possible == 0 and key not in reported:
            reported.add(key)
            issues.append(ValidationIssue("ZERO_POSSIBLE_WORKERS", "warning", "Demand has zero possible workers", f"{day} requires {skill}, but all skilled workers are hard-unavailable. The solver can still remain feasible by using shortage variables.", start_date=day, suggested_fix="Add availability for a skilled worker or reduce/remove demand."))


def _preferred_days_off_swappable(problem: dict[str, Any]) -> bool:
    advanced = problem.get("constraints", {}).get("advanced", {})
    if advanced.get("dayOffSwapping", {}).get("enabled") is True:
        return True

    swappable_types = {
        "day_off_swap_penalty",
        "preferred_day_off",
        "preferred_day_off_work",
        "minimize_preferred_day_off_work",
        "objective4",
        "minimize_day_off_changes",
    }
    for constraint in problem.get("constraints", {}).get("soft", []):
        if not constraint.get("enabled", True):
            continue
        type_name = str(constraint.get("type") or constraint.get("id") or "").strip().lower()
        if type_name not in swappable_types:
            continue
        try:
            return float(constraint.get("weight", 0) or 0) > 0
        except (TypeError, ValueError):
            return False
    return False


def _validate_consecutive_and_weekly(
    header: list[str],
    rows: list[list[str]],
    max_consecutive: int,
    issues: list[ValidationIssue],
) -> None:
    if not header:
        return
    for row in rows:
        if len(row) != len(header):
            continue
        employee_id = row[0]
        streak = []
        for idx, marker in enumerate(row[1:], start=1):
            day = header[idx]
            if marker.strip().upper() not in OFF_MARKERS:
                streak.append(day)
            else:
                streak = []
            if len(streak) > max_consecutive:
                issues.append(ValidationIssue("MAX_CONSECUTIVE_WORKDAYS", "error", "Max consecutive workdays conflict", f"Employee {employee_id} is required to work more than {max_consecutive} consecutive days.", employee_id=employee_id, start_date=streak[0], end_date=streak[-1], suggested_fix="Add a DO/FDO/VAC/NOT/Med day in this period."))
                break

        week_groups = defaultdict(list)
        for idx, marker in enumerate(row[1:], start=1):
            day = datetime.strptime(header[idx], "%Y-%m-%d").date()
            week_start = day - timedelta(days=day.weekday())
            week_groups[week_start].append(marker)
        for week_start, markers in week_groups.items():
            required = sum(1 for marker in markers if marker.strip().upper() not in OFF_MARKERS)
            local_max = len(markers) if len(markers) <= max_consecutive else len(markers) - 1
            if required > local_max:
                start = week_start.isoformat()
                end = (week_start + timedelta(days=len(markers) - 1)).isoformat()
                issues.append(ValidationIssue("WEEKLY_WORKDAYS_CONFLICT", "error", "Weekly workdays conflict with max consecutive rule", f"Employee {employee_id} has {required} required workdays in week {start}.", employee_id=employee_id, start_date=start, end_date=end, suggested_fix="Add at least one off/unavailable marker in this generated week."))


def _validate_fixed_rest(
    header: list[str],
    schedule_by_employee: dict[str, list[str]],
    min_rest_hours: float,
    issues: list[ValidationIssue],
) -> None:
    if not header:
        return
    for employee_id, row in schedule_by_employee.items():
        if len(row) != len(header):
            continue
        for idx in range(1, len(header) - 1):
            today = _parse_equals(row[idx])
            tomorrow = _parse_equals(row[idx + 1])
            if today is None or tomorrow is None:
                continue
            rest = ((24 * 60 - today[1]) + tomorrow[0]) / 60.0
            if rest < min_rest_hours:
                issues.append(ValidationIssue("MIN_REST_FIXED_SHIFT_CONFLICT", "error", "Fixed shifts violate minimum rest", f"Fixed shifts leave only {rest:.1f}h rest, below {min_rest_hours:.1f}h.", employee_id=employee_id, start_date=header[idx], end_date=header[idx + 1], suggested_fix="Move one fixed EQUALS shift or mark one day unavailable/off."))


def _parse_equals(marker: str) -> tuple[int, int] | None:
    match = re.match(r"^\s*EQUALS:(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s*$", marker, re.IGNORECASE)
    if not match:
        return None
    return _parse_hhmm(match.group(1)), _parse_hhmm(match.group(2))

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
import math

"""
Shared compiler for fixed days-off rules.

The solvers consume compiled period targets (week/month -> day indices + exact OFF='0' count)
instead of raw JSON params so the calendar parsing and validation logic lives in one place.
"""


@dataclass
class PeriodTarget:
    label: str
    day_indices: list 
    target_off_days: int


@dataclass
class FixedDaysOffTargets:
    weekly: dict  
    monthly: dict  


def _as_date(value):
    if hasattr(value, "date"):
        return value.date()
    return value


def _require_zero_only_counting(params, rule_type):
    counting = (params or {}).get("dayOffCounting") or {}
    allowed_values = counting.get("countOnlyScheduleValues")
    if allowed_values is None:
        # Default to zero-only for these custom rules in current implementation.
        return
    if not isinstance(allowed_values, list) or allowed_values != ["0"]:
        raise ValueError(
            f"{rule_type} currently supports only dayOffCounting.countOnlyScheduleValues = ['0']"
        )


def _build_week_periods(dates, week_start="monday", apply_to_partial_weeks=True):
    if not dates:
        return []
    week_start = str(week_start or "monday").strip().lower()
    week_start_idx = 0 if week_start == "monday" else 6 if week_start == "sunday" else None
    if week_start_idx is None:
        raise ValueError("fixed_days_off_per_week.params.weekStart must be 'monday' or 'sunday'")

    # Group by the chosen week start date, then keep the original 1-based schedule day indices.
    buckets = defaultdict(list)
    for idx, dt_like in enumerate(dates, start=1):
        d = _as_date(dt_like)
        offset = (d.weekday() - week_start_idx) % 7
        period_start = d - timedelta(days=offset)
        buckets[period_start.isoformat()].append(idx)

    periods = []
    for label in sorted(buckets.keys()):
        day_indices = buckets[label]
        if not apply_to_partial_weeks and len(day_indices) != 7:
            continue
        periods.append((label, day_indices))
    return periods


def _build_month_periods(dates):
    buckets = defaultdict(list)
    for idx, dt_like in enumerate(dates, start=1):
        d = _as_date(dt_like)
        buckets[d.strftime("%Y-%m")].append(idx)
    return [(label, buckets[label]) for label in sorted(buckets.keys())]


def _normalize_count_mode(params, rule_type):
    count_mode = str((params or {}).get("countMode", "exact")).strip().lower()
    if count_mode != "exact":
        raise ValueError(f"{rule_type} currently supports only countMode='exact'")
    return count_mode


def _normalize_vacation_adjustment(params, rule_type):
    raw_mode = (params or {}).get("vacationAdjustment")
    if raw_mode is None:
        # Alias kept for backwards/forward compatibility if another producer uses this key.
        raw_mode = (params or {}).get("vacationHandling")
    # Default is prorated behavior so long vacations do not make exact period rules impossible.
    mode = str(raw_mode if raw_mode is not None else "prorate").strip().lower()
    if mode not in {"prorate", "strict"}:
        raise ValueError(
            f"{rule_type}.params.vacationAdjustment must be 'prorate' or 'strict'"
        )
    return mode


def _round_half_up(value):
    if value >= 0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


def effective_period_off_target(
    *,
    rule_params,
    base_target_off_days,
    period_total_days,
    available_non_vacation_days,
    rule_type,
):
    """
    Compute the effective OFF='0' target for a period.

    The caller controls which days are "counted" via `available_non_vacation_days`:
      - pass non-vacation days -> vacations excluded from OFF counting
      - pass full period length -> vacations counted as OFF

    Modes:
      - prorate (default): round(base_target * available_days / period_days), clamped to [0, available_days]
      - strict: keep base_target and fail if impossible after vacation filtering
    """
    base_target = _coerce_int(base_target_off_days, f"{rule_type}.target")
    total_days = _coerce_int(period_total_days, f"{rule_type}.period_total_days")
    available_days = _coerce_int(
        available_non_vacation_days,
        f"{rule_type}.available_non_vacation_days",
    )

    if base_target < 0:
        raise ValueError(f"{rule_type} target must be >= 0 (got {base_target})")
    if total_days < 0:
        raise ValueError(f"{rule_type} period_total_days must be >= 0 (got {total_days})")
    if available_days < 0:
        raise ValueError(
            f"{rule_type} available_non_vacation_days must be >= 0 (got {available_days})"
        )
    if total_days and available_days > total_days:
        raise ValueError(
            f"{rule_type} available_non_vacation_days ({available_days}) "
            f"cannot exceed period_total_days ({total_days})"
        )

    adjustment_mode = _normalize_vacation_adjustment(rule_params, rule_type)
    if adjustment_mode == "strict":
        # Strict semantics: configured target must fit within the days counted for this period.
        if base_target > available_days:
            raise ValueError(
                f"{rule_type} is impossible with vacationAdjustment='strict': "
                f"target_off_days={base_target}, available_non_vacation_days={available_days}"
            )
        return base_target

    if total_days == 0 or available_days == 0:
        return 0

    # Pro-rate to the schedulable slice of the period and clamp to a feasible integer target.
    prorated_target = _round_half_up(base_target * (available_days / float(total_days)))
    return max(0, min(available_days, prorated_target))


def _employee_id_map(employees, base_index=0):
    mapping = {}
    for idx, emp in enumerate(employees, start=base_index):
        if isinstance(emp, dict):
            emp_id = emp.get("id")
            if emp_id is not None:
                mapping[str(emp_id)] = idx
    return mapping


def _coerce_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid integer for {field_name}: {value!r}") from None


def _resolve_weekly_targets(params, emp_idx_by_id):
    # Backward-compatible format: explicit perEmployee mapping.
    per_employee = params.get("perEmployee")
    if per_employee is not None:
        if not isinstance(per_employee, dict):
            raise ValueError("fixed_days_off_per_week.params.perEmployee must be an object")
        targets = {}
        for emp_id, target in per_employee.items():
            solver_emp = emp_idx_by_id.get(str(emp_id))
            if solver_emp is None:
                continue
            targets[solver_emp] = _coerce_int(target, f"fixed_days_off_per_week.perEmployee[{emp_id}]")
        return targets

    # Compact format: one default for all employees + optional per-employee overrides.
    targets = {}
    default_target = params.get("default")
    if default_target is not None:
        default_target_int = _coerce_int(default_target, "fixed_days_off_per_week.default")
        for solver_emp in emp_idx_by_id.values():
            targets[solver_emp] = default_target_int

    overrides = params.get("overrides") or {}
    if not isinstance(overrides, dict):
        raise ValueError("fixed_days_off_per_week.params.overrides must be an object")
    for emp_id, target in overrides.items():
        solver_emp = emp_idx_by_id.get(str(emp_id))
        if solver_emp is None:
            continue
        targets[solver_emp] = _coerce_int(target, f"fixed_days_off_per_week.overrides[{emp_id}]")
    return targets


def _resolve_monthly_targets(params, emp_idx_by_id):
    # Backward-compatible format: explicit perEmployee -> {YYYY-MM: n}
    per_employee = params.get("perEmployee")
    if per_employee is not None:
        if not isinstance(per_employee, dict):
            raise ValueError("fixed_days_off_per_month.params.perEmployee must be an object")
        targets = {}
        for emp_id, per_month in per_employee.items():
            solver_emp = emp_idx_by_id.get(str(emp_id))
            if solver_emp is None:
                continue
            if not isinstance(per_month, dict):
                raise ValueError(
                    f"fixed_days_off_per_month.params.perEmployee[{emp_id}] must be an object keyed by YYYY-MM"
                )
            targets[solver_emp] = dict(per_month)
        return targets

    # Compact format: one month table shared by all employees + optional per-employee month overrides.
    targets = {}
    default_by_month = params.get("defaultByMonth") or {}
    if not isinstance(default_by_month, dict):
        raise ValueError("fixed_days_off_per_month.params.defaultByMonth must be an object")
    if default_by_month:
        for solver_emp in emp_idx_by_id.values():
            targets[solver_emp] = dict(default_by_month)

    overrides = params.get("overrides") or {}
    if not isinstance(overrides, dict):
        raise ValueError("fixed_days_off_per_month.params.overrides must be an object")
    for emp_id, per_month_override in overrides.items():
        solver_emp = emp_idx_by_id.get(str(emp_id))
        if solver_emp is None:
            continue
        if not isinstance(per_month_override, dict):
            raise ValueError(
                f"fixed_days_off_per_month.params.overrides[{emp_id}] must be an object keyed by YYYY-MM"
            )
        targets.setdefault(solver_emp, {})
        targets[solver_emp].update(per_month_override)
    return targets


def compile_fixed_days_off_targets(plan, employees, dates, employee_index_base=0):
    # Convert the problem-level rule config into solver-friendly targets keyed by solver employee index.
    weekly_targets = defaultdict(list)
    monthly_targets = defaultdict(list)
    emp_idx_by_id = _employee_id_map(employees, base_index=employee_index_base)

    weekly = getattr(plan, "fixed_days_off_per_week", None)
    if weekly:
        _normalize_count_mode(weekly, "fixed_days_off_per_week")
        _require_zero_only_counting(weekly, "fixed_days_off_per_week")
        week_start = weekly.get("weekStart", "monday")
        apply_partial = bool(weekly.get("applyToPartialWeeks", True))
        periods = _build_week_periods(dates, week_start=week_start, apply_to_partial_weeks=apply_partial)
        for solver_emp, target_off in _resolve_weekly_targets(weekly, emp_idx_by_id).items():
            for label, day_indices in periods:
                weekly_targets[solver_emp].append(
                    PeriodTarget(label=label, day_indices=list(day_indices), target_off_days=target_off)
                )

    monthly = getattr(plan, "fixed_days_off_per_month", None)
    if monthly:
        _normalize_count_mode(monthly, "fixed_days_off_per_month")
        _require_zero_only_counting(monthly, "fixed_days_off_per_month")
        periods = dict(_build_month_periods(dates))
        for solver_emp, per_month in _resolve_monthly_targets(monthly, emp_idx_by_id).items():
            for month_key, target in per_month.items():
                if month_key not in periods:
                    # Ignore out-of-horizon month entries (e.g., copied configs spanning another year).
                    continue
                target_off = _coerce_int(
                    target,
                    f"fixed_days_off_per_month month target[{solver_emp}][{month_key}]",
                )
                monthly_targets[solver_emp].append(
                    PeriodTarget(label=str(month_key), day_indices=list(periods[month_key]), target_off_days=target_off)
                )

    return FixedDaysOffTargets(weekly=dict(weekly_targets), monthly=dict(monthly_targets))

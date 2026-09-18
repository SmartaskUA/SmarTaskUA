import csv
import pandas as pd
import sys
import json
import holidays as hl
import os
import re
import math

def _normalize_rule_entries(rules):
    if rules is None:
        return []
    if isinstance(rules, dict):
        if "hard" in rules or "soft" in rules:
            entries = []
            for bucket in ("hard", "soft"):
                for rule in rules.get(bucket, []) or []:
                    if isinstance(rule, dict) and rule.get("enabled", True):
                        entries.append(rule)
            return entries
        if "rules" in rules:
            return [
                rule for rule in (rules.get("rules") or [])
                if isinstance(rule, dict) and rule.get("enabled", True)
            ]
        return []
    if isinstance(rules, list):
        return [rule for rule in rules if isinstance(rule, dict) and rule.get("enabled", True)]
    return []


def _extract_fixed_days_off_rule_params(rules):
    weekly = None
    monthly = None
    for rule in _normalize_rule_entries(rules):
        rule_type = str(rule.get("type") or rule.get("id") or "").strip()
        params = rule.get("params") or {}
        if not isinstance(params, dict):
            continue
        if rule_type == "fixed_days_off_per_week":
            weekly = params
        elif rule_type == "fixed_days_off_per_month":
            monthly = params
    return weekly, monthly


def _supports_exact_zero_only(params):
    if params is None:
        return False
    count_mode = str(params.get("countMode", "exact")).strip().lower()
    if count_mode != "exact":
        return False
    counting = params.get("dayOffCounting") or {}
    values = counting.get("countOnlyScheduleValues")
    return values is None or values == ["0"]


def _normalize_vacation_adjustment(params):
    raw_mode = (params or {}).get("vacationAdjustment")
    if raw_mode is None:
        raw_mode = (params or {}).get("vacationHandling")
    mode = str(raw_mode if raw_mode is not None else "prorate").strip().lower()
    if mode not in {"prorate", "strict"}:
        return None
    return mode


def _supports_fixed_days_off_rule(params):
    if not _supports_exact_zero_only(params):
        return False
    return _normalize_vacation_adjustment(params) is not None


def _normalize_employee_ref(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    match = re.search(r"(\d+)\s*$", text)
    if match:
        return match.group(1)
    return text


def _to_int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_weekly_targets(params, employee_keys):
    per_employee = params.get("perEmployee")
    if isinstance(per_employee, dict):
        out = {}
        for emp_id, target in per_employee.items():
            key = _normalize_employee_ref(emp_id)
            if key in employee_keys:
                target_int = _to_int_or_none(target)
                if target_int is not None:
                    out[key] = target_int
        return out

    out = {}
    default_target = _to_int_or_none(params.get("default"))
    if default_target is not None:
        for key in employee_keys:
            out[key] = default_target
    overrides = params.get("overrides") or {}
    if isinstance(overrides, dict):
        for emp_id, target in overrides.items():
            key = _normalize_employee_ref(emp_id)
            if key in employee_keys:
                target_int = _to_int_or_none(target)
                if target_int is not None:
                    out[key] = target_int
    return out


def _resolve_monthly_targets(params, employee_keys):
    per_employee = params.get("perEmployee")
    if isinstance(per_employee, dict):
        out = {}
        for emp_id, month_map in per_employee.items():
            key = _normalize_employee_ref(emp_id)
            if key not in employee_keys or not isinstance(month_map, dict):
                continue
            parsed = {}
            for month_key, target in month_map.items():
                target_int = _to_int_or_none(target)
                if target_int is not None:
                    parsed[str(month_key)] = target_int
            out[key] = parsed
        return out

    out = {}
    default_by_month = params.get("defaultByMonth") or {}
    if isinstance(default_by_month, dict):
        parsed_defaults = {}
        for month_key, target in default_by_month.items():
            target_int = _to_int_or_none(target)
            if target_int is not None:
                parsed_defaults[str(month_key)] = target_int
        if parsed_defaults:
            for key in employee_keys:
                out[key] = dict(parsed_defaults)

    overrides = params.get("overrides") or {}
    if isinstance(overrides, dict):
        for emp_id, month_map in overrides.items():
            key = _normalize_employee_ref(emp_id)
            if key not in employee_keys or not isinstance(month_map, dict):
                continue
            out.setdefault(key, {})
            for month_key, target in month_map.items():
                target_int = _to_int_or_none(target)
                if target_int is not None:
                    out[key][str(month_key)] = target_int
    return out


def _is_off_zero(value):
    text = str(value).strip()
    return text == "0" or text == "0.0"


def _is_vacation(value):
    return str(value).strip().upper() == "F"


def _round_half_up(value):
    if value >= 0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


def _effective_period_target(rule_params, base_target_off_days, period_total_days, available_non_vacation_days):
    """
    Mirror solver semantics for vacation-aware fixed days-off rules.

    - strict: keep configured target even if vacations make it impossible.
    - prorate (default): scale target by available non-vacation days in the period.
    """
    base_target = _to_int_or_none(base_target_off_days)
    total_days = _to_int_or_none(period_total_days)
    available_days = _to_int_or_none(available_non_vacation_days)
    if base_target is None or total_days is None or available_days is None:
        return None
    if base_target < 0 or total_days < 0 or available_days < 0:
        return None
    if total_days and available_days > total_days:
        return None

    adjustment_mode = _normalize_vacation_adjustment(rule_params)
    if adjustment_mode is None:
        return None
    if adjustment_mode == "strict":
        return base_target

    if total_days == 0 or available_days == 0:
        return 0
    prorated_target = _round_half_up(base_target * (available_days / float(total_days)))
    return max(0, min(available_days, prorated_target))


def _build_week_periods(day_entries, week_start="monday", apply_to_partial_weeks=True):
    if not day_entries:
        return []
    week_start = str(week_start or "monday").strip().lower()
    if week_start == "monday":
        week_start_idx = 0
    elif week_start == "sunday":
        week_start_idx = 6
    else:
        return []

    buckets = {}
    for day_num, col_name, current_date in day_entries:
        offset = (current_date.weekday() - week_start_idx) % 7
        period_start = (current_date - pd.Timedelta(days=offset)).date().isoformat()
        buckets.setdefault(period_start, []).append((day_num, col_name, current_date))

    periods = []
    for label in sorted(buckets.keys()):
        entries = buckets[label]
        if not apply_to_partial_weeks and len(entries) != 7:
            continue
        periods.append((label, entries))
    return periods


def _compute_fixed_days_off_violations(df, year, rules):
    weekly_rule, monthly_rule = _extract_fixed_days_off_rule_params(rules)
    weekly_supported = _supports_fixed_days_off_rule(weekly_rule)
    monthly_supported = _supports_fixed_days_off_rule(monthly_rule)
    if not weekly_supported and not monthly_supported:
        return None

    day_entries = []
    for col in df.columns:
        match = re.match(r"^Dia\s+(\d+)$", str(col))
        if not match:
            continue
        day_num = int(match.group(1))
        current_date = (pd.Timestamp(f"{int(year)}-01-01") + pd.Timedelta(days=day_num - 1)).to_pydatetime()
        day_entries.append((day_num, col, current_date))
    day_entries.sort(key=lambda x: x[0])
    if not day_entries or "funcionario" not in df.columns:
        return None

    row_emp_keys = {}
    employee_keys = set()
    for row_idx, row in df.iterrows():
        key = _normalize_employee_ref(row.get("funcionario"))
        if key is None:
            continue
        row_emp_keys[row_idx] = key
        employee_keys.add(key)

    violations = 0

    if weekly_supported:
        week_start = weekly_rule.get("weekStart", "monday")
        apply_partial = bool(weekly_rule.get("applyToPartialWeeks", True))
        weekly_targets = _resolve_weekly_targets(weekly_rule, employee_keys)
        weekly_periods = _build_week_periods(
            day_entries,
            week_start=week_start,
            apply_to_partial_weeks=apply_partial,
        )
        for row_idx, row in df.iterrows():
            emp_key = row_emp_keys.get(row_idx)
            if emp_key not in weekly_targets:
                continue
            base_target = weekly_targets[emp_key]
            for _, entries in weekly_periods:
                available_entries = [entry for entry in entries if not _is_vacation(row[entry[1]])]
                target = _effective_period_target(
                    weekly_rule,
                    base_target,
                    period_total_days=len(entries),
                    available_non_vacation_days=len(available_entries),
                )
                if target is None:
                    continue
                actual = sum(1 for _, col_name, _ in available_entries if _is_off_zero(row[col_name]))
                if actual != target:
                    violations += 1

    if monthly_supported:
        monthly_targets = _resolve_monthly_targets(monthly_rule, employee_keys)
        month_periods = {}
        for day_num, col_name, current_date in day_entries:
            month_periods.setdefault(current_date.strftime("%Y-%m"), []).append(
                (day_num, col_name, current_date)
            )
        for row_idx, row in df.iterrows():
            emp_key = row_emp_keys.get(row_idx)
            if emp_key not in monthly_targets:
                continue
            for month_key, base_target in monthly_targets[emp_key].items():
                entries = month_periods.get(str(month_key))
                if not entries:
                    continue
                available_entries = [entry for entry in entries if not _is_vacation(row[entry[1]])]
                target = _effective_period_target(
                    monthly_rule,
                    base_target,
                    period_total_days=len(entries),
                    available_non_vacation_days=len(available_entries),
                )
                if target is None:
                    continue
                actual = sum(1 for _, col_name, _ in available_entries if _is_off_zero(row[col_name]))
                if actual != target:
                    violations += 1

    return violations


def analyze(file, holidays, mins, employees, year=2025, rules=None):
    print(f"Analyzing file: {file}")
    df = pd.read_csv(file, encoding='ISO-8859-1')

    # --- helpers -------------------------------------------------------------
    def parse_shift(val):
        """Return (prefix, team) if val matches 'M_X'/'T_X'/'N_X', else (None, None)."""
        if not isinstance(val, str):
            return (None, None)
        m = re.match(r'^\s*([MTN])\s*[_-]\s*([A-Za-z])\s*$', val)
        if m:
            return (m.group(1), m.group(2).upper())
        return (None, None)

    def is_work_shift(val):
        p, _ = parse_shift(val)
        return p in {'M', 'T', 'N'}

    # ------------------------------------------------------------------------

    missed_work_days = 0
    missed_vacation_days = 0
    missed_team_min = 0
    workHolidays = 0
    consecutiveDays = 0
    total_tm_fails = 0
    single_team_violations = 0
    team_satisfaction_values = []    # % of total shifts worked in the preferred (first) team
    per_employee_shift_balance = []  # min(M%, T%) per employee

    print(f"Year: {year}")
    print(f"Holidays: {holidays}")
    print(f"Minimuns: {mins}")
    print(f"Employees: {employees}")

    mins, ideals = parse_requirements(mins)
    teams = parse_employees(employees)

    # Sundays of the given year (day-of-year numbers)
    sunday = []
    for day in pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31'):
        if day.weekday() == 6:
            sunday.append(day.dayofyear)

    dia_cols = [col for col in df.columns if col.startswith("Dia ")]
    all_special_cols = [f'Dia {d}' for d in set(holidays).union(sunday) if f'Dia {d}' in df.columns]

    # order of shifts during a day for TM fail detection
    shift_order = {'M': 1, 'T': 2, 'N': 3}

    for _, row in df.iterrows():
        # Work/vacation counting (generic)
        worked_days  = sum(is_work_shift(row[col]) for col in dia_cols)
        vacation_days = sum(str(row[col]).strip() == 'F' for col in dia_cols)

        missed_work_days += abs(223 - worked_days)
        missed_vacation_days += abs(30 - vacation_days)

        # Worked holidays/sundays (generic)
        total_worked_holidays = sum(is_work_shift(row[col]) for col in all_special_cols)
        if total_worked_holidays > 22:
            workHolidays += total_worked_holidays - 22

        # 6+ consecutive days worked
        work_sequence = [1 if is_work_shift(row[col]) else 0 for col in dia_cols]
        streak = 0
        fails = 0
        for day in work_sequence:
            if day == 1:
                streak += 1
                if streak >= 6:
                    fails += 1
            else:
                streak = 0
        consecutiveDays += fails

        # Tomorrow earlier than today (TM fails) — compare by M<T<N
        tm_fails = 0
        for i in range(len(dia_cols) - 1):
            p_today, _ = parse_shift(row[dia_cols[i]])
            p_tomorrow, _ = parse_shift(row[dia_cols[i + 1]])
            if p_today in shift_order and p_tomorrow in shift_order:
                if shift_order[p_tomorrow] < shift_order[p_today]:
                    tm_fails += 1
        total_tm_fails += tm_fails

        # Allowed teams for employee
        emp_id = row['funcionario']
        allowed_codes = teams.get(emp_id, [])  # e.g. ["A"], ["A","B"], ["B","C","D"], ...

        # Count assignments per team actually present in the row
        team_counts = {}
        for col in dia_cols:
            pfx, code = parse_shift(row[col])
            if pfx and code:
                team_counts[code] = team_counts.get(code, 0) + 1

        # Single-team violation: employee allowed only 1 code but worked others
        if len(allowed_codes) == 1:
            allowed = set(allowed_codes)
            worked_codes = set(team_counts.keys())
            other_work = worked_codes - allowed
            if other_work:
                single_team_violations += 1

        # Legacy metric: when exactly 2 allowed teams, compute % on the first team
        if len(allowed_codes) >= 1:
            total_worked = sum(team_counts.get(code, 0) for code in allowed_codes)
            if total_worked > 0:
                preferred = allowed_codes[0]
                preferred_count = team_counts.get(preferred, 0)
                satisfaction_pct = round((preferred_count / total_worked) * 100.0, 2)
                team_satisfaction_values.append(satisfaction_pct)

        # ✅ FIX: Per-employee shift balance calculation moved INSIDE the loop
        # Previously this block was outside the for loop and only ran for the
        # last employee, making the result incorrect.
        emp_morning   = sum(1 for col in dia_cols if parse_shift(row[col])[0] == 'M')
        emp_afternoon = sum(1 for col in dia_cols if parse_shift(row[col])[0] == 'T')
        emp_night     = sum(1 for col in dia_cols if parse_shift(row[col])[0] == 'N')

        total_emp_shifts_all = emp_morning + emp_afternoon + emp_night
        if total_emp_shifts_all > 0:
            morning_pct_all   = (emp_morning  / total_emp_shifts_all) * 100.0
            afternoon_pct_all = (emp_afternoon / total_emp_shifts_all) * 100.0
            night_pct_all     = (emp_night    / total_emp_shifts_all) * 100.0

            # Only consider shifts the employee actually worked (non-zero).
            pcts = [p for p in [morning_pct_all, afternoon_pct_all, night_pct_all] if p > 0]
            active_shifts = len(pcts)

            if active_shifts >= 2:
                min_pct = min(pcts)
                ideal_min = 100.0 / active_shifts
                scale = 50.0 / ideal_min
                balanced_score = min(50.0, min_pct * scale)
            else:
                balanced_score = 0.0

            per_employee_shift_balance.append(balanced_score)

    # end of employee loop

    if team_satisfaction_values:
        team_satisfaction = round(sum(team_satisfaction_values) / len(team_satisfaction_values), 2)
    else:
        team_satisfaction = 0

    print(per_employee_shift_balance)
    shift_balance = round(min(per_employee_shift_balance), 2) if per_employee_shift_balance else 0

    def givenShift(team_label, shift):
        if shift == 1:
            prefix = "M"
        elif shift == 2:
            prefix = "T"
        elif shift == 3:
            prefix = "N"
        else:
            return None  # unknown shift; skip
        return f"{prefix}_{team_label}"

    # Minimums compliance (generic for any team code)
    for (day, team_label, shift), required in mins.items():
        col = f"Dia {day}"
        if col not in df.columns:
            continue
        code = givenShift(team_label, shift)
        if not code:
            continue
        assigned = sum(str(v).strip().upper() == code for v in df[col])
        missing = max(0, required - assigned)
        missed_team_min += int(missing)


    # Ideals compliance (generic for any team code)
    missed_team_ideal = 0
    for (day, team_label, shift), target in ideals.items():
        col = f"Dia {day}"
        if col not in df.columns:
            continue
        code = givenShift(team_label, shift)
        if not code:
            continue
        assigned = sum(str(v).strip().upper() == code for v in df[col])
        missing = max(0, target - assigned)
        missed_team_ideal += int(missing)


    result = {
        "missedWorkDays": missed_work_days,
        "missedVacationDays": missed_vacation_days,
        "workHolidays": workHolidays,
        "tmFails": total_tm_fails,
        "consecutiveDays": consecutiveDays,
        "singleTeamViolations": single_team_violations,
        "missedTeamMin": missed_team_min,
        "missedTeamIdeal": missed_team_ideal,
        "shiftBalance": shift_balance,
        "teamSatisfactionLevel": team_satisfaction
    }

    # Optional KPI for fixed folga rules.
    # Uses the same vacation-aware target semantics as the solvers:
    # strict target or prorated target (default) when vacation days reduce period size.
    fixed_days_off_violations = _compute_fixed_days_off_violations(df, year, rules)
    if fixed_days_off_violations is not None:
        result["fixedDaysOffViolations"] = fixed_days_off_violations

    return result

def parse_requirements(requirements_text):
    """
    Parses both Minimo and Ideal rows from the requirements CSV text.
    Returns:
        mins  -> dict[(day:int, team_code:str, shift:int) -> int]
        ideals -> dict[(day:int, team_code:str, shift:int) -> int]
    """
    mins, ideals = {}, {}
    shift_map = {"M": 1, "T": 2, "N": 3}

    # Guard: if requirements_text is None or not a string, return empty dicts.
    if not requirements_text or not isinstance(requirements_text, str):
        print(f"[parse_requirements] WARNING: received non-string input "
              f"(type={type(requirements_text).__name__}). "
              f"missedTeamMin and missedTeamIdeal will be 0.")
        return mins, ideals

    requirements_text = requirements_text.replace('\r\n', '\n').replace('\r', '\n').strip()
    lines = requirements_text.split('\n')

    if len(lines) == 1 and ',' in lines[0]:
        parts = lines[0].split(',')
        if len(parts) >= 368:
            lines = [','.join(parts[i:i+368]) for i in range(0, len(parts), 368)]

    for line_num, line in enumerate(lines, 1):
        parts = line.strip().split(',')
        if len(parts) < 4:
            continue

        team_label_raw, req_type, shift_code = parts[0].strip(), parts[1].strip(), parts[2].strip().upper()
        shift_num = shift_map.get(shift_code)
        if not shift_num:
            continue

        team_code = team_label_raw.strip()[-1].upper()
        values = parts[3:]
        target = mins if req_type.lower() == "minimo" else ideals

        for day, value in enumerate(values[:365], 1):
            v = value.strip()
            if v:
                try:
                    target[(day, team_code, shift_num)] = int(v)
                except ValueError:
                    pass
    return mins, ideals


def parse_employees(employees):
    """
    Returns dict[int -> list[str team_codes]]
    Example: { 5: ["A","B"], 7: ["C"] }
    """
    teams = {}
    if isinstance(employees, str):
        employees = json.loads(employees)

    for emp in employees:
        emp_name = emp["name"]
        emp_id = int(emp_name.split(' ')[1])

        codes = []
        for t in emp.get("teams", []):
            t = str(t).strip()
            if not t:
                continue
            codes.append(t[-1].upper())  # 'Equipa X' -> 'X'
        # de-dup while preserving order
        seen = set()
        codes = [c for c in codes if not (c in seen or seen.add(c))]
        teams[emp_id] = codes
    return teams


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python kpiVerification.py <file>")
        sys.exit(1)
    ano = 2026
    holidays = hl.country_holidays("PT", years=[ano])
    dias_ano = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31').to_list()
    start_date = dias_ano[0].date()
    holidays = {(d - start_date).days + 1 for d in holidays}
    file = sys.argv[1]
    teams = {
        1: [1], 2: [1], 3: [1], 4: [1],
        5: [1, 2], 6: [1, 2], 7: [1], 8: [1],
        9: [1], 10: [2], 11: [2, 1], 12: [2]
    }
    data = analyze(file=file, holidays=holidays, mins=minimums_text, employees=employees_json, year=ano)
    print(json.dumps(data, indent=4))
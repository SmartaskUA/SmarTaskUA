def _normalize_constraints(constraints):
    hard = []
    soft = []

    if constraints is None:
        return hard, soft

    if isinstance(constraints, dict):
        if "hard" in constraints or "soft" in constraints:
            for c in constraints.get("hard", []):
                if c and c.get("enabled", True):
                    hard.append(c)
            for c in constraints.get("soft", []):
                if c and c.get("enabled", True):
                    soft.append(c)
        elif "rules" in constraints:
            for r in constraints.get("rules", []):
                if not r or r.get("enabled", True) is False:
                    continue
                kind = str(r.get("kind", "hard")).lower()
                if kind == "soft":
                    soft.append(r)
                else:
                    hard.append(r)
    elif isinstance(constraints, list):
        for r in constraints:
            if not r or r.get("enabled", True) is False:
                continue
            kind = str(r.get("kind", "hard")).lower()
            if kind == "soft":
                soft.append(r)
            else:
                hard.append(r)

    return hard, soft


def _find_constraint(hard, soft, type_name):
    for c in hard:
        if c.get("type") == type_name:
            return c, "hard"
    for c in soft:
        if c.get("type") == type_name:
            return c, "soft"
    return None, None


def _penalty_from_constraint(c, default_value):
    if not c:
        return default_value
    params = c.get("params") or {}
    if c.get("weight") is not None:
        return int(c.get("weight"))
    if "penalty_per_missing" in params:
        return int(params.get("penalty_per_missing"))
    return default_value


def parse_constraints(constraints):
    """
    Normalize constraints from either problem.json (hard/soft arrays) or legacy
    rules format (rules list), and return a config dict for solvers.
    """
    default_cfg = {
        "provided": False,
        "max_consecutive_window": 6,
        "max_consecutive_worked": 5,
        "special_cap": 22,
        "total_workdays_min": 223,
        "total_workdays_max": 223,
        "enforce_no_earlier": True,
        "enforce_vacation": True,
        "min_coverage_weight": 100,
        "min_coverage_hard": False,
        "ideal_coverage_weight": 1,
        "ideal_coverage_hard": False,
    }

    if constraints is None:
        return default_cfg

    hard, soft = _normalize_constraints(constraints)
    cfg = {
        "provided": True,
        "max_consecutive_window": None,
        "max_consecutive_worked": None,
        "special_cap": None,
        "total_workdays_min": None,
        "total_workdays_max": None,
        "enforce_no_earlier": False,
        "enforce_vacation": False,
        "min_coverage_weight": 0,
        "min_coverage_hard": False,
        "ideal_coverage_weight": 0,
        "ideal_coverage_hard": False,
    }

    max_consec, max_consec_kind = _find_constraint(hard, soft, "max_consecutive_days")
    if max_consec and max_consec_kind == "hard":
        params = max_consec.get("params") or {}
        cfg["max_consecutive_window"] = int(params.get("window", 6))
        cfg["max_consecutive_worked"] = int(params.get("max_worked", 5))

    max_special, max_special_kind = _find_constraint(hard, soft, "max_special_days")
    if max_special and max_special_kind == "hard":
        params = max_special.get("params") or {}
        cfg["special_cap"] = int(params.get("cap", 22))

    total_workdays, total_workdays_kind = _find_constraint(hard, soft, "total_workdays")
    if total_workdays and total_workdays_kind == "hard":
        params = total_workdays.get("params") or {}
        min_days = params.get("min")
        max_days = params.get("max")
        cfg["total_workdays_min"] = int(min_days) if min_days is not None else None
        cfg["total_workdays_max"] = int(max_days) if max_days is not None else None

    no_earlier, no_earlier_kind = _find_constraint(hard, soft, "no_earlier_shift_next_day")
    if no_earlier and no_earlier_kind == "hard":
        cfg["enforce_no_earlier"] = True

    vacation, vacation_kind = _find_constraint(hard, soft, "vacation_block")
    if vacation and vacation_kind == "hard":
        cfg["enforce_vacation"] = True

    min_cov, min_cov_kind = _find_constraint(hard, soft, "min_coverage")
    if min_cov:
        cfg["min_coverage_weight"] = _penalty_from_constraint(min_cov, 100)
        cfg["min_coverage_hard"] = min_cov_kind == "hard"

    ideal_cov, ideal_cov_kind = _find_constraint(hard, soft, "ideal_coverage")
    if ideal_cov:
        cfg["ideal_coverage_weight"] = _penalty_from_constraint(ideal_cov, 1)
        cfg["ideal_coverage_hard"] = ideal_cov_kind == "hard"

    return cfg

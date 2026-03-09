from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ConstraintIR:
    type: str
    kind: str
    params: dict
    weight: Optional[int] = None
    raw: dict = field(default_factory=dict)


@dataclass
class ConstraintPlan:
    provided: bool
    max_consecutive_window: Optional[int]
    max_consecutive_worked: Optional[int]
    special_cap: Optional[int]
    total_workdays_min: Optional[int]
    total_workdays_max: Optional[int]
    enforce_no_earlier: bool
    enforce_vacation: bool
    min_coverage_weight: int
    min_coverage_hard: bool
    ideal_coverage_weight: int
    ideal_coverage_hard: bool
    # Raw params are kept here; solvers compile them into calendar periods separately.
    fixed_days_off_per_week: Optional[dict]
    fixed_days_off_per_month: Optional[dict]
    unknown: List[ConstraintIR] = field(default_factory=list)


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


def _safe_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _penalty_from_constraint(ir, default_value):
    if ir is None:
        return default_value
    params = ir.params or {}
    if ir.weight is not None:
        return _safe_int(ir.weight, default_value)
    if "penalty_per_missing" in params:
        return _safe_int(params.get("penalty_per_missing"), default_value)
    return default_value


def _default_plan():
    return ConstraintPlan(
        provided=False,
        max_consecutive_window=6,
        max_consecutive_worked=5,
        special_cap=22,
        total_workdays_min=223,
        total_workdays_max=223,
        enforce_no_earlier=True,
        enforce_vacation=True,
        min_coverage_weight=100,
        min_coverage_hard=False,
        ideal_coverage_weight=1,
        ideal_coverage_hard=False,
        fixed_days_off_per_week=None,
        fixed_days_off_per_month=None,
        unknown=[],
    )


def _empty_plan():
    return ConstraintPlan(
        provided=True,
        max_consecutive_window=None,
        max_consecutive_worked=None,
        special_cap=None,
        total_workdays_min=None,
        total_workdays_max=None,
        enforce_no_earlier=False,
        enforce_vacation=False,
        min_coverage_weight=0,
        min_coverage_hard=False,
        ideal_coverage_weight=0,
        ideal_coverage_hard=False,
        fixed_days_off_per_week=None,
        fixed_days_off_per_month=None,
        unknown=[],
    )


def parse_constraints_ir(constraints):
    """
    Convert constraints into a solver-agnostic IR list.
    """
    if constraints is None:
        return []

    hard, soft = _normalize_constraints(constraints)
    ir_list = []
    for entry in hard:
        ir_list.append(_to_ir(entry, "hard"))
    for entry in soft:
        ir_list.append(_to_ir(entry, "soft"))
    return [ir for ir in ir_list if ir.type]


def _to_ir(entry, kind):
    if not entry:
        return ConstraintIR(type="", kind=kind, params={}, weight=None, raw={})
    type_name = entry.get("type") or entry.get("id") or ""
    return ConstraintIR(
        type=str(type_name),
        kind=kind,
        params=entry.get("params") or {},
        weight=entry.get("weight"),
        raw=entry,
    )


def build_constraint_plan(constraints):
    """
    Build a plan from IR. Unknown rules are preserved in plan.unknown.
    """
    if constraints is None:
        return _default_plan()

    plan = _empty_plan()
    ir_list = parse_constraints_ir(constraints)
    if not ir_list:
        return plan

    for ir in ir_list:
        if ir.type == "max_consecutive_days" and ir.kind == "hard":
            plan.max_consecutive_window = _safe_int(ir.params.get("window", 6), 6)
            plan.max_consecutive_worked = _safe_int(ir.params.get("max_worked", 5), 5)
        elif ir.type == "max_special_days" and ir.kind == "hard":
            plan.special_cap = _safe_int(ir.params.get("cap", 22), 22)
        elif ir.type == "total_workdays" and ir.kind == "hard":
            min_days = ir.params.get("min")
            max_days = ir.params.get("max")
            plan.total_workdays_min = _safe_int(min_days, None) if min_days is not None else None
            plan.total_workdays_max = _safe_int(max_days, None) if max_days is not None else None
        elif ir.type == "no_earlier_shift_next_day" and ir.kind == "hard":
            plan.enforce_no_earlier = True
        elif ir.type == "vacation_block" and ir.kind == "hard":
            plan.enforce_vacation = True
        elif ir.type == "min_coverage":
            plan.min_coverage_weight = _penalty_from_constraint(ir, 100)
            plan.min_coverage_hard = ir.kind == "hard"
        elif ir.type == "ideal_coverage":
            plan.ideal_coverage_weight = _penalty_from_constraint(ir, 1)
            plan.ideal_coverage_hard = ir.kind == "hard"
        elif ir.type == "fixed_days_off_per_week" and ir.kind == "hard":
            # Stored as raw params so all solvers can compile against their own calendar/indexing.
            plan.fixed_days_off_per_week = dict(ir.params or {})
        elif ir.type == "fixed_days_off_per_month" and ir.kind == "hard":
            plan.fixed_days_off_per_month = dict(ir.params or {})
        else:
            plan.unknown.append(ir)

    return plan


def parse_constraints(constraints):
    """
    Backwards-compatible entrypoint: return a ConstraintPlan instead of a dict.
    """
    return build_constraint_plan(constraints)

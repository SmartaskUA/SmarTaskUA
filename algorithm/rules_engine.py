# algorithm/rules_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Set, Optional, Callable


@dataclass
class Rule:
    id: str
    type: str
    kind: str          # "hard" | "soft"
    description: str
    scope: str
    params: Dict[str, Any]

CPSatHandler   = Callable[[Rule, "CPSatContext"], None]
GreedyCheckFn  = Callable[[Rule, "GreedyContext"], None]  


class RuleEngine:
    """
    General engine that can serve both backends.

    - CP-SAT: register CP handlers and call apply_cp_sat(ctx)
    - Greedy/HC: use greedy_is_feasible(...) and greedy_min_coverage_score(...)
                 (and/or register greedy rule hooks if you want)
    """
    def __init__(
        self,
        rules_config: Dict[str, Any],
        *,
        num_days: int,
        shifts: int,
        employees: List[int],               # 1-based ids
        teams_map: Dict[int, List[int]],    # emp_id -> [team_ids]
        vacations_1based: Dict[int, List[int]],
        special_days_1based: Set[int],
        target_workdays: int = 223,
    ):
        self.rules: List[Rule] = [Rule(**r) for r in rules_config.get("rules", [])]
        self.num_days  = int(num_days)
        self.shifts    = int(shifts)
        self.employees = employees
        self.teams_map = teams_map
        self.vac_1b    = vacations_1based
        self.special   = set(special_days_1based)
        self.target_workdays = int(target_workdays)

        # Feature flags 
        self.has_vac_block       = any(r.type == "vacation_block" for r in self.rules)
        self.has_team_elig       = any(r.type == "team_eligibility" for r in self.rules)
        self.has_max_consec      = any(r.type == "max_consecutive_days" for r in self.rules)
        self.has_special_cap     = any(r.type == "max_special_days" for r in self.rules)
        self.has_no_earlier_next = any(r.type == "no_earlier_shift_next_day" for r in self.rules)
        self.has_max_total       = any(r.type == "max_total_workdays" for r in self.rules)
        self.has_min_total       = any(r.type == "min_total_workdays" for r in self.rules)
        self.soft_min_cov        = next((r for r in self.rules if r.type == "min_coverage" and r.kind == "soft"), None)

        # Common params
        self.window        = next((int(r.params.get("window", 6)) for r in self.rules if r.type == "max_consecutive_days"), 6)
        self.max_in_window = next((int(r.params.get("max_worked", 5)) for r in self.rules if r.type == "max_consecutive_days"), 5)
        self.special_cap_v = next((int(r.params.get("cap", 22)) for r in self.rules if r.type == "max_special_days"), 22)
        self.max_total_v   = next((int(r.params.get("max", 223)) for r in self.rules if r.type == "max_total_workdays"), 223)
        self.min_total_v   = next((int(r.params.get("min", 223)) for r in self.rules if r.type == "min_total_workdays"), 223)
        self.penalty_missing = int(self.soft_min_cov.params.get("penalty_per_missing", 1000)) if self.soft_min_cov else 1000

        # Registries
        self._cpsat_handlers: Dict[str, CPSatHandler] = {}   
        self._greedy_hooks:   Dict[str, GreedyCheckFn] = {}  

    def register_cpsat(self, rule_type: str, handler: CPSatHandler):
        self._cpsat_handlers[rule_type] = handler

    def register_greedy(self, rule_type: str, hook: GreedyCheckFn):
        self._greedy_hooks[rule_type] = hook

    def apply_cp_sat(self, ctx: "CPSatContext") -> "CPSatContext":
        for r in self.rules:
            h = self._cpsat_handlers.get(r.type)
            if h:
                h(r, ctx)
        return ctx

    def greedy_is_feasible(
        self,
        p: int, d: int, s: int, t: int,
        assignment: Dict[int, List[Tuple[int,int,int]]],
        *,
        num_days: Optional[int] = None
    ) -> bool:
        """
        Mirrors your previous greedy feasibility, but driven by rules flags/params.
        """
        n_days = num_days or self.num_days
        emp_assign = assignment.get(p, [])

        # team eligibility
        if self.has_team_elig and t not in set(self.teams_map.get(p, [])):
            return False

        # vacations
        if self.has_vac_block and d in set(self.vac_1b.get(p, [])):
            return False

        # max total workdays (cap)
        if self.has_max_total:
            days = sorted({day for (day, _s, _t) in emp_assign})
            already = len(days)
            if d not in days and already + 1 > self.max_total_v:
                return False

        # max consecutive window
        if self.has_max_consec:
            days = sorted({day for (day, _s, _t) in emp_assign} | {d})
            # 1-based numpy vector for sliding sums
            arr = [0] * (n_days + 1)
            for dx in days:
                arr[dx] = 1
            # sliding window
            for i in range(1, n_days - self.window + 2):
                if sum(arr[i:i+self.window]) > self.max_in_window:
                    return False

        # special days cap
        if self.has_special_cap:
            cnt = sum(1 for (dx, _s, _t) in emp_assign if dx in self.special)
            if (d in self.special) and all(existing_d != d for (existing_d, _, _) in emp_assign):
                cnt += 1
            if cnt > self.special_cap_v:
                return False

        # forbid earlier shift than previous/next (M<T<N)
        if self.has_no_earlier_next:
            s_prev = next((ss for (dx, ss, _t2) in emp_assign if dx == d - 1), None)
            s_next = next((ss for (dx, ss, _t2) in emp_assign if dx == d + 1), None)
            if s_prev is not None and s < s_prev:
                return False
            if s_next is not None and s_next < s:
                return False

        return True

    def greedy_min_coverage_score(
        self,
        d: int, s: int, t: int,
        counts_func: Callable[[int,int,int], Tuple[int,int,int]]
    ) -> int:
        """
        Use only if 'min_coverage' exists; otherwise return a neutral 1.
        counts_func(d,s,t) -> (current, min_req, ideal_req)
        Return scale: 0 if below min, 1 if between min & ideal, 2+k if at/above ideal by k.
        """
        if not self.soft_min_cov:
            return 1
        current, min_req, ideal_req = counts_func(d, s, t)
        if current < min_req:
            return 0
        elif current < ideal_req:
            return 1
        else:
            return 2 + (current - ideal_req)


def register_default_handlers(engine: RuleEngine):
    """
    Register built-in CP-SAT handlers here.
    (Greedy uses the built-in helpers above; add greedy hooks only if you want extra per-rule plug-ins.)
    """
    from .rules_handlers_cpsat import (
        h_no_earlier_shift_next_day,
        h_max_consecutive_days,
        h_max_special_days,
        h_vacation_block,
        h_team_eligibility,
        h_min_coverage,
        h_target_workdays_balancing,
        h_total_workdays,
    )
    engine.register_cpsat("no_earlier_shift_next_day", h_no_earlier_shift_next_day)
    engine.register_cpsat("max_consecutive_days",      h_max_consecutive_days)
    engine.register_cpsat("max_special_days",          h_max_special_days)
    engine.register_cpsat("vacation_block",            h_vacation_block)
    engine.register_cpsat("team_eligibility",          h_team_eligibility)
    engine.register_cpsat("min_coverage",              h_min_coverage)
    engine.register_cpsat("target_workdays_balancing", h_target_workdays_balancing)
    engine.register_cpsat("total_workdays",            h_total_workdays)

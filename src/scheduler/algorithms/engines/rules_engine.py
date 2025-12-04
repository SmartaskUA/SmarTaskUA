from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Set, Callable, Optional


@dataclass
class Rule:
    id: str
    type: str
    kind: str          # "hard" | "soft"
    description: str
    scope: Optional[str]
    params: Dict[str, Any]


CPSatHandler   = Callable[[Rule, "CPSatContext"], None]
GreedyHandler  = Callable[[Rule, "GreedyContext"], bool]
ILPHandler = Callable[[Rule, "ILPContext"], None]


class RuleEngine:
    """
    General-purpose rule engine compatible with both:
      - CP-SAT (constraint handlers)
      - Greedy (incremental feasibility + scoring)
    """

    def __init__(
        self,
        rules_config: Dict[str, Any],
        *,
        num_days: int,
        shifts: int,
        employees: List[int],
        teams_map: Dict[int, List[int]],
        vacations_1based: Dict[int, List[int]],
        special_days_1based: Set[int],
        target_workdays: int = 223,
    ):
        self.rules: List[Rule] = [Rule(**r) for r in rules_config.get("rules", [])]
        self.num_days = int(num_days)
        self.shifts = int(shifts)
        self.employees = employees
        self.teams_map = teams_map
        self.vac_1b = vacations_1based
        self.special = set(special_days_1based)
        self.target_workdays = int(target_workdays)

        self.has_vac_block = any(r.type == "vacation_block" for r in self.rules)
        self.has_team_elig = any(r.type == "team_eligibility" for r in self.rules)
        self.has_max_consec = any(r.type == "max_consecutive_days" for r in self.rules)
        self.has_special_cap = any(r.type == "max_special_days" for r in self.rules)
        self.has_no_earlier_next = any(r.type == "no_earlier_shift_next_day" for r in self.rules)
        self.has_total_workdays = any(r.type == "total_workdays" for r in self.rules)
        self.soft_min_cov = next((r for r in self.rules if r.type == "min_coverage" and r.kind == "soft"), None)

        self._cpsat_handlers: Dict[str, CPSatHandler] = {}
        self._greedy_handlers: Dict[str, GreedyHandler] = {}
        self._ilp_handlers: Dict[str, ILPHandler] = {}

    def register_cpsat(self, rule_type: str, handler: CPSatHandler):
        self._cpsat_handlers[rule_type] = handler

    def register_greedy(self, rule_type: str, handler: GreedyHandler):
        self._greedy_handlers[rule_type] = handler

    def register_ilp(self, rule_type: str, handler: ILPHandler):
        self._ilp_handlers[rule_type] = handler

    # CP-SAT backend
    def apply_cp_sat(self, ctx: "CPSatContext") -> "CPSatContext":
        for r in self.rules:
            h = self._cpsat_handlers.get(r.type)
            if h:
                h(r, ctx)
        return ctx

    # Greedy backend
    def apply_greedy(self, ctx: "GreedyContext") -> bool:
        """
        Apply all registered greedy handlers sequentially for a given candidate.
        Reject if any hard rule fails.
        """
        for r in self.rules:
            h = self._greedy_handlers.get(r.type)
            if not h:
                continue
            try:
                ok = h(r, ctx)
            except Exception as ex:
                print(f"[ERROR] Rule '{r.type}' crashed on emp={ctx.e}, day={ctx.d}, shift={ctx.s}: {ex}")
                return False

            if not ok:
                if r.kind.lower() == "hard":
                    print(f"[BLOCKED] Rule '{r.type}' failed for emp={ctx.e}, day={ctx.d}, shift={ctx.s}")
                    return False
                else:
                    # soft rules add score influence only
                    continue

        return True

    def apply_ilp(self, ctx: "ILPContext") -> "ILPContext":
        for r in self.rules:
            h = self._ilp_handlers.get(r.type)
            if h:
                h(r, ctx)
        return ctx

# --------------------------
# Handler registration
# --------------------------
def register_default_handlers(engine: RuleEngine):
    """Register built-in CP-SAT rule handlers."""
    from ..rules.handlers.rules_handlers_cpsat import (
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
    engine.register_cpsat("max_consecutive_days", h_max_consecutive_days)
    engine.register_cpsat("max_special_days", h_max_special_days)
    engine.register_cpsat("vacation_block", h_vacation_block)
    engine.register_cpsat("team_eligibility", h_team_eligibility)
    engine.register_cpsat("min_coverage", h_min_coverage)
    engine.register_cpsat("target_workdays_balancing", h_target_workdays_balancing)
    engine.register_cpsat("total_workdays", h_total_workdays)


def register_default_greedy_handlers(engine: RuleEngine):
    """Register built-in Greedy rule handlers."""
    from ..rules.handlers.rules_handlers_greedy import (
        g_no_earlier_shift_next_day,
        g_max_consecutive_days,
        g_max_special_days,
        g_total_workdays,
        g_vacation_block,
        g_team_eligibility,
        g_min_coverage,
        g_target_workdays_balancing,
    )
    engine.register_greedy("no_earlier_shift_next_day", g_no_earlier_shift_next_day)
    engine.register_greedy("max_consecutive_days", g_max_consecutive_days)
    engine.register_greedy("max_special_days", g_max_special_days)
    engine.register_greedy("total_workdays", g_total_workdays)
    engine.register_greedy("vacation_block", g_vacation_block)
    engine.register_greedy("team_eligibility", g_team_eligibility)
    engine.register_greedy("min_coverage", g_min_coverage)
    engine.register_greedy("target_workdays_balancing", g_target_workdays_balancing)

def register_default_ilp_handlers(engine: RuleEngine):
    from ..rules.handlers.rules_handlers_ilp import (
        i_one_shift_per_day,
        i_total_workdays,
        i_max_consecutive_days,
        i_max_special_days,
        i_no_earlier_shift_next_day,
        i_vacation_block,
        i_min_coverage,
    )
    engine.register_ilp("one_shift_per_day", i_one_shift_per_day)
    engine.register_ilp("total_workdays", i_total_workdays)
    engine.register_ilp("max_consecutive_days", i_max_consecutive_days)
    engine.register_ilp("max_special_days", i_max_special_days)
    engine.register_ilp("no_earlier_shift_next_day", i_no_earlier_shift_next_day)
    engine.register_ilp("vacation_block", i_vacation_block)
    engine.register_ilp("min_coverage", i_min_coverage)

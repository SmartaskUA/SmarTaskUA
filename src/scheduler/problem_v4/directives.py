"""How to solve, as opposed to what to solve.

v4.0 is the problem definition only (FUTURE.md section 6): `constraints.soft` is
always empty, so the objective weights and the day-off-swap switch live here and
reach a solver as keyword arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import List, Mapping


@dataclass(frozen=True)
class SolveDirectives:
    # ObjectiveFunction1: shortage against alpha_dts.
    w1: int = 1000
    # ObjectiveFunction2: p_sl-weighted skill assignment. Kept small on purpose:
    # with four tiers p_sl reaches 31, and w2 * p_sl must stay below w1 or the
    # solver prefers leaving demand uncovered to covering it with a low tier.
    w2: int = 1
    # ObjectiveFunction3: preferred day-offs that end up worked (swap only).
    w3: int = 10
    # Off by default: a swapped DO rests a work cell elsewhere in the week, and
    # the v4 result check rejects a rest on a work cell (next_meeting.md).
    allow_day_off_swap: bool = False

    @classmethod
    def from_kwargs(cls, kwargs: Mapping) -> "SolveDirectives":
        """Pick the directives out of a solver's **kwargs, tolerating CLI strings."""
        values = {}
        for f in fields(cls):
            if f.name not in kwargs or kwargs[f.name] is None:
                continue
            raw = kwargs[f.name]
            if f.type in ("bool", bool):
                values[f.name] = raw if isinstance(raw, bool) else str(raw).strip().lower() in {"1", "true", "yes", "on"}
            else:
                values[f.name] = int(raw)
        return cls(**values)

    def warnings(self, max_priority_weight: int) -> List[str]:
        if self.w1 > 0 and self.w2 * max_priority_weight >= self.w1:
            return [
                f"w2={self.w2} times the largest p_sl ({max_priority_weight}) reaches w1={self.w1}: "
                "covering a slot with a low-priority skill would cost more than leaving it short"
            ]
        return []

# greedy_context.py
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Callable, Optional
import numpy as np

@dataclass
class GreedyContext:
    # static/problem data
    num_days: int
    shifts: int
    employees: List[int]                         # 1-based
    teams_map: Dict[int, List[int]]             # emp_id -> [team_ids allowed]
    vacations_1b: Dict[int, List[int]]          # emp_id -> [days 1..N]
    special_days_1b: Set[int]                   # Sundays+holidays
    mins: Dict[Tuple[int,int,int], int]         # (day, shift, team_id) -> min
    ideals: Dict[Tuple[int,int,int], int]       # (day, shift, team_id) -> ideal

    # dynamic/reference state (mutates during greedy)
    assignment: Dict[int, List[Tuple[int,int,int]]]      # emp_id -> [(day, shift, team_id)]
    schedule_table: Dict[Tuple[int,int,int], List[int]]  # (day, shift, team_id) -> [emp_id]

    # helper for min_coverage scoring
    def counts_for(self, d: int, s: int, t: int) -> Tuple[int, int, int]:
        current = len(self.schedule_table.get((d, s, t), []))
        min_req  = int(self.mins.get((d, s, t), 0))
        ideal_req = int(self.ideals.get((d, s, t), min_req))
        return current, min_req, ideal_req

    # small utilities reused by handlers
    @staticmethod
    def _worked_days(assign_list: List[Tuple[int,int,int]]) -> List[int]:
        return sorted({d for (d, _s, _t) in assign_list})

    @staticmethod
    def _shift_on_day(assign_list: List[Tuple[int,int,int]], d: int) -> Optional[int]:
        for (day, s, _t) in assign_list:
            if day == d:
                return s
        return None

    def _count_special(self, assign_list: List[Tuple[int,int,int]]) -> int:
        return sum(1 for (d, _s, _t) in assign_list if d in self.special_days_1b)

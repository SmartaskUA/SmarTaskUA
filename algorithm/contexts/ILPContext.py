from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
import pulp


@dataclass
class ILPContext:

    model: pulp.LpProblem
    x: Dict[int, Dict[Any, Dict[int, pulp.LpVariable]]]
    y: Dict[Any, Dict[int, Dict[str, pulp.LpVariable]]]
    employees: List[int]
    dates: List[Any]
    shifts: int
    teams: Dict[str, List[int]]
    vacations: Dict[int, List[Any]]
    sundays_holidays: List[Any]
    min_required: Dict[Tuple[Any, str, int], int]

    def add_constraint(self, expr, name: str):
        """Helper to safely add a constraint with a unique label."""
        if name in self.model.constraints:
            name = f"{name}_{len(self.model.constraints)}"
        self.model += expr, name

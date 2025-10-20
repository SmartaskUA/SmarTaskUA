from dataclasses import dataclass, field
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

    objective_terms: List[pulp.LpAffineExpression] = field(default_factory=list)

    def add_constraint(self, expr, name: str):
        if name in self.model.constraints:
            name = f"{name}_{len(self.model.constraints)}"
        self.model += expr, name

    def add_penalty(self, expr, weight: float = 1.0):
        self.objective_terms.append(weight * expr)

# modules/TaskManager.py

import json
from algorithms.ILP import solve as ilp_solver
from algorithms.greedyRandomized import solve as greedy_randomized_solver
from algorithms.greedyClimbing import solve as greedy_climbing_solver
from algorithms.CSP import solve as csp_solver
from algorithms.CSPv2 import solve as cspv2_solver
from algorithms.CSP_H import solve as CSP_13Hours_solver
from algorithms.CSP_Afonso_Hours import solve as CSP_Afonso_Hours_solver
from algorithms.ILP_1 import solve as ILP_1
from algorithms.ILP_1_Half_Intervals import solve as ILP_1_Half_Intervals
from algorithms.ILP_2 import solve as ILP_2
from algorithms.ILP_2_Half_Intervals import solve as ILP_2_Half_Intervals
from algorithms.ILP_3 import solve as ILP_3
from algorithms.COP_2 import solve as COP_2
from algorithms.COP_1 import solve as COP_1
from algorithms.CSP_1 import solve as CSP_1
from algorithms.ILP_3_Half_Intervals import solve as ILP_3_Half_Intervals
from algorithms.CSP_2_Half_Intervals import solve as CSP_2_Half_Intervals
from algorithms.Heuristica1 import solve as Heuristica_1
from algorithms.Heuristica1_v2 import solve as Heuristica1_v2
from algorithms.Heuristica1_v3 import solve as Heuristica1_v3
from algorithms.Heuristica import solve as Heuristica
from algorithms.Heuristica_Half_Intervals import solve as Heuristica_Half_Intervals
from algorithms.ILP_4 import solve as ILP_4

class TaskManager:
    def __init__(self):
        # No futuro, você pode adicionar suporte a múltiplos algoritmos aqui
        # ToDo: this must be converted to a json file that can be dynamically modified
        self.algorithms = {
            "linear programming": ilp_solver,
            "Greedy Randomized": greedy_randomized_solver,
            "Greedy Randomized + Hill Climbing": greedy_climbing_solver,
            "CSP": csp_solver,
            "CSPv2": cspv2_solver,
            "CSP_13Hours": CSP_13Hours_solver,
            "CSP_Afonso_Hours": CSP_Afonso_Hours_solver,
            "ILP_1": ILP_1,
            "ILP_1_Half_Intervals": ILP_1_Half_Intervals,
            "ILP_2": ILP_2,
            "ILP_2_Half_Intervals": ILP_2_Half_Intervals,
            "ILP_3": ILP_3,
            "ILP_4": ILP_4,
            "CSP_1": CSP_1,
            "COP_1": COP_1,
            "COP_2": COP_2,
            "ILP_3_Half_Intervals": ILP_3_Half_Intervals,
            "CSP_2_Half_Intervals": CSP_2_Half_Intervals,
            "Heuristica_1": Heuristica_1,
            "Heuristica1_v2": Heuristica1_v2,
            "Heuristica1_v3": Heuristica1_v3,
            "Heuristica": Heuristica,
            "Heuristica_Half_Intervals": Heuristica_Half_Intervals,
        }

    def run_task(self, task_id, title, algorithm_name="CSP Scheduling", vacations=None, minimuns=None, employees=None, maxTime=10, year=None, shifts=2, rules=None, hours=13):
        print(f"\n[DEBUG] Vacations received:\n{vacations}")
        print(f"[DEBUG] Minimuns received:\n{minimuns}")
        print(f"[DEBUG] Rules received:\n{json.dumps(rules, indent=2) if rules else 'None'}")

        if algorithm_name not in self.algorithms:
            raise ValueError(f"Algorithm '{algorithm_name}' not found.")

        print(f"[TaskManager] Executing algorithm '{algorithm_name}' with Task ID: {task_id}")
        algorithm = self.algorithms[algorithm_name]

        if not rules:
            from pathlib import Path
            current_dir = Path(__file__).parent
            rules_path = current_dir /  "rules.json"
            with open(rules_path) as f:
                rules = json.load(f)
                
        if isinstance(rules, dict) and "rules" in rules:
            rules_json = rules
        else:
            rules_json = {"rules": rules}

        if algorithm_name in ["linear programming", "hill climbing", "Greedy Randomized", "Greedy Randomized + Hill Climbing", "CSP", "GRHC_ENGINE", "CSP_ENGINE", "Greedy Randomized Engine", "ILP Engine", "linear programming 2", "CSPv2"]:

            schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, shifts=shifts, rules=rules_json)
        elif algorithm_name in [# "CSP_13Hours", 
                                # "CSP_Afonso_Hours", 
                                "ILP_1", 
                                "ILP_1_Half_Intervals", 
                                "ILP_2", 
                                "ILP_2_Half_Intervals",
                                "ILP_3",
                                "ILP_4",
                                "CSP_1",
                                "COP_1",
                                "COP_2",
                                "ILP_3_Half_Intervals",
                                "CSP_2_Half_Intervals",
                                "Heuristica_1",
                                "Heuristica1_v2",
                                "Heuristica1_v3",
                                "Heuristica",
                                "Heuristica_Half_Intervals"
                                ]:
            schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, hours=hours, rules=rules_json)
        else:
            schedule_data = algorithm()

        print(f"[TaskManager] Algorithm '{algorithm_name}' successfully finalized.")
        print(f"[TaskManager] Schedule generated by '{algorithm_name}' algorithm: {schedule_data}")
        return schedule_data
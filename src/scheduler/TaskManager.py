# modules/TaskManager.py

import json
import time
from algorithms.hillClimbing import solve as hill_clibing_alg_solver
from algorithms.ILP import solve as ilp_solver
from algorithms.greedyRandomized import solve as greedy_randomized_solver
from algorithms.greedyClimbing import solve as greedy_climbing_solver
from algorithms.CSP import solve as csp_solver
from algorithms.engines.CSP_Engine import solve as csp_engine_solver
from algorithms.engines.greedyClimbingEngine import solve as grhc_engine_solver
from algorithms.engines.greedyRandomizedEngine import solve as greedy_randomized_engine_solver
from algorithms.engines.ILPEngine import solve as ilp_solver_engine
from algorithms.ILPv2 import solve as ilp_solver_2
from algorithms.ILPv3 import solve as ilp_solver_3
from algorithms.heuristicSolver import solve as heuristic_solver
from algorithms.ilp_greedy import solve as ilp_greedy
from algorithms.CSPv2 import solve as cspv2_solver
from algorithms.ILP_H import solve as ILP_13Hours_solver
from algorithms.CSP_H import solve as CSP_13Hours_solver
from algorithms.CSP_Afonso_Hours import solve as CSP_Afonso_Hours_solver
from algorithms.ILP_Half_Hour import solve as ILP_13_Half_Intervals_solver
from algorithms.CSP_Extra import solve as CSP_Extra_Hours_solver
from algorithms.ILP_Extra import solve as ILP_Extra_Hours_solver
from algorithms.ILP_Sisqual_Hours import solve as ILP_Sisqual_Hours_solver
from algorithms.general.ilp_general import solve as ilp_general_solver
from algorithms.general.csp_general import solve as csp_general_solver
from algorithms.general.heuristic_general import solve as heuristic_general_solver

class TaskManager:
    def __init__(self):
        # No futuro, você pode adicionar suporte a múltiplos algoritmos aqui
        # ToDo: this must be converted to a json file that can be dynamically modified
        self.algorithms = {
            "hill climbing": hill_clibing_alg_solver,
            "linear programming": ilp_solver,
            "linear programming 2": ilp_solver_3,
            "ILP General": ilp_general_solver,
            "ILP Engine": ilp_solver_engine,
            "Greedy Randomized": greedy_randomized_solver,
            "Greedy Randomized + Hill Climbing": greedy_climbing_solver,
            "CSP": csp_solver,
            "CSP Scheduling": csp_solver,
            "CSPv2": cspv2_solver,
            "CSP General": csp_general_solver,
            "CSP_ENGINE": csp_engine_solver,
            "GRHC_ENGINE": grhc_engine_solver,
            "Greedy Randomized Engine": greedy_randomized_engine_solver,
            "Heuristic Solver": heuristic_solver,
            "Heuristic General": heuristic_general_solver,
            "ilp_greedy": ilp_greedy,
            "ILP_13Hours": ILP_13Hours_solver,
            "CSP_13Hours": CSP_13Hours_solver,
            "CSP_Afonso_Hours": CSP_Afonso_Hours_solver,
            "ILP_13_Half_Intervals": ILP_13_Half_Intervals_solver,
            "ILP_Half_Hour": ILP_13_Half_Intervals_solver,
            "CSP_Extra_Hours": CSP_Extra_Hours_solver,
            "ILP_Extra_Hours": ILP_Extra_Hours_solver,
            "ILP_Sisqual_Hours": ILP_Sisqual_Hours_solver,
        }

    def run_task(self, task_id, title, algorithm_name="CSP Scheduling", vacations=None, minimuns=None, employees=None, maxTime=10, year=None, shifts=2, rules=None, hours=13, problem_path=None):
        print(f"\n[DEBUG] Vacations received:\n{vacations}")
        print(f"[DEBUG] Minimuns received:\n{minimuns}")
        print(f"[DEBUG] Rules received:\n{json.dumps(rules, indent=2) if rules else 'None'}")

        if algorithm_name not in self.algorithms:
            raise ValueError(f"Algorithm '{algorithm_name}' not found.")

        print(f"[TaskManager] Executing algorithm '{algorithm_name}' with Task ID: {task_id}")
        algorithm = self.algorithms[algorithm_name]

        no_rules_algorithms = {"ILP General", "CSP General", "ILP_Sisqual_Hours"}
        uses_rules = algorithm_name not in no_rules_algorithms
        rules_json = None
        if uses_rules:
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

        start_time = time.time()
        if algorithm_name in [
            "linear programming",
            "hill climbing",
            "Greedy Randomized",
            "Greedy Randomized + Hill Climbing",
            "CSP",
            "GRHC_ENGINE",
            "CSP_ENGINE",
            "Greedy Randomized Engine",
            "ILP Engine",
            "linear programming 2",
            "ILP General",
            "CSPv2",
            "CSP General",
            "Heuristic Solver",
            "Heuristic Solver Restarts",
            "ilp_greedy",
        ]:
            if uses_rules:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, shifts=shifts, rules=rules_json)
            else:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, shifts=shifts, constraints=rules)
        elif algorithm_name in ["ILP_13Hours", "CSP_13Hours", "CSP_Afonso_Hours", "ILP_13_Half_Intervals", "ILP_Half_Hour", "CSP_Extra_Hours", "ILP_Extra_Hours"]:
            if uses_rules:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, hours=hours, rules=rules_json)
            else:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, hours=hours, constraints=rules)
        elif algorithm_name in ["ILP_Sisqual_Hours"]:
            schedule_data = algorithm(problem_path=problem_path, maxTime=maxTime)
        else:
            schedule_data = algorithm()
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"[TaskManager] Algorithm '{algorithm_name}' executed in {elapsed_time:.2f} seconds.")

        print(f"[TaskManager] Algorithm '{algorithm_name}' successfully finalized.")
        print(f"[TaskManager] Schedule generated by '{algorithm_name}' algorithm")
        return schedule_data, elapsed_time

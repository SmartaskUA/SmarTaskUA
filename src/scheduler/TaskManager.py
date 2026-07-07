# modules/TaskManager.py

import json
import time
import os
import sys
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
from algorithms.CSP_Afonso_Hours import solve as CSP_Afonso_Hours_solver
from algorithms.ILP_Sisqual_Hours import solve as ILP_Sisqual_Hours_solver
from algorithms.CSP_Sisqual_Hours import solve as CSP_Sisqual_Hours_solver
from algorithms.ILP_Sisqual_Hours_MathematicalDefinition7 import solve as ILP_Sisqual_Hours_MathematicalDefinition7_solver
from algorithms.CSP_Sisqual_Hours_MathematicalDefinition7 import solve as CSP_Sisqual_Hours_MathematicalDefinition7_solver
from algorithms.ILP_2 import solve as ILP_2
from algorithms.ILP_2_Half_Intervals import solve as ILP_2_Half_Intervals
from algorithms.ILP_3 import solve as ILP_3
from algorithms.COP_2 import solve as COP_2
from algorithms.COP_1 import solve as COP_1
from algorithms.ILP_3_Half_Intervals import solve as ILP_3_Half_Intervals
from algorithms.Heuristica1 import solve as Heuristica_1
from algorithms.Heuristica_Half_Intervals import solve as Heuristica_Half_Intervals
from algorithms.ILP_4 import solve as ILP_4
from algorithms.general.ilp_general import solve as ilp_general_solver
from algorithms.general.csp_general import solve as csp_general_solver
from algorithms.ILP_4_Half_Intervals import solve as ILP_4_Half_Intervals
from algorithms.COP_2_Half_Intervals import solve as COP_2_Half_Intervals_Solver
from algorithms.COP_1_Half_Intervals import solve as COP_1_Half_Intervals_solver
from algorithms.general.heuristic_general import solve as heuristic_general_solver
from analyzer.kpiVerification_Sisqual import KpiEvaluator_Sisqual
from validators.sisqual_feasibility import validate_sisqual_problem_or_raise
from sisqual_monthly_runner import run_sisqual_monthly, should_run_monthly

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
            "CSP_Afonso_Hours": CSP_Afonso_Hours_solver,
            "ILP_2": ILP_2,
            "ILP_2_Half_Intervals": ILP_2_Half_Intervals,
            "ILP_3": ILP_3,
            "ILP_4": ILP_4,
            "ILP_4_Half_Intervals": ILP_4_Half_Intervals,
            "COP_1": COP_1,
            "COP_2": COP_2,
            "ILP_3_Half_Intervals": ILP_3_Half_Intervals,
            "Heuristica_1": Heuristica_1,
            "Heuristica_Half_Intervals": Heuristica_Half_Intervals,
            "CSP General": csp_general_solver,
            "CSP_ENGINE": csp_engine_solver,
            "GRHC_ENGINE": grhc_engine_solver,
            "Greedy Randomized Engine": greedy_randomized_engine_solver,
            "Heuristic Solver": heuristic_solver,
            "Heuristic General": heuristic_general_solver,
            "ilp_greedy": ilp_greedy,
            "ILP_Sisqual_Hours": ILP_Sisqual_Hours_solver,
            "CSP_Sisqual_Hours": CSP_Sisqual_Hours_solver,
            "ILP_Sisqual_Hours_MathematicalDefinition7": ILP_Sisqual_Hours_MathematicalDefinition7_solver,
            "CSP_Sisqual_Hours_MathematicalDefinition7": CSP_Sisqual_Hours_MathematicalDefinition7_solver,
            "ILP_Sisqual_Hours_MathematicalDefinition5": ILP_Sisqual_Hours_MathematicalDefinition7_solver,
            "CSP_Sisqual_Hours_MathematicalDefinition5": CSP_Sisqual_Hours_MathematicalDefinition7_solver,
            "COP_1_Half_Intervals": COP_1_Half_Intervals_solver,
            "COP_2_Half_Intervals": COP_2_Half_Intervals_Solver,
        }

    def run_task(self, task_id, title, algorithm_name="CSP Scheduling", vacations=None, minimuns=None, employees=None, maxTime=10, year=None, shifts=2, rules=None, hours=13, solver="CBC", problem_path=None):
        print(f"\n[DEBUG] Vacations received:\n{vacations}")
        print(f"[DEBUG] Minimuns received:\n{minimuns}")
        print(f"[DEBUG] Rules received:\n{json.dumps(rules, indent=2) if rules else 'None'}")
        print(f"[DEBUG] Solver received: {solver}")
        print(f"[DEBUG] Problem path received: {problem_path}")

        kpis = None  # Initialize KPIs variable
        extra_metadata = None

        if algorithm_name not in self.algorithms:
            raise ValueError(f"Algorithm '{algorithm_name}' not found.")

        # Defensive: ensure employees is always a list
        if employees is None:
            print("[WARNING] 'employees' is None, converting to empty list.")
            employees = []
        elif not isinstance(employees, list):
            print(f"[WARNING] 'employees' is not a list (type={type(employees)}), converting to list.")
            employees = list(employees)

        print(f"[TaskManager] Executing algorithm '{algorithm_name}' with Task ID: {task_id}")
        algorithm = self.algorithms[algorithm_name]

        no_rules_algorithms = {
            "ILP General",
            "CSP General",
            "ILP_Sisqual_Hours",
            "CSP_Sisqual_Hours",
            "ILP_Sisqual_Hours_MathematicalDefinition7",
            "CSP_Sisqual_Hours_MathematicalDefinition7",
            "ILP_Sisqual_Hours_MathematicalDefinition5",
            "CSP_Sisqual_Hours_MathematicalDefinition5",
        }
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
        # Algoritmos que aceitam 'shifts'
        algs_with_shifts = [
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
        ]
        if algorithm_name in algs_with_shifts:
            if uses_rules:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, shifts=shifts, rules=rules_json)
            else:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, shifts=shifts, constraints=rules)
        elif algorithm_name == "CSP_Afonso_Hours":
            if uses_rules:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, hours=hours, rules=rules_json)
            else:
                schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, hours=hours, constraints=rules)
        elif algorithm_name in [
            "ILP_Sisqual_Hours",
            "CSP_Sisqual_Hours",
            "ILP_Sisqual_Hours_MathematicalDefinition7",
            "CSP_Sisqual_Hours_MathematicalDefinition7",
            "ILP_Sisqual_Hours_MathematicalDefinition5",
            "CSP_Sisqual_Hours_MathematicalDefinition5",
        ]:
            # Request the solver to print the returned rows as JSON so the
            # container logs contain the schedule payload sent to the frontend.
            validate_sisqual_problem_or_raise(problem_path, task_id, algorithm_name=algorithm_name)
            if should_run_monthly(problem_path):
                monthly_result = run_sisqual_monthly(
                    problem_path=problem_path,
                    algorithm=algorithm,
                    algorithm_name=algorithm_name,
                    max_time=maxTime,
                    task_id=task_id,
                )
                schedule_data = monthly_result.schedule
                extra_metadata = {"monthlyExecution": monthly_result.metadata}
            else:
                solver_kwargs = {"problem_path": problem_path, "maxTime": maxTime, "print_json": True, "task_id": task_id}
                schedule_data = algorithm(**solver_kwargs)
            # print(f"[Taskmaster] Schedule data returned by '{algorithm_name}': {schedule_data}")
            try:
                # Attempt to locate expected problem bundle files (demand.csv, schedule_input.csv, problem.json)
                demand_path = None
                input_path = None
                problem_json_path = None
                if problem_path:
                    # If problem_path points to a directory use it directly, otherwise use its parent dir
                    base = problem_path if os.path.isdir(problem_path) else os.path.dirname(problem_path)
                    demand_path = os.path.join(base, "demand.csv")
                    input_path = os.path.join(base, "schedule_input.csv")
                    problem_json_path = os.path.join(base, "problem.json")

                # Only pass paths that actually exist to avoid loader errors
                kp_demand = demand_path if (demand_path and os.path.exists(demand_path)) else None
                kp_input = input_path if (input_path and os.path.exists(input_path)) else None
                kp_problem = problem_json_path if (problem_json_path and os.path.exists(problem_json_path)) else None

                kpi_eval = KpiEvaluator_Sisqual(
                    schedule_data,
                    demand_csv_path=kp_demand,
                    input_csv_path=kp_input,
                    problem_json=kp_problem,
                )
                kpi_eval.evaluate_kpis()
                kpis = getattr(kpi_eval, 'kpis', None)
            except Exception as e:
                print(f"[TaskManager] KPI evaluation failed: {e}")
                kpis = None
        
        elif algorithm_name in [
            "ILP_2",
            "ILP_2_Half_Intervals",
            "ILP_3",
            "ILP_4",
            "ILP_4_Half_Intervals",
            "ILP_3_Half_Intervals",
            "COP_1",
            "COP_1_Half_Intervals",
            "COP_2",
            "COP_2_Half_Intervals",
            "Heuristica_1",
            "Heuristica_Half_Intervals"
        ]:
            schedule_data = algorithm(vacations=vacations, minimuns=minimuns, employees=employees, maxTime=maxTime, year=year, hours=hours, solver=solver)
        else:
            raise ValueError(f"Algorithm '{algorithm_name}' not configured in TaskManager.")
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"[TaskManager] Algorithm '{algorithm_name}' executed in {elapsed_time:.2f} seconds.")

        print(f"[TaskManager] Algorithm '{algorithm_name}' successfully finalized.")
        print(f"[TaskManager] Schedule generated by '{algorithm_name}' algorithm")
        result = {"schedule": schedule_data, "kpis": kpis}
        if extra_metadata:
            result["metadata"] = extra_metadata
        return result, elapsed_time

import os
import re
from ortools.sat.python import cp_model


def _next_log_filename(base_name, log_dir="."):
    scenario_id = 1
    while True:
        filename = os.path.join(log_dir, f"{base_name}_{scenario_id}.txt")
        if not os.path.exists(filename):
            return filename
        scenario_id += 1


class SolutionTracker(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self.best_solution_time = 0.0
        self.best_objective = float('inf')
        self.best_bound = float('-inf')
        self.solution_count = 0
        self.history = []

    def on_solution_callback(self):
        self.solution_count += 1
        self.best_solution_time = self.WallTime()
        self.best_objective = self.ObjectiveValue()
        self.best_bound = self.BestObjectiveBound()

        gap = 0.0
        if self.best_objective != 0:
            gap = abs(self.best_objective - self.best_bound) / abs(self.best_objective)

        self.history.append({
            "count": self.solution_count,
            "time": self.best_solution_time,
            "obj": self.best_objective,
            "bound": self.best_bound,
            "gap": gap
        })

        print(f"Solution #{self.solution_count} found at {self.best_solution_time:.2f}s "
              f"| Obj: {self.best_objective} | Gap: {gap:.2%}")


def solve_cp_with_tracker(solver, model, tracker):
    """
    OR-Tools compatibility helper.

    Some versions accept `solution_callback=` on `CpSolver.Solve`, while others only
    support a positional callback or `SolveWithSolutionCallback`.
    """
    try:
        return solver.Solve(model, solution_callback=tracker)
    except TypeError:
        if hasattr(solver, "SolveWithSolutionCallback"):
            return solver.SolveWithSolutionCallback(model, tracker)
        return solver.Solve(model, tracker)


def write_csp_log(*, tracker, solver, status, n_employees, max_time=None, log_dir="."):
    base_name = f"logs_{n_employees}_employees_scenario"
    filename = _next_log_filename(base_name, log_dir=log_dir)

    final_gap = 0.0
    if tracker.best_objective != 0 and tracker.best_objective != float('inf'):
        final_gap = abs(tracker.best_objective - tracker.best_bound) / abs(tracker.best_objective)

    with open(filename, "w") as f:
        f.write("SOLVER REPORT\n")
        f.write("=============\n")
        f.write(f"Employees: {n_employees}\n")
        f.write(f"Max Time Allowed: {max_time if max_time else 'Unlimited'} mins\n")
        f.write(f"Final Status: {solver.StatusName(status)}\n")
        f.write(f"Total Solutions Found: {tracker.solution_count}\n")
        f.write("\n--- PROGRESS LOG ---\n")
        f.write(f"{'Count':<8} | {'Time (s)':<12} | {'Objective':<15} | {'Gap':<10}\n")
        f.write("-" * 55 + "\n")

        for entry in tracker.history:
            f.write(f"{entry['count']:<8} | {entry['time']:<12.4f} | "
                    f"{entry['obj']:<15} | {entry['gap']:.4%}\n")

        f.write("-" * 55 + "\n")
        f.write("FINAL RESULTS:\n")
        f.write(f"Best Solution Time: {tracker.best_solution_time:.4f}s\n")
        f.write(f"Objective Value:    {tracker.best_objective}\n")
        f.write(f"Lower Bound:        {tracker.best_bound}\n")
        f.write(f"Final Gap:          {final_gap:.4%}\n")

    print(f"\nLog file saved to: {filename}")
    return filename


def parse_cbc_log(log_text):
    """
    Parse CBC solver output to extract progress (time, obj, bound, iterations, nodes).

    Returns:
      history: list of dicts with keys:
          nodes, iters, time, obj, bound, gap
      final_obj, final_bound, final_gap
    """
    history = []
    final_obj = None
    final_bound = None
    final_gap = None

    prog_re = re.compile(
        r"After\s+(?P<nodes>\d+)\s+nodes.*?,\s+"
        r"(?P<iters>\d+)\s+iterations,\s+"
        r"(?P<time>[0-9.]+)\s+seconds.*?"
        r"objective\s+(?P<obj>-?[0-9.]+)"
        r"(?:.*?best possible\s+(?P<bound>-?[0-9.]+))?",
        re.IGNORECASE,
    )

    pass_re = re.compile(
        r"Cbc0038I\s+(?:Pass\s+(?P<pass>\d+):\s+)?\("
        r"(?P<time>[0-9.]+)\s+seconds\).*?"
        r"obj\.\s+(?P<obj>-?[0-9.]+)\s+iterations\s+(?P<iters>\d+)",
        re.IGNORECASE,
    )

    final_re = re.compile(
        r"best objective\s+(-?[0-9.]+),\s+best possible\s+(-?[0-9.]+)\s+\(gap\s+([0-9.]+)%",
        re.IGNORECASE,
    )

    for line in log_text.splitlines():
        m = prog_re.search(line)
        if m:
            nodes = int(m.group("nodes"))
            iters = int(m.group("iters"))
            t = float(m.group("time"))
            obj = float(m.group("obj"))
            bound_raw = m.group("bound")
            bound = float(bound_raw) if bound_raw is not None else None
            history.append(
                {
                    "nodes": nodes,
                    "iters": iters,
                    "time": t,
                    "obj": obj,
                    "bound": bound,
                    "gap": None,
                }
            )

        m2 = final_re.search(line)
        if m2:
            final_obj = float(m2.group(1))
            final_bound = float(m2.group(2))
            final_gap = float(m2.group(3)) / 100.0

        m3 = pass_re.search(line)
        if m3:
            pass_id = m3.group("pass")
            nodes = int(pass_id) if pass_id is not None else None
            t = float(m3.group("time"))
            obj = float(m3.group("obj"))
            iters = int(m3.group("iters"))
            history.append(
                {
                    "nodes": nodes,
                    "iters": iters,
                    "time": t,
                    "obj": obj,
                    "bound": None,
                    "gap": None,
                }
            )

    if final_bound is not None:
        for h in history:
            obj = h["obj"]
            if obj != 0:
                h["gap"] = abs(obj - final_bound) / abs(obj)
            else:
                h["gap"] = 0.0

    return history, final_obj, final_bound, final_gap


def write_ilp_log(*, history, final_obj, final_bound, final_gap, solver_output,
                  n_employees, max_time, status_str, wall_time, log_dir="."):
    base_name = f"logs_ilp_{n_employees}_employees_scenario"
    filename = _next_log_filename(base_name, log_dir=log_dir)

    with open(filename, "w") as f:
        f.write("SOLVER REPORT (ILP / CBC)\n")
        f.write("=========================\n")
        f.write(f"Employees: {n_employees}\n")
        f.write(f"Max Time Allowed: {max_time if max_time else 'Unlimited'} mins\n")
        f.write(f"Final Status: {status_str}\n")
        f.write(f"Wall Time: {wall_time:.4f}s\n")
        f.write(f"Final Objective: {final_obj if final_obj is not None else 'N/A'}\n")
        f.write(f"Final Bound: {final_bound if final_bound is not None else 'N/A'}\n")
        if final_gap is not None:
            f.write(f"Final Gap: {final_gap:.4%}\n")
        else:
            f.write("Final Gap: N/A\n")

        f.write("\n--- PROGRESS LOG ---\n")
        f.write(
            f"{'Count':<8} | {'Time (s)':<10} | "
            f"{'Objective':<15} | {'Bound':<15} | "
            f"{'Gap':<10} | {'Iters':<8} | {'Nodes':<8}\n"
        )
        f.write("-" * 98 + "\n")

        for idx, h in enumerate(history, start=1):
            gap_str = f"{h['gap']:.4%}" if h["gap"] is not None else "N/A"
            bound_str = f"{h['bound']:.4f}" if h["bound"] is not None else "N/A"
            f.write(
                f"{idx:<8} | {h['time']:<10.4f} | "
                f"{h['obj']:<15.4f} | {bound_str:<15} | "
                f"{gap_str:<10} | {h['iters']:<8} | {h['nodes']:<8}\n"
            )

        f.write("\n--- CBC RAW LOG ---\n")
        f.write(solver_output)

    print(f"Log file saved to: {filename}")
    return filename

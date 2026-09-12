#!/usr/bin/env python3
"""Compare heuristic remaining shortages with KpiEvaluator totals."""
import sys
from pathlib import Path

from algorithms.Hybrid_Heuristic_Sisqual_No_Levels_Included import Hybrid_Heuristic_Sisqual
from analyzer.kpiVerification_Sisqual import KpiEvaluator_Sisqual
from algorithms.sisqual_hours_utils import load_problem_json


def main(problem_path: str):
    problem_path = Path(problem_path)
    if not problem_path.exists():
        print(f"Problem file not found: {problem_path}")
        return 1

    print(f"Loading problem: {problem_path}")
    sched = Hybrid_Heuristic_Sisqual(str(problem_path))
    sched.Minimuns()
    rows = sched.build_output_rows()

    # Heuristic remaining shortage from self.need
    heuristic_shortage = sum(v for v in sched.need.values() if v > 0)

    # compute KPI shortage
    problem = load_problem_json(problem_path)
    demand_file = problem.get("demand", {}).get("dataFile", "demand.csv")
    demand_path = problem_path.parent / demand_file

    kpi = KpiEvaluator_Sisqual(rows, demand_csv_path=str(demand_path), problem_json=problem)
    kpi_res = kpi.compute_Total_Shortage()
    kpi_shortage = kpi_res.get("value") if isinstance(kpi_res, dict) else kpi_res

    print("\n--- Shortage comparison ---")
    print(f"Heuristic remaining (sum self.need): {heuristic_shortage}")
    print(f"KPI evaluator total_shortage:       {kpi_shortage}")

    # Optional: show top 10 slot differences
    try:
        stats = kpi._slot_stats or kpi._build_slot_stats()
        # Build map from (date, team, p_start, p_end) -> gap
        slot_map = {(s['date'], s['team'], s['p_start'], s['p_end']): s['gap'] for s in stats['slots']}

        # Build heuristic map from sched.need: (date, slot_idx, skill) -> need
        # Need uses slot_idx; translate slot_idx to minutes via sched.time_slots
        slot_by_idx = {slot.index: (slot.start_min, slot.end_min) for slot in sched.time_slots}
        diffs = []
        for (date, slot_idx, skill), need in sched.alpha.items():
            remaining = sched.need.get((date, slot_idx, skill), 0)
            p_start, p_end = slot_by_idx[slot_idx]
            gap = slot_map.get((date, skill, p_start, p_end), None)
            if gap is None:
                continue
            if remaining != gap:
                diffs.append(((date, skill, p_start, p_end), remaining, gap))

        diffs.sort(key=lambda x: (x[0][0], x[0][1], x[0][2]))
        print("\nTop differences (date,skill,start,end) -> heuristic_remaining vs kpi_gap")
        for item in diffs[:20]:
            (date, skill, s, e), hrem, kgap = item
            print(f"{date} {skill} {s}-{e}: {hrem} vs {kgap}")
    except Exception as ex:
        print("Could not compute per-slot diffs:", ex)

    return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: compare_shortage.py /path/to/problem.json")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))

"""
lns_destroy.py
--------------
Destroy operators for the LNS scheduler (Version 1 model).

Each operator accepts the current Solution + CoverageTracker and returns a
list of (emp_id, day) pairs that were removed from the solution.  The caller
is responsible for passing those pairs to the repair operator.

Operators implemented
---------------------
D1 — Random Employee Days
    Pick q employees at random and remove ALL their currently-worked days,
    or remove a random subset of worked days per employee.

D2 — Worst Shortage Days
    Identify the N days with the highest total shortage and remove the
    assignments of every employee on those days.

D3 — Shift-Time Perturbation
    For employees whose marker allows any feasible block (i.e. NOT a fixed
    EQUALS marker), clear the chosen time window but record that the employee
    must still work — repair will re-choose the block.  Only the assignment
    is cleared; the "must work" flag is carried back via the returned pairs.

D4 — Skill Reallocation Only
    Keep all x_wdh (time assignments) fixed; only clear the skill_map entries
    y_wdts for a random subset of (employee, day) pairs.  Repair will
    re-allocate skills without changing who works when.
"""

from __future__ import annotations

import random
from typing import Dict, List, Set, Tuple

from .lns_solution import Assignment, CoverageTracker, Day, EmpId, Solution
from .lns_constraints import is_off_marker

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_skill_map(
    solution: Solution,
    emp_id:   EmpId,
    day:      Day,
    assignment: Assignment,
) -> Dict[int, str | None]:
    return {
        slot_idx: solution.skill_map.get((emp_id, day, slot_idx))
        for slot_idx in assignment.slot_indices
    }


def _remove(
    emp_id:   EmpId,
    day:      Day,
    solution: Solution,
    tracker:  CoverageTracker,
) -> Tuple[EmpId, Day, Assignment | None, Dict]:
    """
    Remove (emp_id, day) from the solution and revert its coverage.
    Returns a rollback tuple: (emp_id, day, old_assignment, old_skill_map).
    """
    old_asgn = solution.assignments.get((emp_id, day))
    if old_asgn is None:
        return (emp_id, day, None, {})

    old_skill_map = _extract_skill_map(solution, emp_id, day, old_asgn)
    tracker.revert(emp_id, day, old_asgn, old_skill_map)
    solution.clear_assignment(emp_id, day)
    return (emp_id, day, old_asgn, old_skill_map)


# ---------------------------------------------------------------------------
# D1 — Random Employee Days
# ---------------------------------------------------------------------------

def destroy_random_employees(
    solution:    Solution,
    tracker:     CoverageTracker,
    employees:   List[dict],
    days:        List[Day],
    markers:     Dict[Tuple[EmpId, Day], str],
    q_employees: int = 2,
    days_per_emp: float = 1.0,   # fraction of worked days to destroy per employee
    rng:         random.Random = random,
) -> Tuple[List[Tuple[EmpId, Day]], List]:
    """
    Randomly select q_employees and remove a fraction of their worked days.

    Returns
    -------
    destroyed   : list of (emp_id, day) pairs that were removed
    rollback    : list of rollback tuples for revert()
    """
    all_ids = [e["id"] for e in employees]
    chosen_emps = rng.sample(all_ids, min(q_employees, len(all_ids)))

    destroyed  = []
    rollback   = []

    for emp_id in chosen_emps:
        worked = [
            d for d in days
            if solution.assignments.get((emp_id, d)) is not None
        ]
        if not worked:
            continue
        n_remove = max(1, int(len(worked) * days_per_emp))
        to_remove = rng.sample(worked, min(n_remove, len(worked)))

        for day in to_remove:
            rb = _remove(emp_id, day, solution, tracker)
            destroyed.append((emp_id, day))
            rollback.append(rb)

    return destroyed, rollback


# ---------------------------------------------------------------------------
# D2 — Worst Shortage Days
# ---------------------------------------------------------------------------

def destroy_worst_shortage_days(
    solution:  Solution,
    tracker:   CoverageTracker,
    employees: List[dict],
    days:      List[Day],
    n_days:    int = 3,
    rng:       random.Random = random,
) -> Tuple[List[Tuple[EmpId, Day]], List]:
    """
    Find the n_days days with the highest total shortage and remove all
    employee assignments on those days.
    """
    day_shortage = {day: tracker.shortage_on_day(day) for day in days}
    sorted_days  = sorted(day_shortage, key=day_shortage.get, reverse=True)
    target_days  = sorted_days[:n_days]

    # If all worst days have zero shortage, fall back to random days
    if all(day_shortage[d] == 0 for d in target_days):
        target_days = rng.sample(days, min(n_days, len(days)))

    destroyed = []
    rollback  = []

    for day in target_days:
        for emp in employees:
            emp_id = emp["id"]
            if solution.assignments.get((emp_id, day)) is not None:
                rb = _remove(emp_id, day, solution, tracker)
                destroyed.append((emp_id, day))
                rollback.append(rb)

    return destroyed, rollback


# ---------------------------------------------------------------------------
# D3 — Shift-Time Perturbation
# ---------------------------------------------------------------------------

def destroy_shift_time(
    solution:    Solution,
    tracker:     CoverageTracker,
    employees:   List[dict],
    days:        List[Day],
    markers:     Dict[Tuple[EmpId, Day], str],
    q_employees: int = 3,
    rng:         random.Random = random,
) -> Tuple[List[Tuple[EmpId, Day]], List]:
    """
    Clear the chosen time block for employees that have flexible markers
    (numeric contract hours, NOT EQUALS:…).  The employee is still expected
    to work — repair will select a different feasible block.

    Only (emp_id, day) pairs with a flexible marker are eligible.
    """
    candidates = []
    for emp in employees:
        emp_id = emp["id"]
        for day in days:
            asgn   = solution.assignments.get((emp_id, day))
            marker = markers.get((emp_id, day), "")
            if asgn is None:
                continue
            marker_up = marker.strip().upper()
            # Flexible = numeric hours (4, 5, 7, 8) — not EQUALS, not off
            if marker_up in {"4", "5", "7", "8"}:
                candidates.append((emp_id, day))

    chosen = rng.sample(candidates, min(q_employees, len(candidates)))

    destroyed = []
    rollback  = []

    for emp_id, day in chosen:
        rb = _remove(emp_id, day, solution, tracker)
        destroyed.append((emp_id, day))
        rollback.append(rb)

    return destroyed, rollback


# ---------------------------------------------------------------------------
# D4 — Skill Reallocation Only
# ---------------------------------------------------------------------------

def destroy_skill_only(
    solution:    Solution,
    tracker:     CoverageTracker,
    employees:   List[dict],
    days:        List[Day],
    q_pairs:     int = 5,
    rng:         random.Random = random,
) -> Tuple[List[Tuple[EmpId, Day]], List]:
    """
    Keep x_wdh fixed (which employee works which hours) but clear skill
    assignments y_wdts for a random subset of (employee, day) pairs.

    The returned 'destroyed' list marks these pairs as needing skill
    re-assignment only (assignment block is preserved).
    """
    candidates = [
        (emp["id"], day)
        for emp in employees
        for day in days
        if solution.assignments.get((emp["id"], day)) is not None
        and len(employees[0].get("assignable_skills", [])) > 1  # multi-skill only
    ]
    # Re-filter properly using the employees list
    candidates = []
    emp_map = {e["id"]: e for e in employees}
    for emp in employees:
        emp_id = emp["id"]
        if len(emp.get("assignable_skills", ())) < 2:
            continue  # single-skill employee — nothing to reallocate
        for day in days:
            if solution.assignments.get((emp_id, day)) is not None:
                candidates.append((emp_id, day))

    chosen = rng.sample(candidates, min(q_pairs, len(candidates)))

    destroyed = []
    rollback  = []

    for emp_id, day in chosen:
        asgn = solution.assignments.get((emp_id, day))
        if asgn is None:
            continue
        # Revert only the skill contributions (not the assignment itself)
        old_skill_map = _extract_skill_map(solution, emp_id, day, asgn)

        # Remove skill-specific coverage (staff-level stays — employee still works)
        for slot_idx in asgn.slot_indices:
            skill = old_skill_map.get(slot_idx)
            if skill and skill != tracker.STAFF_TEAM:
                skill_key = (day, slot_idx, skill)
                if skill_key in tracker.coverage:
                    tracker.coverage[skill_key] = max(0, tracker.coverage[skill_key] - 1)
            # Clear from solution skill_map
            solution.skill_map.pop((emp_id, day, slot_idx), None)

        destroyed.append((emp_id, day))
        rollback.append((emp_id, day, asgn, old_skill_map, "skill_only"))

    return destroyed, rollback


# ---------------------------------------------------------------------------
# Rollback utility (called when the new solution is rejected)
# ---------------------------------------------------------------------------

def rollback_destroy(
    rollback:  List,
    solution:  Solution,
    tracker:   CoverageTracker,
):
    """
    Restore the solution and coverage to the state before a destroy+repair
    cycle, given the rollback list returned by a destroy operator.
    """
    for entry in rollback:
        if len(entry) == 5 and entry[4] == "skill_only":
            # D4 rollback: restore skill assignments only
            emp_id, day, asgn, old_skill_map, _ = entry
            for slot_idx, skill in old_skill_map.items():
                solution.skill_map[(emp_id, day, slot_idx)] = skill
                if skill and skill != tracker.STAFF_TEAM:
                    skill_key = (day, slot_idx, skill)
                    if skill_key in tracker.coverage:
                        tracker.coverage[skill_key] += 1
        else:
            emp_id, day, old_asgn, old_skill_map = entry
            if old_asgn is None:
                continue
            # Restore assignment
            solution.set_assignment(emp_id, day, old_asgn, old_skill_map)
            # Restore coverage
            tracker.apply(emp_id, day, old_asgn, old_skill_map)

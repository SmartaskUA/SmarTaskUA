"""
lns_repair.py
-------------
Repair operators para o LNS scheduler.

Dois modos de repair, seleccionáveis por parâmetro mode=:

  "greedy"  — repair greedy slot-a-slot (O(k·slots), rápido, sub-óptimo)
  "ilp"     — sub-problema ILP exacto com PuLP/CBC (óptimo no neighbourhood
               destruído, mais lento mas melhor qualidade por iteração)

No modo ILP
-----------
  - As variáveis x_wdh e y_wdts dos pares NÃO destruídos são fixadas ao
    valor actual da solução (lb = ub = valor corrente).
  - Apenas as variáveis dos pares destruídos ficam livres (binárias normais).
  - O sub-problema resultante tem tipicamente < 500 variáveis livres para
    2-5 employees × 31 dias e resolve em < ilp_time_limit segundos.
  - Fallback automático para greedy se o CBC não encontrar solução feasível.

Atribuição de skills
--------------------
Hierarquia de prioridade: Management (1) > Checkout (2) > Storage (3) > Employees (4)
Resource allocation rule: não atribuir skill de menor prioridade se existir
skill de maior prioridade com shortage > 0.

Exports
-------
  repair()                        — interface unificada (greedy ou ILP)
  repair_greedy()                 — repair greedy puro
  repair_ilp_subproblem()         — sub-problema ILP exacto
  assign_skills_greedy()          — atribuição de skills slot-a-slot
  build_greedy_initial_solution() — solução inicial greedy
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import pulp

from .lns_solution import Assignment, CoverageTracker, Day, EmpId, Solution
from .lns_constraints import (
    MIN_REST_HOURS_DEFAULT,
    is_feasible,
    is_off_marker,
)

DEFAULT_PRIORITY: Dict[str, int] = {
    "Management": 1,
    "Checkout":   2,
    "Storage":    3,
    "Employees":  4,
}

STAFF_TEAM = "Employees"


# ---------------------------------------------------------------------------
# Atribuição de skills greedy
# ---------------------------------------------------------------------------

def assign_skills_greedy(
    emp_id:     EmpId,
    day:        Day,
    assignment: Assignment,
    emp_skills: Tuple[str, ...],
    tracker:    CoverageTracker,
    alpha:      Dict[Tuple[Day, int, str], int],
    priority:   Dict[str, int] = DEFAULT_PRIORITY,
) -> Dict[int, Optional[str]]:
    """
    Para cada slot coberto pelo assignment escolhe a skill com maior shortage,
    aplicando a resource allocation rule (prioridade de tasks).
    Mantém shadow de cobertura local para consistência intra-assignment.
    """
    skill_map: Dict[int, Optional[str]] = {}
    local_cov: Dict[Tuple[Day, int, str], int] = {}

    for slot_idx in assignment.slot_indices:
        shortages = {}
        for skill in emp_skills:
            key = (day, slot_idx, skill)
            if key not in alpha:
                shortages[skill] = 0
                continue
            cov = tracker.coverage.get(key, 0) + local_cov.get(key, 0)
            shortages[skill] = max(0, alpha[key] - cov)

        # Resource allocation rule
        min_prio_with_shortage = None
        for skill, sh in shortages.items():
            if sh > 0:
                p = priority.get(skill, 99)
                if min_prio_with_shortage is None or p < min_prio_with_shortage:
                    min_prio_with_shortage = p

        if min_prio_with_shortage is not None:
            eligible = [s for s in emp_skills
                        if priority.get(s, 99) <= min_prio_with_shortage]
            chosen = max(eligible,
                         key=lambda s: (shortages.get(s, 0), -priority.get(s, 99)))
        else:
            chosen = min(emp_skills, key=lambda s: priority.get(s, 99))

        skill_map[slot_idx] = chosen
        key = (day, slot_idx, chosen)
        local_cov[key] = local_cov.get(key, 0) + 1

    return skill_map


# ---------------------------------------------------------------------------
# Repair greedy
# ---------------------------------------------------------------------------

def repair_greedy(
    destroyed:      List[Tuple[EmpId, Day]],
    solution:       Solution,
    tracker:        CoverageTracker,
    employees:      List[dict],
    days:           List[Day],
    assignments_by: Dict[Tuple[EmpId, Day], List[Assignment]],
    markers:        Dict[Tuple[EmpId, Day], str],
    alpha:          Dict[Tuple[Day, int, str], int],
    priority:       Dict[str, int] = DEFAULT_PRIORITY,
    min_rest_hours: float = MIN_REST_HOURS_DEFAULT,
    skill_only_set: Set[Tuple[EmpId, Day]] = None,
):
    """Re-atribui cada (emp_id, day) destruído de forma greedy."""
    if skill_only_set is None:
        skill_only_set = set()

    emp_map = {e["id"]: e for e in employees}

    for emp_id, day in sorted(destroyed,
                              key=lambda p: -tracker.shortage_on_day(p[1])):
        emp        = emp_map.get(emp_id)
        if emp is None:
            continue
        marker     = markers.get((emp_id, day), "")
        emp_skills = emp.get("assignable_skills", ())

        # D4: só realocar skills, manter assignment
        if (emp_id, day) in skill_only_set:
            asgn = solution.assignments.get((emp_id, day))
            if asgn is None:
                continue
            skill_map = assign_skills_greedy(
                emp_id, day, asgn, emp_skills, tracker, alpha, priority)
            for slot_idx, skill in skill_map.items():
                solution.skill_map[(emp_id, day, slot_idx)] = skill
                if skill and skill != STAFF_TEAM:
                    key = (day, slot_idx, skill)
                    if key in tracker.coverage:
                        tracker.coverage[key] += 1
            continue

        if is_off_marker(marker):
            continue

        feasible = [a for a in assignments_by.get((emp_id, day), [])
                    if is_feasible(emp_id, day, a, marker,
                                   solution, days, min_rest_hours)]
        if not feasible:
            continue

        best_block, best_skill_map, best_delta = None, None, 0
        for block in feasible:
            sk    = assign_skills_greedy(emp_id, day, block, emp_skills,
                                         tracker, alpha, priority)
            delta = tracker.delta_if_applied(emp_id, day, block, sk)
            if best_block is None or delta < best_delta:
                best_delta, best_block, best_skill_map = delta, block, sk

        solution.set_assignment(emp_id, day, best_block, best_skill_map)
        tracker.apply(emp_id, day, best_block, best_skill_map)


# ---------------------------------------------------------------------------
# Repair ILP — sub-problema exacto com PuLP/CBC
# ---------------------------------------------------------------------------

def repair_ilp_subproblem(
    destroyed:      List[Tuple[EmpId, Day]],
    solution:       Solution,
    tracker:        CoverageTracker,
    employees:      List[dict],
    days:           List[Day],
    assignments_by: Dict[Tuple[EmpId, Day], List[Assignment]],
    markers:        Dict[Tuple[EmpId, Day], str],
    alpha:          Dict[Tuple[Day, int, str], int],
    time_slots:     list,
    priority:       Dict[str, int] = DEFAULT_PRIORITY,
    min_rest_hours: float = MIN_REST_HOURS_DEFAULT,
    ilp_time_limit: int   = 5,
    skill_only_set: Set[Tuple[EmpId, Day]] = None,
):
    """
    Resolve o sub-problema de repair com ILP exacto (PuLP/CBC).

    Pares NÃO destruídos: x e y fixados ao valor actual da solução.
    Pares destruídos: x e y livres → optimizados pelo CBC.

    Após resolução, actualiza solution + tracker apenas nos pares destruídos.
    Fallback para repair_greedy se o CBC não encontrar solução.
    """
    if skill_only_set is None:
        skill_only_set = set()

    destroyed_set = set(destroyed)
    emp_map       = {e["id"]: e for e in employees}
    day_index     = {d: i for i, d in enumerate(days)}

    model    = pulp.LpProblem("LNS_SubProblem", pulp.LpMinimize)
    x        = {}
    y        = {}
    shortage = {}

    # ------------------------------------------------------------------
    # Variáveis x — pares destruídos com blocks feasíveis
    # ------------------------------------------------------------------
    for emp_id, day in destroyed_set:
        if (emp_id, day) in skill_only_set:
            continue
        marker = markers.get((emp_id, day), "")
        if is_off_marker(marker):
            continue
        for asgn in assignments_by.get((emp_id, day), []):
            if is_feasible(emp_id, day, asgn, marker,
                           solution, days, min_rest_hours):
                x[(emp_id, day, asgn.key)] = pulp.LpVariable(
                    f"x_{emp_id}_{day.replace('-','')}_{asgn.start_min}_{asgn.end_min}",
                    cat="Binary")

    # ------------------------------------------------------------------
    # Variáveis y — pares destruídos
    # ------------------------------------------------------------------
    for emp_id, day in destroyed_set:
        emp        = emp_map.get(emp_id)
        emp_skills = emp.get("assignable_skills", ()) if emp else ()

        if (emp_id, day) in skill_only_set:
            asgn = solution.assignments.get((emp_id, day))
            slots = list(asgn.slot_indices) if asgn else []
        else:
            slots = list({s
                          for asgn in assignments_by.get((emp_id, day), [])
                          if is_feasible(emp_id, day, asgn,
                                         markers.get((emp_id, day), ""),
                                         solution, days, min_rest_hours)
                          for s in asgn.slot_indices})

        for slot_idx in slots:
            for skill in emp_skills:
                y[(emp_id, day, slot_idx, skill)] = pulp.LpVariable(
                    f"y_{emp_id}_{day.replace('-','')}_{slot_idx}_{skill}",
                    cat="Binary")

    # ------------------------------------------------------------------
    # Variáveis de shortage — slots afectados pelos pares destruídos
    # ------------------------------------------------------------------
    affected: Set[Tuple[Day, int, str]] = set()
    for emp_id, day in destroyed_set:
        emp_skills = emp_map.get(emp_id, {}).get("assignable_skills", ())
        all_slots  = {s for asgn in assignments_by.get((emp_id, day), [])
                      for s in asgn.slot_indices}
        for s in all_slots:
            for skill in [STAFF_TEAM] + list(emp_skills):
                if (day, s, skill) in alpha:
                    affected.add((day, s, skill))

    for key in affected:
        d, s, sk = key
        shortage[key] = pulp.LpVariable(
            f"z_{d.replace('-','')}_{s}_{sk}",
            lowBound=0, cat="Integer")

    # ------------------------------------------------------------------
    # Constraint (2): exactamente 1 block por par destruído activo
    # ------------------------------------------------------------------
    for emp_id, day in destroyed_set:
        if (emp_id, day) in skill_only_set:
            continue
        marker = markers.get((emp_id, day), "")
        x_vars = [x[(emp_id, day, asgn.key)]
                  for asgn in assignments_by.get((emp_id, day), [])
                  if (emp_id, day, asgn.key) in x]
        if not x_vars:
            continue
        if is_off_marker(marker):
            model += pulp.lpSum(x_vars) == 0
        else:
            model += pulp.lpSum(x_vars) == 1, f"c2_{emp_id}_{day}"

    # ------------------------------------------------------------------
    # Constraint (3): skill coverage ↔ assignment coverage
    # ------------------------------------------------------------------
    for emp_id, day in destroyed_set:
        emp        = emp_map.get(emp_id)
        emp_skills = emp.get("assignable_skills", ()) if emp else ()

        if (emp_id, day) in skill_only_set:
            asgn = solution.assignments.get((emp_id, day))
            if asgn is None:
                continue
            for slot_idx in asgn.slot_indices:
                lhs = [y[(emp_id, day, slot_idx, sk)]
                       for sk in emp_skills
                       if (emp_id, day, slot_idx, sk) in y]
                if lhs:
                    model += pulp.lpSum(lhs) == 1, \
                        f"c3fix_{emp_id}_{day.replace('-','')}_{slot_idx}"
        else:
            all_slots = {s for asgn in assignments_by.get((emp_id, day), [])
                         for s in asgn.slot_indices}
            for slot_idx in all_slots:
                lhs = [y[(emp_id, day, slot_idx, sk)]
                       for sk in emp_skills
                       if (emp_id, day, slot_idx, sk) in y]
                rhs = [x[(emp_id, day, asgn.key)]
                       for asgn in assignments_by.get((emp_id, day), [])
                       if (emp_id, day, asgn.key) in x
                       and slot_idx in asgn.slot_indices]
                model += pulp.lpSum(lhs) == pulp.lpSum(rhs), \
                    f"c3_{emp_id}_{day.replace('-','')}_{slot_idx}"

    # ------------------------------------------------------------------
    # Constraint de rest mínimo entre dias consecutivos
    # ------------------------------------------------------------------
    for emp_id, day in destroyed_set:
        idx = day_index.get(day, -1)
        if idx <= 0:
            continue
        prev_day  = days[idx - 1]
        prev_asgn = solution.assignments.get((emp_id, prev_day))
        if prev_asgn is None:
            continue
        for cur_asgn in assignments_by.get((emp_id, day), []):
            if (emp_id, day, cur_asgn.key) not in x:
                continue
            rest = (24 * 60 - prev_asgn.end_min + cur_asgn.start_min) / 60.0
            if rest < min_rest_hours:
                model += x[(emp_id, day, cur_asgn.key)] == 0, \
                    f"rest_{emp_id}_{day}_{cur_asgn.key}"

        if idx < len(days) - 1:
            next_day  = days[idx + 1]
            next_asgn = solution.assignments.get((emp_id, next_day))
            if next_asgn is None:
                continue
            for cur_asgn in assignments_by.get((emp_id, day), []):
                if (emp_id, day, cur_asgn.key) not in x:
                    continue
                rest = (24 * 60 - cur_asgn.end_min + next_asgn.start_min) / 60.0
                if rest < min_rest_hours:
                    model += x[(emp_id, day, cur_asgn.key)] == 0, \
                        f"rest_next_{emp_id}_{day}_{cur_asgn.key}"

    # ------------------------------------------------------------------
    # Constraint (5): shortage ≥ alpha − cobertura fixada − cobertura livre
    # ------------------------------------------------------------------
    for (day, slot_idx, skill), minimum in alpha.items():
        if (day, slot_idx, skill) not in shortage:
            continue

        # Cobertura dos pares não destruídos (lida do tracker actual)
        fixed_cov = tracker.coverage.get((day, slot_idx, skill), 0)

        free_terms = []
        if skill == STAFF_TEAM:
            for emp_id, d in destroyed_set:
                if d != day:
                    continue
                for asgn in assignments_by.get((emp_id, day), []):
                    if (emp_id, day, asgn.key) in x and slot_idx in asgn.slot_indices:
                        free_terms.append(x[(emp_id, day, asgn.key)])
        else:
            for emp_id, d in destroyed_set:
                if d != day:
                    continue
                key = (emp_id, day, slot_idx, skill)
                if key in y:
                    free_terms.append(y[key])

        model += (
            shortage[(day, slot_idx, skill)] + fixed_cov + pulp.lpSum(free_terms)
            >= minimum,
            f"c5_{day}_{slot_idx}_{skill}"
        )

    # ------------------------------------------------------------------
    # Objectivo: minimizar shortage total nos slots afectados
    # ------------------------------------------------------------------
    model += pulp.lpSum(shortage.values()), "obj"

    # ------------------------------------------------------------------
    # Resolver com CBC
    # ------------------------------------------------------------------
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=ilp_time_limit, gapRel=0.0)
    model.solve(solver)

    if model.status not in (1, -1):   # 1=Optimal, -1=Not Solved (feasible found)
        # Fallback greedy se CBC falhou completamente
        repair_greedy(destroyed, solution, tracker, employees, days,
                      assignments_by, markers, alpha, priority,
                      min_rest_hours, skill_only_set)
        return

    # ------------------------------------------------------------------
    # Aplicar solução ILP → Solution + CoverageTracker
    # ------------------------------------------------------------------
    for emp_id, day in destroyed_set:
        emp        = emp_map.get(emp_id)
        emp_skills = emp.get("assignable_skills", ()) if emp else ()

        if (emp_id, day) in skill_only_set:
            asgn = solution.assignments.get((emp_id, day))
            if asgn is None:
                continue
            new_skill_map = {}
            for slot_idx in asgn.slot_indices:
                chosen = next(
                    (sk for sk in emp_skills
                     if (emp_id, day, slot_idx, sk) in y
                     and (pulp.value(y[(emp_id, day, slot_idx, sk)]) or 0) > 0.5),
                    min(emp_skills, key=lambda s: priority.get(s, 99))
                    if emp_skills else None
                )
                new_skill_map[slot_idx] = chosen
            solution.set_assignment(emp_id, day, asgn, new_skill_map)
            tracker.apply(emp_id, day, asgn, new_skill_map)
            continue

        chosen_asgn = next(
            (asgn for asgn in assignments_by.get((emp_id, day), [])
             if (emp_id, day, asgn.key) in x
             and (pulp.value(x[(emp_id, day, asgn.key)]) or 0) > 0.5),
            None
        )
        if chosen_asgn is None:
            continue

        new_skill_map = {}
        for slot_idx in chosen_asgn.slot_indices:
            chosen_skill = next(
                (sk for sk in emp_skills
                 if (emp_id, day, slot_idx, sk) in y
                 and (pulp.value(y[(emp_id, day, slot_idx, sk)]) or 0) > 0.5),
                min(emp_skills, key=lambda s: priority.get(s, 99))
                if emp_skills else None
            )
            new_skill_map[slot_idx] = chosen_skill

        solution.set_assignment(emp_id, day, chosen_asgn, new_skill_map)
        tracker.apply(emp_id, day, chosen_asgn, new_skill_map)


# ---------------------------------------------------------------------------
# Interface unificada
# ---------------------------------------------------------------------------

def repair(
    destroyed:      List[Tuple[EmpId, Day]],
    solution:       Solution,
    tracker:        CoverageTracker,
    employees:      List[dict],
    days:           List[Day],
    assignments_by: Dict[Tuple[EmpId, Day], List[Assignment]],
    markers:        Dict[Tuple[EmpId, Day], str],
    alpha:          Dict[Tuple[Day, int, str], int],
    time_slots:     list = None,
    priority:       Dict[str, int] = DEFAULT_PRIORITY,
    min_rest_hours: float = MIN_REST_HOURS_DEFAULT,
    skill_only_set: Set[Tuple[EmpId, Day]] = None,
    mode:           str = "greedy",
    ilp_time_limit: int = 5,
):
    """
    Despacha para repair_greedy (mode='greedy') ou repair_ilp_subproblem (mode='ilp').

    mode='greedy' : rápido (~ms por iteração), centenas de iterações/min
    mode='ilp'    : óptimo no neighbourhood (~segundos), 10-30 iterações/min
    """
    if mode == "ilp":
        repair_ilp_subproblem(
            destroyed=destroyed, solution=solution, tracker=tracker,
            employees=employees, days=days, assignments_by=assignments_by,
            markers=markers, alpha=alpha, time_slots=time_slots or [],
            priority=priority, min_rest_hours=min_rest_hours,
            ilp_time_limit=ilp_time_limit, skill_only_set=skill_only_set,
        )
    else:
        repair_greedy(
            destroyed=destroyed, solution=solution, tracker=tracker,
            employees=employees, days=days, assignments_by=assignments_by,
            markers=markers, alpha=alpha, priority=priority,
            min_rest_hours=min_rest_hours, skill_only_set=skill_only_set,
        )


# ---------------------------------------------------------------------------
# Solução inicial greedy
# ---------------------------------------------------------------------------

def build_greedy_initial_solution(
    employees:      List[dict],
    days:           List[Day],
    assignments_by: Dict[Tuple[EmpId, Day], List[Assignment]],
    markers:        Dict[Tuple[EmpId, Day], str],
    alpha:          Dict[Tuple[Day, int, str], int],
    priority:       Dict[str, int] = DEFAULT_PRIORITY,
    min_rest_hours: float = MIN_REST_HOURS_DEFAULT,
) -> Tuple[Solution, CoverageTracker]:
    """Constrói solução inicial feasível de forma greedy (dia-a-dia)."""
    solution = Solution()
    tracker  = CoverageTracker(alpha, employees)
    for emp in employees:
        for day in days:
            solution.assignments[(emp["id"], day)] = None

    for day in days:
        ordered = sorted(employees,
                         key=lambda e: (-len(e.get("assignable_skills", ())), e["id"]))
        for emp in ordered:
            emp_id     = emp["id"]
            marker     = markers.get((emp_id, day), "")
            emp_skills = emp.get("assignable_skills", ())
            if is_off_marker(marker):
                continue
            feasible = [a for a in assignments_by.get((emp_id, day), [])
                        if is_feasible(emp_id, day, a, marker,
                                       solution, days, min_rest_hours)]
            if not feasible:
                continue
            best_block, best_skill_map, best_delta = None, None, 1
            for block in feasible:
                sk    = assign_skills_greedy(emp_id, day, block, emp_skills,
                                              tracker, alpha, priority)
                delta = tracker.delta_if_applied(emp_id, day, block, sk)
                if best_block is None or delta < best_delta:
                    best_delta, best_block, best_skill_map = delta, block, sk
            solution.set_assignment(emp_id, day, best_block, best_skill_map)
            tracker.apply(emp_id, day, best_block, best_skill_map)

    return solution, tracker
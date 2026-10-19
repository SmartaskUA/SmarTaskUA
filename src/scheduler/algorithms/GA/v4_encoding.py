"""GA encoding of a V4Instance: one gene per employee-day, frozen where nothing is left to choose.

A gene is an index into a global table of shift intervals (0 = rest). Each cell
may only take the genes its candidate set allows, so a work cell never rests,
a rest cell never works, and a partial result's day - whose candidate set is
the one shift it names - is simply a cell with one allowed gene: frozen. That
is all partial resolution costs the GA; crossover by days keeps frozen cells
because every individual carries the same value there.

Fitness is MathematicalDefinition7's objective, computed per day (a day's
coverage depends only on that day's column of genes) and cached by column.
The per-slot skill routing follows the MD7 link: a worker on shift in slot t
takes exactly one demanded value on every axis where it holds one; values are
filled in priority order, leftover workers take their cheapest demanded value.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from algorithms.md7_index import MD7Index
from problem_v4 import (
    UNASSIGNED,
    SolveDirectives,
    V4Instance,
    format_worked_cell,
    rest_cell,
)
from problem_v4.schema_core import MINUTES_PER_DAY

#: Weight of one hard-rule violation the repair could not remove.
HARD_PENALTY = 10 ** 6


class DayAxis:
    """Demand and holders for one (day, axis): the arrays the decoder reads."""

    def __init__(self, skills: List[str], need: np.ndarray, held: np.ndarray, weight: np.ndarray):
        self.skills = skills        # values on the axis demanded that day, in priority order
        self.need = need            # (V, T) alpha
        self.held = held            # (E, V) bool
        self.weight = weight        # (E, V) p_sl for the worker's level (0 where not held)
        self.slots = np.flatnonzero(need.sum(axis=0) > 0)
        # Uniform: every worker holds every value at the same p_sl, so a closed
        # form gives the greedy's result without routing worker by worker.
        self.uniform = bool(held.all()) and bool((weight == weight[:1]).all())
        demanded = need[:, self.slots] > 0
        per_value = weight[0][:, None] if len(weight) else np.zeros((len(skills), 1))
        self.cheapest = np.where(demanded, per_value, np.iinfo(np.int64).max).min(axis=0) if len(skills) else None


class V4Encoding:
    def __init__(self, inst: V4Instance, directives: Optional[SolveDirectives] = None):
        self.inst = inst
        self.directives = directives or SolveDirectives()
        self.index = MD7Index(inst, self.directives)
        employees, days = inst.employees, inst.days
        self.n_emp, self.n_days = len(employees), len(days)
        slot = inst.slot_minutes
        n_slots = len(inst.time_slots)

        # Global shift table; gene 0 is rest.
        intervals = sorted({(s.start_min, s.end_min) for shifts in inst.candidates.values() for s in shifts})
        gene_of = {iv: i + 1 for i, iv in enumerate(intervals)}
        self.start = np.array([0] + [a for a, _ in intervals], dtype=np.int64)
        self.end = np.array([0] + [b for _, b in intervals], dtype=np.int64)
        self.cover = np.zeros((len(intervals) + 1, n_slots), dtype=bool)
        for (a, b), gene in gene_of.items():
            self.cover[gene, a // slot:b // slot] = True

        # Per-cell domains and the Shift each gene stands for there.
        self.domain: List[List[np.ndarray]] = []
        self.shift_of: Dict[Tuple[int, int, int], object] = {}
        self.frozen = np.zeros((self.n_emp, self.n_days), dtype=bool)
        self.may_rest = np.zeros((self.n_emp, self.n_days), dtype=bool)
        for e, employee in enumerate(employees):
            row = []
            for d, day in enumerate(days):
                genes = []
                for shift in inst.candidates[(employee.id, day)]:
                    gene = gene_of[(shift.start_min, shift.end_min)]
                    genes.append(gene)
                    self.shift_of[(e, d, gene)] = shift
                if self.index.day_rule(employee.id, day) != 1:
                    genes.insert(0, 0)
                    self.may_rest[e, d] = True
                row.append(np.array(genes, dtype=np.int64))
                self.frozen[e, d] = len(genes) == 1
            self.domain.append(row)
        self.day_off = np.array([[inst.day_modes[(e.id, d)] == "preferred_day_off" for d in days]
                                 for e in employees], dtype=bool)

        # Demand and holders per (day, axis), values in priority order.
        rank = {tier["skill"]: tier["priority"] for tier in inst.priority_tiers}
        self.day_axes: List[List[DayAxis]] = []
        for day in days:
            per_axis: Dict[str, List[str]] = defaultdict(list)
            for skill in inst.skills:
                if any(inst.alpha.get((day, t, skill), 0) > 0 for t in range(n_slots)):
                    per_axis[inst.skill_axis[skill]].append(skill)
            axes = []
            for axis, skills in per_axis.items():
                skills = sorted(skills, key=lambda s: (rank.get(s, len(rank) + 1), inst.skills.index(s)))
                need = np.array([[inst.alpha.get((day, t, s), 0) for t in range(n_slots)] for s in skills],
                                dtype=np.int64)
                held = np.array([[s in e.skills[day] for s in skills] for e in employees], dtype=bool)
                weight = np.array([[inst.priority_weight(s, e.skills[day][s]) if s in e.skills[day] else 0
                                    for s in skills] for e in employees], dtype=np.int64)
                axes.append(DayAxis(skills, need, held, weight))
            self.day_axes.append(axes)

        self._cache: Dict[Tuple[int, bytes], Tuple[int, int]] = {}
        self._run_windows = [(employees.index(inst.employee(eid)), [days.index(d) for d in window], n)
                             for eid, _, window, n in self.index.run_windows]
        self._week_caps = [(employees.index(inst.employee(eid)), [days.index(d) for d in week], cap)
                           for eid, _, week, cap in self.index.week_caps]
        self._swap_weeks = ([(employees.index(inst.employee(eid)), [days.index(d) for d in week], required)
                             for eid, _, week, required in self.index.swap_weeks()]
                            if self.directives.allow_day_off_swap else [])

    # ------------------------------------------------------------------
    # individuals
    # ------------------------------------------------------------------

    def random_genes(self, rng: np.random.Generator) -> np.ndarray:
        genes = np.zeros((self.n_emp, self.n_days), dtype=np.int64)
        for e in range(self.n_emp):
            for d in range(self.n_days):
                options = self.domain[e][d]
                genes[e, d] = options[rng.integers(len(options))]
        return genes

    # ------------------------------------------------------------------
    # decoding one day
    # ------------------------------------------------------------------

    def decode_day(self, d: int, column: np.ndarray, routing: bool = False):
        """(shortage, p_sl cost) of one day's genes; with `routing`, also {(e, t): [skills]}."""
        present = self.cover[column]                      # (E, T)
        shortage, cost = 0, 0
        skills_at: Dict[Tuple[int, int], List[str]] = defaultdict(list)
        for axis in self.day_axes[d]:
            if axis.uniform and not routing:
                remaining = present[:, axis.slots].sum(axis=0)
                for v in range(len(axis.skills)):
                    need = axis.need[v, axis.slots]
                    taken = np.minimum(need, remaining)
                    shortage += int((need - taken).sum())
                    cost += int(taken.sum()) * int(axis.weight[0, v])
                    remaining = remaining - taken
                cost += int((remaining * axis.cheapest).sum())
                continue
            for t in axis.slots:
                demanded = axis.need[:, t] > 0
                workers = [e for e in np.flatnonzero(present[:, t]) if (axis.held[e] & demanded).any()]
                need = axis.need[:, t].copy()
                taken: Dict[int, int] = {}
                by_flexibility = sorted(workers, key=lambda e: (int((axis.held[e] & demanded).sum()), e))
                for v in range(len(axis.skills)):
                    for e in by_flexibility:
                        if need[v] <= 0:
                            break
                        if e not in taken and axis.held[e, v]:
                            taken[e] = v
                            need[v] -= 1
                for e in workers:
                    if e not in taken:
                        options = [v for v in range(len(axis.skills)) if axis.held[e, v] and demanded[v]]
                        taken[e] = min(options, key=lambda v: axis.weight[e, v])
                shortage += int(np.maximum(need, 0).sum())
                for e, v in taken.items():
                    cost += int(axis.weight[e, v])
                    if routing:
                        skills_at[(e, int(t))].append(axis.skills[v])
        return (shortage, cost, skills_at) if routing else (shortage, cost)

    def day_score(self, d: int, column: np.ndarray) -> Tuple[int, int]:
        key = (d, column.tobytes())
        score = self._cache.get(key)
        if score is None:
            if len(self._cache) > 500_000:
                self._cache.clear()
            score = self._cache[key] = self.decode_day(d, column)
        return score

    # ------------------------------------------------------------------
    # fitness and repair
    # ------------------------------------------------------------------

    def violations(self, genes: np.ndarray) -> int:
        worked = genes > 0
        count = 0
        min_rest = self.inst.legislation.min_rest_minutes
        if min_rest and self.n_days > 1:
            both = worked[:, :-1] & worked[:, 1:]
            rest = MINUTES_PER_DAY - self.end[genes[:, :-1]] + self.start[genes[:, 1:]]
            count += int((both & (rest < min_rest)).sum())
        for e, window, n in self._run_windows:
            count += max(0, int(worked[e, window].sum()) - n)
        for e, week, cap in self._week_caps:
            count += max(0, int(worked[e, week].sum()) - cap)
        for e, week, required in self._swap_weeks:
            count += abs(int(worked[e, week].sum()) - required)
        return count

    def components(self, genes: np.ndarray) -> Dict[str, int]:
        shortage = cost = 0
        for d in range(self.n_days):
            s, c = self.day_score(d, genes[:, d])
            shortage += s
            cost += c
        return {"shortage": shortage, "priority_cost": cost,
                "day_off_worked": int(((genes > 0) & self.day_off).sum()),
                "violations": self.violations(genes)}

    def fitness(self, genes: np.ndarray) -> float:
        parts = self.components(genes)
        w = self.directives
        return -float(w.w1 * parts["shortage"] + w.w2 * parts["priority_cost"]
                      + w.w3 * parts["day_off_worked"] + HARD_PENALTY * parts["violations"])

    def repair_rest(self, genes: np.ndarray, rng: np.random.Generator) -> None:
        """Lamarckian: re-pick the non-frozen side of any pair closer than the minimum rest."""
        min_rest = self.inst.legislation.min_rest_minutes
        if not min_rest:
            return
        for e in range(self.n_emp):
            for d in range(self.n_days - 1):
                if not self._conflict(genes, e, d, min_rest):
                    continue
                for day in (d + 1, d):
                    if self.frozen[e, day]:
                        continue
                    options = [g for g in self.domain[e][day] if self._fits(genes, e, day, g, min_rest)]
                    if options:
                        genes[e, day] = options[rng.integers(len(options))]
                        break

    def _conflict(self, genes, e, d, min_rest) -> bool:
        a, b = genes[e, d], genes[e, d + 1]
        return a > 0 and b > 0 and MINUTES_PER_DAY - self.end[a] + self.start[b] < min_rest

    def _fits(self, genes, e, day, gene, min_rest) -> bool:
        if gene == 0:
            return True
        if day > 0 and genes[e, day - 1] > 0 and \
                MINUTES_PER_DAY - self.end[genes[e, day - 1]] + self.start[gene] < min_rest:
            return False
        if day + 1 < self.n_days and genes[e, day + 1] > 0 and \
                MINUTES_PER_DAY - self.end[gene] + self.start[genes[e, day + 1]] < min_rest:
            return False
        return True

    # ------------------------------------------------------------------
    # output
    # ------------------------------------------------------------------

    def rows(self, genes: np.ndarray) -> List[List[str]]:
        inst = self.inst
        order = {skill: i for i, skill in enumerate(inst.skills)}
        routed = [self.decode_day(d, genes[:, d], routing=True)[2] for d in range(self.n_days)]
        out = [["employee_id", *inst.days]]
        for e, employee in enumerate(inst.employees):
            row = [employee.id]
            for d, day in enumerate(inst.days):
                gene = int(genes[e, d])
                if gene == 0:
                    if not self.may_rest[e, d]:
                        row.append(UNASSIGNED)
                    elif inst.day_modes[(employee.id, day)] in {"work_template", "fixed_time_work"}:
                        row.append("OFF")
                    else:
                        row.append(rest_cell(inst, employee.id, day))
                    continue
                shift = self.shift_of[(e, d, gene)]
                slot_skills = {t: sorted(routed[d].get((e, t), []), key=order.get) for t in shift.slot_indices}
                row.append(format_worked_cell(shift, slot_skills, inst.slot_minutes))
            out.append(row)
        return out

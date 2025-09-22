import time
from collections import defaultdict

import numpy as np
import pandas as pd
import holidays as hl

from algorithm.utils import (
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
)

TIMEOUT = object()

class ConstraintSearchScheduler:
    """
    CSP-style scheduler with:
      - Phase 1: anytime branch-and-bound that MINIMIZES the number of unmet minimum slots,
                 using 'slack tokens' when a min slot has no feasible candidate.
      - Phase 2: greedy fill to take employees up to 223 days while respecting hard constraints.

    Representation:
      - Employees are 1-based externally. Internally we keep 0-based arrays and map back on export.
      - Assignment is stored both as:
          * emp_day_shift[emp_idx][day_idx] = shift_id (0 = OFF, 1..S)
          * coverage[(day, shift, team_id)] = count
      - Allowed teams per employee is a list of team_ids (supports any number of teams).
    """

    # ----------------------------- utils -----------------------------
    @staticmethod
    def _safe_int(x, default=None):
        try:
            s = str(x).strip()
            if s == "":
                return default
            return int(s)
        except Exception:
            return default

    # --- time helpers (monotonic + per-phase deadlines) ---
    @staticmethod
    def _now():
        return time.monotonic()

    @staticmethod
    def _deadline(secs):
        # None -> huge deadline
        return ConstraintSearchScheduler._now() + (secs if secs is not None else 10**9)

    @staticmethod
    def _time_left(deadline):
        return (deadline - ConstraintSearchScheduler._now()) > 0

    def __init__(self, vacations_rows, minimuns_rows, employees, maxTime=None, year=2025, shifts=2, debug=True):
        self.debug = bool(debug)
        self.year = int(year) if year is not None else 2025
        # External maxTime is in MINUTES; convert to seconds (can be None)
        self.total_time_sec = int(maxTime) * 60 if maxTime is not None else None
        self.shifts = int(shifts)  # 2 or 3

        if self.debug:
            print(f"[INIT] year={self.year}, shifts={self.shifts}, total_time_sec={self.total_time_sec}")

        # Calendar / dates
        self.dates = pd.date_range(start=f"{self.year}-01-01", end=f"{self.year}-12-31").to_list()
        self.num_days = len(self.dates)
        self.dias_ano, sundays_1based = build_calendar(self.year)
        self.sundays = set(sundays_1based)  # 1-based DOY

        # Holidays (PT) as 1-based DOY
        hol = hl.country_holidays("PT", years=[self.year])
        start_date = self.dates[0].date()
        self.holidays = {(d - start_date).days + 1 for d in hol}

        # Special days (Sundays + holidays) as 1-based DOY
        self.special_days = set(self.holidays) | set(self.sundays)

        if self.debug:
            print(f"[INIT] num_days={self.num_days}, #Sundays={len(self.sundays)}, #Holidays={len(self.holidays)}, #Special={len(self.special_days)}")

        # Employees
        self.n_emp = len(employees)
        self.emp_ids = [i + 1 for i in range(self.n_emp)]

        # Allowed teams per employee (list of team_ids)
        self.allowed_teams = []
        for idx, e in enumerate(employees):
            codes = [get_team_code(t) for t in e.get("teams", []) if t]
            ids = [get_team_id(c) for c in codes if c]
            if not ids:
                ids = [get_team_id("A")]  # default
            self.allowed_teams.append(ids)
            if self.debug:
                print(f"[INIT] Emp {idx+1} allowed_teams={ids}")

        # Vacations: convert to 0-based mask [n_emp, num_days]
        vacs_dict = rows_to_vac_dict(vacations_rows)  # {emp_id: [1-based days]}
        self.vac_mask = np.zeros((self.n_emp, self.num_days), dtype=bool)
        for emp_id, days in vacs_dict.items():
            i = emp_id - 1
            if 0 <= i < self.n_emp:
                for d in days:
                    if 1 <= d <= self.num_days:
                        self.vac_mask[i, d - 1] = True

        if self.debug:
            total_vac = int(self.vac_mask.sum())
            vac_by_emp = [int(self.vac_mask[i].sum()) for i in range(self.n_emp)]
            print(f"[INIT] total vacation marks={total_vac}, per-emp first10={vac_by_emp[:10]}")

        # Requirements
        mins_raw, ideals_raw = rows_to_req_dicts(minimuns_rows)  # keys: (day, shift, team_id)
        # Safe-cast and filter by horizon/shifts
        self.mins = {}
        self.ideals = {}
        for k, v in mins_raw.items():
            day, shift, team_id = k
            if 1 <= day <= self.num_days and 1 <= shift <= self.shifts:
                val = self._safe_int(v, default=None)
                if val is not None:
                    self.mins[(day, shift, team_id)] = val
        for k, v in ideals_raw.items():
            day, shift, team_id = k
            if 1 <= day <= self.num_days and 1 <= shift <= self.shifts:
                val = self._safe_int(v, default=None)
                if val is not None:
                    self.ideals[(day, shift, team_id)] = val

        if self.debug:
            print(f"[INIT] mins entries={len(self.mins)}, ideals entries={len(self.ideals)}")
            # show a few mins examples
            for idx, (k, v) in enumerate(self.mins.items()):
                if idx >= 5: break
                print(f"       mins sample #{idx+1}: key={k} -> {v}")

        # Derived: all (day, shift, team_id) appearing in mins/ideals
        self.all_teams = sorted({team for (_d, _s, team) in set(self.mins.keys()) | set(self.ideals.keys())})
        if not self.all_teams:
            # fallback: union of employee allowed teams
            self.all_teams = sorted({tid for ids in self.allowed_teams for tid in ids})
        if self.debug:
            print(f"[INIT] all_teams={self.all_teams}")

        # Core state (mutable during search)
        self.emp_day_shift = np.zeros((self.n_emp, self.num_days), dtype=int)  # 0=OFF, 1..shifts
        self.emp_workdays = np.zeros(self.n_emp, dtype=int)
        self.emp_special = np.zeros(self.n_emp, dtype=int)
        self.coverage = defaultdict(int)  # (day, shift, team_id) -> count
        self.emp_day_team = np.zeros((self.n_emp, self.num_days), dtype=int)  # store team_id per assignment

        # For best-incumbent snapshots (anytime)
        self.best_unmet = float("inf")
        self._best_remaining = None
        self.best_snapshot = None
        self.slack = defaultdict(int)  # (day, shift, team_id) -> slack units used

        # For export:
        self.assignment = defaultdict(list)  # 1-based emp_id -> [(day, shift, team_id)]
        self.vacs_1based = {i + 1: [d + 1 for d in np.where(self.vac_mask[i])[0]] for i in range(self.n_emp)}

    # ---------- helpers / checks ----------
    def _is_special(self, day1):
        """day1 is 1-based."""
        return day1 in self.special_days

    def _backward_order_ok(self, i, d0, s):
        """
        Forbid backward shift: if employee worked day d0-1 with shift s_prev, require s >= s_prev.
        And if day d0+1 already assigned with s_next, require s_next >= s.
        d0 is 0-based index.
        """
        # Previous
        if d0 - 1 >= 0:
            s_prev = self.emp_day_shift[i, d0 - 1]
            if s_prev > 0 and s < s_prev:
                if self.debug:
                    print(f"[ORDER] Emp {i+1} day {d0+1}: s={s} < prev({d0})={s_prev} -> reject")
                return False
        # Next (if already fixed)
        if d0 + 1 < self.num_days:
            s_next = self.emp_day_shift[i, d0 + 1]
            if s_next > 0 and s_next < s:
                if self.debug:
                    print(f"[ORDER] Emp {i+1} day {d0+1}: next({d0+2})={s_next} < s={s} -> reject")
                return False
        return True

    def _consecutive_ok_after_assign(self, i, d0):
        """
        Check the 6-day windows around d0 to ensure there is no window with >5 worked days.
        """
        worked = (self.emp_day_shift[i] > 0).astype(int)
        # Only windows touching d0 can change; limit checks
        start = max(0, d0 - 5)
        end = min(self.num_days - 1, d0 + 5)
        for a in range(start, min(end, self.num_days - 6) + 1):
            s = worked[a:a + 6].sum()
            if s > 5:
                if self.debug:
                    print(f"[CONSEC] Emp {i+1} window {a+1}-{a+6} sum={s} -> reject")
                return False
        return True

    def _can_assign(self, i, d0, s, team_id):
        """
        Feasibility for assigning employee i on 0-based day d0, shift s (1..S) in team_id.
        """
        if self.emp_day_shift[i, d0] != 0:
            if self.debug:
                print(f"[CAN] Emp {i+1} day {d0+1}: already assigned")
            return False

        if self.vac_mask[i, d0]:
            if self.debug:
                print(f"[CAN] Emp {i+1} day {d0+1}: vacation")
            return False

        if team_id not in self.allowed_teams[i]:
            if self.debug:
                print(f"[CAN] Emp {i+1} day {d0+1}: team {team_id} not allowed (allowed={self.allowed_teams[i]})")
            return False

        if self.emp_workdays[i] >= 223:
            if self.debug:
                print(f"[CAN] Emp {i+1} day {d0+1}: already has 223 workdays")
            return False

        if self._is_special(d0 + 1) and (self.emp_special[i] + 1) > 22:
            if self.debug:
                print(f"[CAN] Emp {i+1} day {d0+1}: special-days cap 22 exceeded")
            return False

        if not self._backward_order_ok(i, d0, s):
            return False

        # Temporarily assign to check consecutive windows
        self.emp_day_shift[i, d0] = s
        ok = self._consecutive_ok_after_assign(i, d0)
        self.emp_day_shift[i, d0] = 0
        if not ok:
            return False

        return True

    def _apply(self, i, d0, s, team_id):
        """Apply assignment to state."""
        self.emp_day_shift[i, d0] = s
        self.emp_day_team[i, d0] = team_id
        self.emp_workdays[i] += 1
        if self._is_special(d0 + 1):
            self.emp_special[i] += 1
        self.coverage[(d0 + 1, s, team_id)] += 1
        if self.debug:
            print(f"[APPLY] Emp {i+1} -> day {d0+1}, shift {s}, team {team_id} | workdays={self.emp_workdays[i]}, special={self.emp_special[i]}")

    def _revert(self, i, d0, s, team_id):
        """Undo assignment from state."""
        self.emp_day_shift[i, d0] = 0
        self.emp_day_team[i, d0] = 0
        self.emp_workdays[i] -= 1
        if self._is_special(d0 + 1):
            self.emp_special[i] -= 1
        self.coverage[(d0 + 1, s, team_id)] -= 1
        if self.debug:
            print(f"[REVERT] Emp {i+1} <- day {d0+1}, shift {s}, team {team_id} | workdays={self.emp_workdays[i]}, special={self.emp_special[i]}")

    # ---------- Phase 1: minimize unmet minimums (anytime branch-and-bound) ----------

    def _slot_deficit(self, d1, s, team_id):
        """How many more employees needed to reach minimum at (d1, s, team)?"""
        need = int(self.mins.get((d1, s, team_id), 0))
        have = int(self.coverage.get((d1, s, team_id), 0))
        return max(0, need - have)

    def _next_min_slot(self):
        """
        Pick next underfilled slot by MRV/deficit:
          - choose a slot with positive deficit
          - tie-break: earlier day, then higher deficit, then smaller candidate set
        Returns (d0, s, team_id, candidates) or None if all mins met.
        """
        best = None
        for (d1, s, team_id), need in self.mins.items():
            deficit = self._slot_deficit(d1, s, team_id)
            if deficit <= 0:
                continue
            d0 = d1 - 1

            # candidate employees
            cand = []
            for i in range(self.n_emp):
                if self._can_assign(i, d0, s, team_id):
                    cand.append(i)

            if self.debug:
                print(f"[NEXT] Slot (d={d1}, s={s}, team={team_id}) deficit={deficit} candidates={len(cand)}")

            key = (d0, -deficit, len(cand))
            if best is None or key < best[0]:
                best = (key, (d0, s, team_id, cand))
        return None if best is None else best[1]

    # --- slack helpers ---
    def _apply_slack(self, d1, s, team_id):
        self.coverage[(d1, s, team_id)] += 1
        self.slack[(d1, s, team_id)] += 1

    def _revert_slack(self, d1, s, team_id):
        self.coverage[(d1, s, team_id)] -= 1
        self.slack[(d1, s, team_id)] -= 1
        if self.slack[(d1, s, team_id)] == 0:
            del self.slack[(d1, s, team_id)]

    # --- incumbent management ---
    def _remaining_min_units(self):
        total = 0
        for (d1, s, t), req in self.mins.items():
            have = int(self.coverage.get((d1, s, t), 0))
            if have < req:
                total += (req - have)
        return total

    def _snapshot(self):
        return (
            self.emp_day_shift.copy(),
            self.emp_day_team.copy(),
            self.emp_workdays.copy(),
            self.emp_special.copy(),
            dict(self.coverage),
            dict(self.slack),
        )

    def _restore(self, snap):
        (self.emp_day_shift,
         self.emp_day_team,
         self.emp_workdays,
         self.emp_special,
         cov,
         slack) = snap
        self.coverage.clear()
        self.coverage.update(cov)
        self.slack = defaultdict(int, slack)

    def _update_incumbent(self, current_unmet):
        rem = self._remaining_min_units()
        if self._best_remaining is None:
            better = True
        else:
            better = (current_unmet, rem) < (self.best_unmet, self._best_remaining)
        if better:
            self.best_unmet = current_unmet
            self._best_remaining = rem
            self.best_snapshot = self._snapshot()
            if self.debug:
                print(f"[INCUMBENT] unmet={self.best_unmet}, remaining={self._best_remaining}")

    def _search_minimums_min_unmet(self, deadline, current_unmet=0):
        # timeout
        if not self._time_left(deadline):
            return TIMEOUT

        # poda por incumbente
        if current_unmet >= self.best_unmet:
            return False

        nxt = self._next_min_slot()
        if nxt is None:
            # com pessoas/slack não há défice directo
            self._update_incumbent(current_unmet)
            return True

        d0, s, team_id, candidates = nxt
        d1 = d0 + 1

        # tentar pessoas reais (heurística: especiais→workdays)
        candidates.sort(key=lambda i: (self.emp_special[i], self.emp_workdays[i]))
        for i in candidates:
            if not self._time_left(deadline):
                return TIMEOUT
            self._apply(i, d0, s, team_id)
            self._update_incumbent(current_unmet)  # pode melhorar 'remaining'
            res = self._search_minimums_min_unmet(deadline, current_unmet)
            self._revert(i, d0, s, team_id)
            if res is TIMEOUT:
                return TIMEOUT

        # ramo slack (consome uma falta)
        if not self._time_left(deadline):
            return TIMEOUT
        self._apply_slack(d1, s, team_id)
        self._update_incumbent(current_unmet + 1)
        res = self._search_minimums_min_unmet(deadline, current_unmet + 1)
        self._revert_slack(d1, s, team_id)
        if res is TIMEOUT:
            return TIMEOUT

        return res

    # ---------- Phase 2: fill employees up to 223 (greedy feasibility) ----------

    def _fill_to_targets(self, deadline):
        def desirability(d1, s, team_id):
            have = int(self.coverage.get((d1, s, team_id), 0))
            min_req = int(self.mins.get((d1, s, team_id), 0))
            ideal = int(self.ideals.get((d1, s, team_id), 0))

            if have < min_req:
                return (0, min_req - have)
            if have < ideal:
                return (1, ideal - have)
            if have == ideal:
                return (2, 0)
            return (3, have - ideal)

        slots = []
        for d1 in range(1, self.num_days + 1):
            for s in range(1, self.shifts + 1):
                for team_id in self.all_teams:
                    slots.append((d1, s, team_id))
        slots.sort(key=lambda x: (x[0], desirability(*x)))

        if self.debug:
            print(f"[FILL] Starting greedy fill. total slots={len(slots)}")

        progress = True
        loops = 0
        while progress and self._time_left(deadline):
            loops += 1
            progress = False

            for i in range(self.n_emp):
                if not self._time_left(deadline):
                    break
                if self.emp_workdays[i] >= 223:
                    continue

                for (d1, s, team_id) in slots:
                    if not self._time_left(deadline):
                        break
                    d0 = d1 - 1
                    if team_id not in self.allowed_teams[i]:
                        continue
                    if self._can_assign(i, d0, s, team_id):
                        self._apply(i, d0, s, team_id)
                        progress = True
                        if self.emp_workdays[i] >= 223:
                            break

            if self.debug:
                remaining = [223 - int(x) for x in self.emp_workdays]
                print(f"[FILL] Loop {loops} done. Remaining (first 10): {remaining[:10]}. Progress={progress}")

    # ---------- Greedy cover mínimos (best-effort) ----------
    def _remaining_min_deficits(self):
        """
        Return list of (deficit, day1, shift, team_id) for all min slots still underfilled
        given current self.coverage.
        """
        deficits = []
        for (d1, s, team_id), req in self.mins.items():
            have = int(self.coverage.get((d1, s, team_id), 0))
            if have < req:
                deficits.append((req - have, d1, s, team_id))
        return deficits

    def _greedy_cover_minimos(self, deadline):
        """
        Best-effort pass: while there are underfilled min slots, try to add people
        without violating any HARD constraints. No backtracking — if a slot can't
        be improved right now, we skip it and continue.
        """
        improved = True
        loops = 0
        while improved and self._time_left(deadline):
            loops += 1
            improved = False
            deficits = self._remaining_min_deficits()
            if not deficits:
                if self.debug:
                    print("[SOFT-MIN] All minimums satisfied during greedy pass.")
                break

            # Sort: largest deficit first, then earliest day
            deficits.sort(key=lambda tup: (-tup[0], tup[1]))

            for deficit, d1, s, team_id in deficits:
                if not self._time_left(deadline):
                    break
                if deficit <= 0:
                    continue
                d0 = d1 - 1

                # Build feasible candidates (HARD constraints via _can_assign)
                cands = [i for i in range(self.n_emp) if self._can_assign(i, d0, s, team_id)]
                if not cands:
                    if self.debug:
                        print(f"[SOFT-MIN] Slot (d={d1}, s={s}, team={team_id}) has no feasible candidates now.")
                    continue

                cands.sort(key=lambda i: (self.emp_special[i], self.emp_workdays[i]))
                chosen = cands[0]
                self._apply(chosen, d0, s, team_id)
                improved = True

            if self.debug:
                left = sum(defi for (defi, *_rest) in self._remaining_min_deficits())
                print(f"[SOFT-MIN] Loop {loops} complete. Remaining min units to cover: {left}")
                if not improved:
                    print("[SOFT-MIN] No further improvement possible without breaking hard constraints.")
                    break

    # ---------- BUILD ----------
    def build(self):
        t0 = self._now()
        total = self.total_time_sec or 300  # default 5 min if none provided

        # Split time budget (adjust as you see fit)
        t_search = int(total * 0.60)
        t_greedy = int(total * 0.25)
        t_fill   = max(0, total - t_search - t_greedy)

        # Phase 1: search (anytime) minimize unmet mins
        if self.debug:
            print(f"[TIME] Budgets: search={t_search}s, greedy={t_greedy}s, fill={t_fill}s")

        dl_search = self._deadline(t_search)
        # Seed incumbente com o estado vazio (para garantir snapshot sempre)
        self._update_incumbent(current_unmet=10**9)

        res = self._search_minimums_min_unmet(deadline=dl_search, current_unmet=0)

        # Restore best partial found (if any improved incumbente)
        if self.best_snapshot is not None:
            self._restore(self.best_snapshot)

        if self.debug:
            print(f"[SEARCH] Done. best_unmet={self.best_unmet}, remaining={self._best_remaining}")

        # Phase Greedy cover (extra tentativa best-effort)
        dl_greedy = self._deadline(t_greedy)
        self._greedy_cover_minimos(dl_greedy)

        # Phase 2: fill to 223 within remaining time
        dl_fill = self._deadline(t_fill)
        self._fill_to_targets(dl_fill)

        # Materialize for export
        self._materialize_assignment()

        elapsed = self._now() - t0
        print(f"[ConstraintSearch] Build finished in {elapsed:.2f}s; best_unmet={self.best_unmet if self.best_unmet!=float('inf') else 'n/a'}")
        if self.debug:
            print(f"[RESULT] Final workdays per employee (first 20): {self.emp_workdays[:20]}")
            print(f"[RESULT] Final special-days per employee (first 20): {self.emp_special[:20]}")

    # ---------- export / view ----------
    def _materialize_assignment(self):
        self.assignment.clear()
        for i in range(self.n_emp):
            emp_id = i + 1
            for d0 in range(self.num_days):
                s = self.emp_day_shift[i, d0]
                if s > 0:
                    team_id = int(self.emp_day_team[i, d0])
                    if team_id > 0:
                        self.assignment[emp_id].append((d0 + 1, s, team_id))
        if self.debug:
            total_asg = sum(len(v) for v in self.assignment.values())
            print(f"[EXPORT] Built assignment list. total entries={total_asg}")

    def export_csv(self, filename="calendario_csp.csv"):
        class View: pass
        v = View()
        v.employees = [i + 1 for i in range(self.n_emp)]
        v.vacs = self.vacs_1based
        v.assignment = self.assignment
        export_schedule_to_csv(v, filename=filename, num_days=self.num_days)
        if self.debug:
            print(f"[EXPORT] CSV written to {filename}")

    def to_table(self):
        header = ["funcionario"] + [f"Dia {d}" for d in range(1, self.num_days + 1)]
        rows = [header]
        label = {1: "M_", 2: "T_", 3: "N_"}
        for emp_id in range(1, self.n_emp + 1):
            i = emp_id - 1
            vac_days = set(self.vacs_1based.get(emp_id, []))
            day_to_st = {d: (s, t) for (d, s, t) in self.assignment.get(emp_id, [])}
            line = [str(emp_id)]
            for d in range(1, self.num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_st:
                    s, team_id = day_to_st[d]
                    line.append(label.get(s, "") + TEAM_ID_TO_CODE.get(team_id, str(team_id)))
                else:
                    line.append("0")
            rows.append(line)
        return rows


# --------- convenience wrapper (same shape as your other solvers) ---------

def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=2):
    """
    vacations: rows like ['Employee 1','0','1',...]
    minimuns:  rows like ['Equipa A','Minimo','M', ...] / any team label the utils can parse
    employees: [{'teams': ['Equipa A','Equipa B','Equipa C', ...]}, ...]
    maxTime: minutes (int/str), time budget for the WHOLE build.
    """
    csp = ConstraintSearchScheduler(
        vacations_rows=vacations,
        minimuns_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        shifts=shifts,
        debug=True,
    )
    csp.build()
    csp.export_csv("calendario_csp.csv")
    return csp.to_table()

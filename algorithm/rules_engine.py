from collections import defaultdict
import numpy as np

class RuleEngine:
    """
    Stateless, callback-free rule engine:
    - Hard constraints via can_assign(p, d, s, t, assignment) -> bool
    - Optional soft penalties via score_horario(horario, assignment) -> int
    """

    def __init__(self, rules, employees, num_days, shifts, teams, vacation_array, holidays_set, sunday_set):
        self.rules = rules or []  # list of rule dicts
        self.employees = employees            # [1..N]
        self.num_days = int(num_days)
        self.shifts = int(shifts)
        self.teams = teams                    # {emp_id: [team_id,...]}
        self.vacation_array = vacation_array  # shape [N, D] -> True if on vacation
        self.holidays_set = set(holidays_set)
        self.sunday_set = set(sunday_set)
        self.special_days = self.holidays_set | self.sunday_set

        # containers
        self.hard_per_employee_day = []      # fn(p,d,s,t,ctx) -> bool
        self.hard_per_employee_window = []   # fn(p,assignment_list,ctx) -> bool
        self.hard_per_employee_global = []   # fn(p,assignment_list,ctx) -> bool
        self.hard_adjacent = []              # fn(p,d,s,t,ctx) -> bool
        self.soft_slot_penalties = []        # fn(horario, assignment) -> int

        # mins map used by min_coverage soft rule
        self.rules_mins = {}

        self.compile_rules()

    # ---------- public API ----------

    def can_assign(self, employee_id, day, shift, team_id, assignment):
        """
        employee_id: 1-based
        day:         1-based
        shift:       1..S
        team_id:     int
        assignment:  dict p -> list[(day,shift,team)]
        """
        # hard per-day (fast guards)
        if self.vacation_array[employee_id - 1, day - 1]:
            return False

        ctx = {
            "assignment": assignment,
            "employee_id": employee_id,
            "day": day,
            "shift": shift,
            "team_id": team_id,
        }

        for fn in self.hard_per_employee_day:
            if not fn(employee_id, day, shift, team_id, ctx):
                return False

        # adjacency (prev/next day dependent)
        for fn in self.hard_adjacent:
            if not fn(employee_id, day, shift, team_id, ctx):
                return False

        # Build augmented assignment list for window/global checks
        employee_assign = list(assignment.get(employee_id, []))
        # ensure tentative (day,shift,team) is considered exactly once
        if (day, shift, team_id) not in employee_assign:
            employee_assign.append((day, shift, team_id))

        # window-based and global checks
        for fn in self.hard_per_employee_window:
            if not fn(employee_id, employee_assign, ctx):
                return False

        for fn in self.hard_per_employee_global:
            if not fn(employee_id, employee_assign, ctx):
                return False

        return True

    def score_horario(self, horario, assignment):
        """
        horario: numpy array [N, D, S] storing team_id (0=off)
        assignment: dict p -> list[(d,s,t)]
        Returns total soft penalty (lower is better)
        """
        total = 0
        for fn in self.soft_slot_penalties:
            total += fn(horario, assignment)
        return total

    def set_mins_map(self, mins_map):
        self.rules_mins = mins_map or {}

    # ---------- rule compilation ----------

    def compile_rules(self):
        for rule in self.rules:
            rtype = rule.get("type")
            params = rule.get("params", {})

            if rtype == "vacation_block":
                def not_vacation():
                    def check(employee_id, day, shift, team_id, ctx):
                        return not self.vacation_array[employee_id - 1, day - 1]
                    return check
                self.hard_per_employee_day.append(not_vacation())

            elif rtype == "team_eligibility":
                def belongs_to_team():
                    def check(employee_id, day, shift, team_id, ctx):
                        return team_id in self.teams.get(employee_id, [])
                    return check
                self.hard_per_employee_day.append(belongs_to_team())

            elif rtype == "max_consecutive_days":
                window = params.get("window", 6)
                max_worked = params.get("max_worked", 5)

                def make_max_consecutive_days(window=window, max_worked=max_worked):
                    def check(p, assignment_list, ctx):
                        days = sorted(d for (d, _, _) in assignment_list)
                        # detect any run of > max_worked consecutive days
                        run = 1
                        for i in range(1, len(days)):
                            if days[i] == days[i - 1] + 1:
                                run += 1
                                if run > max_worked:
                                    return False
                            else:
                                run = 1
                        # enforce at most `max_worked` workdays in any `window`-day span
                        if window and window > 0:
                            for i in range(len(days)):
                                end = days[i] + window
                                worked_in_span = sum(1 for d in days if days[i] <= d < end)
                                if worked_in_span > max_worked:
                                    return False
                        return True
                    return check
                self.hard_per_employee_window.append(make_max_consecutive_days())

            elif rtype == "max_special_days":
                cap = params.get("cap", 22)
                def make_max_special_days(cap=cap):
                    def check(p, assignment_list, ctx):
                        cnt = sum(1 for (d, _, _) in assignment_list if d in self.special_days)
                        return cnt <= cap
                    return check
                self.hard_per_employee_global.append(make_max_special_days())

            elif rtype == "no_earlier_shift_next_day":
                def no_earlier_shift():
                    def check(employee_id, day, shift, team_id, ctx):
                        assignments = ctx.get("assignment", {}).get(employee_id, [])
                        for (d, s, _) in assignments:
                            if d + 1 == day and shift < s:
                                return False
                            if d - 1 == day and s < shift:
                                return False
                        return True
                    return check
                self.hard_adjacent.append(no_earlier_shift())

            elif rtype == "max_total_workdays":
                max_workdays = params.get("max")
                def max_days_worked():
                    def check(employee_id, assignment_list, ctx):
                        existing_days = {d for (d, _, _) in assignment_list}
                        return len(existing_days) <= max_workdays
                    return check
                self.hard_per_employee_global.append(max_days_worked())

            elif rtype == "min_coverage":
                # Soft penalty; you can include this in the HC objective if desired
                penalty = params.get("penalty_per_missing", 1000)
                def minimum_coverage():
                    def score(horario, assignment):
                        total_penalization = 0
                        for (day, shift, team), req in self.rules_mins.items():
                            assigned = np.sum(horario[:, day - 1, shift - 1] == team)
                            if assigned < req:
                                total_penalization += (req - assigned) * penalty
                        return total_penalization
                    return score
                self.soft_slot_penalties.append(minimum_coverage())

            else:
                print(f"[RuleEngine] Unknown rule type: {rtype} (ignored)")

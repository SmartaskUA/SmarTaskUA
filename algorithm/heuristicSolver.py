import time
import math
import random
import numpy as np
from collections import defaultdict
import holidays as hl

# Import your existing utilities
from algorithm.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    get_team_id,
    get_team_code,
    export_schedule_to_csv,
    build_calendar,
    schedule_to_table
)

# --- CONFIGURATION ---
WEIGHT_UNMET_MIN = 100       # High penalty for missing minimum staff
WEIGHT_UNMET_IDEAL = 1       # Low penalty for missing ideal staff
WEIGHT_CONSTRAINT_HARD = 500 # Penalty for breaking rules (5-in-6, rotation)
WEIGHT_SPECIAL_CAP = 200     # Penalty for exceeding special days

class HeuristicScheduler:
    def __init__(self, employees, vac_dict, min_reqs, ideal_reqs, allowed_teams, 
                 num_days, shifts, special_days):
        self.n_employees = len(employees)
        self.num_days = num_days
        self.n_shifts = shifts
        self.employees = list(range(self.n_employees))
        self.vac_dict = vac_dict
        self.min_reqs = min_reqs     # Dict: (day, shift, team) -> count
        self.ideal_reqs = ideal_reqs
        self.allowed_teams = allowed_teams # List of lists [[1,2], [1], ...]
        self.special_days = special_days
        
        # State: 0 = OFF, 1..S = Shift ID
        self.schedule = np.zeros((self.n_employees, self.num_days + 1), dtype=int)
        
        # Precompute simple demand lookup for speed: (day, shift) -> total_needed
        # (We simplify team matching in the inner loop to pure capacity)
        self.daily_demand_min = np.zeros((num_days + 1, shifts + 1), dtype=int)
        for (d, s, t), count in min_reqs.items():
            self.daily_demand_min[d, s] += count

    def initialize_solution(self):
        """
        Create a random schedule that satisfies:
        1. Vacation days are OFF
        2. Exactly 223 work days per year
        """
        target_work = 223
        
        for emp in self.employees:
            # 1. Identify valid days (not vacation)
            vacations = self.vac_dict.get(emp + 1, [])
            valid_days = [d for d in range(1, self.num_days + 1) if d not in vacations]
            
            # 2. If valid days < target, work all valid days (rare edge case)
            if len(valid_days) <= target_work:
                days_to_work = valid_days
            else:
                # 3. Randomly pick exactly 223 days to work
                days_to_work = np.random.choice(valid_days, target_work, replace=False)
            
            # 4. Assign random shifts to those days
            for d in days_to_work:
                self.schedule[emp, d] = np.random.randint(1, self.n_shifts + 1)

    def calculate_cost(self, schedule_snapshot=None):
        """
        Calculates the 'Energy' (Badness) of the schedule.
        Lower is better. 0 is perfect.
        """
        sched = schedule_snapshot if schedule_snapshot is not None else self.schedule
        cost = 0
        
        # --- 1. CONSTRAINT VIOLATIONS (Per Employee) ---
        for emp in self.employees:
            emp_sched = sched[emp] # Array of shifts for this emp
            
            # A. 5 worked days in 6-day window
            # Rolling sum of (sched > 0)
            is_working = (emp_sched > 0).astype(int)
            # Create a simple convolution or loop for the window
            # (Loop is safer for variable window logic)
            for start in range(1, self.num_days - 6 + 2):
                if np.sum(is_working[start : start+6]) > 5:
                    cost += WEIGHT_CONSTRAINT_HARD
            
            # B. Rotation: Cannot work Shift X then Shift Y if Y < X (unless Off in between)
            # We iterate 1 to num_days-1
            # Logic: If Worked(d) and Worked(d+1), require Shift(d+1) >= Shift(d)
            # Vectorized approach:
            mask_consecutive = (emp_sched[1:-1] > 0) & (emp_sched[2:] > 0)
            mask_violation = emp_sched[2:] < emp_sched[1:-1]
            violations = np.sum(mask_consecutive & mask_violation)
            cost += violations * WEIGHT_CONSTRAINT_HARD

            # C. Special Days Cap (Max 22)
            # We only check if the employee worked on special days
            special_worked = sum(1 for d in self.special_days if emp_sched[d] > 0)
            if special_worked > 22:
                cost += (special_worked - 22) * WEIGHT_SPECIAL_CAP

        # --- 2. DEMAND COVERAGE (Per Day) ---
        # We approximate team coverage here. 
        # Ideally, we solve a Min-Cost-Flow, but for speed, we check aggregate capacity.
        
        for d in range(1, self.num_days + 1):
            for s in range(1, self.n_shifts + 1):
                needed = self.daily_demand_min[d, s]
                if needed > 0:
                    # Count how many people are working this shift
                    # (Refinement: Only count people who CAN do the teams required? 
                    # For simplicity/speed in heuristic, we count raw bodies on shift s)
                    actual = np.count_nonzero(sched[:, d] == s)
                    if actual < needed:
                        cost += (needed - actual) * WEIGHT_UNMET_MIN

        return cost

    def solve_simulated_annealing(self, max_time_mins=5):
        current_cost = self.calculate_cost()
        best_schedule = self.schedule.copy()
        best_cost = current_cost
        
        t_start = time.time()
        time_limit = max_time_mins * 60 if max_time_mins else 600
        
        # SA Parameters
        temperature = 1000.0
        alpha = 0.995 # Cooling rate
        iteration = 0
        
        print(f"Initial Cost: {current_cost}")
        
        while True:
            iteration += 1
            elapsed = time.time() - t_start
            if elapsed > time_limit:
                break
                
            if best_cost == 0:
                break # Perfect score
                
            # --- GENERATE NEIGHBOR (MOVE) ---
            # We operate on a copy or modify-restore basis
            # Type 1: Swap Work Day with Off Day (Preserves 223 count)
            # Type 2: Change Shift on a Work Day
            
            emp = np.random.randint(0, self.n_employees)
            move_type = np.random.random()
            
            # Store old values to revert if rejected
            prev_d1_val = None
            prev_d2_val = None
            d1, d2 = 0, 0
            
            performed_move = False
            
            if move_type < 0.7: # 70% chance: Swap Days for 1 employee
                # Find a work day and an off day
                # Only look at non-vacation days
                valid_indices = [d for d in range(1, self.num_days+1) 
                                 if d not in self.vac_dict.get(emp+1, [])]
                if len(valid_indices) < 2: continue
                
                d1, d2 = np.random.choice(valid_indices, 2, replace=False)
                val1, val2 = self.schedule[emp, d1], self.schedule[emp, d2]
                
                # We only care if one is work and one is off, or different shifts
                if val1 != val2:
                    prev_d1_val, prev_d2_val = val1, val2
                    self.schedule[emp, d1] = val2
                    self.schedule[emp, d2] = val1
                    performed_move = True
                    
            else: # 30% chance: Change Shift
                # Pick a random day
                d1 = np.random.randint(1, self.num_days + 1)
                # If working, change shift
                if self.schedule[emp, d1] > 0:
                    prev_d1_val = self.schedule[emp, d1]
                    # Pick different shift
                    choices = [s for s in range(1, self.n_shifts+1) if s != prev_d1_val]
                    if choices:
                        new_s = np.random.choice(choices)
                        self.schedule[emp, d1] = new_s
                        performed_move = True

            if not performed_move:
                continue

            # --- EVALUATE ---
            # Optimization: In a full production code, we would calculate Delta Cost.
            # Here, we recalculate full cost for safety/clarity.
            new_cost = self.calculate_cost()
            
            delta = new_cost - current_cost
            
            # Acceptance Probability (Metropolis Criterion)
            accept = False
            if delta < 0:
                accept = True
            else:
                if random.random() < math.exp(-delta / temperature):
                    accept = True
            
            if accept:
                current_cost = new_cost
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_schedule = self.schedule.copy()
                    print(f"Iter {iteration} | Time {elapsed:.1f}s | Temp {temperature:.1f} | New Best: {best_cost}")
            else:
                # Revert move
                if prev_d1_val is not None:
                    self.schedule[emp, d1] = prev_d1_val
                if prev_d2_val is not None:
                    self.schedule[emp, d2] = prev_d2_val
            
            # Cool down
            if iteration % 100 == 0:
                temperature *= alpha
                if temperature < 0.1: 
                    temperature = 0.1 # Floor

        self.schedule = best_schedule
        return best_cost

    def assign_teams_greedily(self):
        """
        The heuristic solved (Employee, Day) -> Shift.
        Now we must determine (Employee, Day) -> Team.
        We do this Greedily day by day.
        """
        final_assignment = defaultdict(list) # emp_id -> [(day, shift, team), ...]
        
        for d in range(1, self.num_days + 1):
            # 1. Gather all requirements for this day
            # reqs: list of (shift, team, count)
            day_reqs = []
            for (dd, ss, tt), count in self.min_reqs.items():
                if dd == d:
                    day_reqs.append({'s': ss, 't': tt, 'needed': count, 'filled': 0})
            
            # Sort requirements: Rare teams first (hardest to fill)
            # (We estimate rarity by looking at how many employees allow that team)
            # For now, just simplistic sort
            day_reqs.sort(key=lambda x: x['needed'], reverse=True)
            
            # 2. Identify who is working what shift
            workers_on_day = [] # (emp_idx, shift)
            for emp in self.employees:
                s = self.schedule[emp, d]
                if s > 0:
                    workers_on_day.append((emp, s))
            
            # 3. Match Workers to Requirements
            # Keep track of who is assigned a team
            assigned_workers = set()
            
            # Pass 1: Fill Mandatory Requirements
            for req in day_reqs:
                needed = req['needed']
                shift = req['s']
                team = req['t']
                
                # Find available workers for this shift who allow this team
                candidates = []
                for emp, s in workers_on_day:
                    if emp not in assigned_workers and s == shift:
                        # Check if emp allows this team
                        allowed = self.allowed_teams[emp]
                        if team in allowed:
                            candidates.append(emp)
                
                # Assign up to 'needed'
                take = candidates[:needed]
                for emp in take:
                    final_assignment[emp + 1].append((d, shift, team))
                    assigned_workers.add(emp)
                    req['filled'] += 1
            
            # Pass 2: Assign remaining workers to their "primary" or "first allowed" team
            # (They are working the shift, so they must be assigned a team even if not "needed")
            for emp, s in workers_on_day:
                if emp not in assigned_workers:
                    # Just pick the first allowed team
                    # (In a real scenario, you'd pick the one with Ideal demand)
                    allowed = self.allowed_teams[emp]
                    if allowed:
                        t = allowed[0]
                        final_assignment[emp + 1].append((d, s, t))
        
        return final_assignment

# --- MAIN WRAPPER FUNCTION ---

def _build_allowed_teams(employees):
    allowed = []
    for Employees in employees:
        codes = [get_team_code(t) for t in Employees.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed

def solve(*, vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):
    
    num_days = 365
    n_employees = len(employees)
    
    # 1. Process Data
    allowed_teams = _build_allowed_teams(employees)
    vacs_dict = rows_to_vac_dict(vacations)
    mins_raw, ideals_raw = rows_to_req_dicts(minimuns)
    
    min_reqs = {}
    for (d, s, t), v in mins_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shifts) and int(v) > 0:
            min_reqs[(d, s, t)] = int(v)

    ideal_reqs = {}
    for (d, s, t), v in ideals_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shifts) and int(v) > 0:
            ideal_reqs[(d, s, t)] = int(v)
            
    # Calendar & Special Days
    year = int(year) if year is not None else 2025
    dias_ano, sundays_1based = build_calendar(year)
    pt_holidays = hl.country_holidays("PT", years=[year])
    start_date = dias_ano[0].date()
    special_days = {(d - start_date).days + 1 for d in pt_holidays}
    special_days |= set(sundays_1based)

    # 2. Instantiate Heuristic Solver
    print("--- Starting Heuristic Solver (Simulated Annealing) ---")
    scheduler = HeuristicScheduler(
        employees=employees,
        vac_dict=vacs_dict,
        min_reqs=min_reqs,
        ideal_reqs=ideal_reqs,
        allowed_teams=allowed_teams,
        num_days=num_days,
        shifts=int(shifts),
        special_days=special_days
    )
    
    # 3. Initialize Random Valid Solution
    scheduler.initialize_solution()
    
    # 4. Run Optimization
    final_cost = scheduler.solve_simulated_annealing(max_time_mins=maxTime)
    
    print(f"--- Optimization Finished ---")
    print(f"Final Heuristic Cost: {final_cost}")
    
    # 5. Assign Teams (Post-processing)
    assignment_dict = scheduler.assign_teams_greedily()
    
    # 6. Export Results
    class View: pass
    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assignment_dict
    
    export_schedule_to_csv(v, "schedule_heuristic.csv", num_days=num_days)

    return schedule_to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        shifts=int(shifts),
    )
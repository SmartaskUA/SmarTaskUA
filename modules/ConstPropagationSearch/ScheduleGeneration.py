import random
from calendar import monthrange, day_abbr, weekday
import csv

class SmarTask:
    def __init__(self):
        self.num_employees = 24
        self.num_days = 365 
        self.days = list(range(1, self.num_days + 1))
        self.shifts = ["M", "T"] 
        self.domain = ["0", "M", "T", "F"]  # 0: off, M: morning, T: afternoon, F: vacation
        self.holidays = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}
        self.employees = [f"Employee_{i}" for i in range(1, self.num_employees + 1)]
        self.schedule = {} 
        self.min_workers = 2
        self.ideal_workers = 4
        self.counters = {
            "work_days": {emp: 0 for emp in self.employees},
            "consecutive_days": {emp: 0 for emp in self.employees},
            "work_holidays_sunday": {emp: 0 for emp in self.employees},
            "vacations": {emp: set(random.sample(self.days, 30)) for emp in self.employees},
        }

    def initialize_schedule(self):
        """Initialize the schedule with all variables set to '0' (off)."""
        for e in range(1, self.num_employees + 1):
            for d in self.days:
                for s in self.shifts:
                    self.schedule[f"E{e},{d},{s}"] = "0"
                if d in self.counters["vacations"][f"Employee_{e}"]:
                    self.schedule[f"E{e},{d},M"] = "F"
                    self.schedule[f"E{e},{d},T"] = "F"

    def is_valid_assignment(self, var):
        """Check if assigning 'shift' to 'var' respects all constraints."""
        e, d, s = var.split(",")
        emp = f"Employee_{e[1:]}"
        d = int(d)

        if d in self.counters["vacations"][emp]:
            return False

        # Check max workdays (223 days per year)
        if self.counters["work_days"][emp] >= 223:
            return False

        # Check max Sundays/holidays (22 per year)
        is_sunday = (d - 1) % 7 == 6  # Assuming day 1 is Monday
        if (is_sunday or d in self.holidays) and self.counters["work_holidays_sunday"][emp] >= 22:
            return False

        # Check consecutive days (max 5)
        if self.counters["consecutive_days"][emp] >= 5:
            prev_days = [self.schedule.get(f"E{e[1:]},{d_prev},{shift_prev}") in ["M", "T"]
                         for d_prev in range(max(1, d-5), d) for shift_prev in self.shifts]
            if all(prev_days[-5:]): 
                return False

        # Check T->M transition
        if s == "M" and d > 1 and self.schedule.get(f"E{e[1:]},{d-1},T") == "T":
            return False
        if s == "T" and d < self.num_days and self.schedule.get(f"E{e[1:]},{d+1},M") == "M":
            return False 

        return True

    def update_counters(self, var):
        """Update counters after assigning a shift."""
        e, d, s = var.split(",")
        emp = f"Employee_{e[1:]}"
        d = int(d)

        self.counters["work_days"][emp] += 1
        if (d - 1) % 7 == 6 or d in self.holidays:  # Sunday or holiday
            self.counters["work_holidays_sunday"][emp] += 1

        # Update consecutive days
        work_days = [d for day in range(max(1, d-5), d+1)
                     if any(self.schedule.get(f"E{e[1:]},{day},{shift_prev}") in ["M", "T"]
                            for shift_prev in self.shifts)]
        max_consecutive = 1
        current = 1
        for i in range(1, len(work_days)):
            if work_days[i] == work_days[i-1] + 1:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 1
        self.counters["consecutive_days"][emp] = max_consecutive

    def generate_schedule(self):
        """Generate a schedule aiming for ideal employees per shift, ensuring at least the minimum."""
        self.initialize_schedule()

        for d in self.days:
            for shift in self.shifts:
                assigned_employees = set()
                target = self.ideal_workers
                available_employees = [
                    f"E{e},{d},{shift}"
                    for e in range(1, self.num_employees + 1)
                    if f"Employee_{e}" not in assigned_employees
                    and self.is_valid_assignment(f"E{e},{d},{shift}")
                ]

                for _ in range(min(target, len(available_employees))):
                    if available_employees:
                        selected_var = random.choice(available_employees)
                        self.schedule[selected_var] = shift
                        assigned_employees.add(f"Employee_{selected_var.split(',')[0][1:]}")
                        self.update_counters(selected_var)
                        available_employees.remove(selected_var)

                if len(assigned_employees) < self.min_workers:
                    print(f"Warning: Day {d}, Shift {shift} - Only {len(assigned_employees)} assigned, below minimum {self.min_workers}. Relaxing constraints...")
                    fallback_employees = [
                        f"E{e},{d},{shift}"
                        for e in range(1, self.num_employees + 1)
                        if f"Employee_{e}" not in assigned_employees
                    ]
                    while len(assigned_employees) < self.min_workers and fallback_employees:
                        selected_var = random.choice(fallback_employees)
                        self.schedule[selected_var] = shift
                        assigned_employees.add(f"Employee_{selected_var.split(',')[0][1:]}")
                        self.update_counters(selected_var)
                        fallback_employees.remove(selected_var)

                if len(assigned_employees) < self.min_workers:
                    print(f"Error: Day {d}, Shift {shift} - Only {len(assigned_employees)} assigned, below minimum {self.min_workers}.")
                    return False
        return True

    def export(self, filename="schedule_J.csv"):
        """Export the schedule to a CSV file."""
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            month_days = [day for month in range(1, 13) for day in range(1, monthrange(2025, month)[1] + 1)]
            writer.writerow([""] + month_days[:self.num_days])
            writer.writerow([""] + [day_abbr[(d-1) % 7] for d in self.days])  # Weekdays starting Monday

            for emp in self.employees:
                e = emp.split("_")[1]
                row = [emp]
                for d in self.days:
                    morning = self.schedule.get(f"E{e},{d},M")
                    afternoon = self.schedule.get(f"E{e},{d},T")
                    if morning == "M":
                        row.append("M")
                    elif afternoon == "T":
                        row.append("T")
                    elif morning == "F" or afternoon == "F":
                        row.append("F")
                    else:
                        row.append("0")
                writer.writerow(row)

    def verify(self):
        """Verify the schedule for constraint violations."""
        violations = []
        for d in self.days:
            morning_count = sum(1 for e in range(1, self.num_employees + 1) if self.schedule[f"E{e},{d},M"] == "M")
            afternoon_count = sum(1 for e in range(1, self.num_employees + 1) if self.schedule[f"E{e},{d},T"] == "T")
            if morning_count < self.min_workers:
                violations.append(f"Day {d}: Morning shift has {morning_count} employees, below minimum {self.min_workers}")
            if afternoon_count < self.min_workers:
                violations.append(f"Day {d}: Afternoon shift has {afternoon_count} employees, below minimum {self.min_workers}")
            if morning_count < self.ideal_workers:
                violations.append(f"Day {d}: Morning shift has {morning_count} employees, below ideal {self.ideal_workers}")
            if afternoon_count < self.ideal_workers:
                violations.append(f"Day {d}: Afternoon shift has {afternoon_count} employees, below ideal {self.ideal_workers}")

        for e in range(1, self.num_employees + 1):
            emp = f"Employee_{e}"
            if self.counters["work_days"][emp] > 223:
                violations.append(f"{emp} exceeds 223 workdays: {self.counters['work_days'][emp]}")
            if self.counters["work_holidays_sunday"][emp] > 22:
                violations.append(f"{emp} exceeds 22 Sundays/holidays: {self.counters['work_holidays_sunday'][emp]}")
            if self.counters["consecutive_days"][emp] > 5:
                violations.append(f"{emp} has >5 consecutive days: {self.counters['consecutive_days'][emp]}")
            for d in range(1, self.num_days):
                if self.schedule[f"E{e},{d},T"] == "T" and self.schedule[f"E{e},{d+1},M"] == "M":
                    violations.append(f"{emp} has T->M transition on day {d}->{d+1}")

        return violations if violations else ["Schedule is valid"]

smar_task = SmarTask()
success = smar_task.generate_schedule()
if success:
    smar_task.export()
    for violation in smar_task.verify():
        print(violation)
else:
    print("Failed to generate a valid schedule.")
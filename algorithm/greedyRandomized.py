import random
from collections import defaultdict
import holidays

class GreedyRandomized:
    def __init__(self, employees, num_days, holidays, vacations, minimums, ideals, teams, num_iter=10):
        self.employees = employees   
        self.num_days = num_days     
        self.holidays = set(holidays)
        self.vacations = vacations   
        self.minimums = minimums     
        self.ideals = ideals         
        self.teams = teams           
        self.num_iter = num_iter
        self.assignment = defaultdict(list)    
        self.schedule_table = defaultdict(list)

    def f1(self, p, d, s):
        assignments = self.assignment[p]

        days = sorted([day for (day, _, _) in assignments] + [d])
        count = 1
        for i in range(1, len(days)):
            if days[i] == days[i-1] + 1:
                count += 1
                if count > 5:
                    return False
            else:
                count = 1

        sundays_and_holidays = sum(1 for (day, _, _) in assignments if day in self.holidays)
        if d in self.holidays:
            sundays_and_holidays += 1
        if sundays_and_holidays > 22:
            return False

        for (day, shift, _) in assignments:
            if shift == 2 and day + 1 == d and s == 1:
                return False
            if shift == 1 and day - 1 == d and s == 2:
                return False

        return True

    def f2(self, d, s, t):
        current = len(self.schedule_table[(d, s, t)])
        min_required = self.minimums.get((d, s, t), 0)
        ideal_required = self.ideals.get((d, s, t), min_required)

        if current < min_required:
            return 0
        elif current < ideal_required:
            return 1
        else:
            return 2 + (current - ideal_required)

    def build_schedule(self):
        all_days = set(range(1, self.num_days + 1))

        while not self.is_complete():
            P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 1]
            if not P:
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 2]

            if not P:
                break

            p = random.choice(P)
            f_value = float('inf')
            count = 0
            best = None
            available_days = list(all_days - {day for (day, _, _) in self.assignment[p]} - set(self.vacations.get(p, [])))

            while f_value > 0 and count < self.num_iter and available_days:
                d = random.choice(available_days)
                s = random.choice([1, 2])

                if self.f1(p, d, s):
                    count += 1
                    for t in self.teams[p]:
                        f_aux = self.f2(d, s, t)
                        if f_aux < f_value:
                            f_value = f_aux
                            best = (d, s, t)

            if best:
                d, s, t = best
                self.assignment[p].append((d, s, t))
                self.schedule_table[(d, s, t)].append(p)

    def is_complete(self):
        return all(len(self.assignment[p]) >= 223 for p in self.employees)


def schedule():
    num_employees = 12
    employees = list(range(num_employees))
    num_days = 365  
    holiDays = holidays.country_holidays("PT", years=[2025])

    vacations = {emp: list(range(1 + i * 30, 1 + i * 30 + 30)) for i, emp in enumerate(employees)}

    teams = {
        "E1": [1], "E2": [1], "E3": [1], "E4": [1],
        "E5": [1, 2], "E6": [1, 2], "E7": [1], "E8": [1],
        "E9": [1], "E10": [2], "E11": [1, 2], "E12": [2]
    }

    minimums = {}
    ideals = {}
    for day in range(1, num_days + 1):
        for shift in [1, 2]:
            for team in [1, 2]:
                minimums[(day, shift, team)] = 2
                ideals[(day, shift, team)] = 4

    scheduler = GreedyRandomized(employees, num_days, holiDays, vacations, minimums, ideals, teams)
    scheduler.build_schedule()

    for emp in employees:
        print(f"\nSchedule for {emp} ({len(scheduler.assignment[emp])} working days):")
        for (day, shift, team) in sorted(scheduler.assignment[emp]):
            shift_str = "M" if shift == 1 else "T"
            print(f"  Day {day}: {shift_str}, Team {team}")

    print("\nSchedule generation complete.")

schedule()
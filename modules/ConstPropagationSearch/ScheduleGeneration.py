from calendar import day_abbr, monthrange, weekday
import csv
import random

class SmarTask:
    def __init__(self):
        self.counters = {}
        self.num_teams = 2
        self.num_employees = 10 
        self.days = list(range(1, 366))
        self.num_days = len(self.days) 
        self.shifts = ["M", "T"] 
        self.variables = []
        self.employees = []
        self.work = {}
        self.domain = ["0", "M", "T", "F", "L"]
        self.holidays = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}

    def generateVariables(self):
        """Gera as variáveis do problema sem realizar alocações."""
        self.variables = [
            f"E{e},{d},{s}"
            for e in range(1, self.num_employees + 1)
            for d in range(1, self.num_days + 1)
            for s in self.shifts
        ]

        self.work = { f: 0 for f in self.variables }

        self.employees = [f"Employee_{i}" for i in range(1, self.num_employees + 1)]

        self.counters = {
            "work_days": {f: 0 for f in self.employees}, 
            "work_holidays_sunday": {f: 0 for f in self.employees},
            "consecutive_days": {f: 0 for f in self.employees}, 
            "vacations": {f: set(random.sample(self.days, 30)) for f in self.employees},
            "days_off": {f: 0 for f in self.employees}, 
            "alarm_days": list(range(1, 366, 7)), 
        }

    def constraint_consecutive_shift(self, x1, x2):
        x1 = x1[1:]
        x2 = x2[1:]
        e1, d1, s1 = x1.split(",")
        e2, d2, s2 = x2.split(",")
        if e1 != e2:
            return True
        if d1 == d2:
            return False
        if abs(int(d1) - int(d2)) != 1:
            return True
        if d1 > d2 and s1 == "M" and s2 == "T":
            return False
        if d1 < d2 and s1 == "T" and s2 == "M":
            return False
        return True

    def constraint_max_workdays(self, x):
        e, _, _ = x.split(",")
        return self.counters["work_days"][f"Employee_{e}"] <= 223
    
    def constraint_max_sundays_holidays(self, x):
        e, d, _ = x.split(",")
        if d in self.holidays or int(d) % 7 == 0:   # This will need alteration, the week may not begin on a Monday
            return self.counters["work_holidays_sunday"][f"Employee_{e}"] <= 22
        return True
    
    def constraint_max_consecutive_days(self, x):
        e, _, _ = x.split(",")
        return self.counters["consecutive_days"][f"Employee_{e}"] <= 5
    
    def constraint_vacation_days(self, x):
        e, d, _ = x.split(",")
        return d not in self.counters["vacations"][f"Employee_{e}"]

    def check_vacation_days(self, x):
        e, d, _ = x.split(",")
        return d not in self.counters["vacations"][f"Employee_{e}"]
    
    # def vacation_days(self, employee):
    #     employee = employee.split("_")[1]
    #     self.counters["vacations"][employee] = [
    #         d for var in self.work if self.work[var] == "F" for e, d, _ in var.split(",") if e == employee
    #     ]
    #     self.counters["days_off"][employee] += len(self.counters["vacations"][employee])

    def work_days(self, employee):
        employee = employee.split("_")[1]
        self.counters["work_days"][employee] = len([
            var for var in self.work
            if self.work[var] == "M" or self.work[var] == "T"
            and len(var.split(",")) == 3 
            and var.split(",")[0][1:] == employee
        ])

        self.counters["work_holidays_sunday"][employee] = len([
            var for var in self.work
            if self.work[var] == "M" or self.work[var] == "T"
            and len(var.split(",")) == 3 
            and var.split(",")[0][1:] == employee
            and (int(var.split(",")[1]) % 7 == 0 or int(var.split(",")[1]) in self.holidays)
        ])


    def consecutive_days(self, employee):
        employee = employee.split("_")[1]
        workdays = sorted([
            int(var.split(",")[1]) for var in self.work
            if self.work[var] == "M" or self.work[var] == "T"
            and len(var.split(",")) == 3 
            and var.split(",")[0][1:] == employee
        ])
        max_streak = 0
        current_streak = 1
        for i in range(1, len(workdays)):
            if workdays[i] == workdays[i - 1] + 1: 
                current_streak += 1
            else:
                max_streak = max(max_streak, current_streak)
                current_streak = 1 

        max_streak = max(max_streak, current_streak)
        self.counters["consecutive_days"][employee] = max_streak

    def vacation_days(self, employee):
        vacation_days = self.counters["vacations"][employee]
        employee = employee.split("_")[1]
        for i in vacation_days:
            self.work[f"E{employee},{i},M"] = "F"
            self.work[f"E{employee},{i},T"] = "F"

    def generateSchedule(self):
        """Gera o calendário respeitando as restrições."""
        self.generateVariables()

        for d in self.days:
            assigned = set()
            for shift in self.shifts:
                available_variables = [
                    var for var in self.variables
                    if self.constraint_max_workdays(var[1:])
                    and self.constraint_max_sundays_holidays(var[1:])
                    and self.constraint_max_consecutive_days(var[1:])
                    and self.constraint_vacation_days(var[1:])
                    and var[1:].split(",")[0] not in assigned 
                ]

                if available_variables:
                    selected_var = random.choice(available_variables)
                    print(selected_var)
                    self.work[selected_var] = shift
                    assigned.add(selected_var.split(",")[0][1:]) 

                    print(f"Employee_{selected_var.split(',')[0][1:]}")
                    employee = f"Employee_{selected_var.split(',')[0][1:]}"
                    self.vacation_days(employee)
                    self.work_days(employee)
                    self.consecutive_days(employee)

                if len(assigned) < 2:
                    fallback_variables = [
                        var for var in self.variables if var.endswith(f",{d},M") or var.endswith(f",{d},T")
                    ]
                    while len(assigned) < 2 and fallback_variables:
                        selected_var = random.choice(fallback_variables)
                        if selected_var.split(",")[0][1:] not in assigned: 
                            self.work[selected_var] = selected_var.split(",")[2]  
                            assigned.add(selected_var.split(",")[0][1:])

    def export(self, archive_name="schedule_J.csv"):
        """Exporta a escala de trabalho para um CSV anual."""
        with open(archive_name, mode='w', newline='') as file:
            writer = csv.writer(file)

            # Cabeçalho com os dias representados corretamente por monthes
            month_days = []
            for month in range(1, 13):
                for day in range(1, monthrange(2025, month)[1] + 1):
                    month_days.append(day)

            writer.writerow([""] + month_days)

            def calculate_weekDay(day):
                month, month_day = 1, day
                while month_day > monthrange(2025, month)[1]:
                    month_day -= monthrange(2025, month)[1]
                    month += 1
                return day_abbr[weekday(2025, month, month_day)]
            
            writer.writerow([""] + [calculate_weekDay(day) for day in self.days])

            for employee in self.employees:
                line = [employee]
                for day in self.days:
                    morning_shift = self.work.get(f"E{employee.split('_')[1]},{day},M")
                    afternoon_shift = self.work.get(f"E{employee.split('_')[1]},{day},T")

                    if morning_shift == "M":
                        line.append("M")
                    elif afternoon_shift == "T":
                        line.append("T")
                    elif morning_shift == "F" or afternoon_shift == "F":
                        line.append("F")
                    else:
                        line.append("0")

                writer.writerow(line)

    def verify(self):
        for employee in self.employees:
            self.consecutive_days(employee)
            self.work_days(employee)
            self.consecutive_days(employee)
            for day in self.days:
                for shift in self.shifts:
                    if not self.constraint_consecutive_shift(f"{employee.split('_')[1]},{day},{shift}", f"{employee.split('_')[1]},{day+1},{shift}"):
                        print(f"Employee {employee} has consecutive shifts on day {day} ({shift})")
                    if not self.constraint_max_workdays(f"{employee.split('_')[1]},{day},{shift}"):
                        print(f"Employee {employee} has more than 223 workdays")
                    if not self.constraint_max_sundays_holidays(f"{employee.split('_')[1]},{day},{shift}"):
                        print(f"Employee {employee} has more than 22 sundays/holidays")
                    if not self.constraint_max_consecutive_days(f"{employee.split('_')[1]},{day},{shift}"):
                        print(f"Employee {employee} has more than 5 consecutive days")
                    if not self.constraint_vacation_days(f"{employee.split('_')[1]},{day},{shift}"):
                        print(f"Employee {employee} has vacation on day {day}")
    


# Exemplo de uso
smar_task = SmarTask()
smar_task.generateSchedule()
smar_task.export()
smar_task.verify()

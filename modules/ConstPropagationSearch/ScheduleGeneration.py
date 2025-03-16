import random

class SmarTask:
    def __init__(self):
        self.counters = {}
        self.num_teams = 2
        self.num_employees = 50 
        self.days = list(range(1, 366))
        self.num_days = len(self.days) 
        self.shifts = ["M", "T"] 
        self.variables = []
        self.employees = []
        self.work = {}
        self.domain = ["0", "1", "F", "L"]
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
        if d1 == d2 and s1 == s2:
            return False
        if abs(int(d1) - int(d2)) != 1:
            return True
        if d1 > d2 and s1 == "M" and s2 == "T":
            return True
        if d1 < d2 and s1 == "T" and s2 == "M":
            return True
        return False

    def constraint_max_workdays(self, x):
        e, _, _ = x.split(",")
        return self.counters["work_days"][f"Employee_{e}"] <= 223
    
    def constraint_max_sundays_holidays(self, x):
        e, d, _ = x.split(",")
        if d in self.counters["alarm_days"] or int(d) % 7 == 0:   # This will need alteration, the week may not begin on a Monday
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
            if self.work[var] == "1"
            and len(var.split(",")) == 3 
            and var.split(",")[0][1:] == employee
        ])

        self.counters["work_holidays_sunday"][employee] = len([
            var for var in self.work
            if self.work[var] == "1"
            and len(var.split(",")) == 3 
            and var.split(",")[0][1:] == employee
            and (int(var.split(",")[1]) % 7 == 0 or int(var.split(",")[1]) in self.holidays)
        ])


    def consecutive_days(self, employee):
        employee = employee.split("_")[1]
        workdays = sorted([
            int(var.split(",")[1]) for var in self.work
            if self.work[var] == "1"
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
                    self.work[selected_var] = "1"
                    assigned.add(selected_var.split(",")[0][1:]) 

                    print(f"Employee_{selected_var.split(',')[0][1:]}")
                    employee = f"Employee_{selected_var.split(',')[0][1:]}"
                    self.work_days(employee)
                    self.consecutive_days(employee)

    def displaySchedule(self, days=365):
        """Exibe a programação para os primeiros dias especificados."""
        print("Generated Schedule (First {} Days)".format(days))
        for d in range(1, days + 1):
            print(f"\nDay {d}:")
            for shift in self.shifts:
                assigned = [e for e in self.employees if self.work.get(f"E{e.split('_')[1]},{d},{shift}", "0") == "1"]
                print(f"  {shift} Shift: {', '.join(assigned) if assigned else 'No Assignment'}")
    


# Exemplo de uso
smar_task = SmarTask()
smar_task.generateSchedule()
smar_task.displaySchedule()


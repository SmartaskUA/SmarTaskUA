class SmarTask:
    def __init__(self):
        self.counters = {}
        self.num_teams = 2
        self.num_employees = 50 
        self.num_days = 365 
        self.shifts = ["M", "T"] 
        self.variables = []
        self.employees = []
        self.work = {}
        self.domain = ["0", "1", "F", "L"]

    def gerar_variaveis(self):
        """Gera as variáveis do problema sem realizar alocações."""
        self.variables = [
            f"E{e},{d},{s}"
            for e in range(1, self.num_employees + 1)
            for d in range(1, self.num_days + 1)
            for s in self.shifts
        ]

        self.work = { f: 0 for f in self.variables }

        self.employees = [f"Funcionario_{i}" for i in range(1, self.num_employees + 1)]

        self.counters = {
            "dias_trabalhados": {f: 0 for f in self.employees}, 
            "domingos_feriados_trabalhados": {f: 0 for f in self.employees},
            "dias_consecutivos": {f: 0 for f in self.employees}, 
            "ferias": {f: [] for f in self.employees},
            "dias_ferias_folga": {f: 0 for f in self.employees}, 
            "dias_com_alarme": list(range(1, 366, 7)), 
        }

    def constraint_consecutive_shift(self, x1, x2):
        x1 = x1[1:]
        x2 = x2[1:]
        e1, d1, s1 = x1.split(",")
        e2, d2, s2 = x2.split(",")
        if e1 != e2:
            return True
        if d1 == d2:
            return True
        if abs(int(d1) - int(d2)) != 1:
            return True
        if d2 > d1:
            if s1 == "T" and s2 == "M":
                return False
        if d1 > d2:
            if s1 == "M" and s2 == "T":
                return False
        return True

    def constraint_max_workdays(self, x):
        e, _, _ = x.split(",")
        return self.counters["dias_trabalhados"][e] <= 223
    
    def constraint_max_sundays_holidays(self, x):
        e, d, _ = x.split(",")
        if d in self.counters["dias_com_alarme"] or d % 7 == 0:   # This will need alteration, the week may not begin on a Monday
            return self.counters["domingos_feriados_trabalhados"][e] <= 22
        return True
    
    def constraint_max_consecutive_days(self, x):
        e, _, _ = x.split(",")
        return self.counters["dias_consecutivos"][e] <= 5
    
    def constraint_vacation_days(self, x):
        e, d, _ = x.split(",")
        return d not in self.counters["ferias"][e]

    def check_vacation_days(self, employee):
        employee = employee.split("_")[1]
        return len(self.counters["ferias"][employee]) == 30
    
    def vacation_days(self, employee):
        employee = employee.split("_")[1]
        self.counters["ferias"][employee] = [
            d for var in self.work if self.work[var] == "F" for e, d, _ in var.split(",") if e == employee
        ]
        self.counters["dias_ferias_folga"][employee] += len(self.counters["ferias"][employee])

    def work_days(self, employee):
        employee = employee.split("_")[1]
        self.counters["dias_trabalhados"][employee] = len([
            var for var in self.work if self.work[var] == "1" for e, _, _ in var.split(",") if e == employee
        ])

    def consecutive_days(self, employee):
        employee = employee.split("_")[1]
        workdays = sorted(
            [int(d) for var in self.work if self.work[var] == "1"
            for e, d, _ in var.split(",") if e == employee]
        )
        max_streak = 0
        current_streak = 1
        for i in range(1, len(workdays)):
            if workdays[i] == workdays[i - 1] + 1:  # Consecutive days
                current_streak += 1
            else:
                max_streak = max(max_streak, current_streak)
                current_streak = 1 

        max_streak = max(max_streak, current_streak)
        self.counters["dias_consecutivos"][employee] = max_streak

    

    def iniciar_solucao(self):
        """Inicializa as variáveis para o problema."""
        self.gerar_variaveis()
        return self.variables


# Exemplo de uso
smar_task = SmarTask()
variaveis = smar_task.iniciar_solucao()
print(variaveis[:20])
print(len(variaveis))


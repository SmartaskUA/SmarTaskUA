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
        self.domain = ["0", "1", "F"]

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

        # Inicializando variáveis para restrições por funcionário
        self.counters = {
            "dias_trabalhados": {f: 0 for f in self.employees},  # Dias totais trabalhados no ano
            "domingos_feriados_trabalhados": {f: 0 for f in self.employees},  # Domingos e feriados trabalhados
            "dias_consecutivos": {f: 0 for f in self.employees},  # Dias consecutivos trabalhados
            "ferias": {f: [] for f in self.employees},  # Lista de dias de férias por funcionário
            "dias_com_alarme": list(range(1, 366, 7)),  # Exemplo: Alarme a cada 7 dias (ajustável)
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
        return self.counters["dias_trabalhados"][e] == 223
    
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
        for i in self.work:
            e, d, s = i.split(",")
            if e[1:] == employee and self.work[i] == "F":
                self.counters["ferias"][employee].append(d)

    def work_days(self, employee):
        employee = employee.split("_")[1]
        for i in self.work:
            e, d, s = i.split(",")
            if e[1:] == employee and self.work[i] == "1":
                self.counters["dias_trabalhados"][employee] += 1

    def consecutive_days(self, employee):
        employee = employee.split("_")[1]
        for i in self.work:
            e, d, s = i.split(",")
            if e[1:] == employee and self.work[i] == "1":
                self.counters["dias_consecutivos"][employee] += 1
            elif e[1:] == employee and self.work[i] == "0":
                self.counters["dias_consecutivos"][employee] = 0

    

    def iniciar_solucao(self):
        """Inicializa as variáveis para o problema."""
        self.gerar_variaveis()
        return self.variables


# Exemplo de uso
smar_task = SmarTask()
variaveis = smar_task.iniciar_solucao()
print(variaveis[:20])
print(len(variaveis))


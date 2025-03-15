class SmarTask:
    def __init__(self):
        self.restrictions = {}
        self.num_teams = 2
        self.num_employees = 50 
        self.num_days = 365 
        self.shifts = ["M", "T"] 
        self.variables = []

    def gerar_variaveis(self):
        """Gera as variáveis do problema sem realizar alocações."""
        self.variables = [
            f"E{e},{d},{s}"
            for e in range(1, self.num_employees + 1)
            for d in range(1, self.num_days + 1)
            for s in self.shifts
        ]

        # Inicializando variáveis para restrições por funcionário
        # self.restrictions = {
        #     "dias_trabalhados": {f: 0 for f in self.funcionarios},  # Dias totais trabalhados no ano
        #     "domingos_feriados_trabalhados": {f: 0 for f in self.funcionarios},  # Domingos e feriados trabalhados
        #     "dias_consecutivos": {f: 0 for f in self.funcionarios},  # Dias consecutivos trabalhados
        #     "turno_anterior": {f: None for f in self.funcionarios},  # Último turno do funcionário
        #     "sequencia_turnos": {f: [] for f in self.funcionarios},  # Sequência de turnos por funcionário
        #     "ferias": {f: [] for f in self.funcionarios},  # Lista de dias de férias por funcionário
        #     "dias_com_alarme": list(range(1, 366, 7)),  # Exemplo: Alarme a cada 7 dias (ajustável)
        # }

    def iniciar_solucao(self):
        """Inicializa as variáveis para o problema."""
        self.gerar_variaveis()
        return self.variables


# Exemplo de uso
smar_task = SmarTask()
variaveis = smar_task.iniciar_solucao()
print(variaveis[:20])


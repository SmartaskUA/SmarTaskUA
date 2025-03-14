class SmarTask:
    def __init__(self):
        self.funcionarios = []
        self.dias = []
        self.turnos = []
        self.variaveis = {}

    def gerar_variaveis(self):
        """Gera as variáveis do problema sem realizar alocações."""
        self.funcionarios = [f"Funcionario_{i}" for i in range(1, 51)]  # Exemplo: 50 funcionários
        self.dias = list(range(1, 366))  # 365 dias do ano
        self.turnos = ["Manhã", "Tarde"]

        # Inicializando variáveis para restrições por funcionário
        self.variaveis = {
            "funcionarios": self.funcionarios,
            "dias": self.dias,
            "turnos": self.turnos,
            "dias_trabalhados": {f: 0 for f in self.funcionarios},  # Dias totais trabalhados no ano
            "domingos_feriados_trabalhados": {f: 0 for f in self.funcionarios},  # Domingos e feriados trabalhados
            "dias_consecutivos": {f: 0 for f in self.funcionarios},  # Dias consecutivos trabalhados
            "turno_anterior": {f: None for f in self.funcionarios},  # Último turno do funcionário
            "sequencia_turnos": {f: [] for f in self.funcionarios},  # Sequência de turnos por funcionário
            "ferias": {f: [] for f in self.funcionarios},  # Lista de dias de férias por funcionário
            "dias_com_alarme": list(range(1, 366, 7)),  # Exemplo: Alarme a cada 7 dias (ajustável)
        }

    def iniciar_solucao(self):
        """Inicializa as variáveis para o problema."""
        self.gerar_variaveis()
        return self.variaveis


# Exemplo de uso
smar_task = SmarTask()
variaveis = smar_task.iniciar_solucao()
print(variaveis.get("sequencia_turnos"))

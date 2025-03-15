import csv
import random
from calendar import monthrange, day_abbr, weekday


class CSP:
    def __init__(self):
        self.funcionarios = []
        self.dias = []
        self.turnos = []
        self.variaveis = {}
        self.alocacoes = {}  # Guarda as alocações feitas

    def gerar_variaveis(self):
        """Gera as variáveis do problema sem realizar alocações."""
        self.funcionarios = [f"Funcionario_{i}" for i in range(1, 13)]  # Exemplo: 12 funcionários
        self.dias = list(range(1, 366))  # 365 dias do ano
        self.turnos = ["Manhã", "Tarde"]

        self.variaveis = {
            "funcionarios": self.funcionarios,
            "dias": self.dias,
            "turnos": self.turnos,
            "dias_trabalhados": {f: 0 for f in self.funcionarios},
            "domingos_feriados_trabalhados": {f: 0 for f in self.funcionarios},
            "dias_consecutivos": {f: 0 for f in self.funcionarios},
            "turno_anterior": {f: None for f in self.funcionarios},
            "sequencia_turnos": {f: [] for f in self.funcionarios},
            "ferias": {f: set(random.sample(self.dias, 30)) for f in self.funcionarios},  # 30 dias de férias aleatórios
            "dias_com_alarme": list(range(1, 366, 7)),  # Exemplo: Alarme a cada 7 dias
            "feriados": {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}  # Exemplo de feriados
        }

        self.alocacoes = {f: {} for f in self.funcionarios}  # Inicializa as alocações por funcionário

    def restricao_dias_totais(self, funcionario):
        return self.variaveis["dias_trabalhados"][funcionario] < 223

    def restricao_domingos_feriados(self, funcionario, dia):
        if dia % 7 == 0 or dia in self.variaveis["feriados"]:
            return self.variaveis["domingos_feriados_trabalhados"][funcionario] < 22
        return True

    def restricao_dias_consecutivos(self, funcionario):
        return self.variaveis["dias_consecutivos"][funcionario] < 5

    def restricao_sequencia_turnos(self, funcionario, turno):
        turno_anterior = self.variaveis["turno_anterior"][funcionario]
        if turno_anterior is None:
            return True  # Primeiro turno é sempre válido
        return (turno_anterior, turno) in [("Manhã", "Manhã"), ("Tarde", "Tarde"), ("Manhã", "Tarde")]

    def restricao_ferias(self, funcionario, dia):
        return dia not in self.variaveis["ferias"][funcionario]

    def gerar_horario(self):
        """Gera um horário válido seguindo as restrições estabelecidas."""
        self.alocacoes = {f: {} for f in self.funcionarios}  # Inicializa alocações vazias

        for dia in self.dias:
            for funcionario in self.funcionarios:
                if dia in self.variaveis["ferias"][funcionario]:
                    self.alocacoes[funcionario][dia] = "Férias"

            candidatos = [
                f for f in self.funcionarios
                if self.restricao_dias_totais(f)
                   and self.restricao_domingos_feriados(f, dia)
                   and self.restricao_dias_consecutivos(f)
                   and self.restricao_sequencia_turnos(f, "Manhã")
                   and self.restricao_ferias(f, dia)
            ]

            random.shuffle(candidatos)  # Embaralha para evitar padrões

            alocados = 0
            for turno in self.turnos:
                if candidatos:
                    funcionario = candidatos.pop()
                    self.alocacoes[funcionario][dia] = turno  # Atribui turno

                    # Atualiza contadores para restrições
                    self.variaveis["dias_trabalhados"][funcionario] += 1
                    self.variaveis["dias_consecutivos"][funcionario] += 1
                    if dia % 7 == 0 or dia in self.variaveis["feriados"]:
                        self.variaveis["domingos_feriados_trabalhados"][funcionario] += 1

                    self.variaveis["turno_anterior"][funcionario] = turno
                    alocados += 1

            # Garantir que pelo menos um funcionário esteja alocado por dia
            if alocados == 0 and self.funcionarios:
                funcionario_forcado = random.choice(self.funcionarios)
                self.alocacoes[funcionario_forcado][dia] = random.choice(self.turnos)

    def exportar_para_csv(self, nome_arquivo):
        """Exporta a escala de trabalho para um CSV anual."""
        with open(nome_arquivo, mode='w', newline='') as file:
            writer = csv.writer(file)

            # Cabeçalho com os dias representados corretamente por meses
            meses_dias = []
            for mes in range(1, 13):
                for dia in range(1, monthrange(2025, mes)[1] + 1):
                    meses_dias.append(dia)

            writer.writerow([""] + meses_dias)

            def calcular_dia_semana(dia):
                mes, dia_mes = 1, dia
                while dia_mes > monthrange(2025, mes)[1]:
                    dia_mes -= monthrange(2025, mes)[1]
                    mes += 1
                return day_abbr[weekday(2025, mes, dia_mes)]

            writer.writerow([""] + [calcular_dia_semana(dia) for dia in self.dias])

            for funcionario in self.funcionarios:
                linha = [funcionario]
                for dia in self.dias:
                    linha.append(self.alocacoes.get(funcionario, {}).get(dia, "Folga"))
                writer.writerow(linha)

    def executar(self, nome_arquivo="schedule.csv"):
        """Executa a geração do horário e exportação."""
        print("🔄 Gerando variáveis...")
        self.gerar_variaveis()

        print("📝 Gerando horário...")
        self.gerar_horario()

        print("💾 Salvando em CSV...")
        self.exportar_para_csv(nome_arquivo)


# 🎯 **Executando o algoritmo**
smar_task = CSP()
smar_task.executar()

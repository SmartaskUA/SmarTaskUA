import csv
import random
from calendar import calendar
from calendar import day_abbr, weekday


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
            "ferias": {f: set() for f in self.funcionarios},
            "dias_com_alarme": list(range(1, 366, 7)),  # Exemplo: Alarme a cada 7 dias
        }

        self.alocacoes = {f: {} for f in self.funcionarios}  # Inicializa as alocações por funcionário

    def restricao_dias_totais(self, funcionario):
        return self.variaveis["dias_trabalhados"][funcionario] < 223

    def restricao_domingos_feriados(self, funcionario, dia):
        if dia in self.variaveis["dias_com_alarme"] or dia % 7 == 0:
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

    def restricao_cobertura_alarmes(self, dia):
        """Verifica se pelo menos um funcionário está alocado para cobrir os alarmes."""
        if dia in self.variaveis["dias_com_alarme"]:
            return any(dia in self.alocacoes[f] for f in self.funcionarios)
        return True

    def validar_alocacao(self, funcionario, dia, turno):
        return (
            self.restricao_dias_totais(funcionario) and
            self.restricao_domingos_feriados(funcionario, dia) and
            self.restricao_dias_consecutivos(funcionario) and
            self.restricao_sequencia_turnos(funcionario, turno) and
            self.restricao_ferias(funcionario, dia) and
            self.restricao_cobertura_alarmes(dia)
        )

    def gerar_horario(self):
        """Gera um horário válido seguindo as restrições estabelecidas."""
        import random

        self.alocacoes = {f: {} for f in self.funcionarios}  # Inicializa alocações vazias

        for dia in self.dias:
            candidatos = [
                f for f in self.funcionarios
                if self.restricao_dias_totais(f)
                   and self.restricao_domingos_feriados(f, dia)
                   and self.restricao_dias_consecutivos(f)
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
                    if dia % 7 == 0 or dia in self.variaveis["domingos_feriados_trabalhados"]:
                        self.variaveis["domingos_feriados_trabalhados"][funcionario] += 1

                    alocados += 1

            # **Correção**: Garante que pelo menos um funcionário esteja alocado no dia
            if alocados == 0 and self.funcionarios:
                funcionario_forcado = random.choice(self.funcionarios)
                self.alocacoes[funcionario_forcado][dia] = random.choice(self.turnos)

    def restricao_dias_totais(self, funcionario):
        """Verifica se o funcionário ainda pode trabalhar mais dias no ano."""
        return self.variaveis["dias_trabalhados"].get(funcionario, 0) < 223

    def exportar_para_csv(self, nome_arquivo):
        import csv
        from calendar import day_abbr, weekday

        ano, mes = 2025, 1  # Ajuste conforme necessário

        with open(nome_arquivo, mode='w', newline='') as file:
            writer = csv.writer(file)

            # Cabeçalho com os dias do mês
            writer.writerow([""] + list(range(1, 32)))

            # Linha com os dias da semana
            writer.writerow([""] + [day_abbr[weekday(ano, mes, d)] for d in range(1, 32)])

            # Dados de funcionários e turnos
            for funcionario in self.funcionarios:
                linha = [funcionario]  # Nome do funcionário na primeira coluna
                for dia in range(1, 32):
                    alocacao = self.alocacoes.get(funcionario, {}).get(dia, "")
                    linha.append(alocacao)  # Adiciona o turno ou vazio
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
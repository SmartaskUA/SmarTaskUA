import csv
import random
from calendar import monthrange, weekday


class CSP:
    def __init__(self):
        self.funcionarios = [f"Funcionario_{i}" for i in range(1, 13)]  # 12 funcionários
        self.dias = list(range(1, 366))  # 365 dias do ano
        self.turnos = ["Manhã", "Tarde"]
        self.feriados = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}  # Exemplo de feriados
        self.ferias = {f: set(random.sample(self.dias, 30)) for f in self.funcionarios}  # 30 dias de férias aleatórios

        self.alocacoes = {f: {} for f in self.funcionarios}
        self.dias_trabalhados = {f: 0 for f in self.funcionarios}
        self.domingos_feriados_trabalhados = {f: 0 for f in self.funcionarios}
        self.dias_consecutivos = {f: 0 for f in self.funcionarios}
        self.turno_anterior = {f: None for f in self.funcionarios}

    def obter_mes_dia(self, dia):
        """Converte um número de dia do ano para (mês, dia do mês)."""
        mes = 1
        while dia > monthrange(2025, mes)[1]:
            dia -= monthrange(2025, mes)[1]
            mes += 1
        return mes, dia

    def validar_restricoes(self, funcionario, dia, turno):
        """Verifica se a alocação atende a todas as restrições."""

        # Restrição de dias totais no ano
        if self.dias_trabalhados[funcionario] >= 223:
            return False

        # Restrição de domingos e feriados
        mes, dia_mes = self.obter_mes_dia(dia)
        if dia in self.feriados or weekday(2025, mes, dia_mes) == 6:  # Domingo
            if self.domingos_feriados_trabalhados[funcionario] >= 22:
                return False

        # Restrição de 5 dias consecutivos no máximo
        if self.dias_consecutivos[funcionario] >= 5:
            return False

        # Restrição de sequência de turnos
        turno_anterior = self.turno_anterior[funcionario]
        if turno_anterior:
            if (turno_anterior, turno) not in [("Manhã", "Manhã"), ("Tarde", "Tarde"), ("Manhã", "Tarde")]:
                return False

        # Restrição de férias
        if dia in self.ferias[funcionario]:
            return False

        return True

    def backtrack(self, dia=1):
        """Resolve a escala usando busca com propagação de restrições."""
        if dia > 365:
            return True  # Solução encontrada

        for turno in self.turnos:
            for funcionario in self.funcionarios:
                if self.validar_restricoes(funcionario, dia, turno):
                    # Alocar funcionário
                    self.alocacoes[funcionario][dia] = turno
                    self.dias_trabalhados[funcionario] += 1
                    self.dias_consecutivos[funcionario] += 1
                    self.turno_anterior[funcionario] = turno

                    # Atualiza contagem de domingos/feriados
                    mes, dia_mes = self.obter_mes_dia(dia)
                    if dia in self.feriados or weekday(2025, mes, dia_mes) == 6:
                        self.domingos_feriados_trabalhados[funcionario] += 1

                    # Verifica se consegue resolver os próximos dias
                    if self.backtrack(dia + 1):
                        return True  # Encontrou solução válida

                    # Backtracking (desfaz alocação)
                    del self.alocacoes[funcionario][dia]
                    self.dias_trabalhados[funcionario] -= 1
                    self.dias_consecutivos[funcionario] -= 1
                    self.turno_anterior[funcionario] = None
                    if dia in self.feriados or weekday(2025, mes, dia_mes) == 6:
                        self.domingos_feriados_trabalhados[funcionario] -= 1

        return False  # Nenhuma alocação possível

    def exportar_para_csv(self, nome_arquivo):
        """Exporta a escala para um arquivo CSV."""
        with open(nome_arquivo, mode='w', newline='') as file:
            writer = csv.writer(file)

            # Cabeçalho com os dias
            writer.writerow(["Funcionário"] + list(range(1, 366)))

            for funcionario in self.funcionarios:
                linha = [funcionario]
                for dia in self.dias:
                    linha.append(self.alocacoes.get(funcionario, {}).get(dia, "Folga"))
                writer.writerow(linha)

    def executar(self, nome_arquivo="schedule.csv"):
        """Executa a geração do horário e exportação."""
        print("🔄 Gerando horário com propagação de restrições...")
        if self.backtrack():
            print("✅ Horário gerado com sucesso!")
            self.exportar_para_csv(nome_arquivo)
            print(f"📂 Exportado para {nome_arquivo}")
        else:
            print("❌ Não foi possível encontrar um horário válido.")


# 🎯 Executando o algoritmo
smar_task = CSP()
smar_task.executar()

import csv
import random
from calendar import monthrange, weekday


class CSP:
    def __init__(self):
        self.funcionarios = [f"Funcionario_{i}" for i in range(1, 13)]
        self.dias = [(mes, dia) for mes in range(1, 13) for dia in range(1, monthrange(2025, mes)[1] + 1)]
        self.turnos = ["Manhã", "Tarde"]
        self.feriados = {(1, 1), (12, 25), (4, 25), (5, 1), (6, 10)}  # Exemplo de feriados reais
        self.dias_com_alarme = self.dias[::7]  # Exemplo simplificado

        # Estado das variáveis de restrição
        self.dias_trabalhados = {f: 0 for f in self.funcionarios}
        self.domingos_feriados_trabalhados = {f: 0 for f in self.funcionarios}
        self.dias_consecutivos = {f: 0 for f in self.funcionarios}
        self.turno_anterior = {f: None for f in self.funcionarios}
        self.ferias = {f: set(random.sample(self.dias, 30)) for f in self.funcionarios}

        self.alocacoes = {f: {dia: "Folga" for dia in self.dias} for f in self.funcionarios}
        self.memo_feriados = {}

    def is_feriado_ou_domingo(self, data):
        mes, dia = data
        if data not in self.memo_feriados:
            self.memo_feriados[data] = data in self.feriados or weekday(2025, mes, dia) == 6
        return self.memo_feriados[data]

    def restricoes_validas(self, funcionario, data, turno):
        if self.dias_trabalhados[funcionario] >= 223:
            return False
        if self.is_feriado_ou_domingo(data) and self.domingos_feriados_trabalhados[funcionario] >= 22:
            return False
        if self.dias_consecutivos[funcionario] >= 5:
            return False
        if self.turno_anterior[funcionario] == "Tarde" and turno == "Manhã":
            return False
        if data in self.ferias[funcionario]:
            return False
        return True

    def gerar_horario(self):
        print("🔄 Iniciando geração de horários...")
        for data in self.dias:
            candidatos = [f for f in self.funcionarios if self.restricoes_validas(f, data, "Manhã")]
            candidatos.sort(key=lambda f: self.dias_trabalhados[f])

            if not candidatos:
                print(f"⚠️ Nenhum funcionário disponível para o dia {data}! Alocação forçada!")
                # Forçar alocação ignorando restrições
                candidatos = sorted(self.funcionarios, key=lambda f: self.dias_trabalhados[f])

            for turno in self.turnos:
                if candidatos:
                    funcionario = candidatos.pop(0)
                    self.alocacoes[funcionario][data] = turno
                    self.dias_trabalhados[funcionario] += 1
                    self.dias_consecutivos[funcionario] += 1
                    self.turno_anterior[funcionario] = turno
                    if self.is_feriado_ou_domingo(data):
                        self.domingos_feriados_trabalhados[funcionario] += 1

    def exportar_para_csv(self, nome_arquivo="schedule.csv"):
        with open(nome_arquivo, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Funcionario"] + [f"{dia}/{mes}" for mes, dia in self.dias])
            for funcionario in self.funcionarios:
                writer.writerow([funcionario] + [self.alocacoes[funcionario].get(data, "Folga") for data in self.dias])
        print("💾 Escala exportada para", nome_arquivo)

    def executar(self):
        self.gerar_horario()
        self.exportar_para_csv()

# 🚀 Executando
csp = CSP()
csp.executar()

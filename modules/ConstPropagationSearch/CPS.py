import csv
import random
from calendar import monthrange, day_abbr, weekday


class CSP:
    def __init__(self):
        self.funcionarios = [f"Funcionario_{i}" for i in range(1, 13)]
        self.dias = list(range(1, 366))
        self.turnos = ["Manhã", "Tarde"]
        self.feriados = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}  # Exemplo
        self.dias_com_alarme = list(range(1, 366, 7))

        # Estado das variáveis de restrição
        self.dias_trabalhados = {f: 0 for f in self.funcionarios}
        self.domingos_feriados_trabalhados = {f: 0 for f in self.funcionarios}
        self.dias_consecutivos = {f: 0 for f in self.funcionarios}
        self.turno_anterior = {f: None for f in self.funcionarios}
        self.ferias = {f: set(random.sample(self.dias, 30)) for f in self.funcionarios}

        self.alocacoes = {f: {} for f in self.funcionarios}
        self.memo_feriados = {}

    def is_feriado_ou_domingo(self, dia):
        if dia not in self.memo_feriados:
            self.memo_feriados[dia] = dia in self.feriados or weekday(2025, (dia - 1) // 31 + 1,
                                                                      (dia - 1) % 31 + 1) == 6
        return self.memo_feriados[dia]

    def restricoes_validas(self, funcionario, dia, turno):
        if self.dias_trabalhados[funcionario] >= 223:
            return False
        if self.is_feriado_ou_domingo(dia) and self.domingos_feriados_trabalhados[funcionario] >= 22:
            return False
        if self.dias_consecutivos[funcionario] >= 5:
            return False
        if self.turno_anterior[funcionario] == "Tarde" and turno == "Manhã":
            return False
        if dia in self.ferias[funcionario]:
            return False
        return True

    def forward_checking(self, funcionario, dia):
        """Remove futuras possibilidades inválidas"""
        if self.dias_trabalhados[funcionario] + (365 - dia) < 223:
            return False  # Já inviabiliza o limite total
        return True

    def gerar_horario(self):
        """Gera um horário seguindo as restrições com heurísticas"""
        print("🔄 Iniciando geração de horários...")
        dias_ordenados = sorted(self.dias,
                                key=lambda d: sum(self.restricoes_validas(f, d, "Manhã") for f in self.funcionarios))

        for dia in dias_ordenados:
            candidatos = [f for f in self.funcionarios if self.restricoes_validas(f, dia, "Manhã")]
            candidatos.sort(key=lambda f: self.dias_trabalhados[f])  # Escolhe quem trabalhou menos

            if not candidatos:
                print(f"⚠️ Nenhum funcionário disponível para o dia {dia}, alocação forçada!")
                continue

            for turno in self.turnos:
                if candidatos:
                    funcionario = candidatos.pop(0)
                    self.alocacoes[funcionario][dia] = turno
                    self.dias_trabalhados[funcionario] += 1
                    self.dias_consecutivos[funcionario] += 1
                    self.turno_anterior[funcionario] = turno
                    if self.is_feriado_ou_domingo(dia):
                        self.domingos_feriados_trabalhados[funcionario] += 1

                    if not self.forward_checking(funcionario, dia):
                        print(f"❌ Forward Checking: Removendo {funcionario} por impossibilidade futura!")
                        candidatos.remove(funcionario)

    def exportar_para_csv(self, nome_arquivo="schedule.csv"):
        """Exporta a escala de trabalho para CSV"""
        with open(nome_arquivo, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Dia"] + self.funcionarios)
            for dia in self.dias:
                writer.writerow([dia] + [self.alocacoes[f].get(dia, "Folga") for f in self.funcionarios])
        print("💾 Escala exportada para", nome_arquivo)

    def executar(self):
        """Executa geração e exportação"""
        self.gerar_horario()
        self.exportar_para_csv()


# 🚀 Executando
csp = CSP()
csp.executar()

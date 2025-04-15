import csv
from calendar import monthrange, weekday


def carregar_schedule(nome_arquivo):
    """Carrega o schedule a partir de um arquivo CSV."""
    schedule = {}
    with open(nome_arquivo, mode='r', newline='') as file:
        reader = list(csv.reader(file))
        dias = reader[0][1:]  # Ignora a primeira célula vazia
        funcionarios = [linha[0] for linha in reader[2:]]

        for i, funcionario in enumerate(funcionarios):
            schedule[funcionario] = {int(dias[j]): reader[i + 2][j + 1] for j in range(len(dias))}

    return schedule


def validar_restricoes(schedule):
    """Valida as restrições no schedule."""
    erros = []

    for funcionario, dias in schedule.items():
        dias_trabalhados = 0
        domingos_feriados = 0
        dias_consecutivos = 0
        turno_anterior = None
        dias_ferias = 0
        consecutivos = 0

        for mes in range(1, 13):
            for dia in range(1, monthrange(2025, mes)[1] + 1):
                dia_absoluto = sum(monthrange(2025, m)[1] for m in range(1, mes)) + dia
                turno = dias.get(dia_absoluto, "Folga")

                # Contagem de dias trabalhados
                if turno != "Folga":
                    dias_trabalhados += 1
                    consecutivos += 1
                    if weekday(2025, mes, dia) == 6 or dia_absoluto in {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}:
                        domingos_feriados += 1

                    # Verificar sequências inválidas
                    if turno_anterior == "Tarde" and turno == "Manhã":
                        erros.append(f"Erro: {funcionario} fez sequência inválida (T->M) no dia {dia}/{mes}")
                else:
                    consecutivos = 0
                    dias_ferias += 1

                # Verificar sequência máxima de 5 dias consecutivos
                if consecutivos > 5:
                    erros.append(
                        f"Erro: {funcionario} trabalhou mais de 5 dias consecutivos antes de folgar (dia {dia}/{mes})")

                turno_anterior = turno

        # Verificações finais
        if dias_trabalhados > 223:
            erros.append(f"Erro: {funcionario} trabalhou mais de 223 dias no ano ({dias_trabalhados} dias)")
        if domingos_feriados > 22:
            erros.append(f"Erro: {funcionario} trabalhou mais de 22 domingos/feriados ({domingos_feriados} dias)")
        if dias_ferias < 30:
            erros.append(f"Erro: {funcionario} tirou menos de 30 dias de férias ({dias_ferias} dias)")

    return erros


# Teste do validador
schedule = carregar_schedule("schedule.csv")
erros = validar_restricoes(schedule)
if erros:
    print("❌ Restrições violadas:")
    for erro in erros:
        print(erro)
else:
    print("✅ Schedule válido!")

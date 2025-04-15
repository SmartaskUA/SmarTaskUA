# from . import CSPSolver
from ..Formulation import Variaveis, Restricoes

if __name__ == "__main__":
    # Criar variáveis e domínios
    variaveis_obj = Variaveis()
    funcionarios = list(range(1, 4))  # Exemplo: 3 funcionários
    dias_no_ano = 7  # Exemplo: 7 dias

    variaveis = variaveis_obj.criar_variaveis(funcionarios, dias_no_ano)

    # Criar restrições
    restricoes_obj = Restricoes()

    # Restrição 1: Sequência inválida T → M
    restricoes_obj.adicionar_restricao_local(
        "Sequência inválida T → M",
        ["X_1_1", "X_1_2"],
        lambda valores: not (valores[0] == "T" and valores[1] == "M")  # Correto
    )

    # Restrição 2: Máximo de 5 dias consecutivos de trabalho
    for f in funcionarios:
        for i in range(dias_no_ano - 4):
            restricoes_obj.adicionar_restricao_local(
                f"Máximo de 5 dias consecutivos de trabalho - Funcionário {f}",
                [f"X_{f}_{i + k}" for k in range(5)],
                lambda *turnos: sum(1 for turno in turnos if turno in ["M", "T"]) <= 5
            )

    # Restrição 3: M → M e T → T (sequências válidas)
    for f in funcionarios:
        for i in range(dias_no_ano - 1):
            restricoes_obj.adicionar_restricao_local(
                f"Sequência válida M → M ou T → T - Funcionário {f}",
                [f"X_{f}_{i}", f"X_{f}_{i + 1}"],
                lambda *valores: (valores[0] == valores[1]) if valores[0] in ["M", "T"] else True
            )

    # Restrição 4: No máximo 223 dias de trabalho por ano
    for f in funcionarios:
        restricoes_obj.adicionar_restricao_global(
            f"Máximo de 223 dias de trabalho por ano - Funcionário {f}",
            [f"X_{f}_{d}" for d in range(dias_no_ano)],
            lambda *dias: sum(1 for dia in dias if dia in ["M", "T"]) <= 223
        )

    # Restrição 5: No máximo 22 domingos e feriados
    domingos_feriados = [0, 6]  # Exemplo: Dias 0 e 6 são domingos/feriados
    for f in funcionarios:
        restricoes_obj.adicionar_restricao_global(
            f"Máximo de 22 domingos e feriados - Funcionário {f}",
            [f"X_{f}_{d}" for d in domingos_feriados],
            lambda *dias: sum(1 for dia in dias if dia in ["M", "T"]) <= 22
        )

    # Restrição 6: Cobertura mínima por turno (manhã e tarde)
    for d in range(dias_no_ano):
        restricoes_obj.adicionar_restricao_global(
            f"Cobertura mínima por turno no dia {d}",
            [f"X_{f}_{d}" for f in funcionarios],
            lambda *turnos: turnos.count("M") >= 1 and turnos.count("T") >= 1
        )

    # Restrição 7: Turnos de férias ("F") em 30 dias
    for f in funcionarios:
        restricoes_obj.adicionar_restricao_global(
            f"Exatamente 30 dias de férias - Funcionário {f}",
            [f"X_{f}_{d}" for d in range(dias_no_ano)],
            lambda *dias: dias.count("F") == 30
        )

    # Obter restrições
    restricoes = restricoes_obj.obter_restricoes()

    # Usar o solver CSP
    csp_solver = CSPSolver()
    solucao_csp = csp_solver.buscar_solucao(variaveis, restricoes)
    print(f"Solução CSP encontrada: {solucao_csp}")

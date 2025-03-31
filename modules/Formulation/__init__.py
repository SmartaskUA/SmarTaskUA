from .restricoes import Restricoes
from .variaveis import Variaveis

if __name__ == "__main__":
    # Criar variáveis e domínios
    # A criaçao das variavies devem ser suportadas pelo acesso a base de dados e comunicaçao com message broker para receber a copnfiguraçoa
    variaveis_obj = Variaveis()
    funcionarios = list(range(1, 13))  # 12 funcionários
    dias_no_ano = 365

    # Criar variáveis sem valores de configuração
    variaveis = variaveis_obj.criar_variaveis(funcionarios, dias_no_ano)

    # Criar restrições
    restricoes_obj = Restricoes()

    # Definir limites para restrições
    max_dias_trabalhados = 223
    max_dias_trabalho_domingos_feriados = 22
    max_consecutivos = 5
    min_cobertura = 180

    # 1. Restrições Globais: 22 dias de trabalho máximo em domingos e feriados
    restricoes_obj.adicionar_restricao_global(
        "Máximo de 22 dias de trabalho em domingos e feriados",
        variaveis.keys(),
        lambda X: sum(X[dia] != 'F' for dia in range(1, dias_no_ano + 1) if dia in range(1, 366)),  # Exemplificando com dias fictícios
        {"limite": max_dias_trabalho_domingos_feriados}
    )

    # 2. Restrições Globais: 223 dias de trabalho no ano
    restricoes_obj.adicionar_restricao_global(
        "Máximo de 223 dias trabalhados",
        variaveis.keys(),
        lambda X: sum(x != 'F' for x in X) <= max_dias_trabalhados,
        {"limite": max_dias_trabalhados}
    )

    # 3. Restrição Local: Máximo de 5 dias consecutivos de trabalho
    restricoes_obj.adicionar_restricao_local(
        "Máximo de 5 dias consecutivos de trabalho",
        ["X_i_j", "X_i_j+1", "X_i_j+2", "X_i_j+3", "X_i_j+4"],
        lambda *turnos: not all(turno in ["M", "T"] for turno in turnos)
    )

    # 4. Restrição Local: Sequências de turnos válidas (M → M, T → T, M → T)
    restricoes_obj.adicionar_restricao_local(
        "Sequência válida M → M, T → T, M → T",
        ["X_i_j", "X_i_j+1"],
        lambda x, y: (x == "M" and y == "M") or (x == "T" and y == "T") or (x == "M" and y == "T")
    )

    # 5. Restrição Local: Sequência inválida T → M
    restricoes_obj.adicionar_restricao_local(
        "Sequência inválida T → M",
        ["X_i_j", "X_i_j+1"],
        lambda x, y: not (x == "T" and y == "M")
    )

    # 6. Restrições Globais: Cobrir alarmes (Exemplo: garantir cobertura mínima de turnos)
    restricoes_obj.adicionar_restricao_global(
        "Cobrir alarmes (mínima cobertura de turnos)",
        variaveis.keys(),
        lambda X: sum(1 for turno in X if turno != "F") >= min_cobertura,
        {"limite": min_cobertura}
    )

    # 7. Restrições Globais: 30 dias de férias obrigatórios por funcionário
    for funcionario in funcionarios:
        restricoes_obj.adicionar_restricao_global(
            f"30 dias de férias para funcionário {funcionario}",
            [f"X_{funcionario}_{j}" for j in range(1, dias_no_ano + 1)],
            lambda X: sum(1 for dia in X if dia == "Fer") >= 30,
            {"limite": 30}
        )

    # Exibir configuração final
    print(f"Variáveis formuladas: {len(variaveis)}")
    print(f"Restrições adicionadas: {len(restricoes_obj.obter_restricoes())}")

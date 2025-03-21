from restricoes import Restricoes
from PropagadorRestricoes import PropagadorRestricoes

if __name__ == "__main__":
    # Criar variáveis de teste (pequeno conjunto)
    funcionarios = [1]
    dias = 3
    variaveis = [f"X_{funcionario}_{dia}" for funcionario in funcionarios for dia in range(1, dias + 1)]

    print("Variáveis criadas:", variaveis)

    # Criar objeto de restrições
    restricoes_obj = Restricoes()

    # Adicionar restrição simples: sequência inválida "T → M"
    restricoes_obj.adicionar_restricao_local(
        "Sequência inválida T → M entre variáveis consecutivas",
        [variaveis[0], variaveis[1]],
        lambda x, y: not (x == "T" and y == "M")
    )
    restricoes_obj.adicionar_restricao_local(
        "Sequência inválida T → M entre variáveis consecutivas",
        [variaveis[1], variaveis[2]],
        lambda x, y: not (x == "T" and y == "M")
    )

    # Inicializar o propagador de restrições
    propagador = PropagadorRestricoes(variaveis, restricoes_obj)

    # Propagar restrições e reduzir os domínios
    propagador.propagate()

    # Exibir os domínios após a propagação
    print("\nDomínios após propagação:")
    for var, dominio in propagador.domains.items():
        print(f"{var}: {dominio}")

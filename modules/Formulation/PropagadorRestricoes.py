class PropagadorRestricoes:
    def __init__(self, variaveis, restricoes):
        self.domains = {var: ["M", "T", "F"] for var in variaveis}  # Domínio inicial
        self.constraints = restricoes.obter_restricoes()  # Carregar restrições locais e globais
        self.calls = 0

    def propagate(self):
        print("Restrições carregadas:", self.constraints)

        # Extrair as variáveis de cada restrição corretamente
        edges = [(restricao['variaveis'][0], restricao['variaveis'][1]) for restricao in self.constraints if
                 len(restricao['variaveis']) >= 2]

        while edges:
            vj, vi = edges.pop()

            # Filtrar e aplicar apenas as funções de restrição relevantes a vj e vi
            for restricao in self.constraints:
                if restricao['variaveis'] == [vj, vi]:
                    constraint_func = restricao['regra']
                    new_domain_vj = []

                    for xj in self.domains[vj]:
                        valid = False
                        for xi in self.domains[vi]:
                            if constraint_func(xj, xi):  # Aplica a função de restrição
                                valid = True
                                break
                        if valid:
                            new_domain_vj.append(xj)

                    if len(new_domain_vj) < len(self.domains[vj]):
                        print(f"Domínio reduzido para {vj}: {new_domain_vj}")
                        self.domains[vj] = new_domain_vj
                        edges += [(vk, vj) for restricao in self.constraints if restricao['variaveis'][0] == vj]


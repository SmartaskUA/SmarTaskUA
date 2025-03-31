class Restricoes:
    def __init__(self):
        """
        Inicializa as estruturas necessárias para armazenar as restrições.
        """
        self.restricoes_globais = []  # Restrições globais que afetam todo o problema.
        self.restricoes_locais = []   # Restrições locais que afetam variáveis específicas.

    def adicionar_restricao_global(self, nome, variaveis, regra, parametros=None):
        """
        Adiciona uma restrição global ao problema.

        Args:
            nome (str): Nome da restrição.
            variaveis (list): Lista de variáveis afetadas.
            regra (callable): Função lambda que define a regra da restrição.
            parametros (dict, opcional): Parâmetros adicionais da restrição.
        """
        self.restricoes_globais.append({
            "nome": nome,
            "variaveis": variaveis,
            "regra": regra,
            "parametros": parametros or {}
        })

    def adicionar_restricao_local(self, nome, variaveis, regra, parametros=None):
        """
        Adiciona uma restrição local ao problema.

        Args:
            nome (str): Nome da restrição.
            variaveis (tuple): Tupla de variáveis afetadas.
            regra (callable): Função lambda que define a regra da restrição.
            parametros (dict, opcional): Parâmetros adicionais da restrição.
        """
        self.restricoes_locais.append({
            "nome": nome,
            "variaveis": variaveis,
            "regra": regra,
            "parametros": parametros or {}
        })

    def obter_restricoes(self):
        """
        Retorna todas as restrições adicionadas (globais e locais).

        Returns:
            list: Lista de restrições globais e locais.
        """
        return self.restricoes_globais + self.restricoes_locais

class ConfiguracaoProblema:
    """
    Classe que encapsula as configurações e parâmetros globais do problema.
    Inclui limites e sequências válidas/inválidas.
    """

    def __init__(self):
        self.configuracao = {
            "max_dias_trabalhados": 223,
            "max_dias_consecutivos": 5,
            "min_dias_ferias": 30,
            "sequencias_validas": [("M", "M"), ("T", "T"), ("M", "T")],
            "sequencias_invalidas": [("T", "M")]
        }

    def obter_configuracao(self):
        return self.configuracao

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any


class FormuladorDeProblema(ABC):
    """
    Interface que padroniza a formulação de problemas genéricos.
    Define os métodos necessários para a criação de variáveis, domínios e restrições.
    """

    @abstractmethod
    def criar_variaveis_e_dominios(self, dados: Dict[str, Any]) -> Dict[str, List[str]]:
        """Converte os dados de entrada em variáveis e seus domínios possíveis."""
        pass

    @abstractmethod
    def definir_restricoes(self) -> List[Dict[str, Any]]:
        """Define as restrições do problema."""
        pass

    @abstractmethod
    def configurar_problema(self) -> Dict[str, Any]:
        """Configura o problema com parâmetros globais e restrições adicionais."""
        pass


class FormuladorBase(FormuladorDeProblema):
    """
    Classe base que implementa a lógica genérica para criar variáveis, domínios e restrições.
    Pode ser estendida por formuladores mais específicos.
    """

    def __init__(self):
        self.variaveis = {}
        self.restricoes = []
        self.configuracao = {}

    def __str__(self):
        return f"Problema formulado com {len(self.variaveis)} variáveis e {len(self.restricoes)} restrições."

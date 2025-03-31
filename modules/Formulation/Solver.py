from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Optional


class Solver(ABC):
    """
    Interface Solver genérica para integrar algoritmos de solução (CSP, otimização, busca local, etc.).
    Define os métodos básicos para buscar soluções e propagar restrições.
    """

    @abstractmethod
    def buscar_solucao(self, variaveis: Dict[str, List[str]], restricoes: List[Dict[str, Any]]) -> Optional[
        Dict[str, str]]:
        """
        Executa a busca por uma solução viável para as variáveis e restrições fornecidas.

        Args:
            variaveis (Dict[str, List[str]]): As variáveis do problema e seus domínios.
            restricoes (List[Dict[str, Any]]): Lista de restrições que afetam as variáveis.

        Returns:
            Optional[Dict[str, str]]: Um dicionário que representa a solução encontrada (ou None se não houver solução).
        """
        pass

    @abstractmethod
    def propagar_restricoes(self, variaveis: Dict[str, List[str]], restricoes: List[Dict[str, Any]]) -> Dict[
        str, List[str]]:
        """
        Propaga restrições para reduzir os domínios das variáveis.

        Args:
            variaveis (Dict[str, List[str]]): As variáveis do problema e seus domínios.
            restricoes (List[Dict[str, Any]]): Lista de restrições a serem propagadas.

        Returns:
            Dict[str, List[str]]: Domínios reduzidos após a propagação de restrições.
        """
        pass

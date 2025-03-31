from typing import Dict, List


class Variaveis:
    """
    Classe responsável por criar e armazenar as variáveis e domínios do problema.
    """

    def __init__(self):
        self.variaveis = {}

    def criar_variaveis(self, funcionarios: List[int], dias: int) -> Dict[str, List[str]]:
        """
        Cria variáveis X_{i,j} para cada funcionário i e cada dia j, com os domínios possíveis.
        Exemplo de domínio: ["M", "T", "F"] (Manhã, Tarde, Folga).
        """
        self.variaveis = {
            f"X_{i}_{j}": ["M", "T", "F"]  # Manhã, Tarde, Folga
            for i in funcionarios
            for j in range(1, dias + 1)
        }
        return self.variaveis

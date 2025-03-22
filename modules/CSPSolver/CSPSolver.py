import time
import csv
import logging
from typing import Dict, List, Optional, Any
from Formulation.Solver import Solver

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class CSPSolver(Solver):
    """
    Solver baseado em CSP (Constraint Satisfaction Problem).
    Utiliza Backtracking básico para encontrar uma solução.
    """

    def buscar_solucao(self, variaveis: Dict[str, List[str]], restricoes: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        inicio = time.time()  # Início do contador de tempo

        def backtrack(atual: Dict[str, str]) -> Optional[Dict[str, str]]:
            # Verificar se a atribuição está completa (todas as variáveis atribuídas)
            if len(atual) == len(variaveis):
                logger.info("Solução completa encontrada!")
                return atual

            # Selecionar a próxima variável a ser atribuída
            var = self.selecionar_variavel_nao_atribuida(variaveis, atual)
            logger.info(f"Selecionando variável não atribuída: {var}")

            for valor in variaveis[var]:
                logger.info(f"Tentando atribuir {valor} a {var}")
                atual[var] = valor

                if self.verificar_consistencia(atual, restricoes):
                    logger.info(f"Atribuição consistente: {var} = {valor}")
                    resultado = backtrack(atual)
                    if resultado:
                        return resultado

                logger.info(f"Revertendo atribuição: {var} = {valor}")
                del atual[var]  # Reverter atribuição em caso de falha

            return None

        solucao = backtrack({})

        fim = time.time()
        logger.info(f"Tempo total de execução: {fim - inicio:.2f} segundos")

        if solucao:
            self.salvar_solucao_csv(solucao)
        else:
            logger.warning("Nenhuma solução encontrada.")

        return solucao

    def salvar_solucao_csv(self, solucao: Dict[str, str], filename: str = "schedule_result.csv"):
        """Salva a solução encontrada em um arquivo CSV no formato esperado."""
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Funcionário", "Dia", "Turno"])

            for key, value in sorted(solucao.items()):
                f, d = key.split('_')[1:]
                writer.writerow([f, d, value])

        logger.info(f"Solução salva em {filename}")

    def propagar_restricoes(self, variaveis: Dict[str, List[str]], restricoes: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        for restricao in restricoes:
            for var in restricao["variaveis"]:
                for valor in variaveis[var][:]:
                    if not restricao["regra"]([valor]):
                        variaveis[var].remove(valor)
        return variaveis

    def selecionar_variavel_nao_atribuida(self, variaveis: Dict[str, List[str]], atual: Dict[str, str]) -> str:
        return min((v for v in variaveis if v not in atual), key=lambda x: len(variaveis[x]))

    def verificar_consistencia(self, atual: Dict[str, str], restricoes: List[Dict[str, Any]]) -> bool:
        for restricao in restricoes:
            variaveis_restricao = restricao["variaveis"]
            valores = [atual.get(var, None) for var in variaveis_restricao]

            if all(valores) and not restricao["regra"](valores):
                logger.info(
                    f"Inconsistência detectada: {valores} falham na restrição {restricao.get('descricao', 'sem descrição')}")
                return False

        return True

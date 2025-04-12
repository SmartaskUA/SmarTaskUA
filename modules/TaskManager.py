# modules/TaskManager.py

from algorithm.CSP_joao import employee_scheduling

class TaskManager:
    def __init__(self):
        # No futuro, você pode adicionar suporte a múltiplos algoritmos aqui
        self.algorithms = {
            "CSP Scheduling": employee_scheduling
        }

    def run_task(self, task_id, title, algorithm_name="CSP Scheduling"):
        """
        Executa o algoritmo especificado e retorna o resultado.

        :param task_id: ID da tarefa
        :param title: Título associado ao calendário
        :param algorithm_name: Nome do algoritmo a ser executado
        :return: dicionário com dados do calendário gerado
        :raises: Exception se a execução falhar
        """
        if algorithm_name not in self.algorithms:
            raise ValueError(f"Algoritmo '{algorithm_name}' não encontrado.")

        print(f"[TaskManager] Executando algoritmo '{algorithm_name}' para Task ID: {task_id}")
        algorithm = self.algorithms[algorithm_name]
        schedule_data = algorithm()
        print(f"[TaskManager] Algoritmo '{algorithm_name}' finalizado com sucesso.")
        return schedule_data

import pandas as pd
import numpy as np

# Definir os funcionários (IDs genéricos por enquanto)
n_funcionarios = 12  # Ajuste conforme necessário
funcionarios = [f"F{i+1}" for i in range(n_funcionarios)]

# Definir os dias do ano de 2025
dias_ano = pd.date_range(start="2025-01-01", end="2025-12-31")

# Definir turnos
turnos = ["Manhã", "Tarde"]

# Feriados e domingos (placeholder, considerar feriados reais)
feriados_domingos = [dia for dia in dias_ano if dia.weekday() == 6]  # Apenas domingos como exemplo

# Variáveis de decisão: alocação de trabalho
# Dicionário com chaves (funcionário, dia, turno) e valor binário (1 se trabalha, 0 se não trabalha)
alocacao_trabalho = {(f, d, t): 0 for f in funcionarios for d in dias_ano for t in turnos}

# Contadores para restrições
contagem_dias_trabalhados = {f: 0 for f in funcionarios}
contagem_domingos_feriados = {f: 0 for f in funcionarios}

# Restrição de sequência (5 dias consecutivos)
sequencia_trabalho = {f: [] for f in funcionarios}  # Lista para rastrear sequência de trabalho

# Exibir algumas variáveis geradas como exemplo
print("Funcionários:", funcionarios)
print("Dias do ano:", dias_ano)
print("Turnos:", turnos)
print("Exemplo de alocação:", list(alocacao_trabalho.items())[:5])

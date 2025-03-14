import pandas as pd

#  Leitura do CSV e remoção de colunas irrelevantes
df = pd.read_csv("ex1.csv", header=0, dtype=str)  # Garantir que tudo é tratado como string

#  Remover colunas "Unnamed" (geralmente criadas por erros na leitura)
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

#  Verificar as colunas disponíveis no DataFrame
print("Colunas detectadas:", df.columns.tolist())

#  Identificar corretamente as colunas fixas e de escala
fixed_columns = ["Competencia", "Contrato", "Férias"]
schedule_columns = [col for col in df.columns if col not in fixed_columns]

#  Certificar-se de que todas as colunas de escala são strings válidas e sem valores NaN
df[schedule_columns] = df[schedule_columns].applymap(lambda x: x.strip() if isinstance(x, str) else "")

#  Imprimir uma amostra para depuração
print("Prévia do DataFrame tratado:\n", df.head())


#  Função para preencher os turnos vazios respeitando regras
def fill_gaps(df):
    for idx, row in df.iterrows():
        consecutive_days = 0
        last_shift = None

        for day in schedule_columns:
            current_value = row[day].strip()  # Remover espaços extras

            if not current_value:  # Se o valor estiver vazio
                new_shift = 'M' if last_shift != 'M' else 'T'

                #  Evitar mais de 5 dias consecutivos de trabalho
                if consecutive_days < 5:
                    df.at[idx, day] = new_shift
                    consecutive_days += 1
                    last_shift = new_shift
                else:
                    df.at[idx, day] = 'F'  # Dia de folga
                    consecutive_days = 0  # Resetar contagem
            else:
                last_shift = current_value
                consecutive_days = 0 if current_value == 'F' else consecutive_days + 1

    return df


#  Aplicar o preenchimento de escalas
df = fill_gaps(df)

#  Salvar a escala corrigida
df.to_csv("filled_schedule.csv", index=False)
print("✅ Escala gerada e salva como 'filled_schedule.csv'")

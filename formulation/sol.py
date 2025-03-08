import pandas as pd

# 📌 Leitura do CSV e remoção de colunas irrelevantes
df = pd.read_csv("ex1.csv", skiprows=[0], header=0)

# 🔍 Remover colunas "Unnamed" (geralmente criadas por erros na leitura)
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# 🔍 Verificar as colunas disponíveis no DataFrame
print("Colunas detectadas:", df.columns.tolist())

# 📌 Identificar corretamente as colunas fixas e de escala (ajustar conforme necessário)
fixed_columns = ["Competencia", "Contrato", "Férias"]
schedule_columns = [col for col in df.columns if col not in fixed_columns]

# 🔍 Certificar-se de que todas as colunas de escala são strings válidas e sem valores NaN
df[schedule_columns] = df[schedule_columns].astype(str).fillna("")

# 🔍 Imprimir uma amostra para depuração
print("Prévia do DataFrame tratado:\n", df.head())

# 📌 Função para preencher os turnos vazios respeitando as regras
def fill_gaps(df):
    for idx, row in df.iterrows():
        consecutive_days = 0
        last_shift = None

        for day in schedule_columns:
            if row[day] in ["nan", "None", ""]:  # Considerar valores ausentes
                new_shift = 'M' if last_shift != 'M' else 'T'

                # 🔍 Evitar mais de 5 dias consecutivos de trabalho
                if consecutive_days < 5:
                    df.at[idx, day] = new_shift
                    consecutive_days += 1
                    last_shift = new_shift
                else:
                    df.at[idx, day] = 'F'  # Dia de folga
                    consecutive_days = 0
            else:
                last_shift = row[day]
                consecutive_days = 0 if row[day] == 'F' else consecutive_days + 1

    return df

# 📌 Aplicar o preenchimento de escalas
df = fill_gaps(df)

# 📌 Salvar a escala corrigida
df.to_csv("filled_schedule.csv", index=False)
print("✅ Escala gerada e salva como 'filled_schedule.csv'")

import pandas as pd

df = pd.read_csv("Mins_R10-R62_30min.csv")

df["Hora"] = df["Hora"].astype(str)
mask = df["Hora"].str.contains("18:00-18:30")
mask1 = df["Hora"].str.contains("18:30-19:00")
# mask4 = df["Hora"].str.contains("11:00-11:30")

# Converter para numérico
for col in df.columns:
    if col != "Hora":
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Incrementar +1 exceto -1, apenas nas colunas 1, 4, 7, ...
cols = [col for col in df.columns if col != "Hora"]
for i in range(0, len(cols), 1):
    col = cols[i]
    df.loc[mask & (df[col] != -1), col] += 1
    df.loc[mask1 & (df[col] != -1), col] += 1
    # df.loc[mask4 & (df[col] != -1), col] += 1
# Converter para inteiros com NaN
for col in df.columns:
    if col != "Hora":
        df[col] = df[col].astype("Int64")


df.to_csv("Mins_R10-R62_30min_New.csv", index=False)

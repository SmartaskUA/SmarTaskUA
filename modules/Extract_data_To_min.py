"""
extract_calendar_by_roster.py

Lê um ficheiro Excel e cria uma folha por RosterCode.
Cada folha tem:
- Linhas = intervalos StartDate–EndDate
- Colunas = dias (Date)
- Valores = Persons
"""

import pandas as pd
from pathlib import Path

def build_roster_calendars(input_path: str, output_path: str):
    # Lê todos os dados
    df = pd.read_excel(input_path, engine="openpyxl")

    # Garante colunas esperadas
    required_cols = {"RosterCode", "Date", "StartDate", "EndDate", "Persons"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Faltam colunas no ficheiro: {missing}")

    # Normaliza datas e cria intervalo de horas
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df["StartDate"] = pd.to_datetime(df["StartDate"])
    df["EndDate"] = pd.to_datetime(df["EndDate"])
    df["Hora"] = df["StartDate"].dt.strftime("%H") + "-" + df["EndDate"].dt.strftime("%H")

    # Cria um ExcelWriter para salvar várias folhas
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for roster_code, subdf in df.groupby("RosterCode"):
            # Cria tabela pivô: linhas = hora, colunas = data, valores = Persons
            pivot = subdf.pivot_table(
                index="Hora", 
                columns="Date", 
                values="Persons", 
                aggfunc="first"  # se houver duplicados, pega o primeiro
            )

            # Ordena as horas
            pivot = pivot.sort_index(key=lambda x: x.str.extract(r"^(\d+)", expand=False).astype(int))

            # Escreve cada RosterCode numa folha separada
            sheet_name = str(roster_code)[:31]  # máximo permitido pelo Excel
            pivot.to_excel(writer, sheet_name=sheet_name)

    print(f"✅ Ficheiro Excel criado com sucesso em: {output_path}")


if __name__ == "__main__":
    # Exemplo de uso
    build_roster_calendars(
        input_path="/home/hugo/Desktop/SmarTaskUA/modules/2021-2022 Clientes estimados e Pessoas caixa.xlsx",
        output_path="/home/hugo/Desktop/SmarTaskUA/modules/extracted/Calendarios_por_Roster.xlsx"
    )

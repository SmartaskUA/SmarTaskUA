import pandas as pd
from datetime import datetime, timedelta


class ScheduleVariables:
    def __init__(self, csv_file, year=2025):
        self.year = year
        self.df = pd.read_csv(csv_file, skiprows=[0], header=0, index_col=False, engine="python")
        self.process_data()

    def process_data(self):
        # Remover colunas Unnamed
        self.df = self.df.loc[:, ~self.df.columns.str.contains('^Unnamed')]

        # Lista de funcionários
        self.employees = self.df.iloc[1:, 0].dropna().astype(str).tolist()

        # Equipes de cada funcionário
        self.teams = self.extract_teams()

        # Lista de dias do ano
        self.days = [datetime(self.year, 1, 1) + timedelta(days=i) for i in range(365)]

        # Turnos disponíveis
        self.shifts = ['M', 'T']  # Manhã (08:00-16:00) e Tarde (16:00-24:00)

        # Feriados do ano
        self.holidays = self.get_holidays()

        # Dias de férias de cada funcionário
        self.vacations = self.extract_vacations()

    def extract_teams(self):
        """Associa funcionários a suas equipes."""
        teams = {}
        current_team = None
        for _, row in self.df.iterrows():
            first_col = str(row.iloc[0]).strip()
            if "Equipa" in first_col:
                current_team = first_col
            elif first_col and current_team:
                teams[first_col] = current_team
        return teams

    def get_holidays(self):
        """Retorna a lista de feriados em Portugal para o ano especificado."""
        return [
            "2025-01-01", "2025-04-18", "2025-04-25", "2025-05-01", "2025-06-10",
            "2025-06-19", "2025-08-15", "2025-10-05", "2025-11-01", "2025-12-01", "2025-12-08", "2025-12-25"
        ]

    def extract_vacations(self):
        """Extrai os dias de férias de cada funcionário."""
        vacations = {}
        if "Férias" in self.df.columns:
            vacation_col = "Férias"
        else:
            vacation_col = self.df.columns[2]  # Assume que a terceira coluna contém as férias

        for _, row in self.df.iterrows():
            employee = str(row.iloc[0]).strip()
            if employee:
                try:
                    vacations[employee] = int(row[vacation_col]) if not pd.isna(row[vacation_col]) else 30
                except (KeyError, ValueError):
                    vacations[employee] = 30  # Se houver erro, assume 30 dias de férias
        return vacations

    def get_variables(self):
        """Retorna as variáveis extraídas e seus possíveis valores."""
        return {
            "employees": self.employees,  # Lista de funcionários
            "teams": self.teams,  # Associações funcionário -> equipe
            "days": self.days,  # Lista de dias do ano
            "shifts": self.shifts,  # Turnos disponíveis
            "holidays": self.holidays,  # Lista de feriados
            "vacations": self.vacations  # Dias de férias por funcionário
        }

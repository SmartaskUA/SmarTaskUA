import traceback
import pandas as pd
import re
import json
from datetime import date, datetime

import pandas as pd
import re

def extract_minimums_from_csv(file_path):
    """
    Lê o CSV gerado pelo algoritmo (formato EmpX / Day1..Day365)
    e calcula o número de funcionários por hora, por dia e por equipa.

    Retorna um dicionário no formato:
        {(day_number, '09-10', 'A'): 3, (day_number, '10-11', 'A'): 2, ...}
    """
    df = pd.read_csv(file_path, encoding="utf-8")
    df = df.fillna("")

    # detectar colunas de dias
    day_cols = [c for c in df.columns if re.match(r"Day\d+", c, re.IGNORECASE)]
    result = {}

    # extrair blocos de cada célula
    def parse_block(cell):
        m = re.match(r"^\s*(\d{1,2})[-_](\d{1,2})[-_](\d{1,2})[_\-]([A-Za-z])\s*$", str(cell).strip())
        if not m:
            return None
        start = int(m.group(1))
        break_h = int(m.group(2))
        end = int(m.group(3))
        team = m.group(4).upper()
        # horas efetivamente trabalhadas (sem pausa)
        hours = list(range(start, break_h)) + list(range(break_h + 1, end))
        return hours, team

    for day_col in day_cols: # iterar sobre as colunas de dias
        day_num = int(re.findall(r"\d+", day_col)[0])
        for _, row in df.iterrows(): # iterar sobre as linha
            cell = row[day_col] # obter o valor da célula
            parsed = parse_block(cell)
            if not parsed:
                continue
            hours, team = parsed # desempacotar horas () e equipa de trabalho
            for h in hours: 
                key = (day_num, f"{h:02d}-{h+1:02d}", team) # criar chave única
                result[key] = result.get(key, 0) + 1 # {(1, "09-10", "A"): 1}

    return result

def order_minimums(mins_dict):
    """
    Ordena o dicionário de mínimos por: Equipa → Hora → Dia
    
    Input:  {(362, '20-21', 'A'): 4, (363, '14-15', 'B'): 8, ...}
    
    Output: Ordenado como:
        - Equipa A, 09-10: [dia 1, dia 2, dia 3, ..., dia 365]
        - Equipa A, 10-11: [dia 1, dia 2, dia 3, ..., dia 365]
        - ...
        - Equipa B, 09-10: [dia 1, dia 2, dia 3, ..., dia 365]
        - ...
    
    Ordenação: key[2] (Equipa), key[1] (Hora), key[0] (Dia)
    """
    # Ordena por: Equipa (3º elemento), depois Hora (2º elemento), depois Dia (1º elemento)
    ordered = dict(sorted(mins_dict.items(), key=lambda x: (x[0][2], x[0][1], x[0][0])))
    
    print(f"\n[ORDER MINIMUMS]")
    print(f"  Total keys: {len(ordered)}")
    
    # Print exemplo do resultado
    print(f"\n  Ordered structure (Team → Hour → Day):")
    current_team = None
    current_hour = None
    for (day, hour, team), count in list(ordered.items())[:30]:  # Mostra primeiros 30
        if team != current_team:
            if current_team is not None:
                print()
            current_team = team
            current_hour = None
            print(f"  Team {team}:")
        if hour != current_hour:
            current_hour = hour
            print(f"    Hour {hour}:")
        print(f"      Day {day:3d}: {count} employees")
    
    return ordered

def add_feriados_and_sundays(mins_dict, all_teams_and_hours=None):
    """
    Adiciona entradas para dias falhados (feriados, domingos, etc.) ao dicionário.
    Os dias falhados são aqueles que não aparecem no dicionário.
    Para cada dia falhado adiciona uma entrada com valor -1 para todas as (hora, equipa).
    
    Args:
        mins_dict: Dicionário com formato {(day, 'HH-MM', team): count}
        all_teams_and_hours: Opcional. Tuple (teams_set, hours_set) para forçar equipas/horas.
                            Se None, usa as que encontra em mins_dict.
    
    Returns:
        mins_dict: Dicionário atualizado com entradas -1 para dias falhados (1-365)
    """
    
    if not mins_dict:
        return mins_dict
    
    # Extrair dias, horas e equipas presentes
    days_in_dict = set()
    hours_in_dict = set()
    teams_in_dict = set()
    
    for (day, hour, team) in mins_dict.keys():
        days_in_dict.add(day)
        hours_in_dict.add(hour)
        teams_in_dict.add(team)
    
    # Usar teams/hours fornecidas ou as do dicionário
    if all_teams_and_hours:
        teams_to_use, hours_to_use = all_teams_and_hours
    else:
        teams_to_use = teams_in_dict
        hours_to_use = hours_in_dict
    
    # Encontrar dias falhados no intervalo 1-365 (ano completo)
    all_days = set(range(1, 366))  # 1 a 365
    missing_days = sorted(all_days - days_in_dict)
    
    print(f"\n[ADD FERIADOS & SUNDAYS]")
    print(f"  Days present: {len(days_in_dict)} / 365")
    print(f"  Teams to cover: {sorted(teams_to_use)}")
    print(f"  Hours to cover: {sorted(hours_to_use)}")
    print(f"  Missing days: {len(missing_days)} ({missing_days[:15]}...)")
    
    # Adicionar entradas -1 para dias falhados
    added_count = 0
    for daynum in missing_days:
        for team in teams_to_use:
            for hour in hours_to_use:
                key = (daynum, hour, team)
                mins_dict[key] = -1
                added_count += 1
    
    print(f"  Total entries added: {added_count}")
    print(f"  Dictionary size: {len(mins_dict)}")
    print(f"Dictionary sample after adding missing days: {list(mins_dict.items())}")
    
    return mins_dict

def compare_minimums(mins_required, mins_actual):
    """
    Compara listas de mínimos requeridos com mínimos atuais.
    Retorna apenas o total de mínimos falhados (coverage gaps).
    
    Args:
        mins_required: Lista de valores ordenados [required1, required2, ...]
        mins_actual: Lista de valores ordenados [actual1, actual2, ...]
    
    Returns:
        int: Total de mínimos falhados (soma dos gaps onde gap > 0)
    
    Example:
        mins_required = [-1, 10, 8, -1, 6]
        mins_actual   = [-1,  8, 8, -1, 6]
        
        Return: 2 (gap de 2 na posição 1)
    """
    if not mins_required or not mins_actual:
        return 0
    
    total_gaps = 0
    min_length = min(len(mins_required), len(mins_actual))
    
    for i in range(min_length):
        if isinstance(mins_required[i], str) or isinstance(mins_actual[i], str):
            continue
        gap = mins_required[i] - mins_actual[i]
        if gap > 0:
            total_gaps += gap
    
    return total_gaps

def analyze(file, holidays, mins, employees, year=2025):
    """
    Analisa ficheiro horário (cada célula ex.: '9-18_A' ou '09-18_A' ou 'VACATION' / 'F').
    - holidays: conjunto de dias do ano (1-based) ou conjunto de datetime.dates.
    - mins: texto CSV dos requisitos por hora.
    - employees: JSON string ou lista de dicts com "name" e "teams".
    """

    print(f"[DEBUG] Entering analyze() in kpiVerification_Hours with {file}")
    print(f"[KPI Hours] Analyzing hourly file: {file}")

# --------------------------- Minimos ---------------------------

    #print(f"[DEBUG] Mins: {str(mins)[:6000]}")

    mins_F = extract_minimums_from_csv(file)
    #print(f"[DEBUG] Extracted mins_F keys sample: {mins_F}")

    mins_F_Ordered = order_minimums(mins_F)
    print(f"[DEBUG] Ordered mins_F sample: {list(mins_F_Ordered.items())[:200]}")

    mins_with_holidays = add_feriados_and_sundays(mins_F_Ordered)
    
    # Re-order after adding missing days to keep everything organized
    mins_final_ordered = order_minimums(mins_with_holidays)
    print(f"[DEBUG] Mins with holidays (final ordered) sample: {list(mins_final_ordered.items())[:200]}")

    mins_final_list = list(mins_final_ordered.values())
    print(f"[DEBUG] Final mins list sample: {mins_final_list[:200]}")
    
    missed_team_min = compare_minimums(mins, mins_final_list)

    print(f"[DEBUG] Minimus Falhados: {missed_team_min}")


# --------------------------- xxx ---------------------------

    df = pd.read_csv(file, encoding='ISO-8859-1', dtype=str).fillna("")

    # 🔹 Normalizar nome da coluna do funcionário
    col_names_lower = [c.lower() for c in df.columns]
    employee_col = None
    
    # Procurar por variações de nome de coluna
    if any("employee" in c.lower() for c in col_names_lower):
        employee_col = next(c for c in df.columns if "employee" in c.lower())
    elif any("funcionario" in c.lower() for c in col_names_lower):
        employee_col = next(c for c in df.columns if "funcionario" in c.lower())
    elif any("emp" in c.lower() for c in col_names_lower):
        employee_col = next(c for c in df.columns if "emp" in c.lower())
    else:
        # fallback: assume que a primeira coluna é o identificador do funcionário
        employee_col = df.columns[0]
    
    # Renomear para padrão interno
    if employee_col != "Employee":
        df.rename(columns={employee_col: "Employee"}, inplace=True)
    
    print(f"[KPI Hours] Employee column detected: {employee_col}")

    # Helpers --------------------------------------------------------------
    def parse_block(val):
        """
        Extrai (start, end, team) de células tipo '9-18_A' ou '09-18-A'.
        """
        if not isinstance(val, str):
            return (None, None, None)
        m = re.match(r'^\s*(\d{1,2})\s*-\s*(\d{1,2})\s*[_\-]\s*([A-Za-z])\s*$', val.strip())
        if m:
            return int(m.group(1)), int(m.group(2)), m.group(3).upper()
        return (None, None, None)

    def is_work_block(val):
        s, e, t = parse_block(val)
        return s is not None and e is not None and t is not None

    # ----------------------------------------------------------------------
    missed_work_days = 0
    missed_vacation_days = 0
    missed_team_min = 0
    missed_team_ideal = 0
    workHolidays = 0
    consecutiveDays = 0
    single_team_violations = 0
    team_satisfaction_values = []
    hourlyCoverageGaps = 0
    hourlyOverstaff = 0

    #print(f"[DEBUG] first 200 chars of mins: {str(mins)[:200]}")
    mins_dict, ideals_dict = parse_requirements_hourly(mins)
    print(f"[DEBUG] mins_dict keys sample: {list(mins_dict.keys())[:5]}")
    print(f"[DEBUG] ideals_dict keys sample: {list(ideals_dict.keys())[:5]}")
    teams = parse_employees(employees)
    print(f"[DEBUG] Parsed teams for employees: {list(teams.items())[:5]}")

    # 🔹 Normalizar holidays para set de datas (datetime.date objects)
    # Mantém as datas originais sem converter para day-of-year
    holidays_set = set()
    if holidays:
        print(f"[DEBUG] Input holidays type: {type(holidays).__name__}")
        
        # Se for um dicionário (de hl.country_holidays), usa as chaves
        if isinstance(holidays, dict):
            holidays_iterable = holidays.keys()
        else:
            holidays_iterable = holidays

        for h in holidays_iterable:
            try:
                print(f"[DEBUG] Processing holiday {h} of type {type(h).__name__}")
                
                if isinstance(h, datetime):
                    # datetime.datetime: extrai a data
                    d = h.date()
                    print(f"  → Converting datetime to date: {d}")
                    holidays_set.add(d)
                elif isinstance(h, date):
                    # datetime.date: adiciona diretamente
                    print(f"  → Adding date directly: {h}")
                    holidays_set.add(h)
                elif isinstance(h, int):
                    # Se for inteiro, assume que é day-of-year e tenta converter
                    # (compatibilidade com dados antigos)
                    print(f"  → Skipping int (day-of-year not supported in this context): {h}")
                    continue
                else:
                    # Fallback: tenta converter string/outro formato para data
                    print(f"  → Fallback: converting {type(h).__name__} to date")
                    d = pd.to_datetime(str(h)).date()
                    print(f"  → Converted to date: {d}")
                    holidays_set.add(d)
            except Exception as e:
                print(f"[ERROR] Failed to normalize holiday value {h} (type={type(h).__name__}): {e}")
                import traceback
                traceback.print_exc()

    print(f"[DEBUG] Normalized holidays_set (dates): {sorted(list(holidays_set))[:5]} ... total={len(holidays_set)}")



    # 🔹 Colunas dos dias
    dia_cols = [c for c in df.columns if re.match(r'^(Dia|Day)\s*\d+$', c, flags=re.I)]
    if not dia_cols:
        dia_cols = [c for c in df.columns if c.lower().startswith("dia") or c.lower().startswith("day")]

    # Mapa coluna → número do dia
    col_to_day = {}
    for c in dia_cols:
        m = re.search(r'(\d+)', c)
        if m:
            col_to_day[c] = int(m.group(1))
        else:
            col_to_day[c] = len(col_to_day) + 1

    # 🔹 Criar mapa de números de dia para datas reais
    # Assumindo que dia 1 é 1º de novembro de 2021
    start_date = date(2021, 11, 1)
    daynum_to_date = {}
    for daynum in col_to_day.values():
        daynum_to_date[daynum] = start_date + pd.Timedelta(days=daynum - 1)

    # Colunas especiais (feriados): compara datas reais
    all_special_cols = [col for col, daynum in col_to_day.items() 
                        if daynum in daynum_to_date and daynum_to_date[daynum] in holidays_set]

    print(f"[DEBUG] Holiday columns detected: {all_special_cols}")

    # ----------------------------------------------------------------------
    for _, row in df.iterrows():
        try:
            emp_val = row.get("Employee", row.iloc[0] if len(row) > 0 else None)
            emp_id = None
            if isinstance(emp_val, str):
                m = re.search(r'(\d+)', emp_val)
                if m:
                    emp_id = int(m.group(1))
            else:
                try:
                    emp_id = int(emp_val)
                except Exception:
                    emp_id = None
        except Exception as e:
            print(f"[WARNING] Error parsing employee row: {e}")
            continue

        # Contagem de dias
        worked_days = sum(1 for c in dia_cols if c in row.index and is_work_block(row[c]))
        vacation_days = sum(1 for c in dia_cols if c in row.index and str(row[c]).strip().upper() in ("F", "VACATION"))

        missed_work_days += abs(223 - worked_days)
        missed_vacation_days += abs(30 - vacation_days)

        total_worked_holidays = sum(1 for c in all_special_cols if c in row.index and is_work_block(row[c]))
        if total_worked_holidays > 22:
            workHolidays += (total_worked_holidays - 22)

        # 6+ dias consecutivos de trabalho
        work_seq = [1 if c in row.index and is_work_block(row[c]) else 0 for c in dia_cols]
        streak = 0
        fails = 0
        for v in work_seq:
            if v:
                streak += 1
                if streak >= 6:
                    fails += 1
            else:
                streak = 0
        consecutiveDays += fails

        # Equipas
        allowed_codes = teams.get(emp_id, []) if emp_id is not None else []
        team_counts = {}
        for c in dia_cols:
            if c in row.index:
                _, _, t = parse_block(row[c])
                if t:
                    team_counts[t] = team_counts.get(t, 0) + 1

        if len(allowed_codes) == 1:
            allowed = set(allowed_codes)
            worked = set(team_counts.keys())
            if worked - allowed:
                single_team_violations += 1

        if len(allowed_codes) >= 1:
            total_worked = sum(team_counts.values())
            if total_worked > 0:
                preferred = allowed_codes[0]
                pref_count = team_counts.get(preferred, 0)
                team_satisfaction_values.append(round((pref_count / total_worked) * 100, 2))
        

    # ----------------------------------------------------------------------
    team_satisfaction = (
        round(sum(team_satisfaction_values) / len(team_satisfaction_values), 2)
        if team_satisfaction_values
        else 0
    )


    return {
        "missedWorkDays": missed_work_days,
        "missedVacationDays": missed_vacation_days,
        "workHolidays": workHolidays,
        "consecutiveDays": consecutiveDays,
        "singleTeamViolations": single_team_violations,
        "missedTeamMin": missed_team_min,
        "missedTeamIdeal": missed_team_ideal,
        "teamSatisfactionLevel": team_satisfaction,
        "hourlyCoverageGaps": hourlyCoverageGaps,
        "hourlyOverstaff": hourlyOverstaff
    }

# ----------------------------------------------------------------------
def parse_requirements_hourly(requirements_text):
    mins, ideals = {}, {}
    if not requirements_text:
        print("[DEBUG] parse_requirements_hourly: empty input")
        return mins, ideals

    print(f"[DEBUG] parse_requirements_hourly: raw length={len(str(requirements_text))}")
    
    # Normalizar separadores e novas linhas
    text = requirements_text.replace('\r', '\n').replace(';', ',').strip()
    lines = [l for l in text.split('\n') if l.strip()]
    print(f"[DEBUG] Lines detected: {len(lines)}")
    
    # Se for tudo numa linha, tenta forçar split por "Team" keywords ou padrões
    if len(lines) == 1:
        long_line = lines[0]
        # tenta dividir em cada “A,”, “B,”, “C,”...
        chunks = re.split(r'(?=[A-Z]\s*,)', long_line)
        lines = [l.strip() for l in chunks if l.strip()]
        print(f"[DEBUG] Split long line into {len(lines)} logical entries")

    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 4:
            continue
        
                # Detectar padrão tipo "Equipa A,09-10"
        if len(parts) >= 3 and ("Equipa" in parts[1] or "Team" in parts[1]):
            # Exemplo: ['', 'Equipa A', '09-10', -1, 4, 3, 2...]
            team_code = parts[1].split()[-1].upper().strip()
            hour_range = parts[2]
            values = parts[3:]
            target = mins  # trata como mínimos
        elif len(parts) >= 3 and re.match(r'^\d{2}-\d{2}$', parts[1]):
            # Exemplo: ['Equipa A', '09-10', -1, 4, 3...]
            team_code = parts[0].split()[-1].upper().strip()
            hour_range = parts[1]
            values = parts[2:]
            target = mins
        else:
            # Fallback: ideal / min parsing normal
            team_label_raw, req_type, hour_range = parts[:3]
            values = parts[3:]
            team_match = re.search(r'([A-Za-z])$', team_label_raw)
            if not team_match:
                print(f"[DEBUG] Skipping invalid team_label: {team_label_raw}")
                continue
            team_code = team_match.group(1).upper()
            target = mins if 'min' in req_type.lower() else ideals

        for day_idx, val in enumerate(values, start=1):
            if val.isdigit():
                target[(day_idx, hour_range, team_code)] = int(val)
    
    print(f"[CHECK] Total mins={len(mins)} ideals={len(ideals)}")
    print(f"[CHECK] Sample mins: {list(mins.keys())[:10]}")

    print(f"[DEBUG] Created {len(mins)} mins and {len(ideals)} ideals")
    return mins, ideals


# ----------------------------------------------------------------------
def parse_employees(employees_json):
    teams = {}
    if not employees_json:
        return teams
    if isinstance(employees_json, str):
        try:
            employees_list = json.loads(employees_json)
        except Exception:
            employees_list = []
    else:
        employees_list = employees_json

    for emp in employees_list:
        name = emp.get("name", "")
        m = re.search(r'(\d+)', str(name))
        emp_id = int(m.group(1)) if m else emp.get("id", None)
        if emp_id is None:
            continue
        codes = []
        for t in emp.get("teams", []):
            mt = re.search(r'([A-Za-z])\s*$', str(t))
            if mt:
                codes.append(mt.group(1).upper())
        seen = set()
        codes = [c for c in codes if not (c in seen or seen.add(c))]
        teams[int(emp_id)] = codes
    return teams

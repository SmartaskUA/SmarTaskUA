import csv
import decimal
import os
from datetime import date, time
import pandas as pd
from collections import defaultdict
from time import sleep
import math

TEAM_CODE_TO_ID = {'A': 1, 'B': 2} # will be updated if there are more teams
TEAM_ID_TO_CODE = {v: k for k, v in TEAM_CODE_TO_ID.items()}

def get_team_code(s: str) -> str:
    """Extract a team code from labels like 'Equipa C', 'Team_D', 'C'."""
    if not s:
        return ""
    return s.strip().split()[-1].upper()

def get_team_id(code: str) -> int:
    """Return an id for a team code (A, B, C, ...), creating one if new."""
    code = code.strip().upper()
    if code not in TEAM_CODE_TO_ID:
        TEAM_CODE_TO_ID[code] = (max(TEAM_CODE_TO_ID.values(), default=0) + 1)
        TEAM_ID_TO_CODE[TEAM_CODE_TO_ID[code]] = code
    return TEAM_CODE_TO_ID[code]


def build_calendar(year: int):
    """
    Returns:
      dias_ano: list[pd.Timestamp] for every day of the given year
      sundays:  list[int] day-of-year indices (1..365/366) that fall on Sunday
    """
    dias_ano = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31').to_list()
    sundays = [d.dayofyear for d in dias_ano if d.weekday() == 6]  # Monday=0 ... Sunday=6
    return dias_ano, sundays

def parse_vacs_file(file_path: str):
    """
    CSV format: rows like 'Employee 1,0,1,0,...'
    Returns: dict[int, list[int]] -> {emp_id: [day_numbers_with_vacation]}
    """
    vacs = {}
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].startswith("Employee"):
                emp_id = int(row[0].split()[1])
                vacs[emp_id] = [i + 1 for i, val in enumerate(row[1:]) if val.strip() == "1"]
    return vacs

def rows_to_vac_dict(vac_rows):
    """
    vac_rows: rows like ['Employee 3', '0','1','0',...]
    Returns: {emp_id: [day_numbers]}
    """
    vacs = {}
    for row in vac_rows:
        emp_id = int(row[0].split()[-1])
        vacs[emp_id] = [
            idx + 1
            for idx, bit in enumerate(row[1:])
            if bit.strip() == '1'
        ]
    return vacs

# -----------------------------
# Requirements parsing
# -----------------------------

def parse_requirements_file(file_path: str):
    """
    Reads a fixed 8-row CSV layout and returns mins/ideals using
    normalized keys: (day:int, shift:int [1=M,2=T], team:int [1=A,2=B])

    Expected row indices (after header row):
      1:  A, M, Minimo
      2:  A, M, Ideal
      3:  A, T, Minimo
      4:  A, T, Ideal
      5:  B, M, Minimo
      6:  B, M, Ideal
      7:  B, T, Minimo
      8:  B, T, Ideal
    We only read the numeric day columns starting at col index 3.
    """
    from .utils import TEAM_LETTER_TO_ID 

    mins, ideals = {}, {}
    with open(file_path, newline='', encoding='ISO-8859-1') as f:
        rows = list(csv.reader(f))
        # day columns are after the first 3 meta columns
        day_indices = list(range(1, len(rows[0]) - 3 + 1))

        layout = {
            ("A", 1, "Minimo"): 1,
            ("A", 1, "Ideal"):  2,
            ("A", 2, "Minimo"): 3,
            ("A", 2, "Ideal"):  4,
            ("B", 1, "Minimo"): 5,
            ("B", 1, "Ideal"):  6,
            ("B", 2, "Minimo"): 7,
            ("B", 2, "Ideal"):  8,
        }

        for (team_letter, shift, kind), row_idx in layout.items():
            values = rows[row_idx][3:]  # numeric day columns
            team_id = TEAM_LETTER_TO_ID[team_letter]
            for day, val in zip(day_indices, values):
                try:
                    n = int(val)
                except (ValueError, TypeError):
                    continue
                key = (day, shift, team_id)  # <-- (day, shift, team_id)
                (mins if kind.lower().startswith('min') else ideals)[key] = n

    return mins, ideals

def rows_to_req_dicts(req_rows):
    """
    req_rows: rows like ['Equipa A','Minimo','M', <day1>, ...]
    Supports 'Equipa C', 'Team D', or just 'C' as the last token.
    """
    mins, ideals = {}, {}
    for row in req_rows:
        team_label, kind, shift_code, *counts = row

        # robust final token as team code (A, B, C, D, ...):
        team_code = team_label.strip().split()[-1].upper()
        team_id = get_team_id(team_code)

        code = shift_code.strip().upper()
        if code.startswith('M'):
            shift = 1
        elif code.startswith('T') or code.startswith('A'):
            shift = 2
        elif code.startswith('N'):
            shift = 3
        else:
            continue

        target = mins if kind.strip().lower().startswith('min') else ideals
        for day, value in enumerate(counts, start=1):
            v = str(value).strip()
            if v:
                target[(day, shift, team_id)] = int(v)
    return mins, ideals

def rows_to_req_dicts(req_rows):
    """
    Aceita ficheiros de requisitos (mínimos/ideais) tanto por turnos como por horas.
    Formatos suportados:
      - Turnos: Equipa A, Minimo, M, <dia1>, <dia2>, ...
      - Horas simples: Equipa A, 09-10, <dia1>, <dia2>, ...
      - Horas com minutos: Equipa A, 09:00-09:30, <dia1>, <dia2>, ...
    Retorna dois dicionários:
      mins[(day, hora_ou_turno, team_id)] e ideals[(day, hora_ou_turno, team_id)]
    """
    mins, ideals = {}, {}
    for row in req_rows:
        # Saltar linhas vazias ou que não começam com "Equipa"
        if not row or len(row) < 3:
            continue
        
        team_label = row[0].strip()
        if not team_label.upper().startswith('EQUIPA'):
            continue
        
        second_col = row[1].strip()
        
        # Detectar formato baseado na segunda coluna
        # Formato 1: Turnos → row[1]="Minimo/Ideal", row[2]="M/T/N"
        # Formato 2: Horas → row[1]="09-10" ou "09:00-09:30"
        
        team_code = get_team_code(team_label)
        team_id = get_team_id(team_code)
        
        # MODO 1: Formato de turnos (Equipa A, Minimo, M, ...)
        if second_col.lower() in ('minimo', 'ideal', 'mínimo'):
            if len(row) < 4:
                continue
                
            kind = second_col.lower()
            shift_code = row[2].strip().upper()
            counts = row[3:]
            
            if shift_code.startswith('M'):
                shift = 1
            elif shift_code.startswith('T') or shift_code.startswith('A'):
                shift = 2
            elif shift_code.startswith('N'):
                shift = 3
            else:
                continue
            
            target = mins if kind.startswith('min') else ideals
            for day, val in enumerate(counts, start=1):
                v = str(val).strip()
                if v and v != '0':
                    try:
                        target[(day, shift, team_id)] = int(v)
                    except ValueError:
                        continue
        
        # MODO 2: Formato de horas (Equipa A, 09-10, ...) ou (Equipa A, 09:00-09:30, ...)
        elif '-' in second_col:
            hour_label = second_col
            counts = row[2:]
            
            # Converter formato "09:00-09:30" para "09.0-09.5" (ILP format)
            if ':' in hour_label:
                try:
                    start_str, end_str = hour_label.split('-')
                    start_hour, start_min = map(int, start_str.split(':'))
                    end_hour, end_min = map(int, end_str.split(':'))
                    
                    start_float = float(start_hour) + (0.5 if start_min == 30 else 0.0)
                    end_float = float(end_hour) + (0.5 if end_min == 30 else 0.0)
                    
                    hour_label = f"{start_float:04.1f}-{end_float:04.1f}"
                except (ValueError, IndexError):
                    # Se falhar, usar o formato original
                    pass
            
            # Sempre mins para formato de horas (não há "ideal" neste formato)
            for day, val in enumerate(counts, start=1):
                v = str(val).strip()
                if v and v != '0':
                    try:
                        mins[(day, hour_label, team_id)] = int(v)
                    except ValueError:
                        continue
    
    print(f"[DEBUG FINAL] mins keys: {len(mins)}, ideals keys: {len(ideals)}")
    print(f"[DEBUG FINAL] Sample mins (first 5): {dict(list(mins.items())[:5])}")
    print(f"[DEBUG FINAL] Sample ideals (first 5): {dict(list(ideals.items())[:5])}")

    return mins, ideals


def rows_to_req_dicts_Half_Hour(req_rows):
    """
    Aceita ficheiros de requisitos (mínimos/ideais) tanto por turnos como por horas.
    Formatos suportados:
      - Equipa A, Minimo, M, <dia1>, <dia2>, ...
      - Equipa A, 09-10, <dia1>, <dia2>, ...
    Retorna dois dicionários:
      mins[(day, hora_ou_turno, team_id)] e ideals[(day, hora_ou_turno, team_id)]
    """
    mins, ideals = {}, {}
    print(f"[DEBUG rows_to_req_dicts_Half_Hour] Processing {len(req_rows)} rows")
    
    for row_idx, row in enumerate(req_rows):
        if not row or not row[0].strip():
            print(f"[DEBUG] Row {row_idx}: SKIPPED (empty)")
            continue
        
        print(f"\n[DEBUG] Row {row_idx}: {row[:5]}...")  # Primeiros 5 elementos
        team_label = row[0].strip()
        print(f"  team_label: '{team_label}'")
        kind = row[1].strip().lower()
        print(f"  kind: '{kind}'")

        # Detecta se é por hora (ex: '09-10') ou por turno ('M', 'T', 'N')
        thirdShifts = row[2].strip() if len(row) > 2 else ""
        thirdHours = row[1].strip()
        print(f"  thirdShifts: '{thirdShifts}'")
        print(f"  thirdHours: '{thirdHours}'")
        
        countsHours = row[2:]
        countsShifts = row[3:]
        print(f"  countsHours length: {len(countsHours)}")

        team_code = get_team_code(team_label)
        team_id = get_team_id(team_code)
        print(f"  team_code: '{team_code}', team_id: {team_id}")

        
        hour_label = thirdHours
        print(f"  hour_label: '{hour_label}'")
        target = ideals if kind.startswith('min') else mins
        print(f"  target: {'ideals' if kind.startswith('min') else 'mins'}")
        
        # Dividir a hora em 2 períodos de 30 minutos
        # Ex: '09-10' → [(9.0, 9.5), (9.5, 10.0)]
        hour_parts = hour_label.split('-')
        if len(hour_parts) != 2:
            print(f"  [WARNING] Invalid hour format: '{hour_label}', skipping row")
            continue
            
        start_hour = int(hour_parts[0])
        end_hour = int(hour_parts[1])
        print(f"  Parsed: start_hour={start_hour}, end_hour={end_hour}")
        
        entries_created = 0
        for day, val in enumerate(countsHours, start=1):
            v = str(val).strip()
            if v and v != '0':
                val_int = int(v)
                # Criar 2 entradas: uma para cada meia hora
                # Format: "09.0-09.5" to match ILP lookup format
                first_half = f"{float(start_hour):04.1f}-{float(start_hour)+0.5:04.1f}"
                second_half = f"{float(start_hour)+0.5:04.1f}-{float(end_hour):04.1f}"
                
                target[(day, first_half, team_id)] = val_int
                target[(day, second_half, team_id)] = val_int
                entries_created += 2
                
                if day <= 3:  # Debug primeiros 3 dias
                    print(f"    Day {day}: '{first_half}' = {val_int}, '{second_half}' = {val_int}")
        
        print(f"  Total entries created: {entries_created}")

    print(f"\n[DEBUG FINAL] mins keys: {len(mins)}, ideals keys: {len(ideals)}")
    print(f"[DEBUG FINAL] Sample mins (first 5): {dict(list(mins.items())[:5])}")
    print(f"[DEBUG FINAL] Sample ideals (first 5): {dict(list(ideals.items())[:5])}")

    # sleep(1500)  # para debug sequencial
    return mins, ideals


def rows_to_req_dicts_Half_Hour_2(req_rows):
    """
    Processa ficheiros CSV de requisitos mínimos com intervalos de 30 minutos.
    
    Formato esperado:
      - Linha 1: Header com datas (vazio, 'Hora', '2021-11-01', '2021-11-02', ...)
      - Linha 2: Dias da semana (vazio, vazio, 'Segunda', 'Terça', ...)
      - Linhas de dados: 'Equipa A', '09:00-09:30', val_dia1, val_dia2, ...
    
    Retorna:
      mins[(day, hora_str, team_id)] onde hora_str = "09.0-09.5"
    """
    mins = {}
    
    if len(req_rows) < 3:
        print(f"[WARNING] Ficheiro tem menos de 3 linhas - vazio ou inválido")
        return mins, {}
    
    # Parse header (primeira linha) para extrair datas
    header = req_rows[0]
    date_map = {}  # {col_index: day_number}
    
    from datetime import datetime
    for col_idx, cell in enumerate(header[2:], start=2):  # Skip primeiras 2 colunas
        try:
            # Parse data (formato: 2021-11-01)
            date_obj = datetime.strptime(cell.strip(), '%Y-%m-%d')
            # Calcular day-of-year
            day_of_year = date_obj.timetuple().tm_yday
            date_map[col_idx] = day_of_year
        except ValueError:
            continue
    
    print(f"[DEBUG] Parsed {len(date_map)} dates from header")
    print(f"[DEBUG] First 5 date mappings: {dict(list(date_map.items())[:5])}")
    
    # Processar linhas de dados (skip header e dias da semana)
    for row_idx, row in enumerate(req_rows[2:], start=2):
        if not row or len(row) < 3:
            continue
        
        team_label = row[0].strip()
        hour_range = row[1].strip()
        
        # Validar formato de equipa
        if not team_label.startswith('Equipa'):
            continue
        
        team_code = get_team_code(team_label)
        team_id = get_team_id(team_code)
        
        # Parse formato hora: "09:00-09:30" -> "09.0-09.5"
        if ':' not in hour_range or '-' not in hour_range:
            print(f"[WARNING] Row {row_idx}: Invalid hour format '{hour_range}'")
            continue
        
        try:
            # "09:00-09:30" -> ["09:00", "09:30"]
            start_str, end_str = hour_range.split('-')
            
            # "09:00" -> 9.0, "09:30" -> 9.5
            start_hour, start_min = map(int, start_str.split(':'))
            end_hour, end_min = map(int, end_str.split(':'))
            
            start_float = float(start_hour) + (0.5 if start_min == 30 else 0.0)
            end_float = float(end_hour) + (0.5 if end_min == 30 else 0.0)
            
            # Criar string no formato ILP: "09.0-09.5"
            hora_str = f"{start_float:04.1f}-{end_float:04.1f}"
            
        except (ValueError, IndexError) as e:
            print(f"[WARNING] Row {row_idx}: Failed to parse '{hour_range}': {e}")
            continue
        
        # Processar valores por dia
        entries_created = 0
        for col_idx in range(2, len(row)):
            if col_idx not in date_map:
                continue
            
            day = date_map[col_idx]
            val_str = str(row[col_idx]).strip()
            
            if val_str and val_str != '0':
                try:
                    val_int = int(val_str)
                    mins[(day, hora_str, team_id)] = val_int
                    entries_created += 1
                except ValueError:
                    continue
        
        if row_idx <= 5:  # Debug primeiras linhas
            print(f"[DEBUG] Row {row_idx}: {team_label} {hora_str} -> {entries_created} entries")
    
    print(f"\n[DEBUG FINAL] Total mins entries: {len(mins)}")
    print(f"[DEBUG FINAL] Sample (first 5): {dict(list(mins.items())[:5])}")
    
    return mins, {}


def export_schedule_to_csv_shifts(scheduler, filename="schedule.csv", num_days=365):
    header = ["funcionario"] + [f"Dia {i+1}" for i in range(num_days)]
    label_all = {1: "M_", 2: "T_", 3: "N_"}
    label = {k: v for k, v in label_all.items() if k <= getattr(scheduler, "shifts", 2)}

    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for emp in scheduler.employees:
            row = [emp]
            day_assignments = {day: (shift, team) for (day, shift, team) in scheduler.assignment[emp]}
            vacation_days = set(getattr(scheduler, "vacs", {}).get(emp, []))

            for day_num in range(1, num_days + 1):
                if day_num in vacation_days:
                    row.append("F")
                elif day_num in day_assignments:
                    shift, team_id = day_assignments[day_num]
                    team_code = TEAM_ID_TO_CODE.get(team_id, str(team_id))  # <- no A/B assumption
                    row.append(label.get(shift, "") + team_code)
                else:
                    row.append("0")
            writer.writerow(row)
    print(f"Schedule exported to {filename}")

def export_schedule_to_csv_hours(scheduler, filename="schedule_hours.csv", num_days=365, work_blocks=None):
    """
    Exporta o horário por blocos de horas, usando:
      • scheduler.assignment[emp] = [(day, block_idx, team_id), ...]
      • scheduler.vacs[emp] = [dias de férias]

    Output: CSV com 1 linha por funcionário e 365 colunas de dias.

    Dia sem trabalho -> "OFF"
    Dia de férias    -> "F"
    Trabalho         -> "start-break-end_TEAM"
    """
    import csv

    if work_blocks is None:
        work_blocks = []

    # Cabeçalho
    header = ["funcionario"] + [f"Dia {i+1}" for i in range(num_days)]

    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for emp in sorted(scheduler.employees):

            # Linha do funcionário
            row = [str(emp)]

            # Dicionário rápido: day → (block_idx, team_id)
            emp_assignments = scheduler.assignment.get(emp, [])
            day_assign = {d: (b, t) for (d, b, t) in emp_assignments}

            # Dias de férias
            vac_days = set(scheduler.vacs.get(emp, []))

            for day in range(1, num_days + 1):

                # 1) Férias
                if day in vac_days:
                    row.append("F")
                    continue

                # 2) Trabalhou?
                if day in day_assign:
                    block_idx, team_id = day_assign[day]

                    # Garantir id → code (A/B)
                    team_code = TEAM_ID_TO_CODE.get(team_id, f"UNK{team_id}")

                    # Garantir bloco válido
                    if 0 <= block_idx < len(work_blocks):
                        start, break_start, end = work_blocks[block_idx]
                        row.append(f"{start}-{break_start}-{end}_{team_code}")
                    else:
                        row.append(f"INVALID_BLOCK_{block_idx}_{team_code}")

                # 3) OFF total
                else:
                    row.append("OFF")

            writer.writerow(row)

    print(f"Schedule (hours) exported to {filename}")


def schedule_to_table(*, employees: list, vacs: dict, assignment: dict, num_days: int, shifts: int = 2):
    """Builds the schedule table as a list of rows."""
    header = ["funcionario"] + [f"Dia {d}" for d in range(1, num_days + 1)]
    rows = [header]
    label_all = {1: "M_", 2: "T_", 3: "N_"}
    label = {k: v for k, v in label_all.items() if k <= shifts}

    all_emp_ids = sorted(set(employees) | set(vacs.keys()) | set(assignment.keys()))
    for emp_id in all_emp_ids:
        vac_days = set(vacs.get(emp_id, []))
        day_to = {d: (s, t) for (d, s, t) in assignment.get(emp_id, [])}
        line = [str(emp_id)]
        for d in range(1, num_days + 1):
            if d in vac_days:
                line.append("F")
            elif d in day_to:
                s, t = day_to[d]
                line.append(label.get(s, "") + TEAM_ID_TO_CODE.get(t, str(t)))
            else:
                line.append("0")
        rows.append(line)
    return rows

def to_table(*, employees: list, vacs: dict, assignment: dict, num_days: int, work_blocks: list):
        """Return schedule as table for display."""
        header = ["Employee"] + [f"Day{i}" for i in range(1, num_days + 1)]
        rows = [header]
        
        for emp_id in sorted([i + 1 for i in employees]):
            vac_days = set(vacs.get(emp_id, []))
            day_to_block = {d: (b, t) for (d, b, t) in assignment.get(emp_id, [])}
            
            line = [f"Emp{emp_id}"]
            for d in range(1, num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_block:
                    block_idx, team_id = day_to_block[d]
                    block = work_blocks[block_idx]
                    team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                    line.append(f"{block[0]}-{block[1]}-{block[2]}_{team_code}")
                else:
                    line.append("OFF")
            
            rows.append(line)
        
        return rows

def to_table_hours(*, employees, vacs, assignment, num_days, work_blocks):
    """
    Constrói uma tabela (lista de listas) com o horário por horas.
    employees: lista de IDs reais dos empregados (ex: [1,2,3,...])
    vacs: dict emp_id -> [dias]
    assignment: dict emp_id -> [(day, block_idx, team_id)]
    work_blocks: lista de blocos (start, break, end)
    """
    # Cabeçalho
    header = ["Employee"] + [f"Day{d}" for d in range(1, num_days + 1)]
    rows = [header]
    
    # Garantir ordenação correcta dos IDs reais
    for emp_id in sorted(employees):
        emp_vacs = set(vacs.get(emp_id, []))
        emp_assign = assignment.get(emp_id, [])
        
        # Criar mapeamento day -> (block_idx, team_id)
        day_map = {}
        for (d, b, t) in emp_assign:
            if d in day_map:
                print(f"[WARNING] Employee {emp_id}: Day {d} assigned multiple times!")
            day_map[d] = (b, t)
        
        line = [f"Emp{emp_id}"]
        
        for day in range(1, num_days + 1):
            # Férias (prioridade)
            if day in emp_vacs:
                line.append("F")
                continue
            
            # Trabalhou
            if day in day_map:
                block_idx, team_id = day_map[day]
                
                # Garantir bloco válido
                if 0 <= block_idx < len(work_blocks):
                    start, brk, end = work_blocks[block_idx]
                    # Converter equipa
                    team_code = TEAM_ID_TO_CODE.get(team_id, f"UNK{team_id}")
                    line.append(f"{start}-{brk}-{end}_{team_code}")
                else:
                    print(f"[ERROR] Employee {emp_id}, Day {day}: Invalid block_idx {block_idx}")
                    line.append(f"ERROR_BLOCK_{block_idx}")
            else:
                # OFF total
                line.append("OFF")
        
        rows.append(line)
    
    return rows


def create_Blocks(interval_in_hours, inicial_Hour, final_Hour):
    """
    Cria blocos de trabalho com base no intervalo e horas iniciais/finais.
    Retorna uma lista de tuplos (start, break, end).
    """
    blocks = []
    start_hour = float(inicial_Hour)
    final_Hour = float(final_Hour)
    interval_in_hours = float(interval_in_hours)
    
    while start_hour + 9 <= final_Hour:
        end_hour = start_hour + 9
        for i in range(0, 3):
            break_hour = start_hour + 5 + i
            blocks.append((start_hour, break_hour, end_hour))
            print(f"Created block: {start_hour}-{break_hour}-{end_hour}")
        start_hour += interval_in_hours

    # sleep(1000)  # para debug sequencial
    return blocks


def drange(x, y, jump):
    while x < y:
        yield float(x)
        x += (jump)


def drange_indexed(start, stop, step):
    # print(f"drange_indexed: start={start}, stop={stop}, step={step}")
    x = int(start)
    y = x * 2 + 10
    counter = 0
    counter2 = 0
    index2 = y
    while x < stop:
        # Geramos um índice inteiro (ex: 9.0 -> 18, 9.5 -> 19)
        # Multiplicamos por 2 e convertemos para int
        if counter % 2 == 0:
            index = start + counter2
            counter2 += 1
            yield counter, x, index
        else:
            index2 =  index2 + 1
            yield counter, x, index2

        counter += 1
        
        # print(f"drange_indexed: counter={counter}, x={x}, index={index}")
        x += step

def drange_indexed_h(start, stop, step):
    x = float(start)  # Force float to avoid int/float mixing
    list_indices = set()

    while x < stop:
        # Round to 1 decimal to avoid floating point precision issues
        list_indices.add(round(x, 1))
        x += step

    return list_indices


def automatic_weight_search(
    vacations,
    minimuns,
    employees,
    maxTime,
    year,
    hours,
    work_blocks=None,
    max_seconds=25200,
    early_stop_score=0,
    seed=None
):
    
    def count_minimum_failures(scheduler):
        """
        Conta o número total de falhas aos mínimos necessários na solução atribuída.
        Para cada (dia, hora, equipa), verifica se o número de funcionários atribuídos < mínimo.
        """
        # Reconstruir cobertura por (dia, hora, equipa)
        coverage = {}
        for emp_id, assignments in scheduler.assignment.items():
            for (day_idx, block_idx, team_id) in assignments:
                date = scheduler.dates[day_idx - 1]
                block = scheduler.work_blocks[block_idx]
                team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                hours = scheduler._get_working_hours(block)
                for h in hours:
                    key = (date, f"{h:02d}-{h+1:02d}", team_code)
                    coverage[key] = coverage.get(key, 0) + 1
        failures = 0
        for key, minimo in scheduler.minimos.items():
            if minimo > 0:
                covered = coverage.get(key, 0)
                if covered < minimo:
                    failures += 1
        return failures
    
    """
    Pesquisa automática de pesos contínuos em [0,1] para a heurística.
    Corre o máximo de combinações possíveis dentro do tempo dado.
    """

    if seed is not None:
        random.seed(seed)

    best_score = None
    best_weights = None
    best_assignment = None
    best_scheduler = None

    start_time = time.time()
    n_iter = 0

    print("\n" + "=" * 80)
    print("[AutoSearch] INÍCIO DA PESQUISA AUTOMÁTICA DE PESOS")
    print("=" * 80)

    while time.time() - start_time < max_seconds:

        n_iter += 1
        used_weights = set()

        # -----------------------------
        # 1. Gerar pesos aleatórios contínuos
        # -----------------------------
        while True:
            w = [random.random(), random.random(), random.random()]
            s = sum(w)
            weights_tuple = tuple(round(x / s, 3) for x in w)  # arredondar para evitar flutuação de ponto flutuante
            if weights_tuple not in used_weights:
                used_weights.add(weights_tuple)
                W_TOTAL, W_WEEK, W_TEAMS = weights_tuple
                break

        print(f"\n[AutoSearch] Iteração {n_iter}")
        print(f"  Pesos → TOTAL={W_TOTAL:.4f}, WEEK={W_WEEK:.4f}, TEAMS={W_TEAMS:.4f}")

        # -----------------------------
        # 2. Executar heurística
        # -----------------------------
        scheduler = Heuristica(
            vacations,
            minimuns,
            employees,
            maxTime,
            year=year,
            store_hours=hours,
            work_blocks=work_blocks,
            W_TOTAL=W_TOTAL,
            W_WEEK=W_WEEK,
            W_TEAMS=W_TEAMS
        )

        scheduler.solve()

        # -----------------------------
        # 3. Avaliar solução
        # -----------------------------
        score = count_minimum_failures(scheduler)
        print(f"  Falhas nos mínimos: {score}")

        # -----------------------------
        # 4. Atualizar melhor solução
        # -----------------------------
        if best_score is None or score < best_score:
            best_score = score
            best_weights = (W_TOTAL, W_WEEK, W_TEAMS)
            best_assignment = copy.deepcopy(scheduler.assignment)
            best_scheduler = scheduler

            print("\033[92m"
                  f"  ★ NOVA MELHOR SOLUÇÃO (falhas={score})"
                  "\033[0m")

        # -----------------------------
        # 5. Early stop se perfeito
        # -----------------------------
        if best_score <= early_stop_score:
            print("[AutoSearch] Solução perfeita encontrada. A terminar.")
            break

    print("\n" + "=" * 80)
    print("[AutoSearch] RESULTADO FINAL")
    print(f"  Iterações: {n_iter}")
    print(f"  Melhor score: {best_score}")
    print(f"  Melhores pesos:")
    print(f"    W_TOTAL = {best_weights[0]:.4f}")
    print(f"    W_WEEK  = {best_weights[1]:.4f}")
    print(f"    W_TEAMS = {best_weights[2]:.4f}")
    print("=" * 80)

    if best_scheduler and best_assignment:
        best_scheduler.assignment = best_assignment
        best_scheduler.export_csv("heuristic_best_auto_weights.csv")
        return best_scheduler

    return None

def count_minimum_failures(scheduler):
        """
        Conta o número total de falhas aos mínimos necessários na solução atribuída.
        Para cada (dia, hora, equipa), verifica se o número de funcionários atribuídos < mínimo.
        """
        # Reconstruir cobertura por (dia, hora, equipa)
        coverage = {}
        for emp_id, assignments in scheduler.assignment.items():
            for (day_idx, block_idx, team_id) in assignments:
                date = scheduler.dates[day_idx - 1]
                block = scheduler.work_blocks[block_idx]
                team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                hours = scheduler._get_working_hours(block)
                for h in hours:
                    # Suporta tanto inteiros (hora cheia) quanto floats (meia hora)
                    if isinstance(h, float) and h % 1 == 0:
                        # Hora cheia: 9.0 -> '09-10'
                        key1 = (date, f"{int(h):02d}-{int(h+1):02d}", team_code)
                        coverage[key1] = coverage.get(key1, 0) + 1
                    elif isinstance(h, float):
                        # Meia hora: 9.5 -> '09.5-10.0'
                        start = h
                        end = h + 0.5
                        key2 = (date, f"{start:04.1f}-{end:04.1f}", team_code)
                        coverage[key2] = coverage.get(key2, 0) + 1
        failures = 0
        for key, minimo in scheduler.minimos.items():
            if minimo > 0:
                covered = coverage.get(key, 0)
                if covered < minimo:
                    failures += 1
        return failures

def check_5_consecutive_days(table):
    violations = []
    for row in table[1:]:  # Ignora header
        emp = row[0]
        work_streak = 0
        start_idx = None
        for i, cell in enumerate(row[1:], 1):
            if cell not in ("OFF", "F", "VACATION"):
                if work_streak == 0:
                    start_idx = i
                work_streak += 1
                if work_streak > 5:
                    violations.append((emp, start_idx, i))
            else:
                work_streak = 0
                start_idx = None
    return violations


def rows_to_req_dicts_FIXED(req_rows):
    """
    FIXED: Store minimums with FLOAT keys (not strings)
    Key format: (pd.Timestamp, float, int)
    Example: (Timestamp('2021-11-02'), 9.0, 1)
    """
    mins = {}
    dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()

    print(f"[DEBUG] Created {len(dates)} dates for conversion")

    for row in req_rows:
        if not row or len(row) < 3:
            continue
        
        team_label = row[0].strip()
        if not team_label.upper().startswith('EQUIPA'):
            continue
        
        second_col = row[1].strip()
        team_code = get_team_code(team_label)
        team_id = get_team_id(team_code)

        if '-' not in second_col:
            continue
            
        hour_label = second_col
        counts = row[2:]

        # Parse hour to FLOAT
        if ':' in hour_label:
            try:
                start_str, _ = hour_label.split('-')
                start_hour, start_min = map(int, start_str.split(':'))
                start_float = round(float(start_hour) + (0.5 if start_min == 30 else 0.0), 1)
            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        else:
            try:
                parts = hour_label.split('-')
                start_float = round(float(parts[0]), 1)
            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        
        # Store with (Timestamp, FLOAT, team_id) format
        for day_num, val in enumerate(counts, start=1):
            v = str(val).strip()
            if not v:
                continue
            
            try:
                val_int = int(v)
            except ValueError:
                continue
            
            if 1 <= day_num <= len(dates):
                date_key = dates[day_num - 1]
                # KEY FIX: Store as (date, FLOAT, team_id)
                mins[(date_key, start_float, team_id)] = val_int
                
    print(f"[DEBUG] Processed {len(mins)} minimum entries")
    print(f"[DEBUG] Sample keys (first 10):")
    for i, (key, val) in enumerate(list(mins.items())[:10]):
        print(f"  {key} → {val}")

    return mins, {}
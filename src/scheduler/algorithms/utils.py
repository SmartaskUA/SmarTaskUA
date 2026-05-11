import csv
import decimal
import os
import re
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

def safe_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def build_allowed_teams(employees):
    """
    Convert employee 'teams' labels to internal numeric team IDs.
    Fallback to team 'A' when none provided.
    """
    allowed = []
    for employee in employees:
        codes = [get_team_code(t) for t in employee.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed


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
    if not vac_rows:
        return vacs
    for row in vac_rows:
        if not row:
            continue
        try:
            emp_id = int(str(row[0]).split()[-1])
        except (ValueError, TypeError, IndexError):
            continue
        vacs[emp_id] = [
            idx + 1
            for idx, bit in enumerate(row[1:])
            if str(bit).strip() == '1'
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


def rows_to_req_dicts_any(req_rows, year=None):
    """
    Accept either the legacy minimuns format or demand.csv rows.
    Demand rows format: date, shift, team, minimum, ideal, estimated
    """
    if not req_rows:
        return {}, {}
    if _looks_like_demand_rows(req_rows):
        return rows_to_req_dicts_from_demand(req_rows, year=year)
    return rows_to_req_dicts(req_rows)


def infer_shift_count_from_dicts(mins_raw, ideals_raw):
    shift_values = [
        key[1]
        for key in list(mins_raw.keys()) + list(ideals_raw.keys())
        if isinstance(key[1], int)
    ]
    return max(shift_values) if shift_values else None


def infer_shift_count_from_rows(req_rows, year=None):
    if not req_rows:
        return None
    mins_raw, ideals_raw = rows_to_req_dicts_any(req_rows, year=year)
    return infer_shift_count_from_dicts(mins_raw, ideals_raw)


def rows_to_req_dicts_from_demand(demand_rows, year=None):
    mins, ideals = {}, {}
    if not demand_rows:
        return mins, ideals

    for row in demand_rows:
        if not row or len(row) < 5:
            continue
        if _is_demand_header(row):
            continue
        demand_date = _parse_iso_date(row[0])
        if demand_date is None:
            continue
        day = demand_date.timetuple().tm_yday

        shift_code = str(row[1]).strip().upper()
        shift = _shift_code_to_index(shift_code)
        if shift is None:
            continue

        team_code = get_team_code(str(row[2]))
        if not team_code:
            continue
        team_id = get_team_id(team_code)

        min_val = _parse_int(row[3])
        ideal_val = _parse_int(row[4])
        if min_val is None and ideal_val is None:
            continue
        if min_val is None:
            min_val = 0
        if ideal_val is None:
            ideal_val = min_val

        mins[(day, shift, team_id)] = min_val
        ideals[(day, shift, team_id)] = ideal_val

    return mins, ideals


def _looks_like_demand_rows(rows):
    if not rows:
        return False
    for row in rows[:3]:
        if not row or len(row) < 5:
            continue
        if _is_demand_header(row):
            return True
        if _parse_iso_date(row[0]) is not None and str(row[1]).strip():
            return True
    return False


def _is_demand_header(row):
    if not row:
        return False
    first = str(row[0]).strip().lower()
    second = str(row[1]).strip().lower() if len(row) > 1 else ""
    return first in {"date", "data"} and second in {"shift", "turno"}


def _parse_iso_date(value):
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_int(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _shift_code_to_index(code):
    if not code:
        return None
    text = str(code).strip().upper()
    if not text:
        return None
    if text.startswith("M"):
        return 1
    if text.startswith("T") or text.startswith("A"):
        return 2
    if text.startswith("N"):
        return 3
    match = re.search(r"\d+", text)
    if match:
        try:
            return int(match.group())
        except ValueError:
            return None
    return None

def rows_to_req_dicts(req_rows):
    """
    Aceita ficheiros de requisitos (mínimos/ideais) tanto por turnos como por horas.
    Formatos suportados:
      - Equipa A, Minimo, M, <dia1>, <dia2>, ...
      - Equipa A, 09-10, <dia1>, <dia2>, ...
    Retorna dois dicionários:
      mins[(day, hora_ou_turno, team_id)] e ideals[(day, hora_ou_turno, team_id)]
    """
    mins, ideals = {}, {}
    for row in req_rows:
        if not row or not row[0].strip():
            continue
        
        #print(f"Processing row: {row}, from")
        team_label = row[0].strip()
        #print(f"team_label: {team_label}")
        kind = row[1].strip().lower()
        #print(f"kind: {kind}")

        # Detecta se é por hora (ex: '09-10') ou por turno ('M', 'T', 'N')
        thirdShifts = row[2].strip()
        thirdHours = row[1].strip()
        #print(f"third_Shifts: {thirdShifts}")
        #print(f"third_Hours: {thirdHours}")
        countsHours = row[2:]
        countsShifts = row[3:]
        #print(f"counts: {counts}")

        team_code = get_team_code(team_label)
        team_id = get_team_id(team_code)
        #print(f"team_code: {team_code}, team_id: {team_id}")
        #time.sleep(15)  # para debug sequencial

        is_shift_mode = kind.startswith("min") or kind.startswith("ideal")

        # → modo por turno
        if is_shift_mode:
            shift = _shift_code_to_index(thirdShifts)
            if shift is None:
                continue
            target = mins if kind.startswith('min') else ideals
            for day, val in enumerate(countsShifts, start=1):
                v = str(val).strip()
                if v:
                    try:
                        target[(day, shift, team_id)] = int(v)
                    except (TypeError, ValueError):
                        continue

        # → modo por meias horas
        elif "-" in thirdHours:
            hour_label = thirdHours
            # print(f"hour_label: {hour_label}")
            target = ideals if kind.startswith('min') else mins
            for day, val in enumerate(countsHours, start=1):
                v = str(val).strip()
                if v:
                    try:
                        target[(day, hour_label, team_id)] = int(v)
                    except (TypeError, ValueError):
                        continue


    # print(f"Current mins: {mins}")
    # print(f"Current ideals: {ideals}")
    # time.sleep(15)  # para debug sequencial

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


def export_schedule_to_csv(scheduler, filename="schedule.csv", num_days=None):
    """Compatibility wrapper for shift-based exports."""
    resolved_days = num_days or getattr(scheduler, "num_days", 365)
    work_blocks = getattr(scheduler, "work_blocks", None) or getattr(scheduler, "blocks", None)
    if work_blocks:
        export_schedule_to_csv_hours(
            scheduler,
            filename=filename,
            num_days=resolved_days,
            work_blocks=work_blocks,
        )
    else:
        export_schedule_to_csv_shifts(
            scheduler,
            filename=filename,
            num_days=resolved_days,
        )


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
                prefix = label.get(s, f"S{s}_")
                line.append(prefix + TEAM_ID_TO_CODE.get(t, str(t)))
            else:
                line.append("0")
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




def count_minimum_failures(scheduler):
        """
        Conta o número total de falhas aos mínimos necessários na solução atribuída.
        Para cada (dia, hora, equipa), verifica se o número de funcionários atribuídos < mínimo.
        
        Suporta dois formatos de chaves:
        - COP: (Timestamp, float, team_code) ex: (Timestamp, 9.0, 'A')
        - Heurística: (Timestamp, str, team_code) ex: (Timestamp, '09-10', 'A')
        """
        # Obter o dicionário de mínimos correto (theta em COP_1, minimos em COP_2/Heuristica)
        minimos_dict = getattr(scheduler, 'minimos', None) or getattr(scheduler, 'theta', {})
        
        if not minimos_dict:
            return 0
        
        # Detectar formato das chaves: float ou string?
        sample_key = next(iter(minimos_dict.keys()), None)
        if sample_key is None:
            return 0
        
        use_string_hours = isinstance(sample_key[1], str)
        
        # Reconstruir cobertura por (dia, hora, equipa)
        coverage = {}
        for emp_id, assignments in scheduler.assignment.items():
            for (day_idx, block_idx, team_id) in assignments:
                date = scheduler.dates[day_idx - 1]
                block = scheduler.work_blocks[block_idx]
                team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                hours = scheduler._get_working_hours(block)
                for h in hours:
                    if use_string_hours:
                        # Formato Heurística: '09-10' (hora inteira)
                        h_int = int(h)
                        hour_key = f"{h_int:02d}-{h_int+1:02d}"
                    else:
                        # Formato COP: float (9.0, 9.5, etc.)
                        hour_key = round(float(h), 1)
                    
                    key = (date, hour_key, team_code)
                    coverage[key] = coverage.get(key, 0) + 1
        
        failures = 0
        for key, minimo in minimos_dict.items():
            if minimo > 0:
                covered = coverage.get(key, 0)
                if covered < minimo:
                    failures += 1
        return failures

def count_minimum_shift_failures(scheduler):
        """
        Conta o número total de falhas aos mínimos necessários em problemas por turnos.

        Suporta mínimos em qualquer uma destas formas:
        - (dia, turno, equipa)
        - (dia, equipa, turno)
        - dia como `int` ou `Timestamp`
        - equipa como código (`'A'`, `'B'`) ou ID inteiro

        Se o scheduler for horário, delega para `count_minimum_failures()`.
        """
        minimos_dict = getattr(scheduler, 'minimos', None) or getattr(scheduler, 'theta', {})
        
        if not minimos_dict:
            return 0
        
        sample_key = next(iter(minimos_dict.keys()), None)
        if sample_key is None:
            return 0

        sample_value = sample_key[1] if len(sample_key) > 1 else None
        if isinstance(sample_value, float) or (
            isinstance(sample_value, str) and ('-' in sample_value or ':' in sample_value)
        ):
            return count_minimum_failures(scheduler)

        dates = getattr(scheduler, 'dates', [])
        num_days = len(dates)

        # Reconstruir cobertura por (dia, turno, equipa)
        coverage = {}
        for assignments in scheduler.assignment.values():
            for assignment in assignments:
                if len(assignment) < 3:
                    continue

                day_idx, shift, team_id = assignment[:3]

                day_values = {day_idx}
                if isinstance(day_idx, int):
                    if 1 <= day_idx <= num_days:
                        day_values.add(dates[day_idx - 1])
                    elif 0 <= day_idx < num_days:
                        day_values.add(dates[day_idx])

                team_code = TEAM_ID_TO_CODE.get(team_id, str(team_id))
                team_values = {team_id, team_code}

                for day_value in day_values:
                    for team_value in team_values:
                        coverage[(day_value, shift, team_value)] = coverage.get((day_value, shift, team_value), 0) + 1
                        coverage[(day_value, team_value, shift)] = coverage.get((day_value, team_value, shift), 0) + 1
        
        failures = 0
        for key, minimo in minimos_dict.items():
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

    return mins, {}
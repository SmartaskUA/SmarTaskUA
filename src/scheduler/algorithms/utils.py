import csv
import decimal
import os
from datetime import date, time
import pandas as pd
from collections import defaultdict

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


def rows_to_req_dicts_any(req_rows, year=None):
    """
    Accept either the legacy minimuns format or demand.csv rows.
    Demand rows format: date, shift, team, minimum, ideal, estimated
    """
    if _looks_like_demand_rows(req_rows):
        return rows_to_req_dicts_from_demand(req_rows, year=year)
    return rows_to_req_dicts(req_rows)


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
    if code.startswith("M"):
        return 1
    if code.startswith("T"):
        return 2
    if code.startswith("N"):
        return 3
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

        # → modo por turno
        if thirdShifts.upper().startswith(("M", "T", "N")):
            code = thirdShifts.upper()
            if code.startswith('M'):
                shift = 1
            elif code.startswith('T') or code.startswith('A'):
                shift = 2
            elif code.startswith('N'):
                shift = 3
            else:
                continue
            target = mins if kind.startswith('min') else ideals
            for day, val in enumerate(countsShifts, start=1):
                v = str(val).strip()
                if v:
                    target[(day, shift, team_id)] = int(v)

        # → modo por meias horas
        elif "-" in thirdHours:
            hour_label = thirdHours
            # print(f"hour_label: {hour_label}")
            target = ideals if kind.startswith('min') else mins
            for day, val in enumerate(countsHours, start=1):
                v = str(val).strip()
                if v:
                    target[(day, hour_label, team_id)] = int(val)


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

        
        hour_label = thirdHours
        # print(f"hour_label: {hour_label}")
        target = ideals if kind.startswith('min') else mins
        # Dividir a hora em 2 períodos de 30 minutos
        # Ex: '09-10' → [(9.0, 9.5), (9.5, 10.0)]
        hour_parts = hour_label.split('-')
        start_hour = int(hour_parts[0])
        end_hour = int(hour_parts[1])
        for day, val in enumerate(countsHours, start=1):
            v = str(val).strip()
            if v:
                val_int = int(v)
                # Criar 2 entradas: uma para cada meia hora
                # Ex: (1, '9.0-9.5', 1) e (1, '9.5-10.0', 1)
                first_half = f"{start_hour}.0-{start_hour}.5"
                second_half = f"{start_hour}.5-{end_hour}.0"
                
                target[(day, first_half, team_id)] = val_int
                target[(day, second_half, team_id)] = val_int


    # print(f"Current mins: {mins}")
    # print(f"Current ideals: {ideals}")
    # time.sleep(15)  # para debug sequencial

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
    start_hour = inicial_Hour
    while start_hour + 9 <= final_Hour:
        end_hour = start_hour + 9
        for i in range(0,3):
            break_hour = start_hour + 5 + i
            blocks.append((start_hour, break_hour, end_hour))
        start_hour += interval_in_hours
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
    # print(f"drange_indexed: start={start}, stop={stop}, step={step}")
    x = start

    while x < stop:
        # Geramos um índice inteiro (ex: 9.0 -> 18, 9.5 -> 19)
        # Multiplicamos por 2 e convertemos para int
        yield x
        
        # print(f"drange_indexed: counter={counter}, x={x}, index={index}")
        x += step


def compute_lower_bound_and_report(scheduler, csv_filename="csp_lb_report.csv", verbose=True):
    """
    Calcula um lower bound (LB) válido para as shortages e gera relatório.
    LB por slot (dia,hora,team) = max(0, minimo - capacidade_maxima_disponivel).
    capacidade_maxima_disponivel = número de empregados que:
        - pertencem àquela equipa (podem trabalhar nessa equipa),
        - não estão de férias nesse dia,
        - o dia não é fechado para essa equipa (mínimo != -1).
    Retorna dicionário com LB_total, objective (valor da solução), quality_pct, e paths do csv.
    """
    # 1) recolhe inputs do scheduler
    dates = scheduler.dates
    hours = scheduler.hours
    teams = list(scheduler.teams.keys())  # códigos ('A','B',...)
    emp_team_code = scheduler.emp_team_code  # {f_idx: (teams...)}
    vacations = scheduler.vacations_dates     # {f_idx: set(dates)}
    minimos = scheduler.minimos               # {(date, "HH-HH", team_code): val}
    objective = None
    # tenta ler objective do solver/relatório
    try:
        # se tens o valor guardado em scheduler.solver e model -> cp-sat
        objective = float(scheduler.solver.ObjectiveValue()) if scheduler.solver is not None else None
    except Exception:
        # fallback: procura scheduler.attribute
        objective = getattr(scheduler, "objective_value", None) or getattr(scheduler, "last_objective", None) or None

    # Se não conseguimos objective programaticamente, podes passar como argumento:
    if objective is None:
        # tenta usar scheduler.calculated_shortages (se soma represente objective)
        if hasattr(scheduler, "calculated_shortages"):
            # assumimos que objective = soma(shortage * weight). Não ideal; prefer passar objective explícito.
            pass

    # 2) calcula disponibilidade máxima por (date,h,team)
    lb_per_slot = {}
    total_minimos = 0
    total_lb = 0

    # Precompute: lista de empregados por equipa (indice interno)
    team_members = {tc: set() for tc in teams}
    for f, tcs in emp_team_code.items():
        for tc in tcs:
            if tc in team_members:
                team_members[tc].add(f)

    for d_idx, d in enumerate(dates):
        for h in hours:
            hour_label = f"{h:02d}-{h+1:02d}"
            for tc in teams:
                key = (d, hour_label, tc)
                minimo = minimos.get(key, None)
                if minimo is None:
                    # se não existe requisito, assumimos 0 (nenhuma necessidade)
                    minimo = 0
                if minimo == -1:
                    # dia fechado -> não contam para requisitos
                    lb_per_slot[(d_idx+1, hour_label, tc)] = {'minimo': -1, 'capacity': 0, 'lb': 0}
                    continue

                # conta empregados potencialmente disponíveis naquele dia para aquela equipa
                members = team_members.get(tc, set())
                avail = 0
                for f in members:
                    # funcionário f disponível? (não em férias nesse dia)
                    if d not in vacations.get(f, set()):
                        # NOTA: estamos a ignorar limites globais (223 dias por empregado)
                        # porque isso tornaria o LB ainda mais complexo. Este LB é válido.
                        avail += 1

                capacity = avail
                lb_here = max(0, int(minimo) - capacity)
                lb_per_slot[(d_idx+1, hour_label, tc)] = {
                    'minimo': int(minimo),
                    'capacity': capacity,
                    'lb': lb_here
                }
                total_minimos += max(0, int(minimo))
                total_lb += lb_here

    # 3) calcula quality (usar objective passado se disponível)
    # Se objective não está disponível, tenta ler scheduler.calculated_shortages somando
    if objective is None:
        # tenta somar shortages reais (se guardaste as variáveis)
        real_shortages = 0
        for k, v in getattr(scheduler, "calculated_shortages", {}).items():
            if v is not None:
                real_shortages += int(v)
        objective = real_shortages

    # Evita divisão por zero
    if objective == 0:
        quality = 0.0
    else:
        # fórmula: quality = 1 - (objective - LB)/objective = LB/objective
        quality = float(total_lb) / float(objective) if objective > 0 else 0.0

    quality_pct = quality * 100.0

    # 4) escreve CSV com detalhes por slot
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["DayIndex", "Date", "Hour", "Team", "Minimo", "Capacity", "LB_slot"])
        for (d_idx, hour_label, tc), info in sorted(lb_per_slot.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
            date_str = dates[d_idx-1].strftime("%Y-%m-%d")
            writer.writerow([d_idx, date_str, hour_label, tc, info['minimo'], info['capacity'], info['lb']])

    # 5) resumo por equipa e por dia / top piores
    lb_by_team = defaultdict(int)
    min_by_team = defaultdict(int)
    for (d_idx, hour_label, tc), info in lb_per_slot.items():
        if info['minimo'] >= 0:
            lb_by_team[tc] += info['lb']
            min_by_team[tc] += info['minimo']

    team_stats = []
    for tc in teams:
        team_stats.append((tc, min_by_team.get(tc,0), lb_by_team.get(tc,0),
                           (1 - ( (min_by_team.get(tc,0)-lb_by_team.get(tc,0)) / max(1, min_by_team.get(tc,0)) )) if min_by_team.get(tc,0)>0 else 1.0))

    # 6) imprime resumo
    if verbose:
        print("===== LB REPORT =====")
        print(f"Objective (solution) = {objective}")
        print(f"Lower bound (sum of slot LBs) = {total_lb}")
        print(f"Total mínimos (sum of requisitos positivos) = {total_minimos}")
        print(f"Quality (LB/objective) = {quality_pct:.2f}%")
        print(f"CSV detalhado escrito em: {csv_filename}")
        print("")
        print("Per-team summary (team, total_min, total_LB, approx_coverage):")
        for tc, totmin, totlb, approx_cov in sorted(team_stats, key=lambda x: x[2], reverse=True):
            cov_pct = 100.0 * (1.0 - ( (totmin - totlb) / max(1, totmin) )) if totmin>0 else 100.0
            print(f"  Team {tc}: min={totmin}  LB={totlb}  approx_coverage={cov_pct:.2f}%")
        # top worst slots (largest LB)
        worst_slots = sorted([(k,v['lb']) for k,v in lb_per_slot.items()], key=lambda x: -x[1])[:10]
        print("")
        print("Top 10 slots com maior LB (dayindex, hour, team, LB):")
        for (d_idx, hour_label, tc), lb_val in worst_slots:
            print(f"  Day {d_idx} {hour_label} Team {tc} -> LB = {lb_val}")

    result = {
        'objective': objective,
        'total_lb': total_lb,
        'total_minimos': total_minimos,
        'quality_pct': quality_pct,
        'csv': csv_filename,
        'per_slot': lb_per_slot,
        'team_stats': team_stats
    }
    return result

import traceback
import pandas as pd
import re
import json
from datetime import date, datetime
import holidays

# ==============================================================================
# CONFIGURATION - EDIT THESE FLAGS TO CONTROL TESTS
# ==============================================================================

class TestConfig:
    """Local testing configuration - edit these flags to control what runs"""
    
    # Test flags - set to True/False to enable/disable each test
    TEST_30MIN = True
    TEST_1HOUR = True
    
    # File paths
    CSV_30MIN = "Horário_Por_Intervalos_30min.csv"
    CSV_1HOUR = "Horário_Por_Intervalos_1Hora_7hours_to_run.csv"
    
    MINS_CSV = "Mins_R10-R62.csv"  # Same CSV for both granularities
    VACATION_CSV = "VacationTemplate_Case1_21.csv"

# ==============================================================================
# MINIMUMS LOADING - UNIFIED FOR BOTH GRANULARITIES
# ==============================================================================

def expand_hour_to_30min(hour_range):
    """
    Expands 1-hour range to two 30-minute slots.
    FIXED: Now uses HH:MM-HH:MM format to match ScheduleParser output.
    
    Args:
        hour_range: String like "09-10"
        
    Returns:
        List of two 30-min slots: ["09:00-09:30", "09:30-10:00"]
    """
    parts = hour_range.split('-')
    start_h = int(parts[0])
    end_h = int(parts[1])
    
    return [
        f"{start_h:02d}:00-{start_h:02d}:30",  # 09:00-09:30
        f"{start_h:02d}:30-{end_h:02d}:00"     # 09:30-10:00
    ]

def load_minimums_from_csv(mins_csv_file, granularity=30):
    """
    Loads minimums from CSV file (always in 1-hour format).
    Expands to 30-minute slots if granularity=30.
    
    CSV structure:
    Hora | 2021-11-01 | 2021-11-02 | ... | 2022-10-31
    Equipa A | 09-10 | -1 | 4 | 3 | ... 
    Equipa A | 10-11 | -1 | 4 | 4 | ...
    
    Args:
        mins_csv_file: Path to CSV file
        granularity: 30 or 60 (minutes)
        
    Returns:
        Text string in format expected by parse_requirements_hourly()
    """
    print(f"\n[LOAD MINIMUMS] Reading from: {mins_csv_file}")
    print(f"[LOAD MINIMUMS] Target granularity: {granularity} minutes")
    
    df = pd.read_csv(mins_csv_file, encoding='utf-8')
    
    lines = []
    
    for _, row in df.iterrows():
        row_values = row.values.tolist()
        
        # Find team name (contains "Equipa" or "Team")
        team = None
        hour_range = None
        values_start_idx = None
        
        for idx, val in enumerate(row_values[:5]):  # Check first 5 columns
            val_str = str(val).strip()
            if 'Equipa' in val_str or 'Team' in val_str:
                # Extract team letter (A, B, C, etc.)
                match = re.search(r'([A-Z])$', val_str)
                if match:
                    team = match.group(1)
            elif re.match(r'^\d{2}-\d{2}$', val_str):
                hour_range = val_str
                values_start_idx = idx + 1
                break
        
        if team and hour_range and values_start_idx:
            # Get all values after the hour range
            values = row_values[values_start_idx:]
            # Convert to string, handling NaN
            values_str = ','.join([str(int(v)) if pd.notna(v) and str(v).replace('-','').isdigit() else '-1' for v in values])
            
            # Expand to 30-min if needed
            if granularity == 30:
                time_slots = expand_hour_to_30min(hour_range)
                for slot in time_slots:
                    line = f"Team {team},min,{slot},{values_str}"
                    lines.append(line)
            else:  # granularity == 60
                line = f"Team {team},min,{hour_range},{values_str}"
                lines.append(line)
    
    result = '\n'.join(lines)
    print(f"[LOAD MINIMUMS] Loaded {len(lines)} team-hour combinations")
    return result

# ==============================================================================
# SCHEDULE PARSING - UNIFIED FOR BOTH GRANULARITIES
# ==============================================================================

class ScheduleParser:
    """Unified parser for schedule CSV files"""
    
    @staticmethod
    def time_to_minutes(time_str):
        """Convert '9' or '9.5' to minutes from midnight"""
        time_float = float(time_str)
        hours = int(time_float)
        minutes = int((time_float - hours) * 60)
        return hours * 60 + minutes
    
    @staticmethod
    def format_30min_slot(minutes):
        """Format minutes as '09:00-09:30' or '09:30-10:00'"""
        hour = minutes // 60
        minute = minutes % 60
        next_min = minutes + 30
        next_hour = next_min // 60
        next_minute = next_min % 60
        return f"{hour:02d}:{minute:02d}-{next_hour:02d}:{next_minute:02d}"
    
    @staticmethod
    def generate_30min_slots(start_min, break_min, end_min):
        """Generate 30-minute slots"""
        slots = []
        
        # Morning period: start to break
        current = start_min
        while current < break_min:
            slot = ScheduleParser.format_30min_slot(current)
            slots.append(slot)
            current += 30
        
        # Afternoon period: (break + 60 min) to end
        current = break_min + 60  # 1 hour break
        while current < end_min:
            slot = ScheduleParser.format_30min_slot(current)
            slots.append(slot)
            current += 30
        
        return slots
    
    @staticmethod
    def generate_1hour_slots(start_min, break_min, end_min):
        """Generate 1-hour slots"""
        slots = []
        
        # Convert minutes to hours
        start_h = start_min // 60
        break_h = break_min // 60
        end_h = end_min // 60
        
        # Morning: start to break
        for h in range(start_h, break_h):
            slots.append(f"{h:02d}-{h+1:02d}")
        
        # Afternoon: (break + 1h) to end
        for h in range(break_h + 1, end_h):
            slots.append(f"{h:02d}-{h+1:02d}")
        
        return slots
    
    @staticmethod
    def parse_block(cell, granularity=30):
        """
        Parse work block - handles both 30min and 1hour formats.
        
        Formats supported:
        - 30min: 9.5-14.5-18.5_A (decimals)
        - 1hour: 13-17-22_A (integers)
        
        Args:
            cell: Cell value from CSV
            granularity: 30 or 60 minutes
            
        Returns:
            (slots, team) or None
            where slots is a list of time slot strings
        """
        if not isinstance(cell, str):
            return None
        
        # Match format: START-BREAK-END_TEAM
        m = re.match(
            r"^\s*(\d{1,2}(?:\.\d)?)\s*[-_]\s*(\d{1,2}(?:\.\d)?)\s*[-_]\s*(\d{1,2}(?:\.\d)?)\s*[_\-]\s*([A-Za-z])\s*$",
            str(cell).strip()
        )
        if not m:
            return None
        
        start_str = m.group(1)
        break_str = m.group(2)
        end_str = m.group(3)
        team = m.group(4).upper()
        
        # Convert to minutes from midnight
        start_min = ScheduleParser.time_to_minutes(start_str)
        break_min = ScheduleParser.time_to_minutes(break_str)
        end_min = ScheduleParser.time_to_minutes(end_str)
        
        # Generate slots based on granularity
        if granularity == 30:
            slots = ScheduleParser.generate_30min_slots(start_min, break_min, end_min)
        else:  # 60 minutes
            slots = ScheduleParser.generate_1hour_slots(start_min, break_min, end_min)
        
        return slots, team

def extract_minimums_from_csv(file_path, granularity=30):
    """
    Reads the CSV generated by the algorithm and calculates employee counts.
    
    Args:
        file_path: Path to schedule CSV
        granularity: 30 or 60 minutes
        
    Returns:
        Dictionary {(day_number, time_slot, team): count}
        Example for 30min: {(1, '09:00-09:30', 'A'): 3, ...}
        Example for 1hour: {(1, '09-10', 'A'): 3, ...}
    """
    df = pd.read_csv(file_path, encoding="utf-8").fillna("")
    
    # Detect day columns
    day_cols = [c for c in df.columns if re.match(r"Day\d+", c, re.IGNORECASE)]
    result = {}
    
    parser = ScheduleParser()
    
    for day_col in day_cols:
        day_num = int(re.findall(r"\d+", day_col)[0])
        
        for _, row in df.iterrows():
            cell = row[day_col]
            parsed = parser.parse_block(cell, granularity)
            if not parsed:
                continue
            slots, team = parsed
            
            for slot in slots:
                key = (day_num, slot, team)
                result[key] = result.get(key, 0) + 1
    
    return result

# ==============================================================================
# UTILITY FUNCTIONS (SHARED BY BOTH GRANULARITIES)
# ==============================================================================

def load_vacations_from_csv(vacation_csv_file):
    """
    Loads employee vacations from CSV.
    
    Returns a dictionary: {employee_id: [list of 365 values]}
    """
    print(f"\n[LOAD VACATIONS] Reading from: {vacation_csv_file}")
    
    df = pd.read_csv(vacation_csv_file, header=None, encoding='utf-8')
    
    vacations = {}
    
    for _, row in df.iterrows():
        emp_name = str(row.iloc[0]).strip()
        match = re.search(r'(\d+)', emp_name)
        if match:
            emp_id = int(match.group(1))
            vacation_values = row.iloc[1:].tolist()
            vacations[emp_id] = [int(v) if pd.notna(v) else 0 for v in vacation_values]
    
    print(f"[LOAD VACATIONS] Loaded vacations for {len(vacations)} employees")
    return vacations

def order_minimums(mins_dict, stage="RAW"):
    """Orders the minimums dictionary by: Team → Hour → Day"""
    ordered = dict(sorted(mins_dict.items(), key=lambda x: (x[0][2], x[0][1], x[0][0])))
    
    print(f"\n[ORDER MINIMUMS - {stage}]")
    print(f"  Total keys: {len(ordered)}")
    
    # Print example of result
    print(f"\n  Ordered structure (Team → Hour → Day):")
    current_team = None
    current_hour = None
    for (day, hour, team), count in list(ordered.items())[:30]:
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
    """Adds entries for missing days (holidays, sundays, etc.)"""
    if not mins_dict:
        return mins_dict
    
    # Extract days, hours and teams present
    days_in_dict = set()
    hours_in_dict = set()
    teams_in_dict = set()
    
    for (day, hour, team) in mins_dict.keys():
        days_in_dict.add(day)
        hours_in_dict.add(hour)
        teams_in_dict.add(team)
    
    # Use provided teams/hours or those from dictionary
    if all_teams_and_hours:
        teams_to_use, hours_to_use = all_teams_and_hours
    else:
        teams_to_use = teams_in_dict
        hours_to_use = hours_in_dict
    
    # Find missing days in range 1-365
    all_days = set(range(1, 366))
    missing_days = sorted(all_days - days_in_dict)
    
    print(f"\n[EXPAND MINIMUMS - ADD FERIADOS & SUNDAYS]")
    print(f"  Missing days: {len(missing_days)} ({missing_days[:15]}...)")
    
    # Add -1 entries for missing days
    added_count = 0
    for daynum in missing_days:
        for team in teams_to_use:
            for hour in hours_to_use:
                key = (daynum, hour, team)
                mins_dict[key] = -1
                added_count += 1
    
    print(f"  Total entries added: {added_count}")
    print(f"  Dictionary size: {len(mins_dict)}")
    
    return mins_dict

def compare_minimums(mins_required, mins_actual):
    """
    Compares required minimums with actual minimums.
    
    Returns:
        int: Total of missed minimums (sum of gaps where gap > 0)
    """
    if not mins_required or not mins_actual:
        return 0
    
    total_gaps = 0
    
    for key, required in mins_required.items():
        if required == -1:
            continue
        
        actual = mins_actual.get(key, 0)
        gap = max(0, required - actual)
        total_gaps += gap
    
    return total_gaps

def parse_requirements_hourly(requirements_text):
    """Parse requirements text into mins and ideals dictionaries"""
    mins, ideals = {}, {}
    if not requirements_text:
        print("[DEBUG] parse_requirements_hourly: empty input")
        return mins, ideals

    print(f"[DEBUG] parse_requirements_hourly: raw length={len(str(requirements_text))}")
    
    # Normalize separators and newlines
    text = requirements_text.replace('\r', '\n').replace(';', ',').strip()
    lines = [l for l in text.split('\n') if l.strip()]
    print(f"[DEBUG] Lines detected: {len(lines)}")
    
    # If everything is in one line, try to force split
    if len(lines) == 1:
        long_line = lines[0]
        chunks = re.split(r'(?=[A-Z]\s*,)', long_line)
        lines = [l.strip() for l in chunks if l.strip()]
        print(f"[DEBUG] Split long line into {len(lines)} logical entries")

    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 4:
            continue
        
        # Detect pattern variations
        if len(parts) >= 3 and ("Equipa" in parts[1] or "Team" in parts[1]):
            team_code = parts[1].split()[-1].upper().strip()
            hour_range = parts[2]
            values = parts[3:]
            target = mins
        elif len(parts) >= 3 and (re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', parts[1]) or 
                                   re.match(r'^\d{2}-\d{2}$', parts[1]) or
                                   re.match(r'^\d{2}\.0-\d{2}\.\d$', parts[1])):
            team_code = parts[0].split()[-1].upper().strip()
            hour_range = parts[1]
            values = parts[2:]
            target = mins
        else:
            team_label_raw, req_type, hour_range = parts[:3]
            values = parts[3:]
            team_match = re.search(r'([A-Za-z])$', team_label_raw)
            if not team_match:
                print(f"[DEBUG] Skipping invalid team_label: {team_label_raw}")
                continue
            team_code = team_match.group(1).upper()
            target = mins if 'min' in req_type.lower() else ideals

        for day_idx, val in enumerate(values, start=1):
            val_str = str(val).strip()
            if val_str.lstrip('-').isdigit():
                target[(day_idx, hour_range, team_code)] = int(val_str)
    
    print(f"[CHECK] Total mins={len(mins)} ideals={len(ideals)}")
    print(f"[CHECK] Sample mins: {list(mins.keys())[:10]}")

    return mins, ideals

def parse_employees(employees_json):
    """Parse employees JSON into teams dictionary"""
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

def generate_employees_from_vacation_csv(vacation_csv_file):
    """
    Generates employees JSON structure from vacation CSV.
    Assumes all employees can work in both Team A and Team B.
    """
    print(f"\n[GENERATE EMPLOYEES] Extracting from: {vacation_csv_file}")
    
    df = pd.read_csv(vacation_csv_file, header=None, encoding='utf-8')
    
    employees = []
    for _, row in df.iterrows():
        emp_name = str(row.iloc[0]).strip()
        if re.match(r'Employee\s*\d+', emp_name, re.IGNORECASE):
            employees.append({
                "name": emp_name,
                "teams": ["Team A", "Team B"]
            })
    
    print(f"[GENERATE EMPLOYEES] Created {len(employees)} employee records")
    return employees

# ==============================================================================
# KPI CALCULATION HELPERS
# ==============================================================================

def filter_holidays_by_schedule_range(holidays, schedule_start_date, schedule_end_date):
    """
    Filters holidays to only include those within the schedule date range.
    
    Args:
        holidays: set/list/dict of holiday dates
        schedule_start_date: datetime.date object for schedule start
        schedule_end_date: datetime.date object for schedule end
    
    Returns:
        set of datetime.date objects within the range
    """
    holidays_set = set()
    
    # If it's a dictionary (from holidays.country_holidays), use keys
    if isinstance(holidays, dict):
        holidays_iterable = holidays.keys()
    else:
        holidays_iterable = holidays
    
    for h in holidays_iterable:
        try:
            if isinstance(h, datetime):
                d = h.date()
            elif isinstance(h, date):
                d = h
            else:
                d = pd.to_datetime(str(h)).date()
            
            # Only include if within schedule range
            if schedule_start_date <= d <= schedule_end_date:
                holidays_set.add(d)
        except Exception as e:
            print(f"[WARNING] Failed to parse holiday {h}: {e}")
    
    print(f"[FILTER HOLIDAYS] Filtered from {len(list(holidays_iterable))} to {len(holidays_set)} holidays")
    print(f"  Schedule range: {schedule_start_date} to {schedule_end_date}")
    print(f"  Holidays in range: {sorted(holidays_set)}")
    
    return holidays_set

# ==============================================================================
# MAIN ANALYSIS FUNCTION
# ==============================================================================

def analyze(file, holidays, mins, employees, year, granularity=30):
    """
    Main KPI verification function - works for both 30min and 1hour granularity.
    
    Args:
        file: Path to schedule CSV
        holidays: List/set of holiday dates
        mins: Minimums text (from load_minimums_from_csv)
        employees: List of employee dicts
        year: Year for date calculations
        granularity: 30 or 60 (minutes)
        
    Returns:
        Dictionary with KPI results
    """
    print(f"\n{'='*80}")
    print(f"ANALYZE - Granularity: {granularity} minutes")
    print(f"{'='*80}")
    
    # Read CSV to detect schedule date range
    df_temp = pd.read_csv(file, encoding='utf-8', dtype=str, nrows=0)
    dia_cols_temp = [c for c in df_temp.columns if re.match(r'^(Dia|Day)\s*\d+$', c, flags=re.I)]
    if not dia_cols_temp:
        dia_cols_temp = [c for c in df_temp.columns if c.lower().startswith("dia") or c.lower().startswith("day")]
    
    # Extract day numbers from columns
    day_numbers = []
    for c in dia_cols_temp:
        m = re.search(r'(\d+)', c)
        if m:
            day_numbers.append(int(m.group(1)))
    
    if day_numbers:
        min_day = min(day_numbers)
        max_day = max(day_numbers)
        schedule_start_date = date(2021, 11, 1) + pd.Timedelta(days=min_day - 1)
        schedule_end_date = date(2021, 11, 1) + pd.Timedelta(days=max_day - 1)
        
        print(f"[SCHEDULE RANGE] Detected from CSV columns:")
        print(f"  Day range: {min_day} to {max_day}")
        print(f"  Date range: {schedule_start_date} to {schedule_end_date}")
        
        holidays = filter_holidays_by_schedule_range(holidays, schedule_start_date, schedule_end_date)
    else:
        print("[WARNING] Could not detect day columns, using all holidays")
        schedule_start_date = date(2021, 11, 1)
        schedule_end_date = date(2022, 10, 31)

    # --------------------------- Process Minimums ---------------------------
    
    # Extract actual coverage from schedule
    mins_F = extract_minimums_from_csv(file, granularity)
    mins_F_Ordered = order_minimums(
        mins_F,
        stage="RAW (WITHOUT HOLIDAYS / SUNDAYS)"
    )
    
    # Parse required minimums from CSV
    mins_required_dict, ideals_required_dict = parse_requirements_hourly(mins)
    
    # Get all teams and hours for expansion
    all_teams = set(k[2] for k in mins_required_dict.keys())
    all_hours = set(k[1] for k in mins_required_dict.keys())
    
    # Add missing days (holidays, sundays) to both dictionaries
    mins_required_ordered = order_minimums(mins_required_dict, "REQUIRED")
    mins_required_ordered = add_feriados_and_sundays(mins_required_ordered, (all_teams, all_hours))
    
    mins_final_ordered = add_feriados_and_sundays(mins_F_Ordered, (all_teams, all_hours))
    mins_final_ordered = order_minimums(mins_final_ordered, stage="FINAL (WITH HOLIDAYS & SUNDAYS)")
    
    # Calculate total staffing gap (people missing across all time slots)
    totalStaffingGap = compare_minimums(mins_required_ordered, mins_final_ordered)

    # Calculate overstaff AND coverage rate
    hourlyOverstaff = 0
    totalRequiredSlots = 0  # Total slots with valid requirements
    slotsMet = 0            # Slots where actual >= required

    for key, actual_count in mins_final_ordered.items():
        required = mins_required_ordered.get(key, 0)

        # Skip special days (marked as -1)
        if required == -1 or actual_count == -1:
            continue

        totalRequiredSlots += 1
        gap = required - actual_count

        if gap <= 0:
            slotsMet += 1  # Requirement was met (or exceeded)
        if gap < 0:
            hourlyOverstaff += abs(gap)

    # Calculate coverage rate as percentage
    if totalRequiredSlots > 0:
        staffingCoverageRate = round((slotsMet / totalRequiredSlots) * 100, 2)
    else:
        staffingCoverageRate = 100.0  # No requirements = 100% coverage

    # Ideals: only calculate if we actually have ideal values
    has_ideals = len(ideals_required_dict) > 0
    if has_ideals:
        ideals_required_ordered = order_minimums(ideals_required_dict)
        ideals_required_ordered = add_feriados_and_sundays(ideals_required_ordered, (all_teams, all_hours))
        totalIdealGap = compare_minimums(ideals_required_ordered, mins_final_ordered)
    else:
        totalIdealGap = 0
        print("[INFO] No ideal requirements provided - totalIdealGap set to 0")

    print(f"[DEBUG] Total Staffing Gap: {totalStaffingGap}")
    print(f"[DEBUG] Overstaff: {hourlyOverstaff}")
    print(f"[DEBUG] Coverage Rate: {staffingCoverageRate}% ({slotsMet}/{totalRequiredSlots} slots met)")
    
    # --------------------------- Process Schedule DataFrame ---------------------------
    
    df = pd.read_csv(file, encoding='utf-8', dtype=str).fillna("")
    
    # Normalize employee column name
    col_names_lower = [c.lower() for c in df.columns]
    employee_col = None
    
    if any("employee" in c.lower() for c in col_names_lower):
        employee_col = next(c for c in df.columns if "employee" in c.lower())
    elif any("funcionario" in c.lower() for c in col_names_lower):
        employee_col = next(c for c in df.columns if "funcionario" in c.lower())
    elif any("emp" in c.lower() for c in col_names_lower):
        employee_col = next(c for c in df.columns if "emp" in c.lower())
    else:
        employee_col = df.columns[0]
    
    if employee_col != "Employee":
        df.rename(columns={employee_col: "Employee"}, inplace=True)
    
    print(f"[KPI] Employee column detected: {employee_col}")
    
    # Helpers for parsing work blocks
    def parse_block(val):
        if not isinstance(val, str):
            return (None, None, None)
        # Match both decimal and integer formats
        m = re.match(r'^\s*(\d{1,2}(?:\.\d)?)\s*[-_]\s*(\d{1,2}(?:\.\d)?)\s*[-_]\s*(\d{1,2}(?:\.\d)?)\s*[_\-]\s*([A-Za-z])\s*$', val.strip())
        if m:
            start = float(m.group(1))
            end = float(m.group(3))
            team = m.group(4).upper()
            return (start, end, team)
        return (None, None, None)
    
    def is_work_block(val):
        s, e, t = parse_block(val)
        return s is not None and e is not None and t is not None
    
    # Initialize KPI counters
    workDaysTargetDeviation = 0
    vacationDaysQuotaDeviation = 0
    holidayWorkLimitViolations = 0
    consecutiveDaysViolations = 0
    minRestViolations = 0
    
    # Parse employee teams
    teams = parse_employees(employees)
    
    holidays_set = holidays if isinstance(holidays, set) else set(holidays)
    
    # Day columns
    dia_cols = [c for c in df.columns if re.match(r'^(Dia|Day)\s*\d+$', c, flags=re.I)]
    if not dia_cols:
        dia_cols = [c for c in df.columns if c.lower().startswith("dia") or c.lower().startswith("day")]
    
    # Map column → day number
    col_to_day = {}
    for c in dia_cols:
        m = re.search(r'(\d+)', c)
        if m:
            col_to_day[c] = int(m.group(1))
        else:
            col_to_day[c] = len(col_to_day) + 1
    
    # Create map of day numbers to real dates
    start_date = date(2021, 11, 1)
    daynum_to_date = {}
    for daynum in col_to_day.values():
        daynum_to_date[daynum] = start_date + pd.Timedelta(days=daynum - 1)
    
    # Special columns (holidays)
    all_special_cols = [col for col, daynum in col_to_day.items() 
                        if daynum in daynum_to_date and daynum_to_date[daynum] in holidays_set]
    
    # Debug counters
    debug_work_holidays = []
    
    # Process each employee row
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
        
        # Day counts
        worked_days = sum(1 for c in dia_cols if c in row.index and is_work_block(row[c]))
        vacation_days = sum(1 for c in dia_cols if c in row.index and str(row[c]).strip().upper() in ("F", "VACATION"))
        
        # KPI: Work days target deviation (target: 223 days/year)
        workDaysTargetDeviation += abs(223 - worked_days)
        
        # KPI: Vacation days quota deviation (quota: 30 days/year)
        vacationDaysQuotaDeviation += abs(30 - vacation_days)
        
        # KPI: Holiday work limit violations (limit: max 22 holidays/year)
        total_worked_holidays = sum(1 for c in all_special_cols if c in row.index and is_work_block(row[c]))
        
        if total_worked_holidays > 0:
            worked_holiday_details = []
            for c in all_special_cols:
                if c in row.index and is_work_block(row[c]):
                    daynum = col_to_day.get(c)
                    real_date = daynum_to_date.get(daynum) if daynum else None
                    worked_holiday_details.append((c, daynum, real_date, row[c]))
            
            debug_work_holidays.append({
                'emp_id': emp_id,
                'total': total_worked_holidays,
                'details': worked_holiday_details
            })
        
        if total_worked_holidays > 22:
            holidayWorkLimitViolations += (total_worked_holidays - 22)
        
        # KPI: Consecutive days violations (6+ consecutive work days)
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
        consecutiveDaysViolations += fails
        
        # KPI: Minimum rest time violations (11 hours between shifts)
        # Check each consecutive day pair (day D and day D+1)
        for i in range(len(dia_cols) - 1):
            current_col = dia_cols[i]
            next_col = dia_cols[i + 1]
            
            current_shift = row.get(current_col, "")
            next_shift = row.get(next_col, "")
            
            # Skip if either shift is not a work block (OFF/VACATION/empty)
            if not is_work_block(current_shift) or not is_work_block(next_shift):
                continue
            
            # Parse shift times
            _, end_current, _ = parse_block(current_shift)
            start_next, _, _ = parse_block(next_shift)
            
            # Skip if parsing failed
            if end_current is None or start_next is None:
                continue
            
            # Calculate rest hours (assuming next day starts after midnight)
            # Normal case: shift ends at 22h, next starts at 9h → rest = (24-22) + 9 = 11h
            rest_hours = (24 - end_current) + start_next
            
            # Check for violation (less than 11 hours rest)
            if rest_hours < 11:
                minRestViolations += 1
    
    # Print debug info
    print(f"\n[DEBUG WORK HOLIDAYS]")
    print(f"  Total special columns (holidays/sundays): {len(all_special_cols)}")
    print(f"  Employees who worked on holidays/sundays: {len(debug_work_holidays)}")
    
    if debug_work_holidays:
        print(f"\n  Top 5 employees with most worked holidays:")
        sorted_debug = sorted(debug_work_holidays, key=lambda x: x['total'], reverse=True)[:5]
        for emp_data in sorted_debug:
            print(f"    Employee {emp_data['emp_id']}: {emp_data['total']} holidays worked")
            for col, daynum, real_date, shift_val in emp_data['details'][:3]:
                print(f"      - Day {daynum} ({real_date}): {shift_val}")
    
    print(f"  Total holiday work limit violations (>22): {holidayWorkLimitViolations}")
    
    return {
        "workDaysTargetDeviation": workDaysTargetDeviation,
        "vacationDaysQuotaDeviation": vacationDaysQuotaDeviation,
        "holidayWorkLimitViolations": holidayWorkLimitViolations,
        "consecutiveDaysViolations": consecutiveDaysViolations,
        "minRestViolations": minRestViolations,
        "totalStaffingGap": totalStaffingGap,
        "totalIdealGap": totalIdealGap if has_ideals else None,
        "excessStaffing": hourlyOverstaff,
        "staffingCoverageRate": staffingCoverageRate
    }

# ==============================================================================
# LOCAL TESTING MODE
# ==============================================================================

if __name__ == "__main__":
    print("="*80)
    print("UNIFIED KPI VERIFICATION - LOCAL TESTING MODE")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  TEST_30MIN = {TestConfig.TEST_30MIN}")
    print(f"  TEST_1HOUR = {TestConfig.TEST_1HOUR}")
    print("="*80)
    
    # Portuguese holidays
    pt_holidays = holidays.Portugal(years=[2021, 2022])
    holidays_list = list(pt_holidays.keys())
    
    results = {}
    
    # Test 30-minute granularity (if enabled)
    if TestConfig.TEST_30MIN:
        print(f"\n{'='*80}")
        print("TESTING: 30-MINUTE GRANULARITY")
        print(f"{'='*80}")
        print(f"Schedule CSV: {TestConfig.CSV_30MIN}")
        print(f"Minimums CSV: {TestConfig.MINS_CSV}")
        print(f"Vacation CSV: {TestConfig.VACATION_CSV}")
        
        try:
            # Load data
            minimums_text = load_minimums_from_csv(TestConfig.MINS_CSV, granularity=30)
            vacations_dict = load_vacations_from_csv(TestConfig.VACATION_CSV)
            employees_data = generate_employees_from_vacation_csv(TestConfig.VACATION_CSV)
            
            print(f"\nConfiguration loaded successfully:")
            print(f"  Minimums lines: {len(minimums_text.split(chr(10)))}")
            print(f"  Employees: {len(employees_data)}")
            print(f"  Vacations loaded for: {len(vacations_dict)} employees")
            
            # Run analysis
            results['30min'] = analyze(
                file=TestConfig.CSV_30MIN,
                holidays=holidays_list,
                mins=minimums_text,
                employees=employees_data,
                year=2021,
                granularity=30
            )
            
            print(f"\n{'='*80}")
            print("KPI RESULTS - 30-MINUTE GRANULARITY")
            print(f"{'='*80}")
            for key, value in results['30min'].items():
                display_value = "N/A" if value is None else value
                print(f"{key:30s}: {display_value}")
            print(f"{'='*80}")
            
        except FileNotFoundError as e:
            print(f"\n[ERROR] File not found: {e}")
            print(f"Skipping 30min test")
        except Exception as e:
            print(f"\n[ERROR] 30min test failed: {e}")
            traceback.print_exc()
    
    # Test 1-hour granularity (if enabled)
    if TestConfig.TEST_1HOUR:
        print(f"\n{'='*80}")
        print("TESTING: 1-HOUR GRANULARITY")
        print(f"{'='*80}")
        print(f"Schedule CSV: {TestConfig.CSV_1HOUR}")
        print(f"Minimums CSV: {TestConfig.MINS_CSV}")
        print(f"Vacation CSV: {TestConfig.VACATION_CSV}")
        
        try:
            # Load data
            minimums_text = load_minimums_from_csv(TestConfig.MINS_CSV, granularity=60)
            vacations_dict = load_vacations_from_csv(TestConfig.VACATION_CSV)
            employees_data = generate_employees_from_vacation_csv(TestConfig.VACATION_CSV)
            
            print(f"\nConfiguration loaded successfully:")
            print(f"  Minimums lines: {len(minimums_text.split(chr(10)))}")
            print(f"  Employees: {len(employees_data)}")
            print(f"  Vacations loaded for: {len(vacations_dict)} employees")
            
            # Run analysis
            results['1hour'] = analyze(
                file=TestConfig.CSV_1HOUR,
                holidays=holidays_list,
                mins=minimums_text,
                employees=employees_data,
                year=2021,
                granularity=60
            )
            
            print(f"\n{'='*80}")
            print("KPI RESULTS - 1-HOUR GRANULARITY")
            print(f"{'='*80}")
            for key, value in results['1hour'].items():
                display_value = "N/A" if value is None else value
                print(f"{key:30s}: {display_value}")
            print(f"{'='*80}")
            
        except FileNotFoundError as e:
            print(f"\n[ERROR] File not found: {e}")
            print(f"Skipping 1hour test")
        except Exception as e:
            print(f"\n[ERROR] 1hour test failed: {e}")
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    if results:
        print(f"Tests run: {', '.join(results.keys())}")
    print(f"{'='*80}")


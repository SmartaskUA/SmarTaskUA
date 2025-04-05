import csv

def verify_schedule(csv_file="calendario_turnos.csv"):
    schedule = {}
    employees = []
    num_days = 0
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        header = next(reader) 
        num_days = len(header) - 1 
        for row in reader:
            emp = row[0]
            employees.append(emp)
            schedule[emp] = row[1:]

    holidays = {7, 14, 21, 28}
    is_valid = True

    # Check T->M constraint
    print("\nChecking T->M violations:")
    for emp in employees:
        emp_schedule = schedule[emp]
        for d in range(num_days - 1):
            curr = emp_schedule[d]
            next_day = emp_schedule[d + 1]
            if curr.startswith("T_") and next_day.startswith("M_"):
                print(f"T->M violation for {emp} on days {d+1} to {d+2}")
                is_valid = False

    # Check daily team requirements
    print("\nChecking daily team requirements:")
    for day in range(num_days):
        day_vars = [schedule[emp][day] for emp in employees]
        m_a = sum(1 for v in day_vars if v == "M_A")
        t_a = sum(1 for v in day_vars if v == "T_A")
        m_b = sum(1 for v in day_vars if v == "M_B")
        t_b = sum(1 for v in day_vars if v == "T_B")
        if m_a < 2 or t_a < 2 or m_b < 1 or t_b < 1:
            print(f"Day {day+1} team requirement violation: M_A={m_a}, T_A={t_a}, M_B={m_b}, T_B={t_b}")
            is_valid = False

    # Check total shifts and holiday constraints
    print("\nChecking employee constraints:")
    for emp in employees:
        emp_schedule = schedule[emp]
        total_shifts = sum(1 for v in emp_schedule if v in ["M_A", "M_B", "T_A", "T_B"])
        if total_shifts > 20:
            print(f"{emp} exceeds 20 shifts: {total_shifts}")
            is_valid = False
        holiday_shifts = sum(1 for i, v in enumerate(emp_schedule, 1) if i in holidays and v in ["M_A", "M_B", "T_A", "T_B"])
        if holiday_shifts > 2:
            print(f"{emp} exceeds 2 holiday shifts: {holiday_shifts}")
            is_valid = False
        for start in range(num_days - 5):
            window = emp_schedule[start:start + 6]
            if all(v in ["M_A", "M_B", "T_A", "T_B"] for v in window):
                print(f"{emp} has 6 consecutive workdays starting at day {start + 1}")
                is_valid = False

    if is_valid:
        print("\nAll constraints satisfied!")
        
if __name__ == "__main__":
    verify_schedule()
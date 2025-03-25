from algorithm.formulation import HOLIDAYS


def constraint_TM(v1, x1, v2, x2):
    """Impedir a sequência inválida de turnos T->M."""
    e1, d1 = v1[1:].split(',')
    e2, d2 = v2[1:].split(',')
    d1 = int(d1)
    d2 = int(d2)

    if e1 != e2:
        return True
    if d1 == d2:
        return x1 != x2
    if abs(d1 - d2) != 1:
        return True
    if d1 > d2 and x2 == "T":
        return x1 != "M"
    if d1 < d2 and x1 == "T":
        return x2 != "M"
    return True


def constraint_vacations(v1, x1):
    """Impedir que um funcionário trabalhe durante suas férias."""
    return x1 != "F"


def constraint_work_days(employee, assignment, max_days=223):
    """Garantir que o funcionário não trabalhe mais que 223 dias no ano."""
    work_days = sum(1 for var, val in assignment.items() if var.startswith(f"E{employee}") and val in ["M", "T"])
    return work_days <= max_days


def constraint_sundays_holidays(employee, assignment, max_days=22):
    """Garantir que o funcionário não trabalhe mais que 22 domingos e feriados."""
    sundays_holidays = sum(1 for var, val in assignment.items() if var.startswith(f"E{employee}") and
                           (int(var.split(',')[1]) in HOLIDAYS or (int(var.split(',')[1]) - 1) % 7 == 0)
                           and val in ["M", "T"])
    return sundays_holidays <= max_days


def constraint_max_consecutive_days(employee, assignment, max_consecutive=5):
    """Garantir que o funcionário não trabalhe mais que 5 dias consecutivos."""
    consecutive_days = 0
    variables = sorted((var for var in assignment if var.startswith(f"E{employee}")), key=lambda x: int(x.split(',')[1]))

    for var in variables:
        if assignment[var] in ["M", "T"]:
            consecutive_days += 1
            if consecutive_days > max_consecutive:
                return False
        else:
            consecutive_days = 0
    return True





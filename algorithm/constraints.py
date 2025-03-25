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


def constraint_vacations(v1, x1, v2, x2):
    """Impedir que um funcionário trabalhe durante suas férias."""
    return x1 != "F"  # As férias são verificadas apenas pelo valor de x1


def constraint_work_days(v1, x1, v2, x2):
    """Garantir que o funcionário não trabalhe mais que 223 dias no ano."""
    employee = v1.split(',')[0]
    work_days = sum(1 for day in range(1, 365) if f"{employee},{day}" in v1 and x1 in ["M", "T"])
    return work_days <= 223


def constraint_sundays_holidays(v1, x1, v2, x2):
    """Garantir que o funcionário não trabalhe mais que 22 domingos e feriados."""
    employee = v1.split(',')[0]
    sundays_holidays = sum(
        1 for day in range(1, 365) if f"{employee},{day}" in v1 and
        (day in HOLIDAYS or (day - 1) % 7 == 0) and
        x1 in ["M", "T"]
    )
    return sundays_holidays <= 22


def constraint_max_consecutive_days(v1, x1, v2, x2):
    """Garantir que o funcionário não trabalhe mais que 5 dias consecutivos."""
    e1, d1 = v1.split(',')
    e2, d2 = v2.split(',')
    d1 = int(d1)
    d2 = int(d2)

    # Apenas verificar dias consecutivos (d1, d1+1)
    if e1 != e2 or abs(d1 - d2) != 1:
        return True

    # Verificar turnos consecutivos de trabalho
    if x1 in ["M", "T"] and x2 in ["M", "T"]:
        # Retornar falso se for o 6º dia consecutivo
        consecutive_days = sum(1 for d in range(d1 - 4, d2 + 1) if f"{e1},{d}" in v1 and x1 in ["M", "T"])
        return consecutive_days <= 5

    return True


def create_constraints(employees, days, domain):
    """Cria o dicionário de restrições parametrizado para ser usado no ConstraintSearch.

    Args:
        employees (list): Lista de identificadores de funcionários (ex: ["E1", "E2", ..., "E11"]).
        days (list): Lista de dias para a geração de variáveis (ex: range(1, 365)).
        domain (list): Lista de possíveis valores do domínio (ex: ["0", "M", "T", "F"]).

    Returns:
        dict: Dicionário de restrições entre as variáveis.
    """
    constraints = {}

    for d in days:
        for e in employees:
            # Restrições de sequência inválida T->M e de máximo 5 dias consecutivos
            constraints[(f"{e},{d}", f"{e},{d + 1}")] = constraint_TM
            constraints[(f"{e},{d}", f"{e},{d + 1}")] = constraint_max_consecutive_days

            # Restrições individuais (férias, dias de trabalho, domingos e feriados)
            constraints[(f"{e},{d}", f"{e},{d}")] = constraint_vacations
            constraints[(f"{e},{d}", f"{e},{d}")] = constraint_work_days
            constraints[(f"{e},{d}", f"{e},{d}")] = constraint_sundays_holidays

    return constraints


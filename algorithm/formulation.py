from constraintsearch import ConstraintSearch

EMPLOYEES = [f"E{i}" for i in range(1, 12)]
SHIFTS = ["M", "T"]
DAYS = list(range(1, 365))
DOMAIN = ["0", "M", "T", "F"]

def generate_variables():
    return {f"E{e},{d}" for e in EMPLOYEES for d in DAYS}

def get_domain():
    return {v:DOMAIN for v in generate_variables()}
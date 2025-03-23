from constraintsearch import ConstraintSearch
import random

EMPLOYEES = [f"E{i}" for i in range(1, 12)]
SHIFTS = ["M", "T"]
DAYS = list(range(1, 365))
DOMAIN = ["0", "M", "T", "F"]
SUNDAYS = lambda d: (d-1) % 7
HOLIDAYS = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}
VACATIONS = {emp: set(random.sample(len(DAYS), 30)) for emp in EMPLOYEES}

def generate_variables():
    return {f"E{e},{d}" for e in EMPLOYEES for d in DAYS}

def get_domain():
    return {v:DOMAIN for v in generate_variables()}
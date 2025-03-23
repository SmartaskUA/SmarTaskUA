from constraintsearch import ConstraintSearch
from formulation import generate_variables, get_domain
from constraints import constraint_TM

vars = generate_variables()
domains = get_domain()
constraints = {}
from itertools import product


def handle_ho_constraint(domains, constraints, variables, constraint):
    A = "".join(variables)
    ho_domains = [domains[v] for v in variables]
    A_domain = []
    for combo in product(*ho_domains):
        if constraint(combo):
            A_domain.append(combo)
    domains[A] = A_domain
    variables.append(A)
    for i, v in enumerate(variables):
        if v == A:
            continue

        def make_constraint(index, aux=A, var=v):
            def binary_constraint(varA, valA, varV, valV):
                if varA == aux:
                    return valA[index] == valV
                if varV == aux:
                    return valV[index] == valA
                return True

            return binary_constraint

        c_fn = make_constraint(i)
        constraints[(A, v)] = c_fn
        constraints[(v, A)] = c_fn

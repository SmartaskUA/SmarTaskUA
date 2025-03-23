class ConstraintSearch:

    def __init__(self, domain, constraints):
        self.domain = domain
        self.constraints = constraints
        self.calls = 0

    def search(self, domains=None):
        self.calls += 1
        if domains is None:
            domains = self.domain

        if domains==None:
            domains = self.domains

        if any([lv==[] for lv in domains.values()]):
            return None

        if all([len(lv)==1 for lv in list(domains.values())]):
            for (var1,var2) in self.constraints:
                constraint = self.constraints[var1,var2]
                if not constraint(var1,domains[var1][0],var2,domains[var2][0]):
                    return None 
            return { v:lv[0] for (v,lv) in domains.items() }
       
        for var in domains.keys():
            if len(domains[var])>1:
                for val in domains[var]:
                    newdomains = dict(domains)
                    newdomains[var] = [val]

                    if newdomains := self.propagate_constraints(newdomains, var, val):
                        solution = self.search(newdomains)
                        if solution != None:
                            return solution
        return None

    def propagate_constraints(self, domain, var, val):
        for variable, contra_domain in domain.items():
            if variable == var:
                continue

            for pair, constrain in self.constraints.items():
                if not pair in [(var, variable), (variable, var)]:
                    continue

                domain[variable] = [c for c in contra_domain if constrain(var,val,variable,c)]

            if domain[variable] == []:
                return
        
        return domain
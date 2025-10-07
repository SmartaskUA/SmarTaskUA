class CPSatContext:
    """
    Shared state CP-SAT handlers can read/write.
    """
    def __init__(self, *, m, Employees, D, S, num_days, shifts,
                 off, shift_id, y,
                 vac_mask, allowed_teams_per_emp,
                 min_required, special_days):
        self.m = m
        self.Employees = Employees    # range(0..n-1)
        self.D = D                    # range(1..num_days)
        self.S = S                    # range(1..shifts)
        self.num_days = num_days
        self.shifts = shifts
        self.off = off                # {(e,d)->BoolVar}
        self.shift_id = shift_id      # {(e,d)->IntVar 0..shifts}
        self.y = y                    # {(e,d,s,t)->BoolVar}
        self.vac_mask = vac_mask      # {(e,d)->bool}
        self.allowed_teams_per_emp = allowed_teams_per_emp  # list[list[int]]
        self.min_required = min_required                    # {(day,s,t): req}
        self.special_days = set(special_days)               # {int 1..N}

        # Outputs for handlers:
        self.obj_terms: List[Any] = []   # linear exprs for objective
        self.extras: Dict[str, Any] = {} # stash shared computed vars


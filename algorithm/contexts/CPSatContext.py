class CPSatContext:
    """
    Shared state CP-SAT handlers can read/write.
    """
    def __init__(self, *, m, Employees, D, S, num_days, shifts,
                 off, shift_id, y,
                 vac_mask, allowed_teams_per_emp,
                 min_required, special_days):
        self.m = m
        self.Employees = Employees    
        self.D = D                    
        self.S = S                    
        self.num_days = num_days
        self.shifts = shifts
        self.off = off                
        self.shift_id = shift_id      
        self.y = y                    
        self.vac_mask = vac_mask      
        self.allowed_teams_per_emp = allowed_teams_per_emp  
        self.min_required = min_required                    
        self.special_days = set(special_days)               

        self.obj_terms: List[Any] = [] 
        self.extras: Dict[str, Any] = {} 


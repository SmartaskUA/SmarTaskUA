# rules_engine.py
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Set, Optional
import numpy as np

@dataclass
class Rule:
    id: str
    type: str
    kind: str          # "hard" | "soft"
    description: str
    scope: str
    params: Dict[str, Any]

class RuleEngine:
    """
    Interpreta o JSON de regras e fornece checagens reutilizáveis
    para os algoritmos (greedy/ILP).
    """
    def __init__(
        self,
        rules_config: Dict[str, Any],
        *,
        num_days: int,
        shifts: int,
        employees: List[int],                              # 1-based ids para greedy
        teams_map: Dict[int, List[int]],                  # emp_id -> [team_ids permitidos]
        vacations_1based: Dict[int, List[int]],           # emp_id -> [dias 1..N]
        special_days_1based: Set[int],                    # {dias 1..N} domingos+feriados
        target_workdays: int = 223
    ):
        self.rules: List[Rule] = [Rule(**r) for r in rules_config.get("rules", [])]
        self.num_days = num_days
        self.shifts = int(shifts)
        self.employees = employees
        self.teams_map = teams_map
        self.vac_1b = vacations_1based
        self.special = set(special_days_1based)
        self.target_workdays = target_workdays

        # índices úteis
        self.has_team_elig = any(r.type == "team_eligibility" for r in self.rules)
        self.has_max_consec = any(r.type == "max_consecutive_days" for r in self.rules)
        self.has_special_cap = any(r.type == "max_special_days" for r in self.rules)
        self.has_no_earlier_next = any(r.type == "no_earlier_shift_next_day" for r in self.rules)
        self.has_max_total = any(r.type == "max_total_workdays" for r in self.rules)
        self.has_vac_block = any(r.type == "vacation_block" for r in self.rules)
        self.soft_min_cov = next((r for r in self.rules if r.type == "min_coverage" and r.kind == "soft"), None)

        # parâmetros (com defaults iguais ao código atual)
        self.window = next((int(r.params.get("window", 6)) for r in self.rules if r.type=="max_consecutive_days"), 6)
        self.max_in_window = next((int(r.params.get("max_worked", 5)) for r in self.rules if r.type=="max_consecutive_days"), 5)
        self.special_cap = next((int(r.params.get("cap", 22)) for r in self.rules if r.type=="max_special_days"), 22)
        self.max_total = next((int(r.params.get("max", 223)) for r in self.rules if r.type=="max_total_workdays"), 223)
        self.penalty_per_missing = int(self.soft_min_cov.params.get("penalty_per_missing", 1000)) if self.soft_min_cov else 1000

    # ---------- helpers sobre estado ----------
    @staticmethod
    def _worked_days_for_emp(assign_list: List[Tuple[int,int,int]]) -> List[int]:
        # assignment p -> [(day, shift, team)]
        return sorted({d for (d, _s, _t) in assign_list})

    def _shift_on_day(self, assign_list: List[Tuple[int,int,int]], d: int) -> Optional[int]:
        for (day, s, _t) in assign_list:
            if day == d:
                return s
        return None

    def _count_special(self, assign_list: List[Tuple[int,int,int]]) -> int:
        return sum(1 for (d, _s, _t) in assign_list if d in self.special)

    # ---------- API principal para greedy ----------
    def is_feasible(
        self,
        p: int, d: int, s: int, t: int,
        assignment: Dict[int, List[Tuple[int,int,int]]]
    ) -> bool:
        """
        Verifica todas as regras 'hard' aplicáveis antes de atribuir (p,d,s,t).
        """
        emp_assign = assignment[p]

        # 1) Team eligibility
        if self.has_team_elig:
            if t not in set(self.teams_map.get(p, [])):
                return False

        # 2) Vacation block
        if self.has_vac_block:
            if d in set(self.vac_1b.get(p, [])):
                return False

        # 3) Max total workdays (cap de 223)
        if self.has_max_total:
            # considerar esta atribuição
            already = len(self._worked_days_for_emp(emp_assign))
            if d not in self._worked_days_for_emp(emp_assign) and already + 1 > self.max_total:
                return False

        # 4) Janelas de consecutivos (no máximo 5 em qualquer janela de 6)
        if self.has_max_consec:
            days = self._worked_days_for_emp(emp_assign)
            # incluir d
            if d not in days:
                days = sorted(days + [d])
            # verificar todas as janelas de tamanho 'window'
            # forma simples: contar presença por janela deslizante
            # (equivalente ao comportamento anterior)
            arr = np.zeros(self.num_days+1, dtype=int)  # 1-based
            for dx in days:
                arr[dx] = 1
            # soma em cada janela
            for i in range(1, self.num_days - self.window + 2):
                if arr[i:i+self.window].sum() > self.max_in_window:
                    return False

        # 5) Cap de Domingos/Feriados
        if self.has_special_cap:
            cnt = self._count_special(emp_assign)
            if d in self.special:
                cnt += 1 if all(existing_d != d for (existing_d, _, _) in emp_assign) else 0
            if cnt > self.special_cap:
                return False

        # 6) Proibir transição para turno mais cedo no dia seguinte (e simétrico anterior)
        if self.has_no_earlier_next:
            # ontem/amanhã
            s_prev = self._shift_on_day(emp_assign, d-1)
            s_next = self._shift_on_day(emp_assign, d+1)
            if s_prev is not None and s < s_prev:
                return False
            if s_next is not None and s_next < s:
                return False

        return True

    # ---------- “soft min coverage” (greedy) ----------
    def min_coverage_score(self, d: int, s: int, t: int, counts_func) -> int:
        """
        Interface genérica para a heurística f2 do greedy.
        `counts_func(d,s,t)` deve devolver (current, min_required, ideal_required).
        Retorna exatamente a escala usada no código antigo: 0, 1, 2+k.
        Só é usada se a regra 'min_coverage' existir; caso contrário mantemos 1.
        """
        if not self.soft_min_cov:
            return 1  # neutro
        current, min_req, ideal_req = counts_func(d, s, t)
        if current < min_req:
            return 0
        elif current < ideal_req:
            return 1
        else:
            return 2 + (current - ideal_req)

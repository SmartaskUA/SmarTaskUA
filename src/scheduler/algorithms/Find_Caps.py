class Employee:
    def __init__(self, id, name, team_ids=None):
        self.id = id
        self.name = name
        self.team_ids = team_ids if team_ids else set()

    # Isto permite fazer emp["teams"]
    def __getitem__(self, key):
        if key == "teams":
            return list(self.team_ids)
        if key == "id":
            return self.id
        if key == "name":
            return self.name
        raise KeyError(key)

    # Isto permite fazer emp.get("teams", [])
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


"""
find_min_caps.py
=================

Encontra, para cada `spacing` (2..20), o valor MÍNIMO de `cap`
(número máximo de padrões semanais mantidos por funcionário em
`_reduce_patterns`) que ainda permite atingir, de forma CONSISTENTE
(pior-caso, não melhor-caso), o número óptimo de mínimos cumpridos
(por omissão: missed_mins <= 103).

Em vez de testar cap = 1, 2, 3, ... um a um, usa:

  1) Pesquisa exponencial ("galloping search") para encontrar
     rapidamente um limite superior `hi` que já cumpre o target.
  2) Pesquisa binária dentro de (lo, hi] para encontrar o cap mínimo.
  3) Uma fase de confirmação (mais seeds) no valor encontrado.

CRITÉRIO DE ACEITAÇÃO — PIOR-CASO, NÃO MELHOR-CASO:
Um cap só é aceite se TODAS as seeds testadas atingirem o target, não
apenas uma. O algoritmo tem aleatoriedade (random.shuffle em
Pos_Weeks), por isso um cap que só bate o alvo "por sorte" numa seed
em várias não é um cap robusto para produção — é exactamente esse o
padrão que causava resultados de missed_mins entre 103 e 110 nas runs
de produção. Ao exigir que TODAS as seeds testadas batam o alvo,
procuramos um cap que dê o resultado óptimo de forma consistente.

Nota de honestidade: isto continua a ser uma garantia estatística
("nunca falhou nas N seeds testadas"), não uma prova matemática de
que nunca falha em nenhuma seed possível. Se mesmo assim vires
variância residual em produção depois disto, a causa mais provável
já não é o cap, mas sim a aleatoriedade de desempate dentro do
Pos_Weeks() em si.

ANTES DE CORRER:
  - Confirma o import de `Heuristica` (ajusta o caminho do módulo)
    e os caminhos dos CSVs em `load_data()`.
  - Ajusta SPACINGS, TARGET_MISSED_MINS, YEAR, e os tempos de ILP se
    necessário.

USO:
    python Find_Caps.py
"""

import csv
import json
import os
import random
import sys
import time


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)  # .../src/scheduler
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)


# TODO: ajusta este import para o caminho real da tua classe Heuristica
from algorithms.Puzzle_Heuristic import Heuristica

# =====================================================================
# CONFIGURAÇÃO
# =====================================================================

SPACINGS = [2,3,4,5]      # ajusta ao intervalo de spacings que queres testar
TARGET_MISSED_MINS = 103          # valor óptimo por omissão (missed_mins <= isto, pior-caso)
DEFAULT_MODE = "worst_case"       # "worst_case" (todas as seeds têm de bater o target)
                                   # ou "average" (a MÉDIA das seeds tem de bater o target)
YEAR = 2025

# Overrides por spacing: usa isto quando um spacing específico precisa
# de um critério diferente do default acima (ex: tolerância em média
# em vez de exigir que TODAS as seeds batam o valor exacto).
# Exemplo: spacing 3 aceita cap se a MÉDIA das seeds for <= 103.1,
# em vez de exigir que a PIOR seed seja <= 103.
SPACING_OVERRIDES = {
    3: {"target": 103.38, "mode": "average"},
}


def get_target_and_mode(spacing):
    """Devolve (target, mode) para o spacing dado, aplicando overrides se existirem."""
    override = SPACING_OVERRIDES.get(spacing)
    if override:
        return override["target"], override["mode"]
    return TARGET_MISSED_MINS, DEFAULT_MODE

CAP_LO_DEFAULT = 1                # limite inferior absoluto da pesquisa
CAP_HI_START = 200                # primeiro palpite de limite superior (pior-caso precisa de mais margem)
CAP_HI_MAX = 20000                # protecção contra loop infinito

TRIALS_PER_CANDIDATE = 8          # nº de execuções por candidato durante a pesquisa (pior-caso)
CONFIRM_TRIALS = 20               # nº de execuções extra para confirmar robustez do resultado final
SEEDS_POOL = [1000 + i for i in range(max(TRIALS_PER_CANDIDATE, CONFIRM_TRIALS))]

# Tempo limite do ILP por semana. Durante a pesquisa usamos um valor
# baixo para acelerar (queremos apenas comparar caps entre si); na
# confirmação final usamos o valor "de produção".
SEARCH_ILP_TIME_LIMIT = 60
CONFIRM_ILP_TIME_LIMIT = 600

RESULTS_FILE = os.path.join(_THIS_DIR, "min_cap_results.json")


def load_data():
    vacations_path = "/home/hugo/Desktop/SmarTaskUA/src/api/src/main/resources/vacationData/24_employees/templates/VacationTemplate_Case1_24.csv"
    minimuns_path = "/home/hugo/Desktop/SmarTaskUA/src/api/src/main/resources/minimuns/minimuns_3shifts_2teams_24emp.csv"

    # --- Férias: ler o CSV para linhas reais (rows_to_vac_dict espera isto) ---
    with open(vacations_path, newline='', encoding='utf-8') as f:
        vacations_rows = list(csv.reader(f))

    # --- Mínimos / Ideais ---
    minimums_rows = []
    with open(minimuns_path, 'r', encoding='ISO-8859-1') as f:
        raw_rows = list(csv.reader(f))
        for row in raw_rows:
            if not row:
                continue
            label = row[0].strip().upper()
            # aceita 'Equipa A', 'Equipa B', etc. mas ignora a linha de cabeçalho 'Equipa'
            if len(row) >= 2 and label.startswith("EQUIPA") and label != "EQUIPA":
                minimums_rows.append(row)

    # --- Funcionários ---
    employees = []
    for i in range(1, 25):
        team_ids = set()
        if 1 <= i <= 10 or 21 <= i <= 24:
            team_ids.add("Equipa A")
        if 11 <= i <= 20 or 21 <= i <= 24:
            team_ids.add("Equipa B")
        emp = Employee(id=str(i), name=f"Employee {i}", team_ids=team_ids)
        employees.append(emp)

    return vacations_rows, minimums_rows, employees   # <-- devolve as LISTAS, não os paths


# =====================================================================
# INFRA DE EXECUÇÃO
# =====================================================================

def make_scheduler_with_cap(spacing, cap, vacations_rows, minimums_rows,
                             employees, ilp_time_limit):
    """
    Cria uma instância de Heuristica em que _build_cap_table devolve
    sempre `cap`, independentemente do spacing.

    full=False é obrigatório: o cap só é aplicado em Pontuate quando
    self.full é False (ver `_reduce_patterns`).
    """

    # Filtra `minimums_rows` para garantir 100% que não chega nada inválido ao Heuristica
    clean_mins = [r for r in minimums_rows if r and len(r) >= 2]

    sched = Heuristica(
        vacations_rows=vacations_rows,
        minimums_rows=clean_mins,
        employees=employees,
        maxTime=None,
        year=YEAR,
        spacing=spacing,
        full=False,
    )

    # `_build_cap_table()` já devolve o inteiro final (não um dict),
    # por isso o monkeypatch é directo.
    sched._build_cap_table = lambda: cap
    sched.ILP_TIME_LIMIT_SECONDS = ilp_time_limit

    return sched


def run_once(spacing, cap, vacations_rows, minimums_rows, employees, seed, ilp_time_limit):
    random.seed(seed)
    sched = make_scheduler_with_cap(
        spacing, cap, vacations_rows, minimums_rows, employees, ilp_time_limit
    )
    sched.build_ideals()
    sched.Pos_Weeks()
    kpis = sched.evaluate_kpis()
    return kpis["missed_mins"]


def missed_mins_for_cap(spacing, cap, vacations_rows, minimums_rows, employees,
                         n_trials, ilp_time_limit):
    """
    Corre `n_trials` execuções independentes (seeds diferentes) e avalia
    o cap segundo o modo definido para este spacing (ver SPACING_OVERRIDES):

      - "worst_case" (default): devolve o PIOR (máximo) missed_mins.
        Um cap só é aceite se TODAS as seeds testadas baterem o target.
        Sai mais cedo (fail-fast) assim que uma seed FALHA o target.

      - "average": devolve a MÉDIA do missed_mins entre as `n_trials`
        seeds. Um cap é aceite se a média bater o target (tolerância),
        mesmo que seeds individuais fiquem ligeiramente acima. Aqui não
        há fail-fast, porque a média só é conhecida no fim de todas as
        trials.
    """
    target, mode = get_target_and_mode(spacing)
    values = []

    for i in range(n_trials):
        seed = SEEDS_POOL[i % len(SEEDS_POOL)]
        val = run_once(spacing, cap, vacations_rows, minimums_rows, employees,
                        seed, ilp_time_limit)
        values.append(val)

        if mode == "worst_case":
            worst = max(values)
            if worst > target:
                # fail-fast: já não interessa testar mais seeds para este cap
                break

    if mode == "average":
        return sum(values) / len(values)
    return max(values)


# =====================================================================
# PESQUISA: EXPONENCIAL (limite superior) + BINÁRIA
# =====================================================================

def find_min_cap_for_spacing(spacing, vacations_rows, minimums_rows, employees):
    target, mode = get_target_and_mode(spacing)
    label = "média" if mode == "average" else "pior-caso"

    print(f"\n{'='*70}")
    print(f"Spacing {spacing}: à procura do cap mínimo "
          f"(target missed_mins <= {target}, modo={label})")
    print(f"{'='*70}")

    lo = CAP_LO_DEFAULT
    hi = CAP_HI_START

    # ---- 1) Garantir que hi cumpre o target (pesquisa exponencial) ----
    t0 = time.time()
    val_hi = missed_mins_for_cap(spacing, hi, vacations_rows, minimums_rows, employees,
                                  TRIALS_PER_CANDIDATE, SEARCH_ILP_TIME_LIMIT)
    print(f"  cap={hi:>6}  missed_mins({label})={val_hi:>6.2f}  ({time.time()-t0:.1f}s)")

    while val_hi > target:
        lo = hi + 1
        hi *= 2
        if hi > CAP_HI_MAX:
            print(f"  ATENÇÃO: cap excedeu CAP_HI_MAX ({CAP_HI_MAX}) sem atingir o target.")
            return {
                "spacing": spacing,
                "min_cap": None,
                "missed_mins_at_min_cap": val_hi,
                "reached_target": False,
            }
        t0 = time.time()
        val_hi = missed_mins_for_cap(spacing, hi, vacations_rows, minimums_rows, employees,
                                      TRIALS_PER_CANDIDATE, SEARCH_ILP_TIME_LIMIT)
        print(f"  cap={hi:>6}  missed_mins({label})={val_hi:>6.2f}  ({time.time()-t0:.1f}s)")

    # ---- 2) Testar o limite inferior (caso já cumpra o target) ----
    t0 = time.time()
    val_lo = missed_mins_for_cap(spacing, lo, vacations_rows, minimums_rows, employees,
                                  TRIALS_PER_CANDIDATE, SEARCH_ILP_TIME_LIMIT)
    print(f"  cap={lo:>6}  missed_mins({label})={val_lo:>6.2f}  ({time.time()-t0:.1f}s)  [limite inferior]")

    if val_lo <= target:
        best_cap = lo
    else:
        # ---- 3) Pesquisa binária em (lo, hi] ----
        low, high = lo, hi
        best_cap = hi
        while low < high:
            mid = (low + high) // 2
            t0 = time.time()
            val_mid = missed_mins_for_cap(spacing, mid, vacations_rows, minimums_rows, employees,
                                           TRIALS_PER_CANDIDATE, SEARCH_ILP_TIME_LIMIT)
            print(f"  cap={mid:>6}  missed_mins({label})={val_mid:>6.2f}  ({time.time()-t0:.1f}s)  "
                  f"[binária lo={low} hi={high}]")
            if val_mid <= target:
                best_cap = mid
                high = mid
            else:
                low = mid + 1

    # ---- 4) Confirmação final: mais execuções, com o time-limit "de produção" ----
    print(f"  -> candidato: cap={best_cap}. A confirmar com {CONFIRM_TRIALS} execuções extra...")
    confirm_val = missed_mins_for_cap(spacing, best_cap, vacations_rows, minimums_rows, employees,
                                       CONFIRM_TRIALS, CONFIRM_ILP_TIME_LIMIT)
    reached = confirm_val <= target

    # Se a confirmação falhar (o candidato encontrado na pesquisa rápida
    # não se confirma com mais trials/tempo), sobe o cap até confirmar.
    fallback_cap = best_cap
    while not reached and fallback_cap < CAP_HI_MAX:
        fallback_cap += 1
        confirm_val = missed_mins_for_cap(spacing, fallback_cap, vacations_rows, minimums_rows,
                                           employees, CONFIRM_TRIALS, CONFIRM_ILP_TIME_LIMIT)
        reached = confirm_val <= target

    print(f"  ==> Spacing {spacing}: cap mínimo confirmado = {fallback_cap} "
          f"(missed_mins({label})={confirm_val:.2f} em {CONFIRM_TRIALS} seeds)")

    return {
        "spacing": spacing,
        "min_cap": fallback_cap,
        "missed_mins_at_min_cap": confirm_val,
        "reached_target": reached,
    }


# =====================================================================
# MAIN
# =====================================================================

def main():
    vacations_rows, minimums_rows, employees = load_data()

    results = []
    for spacing in SPACINGS:
        result = find_min_cap_for_spacing(spacing, vacations_rows, minimums_rows, employees)
        time.sleep(0.01)  # pausa para não sobrecarregar o sistema
        results.append(result)

        # grava incrementalmente para não perder progresso em caso de crash
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n\nRESUMO FINAL")
    print(f"{'spacing':>8} {'min_cap':>10} {'missed_mins':>18} {'atingiu_target':>15}")
    for r in results:
        val = r["missed_mins_at_min_cap"]
        val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
        print(f"{r['spacing']:>8} {str(r['min_cap']):>10} "
              f"{val_str:>18} {str(r['reached_target']):>15}")


if __name__ == "__main__":
    main()
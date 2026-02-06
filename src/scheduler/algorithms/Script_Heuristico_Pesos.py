import random
import time
import copy

def automatic_weight_search(
    vacations,
    minimuns,
    employees,
    maxTime,
    year,
    hours,
    work_blocks=None,
    max_seconds=600,
    early_stop_score=0,
    seed=None
):
    """
    Pesquisa automática de pesos contínuos em [0,1] para a heurística.
    Corre o máximo de combinações possíveis dentro do tempo dado.
    """

    if seed is not None:
        random.seed(seed)

    best_score = None
    best_weights = None
    best_assignment = None
    best_scheduler = None

    start_time = time.time()
    n_iter = 0

    print("\n" + "=" * 80)
    print("[AutoSearch] INÍCIO DA PESQUISA AUTOMÁTICA DE PESOS")
    print("=" * 80)

    while time.time() - start_time < max_seconds:

        n_iter += 1

        # -----------------------------
        # 1. Gerar pesos aleatórios contínuos
        # -----------------------------
        w = [random.random(), random.random(), random.random()]
        s = sum(w)
        W_TOTAL, W_WEEK, W_TEAMS = [x / s for x in w]

        print(f"\n[AutoSearch] Iteração {n_iter}")
        print(f"  Pesos → TOTAL={W_TOTAL:.4f}, WEEK={W_WEEK:.4f}, TEAMS={W_TEAMS:.4f}")

        # -----------------------------
        # 2. Executar heurística
        # -----------------------------
        scheduler = Heuristica(
            vacations,
            minimuns,
            employees,
            maxTime,
            year=year,
            store_hours=hours,
            work_blocks=work_blocks,
            W_TOTAL=W_TOTAL,
            W_WEEK=W_WEEK,
            W_TEAMS=W_TEAMS
        )

        scheduler.solve()

        # -----------------------------
        # 3. Avaliar solução
        # -----------------------------
        score = count_minimum_failures(scheduler)
        print(f"  Falhas nos mínimos: {score}")

        # -----------------------------
        # 4. Atualizar melhor solução
        # -----------------------------
        if best_score is None or score < best_score:
            best_score = score
            best_weights = (W_TOTAL, W_WEEK, W_TEAMS)
            best_assignment = copy.deepcopy(scheduler.assignment)
            best_scheduler = scheduler

            print("\033[92m"
                  f"  ★ NOVA MELHOR SOLUÇÃO (falhas={score})"
                  "\033[0m")

        # -----------------------------
        # 5. Early stop se perfeito
        # -----------------------------
        if best_score <= early_stop_score:
            print("[AutoSearch] Solução perfeita encontrada. A terminar.")
            break

    print("\n" + "=" * 80)
    print("[AutoSearch] RESULTADO FINAL")
    print(f"  Iterações: {n_iter}")
    print(f"  Melhor score: {best_score}")
    print(f"  Melhores pesos:")
    print(f"    W_TOTAL = {best_weights[0]:.4f}")
    print(f"    W_WEEK  = {best_weights[1]:.4f}")
    print(f"    W_TEAMS = {best_weights[2]:.4f}")
    print("=" * 80)

    if best_scheduler and best_assignment:
        best_scheduler.assignment = best_assignment
        best_scheduler.export_csv("heuristic_best_auto_weights.csv")
        return best_scheduler

    return None

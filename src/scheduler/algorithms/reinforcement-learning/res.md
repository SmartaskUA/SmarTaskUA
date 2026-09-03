## Fully Connected Graph:

- **Nodes:** added a `team` node type alongside `employee` and `day`. Team membership moved out of the employee features (one-hot in the baseline) into the graph topology.
- **Edges:** `employee ↔ team` (membership), `team ↔ day` (demand relation), and dense `employee ↔ day` — every employee connected to every day.
- **Scenario-size-invariant features** (the enabler for multi-scenario training — in the baseline, feature dims depended on `num_teams`):
  - employee: 3 dims (days worked, consecutive streak, id position) instead of `2 + num_teams + 1`;
  - day: `2·S + 2` — min/ideal gaps averaged over teams instead of flattened per (shift, team) (`2·S·T + 2` in the baseline);
  - team: `1 + 2·S` (relative team size + today's min/ideal gap per shift);
  - slot context for the heads: slot's team **embedding** + a 2-dim gap (min/ideal of the current slot only).
- **Training loop:** round-robin over a pool of two (`2TEAMS_12EMP`, `4TEAMS_24EMP`), one episode each, alternating; `8TEAMS_48EMP` is never trained on and used only for zero-shot evaluation.
- **Checkpoint selection:** eval every 20 episodes, best-of-5 sampled rollouts per pool scenario, metric = combined shortfall fraction.
- **Reward:** made scale-invariant so episodes from different scenarios are comparable — graded coverage term `200·(1 − shortfall/total_min)` instead of the all-or-nothing +200 bonus; ideal penalty charged on the **excess over the scenario's `ideal_floor`** (new env field) rather than the raw ideal gap; penalties normalized by problem size.
- **GNN:** added a team input projection and extended the `HeteroGraphConv` relation set to the new edge types; the two SAGE layers and the pointer/pass/critic heads are otherwise unchanged.
- **Trajectory collection / PPO:** mechanics unchanged (embeddings recomputed once per day, PPO re-embeds each minibatch's own snapshots via `dgl.batch`).

```
Checkpoint: episode 20, best metric = 0.0063

======================================================================
SMARTASK_2TEAMS_12EMP (trained) — 2 teams, 12 employees, total min demand 2086, ideal floor 0
======================================================================
Run  1 | Reward:   2377.6 | Shortfall:   12 | ideal_gap:  233 (excess= 233) | demand_skips:   12 | avg days=223
Run  2 | Reward:   2398.0 | Shortfall:   10 | ideal_gap:  225 (excess= 225) | demand_skips:   10 | avg days=223
Run  3 | Reward:   2361.0 | Shortfall:   17 | ideal_gap:  226 (excess= 226) | demand_skips:   17 | avg days=223
Run  4 | Reward:   2386.5 | Shortfall:   13 | ideal_gap:  222 (excess= 222) | demand_skips:   13 | avg days=223
Run  5 | Reward:   2364.8 | Shortfall:   15 | ideal_gap:  231 (excess= 231) | demand_skips:   15 | avg days=223
Run  6 | Reward:   2371.2 | Shortfall:   13 | ideal_gap:  234 (excess= 234) | demand_skips:   13 | avg days=223
Run  7 | Reward:   2377.6 | Shortfall:   13 | ideal_gap:  229 (excess= 229) | demand_skips:   13 | avg days=223
Run  8 | Reward:   2352.1 | Shortfall:   18 | ideal_gap:  229 (excess= 229) | demand_skips:   18 | avg days=223
Run  9 | Reward:   2376.3 | Shortfall:   11 | ideal_gap:  238 (excess= 238) | demand_skips:   11 | avg days=223
Run 10 | Reward:   2387.7 | Shortfall:   10 | ideal_gap:  233 (excess= 233) | demand_skips:   10 | avg days=223
Run 11 | Reward:   2376.3 | Shortfall:   14 | ideal_gap:  226 (excess= 226) | demand_skips:   14 | avg days=223
Run 12 | Reward:   2362.3 | Shortfall:   16 | ideal_gap:  229 (excess= 229) | demand_skips:   16 | avg days=223
Run 13 | Reward:   2338.0 | Shortfall:   18 | ideal_gap:  240 (excess= 240) | demand_skips:   18 | avg days=223
Run 14 | Reward:   2378.9 | Shortfall:   13 | ideal_gap:  228 (excess= 228) | demand_skips:   13 | avg days=223
Run 15 | Reward:   2386.6 | Shortfall:   14 | ideal_gap:  218 (excess= 218) | demand_skips:   14 | avg days=223
Run 16 | Reward:   2382.7 | Shortfall:   12 | ideal_gap:  229 (excess= 229) | demand_skips:   12 | avg days=223
Run 17 | Reward:   2343.2 | Shortfall:   19 | ideal_gap:  232 (excess= 232) | demand_skips:   19 | avg days=223
Run 18 | Reward:   2336.7 | Shortfall:   18 | ideal_gap:  241 (excess= 241) | demand_skips:   18 | avg days=223
Run 19 | Reward:   2377.6 | Shortfall:   12 | ideal_gap:  233 (excess= 233) | demand_skips:   12 | avg days=223
Run 20 | Reward:   2390.3 | Shortfall:   11 | ideal_gap:  227 (excess= 227) | demand_skips:   11 | avg days=223

BEST: Run 2 | Shortfall: 10 (99.52% coverage) | Ideal gap: 225 (excess=225)
Days worked/employee: avg=223, min=223, max=223
Day 341: M-A=1, T-A=2
Day 358: M-A=2, T-A=1
Day 361: M-A=1, M-B=1, T-A=1, T-B=1

Best schedule written to best_schedule_SMARTASK_2TEAMS_12EMP_multiteam.csv

======================================================================
SMARTASK_4TEAMS_24EMP (trained) — 4 teams, 24 employees, total min demand 2920, ideal floor 488
======================================================================
Run  1 | Reward:   5293.0 | Shortfall:    4 | ideal_gap:  697 (excess= 209) | demand_skips:    4 | avg days=223
Run  2 | Reward:   5289.4 | Shortfall:    2 | ideal_gap:  709 (excess= 221) | demand_skips:    2 | avg days=223
Run  3 | Reward:   5292.0 | Shortfall:    6 | ideal_gap:  689 (excess= 201) | demand_skips:    6 | avg days=223
Run  4 | Reward:   5294.6 | Shortfall:    3 | ideal_gap:  700 (excess= 212) | demand_skips:    3 | avg days=223
Run  5 | Reward:   5280.4 | Shortfall:    4 | ideal_gap:  708 (excess= 220) | demand_skips:    4 | avg days=223
Run  6 | Reward:   5274.2 | Shortfall:    5 | ideal_gap:  709 (excess= 221) | demand_skips:    5 | avg days=223
Run  7 | Reward:   5276.5 | Shortfall:    5 | ideal_gap:  707 (excess= 219) | demand_skips:    5 | avg days=223
Run  8 | Reward:   5290.0 | Shortfall:    3 | ideal_gap:  704 (excess= 216) | demand_skips:    3 | avg days=223
Run  9 | Reward:   5304.2 | Shortfall:    2 | ideal_gap:  696 (excess= 208) | demand_skips:    2 | avg days=223
Run 10 | Reward:   5287.9 | Shortfall:    5 | ideal_gap:  697 (excess= 209) | demand_skips:    5 | avg days=223
Run 11 | Reward:   5276.3 | Shortfall:    3 | ideal_gap:  716 (excess= 228) | demand_skips:    3 | avg days=223
Run 12 | Reward:   5289.4 | Shortfall:    2 | ideal_gap:  709 (excess= 221) | demand_skips:    2 | avg days=223
Run 13 | Reward:   5300.9 | Shortfall:    4 | ideal_gap:  690 (excess= 202) | demand_skips:    4 | avg days=223
Run 14 | Reward:   5288.0 | Shortfall:    7 | ideal_gap:  688 (excess= 200) | demand_skips:    7 | avg days=223
Run 15 | Reward:   5291.7 | Shortfall:    2 | ideal_gap:  707 (excess= 219) | demand_skips:    2 | avg days=223
Run 16 | Reward:   5295.7 | Shortfall:    3 | ideal_gap:  699 (excess= 211) | demand_skips:    3 | avg days=223
Run 17 | Reward:   5305.9 | Shortfall:    1 | ideal_gap:  699 (excess= 211) | demand_skips:    1 | avg days=223
Run 18 | Reward:   5259.1 | Shortfall:   10 | ideal_gap:  700 (excess= 212) | demand_skips:   10 | avg days=223
Run 19 | Reward:   5268.1 | Shortfall:    8 | ideal_gap:  701 (excess= 213) | demand_skips:    8 | avg days=223
Run 20 | Reward:   5284.1 | Shortfall:    8 | ideal_gap:  687 (excess= 199) | demand_skips:    8 | avg days=223

BEST: Run 17 | Shortfall: 1 (99.97% coverage) | Ideal gap: 699 (excess=211)
Days worked/employee: avg=223, min=223, max=223
Day 361: T-A=1

Best schedule written to best_schedule_SMARTASK_4TEAMS_24EMP_multiteam.csv

======================================================================
SMARTASK_8TEAMS_48EMP (ZERO-SHOT (never trained on)) — 8 teams, 48 employees, total min demand 5840, ideal floor 976
======================================================================
Run  1 | Reward:  10496.0 | Shortfall:    6 | ideal_gap: 1365 (excess= 389) | demand_skips:    6 | avg days=223
Run  2 | Reward:  10490.0 | Shortfall:    7 | ideal_gap: 1366 (excess= 390) | demand_skips:    7 | avg days=223
Run  3 | Reward:  10485.2 | Shortfall:    1 | ideal_gap: 1402 (excess= 426) | demand_skips:    1 | avg days=223
Run  4 | Reward:  10502.2 | Shortfall:    4 | ideal_gap: 1369 (excess= 393) | demand_skips:    4 | avg days=223
Run  5 | Reward:  10501.2 | Shortfall:    4 | ideal_gap: 1370 (excess= 394) | demand_skips:    4 | avg days=223
Run  6 | Reward:  10496.8 | Shortfall:    7 | ideal_gap: 1359 (excess= 383) | demand_skips:    7 | avg days=223
Run  7 | Reward:  10507.6 | Shortfall:    6 | ideal_gap: 1353 (excess= 377) | demand_skips:    6 | avg days=223
Run  8 | Reward:  10489.2 | Shortfall:    6 | ideal_gap: 1372 (excess= 396) | demand_skips:    6 | avg days=223
Run  9 | Reward:  10514.8 | Shortfall:    4 | ideal_gap: 1356 (excess= 380) | demand_skips:    4 | avg days=223
Run 10 | Reward:  10504.9 | Shortfall:    5 | ideal_gap: 1361 (excess= 385) | demand_skips:    5 | avg days=223
Run 11 | Reward:  10544.3 | Shortfall:    2 | ideal_gap: 1336 (excess= 360) | demand_skips:    2 | avg days=223
Run 12 | Reward:  10524.1 | Shortfall:    1 | ideal_gap: 1362 (excess= 386) | demand_skips:    1 | avg days=223
Run 13 | Reward:  10484.8 | Shortfall:    9 | ideal_gap: 1361 (excess= 385) | demand_skips:    9 | avg days=223
Run 14 | Reward:  10515.2 | Shortfall:    2 | ideal_gap: 1366 (excess= 390) | demand_skips:    2 | avg days=223
Run 15 | Reward:  10506.5 | Shortfall:    7 | ideal_gap: 1349 (excess= 373) | demand_skips:    7 | avg days=223
Run 16 | Reward:  10516.6 | Shortfall:    5 | ideal_gap: 1349 (excess= 373) | demand_skips:    5 | avg days=223
Run 17 | Reward:  10484.4 | Shortfall:   11 | ideal_gap: 1351 (excess= 375) | demand_skips:   11 | avg days=223
Run 18 | Reward:  10504.3 | Shortfall:    3 | ideal_gap: 1372 (excess= 396) | demand_skips:    3 | avg days=223
Run 19 | Reward:  10514.0 | Shortfall:    3 | ideal_gap: 1362 (excess= 386) | demand_skips:    3 | avg days=223
Run 20 | Reward:  10501.8 | Shortfall:    6 | ideal_gap: 1359 (excess= 383) | demand_skips:    6 | avg days=223

BEST: Run 12 | Shortfall: 1 (99.98% coverage) | Ideal gap: 1362 (excess=386)
Days worked/employee: avg=223, min=223, max=223
Day 361: T-E=1

Best schedule written to best_schedule_SMARTASK_8TEAMS_48EMP_multiteam.csv
```

## Employee <-> Day only when assignment exists:

- **Edges:** dense `employee ↔ day` replaced by sparse per-shift **assignment** relations `works_{shift}` / `worked_by_{shift}` — an edge exists only where the employee is actually assigned that shift on that day.
- **Dynamic topology:** the graph is no longer static per scenario; it's rebuilt (`build_graph(env)`) at every day boundary as assignments accumulate, rather than one fixed graph with refreshed features.
- **Trajectory collection:** stores one heterograph per day snapshot (topology + features) instead of per-snapshot feature tensors over a shared graph.
- **PPO update:** to re-embed a minibatch efficiently, the few day-snapshots it touches are merged into one big graph of disconnected components (`dgl.batch`), so a single GNN forward pass covers them all. Since every snapshot now has its own edge set, it is the stored snapshot graphs themselves that get merged — there is no longer one shared graph that can simply be replicated with each snapshot's features loaded in. Splitting the merged output back into per-snapshot embeddings (`view(n, E, -1)`) still works, because assignments add edges but never change the number of nodes.

```
Checkpoint: episode 120, best metric = 0.0060

======================================================================
SMARTASK_2TEAMS_12EMP (trained) — 2 teams, 12 employees, total min demand 2086, ideal floor 0
======================================================================
Run  1 | Reward:   2153.6 | Shortfall:   15 | ideal_gap:  233 (excess= 233) | demand_skips:   15 | avg days=219
Run  2 | Reward:   2117.5 | Shortfall:   10 | ideal_gap:  235 (excess= 235) | demand_skips:   10 | avg days=217
Run  3 | Reward:   2152.4 | Shortfall:   16 | ideal_gap:  230 (excess= 230) | demand_skips:   16 | avg days=219
Run  4 | Reward:   2082.7 | Shortfall:   14 | ideal_gap:  237 (excess= 237) | demand_skips:   14 | avg days=217
Run  5 | Reward:   2265.1 | Shortfall:   14 | ideal_gap:  236 (excess= 236) | demand_skips:   14 | avg days=221
Run  6 | Reward:   2149.7 | Shortfall:   13 | ideal_gap:  244 (excess= 244) | demand_skips:   13 | avg days=219
Run  7 | Reward:   2079.9 | Shortfall:   13 | ideal_gap:  237 (excess= 237) | demand_skips:   13 | avg days=217
Run  8 | Reward:   2208.9 | Shortfall:   17 | ideal_gap:  228 (excess= 228) | demand_skips:   17 | avg days=220
Run  9 | Reward:   2075.2 | Shortfall:   14 | ideal_gap:  249 (excess= 249) | demand_skips:   14 | avg days=217
Run 10 | Reward:   2116.5 | Shortfall:   10 | ideal_gap:  245 (excess= 245) | demand_skips:   10 | avg days=218
Run 11 | Reward:   2136.0 | Shortfall:   12 | ideal_gap:  231 (excess= 231) | demand_skips:   12 | avg days=218
Run 12 | Reward:   2137.8 | Shortfall:   14 | ideal_gap:  237 (excess= 237) | demand_skips:   14 | avg days=218
Run 13 | Reward:   2142.3 | Shortfall:   17 | ideal_gap:  240 (excess= 240) | demand_skips:   17 | avg days=219
Run 14 | Reward:   2201.4 | Shortfall:   10 | ideal_gap:  234 (excess= 234) | demand_skips:   10 | avg days=219
Run 15 | Reward:   2178.1 | Shortfall:   13 | ideal_gap:  228 (excess= 228) | demand_skips:   13 | avg days=219
Run 16 | Reward:   2161.2 | Shortfall:   13 | ideal_gap:  235 (excess= 235) | demand_skips:   13 | avg days=219
Run 17 | Reward:   2152.1 | Shortfall:   13 | ideal_gap:  236 (excess= 236) | demand_skips:   13 | avg days=218
Run 18 | Reward:   2109.8 | Shortfall:   19 | ideal_gap:  239 (excess= 239) | demand_skips:   19 | avg days=218
Run 19 | Reward:   2135.0 | Shortfall:   14 | ideal_gap:  230 (excess= 230) | demand_skips:   14 | avg days=218
Run 20 | Reward:   2167.5 | Shortfall:   11 | ideal_gap:  235 (excess= 235) | demand_skips:   11 | avg days=218

BEST: Run 14 | Shortfall: 10 (99.52% coverage) | Ideal gap: 234 (excess=234)
Days worked/employee: avg=219, min=203, max=223
Day 347: T-A=1
Day 354: T-A=1, T-B=1
Day 358: M-A=2, T-A=1, T-B=1
Day 361: M-A=1, T-A=1, T-B=1

Best schedule written to best_schedule_SMARTASK_2TEAMS_12EMP_multiteam_v2.csv

======================================================================
SMARTASK_4TEAMS_24EMP (trained) — 4 teams, 24 employees, total min demand 2920, ideal floor 488
======================================================================
Run  1 | Reward:   5344.2 | Shortfall:    2 | ideal_gap:  661 (excess= 173) | demand_skips:    2 | avg days=223
Run  2 | Reward:   5311.7 | Shortfall:    3 | ideal_gap:  685 (excess= 197) | demand_skips:    3 | avg days=223
Run  3 | Reward:   5305.3 | Shortfall:    9 | ideal_gap:  664 (excess= 176) | demand_skips:    9 | avg days=223
Run  4 | Reward:   5306.5 | Shortfall:    2 | ideal_gap:  694 (excess= 206) | demand_skips:    2 | avg days=223
Run  5 | Reward:   5302.2 | Shortfall:    6 | ideal_gap:  680 (excess= 192) | demand_skips:    6 | avg days=223
Run  6 | Reward:   5319.2 | Shortfall:    4 | ideal_gap:  674 (excess= 186) | demand_skips:    4 | avg days=223
Run  7 | Reward:   5309.6 | Shortfall:    5 | ideal_gap:  678 (excess= 190) | demand_skips:    5 | avg days=223
Run  8 | Reward:   5326.6 | Shortfall:    3 | ideal_gap:  672 (excess= 184) | demand_skips:    3 | avg days=223
Run  9 | Reward:   5355.0 | Shortfall:    1 | ideal_gap:  656 (excess= 168) | demand_skips:    1 | avg days=223
Run 10 | Reward:   5328.2 | Shortfall:    2 | ideal_gap:  675 (excess= 187) | demand_skips:    2 | avg days=223
Run 11 | Reward:   5327.7 | Shortfall:    3 | ideal_gap:  671 (excess= 183) | demand_skips:    3 | avg days=223
Run 12 | Reward:   5327.7 | Shortfall:    3 | ideal_gap:  671 (excess= 183) | demand_skips:    3 | avg days=223
Run 13 | Reward:   5334.7 | Shortfall:    5 | ideal_gap:  656 (excess= 168) | demand_skips:    5 | avg days=223
Run 14 | Reward:   5312.7 | Shortfall:    8 | ideal_gap:  662 (excess= 174) | demand_skips:    8 | avg days=223
Run 15 | Reward:   5311.9 | Shortfall:    5 | ideal_gap:  676 (excess= 188) | demand_skips:    5 | avg days=223
Run 16 | Reward:   5332.8 | Shortfall:    2 | ideal_gap:  671 (excess= 183) | demand_skips:    2 | avg days=223
Run 17 | Reward:   5332.1 | Shortfall:    1 | ideal_gap:  676 (excess= 188) | demand_skips:    1 | avg days=223
Run 18 | Reward:   5302.5 | Shortfall:   10 | ideal_gap:  662 (excess= 174) | demand_skips:   10 | avg days=223
Run 19 | Reward:   5284.2 | Shortfall:   10 | ideal_gap:  678 (excess= 190) | demand_skips:   10 | avg days=223
Run 20 | Reward:   5308.1 | Shortfall:    8 | ideal_gap:  666 (excess= 178) | demand_skips:    8 | avg days=223

BEST: Run 9 | Shortfall: 1 (99.97% coverage) | Ideal gap: 656 (excess=168)
Days worked/employee: avg=223, min=223, max=223
Day 361: T-D=1

Best schedule written to best_schedule_SMARTASK_4TEAMS_24EMP_multiteam_v2.csv

======================================================================
SMARTASK_8TEAMS_48EMP (ZERO-SHOT (never trained on)) — 8 teams, 48 employees, total min demand 5840, ideal floor 976
======================================================================
Run  1 | Reward:  10552.3 | Shortfall:    6 | ideal_gap: 1307 (excess= 331) | demand_skips:    6 | avg days=223
Run  2 | Reward:  10550.2 | Shortfall:    7 | ideal_gap: 1304 (excess= 328) | demand_skips:    7 | avg days=223
Run  3 | Reward:  10540.0 | Shortfall:    4 | ideal_gap: 1330 (excess= 354) | demand_skips:    4 | avg days=223
Run  4 | Reward:  10527.7 | Shortfall:    8 | ideal_gap: 1322 (excess= 346) | demand_skips:    8 | avg days=223
Run  5 | Reward:  10559.8 | Shortfall:    2 | ideal_gap: 1320 (excess= 344) | demand_skips:    2 | avg days=223
Run  6 | Reward:  10568.2 | Shortfall:    4 | ideal_gap: 1301 (excess= 325) | demand_skips:    4 | avg days=223
Run  7 | Reward:  10558.3 | Shortfall:    5 | ideal_gap: 1306 (excess= 330) | demand_skips:    5 | avg days=223
Run  8 | Reward:  10563.5 | Shortfall:    3 | ideal_gap: 1311 (excess= 335) | demand_skips:    3 | avg days=223
Run  9 | Reward:  10569.7 | Shortfall:    1 | ideal_gap: 1315 (excess= 339) | demand_skips:    1 | avg days=223
Run 10 | Reward:  10569.0 | Shortfall:    5 | ideal_gap: 1295 (excess= 319) | demand_skips:    5 | avg days=223
Run 11 | Reward:  10577.9 | Shortfall:    4 | ideal_gap: 1291 (excess= 315) | demand_skips:    4 | avg days=223
Run 12 | Reward:  10589.1 | Shortfall:    1 | ideal_gap: 1295 (excess= 319) | demand_skips:    1 | avg days=223
Run 13 | Reward:  10539.8 | Shortfall:   11 | ideal_gap: 1294 (excess= 318) | demand_skips:   11 | avg days=223
Run 14 | Reward:  10586.2 | Shortfall:    1 | ideal_gap: 1298 (excess= 322) | demand_skips:    1 | avg days=223
Run 15 | Reward:  10551.2 | Shortfall:    7 | ideal_gap: 1303 (excess= 327) | demand_skips:    7 | avg days=223
Run 16 | Reward:  10563.2 | Shortfall:    5 | ideal_gap: 1301 (excess= 325) | demand_skips:    5 | avg days=223
Run 17 | Reward:  10547.5 | Shortfall:    6 | ideal_gap: 1312 (excess= 336) | demand_skips:    6 | avg days=223
Run 18 | Reward:  10572.5 | Shortfall:    2 | ideal_gap: 1307 (excess= 331) | demand_skips:    2 | avg days=223
Run 19 | Reward:  10564.3 | Shortfall:    4 | ideal_gap: 1305 (excess= 329) | demand_skips:    4 | avg days=223
Run 20 | Reward:  10568.2 | Shortfall:    4 | ideal_gap: 1301 (excess= 325) | demand_skips:    4 | avg days=223

BEST: Run 12 | Shortfall: 1 (99.98% coverage) | Ideal gap: 1295 (excess=319)
Days worked/employee: avg=223, min=223, max=223
Day 358: T-A=1

Best schedule written to best_schedule_SMARTASK_8TEAMS_48EMP_multiteam_v2.csv

```

## No Employee<->Day connection:

- **Edges:** the per-shift `works_*` / `worked_by_*` assignment relations removed — no `employee ↔ day` edges at all. Only the 4 static relations remain (`employee ↔ team`, `team ↔ day`); emp↔day information flows through team nodes in 2 hops.
- **Static topology again:** with no assignment edges the graph is fixed per scenario — one cached graph per env (`get_graph`), refreshed once per day via `update_graph_features` instead of rebuilt at every day boundary.
- **Trajectory collection:** back to storing per-snapshot feature tensors (employee/day/team) instead of one heterograph per snapshot.
- **PPO update:** back to the v1 fast path — replicate the single static graph (`dgl.batch([graph] * n)`) and overwrite each component's node features — instead of batching per-snapshot graphs.
- **GNN:** `HeteroGraphConv` relation set reduced to the 4 static relations; architecture otherwise unchanged.

```
Checkpoint: step 300, best metric = (0.006643113253391822, 0.20347784972221855)

======================================================================
SMARTASK_2TEAMS_12EMP (trained) — 2 teams, 12 employees, total min demand 2086, ideal floor 0
======================================================================
Run  1 | Reward:   2029.8 | Shortfall:   13 | ideal_gap:  230 (excess= 230) | demand_skips:   13 | avg days=216
Run  2 | Reward:   1995.2 | Shortfall:   10 | ideal_gap:  229 (excess= 229) | demand_skips:   10 | avg days=215
Run  3 | Reward:   1984.6 | Shortfall:   17 | ideal_gap:  231 (excess= 231) | demand_skips:   17 | avg days=215
Run  4 | Reward:   1983.9 | Shortfall:   14 | ideal_gap:  225 (excess= 225) | demand_skips:   14 | avg days=215
Run  5 | Reward:   2068.1 | Shortfall:   14 | ideal_gap:  230 (excess= 230) | demand_skips:   14 | avg days=217
Run  6 | Reward:   1999.9 | Shortfall:   13 | ideal_gap:  238 (excess= 238) | demand_skips:   13 | avg days=215
Run  7 | Reward:   1929.0 | Shortfall:   14 | ideal_gap:  231 (excess= 231) | demand_skips:   14 | avg days=214
Run  8 | Reward:   2057.7 | Shortfall:   16 | ideal_gap:  224 (excess= 224) | demand_skips:   16 | avg days=216
Run  9 | Reward:   1951.6 | Shortfall:   14 | ideal_gap:  241 (excess= 241) | demand_skips:   14 | avg days=214
Run 10 | Reward:   1990.2 | Shortfall:   10 | ideal_gap:  236 (excess= 236) | demand_skips:   10 | avg days=215
Run 11 | Reward:   1982.7 | Shortfall:   15 | ideal_gap:  225 (excess= 225) | demand_skips:   15 | avg days=215
Run 12 | Reward:   2011.6 | Shortfall:   14 | ideal_gap:  228 (excess= 228) | demand_skips:   14 | avg days=215
Run 13 | Reward:   1970.6 | Shortfall:   18 | ideal_gap:  241 (excess= 241) | demand_skips:   18 | avg days=215
Run 14 | Reward:   2055.6 | Shortfall:   12 | ideal_gap:  220 (excess= 220) | demand_skips:   12 | avg days=216
Run 15 | Reward:   2012.7 | Shortfall:   14 | ideal_gap:  224 (excess= 224) | demand_skips:   14 | avg days=215
Run 16 | Reward:   1995.8 | Shortfall:   13 | ideal_gap:  232 (excess= 232) | demand_skips:   13 | avg days=215
Run 17 | Reward:   1907.2 | Shortfall:   19 | ideal_gap:  225 (excess= 225) | demand_skips:   19 | avg days=214
Run 18 | Reward:   1944.4 | Shortfall:   19 | ideal_gap:  236 (excess= 236) | demand_skips:   19 | avg days=215
Run 19 | Reward:   1954.7 | Shortfall:   11 | ideal_gap:  229 (excess= 229) | demand_skips:   11 | avg days=214
Run 20 | Reward:   2039.8 | Shortfall:   11 | ideal_gap:  224 (excess= 224) | demand_skips:   11 | avg days=216

MEAN over 20 runs | Shortfall: 14.1 | Ideal excess: 229.9
BEST: Run 2 | Shortfall: 10 (99.52% coverage) | Ideal gap: 229 (excess=229)
Days worked/employee: avg=215, min=190, max=223
Day 334: T-A=1
Day 341: M-A=1, T-A=2
Day 354: M-A=1
Day 358: M-A=2, T-A=1
Day 361: M-B=1, T-A=1

Best schedule written to best_schedule_SMARTASK_2TEAMS_12EMP_multiteam_v4.csv

======================================================================
SMARTASK_4TEAMS_24EMP (trained) — 4 teams, 24 employees, total min demand 2920, ideal floor 488
======================================================================
Run  1 | Reward:   5349.4 | Shortfall:    3 | ideal_gap:  652 (excess= 164) | demand_skips:    3 | avg days=223
Run  2 | Reward:   5334.6 | Shortfall:    3 | ideal_gap:  665 (excess= 177) | demand_skips:    3 | avg days=223
Run  3 | Reward:   5329.8 | Shortfall:    8 | ideal_gap:  647 (excess= 159) | demand_skips:    8 | avg days=223
Run  4 | Reward:   5329.4 | Shortfall:    2 | ideal_gap:  674 (excess= 186) | demand_skips:    2 | avg days=223
Run  5 | Reward:   5324.9 | Shortfall:    4 | ideal_gap:  669 (excess= 181) | demand_skips:    4 | avg days=223
Run  6 | Reward:   5322.2 | Shortfall:    5 | ideal_gap:  667 (excess= 179) | demand_skips:    5 | avg days=223
Run  7 | Reward:   5325.6 | Shortfall:    5 | ideal_gap:  664 (excess= 176) | demand_skips:    5 | avg days=223
Run  8 | Reward:   5348.8 | Shortfall:    2 | ideal_gap:  657 (excess= 169) | demand_skips:    2 | avg days=223
Run  9 | Reward:   5365.3 | Shortfall:    1 | ideal_gap:  647 (excess= 159) | demand_skips:    1 | avg days=223
Run 10 | Reward:   5329.0 | Shortfall:    5 | ideal_gap:  661 (excess= 173) | demand_skips:    5 | avg days=223
Run 11 | Reward:   5323.2 | Shortfall:    3 | ideal_gap:  675 (excess= 187) | demand_skips:    3 | avg days=223
Run 12 | Reward:   5339.6 | Shortfall:    2 | ideal_gap:  665 (excess= 177) | demand_skips:    2 | avg days=223
Run 13 | Reward:   5360.9 | Shortfall:    3 | ideal_gap:  642 (excess= 154) | demand_skips:    3 | avg days=223
Run 14 | Reward:   5318.9 | Shortfall:    7 | ideal_gap:  661 (excess= 173) | demand_skips:    7 | avg days=223
Run 15 | Reward:   5343.1 | Shortfall:    2 | ideal_gap:  662 (excess= 174) | demand_skips:    2 | avg days=223
Run 16 | Reward:   5337.4 | Shortfall:    2 | ideal_gap:  667 (excess= 179) | demand_skips:    2 | avg days=223
Run 17 | Reward:   5344.7 | Shortfall:    1 | ideal_gap:  665 (excess= 177) | demand_skips:    1 | avg days=223
Run 18 | Reward:   5306.0 | Shortfall:   10 | ideal_gap:  659 (excess= 171) | demand_skips:   10 | avg days=223
Run 19 | Reward:   5316.1 | Shortfall:    8 | ideal_gap:  659 (excess= 171) | demand_skips:    8 | avg days=223
Run 20 | Reward:   5332.1 | Shortfall:    8 | ideal_gap:  645 (excess= 157) | demand_skips:    8 | avg days=223

MEAN over 20 runs | Shortfall: 4.2 | Ideal excess: 172.2
BEST: Run 9 | Shortfall: 1 (99.97% coverage) | Ideal gap: 647 (excess=159)
Days worked/employee: avg=223, min=223, max=223
Day 354: T-D=1

Best schedule written to best_schedule_SMARTASK_4TEAMS_24EMP_multiteam_v4.csv

======================================================================
SMARTASK_8TEAMS_48EMP (ZERO-SHOT (never trained on)) — 8 teams, 48 employees, total min demand 5840, ideal floor 976
======================================================================
Run  1 | Reward:  10576.6 | Shortfall:    6 | ideal_gap: 1282 (excess= 306) | demand_skips:    6 | avg days=223
Run  2 | Reward:  10566.7 | Shortfall:    7 | ideal_gap: 1287 (excess= 311) | demand_skips:    7 | avg days=223
Run  3 | Reward:  10567.4 | Shortfall:    3 | ideal_gap: 1307 (excess= 331) | demand_skips:    3 | avg days=223
Run  4 | Reward:  10575.0 | Shortfall:    4 | ideal_gap: 1294 (excess= 318) | demand_skips:    4 | avg days=223
Run  5 | Reward:  10579.9 | Shortfall:    4 | ideal_gap: 1289 (excess= 313) | demand_skips:    4 | avg days=223
Run  6 | Reward:  10569.0 | Shortfall:    5 | ideal_gap: 1295 (excess= 319) | demand_skips:    5 | avg days=223
Run  7 | Reward:  10573.1 | Shortfall:    4 | ideal_gap: 1296 (excess= 320) | demand_skips:    4 | avg days=223
Run  8 | Reward:  10574.0 | Shortfall:    4 | ideal_gap: 1295 (excess= 319) | demand_skips:    4 | avg days=223
Run  9 | Reward:  10587.8 | Shortfall:    3 | ideal_gap: 1286 (excess= 310) | demand_skips:    3 | avg days=223
Run 10 | Reward:  10568.6 | Shortfall:    7 | ideal_gap: 1285 (excess= 309) | demand_skips:    7 | avg days=223
Run 11 | Reward:  10606.3 | Shortfall:    3 | ideal_gap: 1267 (excess= 291) | demand_skips:    3 | avg days=223
Run 12 | Reward:  10593.8 | Shortfall:    2 | ideal_gap: 1285 (excess= 309) | demand_skips:    2 | avg days=223
Run 13 | Reward:  10556.6 | Shortfall:    9 | ideal_gap: 1287 (excess= 311) | demand_skips:    9 | avg days=223
Run 14 | Reward:  10600.8 | Shortfall:    1 | ideal_gap: 1283 (excess= 307) | demand_skips:    1 | avg days=223
Run 15 | Reward:  10586.7 | Shortfall:    4 | ideal_gap: 1282 (excess= 306) | demand_skips:    4 | avg days=223
Run 16 | Reward:  10590.7 | Shortfall:    3 | ideal_gap: 1283 (excess= 307) | demand_skips:    3 | avg days=223
Run 17 | Reward:  10561.5 | Shortfall:    9 | ideal_gap: 1282 (excess= 306) | demand_skips:    9 | avg days=223
Run 18 | Reward:  10583.9 | Shortfall:    3 | ideal_gap: 1290 (excess= 314) | demand_skips:    3 | avg days=223
Run 19 | Reward:  10574.2 | Shortfall:    3 | ideal_gap: 1300 (excess= 324) | demand_skips:    3 | avg days=223
Run 20 | Reward:  10574.7 | Shortfall:    6 | ideal_gap: 1284 (excess= 308) | demand_skips:    6 | avg days=223

MEAN over 20 runs | Shortfall: 4.5 | Ideal excess: 311.9
BEST: Run 14 | Shortfall: 1 (99.98% coverage) | Ideal gap: 1283 (excess=307)
Days worked/employee: avg=223, min=223, max=223
Day 361: T-E=1

Best schedule written to best_schedule_SMARTASK_8TEAMS_48EMP_multiteam_v4.csv
```


## Demand Node Graph:

- **Nodes:** `day` nodes replaced by **demand nodes** — one node per slot-queue entry, i.e. one headcount unit of (day, shift, team, kind). The graph now mirrors the decision sequence itself: one node per decision the policy will make.
- **Edges (all static):** `employee ↔ team` kept; each demand node `belongs_to` / `has_demand` its team; new **`qualified` / `qualified_by` employee↔demand edges** wherever the employee could in principle cover that slot (team membership + not on vacation), precomputed once per scenario.
- **Demand-node features (`S + 7` dims):** each demand node describes its own slot — what it is, and what has happened to it so far.
  - *Static (set once per scenario):* shift one-hot (`S` dims); kind (0 = min demand, must fill; 1 = capacity); day position in the year; special-day flag.
  - *Dynamic (refreshed at every day boundary):* **filled** flag (an employee was assigned to this slot — tracked by the new `env.slot_filled` array) and **already-passed** flag (the queue pointer moved past it).
- **GNN impact:** `day_proj` → `demand_proj`; conv relation set = the 6 static relations. The heads' slot context now uses the **embedding of the exact demand node being decided** (`demand_ids` = slot-queue index) instead of the current day's embedding, so the policy sees a slot-specific neighborhood — its qualified employees and team — rather than a day-level average. Head dimensions unchanged.

```
Checkpoint: iteration 30, best metric = (0.00660200422910729, 0.17709439314937153)

======================================================================
2teams (trained) — 2 teams, 12 employees, total min demand 2086, ideal floor 0
======================================================================
Run  1 | Reward:   2377.4 | Shortfall:   11 | ideal_gap:  234 (excess= 234) | demand_skips:   11 | avg days=223
Run  2 | Reward:   2390.3 | Shortfall:   11 | ideal_gap:  227 (excess= 227) | demand_skips:   11 | avg days=223
Run  3 | Reward:   2370.0 | Shortfall:   16 | ideal_gap:  223 (excess= 223) | demand_skips:   16 | avg days=223
Run  4 | Reward:   2363.2 | Shortfall:   13 | ideal_gap:  231 (excess= 231) | demand_skips:   13 | avg days=223
Run  5 | Reward:   2350.8 | Shortfall:   16 | ideal_gap:  238 (excess= 238) | demand_skips:   16 | avg days=223
Run  6 | Reward:   2367.3 | Shortfall:   11 | ideal_gap:  245 (excess= 245) | demand_skips:   11 | avg days=223
Run  7 | Reward:   2374.9 | Shortfall:   10 | ideal_gap:  240 (excess= 240) | demand_skips:   10 | avg days=223
Run  8 | Reward:   2354.6 | Shortfall:   17 | ideal_gap:  231 (excess= 231) | demand_skips:   17 | avg days=223
Run  9 | Reward:   2394.2 | Shortfall:   11 | ideal_gap:  224 (excess= 224) | demand_skips:   11 | avg days=223
Run 10 | Reward:   2396.7 | Shortfall:   10 | ideal_gap:  226 (excess= 226) | demand_skips:   10 | avg days=223
Run 11 | Reward:   2319.4 | Shortfall:   16 | ideal_gap:  241 (excess= 241) | demand_skips:   16 | avg days=222
Run 12 | Reward:   2367.1 | Shortfall:   14 | ideal_gap:  224 (excess= 224) | demand_skips:   14 | avg days=223
Run 13 | Reward:   2345.5 | Shortfall:   17 | ideal_gap:  232 (excess= 232) | demand_skips:   17 | avg days=223
Run 14 | Reward:   2353.0 | Shortfall:   16 | ideal_gap:  227 (excess= 227) | demand_skips:   16 | avg days=223
Run 15 | Reward:   2364.4 | Shortfall:   11 | ideal_gap:  238 (excess= 238) | demand_skips:   11 | avg days=223
Run 16 | Reward:   2365.5 | Shortfall:   11 | ideal_gap:  231 (excess= 231) | demand_skips:   11 | avg days=223
Run 17 | Reward:   2349.5 | Shortfall:   16 | ideal_gap:  239 (excess= 239) | demand_skips:   16 | avg days=223
Run 18 | Reward:   2363.1 | Shortfall:   12 | ideal_gap:  232 (excess= 232) | demand_skips:   12 | avg days=223
Run 19 | Reward:   2356.7 | Shortfall:   12 | ideal_gap:  237 (excess= 237) | demand_skips:   12 | avg days=223
Run 20 | Reward:   2347.7 | Shortfall:   14 | ideal_gap:  233 (excess= 233) | demand_skips:   14 | avg days=223

MEAN over 20 runs | Shortfall: 13.2 | Ideal excess: 232.7
BEST: Run 10 | Shortfall: 10 (99.52% coverage) | Ideal gap: 226 (excess=226)
Days worked/employee: avg=223, min=223, max=223
Day 341: T-A=1
Day 358: M-A=2, T-A=2, T-B=1
Day 361: M-A=1, M-B=1, T-A=1, T-B=1

Best schedule written to /kaggle/working/best_schedule_2teams_multiteam_option7.csv

======================================================================
4teams (trained) — 4 teams, 24 employees, total min demand 2920, ideal floor 488
======================================================================
Run  1 | Reward:   5292.0 | Shortfall:    6 | ideal_gap:  689 (excess= 201) | demand_skips:    6 | avg days=223
Run  2 | Reward:   5304.2 | Shortfall:    2 | ideal_gap:  696 (excess= 208) | demand_skips:    2 | avg days=223
Run  3 | Reward:   5286.7 | Shortfall:    5 | ideal_gap:  698 (excess= 210) | demand_skips:    5 | avg days=223
Run  4 | Reward:   5312.2 | Shortfall:    2 | ideal_gap:  689 (excess= 201) | demand_skips:    2 | avg days=223
Run  5 | Reward:   5294.6 | Shortfall:    3 | ideal_gap:  700 (excess= 212) | demand_skips:    3 | avg days=223
Run  6 | Reward:   5292.0 | Shortfall:    6 | ideal_gap:  689 (excess= 201) | demand_skips:    6 | avg days=223
Run  7 | Reward:   5281.0 | Shortfall:    5 | ideal_gap:  703 (excess= 215) | demand_skips:    5 | avg days=223
Run  8 | Reward:   5306.7 | Shortfall:    4 | ideal_gap:  685 (excess= 197) | demand_skips:    4 | avg days=223
Run  9 | Reward:   5316.2 | Shortfall:    1 | ideal_gap:  690 (excess= 202) | demand_skips:    1 | avg days=223
Run 10 | Reward:   5268.9 | Shortfall:   11 | ideal_gap:  687 (excess= 199) | demand_skips:   11 | avg days=223
Run 11 | Reward:   5297.4 | Shortfall:    2 | ideal_gap:  702 (excess= 214) | demand_skips:    2 | avg days=223
Run 12 | Reward:   5289.5 | Shortfall:    4 | ideal_gap:  700 (excess= 212) | demand_skips:    4 | avg days=223
Run 13 | Reward:   5297.5 | Shortfall:    4 | ideal_gap:  693 (excess= 205) | demand_skips:    4 | avg days=223
Run 14 | Reward:   5325.3 | Shortfall:    1 | ideal_gap:  682 (excess= 194) | demand_skips:    1 | avg days=223
Run 15 | Reward:   5292.5 | Shortfall:    5 | ideal_gap:  693 (excess= 205) | demand_skips:    5 | avg days=223
Run 16 | Reward:   5313.4 | Shortfall:    2 | ideal_gap:  688 (excess= 200) | demand_skips:    2 | avg days=223
Run 17 | Reward:   5324.6 | Shortfall:    0 | ideal_gap:  687 (excess= 199) | demand_skips:    0 | avg days=223
Run 18 | Reward:   5270.5 | Shortfall:   10 | ideal_gap:  690 (excess= 202) | demand_skips:   10 | avg days=223
Run 19 | Reward:   5271.5 | Shortfall:    8 | ideal_gap:  698 (excess= 210) | demand_skips:    8 | avg days=223
Run 20 | Reward:   5292.1 | Shortfall:    8 | ideal_gap:  680 (excess= 192) | demand_skips:    8 | avg days=223

MEAN over 20 runs | Shortfall: 4.5 | Ideal excess: 203.9
BEST: Run 17 | Shortfall: 0 (100.00% coverage) | Ideal gap: 687 (excess=199)
Days worked/employee: avg=223, min=223, max=223

Best schedule written to /kaggle/working/best_schedule_4teams_multiteam_option7.csv

======================================================================
8teams (ZERO-SHOT (never trained on)) — 8 teams, 48 employees, total min demand 5840, ideal floor 976
======================================================================
Run  1 | Reward:  10536.8 | Shortfall:    6 | ideal_gap: 1323 (excess= 347) | demand_skips:    6 | avg days=223
Run  2 | Reward:  10548.8 | Shortfall:    4 | ideal_gap: 1321 (excess= 345) | demand_skips:    4 | avg days=223
Run  3 | Reward:  10519.0 | Shortfall:    2 | ideal_gap: 1362 (excess= 386) | demand_skips:    2 | avg days=223
Run  4 | Reward:  10507.6 | Shortfall:    6 | ideal_gap: 1353 (excess= 377) | demand_skips:    6 | avg days=223
Run  5 | Reward:  10541.2 | Shortfall:    3 | ideal_gap: 1334 (excess= 358) | demand_skips:    3 | avg days=223
Run  6 | Reward:  10519.5 | Shortfall:    5 | ideal_gap: 1346 (excess= 370) | demand_skips:    5 | avg days=223
Run  7 | Reward:  10541.4 | Shortfall:    2 | ideal_gap: 1339 (excess= 363) | demand_skips:    2 | avg days=223
Run  8 | Reward:  10535.6 | Shortfall:    7 | ideal_gap: 1319 (excess= 343) | demand_skips:    7 | avg days=223
Run  9 | Reward:  10543.0 | Shortfall:    4 | ideal_gap: 1327 (excess= 351) | demand_skips:    4 | avg days=223
Run 10 | Reward:  10546.1 | Shortfall:    3 | ideal_gap: 1329 (excess= 353) | demand_skips:    3 | avg days=223
Run 11 | Reward:  10565.1 | Shortfall:    5 | ideal_gap: 1299 (excess= 323) | demand_skips:    5 | avg days=223
Run 12 | Reward:  10556.7 | Shortfall:    3 | ideal_gap: 1318 (excess= 342) | demand_skips:    3 | avg days=223
Run 13 | Reward:  10507.3 | Shortfall:    8 | ideal_gap: 1343 (excess= 367) | demand_skips:    8 | avg days=223
Run 14 | Reward:  10539.9 | Shortfall:    5 | ideal_gap: 1325 (excess= 349) | demand_skips:    5 | avg days=223
Run 15 | Reward:  10534.2 | Shortfall:    4 | ideal_gap: 1336 (excess= 360) | demand_skips:    4 | avg days=223
Run 16 | Reward:  10559.3 | Shortfall:    5 | ideal_gap: 1305 (excess= 329) | demand_skips:    5 | avg days=223
Run 17 | Reward:  10542.1 | Shortfall:    9 | ideal_gap: 1302 (excess= 326) | demand_skips:    9 | avg days=223
Run 18 | Reward:  10541.4 | Shortfall:    2 | ideal_gap: 1339 (excess= 363) | demand_skips:    2 | avg days=223
Run 19 | Reward:  10558.9 | Shortfall:    2 | ideal_gap: 1321 (excess= 345) | demand_skips:    2 | avg days=223
Run 20 | Reward:  10548.8 | Shortfall:    4 | ideal_gap: 1321 (excess= 345) | demand_skips:    4 | avg days=223

MEAN over 20 runs | Shortfall: 4.5 | Ideal excess: 352.1
BEST: Run 19 | Shortfall: 2 (99.97% coverage) | Ideal gap: 1321 (excess=345)
Days worked/employee: avg=223, min=223, max=223
Day 358: T-A=1
Day 361: M-A=1

Best schedule written to /kaggle/working/best_schedule_8teams_multiteam_option7.csv
```

## Summary (averages over 20 runs)

| Version | 2T Shortfall | 2T Ideal Gap | 2T Days | 4T Shortfall | 4T Ideal Gap | 4T Days | 8T Shortfall | 8T Ideal Gap | 8T Days |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fully Connected | 13.95 | 230.2 | 223.0 | 4.35 | 212.6 | 223.0 | 4.95 | 386.0 | 223.0 |
| Emp↔Day only on assignment | 13.60 | 236.0 | 218.4 | 4.60 | 183.4 | 223.0 | 4.50 | 329.9 | 223.0 |
| No Emp↔Day connection | 13.60 | 240.1 | 219.4 | 4.30 | 270.0 | 223.0 | 4.80 | 502.1 | 223.0 |
| Demand Node Graph | 13.20 | 232.7 | 223.0 | 4.50 | 203.9 | 223.0 | 4.50 | 352.1 | 223.0 |



## Employee <-> Day only when assignment exists (Version 2):

- **Joint updates instead of alternation:** one *iteration* = one episode collected from **every** pool scenario, then a single `ppo_update_multi` over all of them — replacing the episode-level round-robin, which gave ~40+ consecutive single-task gradient steps per scenario.
- **Minibatch interleaving:** within each PPO epoch, the scenarios' snapshot-grouped minibatches alternate round-robin, so the shared heads never see a long single-task stretch. Minibatches stay single-scenario (employee counts and mask widths can't mix); GAE and advantage normalization stay per-episode, so neither scenario's return scale dominates.

```
Checkpoint: iteration 80, best metric = (0.014724714009902941, 0.16587852480332024)

======================================================================
SMARTASK_SIMPLE_2025 (trained) — 2 teams, 12 employees, total min demand 2086, ideal floor 0
======================================================================
Run  1 | Reward:   2658.5 | Shortfall:   24 | ideal_gap:  186 (excess= 186) | demand_skips:   24 | avg days=223
Run  2 | Reward:   2657.7 | Shortfall:   22 | ideal_gap:  188 (excess= 188) | demand_skips:   22 | avg days=223
Run  3 | Reward:   2652.2 | Shortfall:   24 | ideal_gap:  181 (excess= 181) | demand_skips:   24 | avg days=223
Run  4 | Reward:   2652.3 | Shortfall:   23 | ideal_gap:  190 (excess= 190) | demand_skips:   23 | avg days=223
Run  5 | Reward:   2641.4 | Shortfall:   24 | ideal_gap:  189 (excess= 189) | demand_skips:   24 | avg days=223
Run  6 | Reward:   2653.9 | Shortfall:   22 | ideal_gap:  189 (excess= 189) | demand_skips:   22 | avg days=223
Run  7 | Reward:   2671.1 | Shortfall:   19 | ideal_gap:  191 (excess= 191) | demand_skips:   19 | avg days=223
Run  8 | Reward:   2670.0 | Shortfall:   20 | ideal_gap:  191 (excess= 191) | demand_skips:   20 | avg days=223
Run  9 | Reward:   2650.3 | Shortfall:   23 | ideal_gap:  190 (excess= 190) | demand_skips:   23 | avg days=223
Run 10 | Reward:   2631.4 | Shortfall:   27 | ideal_gap:  189 (excess= 189) | demand_skips:   27 | avg days=223
Run 11 | Reward:   2650.8 | Shortfall:   25 | ideal_gap:  183 (excess= 183) | demand_skips:   25 | avg days=223
Run 12 | Reward:   2656.9 | Shortfall:   20 | ideal_gap:  196 (excess= 196) | demand_skips:   20 | avg days=223
Run 13 | Reward:   2664.5 | Shortfall:   22 | ideal_gap:  184 (excess= 184) | demand_skips:   22 | avg days=223
Run 14 | Reward:   2661.4 | Shortfall:   23 | ideal_gap:  178 (excess= 178) | demand_skips:   23 | avg days=223
Run 15 | Reward:   2650.3 | Shortfall:   22 | ideal_gap:  192 (excess= 192) | demand_skips:   22 | avg days=223
Run 16 | Reward:   2658.8 | Shortfall:   22 | ideal_gap:  191 (excess= 191) | demand_skips:   22 | avg days=223
Run 17 | Reward:   2655.0 | Shortfall:   21 | ideal_gap:  196 (excess= 196) | demand_skips:   21 | avg days=223
Run 18 | Reward:   2638.2 | Shortfall:   26 | ideal_gap:  184 (excess= 184) | demand_skips:   26 | avg days=223
Run 19 | Reward:   2641.8 | Shortfall:   24 | ideal_gap:  187 (excess= 187) | demand_skips:   24 | avg days=223
Run 20 | Reward:   2650.8 | Shortfall:   23 | ideal_gap:  187 (excess= 187) | demand_skips:   23 | avg days=223

MEAN over 20 runs | Shortfall: 22.8 | Ideal excess: 188.1
BEST: Run 7 | Shortfall: 19 (99.09% coverage) | Ideal gap: 191 (excess=191)
Days worked/employee: avg=223, min=223, max=223
Day 312: T-B=1
Day 319: T-B=1
Day 326: T-B=1
Day 333: T-B=1
Day 334: T-A=1, T-B=1
Day 340: T-B=1
Day 341: M-B=1, T-A=1, T-B=1
Day 347: M-B=1, T-B=1
Day 354: M-B=1, T-B=1
Day 358: M-A=1, M-B=1, T-B=1
Day 361: M-B=1, T-B=1

Best schedule written to best_schedule_SMARTASK_SIMPLE_2025_multiteam_v3.csv

======================================================================
SMARTASK_4TEAMS_24EMP (trained) — 4 teams, 24 employees, total min demand 2920, ideal floor 488
======================================================================
Run  1 | Reward:   5178.2 | Shortfall:   21 | ideal_gap:  722 (excess= 234) | demand_skips:   21 | avg days=223
Run  2 | Reward:   5216.9 | Shortfall:   19 | ideal_gap:  697 (excess= 209) | demand_skips:   19 | avg days=223
Run  3 | Reward:   5210.1 | Shortfall:   19 | ideal_gap:  703 (excess= 215) | demand_skips:   19 | avg days=223
Run  4 | Reward:   5193.1 | Shortfall:   21 | ideal_gap:  709 (excess= 221) | demand_skips:   21 | avg days=223
Run  5 | Reward:   5183.8 | Shortfall:   19 | ideal_gap:  726 (excess= 238) | demand_skips:   19 | avg days=223
Run  6 | Reward:   5223.0 | Shortfall:   16 | ideal_gap:  705 (excess= 217) | demand_skips:   16 | avg days=223
Run  7 | Reward:   5220.1 | Shortfall:   15 | ideal_gap:  712 (excess= 224) | demand_skips:   15 | avg days=223
Run  8 | Reward:   5239.0 | Shortfall:   16 | ideal_gap:  691 (excess= 203) | demand_skips:   16 | avg days=223
Run  9 | Reward:   5220.1 | Shortfall:   15 | ideal_gap:  712 (excess= 224) | demand_skips:   15 | avg days=223
Run 10 | Reward:   5194.1 | Shortfall:   19 | ideal_gap:  717 (excess= 229) | demand_skips:   19 | avg days=223
Run 11 | Reward:   5207.3 | Shortfall:   20 | ideal_gap:  701 (excess= 213) | demand_skips:   20 | avg days=223
Run 12 | Reward:   5194.2 | Shortfall:   21 | ideal_gap:  708 (excess= 220) | demand_skips:   21 | avg days=223
Run 13 | Reward:   5239.1 | Shortfall:   18 | ideal_gap:  682 (excess= 194) | demand_skips:   18 | avg days=223
Run 14 | Reward:   5229.2 | Shortfall:   15 | ideal_gap:  704 (excess= 216) | demand_skips:   15 | avg days=223
Run 15 | Reward:   5232.8 | Shortfall:   17 | ideal_gap:  692 (excess= 204) | demand_skips:   17 | avg days=223
Run 16 | Reward:   5229.3 | Shortfall:   17 | ideal_gap:  695 (excess= 207) | demand_skips:   17 | avg days=223
Run 17 | Reward:   5215.8 | Shortfall:   19 | ideal_gap:  698 (excess= 210) | demand_skips:   19 | avg days=223
Run 18 | Reward:   5202.1 | Shortfall:   19 | ideal_gap:  710 (excess= 222) | demand_skips:   19 | avg days=223
Run 19 | Reward:   5220.2 | Shortfall:   17 | ideal_gap:  703 (excess= 215) | demand_skips:   17 | avg days=223
Run 20 | Reward:   5225.4 | Shortfall:   18 | ideal_gap:  694 (excess= 206) | demand_skips:   18 | avg days=223

MEAN over 20 runs | Shortfall: 18.1 | Ideal excess: 216.1
BEST: Run 14 | Shortfall: 15 (99.49% coverage) | Ideal gap: 704 (excess=216)
Days worked/employee: avg=223, min=223, max=223
Day 284: T-B=1
Day 304: T-C=1
Day 312: M-C=1
Day 319: T-C=1
Day 326: T-D=1
Day 333: T-D=1
Day 340: T-D=1
Day 341: T-D=1
Day 347: M-D=1, T-D=1
Day 354: M-D=1, T-B=1, T-D=1
Day 361: T-B=1, T-C=1

Best schedule written to best_schedule_SMARTASK_4TEAMS_24EMP_multiteam_v3.csv

======================================================================
SMARTASK_8TEAMS_48EMP (ZERO-SHOT (never trained on)) — 8 teams, 48 employees, total min demand 5840, ideal floor 976
======================================================================
Run  1 | Reward:  10352.9 | Shortfall:   24 | ideal_gap: 1419 (excess= 443) | demand_skips:   24 | avg days=223
Run  2 | Reward:  10375.3 | Shortfall:   24 | ideal_gap: 1396 (excess= 420) | demand_skips:   24 | avg days=223
Run  3 | Reward:  10345.1 | Shortfall:   30 | ideal_gap: 1396 (excess= 420) | demand_skips:   30 | avg days=223
Run  4 | Reward:  10343.7 | Shortfall:   32 | ideal_gap: 1387 (excess= 411) | demand_skips:   32 | avg days=223
Run  5 | Reward:  10393.3 | Shortfall:   21 | ideal_gap: 1393 (excess= 417) | demand_skips:   21 | avg days=223
Run  6 | Reward:  10360.2 | Shortfall:   27 | ideal_gap: 1396 (excess= 420) | demand_skips:   27 | avg days=223
Run  7 | Reward:  10345.0 | Shortfall:   25 | ideal_gap: 1422 (excess= 446) | demand_skips:   25 | avg days=223
Run  8 | Reward:  10350.6 | Shortfall:   26 | ideal_gap: 1411 (excess= 435) | demand_skips:   26 | avg days=223
Run  9 | Reward:  10365.2 | Shortfall:   26 | ideal_gap: 1396 (excess= 420) | demand_skips:   26 | avg days=223
Run 10 | Reward:  10384.0 | Shortfall:   24 | ideal_gap: 1387 (excess= 411) | demand_skips:   24 | avg days=223
Run 11 | Reward:  10363.6 | Shortfall:   24 | ideal_gap: 1408 (excess= 432) | demand_skips:   24 | avg days=223
Run 12 | Reward:  10366.2 | Shortfall:   26 | ideal_gap: 1395 (excess= 419) | demand_skips:   26 | avg days=223
Run 13 | Reward:  10360.9 | Shortfall:   23 | ideal_gap: 1416 (excess= 440) | demand_skips:   23 | avg days=223
Run 14 | Reward:  10358.7 | Shortfall:   24 | ideal_gap: 1413 (excess= 437) | demand_skips:   24 | avg days=223
Run 15 | Reward:  10372.0 | Shortfall:   26 | ideal_gap: 1389 (excess= 413) | demand_skips:   26 | avg days=223
Run 16 | Reward:  10339.7 | Shortfall:   33 | ideal_gap: 1386 (excess= 410) | demand_skips:   33 | avg days=223
Run 17 | Reward:  10353.0 | Shortfall:   29 | ideal_gap: 1393 (excess= 417) | demand_skips:   29 | avg days=223
Run 18 | Reward:  10384.5 | Shortfall:   21 | ideal_gap: 1402 (excess= 426) | demand_skips:   21 | avg days=223
Run 19 | Reward:  10393.1 | Shortfall:   22 | ideal_gap: 1388 (excess= 412) | demand_skips:   22 | avg days=223
Run 20 | Reward:  10357.4 | Shortfall:   26 | ideal_gap: 1404 (excess= 428) | demand_skips:   26 | avg days=223

MEAN over 20 runs | Shortfall: 25.6 | Ideal excess: 423.9
BEST: Run 5 | Shortfall: 21 (99.64% coverage) | Ideal gap: 1393 (excess=417)
Days worked/employee: avg=223, min=223, max=223
Day 228: T-H=1
Day 242: T-E=1
Day 270: T-F=1
Day 284: T-F=1
Day 319: T-C=1
Day 333: M-C=1, T-H=1
Day 334: M-C=1, M-G=1, T-D=1
Day 340: M-D=1
Day 341: T-D=1
Day 347: T-C=1, T-D=1
Day 354: T-E=1, T-H=1
Day 358: T-A=1, T-E=1
Day 361: T-E=1, T-F=1, T-H=1

Best schedule written to best_schedule_SMARTASK_8TEAMS_48EMP_multiteam_v3.csv
```
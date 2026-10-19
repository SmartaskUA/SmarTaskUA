# How to solve a problem

A problem is a **schema v4 package**: `problem.json` plus its CSVs, optionally a shift menu and a partial
`result.json` whose days stay fixed ([format](../json_generation/schema_v4/docs/FORMAT.md)). Build one with the
JSON wizard (http://localhost/json-gen → *Download ZIP*) or start from `json_generation/schema_v4/examples/`.

Five solvers read v4. They all solve the same model and are scored the same way:

| alias | algorithm (UI / API name) | kind |
|---|---|---|
| `ilp` | `ILP_Sisqual_Hours_MathematicalDefinition7` | exact, CBC |
| `csp` | `CSP_Sisqual_Hours_MathematicalDefinition7` | exact, CP-SAT |
| `hybrid` | `Hybrid_Heuristic_Sisqual_3` | greedy + restarts |
| `hybrid-levels` | `Hybrid_Heuristic_Sisqual_Levels_Included` | greedy, prefers higher-priority skills |
| `ga` | `Genetic Algorithm v4` | genetic algorithm |

## From the web app

1. **Problems** → *Upload v4 package (.zip)* with the wizard's ZIP (or pick a listed v4 problem).
   A package whose `problemId` already exists as an upload is offered *Replace*.
2. *Use In Schedule* → **Generate Schedule**: pick an algorithm and a time limit → *Generate*.
3. **Schedule** lists the run. Open it for the hourly calendar, the KPIs and *Download Sisqual JSON*
   (the v4 `result.json`).

Uploads land in `data/problems/uploads/<problemId>/`. The same flow over HTTP:
`POST /api/problems/upload` (multipart `file`), then `POST /api/problems/{problemId}/solve`
with `{"algorithm": "...", "maxTime": "1"}`.

## From the command line

With Docker only (build the image once: `docker compose -f infra/docker-compose.yml build scheduler`):

```bash
make solve PKG=json_generation/schema_v4/examples/cenario2_partial            # ilp, 1 minute
make solve PKG=json_generation/schema_v4/examples/cenario2_partial ALG=all TIME=2
```

With a local Python that has the scheduler's requirements:

```bash
cd src
python -m scheduler solve ../json_generation/schema_v4/examples/cenario2_partial -a ga -t 2
```

It prints one line per algorithm and exits 1 if the package is rejected or a result is invalid:

```
ilp   shortage 489/3496   priority 55397   unassigned 0   2.1s   exports/cenario2_partial/ilp/result.json   valid
```

- Results: `exports/<package folder>/<alias>/` - a copy of the package plus `result.json` and
  `result_schedules.csv`. Change it with `-o DIR`.
- `valid` means the v4 validator accepted the result against its input.
- Solve settings go in `--param` (the defaults are shown): `w1=1000` shortage weight, `w2=1` skill-priority
  weight, `w3=10` worked-day-off weight, `allow_day_off_swap=false`.

## When it fails

| code | meaning | fix |
|---|---|---|
| `INVALID_V4_PACKAGE` | the parser rejected the package; every reason is listed | fix the package (the wizard's validator shows the same errors) |
| `SOLVER_INFEASIBLE` | the fixed days and labour law leave no schedule | loosen the partial result or the cells |
| `SOLVER_NO_SOLUTION` | time ran out before a first schedule | raise the time limit |

To check a package or result on its own: `make -C json_generation/schema_v4 validate DIR=<folder>`.

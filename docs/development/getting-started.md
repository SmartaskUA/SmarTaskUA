# Getting Started

## Prerequisites

- **Docker** and **Docker Compose**, **Git**
- Optional: **Maven** (Java), **Node.js 20** (frontend), **Python 3.11** (scheduler) for local development

Developed on Linux; Windows/macOS may need adjustments.

## Quick start

```bash
git clone <repository-url> && cd SmarTaskUA
make build          # build the API and every image, then start the stack
```

- Main app: http://localhost/ (manager/manager)
- JSON wizard: http://localhost/json-gen
- API: http://localhost/api

Solve something straight away. From the app: **Problems** → `C2_January_2026` → *Use In Schedule* →
*Generate*. Or from the command line:

```bash
make solve PKG=json_generation/schema_v4/examples/cenario2_partial ALG=all
```

Details: [how-to-solve.md](../how-to-solve.md).

## Everyday commands

```bash
make help              # every target
make up / make down    # start / stop the stack
make test-scheduler    # scheduler tests, inside the scheduler image
```

## Adding an algorithm

- **For schema v4 problems:** follow [Adding a v4 solver](../architecture/v4-parser.md#adding-a-v4-solver).
  The solver reads the parsed `V4Instance` and returns rows. The shared scorer and writer do the rest.
- **For legacy v2.x inputs:** implement `solve(vacations, minimuns, employees, maxTime, year, shifts, rules)` in
  `src/scheduler/algorithms/`, register it in `TaskManager.py` and in the API's `SchedulingAlgorithmRegistry`.

## Business rules (legacy solvers)

Edit `config/rules.json` (the master copy), then `make build`. Never edit the generated copies
`src/api/src/main/resources/rules.json` or `src/scheduler/rules.json`. v4 solvers read their labour law from
the package's `constraints.hard` instead.

## Next

[System overview](../architecture/system-overview.md) · [Solve flow](../architecture/solve-flow.md) ·
[Algorithms](../algorithms/overview.md) · [Docs index](../README.md)

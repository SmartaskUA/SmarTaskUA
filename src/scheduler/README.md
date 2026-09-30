# Scheduler Service

The Python worker that generates schedules. It consumes tasks from RabbitMQ (`task-queue`), runs the chosen
algorithm, stores the result in MongoDB and reports status on `status-queue`. The same algorithms also run
from the command line.

- **Solve a problem** (web app or CLI): [docs/how-to-solve.md](../../docs/how-to-solve.md)
- **The algorithms:** [docs/algorithms/overview.md](../../docs/algorithms/overview.md)
- **How schema v4 is read:** [docs/architecture/v4-parser.md](../../docs/architecture/v4-parser.md)

## Layout

```
TaskManager.py        algorithm registry (name -> solve) and dispatch; V4_ALGORITHMS take the v4 path
RabbitMQClient.py     queue consumer: runs a task, stores the schedule, publishes its status
cli.py, __main__.py   `python -m scheduler list | param | run | solve | generate-employees`
solve_command.py      `solve`: a v4 package -> result.json for one or all v4 solvers
problem_v4/           the schema v4 parser, scorer and result writer
algorithms/           the solvers (v4: *_MathematicalDefinition7, Hybrid_Heuristic_Sisqual_*, GA/ga_v4.py)
validators/           v2.2 Sisqual precheck and failure reports
tests/                pytest suite (v4 parser, solvers, CLI)
```

## Run

```bash
make solve PKG=json_generation/schema_v4/examples/cenario2_partial ALG=all   # from the repo root, in Docker
cd src && python -m scheduler solve <package> -a ilp -t 1                     # locally
cd src && python -m scheduler list                                            # every registered algorithm
cd src && python -m scheduler run --algorithm <name> --problem-path <bundle> --param KEY=VALUE   # any algorithm
```

`run` is the general form. It passes `--param` values (and `--vacations`, `--minimuns` and so on for legacy
solvers) to the algorithm's `solve()`. `python -m scheduler param --algorithm <name>` lists what an
algorithm accepts.

## Test

```bash
make test-scheduler    # from the repo root: pytest inside the scheduler image (pinned pulp/ortools)
```

Locally: `pip install -r requirements.txt -r requirements-dev.txt`, then run `python -m pytest` from this folder.

## Configuration

- Legacy solvers read business rules from `config/rules.json`, which the build copies here. Don't edit the copy.
- v4 solvers read labour law from the package itself.
- Environment: `MONGO_HOST` / `MONGO_PORT` (their defaults fit the compose network) and `SCHEDULE_EXPORT_DIR` (the CLI's CSV export folder).

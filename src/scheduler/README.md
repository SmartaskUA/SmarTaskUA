# Scheduler Service

## Overview

Python worker service that generates optimized work schedules using various constraint-based algorithms. Consumes schedule generation tasks from RabbitMQ, processes them using the selected algorithm, and stores results in MongoDB.

## Technology Stack

- **Python 3.11**
- **Google OR-Tools** (for CSP algorithms)
- **PuLP** (for ILP algorithms)
- **RabbitMQ** (pika) for message queue
- **MongoDB** (pymongo) for data storage

## Project Structure

```
.
├── RabbitMQClient.py            # RabbitMQ consumer - listens to task-queue
├── TaskManager.py               # Algorithm dispatcher and task coordinator
├── MongoDBClient.py             # MongoDB connection and data access
├── requirements.txt             # Python dependencies
├── send_task.py                 # Testing utility - manual task submission
├── start-env                    # Script to setup local Python venv
└── algorithms/                  # All scheduling algorithms
    ├── contexts/                # Algorithm execution contexts
    ├── engines/                 # Rules engines
    └── handlers/                # Rule handlers
```

## Available Algorithms

- **CSP / CSPv2** - Constraint Satisfaction (Google OR-Tools CP-SAT)
- **ILP / ILPv2** - Integer Linear Programming (PuLP)
- **Greedy Randomized** - Heuristic approach
- **Hill Climbing** - Local search optimization
- **Greedy Climbing** - Hybrid approach
- **Engines** - Advanced versions with rules engine integration

### Hourly Algorithms

- **COP_1_Half_Intervals** - Constraint Optimization Programming
- **COP_1** - Constraint Optimization Programming
- **COP_2_Half_Intervals** - Constraint Optimization Programming
- **COP_2** - Constraint Optimization Programming
- **Heuristica_Half_Intervals** - Mixed Grasp and ILP Heuristic
- **Heuristica1** - Mixed Grasp and ILP Heuristic
- **ILP_2_Half_Intervals** - Integer Linear Programming (PuLP)
- **ILP_2** - Integer Linear Programming (PuLP)
- **ILP_3_Half_Intervals** - Integer Linear Programming (PuLP)
- **ILP_3** - Integer Linear Programming (PuLP)
- **ILP_4_Half_Intervals** - Integer Linear Programming (PuLP)
- **ILP_4** - Integer Linear Programming (PuLP)

### 3 Shifts Algorithms - [ X ]

- **Hybrid_Heuristic** - Grasp Heuristic with Pontuation
- **ILPv3** - ILP
- **Puzzle_Heuristic** - Mixed Grasp and ILP Heuristic
- **R2_Heuristic** - Simple Grasp Greedy Heuristic

### Hourly Sisqual Algorithms - [ X ]

- **CSP_Sisqual_Hours_MathematicalDefiniton7** - Constraint Search Programming
- **Hybrid_Heuristic_Sisqual_Levels_Included** - Grasp Heuristic
- **Hybrid_Heuristic_Sisqual_No_Levels_Included** Grasp Heuristic
- **ILP_Sisqual_Hours_MathematicalDefinition7** - ILP


See `TaskManager.py` for the complete list of available algorithms.

## How It Works

1. **Listens** to `task-queue` via RabbitMQ
2. **Receives** task with: employees, vacations, minimums, algorithm choice, year, max time
3. **Dispatches** to appropriate algorithm in `algorithms/` directory
4. **Generates** optimized schedule respecting all constraints
5. **Saves** result to MongoDB
6. **Publishes** status updates to `status-queue`

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
python RabbitMQClient.py
```

### Run Any Algorithm from the Terminal

The scheduler now includes a generic CLI that can list algorithms, run one algorithm, run all registered algorithms, and inspect which parameters each algorithm accepts.

```bash
# List registered algorithms
python /home/hugo/Desktop/SmarTaskUA/scripts/run_scheduler.py list

# Run one algorithm
python /home/hugo/Desktop/SmarTaskUA/scripts/run_scheduler.py run \
    --algorithm Hybrid_Heuristic_Sisqual_Levels_Included \
    --problem-path /home/hugo/Desktop/SmarTaskUA/data/problems/SISQUAL_OCTOBER_2025/problem.json \
    --max-time 10 \
    --restarts 3
```

#### Discovering an Algorithm's Parameters

Each algorithm can accept a different set of arguments (e.g. `R2_Heuristic` uses `n_outer`/`n_inner` debug knobs that other algorithms don't have). Instead of reading the source code, use the `param` subcommand to list, by introspection, exactly which parameters a given algorithm's entry point accepts:

```bash
python /home/hugo/Desktop/SmarTaskUA/scripts/run_scheduler.py param --algorithm R2_Heuristic
```

```
max-time
vacations
employees
minimuns
year
shifts
...
```

Omit `--algorithm` to list the parameters of every registered algorithm at once, or add `--json` for machine-readable output (which also includes whether each parameter is required and its default value):

```bash
python /home/hugo/Desktop/SmarTaskUA/scripts/run_scheduler.py param --json --algorithm R2_Heuristic
```

> Note: the names shown use dashes (`max-time`) purely for readability. When actually passing a value with `--param`, use the underscore form instead (`max_time`), since that's the real Python argument name.

#### Passing Algorithm-Specific Parameters (`--param`)

The CLI only exposes a fixed set of flags directly (`--vacations`, `--employees`, `--minimuns`, `--max-time`, `--restarts`, `--day-order-mode`, ...). Any other parameter an algorithm accepts — for example the `n_outer`, `n_inner`, `debug_daily_trace`, or `debug_day_delay_seconds` knobs on `R2_Heuristic` — has no dedicated flag and must be passed through `--param KEY=VALUE` (repeatable):

```bash
python /home/hugo/Desktop/SmarTaskUA/scripts/run_scheduler.py run \
    --algorithm R2_Heuristic \
    --vacations /home/hugo/Desktop/SmarTaskUA/src/api/src/main/resources/vacationData_3shifts/24_employees/templates/VacationTemplate_Case1_24.csv \
    --employees /home/hugo/Desktop/SmarTaskUA/tmp/employees_layout.json \
    --minimuns /home/hugo/Desktop/SmarTaskUA/src/api/src/main/resources/minimuns/minimuns_3shifts_2teams_24emp.csv \
    --param n_outer=2 \
    --param n_inner=2 \
    --param debug_daily_trace=true \
    --param debug_day_delay_seconds=100
```

### Generate Employees Layout Files

If you want a file with team layout only, generate it first and then pass it back to the solver with `--employees @file.json`.

```bash
python /home/hugo/Desktop/SmarTaskUA/scripts/run_scheduler.py generate-employees \
    --layout A=6,B=6,AB=6 \
    --output /home/hugo/Desktop/SmarTaskUA/tmp/employees_layout.json
```

This writes a JSON array of employees by default. Use `--wrap-problem` if you want the `{"employees": {"model": "team", "simple": [...]}}` shape used by the API problem files.

### Run with Docker

```bash
# From project root
make build-scheduler
```

### Testing

Use `send_task.py` to manually send test tasks to RabbitMQ:

```bash
python send_task.py
```

## Configuration

Environment variables (set in docker-compose or locally):
- `RABBITMQ_HOST` - RabbitMQ server address
- `MONGODB_URI` - MongoDB connection string
- Queue names: `task-queue` (consume), `status-queue` (publish)

## Business Rules

Schedule generation follows constraints defined in `config/rules.json`:
- Maximum consecutive workdays
- Minimum coverage requirements
- Vacation blocks
- Team eligibility
- Shift transitions
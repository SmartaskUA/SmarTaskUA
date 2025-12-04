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
    ├── CSP.py                   # Constraint Satisfaction Programming
    ├── CSPv2.py                 # CSP variant
    ├── ILP.py                   # Integer Linear Programming
    ├── ILPv2.py                 # ILP variant
    ├── greedyRandomized.py      # Greedy heuristic approach
    ├── greedyClimbing.py        # Greedy + Hill Climbing hybrid
    ├── hillClimbing.py          # Local search optimization
    ├── utils.py                 # Shared utilities
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

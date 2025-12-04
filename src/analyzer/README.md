# Analyzer Service

## Overview

Python worker service that performs KPI (Key Performance Indicator) analysis on generated schedules. Validates single schedules against business rules and compares multiple schedules to identify the best solution.

## Technology Stack

- **Python 3.11**
- **RabbitMQ** (pika) for message queue
- **MongoDB** (pymongo) for data access

## Project Structure

```
.
├── analyze.py                   # RabbitMQ consumer - listens to comparison-queue
├── kpiVerification.py           # Single schedule KPI validation
├── kpiComparison.py             # Multi-schedule comparison
└── requirements.txt             # Python dependencies
```

## Key Files

### `analyze.py`
- RabbitMQ consumer that listens to `comparison-queue`
- Orchestrates KPI analysis tasks
- Stores results in MongoDB

### `kpiVerification.py`
- Analyzes a single schedule
- Validates against business rules
- Calculates metrics:
  - Rule violations count
  - Coverage satisfaction
  - Workload distribution
  - Constraint compliance

### `kpiComparison.py`
- Compares multiple schedules
- Ranks schedules by quality
- Identifies best solution based on KPIs
- Generates comparison reports

## How It Works

1. **Listens** to `comparison-queue` via RabbitMQ
2. **Receives** analysis request with schedule ID(s)
3. **Fetches** schedule data from MongoDB
4. **Analyzes** using verification and comparison modules
5. **Calculates** KPIs and quality metrics
6. **Stores** analysis results in MongoDB
7. **Returns** results to API

## KPIs Calculated

- **Hard Constraint Violations:** Must be zero for valid schedules
- **Soft Constraint Violations:** Penalized but allowed
- **Coverage Satisfaction:** Minimum staffing requirements met
- **Workload Balance:** Fair distribution across employees
- **Rule Compliance Score:** Overall quality metric

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
python analyze.py
```

### Run with Docker

```bash
# From project root
make build-analyzer
```

## Configuration

Environment variables (set in docker-compose or locally):
- `RABBITMQ_HOST` - RabbitMQ server address
- `MONGODB_URI` - MongoDB connection string
- Queue names: `comparison-queue` (consume)

## Integration

- **Input:** Schedule IDs from API via RabbitMQ
- **Output:** Analysis results stored in MongoDB `verifications` and `comparisons` collections
- **Used by:** Frontend to display schedule quality and comparisons

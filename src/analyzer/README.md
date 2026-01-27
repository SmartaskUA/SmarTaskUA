# Analyzer Service

## Overview

Python worker service that performs KPI (Key Performance Indicator) analysis on generated schedules. Validates single schedules against business rules and compares multiple schedules to identify the best solution.

Supports two types of scheduling problems:
- **Shift-based** (turnos): M_A, T_B, N_C format
- **Time-slot based** (horas): 9-14-18_A format (with 30-minute or 1-hour granularity)

## Technology Stack

- **Python 3.11**
- **RabbitMQ** (pika) for message queue
- **MongoDB** (pymongo) for data access
- **pandas** for CSV processing
- **holidays** for public holiday detection

## Project Structure

```
.
├── analyze.py                      # RabbitMQ consumer - orchestrates KPI analysis
├── kpiVerification.py              # KPI validation for SHIFT-based schedules
├── kpiVerification_unified_v3.py   # KPI validation for TIME-SLOT schedules (30min & 1hour)
├── kpiComparison.py                # Multi-schedule comparison
├── requirements.txt                # Python dependencies
│
├── # Legacy files (kept for reference)
├── kpiVerification_HoursLocalv2.py # [DEPRECATED] Use kpiVerification_unified_v3.py
└── kpiVerification_30minLocal.py   # [DEPRECATED] Use kpiVerification_unified_v3.py
```

## Key Files

### `analyze.py`
- RabbitMQ consumer that listens to `comparison-queue`
- **Auto-detects** schedule type (shifts vs time-slots) from CSV content
- Selects appropriate KPI verifier based on schedule type
- Sends results via WebSocket and stores in MongoDB

### `kpiVerification.py`
- Analyzes **shift-based** schedules (M/T/N format)
- Used when cells contain patterns like `M_A`, `T_B`, `N_C`

### `kpiVerification_unified_v3.py`
- Analyzes **time-slot** schedules (both 30-minute and 1-hour granularity)
- Used when cells contain patterns like `9-14-18_A` or `9.5-14.5-18.5_A`
- Unified replacement for the deprecated `*Local*.py` files

### `kpiComparison.py`
- Compares multiple schedules
- Ranks schedules by quality
- Identifies best solution based on KPIs

## How It Works

1. **Listens** to `comparison-queue` via RabbitMQ
2. **Receives** analysis request with schedule ID(s)
3. **Fetches** schedule data from MongoDB
4. **Analyzes** using verification and comparison modules
5. **Calculates** KPIs and quality metrics
6. **Stores** analysis results in MongoDB
7. **Returns** results to API

## KPIs Calculated

### Shift-Based Schedules (`kpiVerification.py`)

| KPI | Description |
|-----|-------------|
| `tmFails` | Number of times an employee works an afternoon shift followed by a morning shift the next day |
| `consecutiveDays` | Number of times employees exceeded the maximum of 5 consecutive working days |
| `workHolidays` | Work days on holidays/Sundays exceeding the threshold of 22 per employee |
| `missedVacationDays` | Total absolute deviation from the target of 30 vacation days per employee |
| `missedWorkDays` | Total absolute deviation from the target of 223 work days per employee |
| `missedTeamMin` | Count of employees below required minimum staffing level per team/shift/day |
| `missedTeamIdeal` | Count of employees below ideal staffing level per team/shift/day |
| `singleTeamViolations` | Employees assigned to one team who worked in other teams |
| `shiftBalance` | Percentage deviation of the most unbalanced shift distribution |
| `teamSatisfactionLevel` | Median work distribution between primary and secondary team |

### Time-Slot Schedules (`kpiVerification_unified_v3.py`)

| KPI | Description |
|-----|-------------|
| `workDaysTargetDeviation` | Total absolute deviation from 223 workdays/year across all employees (0 = everyone has exactly 223 workdays) |
| `vacationDaysQuotaDeviation` | Total absolute deviation from 30 vacation days/year across all employees (0 = everyone has exactly 30 days) |
| `holidayWorkLimitViolations` | Total holiday/weekend workdays beyond the legal limit of 22, summed across employees |
| `consecutiveDaysViolations` | Count of violations where an employee worked 6+ consecutive days without rest |
| `minRestViolations` | Shift transitions where rest time between consecutive days is less than 11 hours |
| `totalStaffingGap` | Total missing staff vs required minimums across all teams, time slots and days |
| `staffingCoverageRate` | Percentage of time slots where minimum staffing was met (100% = all minimums satisfied) |
| `totalIdealGap` | Total missing staff vs ideal levels across all teams, time slots and days (N/A when no ideals provided) |
| `excessStaffing` | Total extra staff beyond required minimums across all teams, time slots and days |

### KPI Interpretation

- **Values of 0** indicate full compliance (good)
- **Higher values** indicate more violations (bad)
- **Percentages** (`staffingCoverageRate`): higher is better
- **N/A**: shown when data is not applicable (e.g., no ideal requirements provided)

## Development

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Locally

```bash
python analyze.py
```

### Local Testing (without RabbitMQ)

```bash
# Test time-slot KPI verification directly
python kpiVerification_unified_v3.py
```

Edit `TestConfig` in the file to configure test parameters:
```python
class TestConfig:
    TEST_30MIN = True   # Enable 30-minute granularity test
    TEST_1HOUR = True   # Enable 1-hour granularity test
    CSV_30MIN = "your_30min_schedule.csv"
    CSV_1HOUR = "your_1hour_schedule.csv"
```

### Run with Docker

```bash
# From project root
make build-analyzer
```

## Configuration

Environment variables (set in docker-compose or locally):
- `RABBITMQ_HOST` - RabbitMQ server address
- `RABBITMQ_USERNAME` - RabbitMQ username
- `RABBITMQ_PASSWORD` - RabbitMQ password
- `MONGODB_URI` - MongoDB connection string

Queue names:
- `comparison-queue` (consume)
- `websocket-exchange` (publish results)

## Integration

- **Input:** Schedule files + requirements from API via RabbitMQ
- **Output:**
  - Real-time results via WebSocket (`websocket-exchange`)
  - Persistent storage in MongoDB (`verifications` and `comparisons` collections)
- **Used by:** Frontend to display schedule quality and comparisons

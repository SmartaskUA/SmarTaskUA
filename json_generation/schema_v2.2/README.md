# JSON + CSV Hybrid Problem Definition System (v2.2)

## What's New in v2.2 🆕

Version 2.2 introduces a **centralized contract system** that eliminates duplication and enables reusable contract definitions with optional constraints:

### Primary Feature: Contract System 🎯

**Before v2.2:** workHoursPerDay duplicated across every employee
```json
"employees": {
  "competency": [
    {"id": "EMP001", "workHoursPerDay": 8},  // Duplicated!
    {"id": "EMP002", "workHoursPerDay": 8},  // Duplicated!
    {"id": "EMP003", "workHoursPerDay": 4}
  ]
}
```

**v2.2:** Define contracts once, reference many times
```json
"contracts": {
  "definitions": [
    {"id": "fullTime_8h", "name": "Full Time", "workHoursPerDay": 8},
    {"id": "partTime_4h", "name": "Part Time", "workHoursPerDay": 4}
  ]
},
"employees": {
  "competency": [
    {"id": "EMP001", "contractType": "fullTime_8h"},  // References contract
    {"id": "EMP002", "contractType": "fullTime_8h"},  // References contract
    {"id": "EMP003", "contractType": "partTime_4h"}   // References contract
  ]
}
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **DRY Principle** | Define contract once, use for multiple employees |
| **Centralized** | All contract logic in one place |
| **Reusable** | Multiple employees share same contract |
| **Extensible** | Easy to add contract constraints (weekendsOnly, etc.) |
| **Maintainable** | Update contract = updates all employees using it |
| **Validatable** | Strong validation of contract references |

### Additional v2.2 Features

| Feature | Description |
|---------|-------------|
| **"A" Auto-Allocation** | "A" in CSV now reads workHoursPerDay from employee's contract |
| **Numeric Hours** | Numbers (1-16) in CSV specify exact hours for that day |
| **Contract Constraints** | Optional: weekendsOnly, maxHoursPerWeek, availableDays, etc. |
| **Contract Evolution** | contractPeriods supports changing contracts over time |

### Example: Contract System in Action

**contracts.json:**
```json
"contracts": {
  "definitions": [
    {
      "id": "fullTime_8h",
      "name": "Full Time - 8 hours/day",
      "workHoursPerDay": 8
    },
    {
      "id": "weekend_6h",
      "name": "Weekend Staff - 6 hours/day",
      "workHoursPerDay": 6,
      "constraints": {
        "weekendsOnly": true,
        "availableDays": ["saturday", "sunday"]
      }
    }
  ]
}
```

**employees.json:**
```json
"employees": {
  "competency": [
    {"id": "EMP001", "contractType": "fullTime_8h"},
    {"id": "EMP002", "contractType": "weekend_6h"}  // Can only work weekends!
  ]
}
```

**schedule_input.csv:**
```csv
employee_id,2025-10-06,2025-10-07,2025-10-08
EMP001,A,8,A
EMP002,DL,DL,A
```

**Interpretation:**
- **EMP001:** Oct-06 = auto (8h from fullTime_8h contract), Oct-07 = exactly 8h, Oct-08 = auto (8h)
- **EMP002:** Oct-06/07 = weekdays (DL = not available due to weekendsOnly constraint), Oct-08 = auto (6h from weekend_6h contract)

---

## Purpose

This directory contains the **hybrid JSON + CSV schema** for defining employee scheduling problems. Version 2.2 builds on v2.1's hybrid approach, adding **contract-based hour allocation** where **JSON contains problem structure and employee contracts**, while **CSV specifies work requirements and constraints**.

### Why Hybrid?

**Problem:** Pure JSON approach (v2.0) requires embedding massive 365-day schedule matrices directly in JSON, making files large, hard to edit, and difficult to validate.

**Solution:** A hybrid architecture that leverages the strengths of both formats:

```
JSON (problem.json)          CSV Files
├─ Problem metadata
├─ Contract definitions      schedule_input.csv (Requirements & Constraints)
├─ Employee list             ├─ Work hour requirements (A, 4, 6, 8)
├─ Priority hierarchy        ├─ Availability constraints (VAC, DL, DLF)
├─ Shifts & competencies     └─ Values: A, 1-16, VAC, DL
├─ Constraints
└─ Optimization settings     demand.csv (Coverage Requirements)
                             ├─ Daily coverage needs
                             └─ Values: minimum, ideal, estimated
```

---

## Design Philosophy

### What Goes in JSON
✅ **Structural data** - Employee definitions, teams, shifts
✅ **Small datasets** - 10-20 employees, optional priority ranks
✅ **Configuration** - Constraints, optimization settings
✅ **Metadata** - Problem ID, dates, feature flags
✅ **Schema-validatable** - Everything that benefits from validation
✅ **v2.2: Contract definitions** - Centralized contracts with workHoursPerDay and constraints

### What Goes in CSV
✅ **schedule_input.csv** - Work requirements and availability constraints
  - When employees should work (A = auto from contract, 4/6/8 = specific hours)
  - When employees are NOT available (VAC, DL, EnfD)
  - Pre-assigned time windows (optional)

✅ **demand.csv** - Daily coverage requirements
  - How many people needed per day/shift/team
  - Minimum (hard), ideal (soft), estimated (KPI)
  - Primary source for all coverage requirements

---

## When to Use v2.2 vs v2.1 vs v2.0

| Use Case | Version | Why |
|----------|---------|-----|
| Contract-based hours | **v2.2 (Hybrid + Contracts)** | Employees have different default hours |
| Variable hour requirements | **v2.2 (Hybrid + Contracts)** | Need specific hours on some days (4h, 6h, 8h) |
| Large problems (365 days) | v2.2 or v2.1 (Hybrid) | Schedule matrix too large for JSON |
| Small problems (<30 days) | v2.0 (Pure JSON) | Everything fits in JSON comfortably |
| Existing Excel schedules | v2.2 or v2.1 (Hybrid) | Easy conversion to CSV |
| API-only workflows | v2.0 (Pure JSON) | No CSV file management needed |

---

## Getting Started

### New Users: Start with Templates
If you're new to the schema, use the templates in `templates/`:
1. Copy `templates/demand_template.csv` and `templates/schedule_input_template.csv`
2. Read the extensive comments in each template
3. Delete comments and fill in your data
4. See `templates/README.md` for step-by-step guide

### Experienced Users: Start from Examples
If you're familiar with the schema, use examples in `examples/`:
1. Check `examples/contract_hours_example/` for v2.2 features (contract hours)
2. Copy and modify for your needs
3. See `examples/README.md` for all available examples

---

## Quick Start (v2.2)

### 1. Create Your Problem JSON

Start with `examples/contract_hours_example/problem.json` and modify:

```json
{
  "schemaVersion": "2.2",
  "problemType": "employee_scheduling",

  "metadata": {
    "problemId": "MY_PROBLEM_2025",
    "createdAt": "2025-01-20T10:00:00Z"
  },

  "contracts": {
    "definitions": [
      {
        "id": "fullTime_8h",
        "name": "Full Time - 8 hours/day",
        "workHoursPerDay": 8
      },
      {
        "id": "partTime_4h",
        "name": "Part Time - 4 hours/day",
        "workHoursPerDay": 4
      }
    ]
  },

  "employees": {
    "model": "competency",
    "competency": [
      {
        "id": "EMP001",
        "name": "John Smith - Full Time",
        "competencies": [{"code": "TeamA", "level": 1}],
        "contractType": "fullTime_8h"
      },
      {
        "id": "EMP002",
        "name": "Jane Doe - Part Time",
        "competencies": [{"code": "TeamA", "level": 2}],
        "contractType": "partTime_4h"
      }
    ]
  },

  "scheduleInput": {
    "enabled": true,
    "dataFile": "schedule_input.csv"
  },

  "demand": {
    "dataFile": "demand.csv"
  }
}
```

**v2.2 Note:** Define contracts first, then reference them via `contractType` in employees

### 2. Create Your Schedule Input CSV (Requirements + Constraints)

Create `schedule_input.csv` with work requirements and constraints:

```csv
employee_id,2025-01-01,2025-01-02,2025-01-03,2025-01-04,...
EMP001,A,8,A,DL,...
EMP002,DL,A,4,A,...
EMP003,6,VAC,VAC,A,...
```

**Column 1:** Employee IDs (must match JSON `employees.id`)
**Columns 2+:** One column per day with values:

**v2.2 Work Requirements:**
- `A` = Auto-allocate from contract (uses workHoursPerDay)
- `4`, `6`, `8`, etc. = Work exactly this many hours (1-16)

**Constraints (unchanged):**
- `DL` = Day off (cannot work)
- `VAC` = Vacation (cannot work)
- `DLF` = Fixed day off (cannot swap)
- `EnfD` = Sick leave (cannot work)
- `NOT` = Unavailable (cannot work)
- `10:00-14:00` = Pre-assigned time window (optional constraint)

**v2.2 Important:** This CSV now contains BOTH work requirements (A, numbers) AND constraints (DL, VAC, etc.)

### 3. Create Your Demand CSV (Requirements)

**Option A: Use the template**
```bash
cp templates/demand_template.csv my_demand.csv
# Edit my_demand.csv, delete comment lines, add your data
```

**Option B: Create from scratch**
```csv
date,shift,team,minimum,ideal,estimated
2025-01-01,M,TeamA,2,3,2
2025-01-01,T,TeamA,2,2,2
2025-01-01,M,TeamB,1,2,1
```

**Purpose:** Tell the algorithm HOW MANY people are needed each day/shift/team

**Note:** The "team" column contains team codes (for team model) or competency codes (for competency model) - same CSV format works for both!

### 4. Validate & Use

```bash
# Validate with v2.2 validator
python3 validator/validator.py problem.json -v

# Use in scheduler
python problem_transformer.py --json problem.json --csv schedule_input.csv
```

---

## File Structure

```
schema_v2.2/
├── README.md                    # This file - overview and quick start
├── FORMAT.md                    # Complete parameter reference (v2.2)
├── schema.json                  # JSON Schema definition (v2.2)
│
├── validator/                   # Validation tools
│   ├── validator.py             # v2.2 validator
│   └── requirements.txt
│
├── templates/                   # CSV templates for users
│   ├── demand_template.csv
│   ├── schedule_input_template.csv
│   └── README.md
│
└── examples/                    # Working examples
    ├── README.md
    └── contract_hours_example/  # v2.2 example with contracts
        ├── problem.json
        ├── demand.csv
        ├── schedule_input.csv
        └── README.md
```

---

## Key Features

### 1. Contract-Based Hour Allocation (v2.2)

Employees have default work hours defined in their contracts:

```json
{
  "employees": {
    "competency": [
      {
        "id": "EMP001",
        "contractType": "fullTime",
        "workHoursPerDay": 8
      },
      {
        "id": "EMP002",
        "contractType": "partTime",
        "workHoursPerDay": 4
      }
    ]
  }
}
```

Use "A" in schedule_input.csv to auto-allocate these hours:
```csv
employee_id,2025-01-01,2025-01-02
EMP001,A,A
EMP002,A,DL
```
Result: EMP001 gets 8 hours both days, EMP002 gets 4 hours on Jan-01

### 2. Specific Hour Requirements (v2.2)

Specify exact hours needed for any day:

```csv
employee_id,2025-01-01,2025-01-02,2025-01-03
EMP001,A,8,6
EMP002,4,A,DL
```

**Interpretation:**
- EMP001: Jan-01=auto (8h), Jan-02=exactly 8h, Jan-03=exactly 6h
- EMP002: Jan-01=exactly 4h, Jan-02=auto (4h), Jan-03=day off

### 3. Team-Based or Competency-Based Employee Model

**Simple/Team Model:**
```json
{
  "employees": {
    "model": "team",
    "simple": [
      {
        "id": "EMP001",
        "name": "John Smith",
        "teams": ["TeamA"],
        "workHoursPerDay": 8
      }
    ]
  }
}
```

**Competency Model:**
```json
{
  "employees": {
    "model": "competency",
    "competency": [
      {
        "id": "EMP001",
        "competencies": [
          {"code": "Management", "level": 1}
        ],
        "contractType": "fullTime",
        "workHoursPerDay": 8
      }
    ]
  }
}
```

### 4. Optional Priority Hierarchy

Priority hierarchy works for both team and competency models:

**For Team Model:**
```json
{
  "demand": {
    "priorityHierarchy": [
      {
        "rank": 1,
        "team": "TeamA",
        "description": "Critical operations"
      }
    ]
  }
}
```

**For Competency Model:**
```json
{
  "demand": {
    "priorityHierarchy": [
      {
        "rank": 1,
        "competency": "Management",
        "level": "N=1",
        "description": "Management team priority"
      }
    ]
  }
}
```

### 5. Two CSV Files for Different Purposes

**schedule_input.csv** - Work requirements and constraints:
- **v2.2:** Work hours (A = auto, numbers = specific)
- Availability constraints (VAC, DL, DLF, EnfD)
- One row per employee, one column per day

**demand.csv** - Daily coverage requirements:
- How many people needed each day
- Values: `minimum`, `ideal`, `estimated` numbers
- One row per day/shift/team combination

---

## Differences from v2.1

| Feature | v2.1 | v2.2 |
|---------|------|------|
| Schema version | `"2.1"` | `"2.2"` |
| "A" in schedule_input.csv | Available (constraint) | Auto-allocate from contract |
| Numbers in schedule_input.csv | Invalid (error) | Valid (specific hours 1-16) |
| workHoursPerDay field | Not present | New field in employee definitions |
| Contract defaults | N/A | 8h for fullTime, 4h for partTime |
| Mixed hour allocation | Not supported | Supported (mix A and numbers) |

---

## Differences from v2.0

| Feature | v2.0 (Pure JSON) | v2.2 (Hybrid + Contracts) |
|---------|------------------|---------------------------|
| Schedule constraints | In JSON as arrays | In schedule_input.csv |
| Work hour specification | Not supported | **v2.2: A and numbers in CSV** |
| Contract hours | Not supported | **v2.2: workHoursPerDay in JSON** |
| Demand requirements | In JSON as arrays | In demand.csv (optional) |
| File count | 1 (JSON only) | 2-3 (JSON + CSVs) |
| Max problem size | ~30 days practical | 365+ days no problem |
| Excel compatibility | Requires conversion | Direct CSV export |
| Human editing | Difficult (nested arrays) | Easy (open CSVs in Excel) |

---

## Example: From Excel to Hybrid (v2.2)

**Excel Input (2030Exemplo2.xlsx):**
- Sheet1: Employee schedules (ID, Name, Teams, Contract Hours, 31 day columns)
- Sheet2: Coverage requirements per day/shift/team

**Hybrid Output:**
- `problem.json`: Employees with workHoursPerDay, teams, shifts, constraints
- `schedule_input.csv`: Work requirements (A, 4, 6, 8) and constraints (VAC, DL per employee/day)
- `demand.csv`: Daily requirements (minimum/ideal/estimated per day/shift/team)

---

## Validation

### Comprehensive Validator Tool (v2.2)

We provide a comprehensive validator that checks JSON and both CSV files for consistency:

```bash
python3 validator/validator.py path/to/problem.json -v
```

The validator performs:
- **JSON validation** against schema.json (v2.2)
- **CSV format validation** (dates, columns, values)
- **v2.2: Numeric value validation** (1-16 hours)
- **v2.2: Contract validation** (workHoursPerDay when "A" is used)
- **Cross-validation** (employee IDs, shift codes, date ranges match)

**Quick validation:**
```bash
# Install dependencies
pip install -r validator/requirements.txt

# Validate a problem
python3 validator/validator.py examples/contract_hours_example/problem.json

# Verbose output with statistics
python3 validator/validator.py examples/contract_hours_example/problem.json -v

# JSON output for automation
python3 validator/validator.py examples/contract_hours_example/problem.json --json
```

---

## Benefits of v2.2

✅ **Contract-based allocation** - Auto-allocate hours from employee contracts
✅ **Specific hour requirements** - Specify exact hours (4, 6, 8) when needed
✅ **Flexible scheduling** - Mix auto (A) and specific hours in same schedule
✅ **Part-time support** - Different employees have different default hours
✅ **Excel-friendly** - Easy conversion from existing spreadsheets
✅ **Scalable** - Handles 365-day problems without bloat
✅ **Validatable** - JSON schema validation + CSV format checks
✅ **Maintainable** - Edit schedules in Excel, contracts in JSON

---

## Migration from v2.1

If you have existing v2.1 files and want to use v2.2 features:

1. **Update schemaVersion** from `"2.1"` to `"2.2"` in JSON
2. **Add workHoursPerDay** to employees:
   ```json
   "competency": [
     {
       "id": "EMP001",
       "contractType": "fullTime",
       "workHoursPerDay": 8  // Add this
     }
   ]
   ```
3. **Review schedule_input.csv:**
   - "A" now means "auto-allocate from contract" (not just "available")
   - You can now use numbers (1-16) for specific hours
4. **Optional:** Replace some "A" values with specific hours (4, 6, 8) where needed

**Note:** v2.1 files still work in v2.2 if you:
- Don't use numeric values in schedule_input.csv
- Don't use "A" with the expectation of auto-allocation

---

## Migration from v2.0

If you have existing v2.0 JSON files with embedded schedule data:

1. Extract `scheduleInput.employeeSchedules` from JSON
2. Convert to CSV format (employee_id, date columns)
3. Add `workHoursPerDay` to employee definitions
4. Update CSV values to use "A" for auto-allocation
5. Remove `scheduleInput.employeeSchedules` from JSON
6. Add `scheduleInput.dataFile` reference
7. Update `schemaVersion` to `"2.2"`

---

## Next Steps

1. Review `FORMAT.md` for complete parameter reference (v2.2)
2. Study `examples/contract_hours_example/` for v2.2 features
3. Examine `schedule_input.csv` format with "A" and numbers
4. Create your own problem JSON + CSV with workHoursPerDay
5. Validate with v2.2 validator

---

## Based On

- Schema v2.1 (hybrid JSON + CSV approach)
- Schema v2.0 (pure JSON approach)
- Real-world Excel files (2030Exemplo2.xlsx)
- User feedback on contract-based hour allocation
- Best practices for flexible scheduling

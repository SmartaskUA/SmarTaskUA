# JSON + CSV Hybrid Problem Definition System (v2.1)

## Purpose

This directory contains the **hybrid JSON + CSV schema** for defining employee scheduling problems. Version 2.1 introduces a pragmatic approach where **JSON contains problem structure and metadata**, while **CSV contains large tabular schedule data**.

### Why Hybrid?

**Problem:** Pure JSON approach (v2.0) requires embedding massive 365-day schedule matrices directly in JSON, making files large, hard to edit, and difficult to validate.

**Solution:** A hybrid architecture that leverages the strengths of both formats:

```
JSON (problem.json)          CSV Files
├─ Problem metadata
├─ Employee list             schedule_input.csv (Constraints)
├─ Priority hierarchy        ├─ Availability constraints
├─ Shifts & competencies     └─ Values: A, VAC, DL, DLF
├─ Constraints
└─ Optimization settings     demand.csv (Requirements)
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

### What Goes in CSV
✅ **schedule_input.csv** - Employee availability constraints
  - When employees are NOT available (VAC, DL, EnfD)
  - Pre-assigned time windows (optional)
  - NOT work assignments (those are algorithm outputs)

✅ **demand.csv** - Daily coverage requirements
  - How many people needed per day/shift/team
  - Minimum (hard), ideal (soft), estimated (KPI)
  - Primary source for all coverage requirements

---

## When to Use v2.1 vs v2.0

| Use Case | Version | Why |
|----------|---------|-----|
| Small problems (<30 days) | v2.0 (Pure JSON) | Everything fits in JSON comfortably |
| Large problems (365 days) | **v2.1 (Hybrid)** | Schedule matrix too large for JSON |
| Existing Excel schedules | **v2.1 (Hybrid)** | Easy conversion to CSV |
| API-only workflows | v2.0 (Pure JSON) | No CSV file management needed |
| Human editing required | **v2.1 (Hybrid)** | CSV is easier to edit than JSON arrays |

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
1. Check `examples/team_based_october_2030/` for a complete working example
2. Copy and modify for your needs
3. See `examples/README.md` for all available examples

---

## Quick Start

### 1. Create Your Problem JSON

Start with `examples/team_based_october_2030/problem.json` and modify:

```json
{
  "schemaVersion": "2.1",
  "problemType": "employee_scheduling",

  "metadata": {
    "problemId": "MY_PROBLEM_2025",
    "createdAt": "2025-01-20T10:00:00Z"
  },

  "employees": {
    "model": "team",
    "simple": [
      {
        "id": "EMP001",
        "name": "John Smith",
        "teams": ["TeamA"]
      },
      {
        "id": "EMP002",
        "name": "Jane Doe",
        "teams": ["TeamA", "TeamB"]
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

### 2. Create Your Schedule Input CSV (Constraints)

Create `schedule_input.csv` with employee availability constraints:

```csv
employee_id,2025-01-01,2025-01-02,2025-01-03,...
EMP001,A,A,DL,...
EMP002,DL,A,A,...
EMP003,A,VAC,VAC,...
```

**Column 1:** Employee IDs (must match JSON `employees.id`)
**Columns 2+:** One column per day with values:
- `A` = Available (algorithm can assign work)
- `DL` = Day off (cannot work)
- `VAC` = Vacation (cannot work)
- `DLF` = Fixed day off (cannot swap)
- `EnfD` = Sick leave (cannot work)
- `10:00-14:00` = Pre-assigned time window (optional constraint)

**Important:** This CSV contains INPUT CONSTRAINTS, not work assignments. Work hours are the algorithm's OUTPUT.

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
# Validate JSON schema
jsonschema -i problem.json schema.json

# Use in scheduler
python problem_transformer.py --json problem.json --csv schedule_input.csv
```

---

## File Structure

```
schema_v2.1/
├── README.md                    # This file - overview and quick start
├── FORMAT.md                    # Complete parameter reference
├── schema.json                  # JSON Schema definition
│
├── templates/                   # CSV templates for users
│   ├── demand_template.csv
│   ├── schedule_input_template.csv
│   └── README.md
│
└── examples/                    # Working examples
    ├── README.md
    └── team_based_october_2030/
        ├── problem.json
        ├── demand.csv
        ├── schedule_input.csv
        └── README.md
```

---

## Key Features

### 1. Team-Based Employee Model
Employees are defined in JSON with simple team membership:
- Typical problems have 10-20 employees (manageable size)
- Employee data includes team assignments
- Benefits from schema validation
- Easy to understand and maintain

```json
{
  "employees": {
    "model": "team",
    "simple": [
      {
        "id": "EMP001",
        "name": "John Smith",
        "teams": ["TeamA"]
      },
      {
        "id": "EMP002",
        "name": "Jane Doe",
        "teams": ["TeamA", "TeamB"]
      }
    ]
  }
}
```

### 2. Optional Priority Hierarchy
Priority hierarchy is optional and works for both team and competency models:
- Only ~10 entries (not large)
- Enable with `features.usePriorityHierarchy: true`
- Defines which teams/competencies get staffed first when resources are scarce
- Benefits from validation

**For Team Model:**
```json
{
  "demand": {
    "priorityHierarchy": [
      {
        "rank": 1,
        "team": "TeamA",
        "description": "Critical operations - highest priority"
      },
      {
        "rank": 2,
        "team": "TeamB",
        "description": "Support - medium priority"
      }
    ]
  }
}
```

### 3. Two CSV Files for Different Purposes

**schedule_input.csv** - Employee availability constraints:
- When employees are NOT available
- Values: `A` (available), `VAC`, `DL`, `DLF`, `EnfD`
- **NOT** work assignments (those are algorithm outputs)
- One row per employee, one column per day

**demand.csv** - Daily coverage requirements:
- How many people needed each day
- Values: `minimum`, `ideal`, `estimated` numbers
- One row per day/shift/team combination
- Primary source for all coverage requirements

### 4. Schema References to CSVs
JSON references both CSV files:

```json
{
  "scheduleInput": {
    "enabled": true,
    "dataFile": "schedule_input.csv",
    "markingTypes": {
      "DL": "Day Off - Day off",
      "VAC": "Vacation"
    }
  },
  "demand": {
    "dataFile": "demand.csv"
  }
}
```

---

## Differences from v2.0

| Feature | v2.0 (Pure JSON) | v2.1 (Hybrid) |
|---------|------------------|---------------|
| Schedule constraints | In JSON as arrays | In schedule_input.csv |
| Demand requirements | In JSON as arrays | In demand.csv (optional) |
| File count | 1 (JSON only) | 2-3 (JSON + CSVs) |
| Max problem size | ~30 days practical | 365+ days no problem |
| Excel compatibility | Requires conversion | Direct CSV export |
| Schema validation | Full validation | JSON validated, CSV format checked |
| Human editing | Difficult (nested arrays) | Easy (open CSVs in Excel) |

---

## Example: From Excel to Hybrid

**Excel Input (2030Exemplo2.xlsx):**
- Sheet1: Employee schedules (ID, Name, Teams, 31 day columns with availability)
- Sheet2: Coverage requirements per day/shift/team

**Hybrid Output:**
- `problem.json`: Employees, teams, shifts, constraints, optimization settings
- `schedule_input.csv`: Availability constraints (A, VAC, DL per employee/day)
- `demand.csv`: Daily requirements (minimum/ideal/estimated per day/shift/team)

---

## Validation

### JSON Validation
```bash
jsonschema -i problem.json schema.json
```

### CSV Validation
The transformer validates:
- Employee IDs match between JSON and CSV
- Date format is consistent (YYYY-MM-DD)
- Values are valid (numbers, DL, VAC, time ranges)
- Number of columns matches temporal scope

---

## Benefits of Hybrid Approach

✅ **Practical** - JSON for structure, CSV for data
✅ **Excel-friendly** - Easy conversion from existing spreadsheets
✅ **Scalable** - Handles 365-day problems without bloat
✅ **Validatable** - JSON schema validation still works
✅ **Maintainable** - Edit schedules in Excel, metadata in JSON
✅ **Flexible** - Can generate demand CSVs if needed

---

## Migration from v2.0

If you have existing v2.0 JSON files with embedded schedule data:

1. Extract `scheduleInput.employeeSchedules` from JSON
2. Convert to CSV format (employee_id, date columns)
3. Remove `scheduleInput.employeeSchedules` from JSON
4. Add `scheduleInput.dataFile` reference
5. Update `schemaVersion` to `"2.1"`

---

## Next Steps

1. Review `FORMAT.md` for complete parameter reference
2. Study `problem_example.json` for real-world example
3. Examine `schedule_input.csv` format
4. Create your own problem JSON + CSV
5. Validate with schema.json

---

## Based On

- Schema v2.0 (pure JSON approach)
- Real-world Excel files (2030Exemplo2.xlsx)
- Feedback on practicality of large JSON arrays
- Best practices for hybrid data formats

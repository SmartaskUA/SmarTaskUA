# JSON + CSV Hybrid Problem Definition System (v2.5)

## What's New in v2.5 🆕

Version 2.5 introduces **operating hours management** that defines when facilities/teams are open for business:

### Primary Feature: Operating Hours 🎯

**The Problem:** Previous versions had no way to specify when the store/facility is actually open. This led to:
- ❌ Potentially scheduling employees outside business hours
- ❌ No distinction between facility hours and work period availability
- ❌ Inability to model team-specific hours (e.g., storage opens earlier)

**v2.5 Solution:** Dedicated `operating_hours.csv` file

```csv
date,team,open,close
2025-10-01,ALL,08:00,22:00
2025-10-02,Storage,06:00,23:00
2025-10-02,Checkout,08:00,22:00
2025-12-25,ALL,10:00,16:00
2025-12-26,ALL,CLOSED,CLOSED
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Explicit Hours** | Clear definition of when facility is open |
| **Hard Constraints** | Algorithm enforces operating hours (no work when closed) |
| **Team-Specific** | Different departments can have different hours |
| **Holiday Support** | CLOSED days for holidays or special events |
| **Validation** | Prevents invalid schedules outside operating hours |

### v2.5 Features

| Feature | Description |
|---------|-------------|
| **operating_hours.csv** | date,team,open,close format (4 columns) |
| **Complete Coverage** | Must define hours for all dates in temporal scope |
| **Team Override** | Specific teams override ALL (store-wide) hours |
| **CLOSED Support** | Use CLOSED,CLOSED for non-operating days |
| **Hard/Soft Enforcement** | Choose strict (hard) or preferential (soft) enforcement |

### Example: Operating Hours in Action

**problem.json:**
```json
{
  "schemaVersion": "2.5",
  "operatingHours": {
    "enabled": true,
    "dataFile": "operating_hours.csv",
    "enforcement": "hard"
  }
}
```

**operating_hours.csv:**
```csv
date,team,open,close
2025-10-01,ALL,08:00,22:00
2025-10-02,Storage,06:00,23:00
2025-10-02,Checkout,08:00,22:00
```

**Result:**
- Oct-01: All teams 08:00-22:00
- Oct-02: Storage opens early (06:00), Checkout normal hours
- Algorithm cannot schedule employees outside these hours

---

## What's New in v2.2 (Previous Release)

Version 2.2 introduced a **centralized contract system** that eliminates duplication and enables reusable contract definitions with optional constraints:

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
├─ Shifts & teams            └─ Values: A, 1-16, VAC, DL
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
  - When employees are NOT available (VAC, NOT, custom constraints)
  - Time window constraints (EQUALS/INCLUDE/EXCEPT with Allen Interval Algebra)

✅ **demand.csv** - Daily coverage requirements
  - How many people needed per day/shift/team
  - Minimum (hard), ideal (soft), estimated (KPI)
  - Primary source for all coverage requirements

---

## When to Use v2.5 vs v2.2 vs v2.1 vs v2.0

| Use Case | Version | Why |
|----------|---------|-----|
| **Operating hours constraints** | **v2.5 (Latest)** | Need to enforce store/facility operating hours |
| **Team-specific hours** | **v2.5 (Latest)** | Different departments have different operating hours |
| Contract-based hours | v2.5 or v2.2 | Employees have different default hours (v2.2 feature) |
| Variable hour requirements | v2.5 or v2.2 | Need specific hours on some days (v2.2 feature: 4h, 6h, 8h) |
| Large problems (365 days) | v2.5, v2.2, or v2.1 | Schedule matrix too large for JSON |
| Small problems (<30 days) | v2.0 (Pure JSON) | Everything fits in JSON comfortably |
| Existing Excel schedules | v2.5, v2.2, or v2.1 | Easy conversion to CSV |
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
        "teams": [{"code": "TeamA", "name": "Team A", "level": 1}],
        "contractType": "fullTime_8h"
      },
      {
        "id": "EMP002",
        "name": "Jane Doe - Part Time",
        "teams": [{"code": "TeamA", "name": "Team A", "level": 2}],
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

**Standard Constraints (always valid):**
- `VAC` = Vacation (cannot work)
- `NOT` = Unavailable (cannot work)

**Custom Constraints (must be defined in scheduleInput.markingTypes):**
- `DL` = Day off (example custom constraint)
- `DLF` = Fixed day off (example custom constraint)
- `EnfD` = Sick leave (example custom constraint)
- Any project-specific codes you define

**Time Window Constraints (Allen Interval Algebra):**
- `EQUALS:08:00-16:00` = Must work exactly 8 AM-4 PM
- `INCLUDE:09:00-17:00` = Must cover 9 AM-5 PM minimum
- `EXCEPT:14:00-22:00` = Cannot work 2 PM-10 PM

**v2.2 Important:** This CSV now contains BOTH work requirements (A, numbers) AND constraints (DL, VAC, etc.)

### 3. Create Your Demand CSV (Requirements)

**Option A: Use the template**
```bash
cp templates/demand_template.csv my_demand.csv
# Edit my_demand.csv, delete comment lines, add your data
```

**Option B: Create from scratch**
```csv
date,workPeriod,team,minimum,ideal,estimated
2025-01-01,M,TeamA,2,3,2
2025-01-01,T,TeamA,2,2,2
2025-01-01,M,TeamB,1,2,1
```

**Purpose:** Tell the algorithm HOW MANY people are needed each day/shift/team

**Note:** The "team" column always contains team codes for both employee models. In the competency-based model, employees are assigned to teams with proficiency levels, but demand is specified at the team level only (not per level).

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
schema_v2.5/
├── README.md                       # This file - overview and quick start
├── FORMAT.md                       # Complete parameter reference (v2.5)
├── schema.json                     # JSON Schema definition (v2.5)
│
├── validator/                      # Validation tools
│   ├── validator.py                # v2.5 validator with operating hours support
│   └── requirements.txt
│
├── templates/                      # CSV templates for users
│   ├── demand_template.csv
│   ├── schedule_input_template.csv
│   ├── operating_hours_template.csv  # NEW in v2.5
│   └── README.md
│
└── examples/                       # Working examples
    ├── README.md
    ├── sisqual_example/            # v2.5 example with operating hours
    │   ├── problem.json
    │   ├── demand.csv
    │   ├── schedule_input.csv
    │   ├── operating_hours.csv     # NEW in v2.5
    │   └── README.md
    └── time_constraints_example/   # v2.5 time window example
        ├── problem.json
        ├── operating_hours.csv     # NEW in v2.5
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

Both models use **teams**, but differ in how team assignments work:

**Team-Based Model:**
- Employees are assigned to teams as simple codes
- Teams represent departments, groups, or work areas
```json
{
  "employees": {
    "model": "team",
    "simple": [
      {
        "id": "EMP001",
        "name": "John Smith",
        "teams": ["TeamA", "TeamB"],
        "contractType": "fullTime_8h"
      }
    ]
  }
}
```

**Competency-Based Model:**
- Employees are assigned to teams with **competency levels**
- Levels indicate proficiency/expertise (e.g., 1=junior, 2=mid, 3=senior)
- Enables skill-based scheduling and training progression
```json
{
  "employees": {
    "model": "competency",
    "competency": [
      {
        "id": "EMP001",
        "name": "John Smith",
        "teams": [
          {"code": "Engineering", "name": "Engineering Team", "level": 2},
          {"code": "Support", "name": "Support Team", "level": 1}
        ],
        "contractType": "fullTime_8h"
      }
    ]
  }
}
```

### 4. Optional Priority Hierarchy

Priority hierarchy defines team assignment preferences for both employee models:

**For Team-Based Model:**
```json
{
  "demand": {
    "priorityHierarchy": [
      {
        "rank": 1,
        "team": "Engineering",
        "description": "Engineering team has highest priority"
      },
      {
        "rank": 2,
        "team": "Support",
        "description": "Support team secondary priority"
      }
    ]
  }
}
```

**For Competency-Based Model:**
- Priority hierarchy uses the same `team` field
- Optionally specify `level` to prioritize by competency level
```json
{
  "demand": {
    "priorityHierarchy": [
      {
        "rank": 1,
        "team": "Engineering",
        "level": "N>=2",
        "description": "Senior engineers (level 2+) highest priority"
      },
      {
        "rank": 2,
        "team": "Engineering",
        "description": "All engineering levels secondary priority"
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

## Differences Between Versions

| Feature | v2.1 | v2.2 | v2.5 |
|---------|------|------|------|
| Schema version | `"2.1"` | `"2.2"` | `"2.5"` |
| Operating hours | Not available | Not available | **New:** operating_hours.csv |
| Team-specific hours | N/A | N/A | **New:** Supported via CSV |
| "A" in schedule_input.csv | Available (constraint) | Auto-allocate from contract | Same as v2.2 |
| Numbers in schedule_input.csv | Invalid (error) | Valid (specific hours 1-16) | Same as v2.2 |
| workHoursPerDay field | Not present | New field | Same as v2.2 |
| Contract defaults | N/A | 8h for fullTime, 4h for partTime | Same as v2.2 |
| CSV files | 2 (schedule, demand) | 2 (schedule, demand) | **3 (+ operating_hours)** |

---

## Differences from v2.0 (Pure JSON)

| Feature | v2.0 | v2.5 |
|---------|------|------|
| Operating hours | Not supported | **operating_hours.csv** |
| Schedule constraints | In JSON as arrays | In schedule_input.csv |
| Work hour specification | Not supported | A and numbers in CSV (v2.2) |
| Contract hours | Not supported | workHoursPerDay in JSON (v2.2) |
| Demand requirements | In JSON as arrays | In demand.csv |
| File count | 1 (JSON only) | 3-4 (JSON + CSVs) |
| Max problem size | ~30 days practical | 365+ days no problem |
| Excel compatibility | Requires conversion | Direct CSV export |
| Human editing | Difficult (nested arrays) | Easy (open CSVs in Excel) |

---

## Example: From Excel to Hybrid (v2.5)

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
- **Cross-validation** (employee IDs, work period codes, date ranges match)

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
2. **Add contracts and update employees:**
   ```json
   "contracts": {
     "definitions": [
       {"id": "fullTime", "name": "Full Time", "workHoursPerDay": 8}
     ]
   },
   "employees": {
     "competency": [
       {
         "id": "EMP001",
         "teams": [{"code": "TeamA", "name": "Team A", "level": 1}],
         "contractType": "fullTime"
       }
     ]
   }
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

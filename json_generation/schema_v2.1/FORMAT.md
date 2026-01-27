# JSON + CSV Hybrid Format Reference (v2.1)

Quick reference guide for the hybrid scheduling problem format.

---

## Root Structure (JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemaVersion` | string | ✓ | Must be `"2.1"` |
| `problemType` | string | ✓ | Must be `"employee_scheduling"` |
| `metadata` | object | ✓ | Problem identification |
| `features` | object | - | Feature flags (defaults to all false) |
| `temporalScope` | object | ✓ | Time period definition |
| `employees` | object | ✓ | Employee definitions |
| `demand` | object | ✓ | Coverage requirements |
| `scheduleInput` | object | - | Reference to CSV schedule data |
| `constraints` | object | ✓ | Hard and soft constraints |
| `optimization` | object | ✓ | Algorithm and objectives |

---

## Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `problemId` | string | ✓ | Unique problem identifier |
| `createdAt` | ISO 8601 | ✓ | Creation timestamp |
| `description` | string | - | Human-readable description |
| `source` | string | - | Source document reference |

**Example:**
```json
{
  "metadata": {
    "problemId": "2030_OCTOBER_SCHEDULE",
    "createdAt": "2025-01-20T10:00:00Z",
    "description": "October 2030 employee scheduling",
    "source": "2030Exemplo2.xlsx"
  }
}
```

---

## Feature Flags

Controls which optional modules are enabled:

| Feature | Default | Description |
|---------|---------|-------------|
| `useShiftBasedScheduling` | true | Enable shift-based (true) or interval-based (false) scheduling |
| `useAdvancedConstraints` | false | Enable day-off swapping, breaks, etc. |
| `usePriorityHierarchy` | false | Enable priority-based allocation ordering |

**Example:**
```json
{
  "features": {
    "useShiftBasedScheduling": true,
    "useAdvancedConstraints": false,
    "usePriorityHierarchy": true
  }
}
```

---

## Temporal Scope

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `year` | integer | ✓ | Scheduling year |
| `numDays` | integer | ✓ | Number of days (typically 365) |
| `targetPeriod` | object | - | Primary scheduling window |
| `targetPeriod.start` | ISO date | - | Start date (YYYY-MM-DD) |
| `targetPeriod.end` | ISO date | - | End date (YYYY-MM-DD) |

**Example:**
```json
{
  "temporalScope": {
    "year": 2030,
    "numDays": 31,
    "targetPeriod": {
      "start": "2030-10-01",
      "end": "2030-10-31"
    }
  }
}
```

---

## Employees (JSON)

### Model Selection
```json
"employees": {
  "model": "team" | "competency"
}
```

### Simple Model (model="team")
```json
"simple": [
  {
    "id": "EMP001",
    "name": "John Smith",
    "teams": ["A", "B"]
  }
]
```

### Competency Model (model="competency")
```json
"competency": [
  {
    "id": "20072412",
    "name": "Emp_20072412",
    "competencies": [
      {"code": "EG", "level": 1, "description": "Management level 1"},
      {"code": "CAJ", "level": 2, "description": "Cashier level 2"}
    ],
    "contractType": "fullTime" | "partTime",
    "contractPeriods": [
      {"start": "2024-01-01", "end": null}
    ],
    "restrictions": {
      "cannotSwapDayOffs": false,
      "preferredShifts": ["M"],
      "blackoutDates": []
    }
  }
]
```

**Key Notes:**
- `id` must be unique and match CSV employee_id column
- `competencies.level`: 1 = highest skill, higher numbers = lower skill
- `unavailability` is optional (can also come from CSV)

---

## Demand Requirements

### Shift Model Selection

```json
"demand": {
  "shiftModel": "fixed" | "flexible"
}
```

| Model | Description | Use Case |
|-------|-------------|----------|
| **fixed** | Predefined shifts with fixed times | Traditional shift work (most common) |
| **flexible** | Shifts with multiple start time options | Variable start times within constraints |

### Organizational Units
```json
"organizationalUnits": {
  "teams": ["A", "B"],  // for team model
  "competencies": [     // for competency model
    {"code": "EG", "name": "Management Team"},
    {"code": "CAJ", "name": "Cashier"},
    {"code": "ALM", "name": "Warehouse"}
  ]
}
```

### Shift Definitions (Fixed Model)
```json
"shifts": [
  {
    "code": "M",
    "name": "Morning",
    "order": 1,
    "timeRange": {
      "start": "08:30",
      "end": "16:30"
    },
    "breaks": [
      {
        "type": "meal",
        "duration": 30,
        "timing": {
          "mode": "window",
          "window": {"start": "12:00", "end": "14:30"}
        },
        "paid": false,
        "required": true,
        "canStagger": true
      }
    ]
  }
]
```

### Priority Hierarchy (Optional)

**Available for both simple and competency models**. Enable with `features.usePriorityHierarchy=true`.

**For Simple/Team Model:**
```json
"priorityHierarchy": [
  {
    "rank": 1,
    "team": "ALM",
    "description": "Warehouse operations - Highest priority"
  },
  {
    "rank": 2,
    "team": "EG",
    "description": "Management Team - Medium priority"
  },
  {
    "rank": 3,
    "team": "CAJ",
    "description": "Cashier - Standard priority"
  }
]
```

**Purpose:** When resources are scarce, ensure higher-rank teams meet minimums first before allocating to lower-rank teams.

**For Competency Model:**
```json
"priorityHierarchy": [
  {
    "rank": 1,
    "competency": "ALM",
    "level": "N≥1",
    "description": "RESP WAREHOUSE N≥1 MaxAlarm"
  },
  {
    "rank": 2,
    "competency": "EG",
    "level": "N=1",
    "description": "RESP - MANAGEMENT TEAM N=1"
  }
]
```

**Purpose:** Defines allocation order for multi-skilled employees - fill high-priority competency requirements first.

---

## Schedule Input (CSV Reference)

### JSON Configuration
```json
"scheduleInput": {
  "enabled": true,
  "dataFile": "schedule_input.csv",  // Path relative to JSON file
  "markingTypes": {
    "DL": "Day Off - Generic day off",
    "DLF": "Fixed day off (cannot change)",
    "DLV": "Variable day off (can swap)",
    "VAC": "Vacation",
    "EnfD": "Sick leave",
    "WORK": "Work shift"
  }
}
```

### CSV Format (schedule_input.csv)

**Purpose:** INPUT CONSTRAINTS ONLY - tells algorithm when employees are NOT available

**Structure:**
```csv
employee_id,YYYY-MM-DD,YYYY-MM-DD,YYYY-MM-DD,...
EMP001,A,A,DL,...
EMP002,DL,A,A,...
EMP003,VAC,VAC,VAC,...
```

**Column 1: employee_id**
- Must match `employees[].id` in JSON
- String format (e.g., "20072412", "EMP001")

**Columns 2+: Date columns**
- Header format: `YYYY-MM-DD` (e.g., "2030-10-01")
- One column per day in temporal scope
- Number of columns = `temporalScope.numDays`

**Cell Values (CONSTRAINTS ONLY):**
- **`A`** = Available (algorithm can assign work)
- **`DL`** = Day off (cannot work)
- **`DLF`** = Fixed day off (cannot work, cannot swap)
- **`DLV`** = Variable day off (can swap within week)
- **`VAC`** = Vacation (cannot work)
- **`EnfD`** = Sick leave (cannot work)
- **`DC-E`** = Special constraint
- **`10:00-14:00`** = Pre-assigned time window (optional constraint)

**IMPORTANT:** Do NOT use work hours (4, 5, 8) - those are algorithm OUTPUTS, not inputs!

**Example CSV:**
```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
20072412,A,A,A,DL,A
20066543,DL,A,A,A,DL
20067009,DL,A,DL,A,A
20062688,A,VAC,VAC,VAC,VAC
```

**Validation Rules:**
1. First column must be named `employee_id`
2. All employee IDs must exist in JSON
3. Date columns must be consecutive and match `temporalScope`
4. Values must be valid: A, DL, DLF, DLV, VAC, EnfD, DC-E, or time ranges
5. No duplicate employee IDs

---

## Demand Requirements (CSV Format)

### JSON Configuration
```json
"demand": {
  "shiftModel": "fixed",
  "dataFile": "demand.csv",
  "organizationalUnits": {
    "teams": ["TeamA", "TeamB", "TeamC"]
  },
  "shifts": [
    {"code": "M", "name": "Morning", "timeRange": {"start": "08:30", "end": "16:30"}},
    {"code": "T", "name": "Afternoon", "timeRange": {"start": "14:00", "end": "22:00"}}
  ],
  "priorityHierarchy": [  // Optional
    {"rank": 1, "team": "TeamA", "description": "Highest priority"},
    {"rank": 2, "team": "TeamB", "description": "Medium priority"}
  ]
}
```

**Note**: The employee model (`employees.model` = "team" or "competency") determines how the "team" column in demand.csv is interpreted. Same CSV format works for both!

### CSV Format (demand.csv)

**Purpose:** Daily coverage requirements - tells algorithm HOW MANY people are needed each day

**Structure:**
```csv
date,shift,team,minimum,ideal,estimated
2030-10-01,M,TeamA,2,3,2
2030-10-01,T,TeamA,2,2,2
2030-10-01,M,TeamB,1,2,1
```

**Column Specifications:**

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `date` | ISO date | Date for this requirement | `2030-10-01` |
| `shift` | string | Shift code (must match shifts[].code in JSON) | `M`, `T`, `N` |
| `team` | string | Team identifier (must match organizationalUnits.teams[] in JSON) | `TeamA`, `TeamB` |
| `minimum` | integer | Minimum people required (hard constraint) | `1`, `2`, `3` |
| `ideal` | integer | Ideal number of people (soft target) | `2`, `3`, `4` |
| `estimated` | integer | Estimated/expected demand (for KPI analysis) | `1`, `2`, `3` |

**Example CSV:**
```csv
date,shift,team,minimum,ideal,estimated
2030-10-01,M,EG,1,2,1
2030-10-01,T,EG,1,1,1
2030-10-01,M,CAJ,2,3,2
2030-10-01,T,CAJ,2,4,3
2030-10-04,M,EG,1,1,1
2030-10-04,M,CAJ,1,2,1
```

**Validation Rules:**
1. All dates must be within `temporalScope.targetPeriod`
2. Shift codes must exist in `demand.shifts[].code`
3. Team codes must exist in `demand.organizationalUnits.teams[]`
4. `minimum ≤ estimated ≤ ideal` (logical constraint)
5. No duplicate rows (same date/shift/team combination)

**Usage Notes:**
- **Simple Model**: CSV is the primary and only source of coverage requirements
- **All Days Required**: Must provide coverage requirements for every day in temporal scope
- **Flexibility**: Easy to edit in Excel for day-by-day adjustments
- **KPI Analysis**: `estimated` column used for post-generation comparison

---

## Constraints

### Hard Constraints (must be satisfied)
```json
"hard": [
  {
    "id": "max-consecutive-days",
    "type": "max_consecutive_days",
    "params": {"window": 6, "max_worked": 5},
    "enabled": true
  },
  {
    "id": "min-rest-hours",
    "type": "min_rest_hours",
    "params": {"hours": 11},
    "enabled": true
  }
]
```

**Common Constraint Types:**
- `max_consecutive_days` - Max work days in rolling window
- `total_workdays` - Annual workday limits (min/max)
- `max_special_days` - Max Sundays/holidays per year
- `no_earlier_shift_next_day` - No backward shift transitions
- `min_rest_hours` - Minimum rest between shifts
- `vacation_block` - Vacation days cannot be worked

### Soft Constraints (with penalties)
```json
"soft": [
  {
    "id": "min-coverage",
    "type": "min_coverage",
    "params": {"penalty_per_missing": 1000},
    "weight": 1000,
    "enabled": true
  }
]
```

---

## Optimization

```json
"optimization": {
  "algorithm": "CSPv2" | "ILP" | "ILPv2" | "CSP" | "Greedy Randomized",
  "maxTimeMinutes": 10,
  "objectives": [
    {
      "goal": "minimize_shortages",
      "weight": 1000,
      "priority": 1
    },
    {
      "goal": "balance_workload",
      "weight": 10,
      "priority": 2
    }
  ]
}
```

**Available Algorithms:**
- `CSPv2` - Constraint Programming v2 (recommended)
- `ILPv2` - Linear Programming v2
- `CSP_ENGINE` - CP-SAT with rule engine
- `ILP Engine` - ILP with rule engine
- `Greedy Randomized` - Greedy randomized search
- `GRHC_ENGINE` - Greedy + Hill Climbing

---

## Complete Example Structure

```json
{
  "schemaVersion": "2.1",
  "problemType": "employee_scheduling",

  "metadata": {...},
  "features": {...},
  "temporalScope": {...},

  "employees": {
    "model": "competency",
    "competency": [...]  // Full employee list in JSON
  },

  "demand": {
    "model": "multiLevel",
    "organizationalUnits": {...},
    "shifts": [...],
    "multiLevel": {
      "priorityHierarchy": [...],  // Priority hierarchy in JSON
      "requirements": [...]
    }
  },

  "scheduleInput": {
    "enabled": true,
    "dataFile": "schedule_input.csv"  // Reference to CSV
  },

  "constraints": {...},
  "optimization": {...}
}
```

And `schedule_input.csv`:
```csv
employee_id,2030-10-01,2030-10-02,...
20072412,A,A,...
20066543,DL,A,...
```

And `demand.csv`:
```csv
date,shift,competency,level,minimum,ideal,estimated,day_type,time_start,time_end,application_type
2030-10-01,M,EG,1,1,2,1,weekday,08:30,16:30,team
2030-10-01,T,EG,1,1,1,1,weekday,14:00,22:00,team
```

---

## Differences from v2.0 Format

| Field | v2.0 | v2.1 |
|-------|------|------|
| `schemaVersion` | `"2.0"` | `"2.1"` |
| `scheduleInput.employeeSchedules` | Array of objects in JSON | **Removed** |
| `scheduleInput.dataFile` | Not present | **New:** path to schedule_input.csv |
| `demand.dataFile` | Not present | **New:** path to demand.csv (optional) |
| Employee data | In JSON | In JSON (unchanged) |
| Priority hierarchy | In JSON | In JSON (unchanged) |
| Schedule constraints | In JSON (nested arrays) | **In schedule_input.csv** |
| Demand requirements | In JSON only | **Hybrid: patterns in JSON, daily values in demand.csv** |

---

## CSV Best Practices

### For schedule_input.csv:
1. **Use UTF-8 encoding** for international characters
2. **Keep employee_id consistent** between JSON and CSV
3. **Use ISO date format** (YYYY-MM-DD) for column headers
4. **Use constraints only** - no work hours (those are outputs)
5. **Document custom markings** in `scheduleInput.markingTypes`

### For demand.csv:
1. **Use UTF-8 encoding** for international characters
2. **Match shift/competency codes** with JSON definitions
3. **Use ISO date format** (YYYY-MM-DD) in date column
4. **Maintain logical order** - minimum ≤ estimated ≤ ideal
5. **Generate from patterns first** - then edit for exceptions

### General:
1. **Validate in Excel** before using in scheduler
2. **Place CSVs in same directory** as JSON for easy reference
3. **Use consistent naming** - schedule_input.csv and demand.csv

---

## Validation Checklist

### JSON Validation
- [ ] Validates against schema.json
- [ ] `schemaVersion` is `"2.1"`
- [ ] All employee IDs are unique
- [ ] `scheduleInput.dataFile` path is correct (if used)
- [ ] `demand.dataFile` path is correct (if used)
- [ ] Dates in `temporalScope` are valid
- [ ] All shift codes in `demand.shifts[]` are unique
- [ ] All competency codes in `organizationalUnits.competencies[]` are unique

### schedule_input.csv Validation
- [ ] First column is `employee_id`
- [ ] All employee IDs exist in JSON
- [ ] Date columns match `temporalScope` period
- [ ] All values are valid constraints (A, DL, DLF, DLV, VAC, EnfD, or time ranges)
- [ ] No work hours (4, 5, 8) - those are outputs!
- [ ] No missing columns for any date
- [ ] No duplicate employee IDs
- [ ] UTF-8 encoding

### demand.csv Validation (if used)
- [ ] All required columns present (date, shift, competency, level, minimum, ideal, estimated)
- [ ] All dates within `temporalScope.targetPeriod`
- [ ] All shift codes exist in JSON `demand.shifts[]`
- [ ] All competency codes exist in JSON `organizationalUnits.competencies[]`
- [ ] Logical order: minimum ≤ estimated ≤ ideal
- [ ] No duplicate rows (same date/shift/competency/level)
- [ ] Time ranges are valid HH:MM format
- [ ] Application types are valid (team, team_type, task)
- [ ] UTF-8 encoding

### Cross-Validation
- [ ] schedule_input.csv employee IDs match JSON `employees[].id`
- [ ] Number of date columns in schedule_input.csv = `temporalScope.numDays`
- [ ] Date range in schedule_input.csv matches `temporalScope.targetPeriod`
- [ ] Markings used in schedule_input.csv are defined in `scheduleInput.markingTypes`
- [ ] demand.csv dates align with `temporalScope.targetPeriod`
- [ ] demand.csv references match JSON shift and competency definitions

---

## See Also

- **[README.md](README.md)** - Overview and philosophy
- **[schema.json](schema.json)** - Formal JSON Schema
- **[problem_example.json](problem_example.json)** - Complete working example
- **[schedule_input.csv](schedule_input.csv)** - Example schedule constraints CSV
- **[demand.csv](demand.csv)** - Example demand requirements CSV

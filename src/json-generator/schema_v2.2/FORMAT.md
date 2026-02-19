# JSON + CSV Hybrid Format Reference (v2.2)

Quick reference guide for the hybrid scheduling problem format.

**What's New in v2.2:**
- 🆕 **"A" in schedule_input.csv** now means "Auto-allocate based on contract" (reads workHoursPerDay from employee JSON)
- 🆕 **Numeric values (1-16)** in schedule_input.csv specify exact hours to work that day (e.g., "8" = work 8 hours)
- 🆕 **workHoursPerDay** field in employee definitions for contract-based allocation

---

## Root Structure (JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemaVersion` | string | ✓ | Must be `"2.2"` |
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
| `useWorkPeriodBasedScheduling` | true | Enable shift-based (true) or interval-based (false) scheduling |
| `useAdvancedConstraints` | false | Enable day-off swapping, breaks, etc. |
| `usePriorityHierarchy` | false | Enable priority-based allocation ordering |

**Example:**
```json
{
  "features": {
    "useWorkPeriodBasedScheduling": true,
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

## Contracts (v2.2)

### Purpose
Define reusable contract types with work hours and optional constraints. Multiple employees can reference the same contract definition, eliminating duplication and centralizing contract logic.

### Contract Structure
```json
"contracts": {
  "definitions": [
    {
      "id": "fullTime_8h",
      "name": "Full Time - 8 hours/day",
      "workHoursPerDay": 8,
      "constraints": {
        "weekendsOnly": false,
        "maxHoursPerWeek": 40,
        "maxConsecutiveDays": 5
      }
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

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✓ | Unique contract identifier (e.g., "fullTime_8h") |
| `name` | string | ✓ | Human-readable contract name |
| `workHoursPerDay` | number | ✓ | Default hours when "A" is used in schedule_input.csv |
| `constraints` | object | - | Optional contract-specific constraints |

### Contract Constraints (Optional)

All contract constraints are optional. Define them only when needed for your use case.

| Constraint | Type | Description |
|------------|------|-------------|
| `weekendsOnly` | boolean | Employee can only work Saturday and Sunday |
| `weekdaysOnly` | boolean | Employee can only work Monday through Friday |
| `availableDays` | array | Specific days employee can work (e.g., ["monday", "friday"]) |
| `maxHoursPerWeek` | number | Maximum hours employee can work per week |
| `maxConsecutiveDays` | integer | Maximum number of consecutive work days |
| `minRestDaysPerWeek` | integer | Minimum number of rest days per week (0-7) |
| `flexibleHours` | boolean | Whether employee can work variable hours |

**Example with Constraints:**
```json
{
  "id": "partTime_weekends",
  "name": "Part Time - Weekends Only",
  "workHoursPerDay": 6,
  "constraints": {
    "weekendsOnly": true,
    "availableDays": ["saturday", "sunday"],
    "maxHoursPerWeek": 12,
    "minRestDaysPerWeek": 5
  }
}
```

**Validation Rules:**
- `weekendsOnly` and `weekdaysOnly` are mutually exclusive
- `availableDays` must contain valid day names (monday-sunday, lowercase)
- Contract IDs must be unique across all definitions
- `workHoursPerDay` must be 0-24

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
    "teams": ["A", "B"],
    "contractType": "fullTime_8h"
  }
]
```

**v2.2:** Employee references contract via `contractType` - work hours come from contract definition

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
    "contractType": "fullTime_8h",
    "contractPeriods": [
      {"start": "2024-01-01", "end": null, "contractType": "fullTime_8h"}
    ],
    "restrictions": {
      "cannotSwapDayOffs": false,
      "preferredWorkPeriods": ["M"],
      "blackoutDates": []
    }
  }
]
```

**Key Notes:**
- `id` must be unique and match CSV employee_id column
- `competencies.level`: 1 = highest skill, higher numbers = lower skill
- **v2.2:** `contractType` references contract ID from `contracts.definitions`
- **v2.2:** `contractPeriods[].contractType` allows contract changes over time
  - Employee can transition from part-time to full-time contracts
  - Each period can reference a different contract
  - workHoursPerDay comes from the referenced contract

---

## Demand Requirements

### Work Period Model Selection

```json
"demand": {
  "workPeriodModel": "fixed" | "flexible"
}
```

| Model | Description | Use Case |
|-------|-------------|----------|
| **fixed** | Predefined shifts with fixed times | Traditional work period work (most common) |
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

### Work Period Definitions (Fixed Model)
```json
"workPeriods": [
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
  }
]
```

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

---

## Schedule Input (CSV Reference) - v2.2 Enhanced

### JSON Configuration
```json
"scheduleInput": {
  "enabled": true,
  "dataFile": "schedule_input.csv",  // Path relative to JSON file
  "markingTypes": {
    "A": "Auto-allocate hours from contract (v2.2)",
    "8": "Work exactly 8 hours (v2.2 - any number 1-16)",
    "EQUALS:08:00-16:00": "Must work exactly 8 AM to 4 PM (v2.2)",
    "INCLUDE:09:00-17:00": "Must cover 9 AM to 5 PM minimum (v2.2)",
    "EXCEPT:14:00-22:00": "Unavailable from 2 PM to 10 PM (v2.2)",
    "DL": "Day Off - Generic day off",
    "DLF": "Fixed day off (cannot change)",
    "DLV": "Variable day off (can swap)",
    "VAC": "Vacation",
    "EnfD": "Sick leave"
  }
}
```

### CSV Format (schedule_input.csv)

**Purpose:** Specifies work requirements and availability constraints for each employee

**Structure:**
```csv
employee_id,YYYY-MM-DD,YYYY-MM-DD,YYYY-MM-DD,...
EMP001,A,8,DL,...
EMP002,DL,A,6,...
EMP003,VAC,VAC,4,...
```

**Column 1: employee_id**
- Must match `employees[].id` in JSON
- String format (e.g., "20072412", "EMP001")

**Columns 2+: Date columns**
- Header format: `YYYY-MM-DD` (e.g., "2030-10-01")
- One column per day in temporal scope
- Number of columns = `temporalScope.numDays`

**Cell Values (v2.2 Enhanced):**

| Value | Type | Description | Example |
|-------|------|-------------|---------|
| **`A`** | Auto-allocate | Algorithm allocates hours from employee's `workHoursPerDay` | Employee with `workHoursPerDay: 8` gets 8 hours |
| **`4`, `6`, `8`, etc.** | Specific hours | Employee must work exactly this many hours | `8` = work 8 hours that day |
| **`EQUALS:HH:MM-HH:MM`** | Time constraint | Must work EXACTLY this time range (no earlier/later) | `EQUALS:08:00-16:00` = work 8 AM to 4 PM only |
| **`INCLUDE:HH:MM-HH:MM`** | Time constraint | Must work entire range minimum (can start earlier/end later) | `INCLUDE:09:00-17:00` = must cover 9-5, could work 8-6 |
| **`EXCEPT:HH:MM-HH:MM`** | Time constraint | Completely unavailable during this time window | `EXCEPT:14:00-22:00` = cannot work 2 PM to 10 PM |
| **`VAC`** | Standard constraint | Vacation (cannot work) | Always valid - approved vacation |
| **`NOT`** | Standard constraint | Unavailable (cannot work) | Always valid - general unavailability |

**Custom Constraints (must be defined in JSON scheduleInput.markingTypes):**

Common custom constraints that must be explicitly defined in your problem.json:
- `DL` = Day off (generic)
- `DLF` = Fixed day off (cannot swap)
- `DLV` = Variable day off (can swap within week)
- `DO` = Day off (alias for DL)
- `EnfD` = Sick leave
- `Med` = Medical reason
- Any project-specific constraint codes you need

**IMPORTANT v2.2 Changes:**
- ✅ **"A" now means AUTO-ALLOCATE** from contract (not just "available")
- ✅ **Numbers 1-16 are WORK HOURS** (algorithm must allocate exactly this many hours)
- ✅ **Time window constraints** with EQUALS/INCLUDE/EXCEPT modifiers (Allen Interval Algebra) for precise time control
- ✅ **All other markings remain CONSTRAINTS** (days employee cannot work)

**Example CSV (v2.2 with Time Constraints):**
```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
20072412,A,A,8,DL,EQUALS:08:00-16:00
20066543,DL,INCLUDE:09:00-17:00,6,A,DL
20067009,EXCEPT:14:00-22:00,4,DL,A,A
20062688,VAC,VAC,VAC,VAC,VAC
```

**Interpretation:**
- Employee 20072412: Oct-01=auto (uses workHoursPerDay), Oct-02=auto, Oct-03=exactly 8 hours, Oct-04=day off, Oct-05=must work exactly 8 AM-4 PM
- Employee 20066543: Oct-01=day off, Oct-02=must cover 9 AM-5 PM minimum (could work longer), Oct-03=exactly 6 hours, Oct-04=auto, Oct-05=day off
- Employee 20067009: Oct-01=unavailable 2 PM-10 PM (can work morning), Oct-02=exactly 4 hours, Oct-03=day off, Oct-04=auto, Oct-05=auto
- Employee 20062688: Vacation all week

### Time Window Constraints (v2.2 Feature)

Time window constraints allow precise control over when employees work using three modifiers:

#### EQUALS:HH:MM-HH:MM
**Semantics:** Employee must work EXACTLY this time range. Cannot start earlier or end later.

**Use Cases:**
- Fixed schedule employees: "I can only work 9 AM to 5 PM"
- Legal restrictions: "Part-time staff must finish by 6 PM"
- Equipment access: "Lab work only during 10 AM-2 PM window"

**Example:** `EQUALS:08:00-16:00`
- ✅ Valid: Assign to work period 08:00-16:00
- ❌ Invalid: Assign to 07:00-16:00 (starts too early)
- ❌ Invalid: Assign to 08:00-17:00 (ends too late)

#### INCLUDE:HH:MM-HH:MM
**Semantics:** Employee must work the ENTIRE specified range as a minimum. Can start earlier or end later.

**Use Cases:**
- Coverage requirements: "Must be present during core hours 10 AM-3 PM"
- Supervision needs: "Must overlap with manager's 9 AM-5 PM shift"
- Peak periods: "Must cover lunch rush 12 PM-2 PM"

**Example:** `INCLUDE:09:00-17:00`
- ✅ Valid: Assign to 09:00-17:00 (exact match)
- ✅ Valid: Assign to 08:00-18:00 (covers and extends)
- ✅ Valid: Assign to 07:00-17:00 (starts earlier, same end)
- ❌ Invalid: Assign to 10:00-17:00 (missing 9-10 AM coverage)
- ❌ Invalid: Assign to 09:00-16:00 (missing 4-5 PM coverage)

#### EXCEPT:HH:MM-HH:MM
**Semantics:** Employee is completely UNAVAILABLE during this time window. Cannot work at all during this period.

**Use Cases:**
- Personal constraints: "Cannot work evenings (6 PM-10 PM)"
- Avoiding specific shifts: "Unavailable during night shift hours"
- Partial day availability: "Not available mornings (before 12 PM)"

**Example:** `EXCEPT:14:00-22:00`
- ✅ Valid: Assign to 06:00-14:00 (ends exactly at exclusion start)
- ✅ Valid: Assign to 08:00-12:00 (completely before exclusion)
- ❌ Invalid: Assign to 10:00-18:00 (overlaps with 14:00-18:00)
- ❌ Invalid: Assign to 14:00-22:00 (exactly matches exclusion)
- ❌ Invalid: Assign to 20:00-23:00 (overlaps with 20:00-22:00)

#### Interaction with Work Periods

Time window constraints work alongside your defined work periods:

1. **Work periods define available shifts** (e.g., Morning=08:30-16:30, Afternoon=14:00-22:00)
2. **Time constraints filter which shifts employees can be assigned to**
3. **The algorithm must respect BOTH** work period definitions AND time constraints

**Example:**
```
Work Periods: M=08:30-16:30, T=14:00-22:00, N=22:00-06:30
Employee constraint: EXCEPT:14:00-22:00
Result: Employee can only be assigned to M (Morning) shift
```

#### Mixing Constraint Types

You can mix different constraint types across days in the same schedule:

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04
EMP001,A,EQUALS:08:00-16:00,8,INCLUDE:09:00-17:00
EMP002,EXCEPT:14:00-22:00,DL,6,A
```

**Validation Rules (v2.2):**
1. First column must be named `employee_id`
2. All employee IDs must exist in JSON
3. Date columns must be consecutive and match `temporalScope`
4. Valid values: A, integers 1-16, VAC, NOT, or custom codes defined in scheduleInput.markingTypes
5. Time window constraints: EQUALS:HH:MM-HH:MM, INCLUDE:HH:MM-HH:MM, EXCEPT:HH:MM-HH:MM
   - Time format: HH must be 00-23, MM must be 00-59
   - Start time must be before end time
   - Times should align with or overlap defined work periods
6. If "A" is used, employee should have `workHoursPerDay` defined (defaults to 8 for fullTime, 4 for partTime)
7. No duplicate employee IDs
8. No contradictory constraints on same day (e.g., both EQUALS:08:00-16:00 and EXCEPT:08:00-16:00)

---

## Demand Requirements (CSV Format)

### JSON Configuration
```json
"demand": {
  "workPeriodModel": "fixed",
  "dataFile": "demand.csv",
  "organizationalUnits": {
    "teams": ["TeamA", "TeamB", "TeamC"]
  },
  "workPeriods": [
    {"code": "M", "name": "Morning", "timeRange": {"start": "08:30", "end": "16:30"}},
    {"code": "T", "name": "Afternoon", "timeRange": {"start": "14:00", "end": "22:00"}}
  ],
  "priorityHierarchy": [
    {"rank": 1, "team": "TeamA", "description": "Highest priority"},
    {"rank": 2, "team": "TeamB", "description": "Medium priority"}
  ]
}
```

### CSV Format (demand.csv)

**Purpose:** Daily coverage requirements - tells algorithm HOW MANY people are needed each day

**Structure:**
```csv
date,workPeriod,team,minimum,ideal,estimated
2030-10-01,M,TeamA,2,3,2
2030-10-01,T,TeamA,2,2,2
2030-10-01,M,TeamB,1,2,1
```

**Column Specifications:**

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `date` | ISO date | Date for this requirement | `2030-10-01` |
| `shift` | string | Work period code (must match shifts[].code in JSON) | `M`, `T`, `N` |
| `team` | string | Team identifier (must match organizationalUnits.teams[] in JSON) | `TeamA`, `TeamB` |
| `minimum` | integer | Minimum people required (hard constraint) | `1`, `2`, `3` |
| `ideal` | integer | Ideal number of people (soft target) | `2`, `3`, `4` |
| `estimated` | integer | Estimated/expected demand (for KPI analysis) | `1`, `2`, `3` |

**Validation Rules:**
1. All dates must be within `temporalScope.targetPeriod`
2. Work period codes must exist in `demand.shifts[].code`
3. Team codes must exist in `demand.organizationalUnits.teams[]`
4. `minimum ≤ estimated ≤ ideal` (logical constraint)
5. No duplicate rows (same date/shift/team combination)

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
- `no_earlier_shift_next_day` - No backward work period transitions
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

## Complete Example Structure (v2.2)

```json
{
  "schemaVersion": "2.2",
  "problemType": "employee_scheduling",

  "metadata": {...},
  "features": {...},
  "temporalScope": {...},

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
        "id": "20072412",
        "name": "Emp_20072412",
        "competencies": [{"code": "Management", "level": 1}],
        "contractType": "fullTime_8h"
      },
      {
        "id": "20066543",
        "name": "Emp_20066543",
        "competencies": [{"code": "Checkout", "level": 1}],
        "contractType": "partTime_4h"
      }
    ]
  },

  "demand": {
    "workPeriodModel": "fixed",
    "dataFile": "demand.csv",
    "organizationalUnits": {...},
    "workPeriods": [...],
    "priorityHierarchy": [...]
  },

  "scheduleInput": {
    "enabled": true,
    "dataFile": "schedule_input.csv",
    "markingTypes": {
      "A": "Auto-allocate from contract",
      "DL": "Day Off",
      "VAC": "Vacation"
    }
  },

  "constraints": {...},
  "optimization": {...}
}
```

And `schedule_input.csv`:
```csv
employee_id,2030-10-01,2030-10-02,2030-10-03
20072412,A,8,A
20066543,DL,A,4
```

And `demand.csv`:
```csv
date,workPeriod,competency,level,minimum,ideal,estimated
2030-10-01,M,Management,1,1,2,1
2030-10-01,M,Checkout,1,2,3,2
```

---

## Differences from v2.1 Format

| Field | v2.1 | v2.2 |
|-------|------|------|
| `schemaVersion` | `"2.1"` | `"2.2"` |
| `employees[].workHoursPerDay` | Not present | **New:** Default hours when "A" is used in CSV |
| `scheduleInput` CSV "A" value | Available (constraint) | **Changed:** Auto-allocate from contract |
| `scheduleInput` CSV numeric values | Invalid (error) | **New:** Valid (specific hours 1-16) |
| `scheduleInput` CSV time constraints | Not available | **New:** EQUALS/INCLUDE/EXCEPT:HH:MM-HH:MM for time window control (Allen Interval Algebra) |
| Employee contract defaults | N/A | Defaults: 8h fullTime, 4h partTime |

---

## Migration Guide: v2.1 → v2.2

### Required Changes:
1. **Update schemaVersion** from `"2.1"` to `"2.2"` in JSON
2. **Add workHoursPerDay** to employees who use "A" in schedule_input.csv
3. **Review "A" usage** in schedule_input.csv - now means "auto-allocate from contract"
4. **Replace work hour numbers** with appropriate values:
   - If you had errors for numeric values in v2.1, you can now use them as intended

### Optional Enhancements:
1. Use numeric values (4, 6, 8) for specific hour requirements instead of "A"
2. Mix "A" (auto) and numbers (specific) in the same schedule for flexibility
3. Use time window constraints (EQUALS/INCLUDE/EXCEPT:HH:MM-HH:MM) for precise time control (Allen Interval Algebra)
4. Combine all constraint types for maximum flexibility (A, numbers, and time windows)

### Example Migration:

**v2.1 schedule_input.csv:**
```csv
employee_id,2030-10-01,2030-10-02
EMP001,A,A
EMP002,DL,A
```
In v2.1, "A" meant "available for work"

**v2.2 schedule_input.csv + JSON:**
```csv
employee_id,2030-10-01,2030-10-02
EMP001,A,8
EMP002,DL,A
```
```json
{
  "employees": {
    "simple": [
      {"id": "EMP001", "workHoursPerDay": 8},
      {"id": "EMP002", "workHoursPerDay": 6}
    ]
  }
}
```
In v2.2:
- EMP001: Oct-01 = auto-allocate 8h (from contract), Oct-02 = exactly 8h
- EMP002: Oct-01 = day off, Oct-02 = auto-allocate 6h (from contract)

---

## CSV Best Practices (v2.2)

### For schedule_input.csv:
1. **Use UTF-8 encoding** for international characters
2. **Keep employee_id consistent** between JSON and CSV
3. **Use ISO date format** (YYYY-MM-DD) for column headers
4. **Define workHoursPerDay** in JSON for employees using "A"
5. **Use numbers (1-16) for specific hours**, "A" for contract-based allocation
6. **Use time window constraints** when you need precise time control:
   - EQUALS:HH:MM-HH:MM for fixed schedules
   - INCLUDE:HH:MM-HH:MM for minimum coverage requirements
   - EXCEPT:HH:MM-HH:MM for unavailability periods
7. **Document markings** in `scheduleInput.markingTypes`
8. **Mix constraint types** for flexible scheduling (A, numbers, and time windows as needed)

### For demand.csv:
1. **Use UTF-8 encoding** for international characters
2. **Match shift/competency codes** with JSON definitions
3. **Use ISO date format** (YYYY-MM-DD) in date column
4. **Maintain logical order** - minimum ≤ estimated ≤ ideal

### General:
1. **Validate in Excel** before using in scheduler
2. **Place CSVs in same directory** as JSON for easy reference
3. **Use the validator** to check for errors

---

## Validation Checklist (v2.2)

### JSON Validation
- [ ] Validates against schema.json
- [ ] `schemaVersion` is `"2.2"`
- [ ] All employee IDs are unique
- [ ] Employees using "A" in CSV have `workHoursPerDay` defined (or use defaults)
- [ ] `scheduleInput.dataFile` path is correct (if used)
- [ ] `demand.dataFile` path is correct (if used)
- [ ] Dates in `temporalScope` are valid

### schedule_input.csv Validation (v2.2)
- [ ] First column is `employee_id`
- [ ] All employee IDs exist in JSON
- [ ] Date columns match `temporalScope` period
- [ ] All values are valid: A, integers 1-16, DL, DLF, DLV, VAC, EnfD, NOT, Med, or time ranges
- [ ] Numeric values are within 1-16 range
- [ ] Time window constraints use valid format: EQUALS:HH:MM-HH:MM, INCLUDE:HH:MM-HH:MM, EXCEPT:HH:MM-HH:MM
- [ ] Time window constraints have valid times (HH: 00-23, MM: 00-59)
- [ ] Time window constraints have start time before end time
- [ ] No contradictory time constraints on same day
- [ ] Time window constraints align with or overlap defined work periods
- [ ] No missing columns for any date
- [ ] No duplicate employee IDs
- [ ] UTF-8 encoding

### demand.csv Validation
- [ ] All required columns present (date, shift, team, minimum, ideal, estimated)
- [ ] All dates within `temporalScope.targetPeriod`
- [ ] All work period codes exist in JSON `demand.shifts[]`
- [ ] All team/competency codes exist in JSON `organizationalUnits`
- [ ] Logical order: minimum ≤ estimated ≤ ideal
- [ ] No duplicate rows
- [ ] UTF-8 encoding

### Cross-Validation
- [ ] schedule_input.csv employee IDs match JSON `employees[].id`
- [ ] Number of date columns in schedule_input.csv = `temporalScope.numDays`
- [ ] Date range in schedule_input.csv matches `temporalScope.targetPeriod`
- [ ] Employees with "A" have `workHoursPerDay` defined or valid defaults
- [ ] demand.csv references match JSON work period and team/competency definitions

---

## See Also

- **[README.md](README.md)** - Overview and philosophy
- **[schema.json](schema.json)** - Formal JSON Schema for v2.2
- **[validator/validator.py](validator/validator.py)** - Validation tool for v2.2
- **[examples/](examples/)** - Working examples with contract hours

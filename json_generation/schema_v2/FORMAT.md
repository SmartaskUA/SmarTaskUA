# JSON Problem Format Reference

Quick reference guide for the scheduling problem JSON format.

## Root Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schemaVersion` | string | ✓ | Must be `"2.0"` |
| `problemType` | string | ✓ | Must be `"employee_scheduling"` |
| `metadata` | object | ✓ | Problem identification |
| `features` | object | - | Feature flags (defaults to all false) |
| `temporalScope` | object | ✓ | Time period definition |
| `employees` | object | ✓ | Employee definitions |
| `demand` | object | ✓ | Coverage requirements |
| `scheduleInput` | object | - | Pre-existing schedule (optional) |
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

---

## Feature Flags

Controls which optional modules are enabled:

| Feature | Default | Description |
|---------|---------|-------------|
| `useShiftBasedScheduling` | true | Enable shift-based (true) or interval-based (false) scheduling |
| `useCompetencyModel` | false | Enable skill-based model (vs. fixed teams) |
| `useScheduleInput` | false | Enable pre-existing schedule with markings |
| `useMultiLevelDemand` | false | Enable minimo/ideal/estimado levels |
| `useAdvancedConstraints` | false | Enable day-off swapping, breaks, etc. |
| `usePriorityHierarchy` | false | Enable competency priority ordering |

---

## Temporal Scope

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `year` | integer | ✓ | Scheduling year |
| `numDays` | integer | ✓ | Number of days (typically 365) |
| `targetPeriod` | object | - | Primary scheduling window |
| `targetPeriod.start` | ISO date | - | Start date |
| `targetPeriod.end` | ISO date | - | End date |
| `targetPeriod.includeBufferWeeks` | boolean | - | Include weeks before/after |

---

## Employees

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
    "name": "João Silva",
    "teams": ["A", "B"]
  }
]
```

### Competency Model (model="competency")
```json
"competency": [
  {
    "id": "EMP001",
    "name": "João Silva",
    "competencies": [
      {"code": "EG", "level": 1, "description": "Gestão nivel 1"}
    ],
    "contractType": "fullTime" | "partTime",
    "contractPeriods": [
      {"start": "2024-01-01", "end": null}
    ],
    "unavailability": [
      {
        "dates": ["2025-01-10"],
        "reason": "vacation",
        "type": "VAC" | "EnfD" | "DLF" | "other"
      }
    ],
    "restrictions": {
      "cannotSwapDayOffs": false,
      "preferredShifts": ["M"],
      "blackoutDates": []
    }
  }
]
```

**Competency Levels:** `1` = highest skill, higher numbers = lower skill

---

## Demand Requirements

### Shift Model Selection ⭐ IMPORTANT

The scheduling system supports **three paradigms**:

```json
"demand": {
  "shiftModel": "fixed" | "flexible" | "interval"
}
```

| Model | Description | Complexity | Use Case |
|-------|-------------|------------|----------|
| **fixed** | Predefined shifts with fixed times | Low | Traditional shift work (retail, manufacturing) |
| **flexible** | Shifts with multiple start time options | Medium | Flexible businesses with some structure |
| **interval** | No shifts - continuous time blocks | High | Highly flexible scheduling (restaurants, call centers) |

**Feature Flag:**
```json
"features": {
  "useShiftBasedScheduling": true  // true = fixed/flexible, false = interval
}
```

---

### Model Selection
```json
"demand": {
  "model": "simple" | "multiLevel",
  "shiftModel": "fixed" | "flexible" | "interval"
}
```

### Organizational Units
```json
"organizationalUnits": {
  "teams": ["A", "B"],  // for team model
  "competencies": [     // for competency model
    {"code": "EG", "name": "Equipo de Gestión"}
  ]
}
```

### Shift Definitions

#### Fixed Model (shiftModel="fixed")
```json
"shifts": [
  {
    "code": "M",
    "name": "Morning",
    "order": 1,
    "timeRange": {
      "start": "08:00",
      "end": "16:00"
    },
    "breaks": [
      {
        "type": "meal",
        "duration": 30,
        "timing": {
          "mode": "window",
          "window": {"start": "12:00", "end": "14:00"}
        },
        "paid": false,
        "required": true
      }
    ]
  },
  {
    "code": "T",
    "name": "Afternoon",
    "order": 2,
    "timeRange": {
      "start": "14:00",
      "end": "22:00"
    }
  }
]
```

#### Flexible Model (shiftModel="flexible")
```json
"shifts": [
  {
    "code": "MORNING_8H",
    "name": "Morning 8-hour shift",
    "order": 1,
    "duration": 8,
    "allowedStartTimes": ["08:00", "08:30", "09:00", "09:30"],
    "breaks": [
      {
        "type": "meal",
        "duration": 30,
        "timing": {
          "mode": "afterWork",
          "afterMinutes": 240  // After 4 hours
        },
        "paid": false
      }
    ]
  }
]
```

#### Interval Model (shiftModel="interval")
```json
"shifts": null,  // No predefined shifts
"workParameters": {
  "minDuration": 4,
  "maxDuration": 8,
  "granularity": 15,  // 15-minute increments
  "operatingHours": {
    "start": "08:00",
    "end": "22:00"
  },
  "breakRules": [
    {
      "type": "meal",
      "duration": 30,
      "trigger": {
        "mode": "afterHours",
        "hours": 4
      },
      "paid": false,
      "required": true,
      "canStagger": true
    },
    {
      "type": "rest",
      "duration": 15,
      "trigger": {
        "mode": "withinWindow",
        "window": {"start": "10:00", "end": "11:00"}
      },
      "paid": true,
      "required": false
    }
  ]
}
```

**Key Fields:**
- `order`: Shift ordering (1=earliest, higher=later) - for transition constraints
- `timeRange`: Fixed start/end times (fixed model)
- `duration`: Work hours (flexible model)
- `allowedStartTimes`: Possible start times (flexible model)
- `workParameters`: Scheduling parameters (interval model)

### Simple Demand (model="simple")
```json
"simple": [
  {
    "pattern": "weekdays" | "weekends" | "all" | "specific",
    "dates": ["2025-01-01"],  // when pattern="specific"
    "unit": "A",              // team or competency code
    "shift": "M",
    "minimum": 2,
    "ideal": 3
  }
]
```

### Multi-Level Demand (model="multiLevel", requires useMultiLevelDemand=true)
```json
"multiLevel": {
  "priorityHierarchy": [
    {
      "rank": 1,
      "competency": "ALM",
      "level": "N≥1",
      "description": "RESP ALMACEN"
    }
  ],
  "requirements": [
    {
      "applies": {
        "dayType": "weekday" | "weekend" | "all",
        "dates": null  // or array of specific dates
      },
      "timeWindow": {
        "start": "08:30",
        "end": "15:30"
      },
      "competency": "ALM",
      "level": 1,
      "minimo": 1,
      "ideal": 2,
      "estimado": 1,
      "applicationType": "tarefa" | "equipa" | "tipo_equipa"
    }
  ]
}
```

---

## Schedule Input (requires useScheduleInput=true)

```json
"scheduleInput": {
  "enabled": true,
  "markingTypes": {
    "DL": "Dia Livre - Generic day off",
    "DLF": "Fixed day off (cannot change)",
    "DLV": "Variable day off (can swap)",
    "VAC": "Vacation",
    "EnfD": "Sick leave",
    "WORK": "Work shift"
  },
  "employeeSchedules": [
    {
      "employeeId": "EMP001",
      "days": [
        {
          "date": "2025-01-06",
          "marking": "WORK" | "DL" | "DLF" | "DLV" | "VAC" | "EnfD",
          "isFixed": false,  // true = cannot modify (red in Excel)
          "shift": {
            "duration": 8,
            "startTime": null,    // null = flexible
            "endTime": null,
            "competency": "EG"
          },
          "note": "Optional note"
        }
      ]
    }
  ]
}
```

---

## Break Scheduling

Breaks can be defined differently depending on shift model:

### Break Timing Modes

| Mode | Description | Use Case | Example |
|------|-------------|----------|---------|
| **fixed** | Break at specific time | Mandatory lunch hour | 12:00 break |
| **window** | Break within time range | Flexible lunch | Between 12:00-14:00 |
| **afterWork** | Break after X hours of work | Labor law compliance | After 4 hours |
| **afterHours** | (Interval mode) Trigger after duration | Dynamic scheduling | After 4h worked |
| **withinWindow** | (Interval mode) Must occur in window | Business requirement | Morning break 10:00-11:00 |

### In Shift-Based Models (fixed/flexible)

Breaks defined **within shift definition**:

```json
"shifts": [
  {
    "code": "M",
    "timeRange": {"start": "08:00", "end": "16:00"},
    "breaks": [
      {
        "type": "meal",           // "meal" | "rest" | "other"
        "duration": 30,           // minutes
        "timing": {
          "mode": "window",
          "window": {"start": "12:00", "end": "14:00"}
        },
        "paid": false,            // Affects duration calculation
        "required": true,         // Must be taken
        "canStagger": true        // Can be staggered across employees
      }
    ]
  }
]
```

**Duration Calculation:**
- **Paid break**: Included in shift duration
  Example: 8h shift with 30min paid break = 8h on-site
- **Unpaid break**: Added to shift duration
  Example: 8h shift with 30min unpaid break = 8.5h on-site

### In Interval Mode

Breaks defined in **workParameters.breakRules**:

```json
"workParameters": {
  "breakRules": [
    {
      "type": "meal",
      "duration": 30,
      "trigger": {
        "mode": "afterHours",
        "hours": 4              // After 4 hours of work
      },
      "paid": false,
      "required": true,
      "canStagger": true
    },
    {
      "type": "rest",
      "duration": 15,
      "trigger": {
        "mode": "withinWindow",
        "window": {"start": "10:00", "end": "11:00"}
      },
      "paid": true,
      "required": false
    }
  ]
}
```

### Break Staggering

When `canStagger: true`, algorithm can schedule breaks at different times for different employees to maintain coverage:

**Example:**
- 3 cashiers working 12:00-14:00 lunch period
- All need 30-min break
- Staggered: Employee 1 breaks 12:00-12:30, Employee 2 breaks 12:30-13:00, Employee 3 breaks 13:00-13:30
- Result: Always 2 cashiers available

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

### Advanced Constraints (requires useAdvancedConstraints=true)
```json
"advanced": {
  "dayOffSwapping": {
    "enabled": true,
    "rules": ["Only DLV can be swapped", "Within same week"],
    "weekDefinition": "monday-sunday" | "sunday-saturday"
  },
  "breaks": {
    "enabled": false,
    "mode": "with_breaks" | "without_breaks",
    "rules": [
      {"minShiftHours": 6, "breakMinutes": 30, "breakType": "meal"}
    ]
  }
}
```

---

## Optimization

```json
"optimization": {
  "algorithm": "CSPv2" | "ILP" | "ILPv2" | "CSP" | ...,
  "maxTimeMinutes": 10,
  "objectives": [
    {
      "goal": "minimize_shortages",
      "weight": 1000,
      "priority": 1
    }
  ],
  "challenges": {
    "multiCompetencyAllocation": {
      "enabled": true,
      "strategy": "priority_first" | "level_first" | "hybrid",
      "weights": {"priorityWeight": 0.5, "levelWeight": 0.5},
      "considerLongTerm": true
    },
    "competencyOrdering": {
      "enabled": true,
      "respectResourceRule": true,
      "dynamicOrdering": true,
      "rule": "Do not allocate to IDEAL if MINIMUM unmet"
    }
  }
}
```

**Available Algorithms:**
- `CSPv2` - Constraint Programming (recommended)
- `ILPv2` - Linear Programming (two-phase)
- `CSP_ENGINE` - CP-SAT with rule engine
- `ILP Engine` - ILP with rule engine
- Others: `Greedy Randomized`, `GRHC_ENGINE`, etc.

---

## Quick Start Examples

### Minimal Problem
```json
{
  "schemaVersion": "2.0",
  "problemType": "employee_scheduling",
  "metadata": {"problemId": "TEST_01", "createdAt": "2025-12-15T10:00:00Z"},
  "temporalScope": {"year": 2025, "numDays": 7},
  "employees": {"model": "team", "simple": [...]},
  "demand": {"model": "simple", "organizationalUnits": {...}, "shifts": [...], "simple": [...]},
  "constraints": {"hard": [...]},
  "optimization": {"algorithm": "CSPv2"}
}
```

### With All Features
Set all feature flags to `true` and include:
- `employees.competency` with multi-competencies
- `demand.multiLevel` with priority hierarchy
- `scheduleInput` with fixed/flexible markings
- `constraints.advanced` with day-off swapping rules
- `optimization.challenges` configurations

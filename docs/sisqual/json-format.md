# Sisqual JSON Format Documentation

Quick reference for Sisqual problem JSON schemas and CSV conversion.

## Overview

The Sisqual scheduling problem uses JSON to represent:
- **Employees** with multiple competencies and skill levels
- **KPI Alarms** with 9-level priority hierarchy
- **Schedule Templates** with fixed/flexible markings
- **Store Configuration** and operational constraints
- **Challenge Configurations** for 4 algorithmic challenges

## File Structure

```
config/sisqual/
├── schemas/                          # JSON schemas
│   ├── employees_schema.json
│   ├── alarms_schema.json
│   ├── schedule_template_schema.json
│   ├── store_config_schema.json
│   └── challenges_config_schema.json
├── examples/                         # Example data
│   ├── employees_example.json
│   ├── alarms_example.json
│   ├── schedule_input_example.json
│   ├── store_config_example.json
│   └── challenges_config_example.json
├── csv_to_json_converter.py         # CSV → JSON converter
└── sisqual_problem_template.json    # Complete problem template
```

## Key Concepts

### Competencies
- **EG** (Equipo Gestión): Management
- **CAJ** (Caja): Cashier
- **ALM** (Almacén): Warehouse

### Skill Levels
- Level 1 = Best performance
- Level 2, 3, 4+ = Lower performance

### Schedule Markings
- **DL**: Day off (generic)
- **DLF**: Fixed day off (cannot change)
- **DLV**: Variable day off (can swap within week)
- **VAC**: Vacation
- **EnfD**: Sick leave/absence
- **DC-E**: Unknown (pending clarification)
- **WORK**: Work shift
- **EMPTY**: Contract gap

### Priority Hierarchy (1-9)
1. ALM N≥1 (Warehouse)
2. EG N=1 (Management level 1)
3. CAJ N=1 (Cashier level 1)
4. EG N=2
5. CAJ N=2
6. EG N=3
7. EG ≥4
8. CAJ N=3
9. EQUIPA N≥1 (Any employee)

## CSV to JSON Conversion

### Usage

```bash
python config/sisqual/csv_to_json_converter.py \
  --employees path/to/employees.csv \
  --schedule path/to/schedule.csv \
  --alarms path/to/alarms.csv \
  --target-month 2025-01 \
  --output ./output
```

### Expected CSV Formats

#### Employees CSV
```csv
Employee ID,Name,Competencies,Part-Time
EMP001,João Silva,"EG-1,CAJ-2",N
EMP002,Maria Santos,CAJ-1,N
EMP003,Pedro Costa,CAJ-2,Y
```

#### Schedule CSV
```csv
Employee ID,Day1,Day2,Day3,...
EMP001,8h,*7h-09:00-16:00,*DLF,...
EMP002,VAC,VAC,5h-FLEX-CAJ,...
```
- Prefix `*` = Fixed (red in Excel)
- `8h` = 8-hour flexible shift
- `7h-09:00-16:00` = 7-hour shift with fixed times
- `5h-FLEX-CAJ` = 5-hour flexible shift, use CAJ competency

#### Alarms CSV
```csv
Alarm ID,Competency,Level,Day Type,Start Time,End Time,Minimo,Ideal,Estimado
ALM_WD,ALM,1,weekday,08:30,15:30,1,1,1
CAJ_PEAK,CAJ,1,weekday,18:00,21:00,2,4,3
```

## Employee JSON

```json
{
  "employees": [
    {
      "id": "EMP001",
      "name": "Employee Name",
      "competencies": [
        {"type": "EG", "level": 1},
        {"type": "CAJ", "level": 2}
      ],
      "partTime": false,
      "contractPeriods": [
        {"startDate": "2024-01-01", "endDate": null}
      ]
    }
  ]
}
```

## Schedule Template JSON

```json
{
  "period": {
    "targetMonth": "2025-01",
    "startDate": "2024-12-23",
    "endDate": "2025-02-02"
  },
  "employeeSchedules": [
    {
      "employeeId": "EMP001",
      "days": [
        {
          "date": "2025-01-06",
          "marking": "WORK",
          "isFixed": false,
          "shift": {
            "duration": 8,
            "startTime": null,
            "endTime": null,
            "isFlexible": true,
            "competencyAssignment": "EG"
          }
        },
        {
          "date": "2025-01-07",
          "marking": "DLV",
          "isFixed": false
        }
      ]
    }
  ]
}
```

## KPI Alarms JSON

```json
{
  "priorityHierarchy": [
    {"rank": 1, "competency": "ALM", "level": "N≥1", "description": "..."},
    {"rank": 2, "competency": "EG", "level": "N=1", "description": "..."}
  ],
  "alarms": [
    {
      "id": "ALM_WAREHOUSE_WEEKDAY",
      "competency": "ALM",
      "level": 1,
      "applicationType": "tarefa",
      "timeRanges": [
        {
          "dayType": "weekday",
          "startTime": "08:30",
          "endTime": "17:30",
          "requirements": {
            "minimo": 1,
            "ideal": 2,
            "estimado": 1
          }
        }
      ]
    }
  ]
}
```

## The 4 Challenges

### Challenge 1: Day-Off Optimization
Minimize day-off swaps while maximizing coverage.
- Only DLV can be swapped
- Swaps within same week only
- Part-time employees cannot swap

### Challenge 2: Competency Ordering
Fill teams by priority order respecting resource allocation.
- Follow priority hierarchy (1-9)
- Don't use ideal if minimum unmet elsewhere

### Challenge 3: Multi-Competency Allocation
Decide which competency to assign for multi-skilled employees.
- Consider alarm priority, skill level, KPI requirements, long-term impact
- **Innovation**: No similar solution exists in market

### Challenge 4: Break Management
Two variants:
- **Without breaks**: Meal included in shift (simpler)
- **With breaks**: Explicit break scheduling (complex)

## Constraints

- Max 5 consecutive working days
- Min 11 hours rest between shifts
- 30-minute time granularity
- Min 1 Sunday off per month
- Store open 365 days/year
- Weekdays: 08:30-22:00
- Weekends: 11:00-21:00

## Integration with Existing System

The Sisqual problem is **separate** from the existing SmarTask scheduling system. It requires:
- New algorithm implementations for the 4 challenges
- Different constraint handling (KPI priorities vs team minimums)
- Competency-level matching (EG-1, CAJ-2) vs simple team assignment

## Quick Start

1. Receive CSV files from Sisqual
2. Run converter: `python csv_to_json_converter.py --employees ... --schedule ... --alarms ...`
3. Verify JSON output matches schemas
4. Feed JSON to algorithm implementations
5. Generate optimized schedule respecting all constraints and priorities

## Reference

Full specification: `docs/BFarias_Doc_Sisqual.pdf`

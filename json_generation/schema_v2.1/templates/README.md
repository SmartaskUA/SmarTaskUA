# CSV Templates for SmarTask Scheduling

This directory contains template CSV files that you can use as starting points for creating your own scheduling problems.

## Available Templates

### 1. `demand_template.csv`
**Purpose**: Define daily coverage requirements (how many people needed per day/shift/team)

**Use this template to specify**:
- Minimum staffing levels (hard constraints)
- Ideal staffing levels (soft targets)
- Estimated demand (for KPI analysis)

**Key features**:
- Comprehensive header comments explaining each column
- Examples of common patterns
- Validation rules
- Tips for large-scale problems

### 2. `schedule_input_template.csv`
**Purpose**: Define employee availability constraints (when employees cannot work)

**Use this template to specify**:
- Vacation days
- Days off
- Sick leave
- Pre-assigned time windows
- Other unavailability

**Key features**:
- Matrix format (employees × dates)
- All allowed values documented
- Examples for common scenarios
- Tips for managing large datasets

---

## Quick Start Guide

### Step 1: Copy Templates
```bash
cp demand_template.csv my_demand.csv
cp schedule_input_template.csv my_schedule_input.csv
```

### Step 2: Clean Up Templates
- Open each CSV file
- Delete all comment lines (lines starting with #)
- Keep only the header row and add your data

### Step 3: Fill In Your Data

**For demand.csv**:
1. Add one row for each day/shift/team combination
2. Specify minimum, ideal, and estimated values
3. Ensure dates are within your planning period

**For schedule_input.csv**:
1. Add one row per employee
2. Add one column per date in your planning period
3. Use "A" for available, VAC/DL/EnfD for unavailable

### Step 4: Create problem.json
Create your problem definition JSON file that references these CSVs:

```json
{
  "schemaVersion": "2.1",
  "problemType": "employee_scheduling",

  "metadata": {
    "problemId": "MY_PROBLEM_2025_Q1",
    "createdAt": "2025-01-21T00:00:00Z",
    "description": "Q1 2025 scheduling problem"
  },

  "features": {
    "useShiftBasedScheduling": true,
    "useAdvancedConstraints": false,
    "usePriorityHierarchy": false
  },

  "temporalScope": {
    "year": 2025,
    "numDays": 90,
    "targetPeriod": {
      "start": "2025-01-01",
      "end": "2025-03-31"
    }
  },

  "employees": {
    "model": "team",
    "simple": [
      {"id": "EMP001", "name": "John Smith", "teams": ["TeamA"]},
      {"id": "EMP002", "name": "Jane Doe", "teams": ["TeamA", "TeamB"]}
    ]
  },

  "demand": {
    "shiftModel": "fixed",
    "dataFile": "my_demand.csv",
    "organizationalUnits": {
      "teams": ["TeamA", "TeamB"]
    },
    "shifts": [
      {"code": "M", "name": "Morning", "order": 1, "timeRange": {"start": "08:30", "end": "16:30"}},
      {"code": "T", "name": "Afternoon", "order": 2, "timeRange": {"start": "14:00", "end": "22:00"}}
    ]
  },

  "scheduleInput": {
    "dataFile": "my_schedule_input.csv",
    "markingTypes": {
      "DL": "Day Off",
      "VAC": "Vacation",
      "EnfD": "Sick Leave"
    }
  },

  "constraints": {
    "hard": [
      {"id": "max-consecutive-days", "type": "max_consecutive_days", "params": {"window": 6, "max_worked": 5}, "enabled": true},
      {"id": "vacation-days", "type": "vacation_block", "params": {}, "enabled": true}
    ],
    "soft": [
      {"id": "min-coverage", "type": "min_coverage", "params": {"penalty_per_missing": 1000}, "weight": 1000, "enabled": true}
    ]
  },

  "optimization": {
    "algorithm": "CSPv2",
    "maxTimeMinutes": 10,
    "objectives": [
      {"goal": "minimize_shortages", "weight": 1000, "priority": 1},
      {"goal": "balance_workload", "weight": 10, "priority": 2}
    ]
  }
}
```

### Step 5: Validate
Check that:
- All employee IDs in schedule_input.csv match employees in problem.json
- All shifts in demand.csv match shifts in problem.json
- All teams in demand.csv match teams in problem.json
- All dates are within temporalScope.targetPeriod
- No duplicate rows in demand.csv

---

## Common Validation Errors

### Error: "Employee ID not found"
**Problem**: Employee ID in schedule_input.csv doesn't match any employee in problem.json
**Solution**: Check spelling, ensure employee is defined in JSON

### Error: "Shift code not found"
**Problem**: Shift code in demand.csv doesn't match any shift in problem.json
**Solution**: Define the shift in demand.shifts[] array

### Error: "Team code not found"
**Problem**: Team code in demand.csv doesn't match organizationalUnits.teams[]
**Solution**: Add the team to organizationalUnits.teams[] array

### Error: "Date out of range"
**Problem**: Date in CSV is outside temporalScope.targetPeriod
**Solution**: Check start/end dates in temporalScope

### Error: "Invalid constraint"
**Problem**: minimum > ideal or estimated > ideal
**Solution**: Ensure minimum <= estimated <= ideal

---

## Tips for Large Problems (365+ days)

### Use Spreadsheet Formulas
Excel/LibreOffice can help generate large CSVs:

**For demand.csv**:
```
= IF(WEEKDAY(A2) IN {1,7}, "weekend_value", "weekday_value")
```

**For schedule_input.csv**:
```
Start with all "A", then manually mark exceptions
```

### Pattern-Based Generation
1. Create a 1-week pattern
2. Copy/paste for entire year
3. Manually adjust for holidays/special events

### Version Control
- Keep templates in version control
- Track changes to CSV files
- Use meaningful commit messages

---

## Next Steps

1. **See working examples**: Check `../examples/` directory for complete examples
2. **Read full documentation**: See `../FORMAT.md` for complete schema reference
3. **Validate your files**: Use JSON Schema validation for problem.json
4. **Test with small dataset**: Start with 7-14 days before scaling up

---

## Need Help?

- **Format questions**: See `../FORMAT.md`
- **Examples**: See `../examples/`
- **Schema reference**: See `../schema.json`
- **Quick start**: See `../README.md`

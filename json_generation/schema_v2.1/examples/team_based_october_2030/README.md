# Team-Based October 2030 Scheduling Example

Complete working example of team-based employee scheduling for October 2030.

## Overview

This example demonstrates a simple team-based scheduling problem derived from a real-world Excel spreadsheet (2030Exemplo2.xlsx). It showcases basic scheduling features without advanced competency models.

## Problem Characteristics

### Temporal Scope
- **Period**: October 1-31, 2030 (31 days)
- **Year**: 2030
- **Day types**: Weekdays and weekends

### Employees (7 total)
- **Employee 20072412**: Team EG
- **Employee 20066543**: Team EG
- **Employee 20067009**: Teams CAJ, EG (multi-team)
- **Employee 20054956**: Teams CAJ, EG (multi-team)
- **Employee 20056459**: Team CAJ
- **Employee 20062688**: Teams CAJ, EG (multi-team, has vacation)
- **Employee 20067696**: Team CAJ

### Teams (2)
- **EG**: Management Team
- **CAJ**: Cashier

(Note: ALM and HOSS teams are defined but have no employees assigned in this example)

### Shifts (2)
- **M (Morning)**: 08:30 - 16:30
  - Includes 30-minute meal break between 12:00-14:30
- **T (Afternoon)**: 14:00 - 22:00
  - Includes 30-minute meal break after 240 minutes

### Coverage Requirements
- **Weekdays**: Both M and T shifts for both teams
- **Weekends**: Only M shift for both teams
- **Total demand rows**: 109 (31 days × varying shifts/teams)

**Typical weekday coverage**:
- EG Morning: minimum=1, ideal=2, estimated=1
- EG Afternoon: minimum=1, ideal=1, estimated=1
- CAJ Morning: minimum=2, ideal=3, estimated=2
- CAJ Afternoon: minimum=2, ideal=4, estimated=3

**Typical weekend coverage**:
- EG Morning: minimum=1, ideal=1, estimated=1
- CAJ Morning: minimum=1, ideal=2, estimated=1
- No afternoon shifts on weekends

## Features Demonstrated

### ✅ Enabled Features
- `useShiftBasedScheduling`: true
- `useCompetencyModel`: false (using simple team model)
- `usePriorityHierarchy`: true
- `useAdvancedConstraints`: false

### Employee Model
- **Type**: Team-based (`employees.model="team"`)
- **Multi-team support**: Some employees can work in multiple teams
- **No skill levels**: Simple team membership only

### Priority Hierarchy
Defines allocation order when resources are scarce:
1. **Rank 1**: ALM (Warehouse) - Highest priority
2. **Rank 2**: HOSS - High priority
3. **Rank 3**: EG (Management) - Medium priority
4. **Rank 4**: CAJ (Cashier) - Standard priority

### Constraints
**Hard constraints**:
- Max 5 consecutive workdays in any 6-day window
- Minimum 11 hours rest between shifts
- Total workdays: 223 per year
- Max 22 special days (Sundays/holidays)
- No backward shift transitions (T→M, N→M forbidden)
- Vacation days must be respected

**Soft constraints**:
- Minimize coverage shortages (penalty: 1000 per missing person)
- Balance workload (penalty: 10 per imbalance)

### Availability Constraints
- **Employee 20062688 has vacation**: Oct 2-7, 2030
- Other employees: Mostly available (marked "A")
- Some scheduled days off (marked "DL")
- One specific time window constraint (Oct 6: 10:00-14:00)

## Files in This Example

### problem.json
Complete problem definition including:
- Metadata (problem ID, creation date, source)
- Feature flags
- Temporal scope (October 2030)
- 7 employees with team assignments
- 2 teams (EG, CAJ)
- 2 shifts with breaks
- Priority hierarchy
- Constraints (hard and soft)
- Optimization settings (CSPv2 algorithm, 10-minute timeout)

### demand.csv
109 rows of daily coverage requirements:
- Format: `date,shift,team,minimum,ideal,estimated`
- Covers all 31 days of October 2030
- Different patterns for weekdays vs weekends
- EG and CAJ teams with varying requirements

### schedule_input.csv
Employee availability matrix:
- 7 rows (one per employee)
- 31 columns (one per day in October)
- Values: A (available), DL (day off), VAC (vacation), time windows
- Notable: Employee 20062688 has 6-day vacation block

## How to Use This Example

### As a Learning Tool
1. **Read problem.json** - Understand the JSON structure
2. **Open demand.csv in Excel** - See how coverage requirements work
3. **Open schedule_input.csv in Excel** - See constraint format
4. **Compare with templates** - Check against `../../templates/`

### As a Starting Point
```bash
# Copy this example
cp -r examples/team_based_october_2030/ my_problem/

# Modify for your needs
cd my_problem/

# Edit problem.json
# - Change metadata (problemId, createdAt, description)
# - Update temporalScope dates
# - Modify employees list
# - Adjust teams and shifts
# - Update constraints

# Edit demand.csv
# - Update dates to match new temporal scope
# - Adjust minimum/ideal/estimated values
# - Add or remove teams as needed

# Edit schedule_input.csv
# - Update employee IDs to match problem.json
# - Update date columns to match temporal scope
# - Mark vacations and constraints
```

### Key Modifications

**To change the time period**:
1. Update `temporalScope.targetPeriod.start` and `end`
2. Update `temporalScope.numDays`
3. Regenerate demand.csv with new dates
4. Regenerate schedule_input.csv with new date columns

**To add/remove employees**:
1. Add/remove from `employees.simple[]` in problem.json
2. Add/remove rows in schedule_input.csv
3. Ensure team assignments are valid

**To change coverage requirements**:
1. Edit demand.csv minimum/ideal/estimated values
2. Add/remove rows for different team/shift combinations
3. Consider weekday vs weekend patterns

**To modify shifts**:
1. Update `demand.shifts[]` definitions
2. Adjust shift codes, times, breaks
3. Update demand.csv shift column to use new codes

## Validation Checklist

Before using as a template, verify:

- [ ] All employee IDs in schedule_input.csv match problem.json
- [ ] All shift codes in demand.csv exist in problem.json shifts[]
- [ ] All team codes in demand.csv exist in organizationalUnits.teams[]
- [ ] All dates in CSVs are within temporal scope
- [ ] No duplicate rows in demand.csv
- [ ] schedule_input.csv has correct number of date columns (31)
- [ ] JSON validates against schema.json

## Expected Outputs

When this problem is solved by the scheduling algorithm, it should produce:
- A schedule assigning each employee to shifts
- Respect for all hard constraints
- Attempt to meet ideal coverage levels
- Balanced workload across employees
- Respect for vacation/availability constraints

## Notes

- This example uses simplified team model (no competency levels)
- Priority hierarchy is defined but may not significantly impact results given balanced demand
- Algorithm choice (CSPv2) is suitable for this problem size
- 10-minute timeout is usually sufficient for 7 employees × 31 days

## References

- **Source**: 2030Exemplo2.xlsx
- **Schema Version**: 2.1
- **Last Updated**: January 2026

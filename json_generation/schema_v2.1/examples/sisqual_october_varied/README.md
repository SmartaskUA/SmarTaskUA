# Sisqual October Varied Example

Algorithm stress test with adjusted resource distribution and varying demand levels for October 2025.

## Overview

This example is a variation of the base sisqual_example, designed to test the scheduling algorithm with:
- Adjusted employee distribution across teams
- Varied ideal/estimated coverage values to provide optimization opportunities
- Realistic availability constraints

## Problem Characteristics

### Temporal Scope
- **Period**: October 1-31, 2025 (31 days)
- **Year**: 2025
- **Start day**: Wednesday, October 1
- **Day types**: Weekdays, Saturdays, Sundays

### Employees (18 total)

**Competency Model with Multi-Team Support**

#### Management Team (7 employees)
- **Emp_20072412**: Management (level 1) - High skill
- **Emp_20066543**: Management (level 2)
- **Emp_20072413**: Management (level 2) - NEW
- **Emp_20067009**: Checkout (level 1), Management (level 3) - Multi-competency
- **Emp_20054956**: Checkout (level 2), Management (level 4) - Multi-competency
- **Emp_20062688**: Checkout (level 3), Management (level 4) - Multi-competency
- **Emp_20072414**: Management (level 3), Storage (level 2) - Multi-competency, NEW

#### Checkout Team (9 employees)
- **Emp_20056459**: Checkout (level 1)
- **Emp_20067696**: Checkout (level 2)
- **Emp_20058959**: Checkout (level 2)
- **Emp_20068397**: Checkout (level 2)
- **Emp_20038706**: Checkout (level 2)
- **Emp_20066338**: Checkout (level 3)
- **Emp_900027719**: Checkout (level 4)
- **Emp_20055066**: Checkout (level 4)
- **Emp_20051293**: Storage (level 1), Checkout (level 4) - Multi-competency, NEW

#### Storage Team (3 employees)
- **Emp_20051291**: Storage (level 1)
- **Emp_20051292**: Storage (level 2) - NEW
- **Emp_20051293**: Storage (level 1), Checkout (level 4) - Multi-competency, NEW

Note: Some employees have multi-competency and can work in multiple teams.

### Teams (3)
- **Management**: Supervisory and administrative roles
- **Checkout**: Customer service and cashier operations
- **Storage**: Inventory and warehouse operations

### Shifts (9 total)
All shifts use descriptive codes without breaks:

**Storage**:
- **STORAGE_0830_1530**: 08:30 - 15:30 (7 hours)

**Checkout**:
- **CHECKOUT_1000_1100**: 10:00 - 11:00 (1 hour)
- **CHECKOUT_1100_2100**: 11:00 - 21:00 (10 hours)
- **CHECKOUT_2100_2200**: 21:00 - 22:00 (1 hour)

**Management**:
- **MANAGEMENT_1000_1100**: 10:00 - 11:00 (1 hour)
- **MANAGEMENT_1100_1400**: 11:00 - 14:00 (3 hours)
- **MANAGEMENT_1400_1900**: 14:00 - 19:00 (5 hours)
- **MANAGEMENT_1900_2100**: 19:00 - 21:00 (2 hours)
- **MANAGEMENT_2100_2200**: 21:00 - 22:00 (1 hour)

### Coverage Requirements (Varied for Algorithm Testing)

**Weekday Pattern** (Mon-Fri, 22 days):
- Storage 08:30-15:30: min=1, ideal=2, estimated=1
- Checkout 10:00-11:00: min=1, ideal=2, estimated=1
- Checkout 11:00-21:00: min=1, ideal=3, estimated=2
- Checkout 21:00-22:00: min=1, ideal=2, estimated=1
- Management 10:00-11:00: min=1, ideal=2, estimated=1
- Management 11:00-14:00: min=1, ideal=2, estimated=1
- Management 14:00-19:00: min=1, ideal=3, estimated=2
- Management 19:00-21:00: min=1, ideal=2, estimated=1
- Management 21:00-22:00: min=1, ideal=1, estimated=1

**Saturday Pattern** (4 days):
- Checkout 11:00-21:00: min=1, ideal=2, estimated=1
- Management 11:00-14:00: min=1, ideal=2, estimated=1
- Management 14:00-19:00: min=1, ideal=2, estimated=2
- Management 19:00-21:00: min=1, ideal=1, estimated=1

**Sunday Pattern** (5 days):
- Checkout 11:00-21:00: min=1, ideal=2, estimated=1
- Management 11:00-14:00: min=1, ideal=1, estimated=1
- Management 19:00-21:00: min=1, ideal=1, estimated=1

**Total demand rows**: 235

## Features Demonstrated

### ✅ Enabled Features
- `useShiftBasedScheduling`: true
- `usePriorityHierarchy`: true
- `useAdvancedConstraints`: false

### Employee Model
- **Type**: Competency-based (`employees.model="competency"`)
- **Multi-competency support**: Several employees can work across multiple teams
- **Skill levels**: Employees have different skill levels (1=highest, 5=lowest)

### Priority Hierarchy
Defines allocation order when resources are scarce:
1. **Rank 1**: Management - Highest priority
2. **Rank 2**: Checkout - Medium priority
3. **Rank 3**: Storage - Standard priority

### Constraints

**Hard constraints**:
- Minimum 11 hours rest between shifts
- Vacation days must be respected

**Soft constraints**:
- Minimize coverage shortages (penalty: 1000 per missing person)
- Balance workload (penalty: 10 per imbalance)

### Availability Constraints

Multiple employees have various constraints:
- **Vacations (VAC)**: Multi-day vacation blocks
- **Unavailable (NOT)**: Single days completely unavailable
- **Day Off (DO)**: Scheduled day off
- **Medical (Med)**: Medical leave periods
- **Time Constraints**: Specific time windows (e.g., "10:00-14:00")

Notable constraints:
- Emp_20072412: Vacation Oct 13-19
- Emp_20066543: Vacation Oct 20-26
- Emp_20062688: Two vacation blocks (Oct 2-12 and Oct 27-31)
- Emp_20055066: Medical leave Oct 1-12
- Emp_20056459: Time constraint Oct 7 (10:00-14:00)

## Algorithm Stress Test Aspects

This example is designed to challenge the scheduling algorithm:

1. **Resource Scarcity**: Only 3 Storage employees with ideal demand of 2
2. **Varied Demand**: Different ideal vs. minimum values create optimization opportunities
3. **Multi-Competency**: Employees with multiple skills require smart allocation
4. **Priority Conflicts**: Priority hierarchy must be balanced with coverage needs
5. **Availability Challenges**: Overlapping vacations and constraints

## Files in This Example

### problem.json
Complete problem definition including:
- Metadata (problem ID, creation date, source)
- Feature flags (competency model, priority hierarchy)
- Temporal scope (October 2025)
- 18 employees with competency assignments and skill levels
- 3 competencies (Storage, Checkout, Management)
- 9 shifts without breaks
- Priority hierarchy
- Minimal constraints (rest hours, vacation blocks)
- Optimization settings (CSPv2 algorithm, 10-minute timeout)

### demand.csv
235 rows of daily coverage requirements with varied ideal/estimated values:
- Format: `date,shift,team,minimum,ideal,estimated`
- Covers all 31 days of October 2025
- Different patterns for weekdays vs. weekends
- Varied ideal values to test algorithm optimization

### schedule_input.csv
Employee availability matrix:
- 18 rows (one per employee)
- 31 columns (one per day in October)
- Values: A (available), VAC (vacation), NOT (unavailable), DO (day off), Med (medical), time windows
- Multiple employees with vacation blocks and constraints

## Expected Behavior

When this problem is solved by the scheduling algorithm, it should:
- Test resource allocation under scarcity
- Optimize between minimum and ideal coverage levels
- Leverage multi-competency employees effectively
- Respect priority hierarchy while meeting coverage
- Balance workload across employees
- Handle overlapping availability constraints

## Comparison to Base Example

**Differences from sisqual_example**:
- 18 employees (vs. 15)
- 3 Storage employees (vs. 1)
- Reduced Checkout employees (9 vs. 12)
- Varied ideal/estimated values (vs. all equal to minimum)
- More multi-competency employees (4 vs. 3)
- Added workload balancing objective

## Notes

- Uses competency model with skill levels for flexible allocation
- Priority hierarchy helps when ideal coverage cannot be met
- Algorithm must optimize between minimum (feasible) and ideal (desired) levels
- CSPv2 algorithm is suitable for this problem size
- 10-minute timeout is usually sufficient for 18 employees × 31 days

## References

- **Based on**: sisqual_example
- **Schema Version**: 2.1
- **Created**: January 2026

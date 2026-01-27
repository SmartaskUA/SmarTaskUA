# Sisqual Full Year 2025 Example

Complete annual employee scheduling for 2025 with seasonal patterns and distributed vacations.

## Overview

This example demonstrates a real-world production scenario for annual employee scheduling with:
- Full calendar year coverage (365 days)
- Realistic vacation distribution across all months
- Seasonal business patterns
- Multi-competency employee model
- Complex availability constraints

## Problem Characteristics

### Temporal Scope
- **Period**: January 1 - December 31, 2025 (365 days)
- **Year**: 2025
- **Scale**: Large-scale annual planning problem
- **Day types**: Weekdays, Saturdays, Sundays, Holidays

### Employees (15 total)

**Competency Model with Multi-Team Support**

#### Management Team (5 employees)
- **Emp_20072412**: Management (level 1) - Senior management
- **Emp_20066543**: Management (level 2)
- **Emp_20067009**: Checkout (level 1), Management (level 3) - Multi-competency
- **Emp_20054956**: Checkout (level 2), Management (level 4) - Multi-competency
- **Emp_20062688**: Checkout (level 3), Management (level 4) - Multi-competency

#### Checkout Team (10 employees)
- **Emp_20056459**: Checkout (level 1)
- **Emp_20067696**: Checkout (level 2)
- **Emp_20058959**: Checkout (level 2)
- **Emp_20068397**: Checkout (level 2)
- **Emp_20038706**: Checkout (level 2)
- **Emp_20066338**: Checkout (level 3)
- **Emp_900027719**: Checkout (level 4)
- **Emp_20055066**: Checkout (level 4)
- **Emp_900027718**: Checkout (level 5)
- Plus 3 multi-competency employees from Management

#### Storage Team (1 employee)
- **Emp_20051291**: Storage (level 1)

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

### Coverage Requirements with Seasonal Patterns

**Standard Weekday Pattern** (Mon-Fri, most of year):
- Storage 08:30-15:30: minimum=1
- Checkout 10:00-11:00: minimum=1
- Checkout 11:00-21:00: minimum=1
- Checkout 21:00-22:00: minimum=1
- Management 10:00-11:00: minimum=1
- Management 11:00-14:00: minimum=1
- Management 14:00-19:00: minimum=1
- Management 19:00-21:00: minimum=1
- Management 21:00-22:00: minimum=1

**Standard Weekend Pattern** (Sat-Sun):
- Saturday: Checkout + 4 Management shifts
- Sunday: Checkout + 2 Management shifts (reduced)

**Winter Holiday Period** (Dec 24-31):
- Reduced coverage for holiday period
- Weekdays: 3 shifts only
- Weekends: Minimal coverage

**Total demand rows**: 2,673

## Features Demonstrated

### ✅ Enabled Features
- `useShiftBasedScheduling`: true
- `usePriorityHierarchy`: true
- `useAdvancedConstraints`: false

### Employee Model
- **Type**: Competency-based (`employees.model="competency"`)
- **Multi-competency support**: 3 employees can work across multiple teams
- **Skill levels**: Different skill levels (1=highest, 5=lowest)

### Priority Hierarchy
1. **Rank 1**: Management - Highest priority
2. **Rank 2**: Checkout - Medium priority
3. **Rank 3**: Storage - Standard priority

### Constraints

**Hard constraints**:
- Minimum 11 hours rest between shifts
- Vacation days must be respected
- Maximum 6 consecutive workdays in any 7-day window

**Soft constraints**:
- Minimize coverage shortages (penalty: 1000 per missing person)
- Balance workload across employees (penalty: 10 per imbalance)

### Vacation Distribution Strategy

**Annual Vacation Allocation**:
- Average: 26.3 vacation days per employee
- Total: 394 vacation days across all employees
- Distribution: 2-3 vacation blocks per employee

**Seasonal Pattern**:
- **Summer preference**: ~60% of vacations occur June-September
- **Year-round coverage**: Vacations distributed across all 12 months
- **Staggered scheduling**: Employees don't vacation simultaneously
- **Realistic blocks**: 5-14 consecutive days per vacation block

**Vacation Blocks by Employee**:
- Emp_20072412: Mar (7d), Jul (10d), Oct (5d)
- Emp_20066543: Feb (7d), Jul (14d), Nov (5d)
- Emp_20067009: Apr (7d), Jul (10d), Dec (7d)
- Emp_20054956: Mar (5d), Jun (10d), Aug (7d), Nov (3d)
- Emp_20056459: May (7d), Jul (14d), Nov (5d)
- Emp_20062688: Jan (10d), Jun (12d), Oct (7d)
- Emp_20067696: Mar (7d), Jul (14d), Oct (5d)
- Emp_20058959: Feb (7d), Jun (10d), Sep (7d), Dec (3d)
- Emp_20068397: Apr (7d), Jul (12d), Nov (7d)
- Emp_20038706: Mar (7d), Jul (10d), Sep (7d), Dec (5d)
- Emp_20066338: Feb (7d), Jun (14d), Oct (5d)
- Emp_900027719: Apr (7d), Aug (10d), Nov (7d)
- Emp_20051291: Feb (7d), Jun (10d), Sep (7d), Dec (3d)
- Emp_20055066: Jan (12d Med), Aug (14d), Oct (5d)
- Emp_900027718: Apr (7d), Jul (12d), Oct (7d)

### Additional Availability Constraints

**Periodic Day Offs**:
- Most employees have 1-2 scheduled day offs per month
- Different patterns per employee (weekends, mid-month, etc.)

**Time Constraints**:
- Emp_20056459: Quarterly time windows (10:00-14:00)
- Emp_20066338: Semi-annual time windows (11:00-16:00)

**Unavailability**:
- Emp_20058959: Occasional NOT days (Jan 1, late May)

**Medical Leave**:
- Emp_20055066: 12-day medical leave at year start

## Seasonal Business Patterns

### Summer Period (June-August)
- High vacation frequency
- Standard coverage requirements maintained
- Multiple employees may be on vacation concurrently (but coverage ensured)

### Winter Holiday Period (Dec 24-31)
- Reduced operational hours
- Minimal staffing requirements
- Fewer shifts scheduled

### Spring/Fall (Mar-May, Sep-Nov)
- Moderate vacation frequency
- Standard business operations
- Balanced workload distribution

## Files in This Example

### problem.json
Complete problem definition including:
- Metadata for annual scheduling
- Feature flags (competency model, priority hierarchy)
- Temporal scope (full year 2025, 365 days)
- 15 employees with competency assignments and skill levels
- 3 competencies (Storage, Checkout, Management)
- 9 shifts without breaks
- Priority hierarchy
- Enhanced constraints (rest hours, vacation blocks, consecutive workdays)
- Optimization settings (CSPv2 algorithm, 60-minute timeout for large scale)

### demand.csv
2,673 rows of daily coverage requirements:
- Format: `date,shift,team,minimum,ideal,estimated`
- Covers all 365 days of 2025
- Seasonal variations (winter holiday reductions)
- Different patterns for weekdays vs. weekends

### schedule_input.csv
Employee availability matrix for full year:
- 15 rows (one per employee)
- 365 columns (one per day in 2025)
- Values: A (available), VAC (vacation), DO (day off), Med (medical), time windows, NOT (unavailable)
- 394 total vacation days distributed across employees
- Periodic day-offs throughout the year
- Occasional time constraints and unavailability

## Expected Behavior

When this problem is solved by the scheduling algorithm, it should:
- Generate a complete annual schedule respecting all 394 vacation days
- Handle seasonal demand variations
- Balance workload across full year
- Respect maximum consecutive workdays constraint
- Leverage multi-competency employees during vacation periods
- Optimize coverage during high-vacation summer months
- Maintain minimum coverage during winter holiday period

## Optimization Considerations

**Algorithm Selection**:
- Uses CSPv2 (Constraint Satisfaction Problem solver v2)
- Extended timeout: 60 minutes (vs. 10 min for monthly problems)
- Suitable for large-scale problems (15 employees × 365 days)

**Challenge Aspects**:
1. **Scale**: 5,475 employee-day combinations to schedule
2. **Vacation Coordination**: Ensuring coverage with 394 vacation days
3. **Long-term Balancing**: Workload equity over full year
4. **Seasonal Patterns**: Adapting to business cycles
5. **Multi-competency Utilization**: Optimal allocation across teams

## Comparison to Monthly Examples

**Differences from sisqual_example and sisqual_october_varied**:
- 365 days (vs. 31 days)
- 2,673 demand rows (vs. 235 rows)
- 365 date columns (vs. 31 columns)
- Distributed vacations (vs. concentrated in single month)
- Seasonal patterns (vs. uniform coverage)
- 60-minute timeout (vs. 10 minutes)
- Added consecutive workdays constraint
- Realistic annual vacation allocation

## Usage Notes

- This example represents a production-scale scheduling problem
- Solver may require significant computational resources
- Results can be analyzed for annual workload distribution
- Vacation patterns ensure no simultaneous team-wide absences
- Suitable for testing annual planning algorithms

## Validation Checklist

Before using:
- [ ] All 15 employee IDs present in schedule_input.csv
- [ ] All 365 dates included (Jan 1 - Dec 31, 2025)
- [ ] Vacation blocks don't cause coverage failures
- [ ] Seasonal patterns correctly implemented
- [ ] Total vacation days within reasonable range (20-30 per employee)
- [ ] No employee has all days as VAC
- [ ] Priority hierarchy aligns with business needs

## Performance Expectations

**Solver Performance**:
- Problem size: Large (15 employees × 365 days)
- Expected solve time: 10-60 minutes depending on hardware
- Memory requirements: Moderate to high
- Feasibility: Should find feasible solution if vacations are well-distributed

**Output Analysis**:
- Review workload balance across full year
- Check vacation coverage strategies
- Analyze seasonal staffing patterns
- Verify consecutive workday compliance

## References

- **Based on**: sisqual_example
- **Schema Version**: 2.1
- **Created**: January 2026
- **Scope**: Production annual scheduling scenario

# Time Window Constraints Example

This example demonstrates the new v2.2 time window constraint features: `ONLY`, `ATLEAST`, and `NOT`.

## Overview

This example shows how to use time window constraints in `schedule_input.csv` to control when employees can work with precision.

## Features Demonstrated

### Three Time Window Constraint Types

1. **ONLY:HH:MM-HH:MM** - Employee must work EXACTLY this time range
2. **ATLEAST:HH:MM-HH:MM** - Employee must cover this entire range minimum (can extend)
3. **NOT:HH:MM-HH:MM** - Employee unavailable during this time window

### Mixed Constraint Usage

The example shows how to combine:
- Auto-allocation (`A`)
- Specific hours (`4`, `6`, `8`)
- Time window constraints (`ONLY`, `ATLEAST`, `NOT`)
- Day-off markers (`DL`)
- Vacation markers (`VAC`)

## Schedule Breakdown

### EMP001 - Regular Full-Time with Fixed Day
```
Oct-01: A (auto-allocate from contract)
Oct-02: A (auto-allocate)
Oct-03: 8 (exactly 8 hours, algorithm chooses time)
Oct-04: ONLY:08:00-16:00 (must work exactly 8 AM to 4 PM)
Oct-05: A (auto-allocate)
Oct-06: DL (day off)
Oct-07: DL (day off)
```
**Use Case:** Regular employee with one fixed schedule day

### EMP002 - Flexible with Coverage Requirements
```
Oct-01: ATLEAST:09:00-17:00 (must cover 9-5, could work 8-6)
Oct-02: A
Oct-03: 6 (exactly 6 hours)
Oct-04: A
Oct-05: ONLY:14:00-22:00 (must work exactly 2 PM to 10 PM)
Oct-06: A
Oct-07: DL
```
**Use Case:** Employee who must be present during core hours on specific days

### EMP003 - Morning Preference with Exclusion
```
Oct-01: NOT:14:00-22:00 (unavailable afternoons/evenings)
Oct-02: A
Oct-03: DL
Oct-04: A
Oct-05: A
Oct-06: ONLY:08:30-16:30 (specific morning shift)
Oct-07: A
```
**Use Case:** Employee who cannot work afternoons/evenings (family commitments, classes)

### EMP004 - Part-Time with Afternoon Exclusion
```
Oct-01: DL
Oct-02: ATLEAST:10:00-15:00 (must cover lunch period)
Oct-03: 4 (exactly 4 hours)
Oct-04: A
Oct-05: NOT:06:00-14:00 (unavailable mornings)
Oct-06: DL
Oct-07: A
```
**Use Case:** Part-time employee with specific availability constraints

### EMP005 - Night Shift Worker
```
Oct-01: ONLY:22:00-06:00 (night shift only)
Oct-02: DL
Oct-03: A
Oct-04: 8
Oct-05: A
Oct-06: ATLEAST:08:00-20:00 (long coverage day)
Oct-07: DL
```
**Use Case:** Night shift worker with occasional day flexibility

### EMP006 - Afternoon/Evening Worker
```
Oct-01: A
Oct-02: NOT:08:00-16:00 (unavailable during standard business hours)
Oct-03: DL
Oct-04: ONLY:09:00-17:00 (specific fixed schedule)
Oct-05: 6
Oct-06: A
Oct-07: A
```
**Use Case:** Employee with morning unavailability (other job, classes)

### EMP007 - Vacation
```
Oct-01-07: VAC (vacation all week)
```
**Use Case:** Employee on vacation

### EMP008 - Complex Mixed Constraints
```
Oct-01: 8 (specific hours)
Oct-02: ONLY:08:00-16:00 (fixed morning)
Oct-03: NOT:14:00-22:00 (no afternoons)
Oct-04: A
Oct-05: DL
Oct-06: ATLEAST:09:00-17:00 (coverage requirement)
Oct-07: A
```
**Use Case:** Employee with varying constraint types throughout the week

## Key Insights

### When to Use Each Constraint Type

**Use `A` (Auto-allocate):**
- Employee is fully flexible
- Let algorithm optimize based on demand
- Relies on contract `workHoursPerDay`

**Use numeric hours (4, 6, 8):**
- Need specific hour count but flexible on timing
- Part-time employees with exact hour requirements
- Overtime or reduced hour days

**Use `ONLY:HH:MM-HH:MM`:**
- Employee has fixed schedule requirement
- Legal restrictions (e.g., minors, part-time limits)
- Equipment access windows
- Coordination with external commitments

**Use `ATLEAST:HH:MM-HH:MM`:**
- Coverage during critical periods (lunch rush, peak hours)
- Supervision overlap requirements
- Core hours presence mandates
- Training/mentoring needs

**Use `NOT:HH:MM-HH:MM`:**
- Personal unavailability (school, other job, family)
- Medical restrictions
- Avoiding specific shift types
- Partial day availability

## Integration with Work Periods

Assuming work periods are defined as:
```json
"workPeriods": [
  {"code": "M", "name": "Morning", "timeRange": {"start": "08:30", "end": "16:30"}},
  {"code": "T", "name": "Afternoon", "timeRange": {"start": "14:00", "end": "22:00"}},
  {"code": "N", "name": "Night", "timeRange": {"start": "22:00", "end": "06:30"}}
]
```

The time window constraints filter which work periods employees can be assigned to:
- `ONLY:08:00-16:00` → Can work Morning (M) shift only
- `NOT:14:00-22:00` → Cannot work Afternoon (T) shift
- `ATLEAST:09:00-17:00` → Could work Morning (M) or extended shift
- `ONLY:22:00-06:00` → Can work Night (N) shift only
- `NOT:08:00-16:00` → Cannot work Morning (M) shift

## Validation

This example should validate successfully if:
1. All time ranges have start < end
2. No contradictory constraints on same day
3. Times align with or overlap defined work periods
4. Employee IDs exist in the problem JSON

## Real-World Applications

This constraint model supports:
- **Retail:** Students available only evenings/weekends
- **Healthcare:** Doctors with specific clinic hours
- **Hospitality:** Staff with other jobs or commitments
- **Manufacturing:** Operators certified for specific shift equipment
- **Call Centers:** Agents covering specific service windows
- **Food Service:** Cooks needed during meal preparation times

## Next Steps

To use this example:
1. Create corresponding `problem.json` with employee definitions
2. Define work periods that align with constraint times
3. Create `demand.csv` specifying coverage requirements
4. Run validator to ensure consistency
5. Execute scheduling algorithm with time constraint support

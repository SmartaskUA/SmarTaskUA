# Schema v2.5 Templates

This directory contains template files to help you create your own scheduling problems.

## Quick Start

1. **Copy the templates:**
   ```bash
   cp templates/schedule_input_template.csv my_schedule_input.csv
   cp templates/demand_template.csv my_demand.csv
   cp templates/operating_hours_template.csv my_operating_hours.csv  # NEW in v2.5
   ```

2. **Read the extensive comments** in each template file

3. **Delete all comment lines** (lines starting with `#`)

4. **Fill in your data**

5. **Create your problem.json** (see examples/ directory)

6. **Validate:**
   ```bash
   python3 validator/validator.py path/to/problem.json -v
   ```

## What's New in v2.5

**Operating Hours Management:**
- New `operating_hours_template.csv` for defining when facility/teams are open
- Supports store-wide hours (ALL) and team-specific hours
- CLOSED support for holidays and non-operating days
- Hard constraint enforcement in algorithm

## Important v2.2 Changes

### Standard vs Custom Constraints

**v2.2 introduces a clear distinction between standard and custom constraints:**

**Standard Constraints (Always Valid):**
- `VAC` - Vacation (no definition needed)
- `NOT` - Unavailable (no definition needed)

**Custom Constraints (Must be Defined in JSON):**
- ALL other constraint codes (DL, DLF, DLV, DO, EnfD, Med, etc.)
- MUST be explicitly defined in `scheduleInput.markingTypes`

**Why this change?**
- Forces explicit documentation
- Makes constraints self-documenting per problem
- Prevents assumption of meaning
- Allows project-specific constraint codes

### How to Define Custom Constraints

In your `problem.json`, add markingTypes:

```json
{
  "scheduleInput": {
    "dataFile": "schedule_input.csv",
    "markingTypes": {
      "DL": "Day Off - Generic (can be swapped)",
      "DLF": "Fixed Day Off - Cannot be changed",
      "DO": "Day Off - Swappable with penalty",
      "EnfD": "Enfermidade - Sick leave",
      "Med": "Medical Appointment"
    }
  }
}
```

**Without this definition**, the validator will REJECT constraint codes like DL, DLF, etc.

## Template Files

### schedule_input_template.csv

Specifies work requirements and availability constraints for each employee.

**Key Features (v2.2):**
- Auto-allocation from contracts (`A`)
- Specific hour requirements (`4`, `6`, `8`)
- Time window constraints using Allen Interval Algebra:
  - `EQUALS:HH:MM-HH:MM` - Must work exactly this time range
  - `INCLUDE:HH:MM-HH:MM` - Must cover entire range minimum (can extend)
  - `EXCEPT:HH:MM-HH:MM` - Unavailable during this time window
- Standard constraints (`VAC`, `NOT`)
- Custom constraints (must be defined in JSON)

**Example rows:**
```csv
EMP001,A,A,8,NOT,EQUALS:08:00-16:00,A,VAC
EMP002,INCLUDE:09:00-17:00,A,6,A,VAC,A,NOT
EMP003,EXCEPT:14:00-22:00,A,NOT,A,A,A,A
```

### demand_template.csv

Specifies daily coverage requirements - how many people are needed.

**Columns:**
- `date` - Date for requirement (YYYY-MM-DD)
- `shift` - Shift code (M, T, N, etc.)
- `team` - Team code (used for both employee models)
- `minimum` - Minimum people (hard constraint)
- `ideal` - Ideal people (soft target)
- `estimated` - Expected demand (for KPIs)

**Example rows:**
```csv
2030-10-01,M,TeamA,2,3,2
2030-10-01,T,TeamA,2,2,2
```

### operating_hours_template.csv (v2.5 NEW)

Defines when the facility/store is open for business. Employees can only be scheduled during operating hours.

**Columns:**
- `date` - Date (YYYY-MM-DD)
- `team` - Team code or `ALL` for store-wide
- `open` - Opening time (HH:MM) or `CLOSED`
- `close` - Closing time (HH:MM) or `CLOSED`

**Key Features:**
- Complete coverage: Must have entry for all dates
- Team override: Specific team hours override `ALL`
- CLOSED support: Use `CLOSED,CLOSED` for non-operating days
- Hard constraint: Algorithm enforces operating hours

**Example rows:**
```csv
2025-10-01,ALL,08:00,22:00
2025-10-02,Storage,06:00,23:00
2025-10-02,Checkout,08:00,22:00
2025-12-25,ALL,10:00,16:00
2025-12-26,ALL,CLOSED,CLOSED
```

**Interpretation:**
- Oct-01: All teams 08:00-22:00
- Oct-02: Storage opens early, others normal
- Dec-25: Holiday reduced hours
- Dec-26: Facility closed

## Step-by-Step Guide

### Step 1: Define Your Problem Structure (JSON)

Create `problem.json` with:
- Contract definitions (workHoursPerDay, constraints) - v2.2
- Employee list with contract references
- **Operating hours configuration** - v2.5 NEW
- Shift/work period definitions
- Organizational units (teams - used for both employee models)
- Custom constraint definitions in markingTypes - v2.2

See `examples/` directory for complete examples.

### Step 2: Create Schedule Input (CSV)

1. Copy `schedule_input_template.csv`
2. Update column headers with your date range
3. Add one row per employee
4. Fill in values for each day:
   - `A` for auto-allocation from contract
   - Numbers (1-16) for specific hours
   - `EQUALS:HH:MM-HH:MM` for fixed schedules
   - `INCLUDE:HH:MM-HH:MM` for coverage requirements
   - `EXCEPT:HH:MM-HH:MM` for unavailability
   - `VAC`, `NOT` for standard constraints
   - Custom codes (DL, etc.) - MUST be defined in JSON first!

### Step 3: Create Demand Requirements (CSV)

1. Copy `demand_template.csv`
2. Add one row per date/shift/team combination
3. Specify minimum, ideal, and estimated requirements
4. Ensure: minimum ≤ estimated ≤ ideal

### Step 4: Create Operating Hours (CSV) - v2.5 NEW

1. Copy `operating_hours_template.csv`
2. Add entry for EVERY date in your temporal scope
3. Use `ALL` for store-wide hours, or specify team codes for team-specific hours
4. Use `CLOSED,CLOSED` for non-operating days (holidays, etc.)
5. Ensure times are in HH:MM format and open < close

**Example for 3 days:**
```csv
date,team,open,close
2025-10-01,ALL,08:00,22:00
2025-10-02,Storage,06:00,23:00
2025-10-02,Checkout,08:00,22:00
```

### Step 5: Validate Your Files

Run the validator to check for errors:
```bash
python3 validator/validator.py problem.json --verbose
```

The validator checks:
- JSON structure and schema compliance
- CSV format and data types
- Cross-validation (employee IDs, dates, shifts, teams)
- **Operating hours coverage and format (v2.5)**
- **Work periods fit within operating hours (v2.5)**
- Time window constraint format (v2.2)
- Contract references (v2.2)
- Custom constraint definitions (v2.2)

### Step 6: Run the Scheduler

Once validation passes, your files are ready for the scheduling algorithm.

## Time Window Constraints (v2.2)

Schema v2.2 introduces precise time control using Allen Interval Algebra operators:

### EQUALS:HH:MM-HH:MM

**Meaning:** Employee must work EXACTLY this time range.

**Use When:**
- Employee has fixed schedule requirements
- Legal restrictions (e.g., part-time staff must finish by 6 PM)
- Equipment access windows
- Coordination with external commitments

**Example:**
```csv
EMP001,EQUALS:08:00-16:00,A,A,EQUALS:09:00-17:00,VAC
```
Employee must work exactly 8 AM-4 PM on Oct-01 and exactly 9 AM-5 PM on Oct-04.

### INCLUDE:HH:MM-HH:MM

**Meaning:** Employee must work the ENTIRE specified range as a minimum (can start earlier or end later).

**Use When:**
- Coverage during critical periods (lunch rush, peak hours)
- Supervision overlap requirements
- Core hours presence mandates
- Training/mentoring needs

**Example:**
```csv
EMP002,INCLUDE:09:00-17:00,A,INCLUDE:10:00-15:00,A,VAC
```
Employee must be present 9 AM-5 PM on Oct-01 (could work 8 AM-6 PM) and cover 10 AM-3 PM on Oct-03 (minimum).

### EXCEPT:HH:MM-HH:MM

**Meaning:** Employee is completely UNAVAILABLE during this time window.

**Use When:**
- Personal unavailability (school, other job, family)
- Medical restrictions
- Avoiding specific shift types
- Partial day availability

**Example:**
```csv
EMP003,EXCEPT:14:00-22:00,A,EXCEPT:06:00-12:00,A,VAC
```
Employee cannot work 2 PM-10 PM on Oct-01 (can work mornings) and cannot work 6 AM-12 PM on Oct-03 (can work afternoons).

### Mixing Constraint Types

You can mix different constraint types across days:

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP001,A,EQUALS:08:00-16:00,8,INCLUDE:09:00-17:00,NOT
EMP002,EXCEPT:14:00-22:00,NOT,6,A,VAC
```

## Common Patterns

### Pattern 1: Full-Time Employees with Flexible Hours

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP001,A,A,A,A,VAC
EMP002,A,A,A,NOT,NOT
```

Uses contract `workHoursPerDay` for all working days.

### Pattern 2: Part-Time with Specific Hours

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP003,4,4,NOT,4,4
EMP004,6,NOT,6,6,VAC
```

Specifies exact hours needed each day.

### Pattern 3: Fixed Schedule Requirements

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP005,EQUALS:08:00-16:00,EQUALS:08:00-16:00,NOT,EQUALS:08:00-16:00,EQUALS:08:00-16:00
```

Employee must work exactly 8 AM-4 PM every working day.

### Pattern 4: Core Hours Coverage

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP006,INCLUDE:09:00-17:00,INCLUDE:09:00-17:00,NOT,INCLUDE:09:00-17:00,VAC
```

Employee must be present during core hours (can work extended hours).

### Pattern 5: Partial Availability

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP007,EXCEPT:14:00-22:00,A,EXCEPT:06:00-14:00,A,NOT
```

Employee has morning/afternoon unavailability on specific days.

### Pattern 6: Mixed Requirements

```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP008,A,EQUALS:08:00-16:00,8,INCLUDE:09:00-17:00,VAC
EMP009,EXCEPT:14:00-22:00,6,A,EQUALS:09:00-17:00,VAC
```

Combines auto-allocation, specific hours, and time constraints.

## Custom Constraints: Complete Example

**problem.json:**
```json
{
  "scheduleInput": {
    "dataFile": "schedule_input.csv",
    "markingTypes": {
      "DL": "Day Off - Generic (swappable)",
      "DLF": "Fixed Day Off - Cannot be changed or swapped",
      "DLV": "Variable Day Off - Can swap within same week",
      "DO": "Day Off - With penalty if swapped",
      "EnfD": "Enfermidade - Sick leave (medical certificate)",
      "Med": "Medical - Doctor appointment",
      "FT": "Formation/Training - Mandatory training day"
    }
  }
}
```

**schedule_input.csv:**
```csv
employee_id,2030-10-01,2030-10-02,2030-10-03,2030-10-04,2030-10-05
EMP001,A,DL,A,A,DLF
EMP002,EnfD,EnfD,Med,A,DLV
EMP003,A,A,FT,A,DO
```

**Validation:**
- ✅ All custom codes (DL, DLF, DLV, DO, EnfD, Med, FT) are defined in markingTypes
- ✅ Validator accepts these codes
- ❌ If you use "DL" without defining it, validator will REJECT it

## Validation Checklist

Before running the scheduler:

- [ ] All comment lines deleted from CSV files
- [ ] Employee IDs in CSV match JSON `employees[].id`
- [ ] Date columns are consecutive and match `temporalScope`
- [ ] All employees have contracts with `workHoursPerDay` (if using `A`)
- [ ] Time window constraints use correct format (EQUALS/INCLUDE/EXCEPT:HH:MM-HH:MM)
- [ ] Time ranges are valid (HH: 00-23, MM: 00-59, start < end)
- [ ] Shift codes in demand.csv match JSON `demand.shifts[].code`
- [ ] Team codes in demand.csv match JSON `organizationalUnits`
- [ ] Demand values follow order: minimum ≤ estimated ≤ ideal
- [ ] No duplicate rows in demand.csv (same date/shift/team)
- [ ] **Custom constraints are defined in JSON `scheduleInput.markingTypes`**
- [ ] UTF-8 encoding used for all files

## Troubleshooting

### "Invalid cell value" error for DL, DO, Med, etc.

**Problem:** Validator rejects custom constraint codes.

**Solution:** Define them in JSON:
```json
"scheduleInput": {
  "markingTypes": {
    "DL": "Day Off",
    "DO": "Day Off with penalty"
  }
}
```

### "Employee has no contract" warning

**Problem:** Employee uses `A` but has no `workHoursPerDay`.

**Solution:**
- Add `contractType` to employee in JSON
- Ensure contract exists in `contracts.definitions`
- Or remove `A` values from schedule_input.csv

### "Date columns don't match temporalScope" error

**Problem:** Date range mismatch.

**Solution:**
- Check date range in CSV headers matches `temporalScope.targetPeriod`
- Verify number of date columns = `temporalScope.numDays`

### "Invalid time range" error

**Problem:** Time window constraint has incorrect format.

**Solution:**
- Use format: EQUALS/INCLUDE/EXCEPT:HH:MM-HH:MM
- Ensure HH is 00-23, MM is 00-59
- Start time must be before end time
- Example: `EQUALS:08:00-16:00` ✅, `EQUALS:08-16` ❌

## Next Steps

1. Review complete examples in `examples/` directory
2. Read `FORMAT.md` for detailed parameter reference
3. Check `README.md` for schema overview and philosophy
4. Run validator frequently to catch errors early

## Support

For issues or questions:
- Read documentation: FORMAT.md, README.md
- Check examples: examples/sisqual_example/
- Validate often: `python3 validator/validator.py problem.json -v`

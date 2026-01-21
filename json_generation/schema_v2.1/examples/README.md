# Scheduling Problem Examples

This directory contains complete, working examples of scheduling problems that demonstrate different features of the schema.

## Available Examples

### 1. team_based_october_2030/
**Description**: Team-based scheduling for October 2030 with priority hierarchy

**Features demonstrated**:
- Simple team-based employee model
- Two teams (EG and CAJ)
- Two shifts (Morning and Afternoon)
- Priority hierarchy (optional feature)
- Employee availability constraints
- Daily coverage requirements

**Problem characteristics**:
- 7 employees
- 2 teams: EG (Management), CAJ (Cashier)
- 31 days (October 2030)
- 2 shifts per day (M and T)
- Weekday/weekend patterns

**Source**: Based on 2030Exemplo2.xlsx

**Files**:
- `problem.json` - Complete problem definition
- `demand.csv` - Daily coverage requirements (109 rows)
- `schedule_input.csv` - Employee availability constraints

**How to use**:
1. Review the files to understand the structure
2. Copy the directory as a starting point
3. Modify for your specific needs
4. Use as reference when creating your own problems

---

## Example Usage Patterns

### Pattern 1: Start from Example
```bash
# Copy example as starting point
cp -r team_based_october_2030/ my_problem/

# Edit the files
cd my_problem/
# Modify problem.json (employees, dates, teams)
# Update demand.csv (coverage requirements)
# Update schedule_input.csv (employee constraints)
```

### Pattern 2: Understand Structure
- Open `team_based_october_2030/problem.json` to see JSON structure
- Open `team_based_october_2030/demand.csv` to see coverage format
- Open `team_based_october_2030/schedule_input.csv` to see constraint format

### Pattern 3: Compare with Templates
- Compare example CSVs with templates in `../templates/`
- Templates have extensive comments
- Examples show actual data

---

## Quick Reference

|Feature|team_based_october_2030|
|-------|----------------------|
|Employee Model|Team|
|Number of Employees|7|
|Number of Teams|2 (EG, CAJ)|
|Number of Days|31|
|Number of Shifts|2 (M, T)|
|Priority Hierarchy|Yes|
|Advanced Constraints|No|
|Competency Model|No|

---

## Future Examples (Planned)

### competency_based_example/
*Coming soon*
- Multi-skilled employees
- Competency-based assignments
- Skill level requirements

### flexible_shifts_example/
*Coming soon*
- Flexible shift start times
- Variable shift lengths
- Multiple start time options

---

## Creating Your Own Example

To contribute an example:

1. Create a new directory under `examples/`
2. Include complete files:
   - `problem.json`
   - `demand.csv`
   - `schedule_input.csv`
   - `README.md` (describing the example)
3. Test that the example validates
4. Document what features it demonstrates

---

## Validation

All examples should:
- Pass JSON Schema validation
- Have valid CSV formats
- Be complete and runnable
- Include documentation

---

## Need Help?

- **Templates**: See `../templates/` for starting point CSV files
- **Format reference**: See `../FORMAT.md` for complete documentation
- **Schema**: See `../schema.json` for formal definition

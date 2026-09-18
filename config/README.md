# Configuration

## Overview

Centralized configuration directory containing business rules and data import templates for the SmarTask scheduling system.

## Contents

```
config/
├── rules.json                              # Business rules (master copy)
└── templates/                              # Data-import templates (examples below)
    ├── minimuns.csv                        # Basic minimum coverage template
    ├── minimuns3shifts.csv                 # 3 shifts coverage template
    ├── minimuns3teams.csv                  # 3 teams coverage template
    ├── minimuns3shifts_3teams.csv          # Combined 3 shifts + 3 teams
    ├── VacationTemplate*.csv               # Several vacation templates (17/30 employees, etc.)
    └── …                                   # plus more minimums variants and .xlsx/.ods sources
```

> The listing above is illustrative — `templates/` also holds additional minimums/vacation
> variants and a few `.xlsx`/`.ods` source workbooks.

---

## Business Rules (`rules.json`)

### Purpose

Defines all scheduling constraints and business logic used by the schedule generation algorithms. This is the **master copy** that gets distributed to services during build/deployment.

### Service Usage

**Build-Time Distribution:**
- `config/rules.json` is the **master copy** (single source of truth)
- During build, this file is automatically copied to:
  - `src/api/src/main/resources/rules.json` (API service)
  - `src/scheduler/rules.json` (Scheduler service)
- Service copies are **NOT committed** to git (in .gitignore)
- Each service loads its local copy at runtime

**Build Process:**
- **Makefile:** Copies before building (`make build`, `make build-api`, `make build-scheduler`)
- **Dockerfiles:** Copy from `config/` during image build
- **CI Pipeline:** Copies before running tests and builds

### Rule Types

#### Hard Constraints (Must be satisfied)
- **team-eligibility** - Employees can only work on their assigned teams
- **max-consecutive-days** - Maximum 5 workdays in any 6-day window
- **special-days-cap** - Maximum 22 Sundays/holidays per employee per year
- **no-earlier-shift-next-day** - No backward shift transitions (Night→Morning forbidden)
- **total-workdays-per-year** - Exactly 223 workdays per employee per year
- **vacation-days** - Vacation days ("F") cannot be scheduled

#### Soft Constraints (Preferred but flexible)
- **min-coverage** - Minimum staffing requirements with penalty for violations

### Modifying Rules

1. **Edit** `config/rules.json` (master copy only)
2. **Rebuild** affected services (automatically copies updated rules):
   ```bash
   make build           # Rebuild everything
   make build-api       # Just API
   make build-scheduler # Just scheduler
   ```
3. **Restart** services for changes to take effect

**⚠️ Important:**
- NEVER edit `src/api/src/main/resources/rules.json` directly
- NEVER edit `src/scheduler/rules.json` directly
- These are generated files - changes will be overwritten on next build
- Always edit `config/rules.json` as the single source of truth

### Critical Values

⚠️ **Total Workdays:** Currently set to **223 days** (min/max)
- This was chosen from majority of original files (2 out of 3)
- One original file had **300 days** - verify with domain expert if this needs adjustment

---

## CSV Templates (`templates/`)

### Purpose

Provide template files for importing data via the web UI. Users download these templates, fill them out, and upload them back to the system.

### Minimum Coverage Templates

Define required staffing levels for each day/shift/team combination.

**Files:**
- `minimuns.csv` - Basic template
- `minimuns3shifts.csv` - For 3-shift operations (Morning, Afternoon, Night)
- `minimuns3teams.csv` - For 3-team organizations
- `minimuns3shifts_3teams.csv` - Combined 3 shifts × 3 teams

**Usage:** Imported via web UI → Stored in MongoDB `references` collection

### Vacation Templates

Define employee vacation days and other absences for the year.

**Files:**
- `VacationTemplate.csv` - Basic template
- `VacationTemplateAlternative.csv` - Alternative format
- `VacationTemplate17Employees.csv` - Pre-configured for 17 employees
- `VacationTemplate30employees.csv` - Pre-configured for 30 employees

**Format:** Days marked with "F" (Férias/Vacation) cannot be scheduled for work

**Usage:** Imported via web UI → Stored in MongoDB `vacations` collection

---

## Integration with Services

### API Service
- Loads `rules.json` from classpath resources
- Serves CSV templates for download via endpoints
- Validates uploaded CSV files against templates

### Scheduler Service
- Loads `rules.json` from service root directory
- Applies rules during schedule generation
- All algorithms receive rules as parameter

### Frontend Service
- Downloads CSV templates from API
- Provides UI for template upload
- Displays rule violations in schedule view

---

## Maintenance

### Adding New Rules

1. Add rule definition to `config/rules.json`
2. Implement rule handler in `src/scheduler/algorithms/handlers/`
3. Register handler in appropriate engine
4. Rebuild and restart services
5. Document in this README

### Adding New Templates

1. Create CSV file in `config/templates/`
2. Ensure proper format (header row + data rows)
3. Test import via web UI
4. Document purpose in this README

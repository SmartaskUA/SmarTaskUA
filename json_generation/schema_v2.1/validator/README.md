# Schema v2.1 Validator

A comprehensive validator that verifies JSON problem definitions and CSV files (demand.csv and schedule_input.csv) are consistent and can be used together for employee scheduling.

## Features

The validator performs three levels of validation:

### 1. JSON Validation
- Validates against schema.json (JSON Schema compliance)
- Checks schema version is "2.1"
- Validates temporal scope (year, numDays, date ranges)
- Ensures employee IDs are unique
- Validates employee model (team vs competency)
- Ensures shift codes are unique
- Validates organizational units (teams or competencies)

### 2. CSV Validation

**demand.csv:**
- Checks required columns: date, shift, team, minimum, ideal, estimated
- Validates date formats (YYYY-MM-DD)
- Ensures numeric columns are integers
- Checks logical order: minimum ≤ estimated ≤ ideal
- Detects duplicate rows (same date/shift/team)

**schedule_input.csv:**
- Verifies first column is "employee_id"
- Validates date column headers (YYYY-MM-DD format)
- Checks dates are consecutive
- Validates cell values (A, VAC, DL, DLF, DLV, EnfD, DO, NOT, Med, or HH:MM-HH:MM time ranges)
- Detects duplicate employee IDs

### 3. Cross-Validation (JSON ↔ CSVs)
- Employee IDs in schedule_input.csv exist in JSON
- All JSON employees appear in schedule_input.csv
- Date columns in schedule_input.csv match temporalScope
- Date range matches targetPeriod
- Shift codes in demand.csv exist in JSON shifts
- Team/competency codes in demand.csv exist in JSON organizationalUnits
- Dates in demand.csv are within targetPeriod

## Installation

Install the required dependencies:

```bash
pip install -r validator_requirements.txt
```

Or install individually:

```bash
pip install pandas python-dateutil jsonschema
```

## Usage

### Basic Usage

Validate a problem with its CSV files:

```bash
python3 validator.py path/to/problem.json
```

### Verbose Output

Show detailed error locations and statistics:

```bash
python3 validator.py path/to/problem.json --verbose
# or
python3 validator.py path/to/problem.json -v
```

### JSON Output

Get machine-readable JSON output for integration with other tools:

```bash
python3 validator.py path/to/problem.json --json
# or
python3 validator.py path/to/problem.json -j
```

## Examples

### Validate the sisqual example:

```bash
cd json_generation/schema_v2.1
python3 validator.py examples/sisqual_example/problem.json -v
```

### Validate all examples:

```bash
cd json_generation/schema_v2.1
for example in examples/*/problem.json; do
    echo "Validating $example..."
    python3 validator.py "$example"
    echo ""
done
```

## Exit Codes

- `0` - Validation successful (no errors)
- `1` - Validation failed (errors found)

## Output Format

### Console Output (Default)

```
================================================================================
  SCHEMA v2.1 VALIDATION REPORT
================================================================================

✅ VALIDATION PASSED - All checks successful!

⚠️  WARNINGS (2):
--------------------------------------------------------------------------------
  [JSON] Target period span (30 days) does not match numDays (31)
    Location: temporalScope
  [Cross-validation] Employee ID in JSON not found in schedule_input.csv: {'EMP999'}

ℹ️  STATISTICS:
--------------------------------------------------------------------------------
  employee_model: competency
  num_employees: 15
  year: 2025
  num_days: 31
  num_shifts: 9
  num_competencies: 3
  demand_csv_rows: 279
  schedule_csv_employees: 15

================================================================================
```

### JSON Output (--json flag)

```json
{
  "success": true,
  "errors": [],
  "warnings": [
    {
      "category": "JSON",
      "severity": "warning",
      "message": "Target period span (30 days) does not match numDays (31)",
      "location": "temporalScope"
    }
  ],
  "stats": {
    "employee_model": "competency",
    "num_employees": 15,
    "year": 2025,
    "num_days": 31
  }
}
```

## Common Error Messages

### JSON Errors

- **"Invalid schema version"** - schemaVersion must be "2.1"
- **"Duplicate employee ID"** - Employee IDs must be unique
- **"Invalid employee model"** - Model must be "team" or "competency"
- **"Duplicate shift code"** - Shift codes must be unique

### CSV Errors

- **"Missing required columns"** - CSV is missing expected columns
- **"Invalid date format"** - Dates must be in YYYY-MM-DD format
- **"Invalid cell value"** - Cell contains unrecognized value
- **"Duplicate rows"** - Same date/shift/team appears multiple times

### Cross-Validation Errors

- **"Employee IDs not found in JSON"** - CSV references employees not defined in JSON
- **"Shift codes not found in JSON"** - demand.csv references undefined shifts
- **"Date is outside targetPeriod"** - demand.csv contains dates outside the scheduling period
- **"Date columns do not match numDays"** - Wrong number of date columns in schedule_input.csv

## Integration

### As a Pre-Processing Step

Add validation before running the scheduler:

```bash
# Validate first
python3 json_generation/schema_v2.1/validator.py problem.json || exit 1

# If validation passes, run scheduler
python3 src/scheduler/main.py problem.json
```

### In a Makefile

```makefile
validate:
	@python3 json_generation/schema_v2.1/validator.py problem.json -v

schedule: validate
	@python3 src/scheduler/main.py problem.json
```

### In Python Scripts

```python
import subprocess
import sys

result = subprocess.run(
    ["python3", "validator.py", "problem.json", "--json"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("Validation failed!")
    sys.exit(1)

# Parse JSON output
import json
report = json.loads(result.stdout)
print(f"Found {len(report['errors'])} errors")
```

## Troubleshooting

### Module Not Found Errors

If you see "No module named 'pandas'" or similar:

```bash
pip install -r validator_requirements.txt
```

### File Not Found Errors

Ensure:
1. The problem.json path is correct
2. The CSV file paths in problem.json (demand.dataFile, scheduleInput.dataFile) are relative to the JSON file location
3. CSV files actually exist at those paths

### Encoding Errors

Ensure CSV files are saved with UTF-8 encoding. In Excel:
- Save As → CSV UTF-8 (Comma delimited)

## Development

### Adding New Validation Rules

Edit `validator.py` and add checks in the appropriate method:
- `_validate_json_content()` - JSON-only checks
- `_validate_demand_csv()` - demand.csv checks
- `_validate_schedule_input_csv()` - schedule_input.csv checks
- `_cross_validate()` - Cross-validation between files

### Running Tests

Test against all examples:

```bash
cd json_generation/schema_v2.1
for example in examples/*/problem.json; do
    python3 validator.py "$example" -v
done
```

## See Also

- [FORMAT.md](FORMAT.md) - Detailed format specification
- [schema.json](schema.json) - JSON Schema definition
- [README.md](README.md) - Schema v2.1 overview

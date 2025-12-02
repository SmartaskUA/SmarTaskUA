# Sisqual JSON Generation

This directory contains JSON schemas, examples, and conversion tools for the Sisqual scheduling problem (Problem 2).

## What's Here

### 📋 Schemas (`schemas/`)
JSON schemas defining the data structure:
- `employees_schema.json` - Employees with competencies & levels
- `alarms_schema.json` - KPI alarms with priority hierarchy
- `schedule_template_schema.json` - Schedule input with markings
- `store_config_schema.json` - Store hours & constraints
- `challenges_config_schema.json` - 4 challenge configurations

### 📝 Examples (`examples/`)
Working example JSON files:
- `employees_example.json` - Sample employees with multi-competencies
- `alarms_example.json` - Sample KPI alarms with priorities
- `schedule_input_example.json` - Sample schedule with fixed/flexible shifts
- `store_config_example.json` - Store configuration
- `challenges_config_example.json` - Challenge settings

### 🔧 Converter (`csv_to_json_converter.py`)
Python script to convert Sisqual's CSV files to JSON.

**Usage:**
```bash
python csv_to_json_converter.py \
  --employees employees.csv \
  --schedule schedule.csv \
  --alarms alarms.csv \
  --target-month 2025-01 \
  --output ./output
```

### 📦 Complete Template (`sisqual_problem_template.json`)
Full Sisqual problem template with all components integrated.

## Quick Start

1. **Receive CSV files** from Sisqual
2. **Run converter**:
   ```bash
   python csv_to_json_converter.py --employees <file> --schedule <file> --alarms <file>
   ```
3. **Verify output** - Check generated JSON files in `./output/`
4. **Use in algorithms** - Feed JSON to your scheduling algorithm implementations

## CSV Format Requirements

### Employees CSV
```csv
Employee ID,Name,Competencies,Part-Time
EMP001,Name,"EG-1,CAJ-2",N
```

### Schedule CSV
```csv
Employee ID,Day1,Day2,Day3,...
EMP001,8h,*7h-09:00-16:00,DLV,...
```
- `*` prefix = Fixed (red in Excel, cannot modify)
- `8h` = 8-hour flexible shift
- `7h-09:00-16:00` = Fixed 7-hour shift with times
- `DLF`, `DLV`, `VAC`, `EnfD` = Day markings

### Alarms CSV
```csv
Alarm ID,Competency,Level,Day Type,Start Time,End Time,Minimo,Ideal,Estimado
ALM_WD,ALM,1,weekday,08:30,15:30,1,1,1
```

## Key Concepts

**Competencies:**
- EG (Gestão) = Management
- CAJ (Caja) = Cashier
- ALM (Almacén) = Warehouse

**Levels:** 1 = best, 2, 3, 4+ = progressively lower skill

**Markings:**
- DLF = Fixed day off
- DLV = Variable day off (can swap)
- VAC = Vacation
- EnfD = Sick leave
- WORK = Work shift

## Documentation

See `docs/sisqual/json-format.md` for complete documentation.

## Reference

Based on: `docs/BFarias_Doc_Sisqual.pdf`

#!/usr/bin/env python3
"""
Schema v2.2 Validator for Employee Scheduling Problems

Validates that problem.json, demand.csv, and schedule_input.csv are consistent
and can be used together for scheduling. v2.2 adds support for contract-based
hour allocation (A) and specific hour requirements (1-16).

Usage:
    python validator.py <path_to_problem.json> [--verbose] [--json]
"""

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import pandas as pd
    from dateutil.parser import parse as parse_date
    import jsonschema
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Install with: pip install pandas python-dateutil jsonschema")
    sys.exit(1)


@dataclass
class ValidationError:
    """Represents a validation error"""
    category: str  # e.g., "JSON", "CSV", "Cross-validation"
    severity: str  # "error" or "warning"
    message: str
    location: Optional[str] = None  # e.g., "demand.csv:line 5" or "employees[3].id"


@dataclass
class ValidationReport:
    """Validation report containing all errors and warnings"""
    success: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, category: str, message: str, location: Optional[str] = None):
        """Add an error to the report"""
        self.errors.append(ValidationError(category, "error", message, location))
        self.success = False

    def add_warning(self, category: str, message: str, location: Optional[str] = None):
        """Add a warning to the report"""
        self.warnings.append(ValidationError(category, "warning", message, location))

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON output"""
        return {
            "success": self.success,
            "errors": [
                {
                    "category": e.category,
                    "severity": e.severity,
                    "message": e.message,
                    "location": e.location
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "category": w.category,
                    "severity": w.severity,
                    "message": w.message,
                    "location": w.location
                }
                for w in self.warnings
            ],
            "stats": self.stats
        }


def validate_time_format(time_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate time format HH:MM with proper ranges.

    Returns:
        (is_valid, error_message): True if valid, False with error message if invalid
    """
    pattern = re.compile(r'^(\d{2}):(\d{2})$')
    match = pattern.match(time_str)

    if not match:
        return False, f"Invalid time format '{time_str}' (expected HH:MM)"

    hours, minutes = int(match.group(1)), int(match.group(2))

    if hours > 23:
        return False, f"Invalid hours '{hours}' in '{time_str}' (must be 00-23)"
    if minutes > 59:
        return False, f"Invalid minutes '{minutes}' in '{time_str}' (must be 00-59)"

    return True, None


def validate_time_range(time_range_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate time range format HH:MM-HH:MM with proper ranges and start < end.

    Returns:
        (is_valid, error_message): True if valid, False with error message if invalid
    """
    pattern = re.compile(r'^(\d{2}):(\d{2})-(\d{2}):(\d{2})$')
    match = pattern.match(time_range_str)

    if not match:
        return False, f"Invalid time range format '{time_range_str}' (expected HH:MM-HH:MM)"

    start_hours, start_mins = int(match.group(1)), int(match.group(2))
    end_hours, end_mins = int(match.group(3)), int(match.group(4))

    # Validate ranges
    if start_hours > 23:
        return False, f"Invalid start hours '{start_hours}' in '{time_range_str}' (must be 00-23)"
    if start_mins > 59:
        return False, f"Invalid start minutes '{start_mins}' in '{time_range_str}' (must be 00-59)"
    if end_hours > 23:
        return False, f"Invalid end hours '{end_hours}' in '{time_range_str}' (must be 00-23)"
    if end_mins > 59:
        return False, f"Invalid end minutes '{end_mins}' in '{time_range_str}' (must be 00-59)"

    # Check start < end (convert to minutes for comparison)
    start_total_mins = start_hours * 60 + start_mins
    end_total_mins = end_hours * 60 + end_mins

    if start_total_mins >= end_total_mins:
        return False, f"Start time must be before end time in '{time_range_str}'"

    return True, None


class SchemaValidator:
    """Validates schema v2.2 JSON and CSV files"""

    def __init__(self, problem_json_path: str):
        self.problem_json_path = Path(problem_json_path)
        self.problem_dir = self.problem_json_path.parent
        self.report = ValidationReport()
        self.problem_data: Optional[Dict] = None
        self.demand_df: Optional[pd.DataFrame] = None
        self.schedule_df: Optional[pd.DataFrame] = None
        self.employee_work_hours: Dict[str, float] = {}  # v2.2: employee_id -> workHoursPerDay
        self.contract_definitions: Dict[str, Dict] = {}  # v2.2: contract_id -> contract_data

    def validate(self) -> ValidationReport:
        """Main validation entry point"""
        # 1. Load and validate JSON
        if not self._validate_json_file():
            return self.report

        # 2. Validate JSON structure and content
        self._validate_json_schema()
        self._validate_json_content()

        # 3. Load and validate CSVs
        self._validate_csv_files()

        # 4. Cross-validation
        if self.problem_data and (self.demand_df is not None or self.schedule_df is not None):
            self._cross_validate()

        # 5. Generate statistics
        self._generate_stats()

        return self.report

    def _validate_json_file(self) -> bool:
        """Load and parse JSON file"""
        if not self.problem_json_path.exists():
            self.report.add_error("JSON", f"File not found: {self.problem_json_path}")
            return False

        try:
            with open(self.problem_json_path, 'r', encoding='utf-8') as f:
                self.problem_data = json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.report.add_error("JSON", f"Invalid JSON syntax: {e}")
            return False
        except Exception as e:
            self.report.add_error("JSON", f"Error reading file: {e}")
            return False

    def _validate_json_schema(self):
        """Validate JSON against the schema"""
        # Try to find schema.json relative to the validator script first
        # (assumes validator is in schema_v2.2/validator/ and schema.json is in schema_v2.2/)
        validator_dir = Path(__file__).parent
        schema_path = validator_dir.parent / "schema.json"

        # Fall back to looking in the problem.json directory for backwards compatibility
        if not schema_path.exists():
            schema_path = self.problem_dir / "schema.json"

        if not schema_path.exists():
            self.report.add_warning("JSON", f"Schema file not found (looked in validator parent dir and problem dir), skipping schema validation")
            return

        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            jsonschema.validate(instance=self.problem_data, schema=schema)
        except jsonschema.ValidationError as e:
            self.report.add_error("JSON Schema", f"Schema validation failed: {e.message}", f"at {'.'.join(str(p) for p in e.path)}")
        except Exception as e:
            self.report.add_warning("JSON Schema", f"Could not validate schema: {e}")

    def _validate_json_content(self):
        """Validate JSON content beyond schema validation"""
        if not self.problem_data:
            return

        # Check schema version
        schema_version = self.problem_data.get("schemaVersion")
        if schema_version != "2.2":
            self.report.add_error("JSON", f"Invalid schema version: expected '2.2', got '{schema_version}'", "schemaVersion")

        # Check problem type
        problem_type = self.problem_data.get("problemType")
        if problem_type != "employee_scheduling":
            self.report.add_error("JSON", f"Invalid problem type: expected 'employee_scheduling', got '{problem_type}'", "problemType")

        # Validate temporal scope
        self._validate_temporal_scope()

        # v2.2: Validate contracts FIRST (employees reference them)
        self._validate_contracts()

        # Validate employees (v2.2: validate contract references)
        self._validate_employees()

        # Validate demand
        self._validate_demand_config()

    def _validate_temporal_scope(self):
        """Validate temporal scope configuration"""
        temporal = self.problem_data.get("temporalScope", {})

        year = temporal.get("year")
        if not year or not (2020 <= year <= 2100):
            self.report.add_error("JSON", f"Invalid year: {year}", "temporalScope.year")

        num_days = temporal.get("numDays")
        if not num_days or not (1 <= num_days <= 366):
            self.report.add_error("JSON", f"Invalid numDays: {num_days}", "temporalScope.numDays")

        # Validate target period if present
        target_period = temporal.get("targetPeriod", {})
        if target_period:
            try:
                start_str = target_period.get("start")
                end_str = target_period.get("end")

                if start_str:
                    start_date = parse_date(start_str).date()
                if end_str:
                    end_date = parse_date(end_str).date()

                if start_str and end_str:
                    days_diff = (end_date - start_date).days + 1
                    if days_diff != num_days:
                        self.report.add_warning(
                            "JSON",
                            f"Target period span ({days_diff} days) does not match numDays ({num_days})",
                            "temporalScope"
                        )
            except Exception as e:
                self.report.add_error("JSON", f"Invalid date format in targetPeriod: {e}", "temporalScope.targetPeriod")

    def _validate_contracts(self):
        """Validate contract definitions (v2.2)"""
        contracts = self.problem_data.get("contracts", {})

        # Check contracts exist
        if not contracts:
            self.report.add_error("JSON", "Missing required 'contracts' section", "contracts")
            return

        definitions = contracts.get("definitions", [])
        if not definitions:
            self.report.add_error("JSON", "Contract definitions required - must have at least 1 contract defined", "contracts.definitions")
            return

        # Track contract IDs for uniqueness validation
        contract_ids = set()

        for idx, contract in enumerate(definitions):
            contract_id = contract.get("id")
            name = contract.get("name")
            work_hours = contract.get("workHoursPerDay")

            # Validate required fields
            if not contract_id:
                self.report.add_error("JSON", f"Contract missing 'id' field", f"contracts.definitions[{idx}]")
                continue

            if not name:
                self.report.add_error("JSON", f"Contract {contract_id} missing 'name' field", f"contracts.definitions[{idx}].name")

            if work_hours is None:
                self.report.add_error("JSON", f"Contract {contract_id} missing 'workHoursPerDay' field", f"contracts.definitions[{idx}].workHoursPerDay")
            elif not isinstance(work_hours, (int, float)) or work_hours < 0 or work_hours > 24:
                self.report.add_error("JSON", f"Contract {contract_id} has invalid workHoursPerDay: must be 0-24, got {work_hours}", f"contracts.definitions[{idx}].workHoursPerDay")

            # Check uniqueness
            if contract_id in contract_ids:
                self.report.add_error("JSON", f"Duplicate contract ID: '{contract_id}'", f"contracts.definitions[{idx}].id")
            else:
                contract_ids.add(contract_id)
                # Store contract definition for later lookup
                self.contract_definitions[contract_id] = contract

            # Validate optional constraints
            constraints = contract.get("constraints", {})
            if constraints:
                weekends_only = constraints.get("weekendsOnly")
                weekdays_only = constraints.get("weekdaysOnly")

                # weekendsOnly and weekdaysOnly are mutually exclusive
                if weekends_only and weekdays_only:
                    self.report.add_error("JSON", f"Contract {contract_id}: weekendsOnly and weekdaysOnly are mutually exclusive", f"contracts.definitions[{idx}].constraints")

                # Validate availableDays
                available_days = constraints.get("availableDays", [])
                valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
                for day in available_days:
                    if day not in valid_days:
                        self.report.add_error("JSON", f"Contract {contract_id}: invalid day '{day}' in availableDays", f"contracts.definitions[{idx}].constraints.availableDays")

                # Validate maxHoursPerWeek
                max_hours_week = constraints.get("maxHoursPerWeek")
                if max_hours_week is not None and (not isinstance(max_hours_week, (int, float)) or max_hours_week < 0):
                    self.report.add_error("JSON", f"Contract {contract_id}: maxHoursPerWeek must be positive, got {max_hours_week}", f"contracts.definitions[{idx}].constraints.maxHoursPerWeek")

                # Validate maxConsecutiveDays
                max_consec = constraints.get("maxConsecutiveDays")
                if max_consec is not None and (not isinstance(max_consec, int) or max_consec < 1):
                    self.report.add_error("JSON", f"Contract {contract_id}: maxConsecutiveDays must be >= 1, got {max_consec}", f"contracts.definitions[{idx}].constraints.maxConsecutiveDays")

                # Validate minRestDaysPerWeek
                min_rest = constraints.get("minRestDaysPerWeek")
                if min_rest is not None and (not isinstance(min_rest, int) or min_rest < 0 or min_rest > 7):
                    self.report.add_error("JSON", f"Contract {contract_id}: minRestDaysPerWeek must be 0-7, got {min_rest}", f"contracts.definitions[{idx}].constraints.minRestDaysPerWeek")

    def _validate_employees(self):
        """Validate employee configuration and validate contract references (v2.2)"""
        employees = self.problem_data.get("employees", {})
        model = employees.get("model")

        if model not in ["team", "competency"]:
            self.report.add_error("JSON", f"Invalid employee model: {model}", "employees.model")
            return

        # Check for appropriate employee list
        if model == "team":
            emp_list = employees.get("simple", [])
            if not emp_list:
                self.report.add_error("JSON", "No employees defined in 'simple' array for team model", "employees.simple")
        else:  # competency
            emp_list = employees.get("competency", [])
            if not emp_list:
                self.report.add_error("JSON", "No employees defined in 'competency' array for competency model", "employees.competency")

        # Check for duplicate employee IDs and validate contract references (v2.2)
        emp_ids = set()
        for idx, emp in enumerate(emp_list):
            emp_id = emp.get("id")
            if not emp_id:
                self.report.add_error("JSON", f"Employee missing 'id' field", f"employees[{idx}]")
            elif emp_id in emp_ids:
                self.report.add_error("JSON", f"Duplicate employee ID: {emp_id}", f"employees[{idx}].id")
            else:
                emp_ids.add(emp_id)

            # v2.2: Validate contractType references
            contract_type = emp.get("contractType")
            if contract_type:
                if contract_type not in self.contract_definitions:
                    self.report.add_error("JSON", f"Employee {emp_id} references contract '{contract_type}' which does not exist in contracts.definitions", f"employees[{idx}].contractType")
                else:
                    # Extract workHoursPerDay from contract
                    contract = self.contract_definitions[contract_type]
                    work_hours = contract.get("workHoursPerDay")
                    if work_hours is not None:
                        self.employee_work_hours[emp_id] = float(work_hours)
            else:
                self.report.add_warning("JSON", f"Employee {emp_id} has no contractType specified", f"employees[{idx}].contractType")

            # v2.2: Validate contractPeriods if present
            contract_periods = emp.get("contractPeriods", [])
            for period_idx, period in enumerate(contract_periods):
                period_contract = period.get("contractType")
                if period_contract and period_contract not in self.contract_definitions:
                    self.report.add_error("JSON", f"Employee {emp_id} contractPeriods[{period_idx}] references contract '{period_contract}' which does not exist in contracts.definitions", f"employees[{idx}].contractPeriods[{period_idx}].contractType")

            # Validate team/competency presence
            if model == "team":
                teams = emp.get("teams", [])
                if not teams:
                    self.report.add_warning("JSON", f"Employee {emp_id} has no teams assigned", f"employees[{idx}].teams")
            else:  # competency
                competencies = emp.get("competencies", [])
                if not competencies:
                    self.report.add_warning("JSON", f"Employee {emp_id} has no competencies assigned", f"employees[{idx}].competencies")

    def _validate_demand_config(self):
        """Validate demand configuration in JSON"""
        demand = self.problem_data.get("demand", {})

        # Check shift model
        shift_model = demand.get("shiftModel")
        if shift_model not in ["fixed", "flexible"]:
            self.report.add_error("JSON", f"Invalid shift model: {shift_model}", "demand.shiftModel")

        # Check organizational units
        org_units = demand.get("organizationalUnits", {})
        employees = self.problem_data.get("employees", {})
        model = employees.get("model")

        if model == "team":
            teams = org_units.get("teams", [])
            if not teams:
                self.report.add_error("JSON", "No teams defined in organizationalUnits for team model", "demand.organizationalUnits.teams")
            # Check for duplicate teams
            if len(teams) != len(set(teams)):
                self.report.add_error("JSON", "Duplicate team codes in organizationalUnits.teams", "demand.organizationalUnits.teams")
        else:  # competency
            competencies = org_units.get("competencies", [])
            if not competencies:
                self.report.add_error("JSON", "No competencies defined in organizationalUnits for competency model", "demand.organizationalUnits.competencies")
            # Check for duplicate competency codes
            codes = [c.get("code") for c in competencies if c.get("code")]
            if len(codes) != len(set(codes)):
                self.report.add_error("JSON", "Duplicate competency codes in organizationalUnits.competencies", "demand.organizationalUnits.competencies")

        # Validate shifts
        shifts = demand.get("shifts")
        if shifts is not None:
            shift_codes = set()
            shift_orders = set()
            for idx, shift in enumerate(shifts):
                code = shift.get("code")
                if not code:
                    self.report.add_error("JSON", f"Shift missing 'code' field", f"demand.shifts[{idx}]")
                elif code in shift_codes:
                    self.report.add_error("JSON", f"Duplicate shift code: {code}", f"demand.shifts[{idx}].code")
                else:
                    shift_codes.add(code)

                # Check order uniqueness
                order = shift.get("order")
                if order is not None:
                    if order in shift_orders:
                        self.report.add_error("JSON", f"Duplicate shift order: {order}", f"demand.shifts[{idx}].order")
                    else:
                        shift_orders.add(order)

                # Validate time range if present (for fixed shift model)
                time_range = shift.get("timeRange")
                if time_range:
                    start_time = time_range.get("start")
                    end_time = time_range.get("end")

                    if start_time:
                        is_valid, error_msg = validate_time_format(start_time)
                        if not is_valid:
                            self.report.add_error("JSON", error_msg, f"demand.shifts[{idx}].timeRange.start")

                    if end_time:
                        is_valid, error_msg = validate_time_format(end_time)
                        if not is_valid:
                            self.report.add_error("JSON", error_msg, f"demand.shifts[{idx}].timeRange.end")

                    # Check start < end
                    if start_time and end_time:
                        combined_range = f"{start_time}-{end_time}"
                        is_valid, error_msg = validate_time_range(combined_range)
                        if not is_valid:
                            self.report.add_error("JSON", f"Shift time range validation failed: {error_msg}", f"demand.shifts[{idx}].timeRange")

    def _validate_csv_files(self):
        """Load and validate CSV files"""
        if not self.problem_data:
            return

        # Get CSV file paths - BOTH ARE REQUIRED
        demand_file = self.problem_data.get("demand", {}).get("dataFile")
        schedule_file = self.problem_data.get("scheduleInput", {}).get("dataFile")

        # Check that demand.csv is specified and exists (REQUIRED)
        if not demand_file:
            self.report.add_error("CSV", "Missing required field: demand.dataFile must specify the demand CSV file path", "demand.dataFile")
        else:
            demand_path = self.problem_dir / demand_file
            self._validate_demand_csv(demand_path)

        # Check that schedule_input.csv is specified and exists (REQUIRED)
        if not schedule_file:
            self.report.add_error("CSV", "Missing required field: scheduleInput.dataFile must specify the schedule input CSV file path", "scheduleInput.dataFile")
        else:
            schedule_path = self.problem_dir / schedule_file
            self._validate_schedule_input_csv(schedule_path)

    def _validate_demand_csv(self, csv_path: Path):
        """Validate demand.csv file"""
        if not csv_path.exists():
            self.report.add_error("CSV", f"Demand CSV file not found: {csv_path}", "demand.dataFile")
            return

        try:
            self.demand_df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception as e:
            self.report.add_error("CSV", f"Error reading demand CSV: {e}", str(csv_path))
            return

        # Check required columns
        required_cols = ["date", "shift", "team", "minimum", "ideal", "estimated"]
        missing_cols = [col for col in required_cols if col not in self.demand_df.columns]
        if missing_cols:
            self.report.add_error("CSV", f"Demand CSV missing required columns: {missing_cols}", str(csv_path))
            return

        # Validate date format
        for idx, row in self.demand_df.iterrows():
            date_str = row["date"]
            try:
                parse_date(str(date_str))
            except Exception:
                self.report.add_error("CSV", f"Invalid date format: {date_str}", f"{csv_path.name}:row {idx+2}")

        # Validate numeric columns
        for col in ["minimum", "ideal", "estimated"]:
            if not pd.api.types.is_numeric_dtype(self.demand_df[col]):
                self.report.add_error("CSV", f"Column '{col}' must be numeric", f"{csv_path.name}:{col}")

        # Check for negative values
        for col in ["minimum", "ideal", "estimated"]:
            if (self.demand_df[col] < 0).any():
                bad_rows = self.demand_df[self.demand_df[col] < 0].index + 2
                self.report.add_error("CSV", f"Column '{col}' contains negative values at rows: {list(bad_rows)}", f"{csv_path.name}:{col}")

        # Check logical order: minimum <= estimated <= ideal
        invalid_order = self.demand_df[
            (self.demand_df["minimum"] > self.demand_df["estimated"]) |
            (self.demand_df["estimated"] > self.demand_df["ideal"])
        ]
        if not invalid_order.empty:
            for idx in invalid_order.index:
                row = self.demand_df.loc[idx]
                self.report.add_error(
                    "CSV",
                    f"Invalid order (should be minimum <= estimated <= ideal): min={row['minimum']}, est={row['estimated']}, ideal={row['ideal']}",
                    f"{csv_path.name}:row {idx+2}"
                )

        # Check for duplicate rows
        duplicates = self.demand_df[self.demand_df.duplicated(subset=["date", "shift", "team"], keep=False)]
        if not duplicates.empty:
            dup_rows = duplicates.index + 2
            self.report.add_error("CSV", f"Duplicate rows (same date/shift/team) at rows: {list(dup_rows)}", str(csv_path.name))

    def _validate_schedule_input_csv(self, csv_path: Path):
        """Validate schedule_input.csv file (v2.2: supports A and numeric values)"""
        if not csv_path.exists():
            self.report.add_error("CSV", f"Schedule input CSV file not found: {csv_path}", "scheduleInput.dataFile")
            return

        try:
            self.schedule_df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception as e:
            self.report.add_error("CSV", f"Error reading schedule input CSV: {e}", str(csv_path))
            return

        # Check first column is employee_id
        if self.schedule_df.columns[0] != "employee_id":
            self.report.add_error("CSV", f"First column must be 'employee_id', found '{self.schedule_df.columns[0]}'", str(csv_path.name))
            return

        # Check for duplicate employee IDs
        dup_ids = self.schedule_df[self.schedule_df["employee_id"].duplicated()]
        if not dup_ids.empty:
            self.report.add_error("CSV", f"Duplicate employee IDs: {list(dup_ids['employee_id'])}", str(csv_path.name))

        # Validate date column headers
        date_columns = self.schedule_df.columns[1:]
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')

        for col in date_columns:
            if not date_pattern.match(str(col)):
                self.report.add_error("CSV", f"Invalid date column header format (expected YYYY-MM-DD): {col}", f"{csv_path.name}:header")
            else:
                try:
                    parse_date(str(col))
                except Exception:
                    self.report.add_error("CSV", f"Invalid date in column header: {col}", f"{csv_path.name}:header")

        # Check date columns are consecutive
        valid_dates = []
        for col in date_columns:
            try:
                valid_dates.append(parse_date(str(col)).date())
            except Exception:
                pass

        if len(valid_dates) > 1:
            for i in range(len(valid_dates) - 1):
                expected_next = valid_dates[i] + timedelta(days=1)
                if valid_dates[i + 1] != expected_next:
                    self.report.add_warning("CSV", f"Date columns are not consecutive: gap between {valid_dates[i]} and {valid_dates[i+1]}", f"{csv_path.name}:headers")

        # v2.2: Track employees using "A" to validate workHoursPerDay
        employees_using_A = set()

        # Validate cell values (v2.2: support A and numeric values)
        # Get valid marking types from JSON if defined
        marking_types = self.problem_data.get("scheduleInput", {}).get("markingTypes", {})
        if marking_types:
            # If markingTypes are defined, use those as valid values (excluding numeric which are always valid in v2.2)
            valid_values = set(marking_types.keys())
        else:
            # Default valid values based on templates and documentation
            valid_values = {"A", "VAC", "DL", "DLF", "DLV", "EnfD", "DO", "NOT", "Med", "DC-E"}

        for col in date_columns:
            for idx, value in enumerate(self.schedule_df[col]):
                value_str = str(value).strip()
                emp_id = str(self.schedule_df.loc[idx, "employee_id"])

                # v2.2: Check if it's "A" (auto-allocate)
                if value_str == "A":
                    employees_using_A.add(emp_id)
                    continue

                # v2.2: Check if it's a numeric value (1-16 hours)
                try:
                    hours = int(value_str)
                    if 1 <= hours <= 16:
                        continue  # Valid hour specification
                    else:
                        self.report.add_error(
                            "CSV",
                            f"Invalid hour value: '{value_str}' (must be 1-16)",
                            f"{csv_path.name}:row {idx+2}, col {col}"
                        )
                        continue
                except ValueError:
                    pass  # Not a number, continue with other validations

                # Check if it's a valid marking type
                if value_str in valid_values:
                    continue

                # Check if it's a time range
                time_range_pattern = re.compile(r'^\d{2}:\d{2}-\d{2}:\d{2}$')
                if time_range_pattern.match(value_str):
                    # Validate time range properly
                    is_valid, error_msg = validate_time_range(value_str)
                    if not is_valid:
                        self.report.add_error(
                            "CSV",
                            f"Invalid time range in cell: {error_msg}",
                            f"{csv_path.name}:row {idx+2}, col {col}"
                        )
                else:
                    # Not a valid marking, number, or time range
                    if marking_types:
                        self.report.add_error(
                            "CSV",
                            f"Invalid cell value: '{value_str}' (must be 'A', 1-16, one of {valid_values} defined in scheduleInput.markingTypes, or a valid time range HH:MM-HH:MM)",
                            f"{csv_path.name}:row {idx+2}, col {col}"
                        )
                    else:
                        self.report.add_error(
                            "CSV",
                            f"Invalid cell value: '{value_str}' (must be 'A', 1-16, one of {valid_values}, or a valid time range HH:MM-HH:MM)",
                            f"{csv_path.name}:row {idx+2}, col {col}"
                        )

        # v2.2: Validate employees using "A" have contract with workHoursPerDay
        for emp_id in employees_using_A:
            if emp_id not in self.employee_work_hours:
                self.report.add_warning(
                    "CSV",
                    f"Employee '{emp_id}' uses 'A' (auto-allocate) but has no valid contract reference or contract workHoursPerDay defined in JSON. Please ensure employee has contractType referencing a valid contract.",
                    f"{csv_path.name}:employee {emp_id}"
                )

    def _cross_validate(self):
        """Cross-validate JSON and CSV data"""
        if not self.problem_data:
            return

        # Get employee IDs from JSON
        employees = self.problem_data.get("employees", {})
        model = employees.get("model")

        if model == "team":
            emp_list = employees.get("simple", [])
        else:
            emp_list = employees.get("competency", [])

        json_emp_ids = {emp.get("id") for emp in emp_list if emp.get("id")}

        # Cross-validate with schedule_input.csv
        if self.schedule_df is not None:
            csv_emp_ids = set(self.schedule_df["employee_id"].astype(str))

            # Check all CSV employee IDs exist in JSON
            missing_in_json = csv_emp_ids - json_emp_ids
            if missing_in_json:
                self.report.add_error(
                    "Cross-validation",
                    f"Employee IDs in schedule_input.csv not found in JSON: {missing_in_json}",
                    "schedule_input.csv:employee_id"
                )

            # Check all JSON employee IDs exist in CSV
            missing_in_csv = json_emp_ids - csv_emp_ids
            if missing_in_csv:
                self.report.add_error(
                    "Cross-validation",
                    f"Employee IDs in JSON not found in schedule_input.csv: {missing_in_csv}",
                    "employees"
                )

            # Validate date columns match temporal scope
            temporal = self.problem_data.get("temporalScope", {})
            num_days = temporal.get("numDays")
            target_period = temporal.get("targetPeriod", {})

            date_columns = self.schedule_df.columns[1:]
            if num_days and len(date_columns) != num_days:
                self.report.add_error(
                    "Cross-validation",
                    f"Number of date columns in schedule_input.csv ({len(date_columns)}) does not match temporalScope.numDays ({num_days})",
                    "schedule_input.csv vs temporalScope.numDays"
                )

            # Check date range matches
            if target_period.get("start") and target_period.get("end") and len(date_columns) > 0:
                try:
                    expected_start = parse_date(target_period["start"]).date()
                    expected_end = parse_date(target_period["end"]).date()
                    actual_start = parse_date(str(date_columns[0])).date()
                    actual_end = parse_date(str(date_columns[-1])).date()

                    if actual_start != expected_start:
                        self.report.add_error(
                            "Cross-validation",
                            f"Schedule CSV start date ({actual_start}) does not match targetPeriod.start ({expected_start})",
                            "schedule_input.csv vs temporalScope.targetPeriod"
                        )

                    if actual_end != expected_end:
                        self.report.add_error(
                            "Cross-validation",
                            f"Schedule CSV end date ({actual_end}) does not match targetPeriod.end ({expected_end})",
                            "schedule_input.csv vs temporalScope.targetPeriod"
                        )
                except Exception as e:
                    self.report.add_warning("Cross-validation", f"Could not validate date ranges: {e}")

        # Cross-validate with demand.csv
        if self.demand_df is not None:
            # Get shift codes from JSON
            demand = self.problem_data.get("demand", {})
            shifts = demand.get("shifts", [])
            json_shift_codes = {s.get("code") for s in shifts if s.get("code")}

            # Check all CSV shift codes exist in JSON
            if json_shift_codes:  # Only validate if shifts are defined
                csv_shift_codes = set(self.demand_df["shift"].unique())
                missing_shifts = csv_shift_codes - json_shift_codes
                if missing_shifts:
                    self.report.add_error(
                        "Cross-validation",
                        f"Shift codes in demand.csv not found in JSON shifts: {missing_shifts}",
                        "demand.csv:shift"
                    )

            # Get organizational units from JSON
            org_units = demand.get("organizationalUnits", {})
            if model == "team":
                json_teams = set(org_units.get("teams", []))
                csv_teams = set(self.demand_df["team"].unique())

                missing_teams = csv_teams - json_teams
                if missing_teams:
                    self.report.add_error(
                        "Cross-validation",
                        f"Team codes in demand.csv not found in JSON organizationalUnits.teams: {missing_teams}",
                        "demand.csv:team"
                    )
            else:  # competency model
                competencies = org_units.get("competencies", [])
                json_comp_codes = {c.get("code") for c in competencies if c.get("code")}
                csv_comp_codes = set(self.demand_df["team"].unique())

                missing_comps = csv_comp_codes - json_comp_codes
                if missing_comps:
                    self.report.add_error(
                        "Cross-validation",
                        f"Competency codes in demand.csv not found in JSON organizationalUnits.competencies: {missing_comps}",
                        "demand.csv:team (competency codes)"
                    )

            # Validate dates in demand.csv are within temporal scope
            temporal = self.problem_data.get("temporalScope", {})
            target_period = temporal.get("targetPeriod", {})

            if target_period.get("start") and target_period.get("end"):
                try:
                    start_date = parse_date(target_period["start"]).date()
                    end_date = parse_date(target_period["end"]).date()

                    for idx, date_str in enumerate(self.demand_df["date"]):
                        try:
                            demand_date = parse_date(str(date_str)).date()
                            if demand_date < start_date or demand_date > end_date:
                                self.report.add_error(
                                    "Cross-validation",
                                    f"Date in demand.csv ({demand_date}) is outside targetPeriod ({start_date} to {end_date})",
                                    f"demand.csv:row {idx+2}"
                                )
                        except Exception:
                            pass  # Already caught in CSV validation
                except Exception as e:
                    self.report.add_warning("Cross-validation", f"Could not validate demand dates: {e}")

    def _generate_stats(self):
        """Generate statistics about the problem"""
        if not self.problem_data:
            return

        stats = {}

        # Employee stats
        employees = self.problem_data.get("employees", {})
        model = employees.get("model")
        stats["employee_model"] = model

        if model == "team":
            emp_list = employees.get("simple", [])
        else:
            emp_list = employees.get("competency", [])

        stats["num_employees"] = len(emp_list)

        # v2.2: workHoursPerDay stats
        if self.employee_work_hours:
            stats["employees_with_work_hours"] = len(self.employee_work_hours)
            stats["avg_work_hours_per_day"] = sum(self.employee_work_hours.values()) / len(self.employee_work_hours)

        # Temporal stats
        temporal = self.problem_data.get("temporalScope", {})
        stats["year"] = temporal.get("year")
        stats["num_days"] = temporal.get("numDays")
        stats["target_period_start"] = temporal.get("targetPeriod", {}).get("start")
        stats["target_period_end"] = temporal.get("targetPeriod", {}).get("end")

        # Shift stats
        demand = self.problem_data.get("demand", {})
        shifts = demand.get("shifts", [])
        stats["num_shifts"] = len(shifts) if shifts else 0

        # Organizational unit stats
        org_units = demand.get("organizationalUnits", {})
        if model == "team":
            stats["num_teams"] = len(org_units.get("teams", []))
        else:
            stats["num_competencies"] = len(org_units.get("competencies", []))

        # CSV stats
        if self.demand_df is not None:
            stats["demand_csv_rows"] = len(self.demand_df)
            stats["demand_csv_unique_dates"] = len(self.demand_df["date"].unique())

        if self.schedule_df is not None:
            stats["schedule_csv_employees"] = len(self.schedule_df)
            stats["schedule_csv_days"] = len(self.schedule_df.columns) - 1

        self.report.stats = stats


def print_report(report: ValidationReport, verbose: bool = False):
    """Print validation report in human-readable format"""
    print("\n" + "=" * 80)
    print("  SCHEMA v2.2 VALIDATION REPORT")
    print("=" * 80)

    if report.success:
        print("\n✅ VALIDATION PASSED - All checks successful!\n")
    else:
        print("\n❌ VALIDATION FAILED - Errors found!\n")

    # Print errors
    if report.errors:
        print(f"\n❌ ERRORS ({len(report.errors)}):")
        print("-" * 80)
        for err in report.errors:
            print(f"  [{err.category}] {err.message}")
            if err.location and verbose:
                print(f"    Location: {err.location}")
        print()

    # Print warnings
    if report.warnings:
        print(f"\n⚠️  WARNINGS ({len(report.warnings)}):")
        print("-" * 80)
        for warn in report.warnings:
            print(f"  [{warn.category}] {warn.message}")
            if warn.location and verbose:
                print(f"    Location: {warn.location}")
        print()

    # Print statistics
    if report.stats and verbose:
        print("\nℹ️  STATISTICS:")
        print("-" * 80)
        for key, value in report.stats.items():
            print(f"  {key}: {value}")
        print()

    print("=" * 80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate Schema v2.2 employee scheduling problem files (JSON + CSVs)"
    )
    parser.add_argument(
        "problem_json",
        help="Path to problem.json file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed information including locations and statistics"
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output report in JSON format"
    )

    args = parser.parse_args()

    # Create validator and run validation
    validator = SchemaValidator(args.problem_json)
    report = validator.validate()

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report, verbose=args.verbose)

    # Exit with appropriate code
    sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()

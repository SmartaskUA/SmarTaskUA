#!/usr/bin/env python3
"""
Sisqual CSV to JSON Converter
Converts Excel/CSV data from Sisqual into structured JSON format for algorithm processing.
"""

import pandas as pd
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path


class SisqualCSVConverter:
    """Converts Sisqual CSV files into JSON format"""

    def __init__(self):
        self.employees = []
        self.schedule_data = []

    def parse_employees_csv(self, csv_path):
        """
        Parse employee CSV with competencies and levels.

        Expected CSV format:
        Employee ID, Name, Competencies (e.g., "EG-1,CAJ-2"), Part-Time (Y/N)
        """
        df = pd.read_csv(csv_path)
        employees = []

        for _, row in df.iterrows():
            competencies = []
            comp_str = str(row.get('Competencies', ''))

            # Parse competencies like "EG-1,CAJ-2,ALM-3"
            if comp_str and comp_str != 'nan':
                for comp in comp_str.split(','):
                    comp = comp.strip()
                    if '-' in comp:
                        comp_type, level = comp.split('-')
                        competencies.append({
                            "type": comp_type.strip().upper(),
                            "level": int(level)
                        })

            employee = {
                "id": str(row['Employee ID']),
                "name": str(row['Name']),
                "competencies": competencies,
                "partTime": str(row.get('Part-Time', 'N')).upper() == 'Y',
                "contractPeriods": [
                    {
                        "startDate": str(row.get('Contract Start', '2024-01-01')),
                        "endDate": None
                    }
                ]
            }
            employees.append(employee)

        return {"employees": employees}

    def parse_schedule_csv(self, csv_path, target_month):
        """
        Parse schedule CSV with daily markings.

        Expected CSV format:
        Employee ID, Day1, Day2, Day3, ... (columns for each day)
        Values: DL, DLF, DLV, VAC, EnfD, DC-E, or shift notation like "8h", "7h-09:00-16:00"
        Red text in Excel = isFixed=true (need to mark in CSV with * prefix, e.g., "*DLF")
        """
        df = pd.read_csv(csv_path)

        # Parse target month to determine date range (month + 1 week before + 1 week after)
        year, month = map(int, target_month.split('-'))
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year, 12, 31)

        start_date = first_day - timedelta(days=7)
        end_date = last_day + timedelta(days=7)

        employee_schedules = []

        for _, row in df.iterrows():
            emp_id = str(row['Employee ID'])
            days = []

            # Get all day columns (skip Employee ID column)
            day_columns = [col for col in df.columns if col.startswith('Day') or col.startswith('Dia')]

            current_date = start_date
            for day_col in day_columns:
                if current_date > end_date:
                    break

                value = str(row.get(day_col, '')).strip()

                if not value or value == 'nan' or value == '':
                    # Empty cell = contract gap
                    days.append({
                        "date": current_date.strftime('%Y-%m-%d'),
                        "marking": "EMPTY"
                    })
                else:
                    day_entry = self._parse_day_value(value, current_date)
                    days.append(day_entry)

                current_date += timedelta(days=1)

            employee_schedules.append({
                "employeeId": emp_id,
                "days": days
            })

        return {
            "period": {
                "targetMonth": target_month,
                "startDate": start_date.strftime('%Y-%m-%d'),
                "endDate": end_date.strftime('%Y-%m-%d')
            },
            "employeeSchedules": employee_schedules
        }

    def _parse_day_value(self, value, date):
        """Parse individual day value from CSV"""
        is_fixed = value.startswith('*')
        if is_fixed:
            value = value[1:].strip()

        # Check for day-off markings
        markings = ['DLF', 'DLV', 'DL', 'VAC', 'EnfD', 'DC-E']
        for marking in markings:
            if value.upper() == marking:
                return {
                    "date": date.strftime('%Y-%m-%d'),
                    "marking": marking,
                    "isFixed": is_fixed
                }

        # Parse work shift (e.g., "8h", "7h-09:00-16:00", "5h-FLEX")
        if 'h' in value.lower():
            return self._parse_shift(value, date, is_fixed)

        # Default to day off
        return {
            "date": date.strftime('%Y-%m-%d'),
            "marking": "DL",
            "isFixed": is_fixed
        }

    def _parse_shift(self, value, date, is_fixed):
        """Parse shift notation like '8h', '7h-09:00-16:00', '5h-FLEX-CAJ'"""
        parts = value.split('-')

        # Extract duration
        duration_str = parts[0].lower().replace('h', '').strip()
        duration = int(duration_str) if duration_str.isdigit() else 8

        # Extract times if present
        start_time = None
        end_time = None
        is_flexible = True
        competency = None

        if len(parts) >= 3 and ':' in parts[1]:
            start_time = parts[1].strip()
            end_time = parts[2].strip()
            is_flexible = False

        # Check for competency assignment
        for part in parts:
            part_upper = part.strip().upper()
            if part_upper in ['EG', 'CAJ', 'ALM']:
                competency = part_upper
                break

        shift_data = {
            "date": date.strftime('%Y-%m-%d'),
            "marking": "WORK",
            "isFixed": is_fixed,
            "shift": {
                "duration": duration,
                "isFlexible": is_flexible
            }
        }

        if start_time:
            shift_data["shift"]["startTime"] = start_time
        if end_time:
            shift_data["shift"]["endTime"] = end_time
        if competency:
            shift_data["shift"]["competencyAssignment"] = competency

        return shift_data

    def parse_alarms_csv(self, csv_path):
        """
        Parse KPI alarms CSV.

        Expected CSV format:
        Alarm ID, Competency, Level, Day Type, Start Time, End Time, Minimo, Ideal, Estimado
        """
        df = pd.read_csv(csv_path)

        # Priority hierarchy from PDF (fixed)
        priority_hierarchy = [
            {"rank": 1, "competency": "ALM", "level": "N≥1", "description": "RESP ALMACEN N≥1: MaxAlarm"},
            {"rank": 2, "competency": "EG", "level": "N=1", "description": "RESP - EQUIPO GESTION N=1"},
            {"rank": 3, "competency": "CAJ", "level": "N=1", "description": "CAJA N=1"},
            {"rank": 4, "competency": "EG", "level": "N=2", "description": "RESP - EQUIPO GESTION N=2"},
            {"rank": 5, "competency": "CAJ", "level": "N=2", "description": "CAJA N=2"},
            {"rank": 6, "competency": "EG", "level": "N=3", "description": "RESP - EQUIPO GESTION N=3"},
            {"rank": 7, "competency": "EG", "level": "≥4", "description": "RESP - EQUIPO GESTION ≥ 4"},
            {"rank": 8, "competency": "CAJ", "level": "N=3", "description": "CAJA N=3"},
            {"rank": 9, "competency": "EQUIPA", "level": "N≥1", "description": "EQUIPA Empleados N≥1"}
        ]

        alarms = []
        for _, row in df.iterrows():
            alarm = {
                "id": str(row['Alarm ID']),
                "competency": str(row['Competency']).upper(),
                "level": int(row['Level']) if pd.notna(row.get('Level')) else None,
                "applicationType": str(row.get('Application Type', 'equipa')),
                "timeRanges": [
                    {
                        "dayType": str(row.get('Day Type', 'all')),
                        "startTime": str(row['Start Time']),
                        "endTime": str(row['End Time']),
                        "requirements": {
                            "minimo": int(row['Minimo']),
                            "ideal": int(row.get('Ideal', row['Minimo'])),
                            "estimado": int(row.get('Estimado', row['Minimo']))
                        }
                    }
                ]
            }
            alarms.append(alarm)

        return {
            "priorityHierarchy": priority_hierarchy,
            "alarms": alarms
        }

    def convert(self, employees_csv, schedule_csv, alarms_csv, target_month, output_dir):
        """Convert all CSV files and generate JSON outputs"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Convert employees
        if employees_csv:
            employees_data = self.parse_employees_csv(employees_csv)
            with open(output_path / 'employees.json', 'w', encoding='utf-8') as f:
                json.dump(employees_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Employees JSON created: {output_path / 'employees.json'}")

        # Convert schedule
        if schedule_csv:
            schedule_data = self.parse_schedule_csv(schedule_csv, target_month)
            with open(output_path / 'schedule_input.json', 'w', encoding='utf-8') as f:
                json.dump(schedule_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Schedule JSON created: {output_path / 'schedule_input.json'}")

        # Convert alarms
        if alarms_csv:
            alarms_data = self.parse_alarms_csv(alarms_csv)
            with open(output_path / 'alarms.json', 'w', encoding='utf-8') as f:
                json.dump(alarms_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Alarms JSON created: {output_path / 'alarms.json'}")


def main():
    parser = argparse.ArgumentParser(description='Convert Sisqual CSV files to JSON format')
    parser.add_argument('--employees', help='Path to employees CSV file')
    parser.add_argument('--schedule', help='Path to schedule CSV file')
    parser.add_argument('--alarms', help='Path to alarms/KPI CSV file')
    parser.add_argument('--target-month', default='2025-01', help='Target month (YYYY-MM)')
    parser.add_argument('--output', default='./output', help='Output directory for JSON files')

    args = parser.parse_args()

    converter = SisqualCSVConverter()
    converter.convert(
        employees_csv=args.employees,
        schedule_csv=args.schedule,
        alarms_csv=args.alarms,
        target_month=args.target_month,
        output_dir=args.output
    )

    print("\n✓ Conversion complete!")


if __name__ == '__main__':
    main()

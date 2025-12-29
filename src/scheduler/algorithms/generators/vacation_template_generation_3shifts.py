"""
Vacation Template Generator (3 shifts)
-------------------------------------
Wrapper to generate vacation templates for 3-shift scenarios where
employee counts are doubled vs the 2-shift cases.
"""

from vacation_template_generation import create_vacation_cases


def main():
    employee_counts = (24, 48, 96, 192)
    output_base = "data/vacationData_3shifts"

    for count in employee_counts:
        create_vacation_cases(employee_count=count, year=2025, output_base=output_base)


if __name__ == "__main__":
    main()

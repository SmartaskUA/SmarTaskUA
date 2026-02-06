# SmarTask Simple 2025 Example (v2.2)

Derived from the simple two-team / two-shift case described in "SmarTask - Relatorio Tecnico".

## Scope
- Year: 2025 (365 days)
- Teams: A, B
- Shifts: M (08:00-16:00), T (14:00-22:00)

## Inputs
- demand.csv: daily minimum/ideal coverage per team and shift
- vacations.csv: vacation template (0/1 per employee per day)

## Model Notes
- All employees use a single contract type: fullTime_8h (v2.2 requirement)
- Constraints reflect the case study rules:
  - 223 workdays per employee per year
  - max 22 special days (Sundays/holidays)
  - max 5 consecutive workdays (window 6)
  - no T -> M transitions on consecutive days
  - vacation days enforced via the vacation template

## Optimization
- algorithm: CSPv2
- maxTimeMinutes: 10

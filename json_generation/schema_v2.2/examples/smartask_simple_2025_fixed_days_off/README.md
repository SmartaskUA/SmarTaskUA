# SmarTask Simple 2025 Fixed Days-Off Example (v2.2)

Derived from the simple two-team / two-shift case described in "SmarTask - Relatorio Tecnico", with additional employee-specific folga rules.

## Scope
- Year: 2025 (365 days)
- Teams: A, B
- Shifts: M (08:00-16:00), T (14:00-22:00)

## Inputs
- demand.csv: daily minimum/ideal coverage per team and shift
- vacations.csv: vacation template (0/1 per employee per day)

## Additional Constraints (Custom)
- `fixed_days_off_per_week` (using `default` + `overrides`)
- `fixed_days_off_per_month` (using `defaultByMonth` + optional per-employee `overrides`)
- Only schedule value `0` counts as folga (`dayOffCounting.countOnlyScheduleValues = ["0"]`)

## Model Notes
- All employees use a single contract type: fullTime_8h (v2.2 requirement)
- Weekly rule uses Monday as start of week (`weekStart = "monday"`)
- Partial weeks are excluded from the weekly exact count (`applyToPartialWeeks = false`)

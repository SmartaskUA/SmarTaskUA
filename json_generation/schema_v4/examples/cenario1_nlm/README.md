# cenario1_nlm — NL scenario, January 2026 · **does not validate, on purpose**

Adapted from the SISQUAL bundle at
`IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_1/`
(generated 2026-09-17), together with the result payload Sisqual emailed on
2026-07-23. It is the only **complete round-trip** we have — problem in, result
back — and it is kept because it fails, not in spite of it.

| | |
|---|---|
| Workers | 12 |
| Horizon | 2026-01-01 .. 2026-01-31 |
| Contracts | 1 — `NL_36` ("[NL] 36h Semanais - Full-Time"), **432 min/day** |
| Dimensions | `Team/T1`, `Responsibility/A`, `Responsibility/C`, `Responsibility/G` |
| Demand | **0 rows** on every grain |
| Grid | 30 minutes |
| Result | `result.json` — 3 roster days for employee 160049, `ScheduleCode 100154` |

```bash
cd ../..                                                          # schema_v4/
PYTHONPATH=src python3 -m schema_v4.validator examples/cenario1_nlm -v
PYTHONPATH=src python3 -m schema_v4.validator examples/cenario1_nlm/result.json
```

## The three reasons it fails

**1. The contract does not fit the grid.** `NL_36` is 432 minutes a day and
`slotMinutes` is 30. 432 is not a multiple of 30, so no assignment of the
contracted length can be placed anywhere — 335 worker-days are unsatisfiable, and
the validator reports the contract once and then collapses the repeats. 432 needs a
grid of 6, 8, 12, 16, 24 or 48 minutes. Either `slotMinutes` or the contract has to
move; only Sisqual can say which.

**2. Nobody holds a competency.** All 12 employees ship with
`competencyAssignments: []`, so no worker can cover any dimension. The three
coordinates in `demand.dimensions[]` were recovered from `priorityHierarchy` alone,
because it is the only block in the bundle that names one.

**3. There is no demand.** All three demand CSVs are header-only, so every day is
closed and nothing needs staffing.

Any one of these is enough to make the scenario unsolvable. They are
[next_meeting.md](../../docs/next_meeting.md) items 18 and 19, and the grid clash
is item 20.

## What the result demonstrates

`result.json` is `import_1.Json` with its indentation repaired — Sisqual pasted it
out of Outlook, so the original is indented with U+2002 EN SPACE characters and is
**not valid JSON**. The raw file keeps those characters; this copy does not.

Validated against the problem, it produces exactly one finding, and it is the one
that matters:

```
ERROR  OutRosterTeamDays[0]: ScheduleCode 100154 is not in the schedules catalogue
```

`100154` is the shift Sisqual's own screenshot shows loading successfully into WFM
(`00:00 - 07:00` with a `04:00 - 04:30` meal break). It is absent from
`schedules_without_meal.csv` because that catalogue, as its name says, holds only
shifts **without** a meal break. **We do not have the with-meal catalogue**, and
without it a solver cannot name any shift that includes a break —
[next_meeting.md](../../docs/next_meeting.md) item 5.

It also warns that `EmployeeCode` is an integer here while the problem states
employee ids as strings; `JSON-Import.docx` says string.

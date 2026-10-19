# cenario2_partial — a result that fixes some days and leaves the rest open

[cenario2_retail](../cenario2_retail/) with a **partial** result: every employee's first week (2026-01-01 .. 2026-01-07) is decided, and the other 24 days are left for the solver.

| | |
|---|---|
| Problem and CSVs | identical to cenario2_retail's, menu included |
| `result.json` | 105 employee-days fixed (15 × 7); 360 left open |
| `result_schedules.csv` | exactly the codes those 105 days use |

```bash
cd ../..                                    # schema_v4/
make validate DIR=examples/cenario2_partial ARGS=-v
```

The result reports `rosterDaysExpected: 465` and `rosterDaysLeft: 360`, with no warning about the missing days.

## What a partial result means

**The entries present are fixed, and a missing employee-day is open.** Nothing in the result marks it as partial — it is `OutRosterTeamDays` in Sisqual's exact shape, and a complete result is simply one with nothing left. Each fixed day is held to the rules a solver would have to respect:

- its `schedule_input.csv` cell, as a hard rule — a worked day on a blank or unavailable cell, a rest on a day that asks for work, a shift outside an `EQUALS`/`INCLUDE`/`WITHIN`/`EXCEPT` window, or a shift of the wrong length is an error;
- the labour law in `constraints.hard[]` — `MaxConsecutiveWorkDays`, `MaxConsecutiveWorkDaysInWeek`, `MinDistanceBetweenShiftsInMinutes` — over the fixed days only. An open day breaks a run, because the solver may yet rest it.

## ⚠ Constructed, like cenario2_retail's

`make result` builds this with the same rule as cenario2_retail's result and stops after 2026-01-07, so each fixed day is exactly cenario2_retail's entry for that day. `tests/test_examples.py` checks that, and that the problem and CSVs have not drifted from cenario2_retail's.

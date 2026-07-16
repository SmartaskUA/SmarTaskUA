# time_constraints_example — time-window operators

Small synthetic demo of `EQUALS` / `INCLUDE` / `EXCEPT` and a midnight-crossing night shift.
Migrated from the v2.6 example of the same name.

| | |
|---|---|
| Model | team, 8 employees, 1 team (TeamA) |
| Horizon | 7 days, 2030-10-01 → 10-07 |
| Contracts | `fullTime_8h` → 480 minutes/day |
| Work periods | MORNING 08:30–16:30, AFTERNOON 14:00–22:00, **NIGHT 22:00–06:30** |
| Grid | 15 minutes → operating window 08:30 → 06:30 next day (`510`–`1830`) |

```bash
python3 ../../src/schema_v3/validator.py problem.json -v
python3 ../../src/schema_v3/transform.py problem.json --stats
```

## What it demonstrates

**Midnight crossing without ambiguity.** NIGHT's `end <= start`, so it unrolls to `1320`–`1830`
and the operating window runs to 06:30 next day. `EQUALS:22:00-06:00` becomes the block
`1320`–`1800`. v2.6 stored bare `HH:MM` and made every reader infer roll-over from `start > end`.

**The operators**, against an 8-hour contract in a `510`–`1830` window:

| cell | blocks |
|---|---|
| `A` / `480` | every 480-minute block on the grid |
| `EQUALS:08:30-16:30` | exactly one |
| `INCLUDE:09:00-17:00` | exactly one — a 480-minute window leaves an 8h contract no slack |
| `INCLUDE:11:00-15:00` | several — the block must cover 11:00–15:00 and may sit anywhere around it |
| `EXCEPT:14:00-22:00` | only the late-night ones; nothing fits before 14:00 |

**`D_wk` vs `U_wk`.** `DL` is classified `preferable` (10 cells, keep their options); EMP007's full
week of `VAC` is `unavailable` (7 cells, no options).

## Three cells were repaired, not migrated

The v2.6 example contained constraints that could never be satisfied — under v2.6 as much as v3:

| employee / date | v2.6 | now | why |
|---|---|---|---|
| EMP001 2030-10-04 | `EQUALS:08:00-16:00` | `EQUALS:08:30-16:30` | the shop opens 08:30, so 08:00–08:30 is outside the operating window and outside `T_d` |
| EMP008 2030-10-02 | `EQUALS:08:00-16:00` | `EQUALS:08:30-16:30` | same |
| EMP005 2030-10-06 | `INCLUDE:08:00-20:00` | `INCLUDE:11:00-15:00` | a 12-hour window an 8-hour contract can never cover |

Left alone, the first two are dropped by the `H_wd ⊆ T_d` rule (excluded whole, never trimmed) and
the third yields nothing, leaving three employees with no legal assignment. A reference example
should demonstrate the operators, not three dead ends.

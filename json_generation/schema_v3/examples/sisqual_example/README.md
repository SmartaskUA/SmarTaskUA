# sisqual_example — retail store, October 2025

Competency-based problem migrated from the v2.6 example of the same name. Diff the two directories
to see every v3.0 change on real data.

| | |
|---|---|
| Model | competency, 15 employees, 3 teams (Storage, Checkout, Management), levels 1–5 |
| Horizon | 31 days, 2025-10-01 → 10-31, week starts Monday |
| Contracts | 480 / 420 / 300 / 240 minutes per day |
| Work periods | 9 (Storage 08:30–15:30; Checkout and Management slices across 10:00–22:00) |
| Grid | 15 minutes → operating window 08:30–22:00 |
| Calendar | 2025-10-05 holiday (Implantação da República), 10-04 its eve |

```bash
python3 ../../src/schema_v3/validator.py problem.json -v
python3 ../../src/schema_v3/transform.py problem.json --stats
python3 ../../src/schema_v3/validator.py problem.expanded.json -v
```

## What it demonstrates

**Work periods are demand buckets.** No declared period is 480 minutes long, yet the two
full-timers ask for `480`. Their assignments are contiguous 8-hour blocks positioned anywhere in
the 08:30–22:00 window — 23 positions on the 15-minute grid — not a choice among the 9 periods.

**`H_wd ⊆ T_d`.** Eight of the 31 days run a reduced set of periods (4 or 3 rows instead of 9), so
`T_d` shrinks and every block that would spill into non-operating time is dropped whole. The
expansion reports 1484 such exclusions.

**`D_wk` vs `U_wk`.** 175 `DO` cells become `dayOff: "preferable"` and **keep** their options — the
solver may schedule over them and pay ObjectiveFunction3. The 55 `VAC`/`Med`/`NOT`/`FDO` cells
become `dayOff: "unavailable"` with no options at all.

**`priorityOrder`.** v2.6 ranked teams only — Management > Checkout > Storage, with no entry
naming a level. That carries over **1:1** as three entries and nothing is invented. Levels
deliberately do not appear: v2.6 never said they mattered, and per-level ordering is the
enterprise's to add. The solver derives the model's weights from the entry positions.

**Level 1 is the highest.** Levels are carried over from v2.6 **unchanged**. v2.6's `schema.json`
prose claimed `1=junior`, but it contradicted the maths it was documenting — both definitions say
`l = 1` is highest — so the prose was the bug. The data corroborates that only weakly: the two
full-timers are Management 1-2 and the level-5 employee is on the smallest contract, but
`20056459` is Checkout **level 1** on that same smallest contract, so the contract correlation is
suggestive rather than conclusive. The maths is the authority.

## Migration notes

- Cells `8/7/5/4` → `480/420/300/240` minutes.
- demand.csv `minimum,ideal,estimated` → `minimum,empiric,maximum` (values swap; invisible here
  because every row was `1,1,1`).
- v2.6's `constraints` and `optimization` (min_rest, algorithm, objectives) are dropped: v3.0
  defines the problem, not how to solve it — those solve directives reached no solver (see
  `../../docs/FUTURE.md`).
- `weekDefinition` → `calendar.weekStart`. Static teams → one open-ended `teamAssignment`.
- v2.6's `markingTypes` + `dayOffCodes` collapse into one `dayOffCodes` map keyed by code
  (`{DO: {kind: "preferable", …}}`); the numeric codes `"8"/"7"/"5"/"4"` are dropped — numeric
  cells are work requirements, never day-off codes.

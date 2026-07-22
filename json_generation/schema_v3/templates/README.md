# Templates

1. Copy `problem_template.json`, `demand_template.csv`, `schedule_input_template.csv` into a new
   directory (point the two `dataFile` fields at your CSV names).
2. Fill in your data. The `_comment*` keys in the JSON and the `#` lines in the CSVs are ignored by
   the validator, so keep them as reminders or delete them — either way it validates.
3. Validate, expand, validate again:

```bash
python3 ../src/schema_v3/validator.py problem.json -v
python3 ../src/schema_v3/transform.py problem.json --stats
python3 ../src/schema_v3/validator.py problem.expanded.json -v
```

`problem_template.solution.json` is **not** an input you author — it shows the *output* form (a solver's
result). Validating it cross-checks it against `problem_template.expanded.json`; validating the whole
folder checks all three forms as one package:

```bash
python3 ../src/schema_v3/validator.py .
```

## The four things that catch people

**Minutes, not hours.** `workMinutesPerDay: 480`, and a schedule_input cell of `480`. A cell of
`8` is rejected — under v3 it would mean 8 *minutes*.

**Level 1 is the highest.** Your most senior person is level 1, and `{team, level: 1}` in
`priorityOrder` means that team's most senior. Nothing can validate this for you -- author it
backwards and every check still passes while the schedule staffs the wrong people.

**Work periods are demand buckets, not shifts.** Asking for one person on an 11:00–21:00 period is
asking for coverage, not a ten-hour shift. A worker works a contiguous block of their contracted
length anywhere in the operating window — so your periods do **not** need to match contract
lengths.

**Classify every day-off code.** `preferable` may be worked at a penalty; `unavailable` may not.
An unclassified code is an error, because guessing wrong yields a file that validates and a model
that is wrong.

## Copying from an existing example

`../examples/sisqual_example/` is a 15-employee, 31-day competency problem;
`../examples/time_constraints_example/` is a small demo of `EQUALS`/`INCLUDE`/`EXCEPT` and a
midnight-crossing night shift. Both ship with their expanded form alongside.

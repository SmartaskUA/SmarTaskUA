# Templates

1. Copy this folder into a new directory and point the five `dataFile` keys at your
   CSV names (`demand.dataFileDays` / `dataFilePeriods` / `dataFileShifts`,
   `scheduleInput.dataFile`, and `schedules.dataFile` if you have a catalogue).
2. Fill in your data. The `_comment*` keys in the JSON and the `#` lines in the CSVs
   are ignored by the validator, so keep them as reminders or delete them — either
   way it validates.
3. Validate:

```bash
cd ..                                                   # schema_v4/
PYTHONPATH=src python3 -m schema_v4.validator templates -v
```

This folder validates as one package, with **no errors and no warnings** — so any
finding you see after editing is yours.

If you are starting from a bundle SISQUAL generated, do not start here. Run the
adapter instead; it produces the same shape from their export and tells you
everything it had to change:

```bash
PYTHONPATH=src python3 -m schema_v4.sisqual_adapt <their-bundle-dir> -o mine/ --stats
```

## The five things that catch people

**Hours in the CSV, minutes in the JSON.** A contract says
`workMinutesPerDay: 480` and the matching `schedule_input.csv` cell says `8`. One
bundle, two units. v3.0 was minutes everywhere and rejected `8` outright; v4.0 keeps
SISQUAL's hours because that is what their exporter emits. A cell above 24 is
rejected as an unconverted v3.0 minute count. We are asking Sisqual to switch —
[docs/next_meeting.md](../docs/next_meeting.md) item 16.

**Everything must fit the grid.** `slotMinutes` divides the day, and every duration
must be a multiple of it — including each contract's `workMinutesPerDay`. This is
not pedantry: Sisqual's Cenário 1 bundle cannot be solved at all because its
contract is 432 minutes on a 30-minute grid, which is one of the three reasons it is
not shipped as an example.

**Level 1 is the highest.** Your most senior person is level 1, and a
`priorityHierarchy` entry with `minAbilityLevel: 1` reaches that dimension's most
senior. Nothing can validate this for you — author it backwards and every check
still passes while the schedule staffs the wrong people.

**Three demand files, two units.** `periods` and `shifts` are headcount; `days` is
workload **minutes**. Their headers are byte-identical, so only the JSON key that
points at a file says which it is. Never decide by looking at the file.

**`tableName`/`tableValue` is a coordinate, not a code.** Coverage is keyed on a
*pair*, and every pair must be declared in `demand.dimensions[]`. SISQUAL exports no
such catalogue and names the same dimension two different ways in two different
blocks, which is exactly why v4.0 requires one.

## Copying from an existing example

`../examples/cenario2_retail/` is a real 15-employee, 31-day SISQUAL bundle that
validates, with a worked result and its sidecar catalogue alongside. Sisqual's other
September bundle is *not* shipped, because it fails three independent ways — see
[docs/next_meeting.md](../docs/next_meeting.md) item 21 before you trust a bundle
just because it arrived from the generator.

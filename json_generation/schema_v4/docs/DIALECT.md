# The SISQUAL dialect ↔ canonical v4.0

SISQUAL's exporter stamps `"schemaVersion": "3.0"` on a payload that is neither
v3.0 nor canonical v4.0. This document is the complete difference list, and it is
also the specification `src/schema_v4/sisqual_adapt.py` implements — if the two
ever disagree, one of them is a bug.

**Why not just accept their spelling?** Because the problem format is a
specification we are writing together, and a misspelling frozen into it is
permanent. The *result* format is the opposite case: `OutRosterTeamDays` is
Sisqual's existing WFM import API, which we do not get to rename, so
`schema-v4-result.json` keeps their PascalCase vocabulary verbatim. The asymmetry
is deliberate: assert on what we co-design, conform on what we consume.

Run the adapter to see the list applied to a real bundle:

```bash
PYTHONPATH=src python3 -m schema_v4.sisqual_adapt <bundle-dir> -o out/ --stats
```

## JSON

| SISQUAL emits | canonical v4.0 | why |
|---|---|---|
| `schemaVersion: "3.0"` | `"4.0"` | the payload is not v3.0; three v3.0-required keys are absent |
| `employees[].contractAssigments` | `contractAssignments` | misspelled — missing `n` |
| `priorityHierachy` (root) | `priorityHierarchy` (root) | misspelled — missing `r` |
| `calendar.inpUAHolidaysCollection` | `calendar.holidays` | an internal `Inp…Collection` name leaking into the payload |
| `weekStart: "Monday"` | `"monday"` | v3.0's enum was lowercase |
| `dayOffCodes[].kind: "Preferable"` / `"Unavailable"` | lowercase | same |
| `end: "9999-12-31"` | `end: null` | a sentinel where the format already has a way to say "no end" |
| `tableName: "Equipa"` | `"Team"` | see the alias table below |
| `tableName: "Piso"` | `"Responsibility"` | see the alias table below |
| *(nothing)* | `metadata.rosterCode` | `problemId` is `<RosterCode>_<Month>_<Year>`, and a result carries `RosterCode` alone; stating the join once beats re-splitting the string wherever it is needed |
| *(nothing)* | `demand.dimensions[]` | required in v4.0; synthesised from every place a coordinate appears |
| `demand.dataFile*` naming a timestamped CSV | fixed names | see "CSV names" below |

Everything else is carried through unchanged: `form`, `problemType`, `metadata`'s
four fields, `timeGrid`, `temporalScope`, `contracts.definitions[]`,
`employees[].id`/`name`, `competencyAssignments[].level`/`start`,
`scheduleInput.dayOffCodes` as a free-key map, `priorityHierarchy`'s nine fields,
and `constraints` in full.

### The alias table

The same dimension is named two different ways in one document:

| block | names used |
|---|---|
| `employees[].competencyAssignments[].tableName` | `Equipa`, `Piso` |
| `priorityHierachy[].tableName` | `Team`, `Responsibility` |
| `periods_demand.csv` `tableName` | `Team`, `Responsibility` |

The intersection of those name sets is **empty**. Only `tableValue` (`T1`, `A`,
`C`, `G`) joins across all three, which is what makes the mapping recoverable:

```
Equipa → Team
Piso   → Responsibility
```

This is stated as a table in `sisqual_adapt.TABLE_NAME_ALIASES`, not inferred by
matching strings, because a wrong guess here silently disconnects employees from
the demand they are meant to cover. The adapter **refuses to run** if it ever meets
a Portuguese name on the demand side, rather than assume the mapping still holds.

## CSVs

| | SISQUAL | canonical v4.0 |
|---|---|---|
| encoding | UTF-8 **with BOM** | plain UTF-8 |
| line endings | CRLF | LF |
| decimal separator in `schedule_input` | comma, field quoted (`"7,2"`) | dot (`7.2`) |
| comments | none | `#` lines permitted (the templates use them) |
| names | `<PREFIX>_<scopeStart>_<yyyymmdd>_<hhmmss>_<kind>.csv` | `days_demand.csv`, `periods_demand.csv`, `shifts_demand.csv`, `schedule_input.csv` |

Column names and order are **unchanged** — including `minimum,ideal,estimated`,
whose ordering is still unresolved (see [next_meeting.md](next_meeting.md) item 1).
Renaming those without knowing which is the upper bound is exactly the swap that
corrupts silently.

### CSV names

The raw names embed a generation timestamp that **does not match the JSON's own**:
Cenário 1's problem is stamped `112509` while its CSVs are stamped `110909`, 16
minutes earlier. Anyone deriving one name from the other gets it wrong. The
adapter renames to fixed names and rewrites the `dataFile*` pointers, which
removes the trap; the authoritative link was always the literal string inside the
JSON, never the filename pattern.

## What the adapter deliberately does not fix

It does not invent data. These come out the other side still broken, and the
validator reports them:

- `contracts.definitions: []` while employees reference contracts (July bundle)
- `competencyAssignments: []` for every employee (Cenário 1)
- header-only demand CSVs (Cenário 1)
- a contract whose `workMinutesPerDay` does not fit `timeGrid.slotMinutes`
- the same competency held at two levels over the same dates (Cenário 2)

An adapter that papered over any of these would hide the defects we most need
Sisqual to see.

## Result format

Not adapted at all — `schema-v4-result.json` describes `OutRosterTeamDays[]`
exactly as `JSON-Import.docx` specifies it, with two tolerances the samples forced:

- `EmployeeCode` is documented as a string but emitted as an integer; both are
  accepted and the mismatch is warned about.
- `Date` is documented as `YYYY-MM-DD` but emitted as naive `YYYY-MM-DDTHH:MM:SS`;
  both are accepted.

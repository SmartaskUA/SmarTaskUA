# Reference material

Vendor material and working notes. Nothing here is authored by us except this file
and the converted catalogue; everything else is kept exactly as it arrived, because
it is the provenance behind every claim in [../docs/](../docs/).

## The raw SISQUAL drop

All of it under `../IntegracaoUA_SISQUAL/`, left as it arrived — the paths carry
dates, and renaming them would cost more than the tidiness is worth.

| path | what it is |
|---|---|
| `../IntegracaoUA_SISQUAL/JSON/20260708_Import_Export_Docs/` | `JSON-Import.docx` and `JSON-Export.docx` — the WFM-side contract, authored by Sisqual 2026-07-08. **Byte-identical** to the copies already transcribed at `../../schema_v3/reference/sisqual-json-import-export/`, so read the `.md` versions there. |
| `../IntegracaoUA_SISQUAL/JSON/20260723_email_Sisqual_to_UA/` | the `Re: Schema 3.0` thread. Sisqual's reply carries the `OutRosterTeamDays` sample and the schedule catalogue; the `.docx` is a Word printout of the same body. |
| `../IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/` | the two September bundles. Cenário 2 is adapted into `../examples/cenario2_retail/`; **Cenário 1 is not shipped as an example** — it fails three independent ways, so it stays here as provenance and as a test fixture (it is the only bundle exercising the decimal-comma path). See [../docs/next_meeting.md](../docs/next_meeting.md) item 21. |
| `../IntegracaoUA_SISQUAL/sisqual-alg-input/` | the July bundle. Not promoted to an example: it predates `priorityHierachy` and `constraints`, and its `contracts.definitions` is `[]` while all 15 employees reference `PT_40`. Kept as a negative test fixture. |
| `../IntegracaoUA_SISQUAL/sisqual-alg-output/` | two screenshots of WFM after importing `import_1.Json`. The first is the field-mapping key: `RosterCode` is the scenario tab, `TeamCode` the `Nº` group row, `EmployeeCode` the employee row, and `ScheduleCode 100154` renders as `00:00-07:00` with a `04:00-04:30` meal break. |

Direction is easy to get backwards, and everything follows from it: Sisqual's
**Export** (`Inp*`) is data leaving WFM and is therefore *the problem*; their
**Import** (`Out*`) is the result read back and is therefore *our output*.

## `schedules/schedules_without_meal.csv`

`Schedules_Without_meal.xlsx` converted to CSV, with `startMin`/`endMin` derived
from each row's `HH:MM-HH:MM` description so the catalogue is usable without
re-parsing strings. 1,277 codes. Regenerate it with the snippet in
[../docs/FORMAT.md](../docs/FORMAT.md) if Sisqual sends a new spreadsheet.

Every windowed row's `endMin - startMin` equals its stated
`scheduleWeightMinutes`, including the four that cross midnight — checked, not
assumed. Three caveats, all in [../docs/next_meeting.md](../docs/next_meeting.md):

- it is the **without-meal** catalogue, and `ScheduleCode 100154` from Sisqual's own
  result sample is not in it (item 5);
- it is on a **15-minute** grid while the bundles declare 30, so 914 of its codes
  are unreachable as specified (item 6);
- `1020 Flexible` has a length but no window (item 7).

## `build_example_result.py`

Builds `../examples/cenario2_retail/result.json` and its sidecar
`result_schedules.csv`. It lives here, not in `src/`, because it is provenance for
one synthetic artifact rather than a tool the format needs: **no v4.0 solver exists
yet**, so the result is constructed by a fixed rule (nearest duration, then best
overlap with that day's demand) purely so the result form has a realistic instance
to be validated against. The rule is stated in full at the top of the file, and
every substitution it makes is counted into the `_comment` block it writes.

```bash
PYTHONPATH=src python3 reference/build_example_result.py
```

## Removed from version control

`../IntegracaoUA_SISQUAL/ServidoresSISQUAL/` held a PuTTY private key
(`KEYLINUX-PC.ppk`) and a plaintext credentials file. Both were committed in
`49fd827`. They are now untracked and listed in `../.gitignore`, and the files
remain on disk for whoever needs them.

> **The blobs are still in git history.** Untracking does not remove them from
> `49fd827`, so anyone who has fetched this branch still has both. The SSH key and
> the four WFM passwords need rotating with Sisqual — that is the actual fix;
> the `.gitignore` only stops it getting worse.

# Reference material

The vendor drop, exactly as it arrived. Nothing here is authored by us except this file, and nothing here is read by the code or the tests — it is the provenance behind the claims in [../next_meeting.md](../next_meeting.md), not a fixture.

Direction is easy to get backwards, and everything follows from it: Sisqual's **Export** (`Inp*`) is data leaving WFM and is therefore *the problem*; their **Import** (`Out*`) is the result read back and is therefore *our output*.

| path | what it is |
|---|---|
| `IntegracaoUA_SISQUAL/JSON/20260708_Import_Export_Docs/` | `JSON-Import.docx` and `JSON-Export.docx` — the WFM-side contract, authored by Sisqual 2026-07-08. **Byte-identical** to the copies transcribed at `../../schema_v3/reference/sisqual-json-import-export/`, so read the `.md` versions there. |
| `IntegracaoUA_SISQUAL/JSON/20260723_email_Sisqual_to_UA/` | the `Re: Schema 3.0` thread. Sisqual's reply carries the `OutRosterTeamDays` sample and a shift spreadsheet; the `.docx` is a Word printout of the same body. |
| `IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_2/` | the bundle behind `../examples/cenario2_retail/`. |
| `IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_1/` | **not shipped as an example.** It fails three independent ways — a contract that cannot fit the grid, no competencies, and no demand. [next_meeting.md](../next_meeting.md) item 21 ("the scenario we had to drop"). |
| `IntegracaoUA_SISQUAL/sisqual-alg-input/` | the July bundle. It predates `priorityHierachy` and `constraints`, and its `contracts.definitions` is `[]` while all 15 employees reference `PT_40`. |
| `IntegracaoUA_SISQUAL/sisqual-alg-output/` | two screenshots of WFM after importing a result. The first is the field-mapping key: `RosterCode` is the scenario tab, `TeamCode` the `Nº` group row, `EmployeeCode` the employee row. |

## On the shift spreadsheet

`Schedules_Without_meal.xlsx` is in the email folder and **v4.0 derives nothing from it**. A schedule code stands for a grouping of hours, and the menu CSV is that translation — so the menu is ours to author. See [../docs/FORMAT.md](../docs/FORMAT.md) and [../next_meeting.md](../next_meeting.md) item 5 ("mint our own schedule codes").

## A note on what used to be here

An earlier revision committed a PuTTY private key and a plaintext credentials file under `ServidoresSISQUAL/`. Those files have been removed from the tree. **The blobs remain in git history** (commit `49fd827`), so untracking them was never the fix: the SSH key and the WFM passwords need rotating with Sisqual.

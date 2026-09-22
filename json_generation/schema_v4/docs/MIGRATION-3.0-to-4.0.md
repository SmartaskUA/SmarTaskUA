# Migrating v3.0 → v4.0

A breaking change. Nothing auto-upgrades, and v4.0 ships no converter: if what you hold is a **SISQUAL export** rather than a v3.0 file we authored, the differences are listed in [next_meeting.md](../next_meeting.md) under *Naming and format* — that list is what we are asking them to change, rather than something we translate around.

## Why there is a v4.0 at all

v3.0 was a specification we wrote and sent to Sisqual in July 2026. They implemented an exporter against it and, in September, delivered bundles that still stamp `"schemaVersion": "3.0"` but do not validate against it: the demand block alone has three file pointers where v3.0 requires one, and both of v3.0's required demand catalogues are absent.

So v4.0 is not a redesign. It is v3.0 reconciled with what the other side actually produces — keeping v3.0's structure wherever both can express a fact, and adopting Sisqual's where theirs is richer or simply is what exists. Where their export is simply wrong (three misspelled keys, three capitalised enums), v4.0 spells it correctly and the correction becomes something to agree with them.

## Changed

| from (v3.0) | to (v4.0) | why |
|---|---|---|
| `demand.dataFile` (one CSV) | `dataFileDays` + `dataFilePeriods` + `dataFileShifts` | Sisqual states demand in three collections at three grains, and the days grain is a different unit; folding them into one file would lose that |
| `competencyAssignments[].competency` (one code) | `.tableName` + `.tableValue` | coverage is keyed on a two-dimensional coordinate: `Team/T1` and `Responsibility/A` are different axes and a worker holds both |
| demand CSV `competency` column | `tableName` + `tableValue` columns | same |
| demand CSV `minimum,empiric,maximum` | `minimum,ideal,estimated` | Sisqual's columns. **The ordering is unresolved — see the callout below.** |
| `minimum` as an integer | a **float** | `4.5` occurs in Cenário 2 |
| demand `start`/`end` optional overrides | **mandatory** on the periods and shifts grains | there are no named work periods left to override |
| schedule_input cells in **minutes** (`480`); `1–24` rejected | cells in **hours** (`8`, `7.2`); above 24 rejected | Sisqual's unit. The guard is inverted, not removed. |
| `demand.priorityOrder[] {order, competency, level?}` | root `priorityHierarchy[]`, nine fields | it is no longer only a fill order; it carries alarm-table and generation settings |
| `calendar.weekStart`, `dayOffCodes[].kind` | unchanged, still lowercase | Sisqual capitalises both |
| — | `metadata.rosterCode` | a result names `RosterCode` alone; stating the join once beats re-splitting `problemId` |
| — | **`demand.dimensions[]`, required** | the replacement for the removed catalogues, and the only thing that makes `tableName` checkable |
| `form: "declarative"` | `form: "input"` | it pairs with `result`; "declarative" only made sense against the expanded form v4.0 does not have |
| — | `schedules.dataFile` (optional) | the shift menu a result picks from, authored by us |
| — | `constraints {hard[], soft[]}` | **re-admitted** — see below |

## Removed

| removed | why |
|---|---|
| `demand.organizationalUnits.competencies[]` | Sisqual exports no competency catalogue; `demand.dimensions[]` replaces it in a shape that matches the new coordinate |
| `demand.workPeriods[]` (`{code, name, timeRange}`) | there are no named, reusable periods any more; every demand row carries its own literal window. The name survives only as `shifts_demand.csv`'s `workPeriod`, which is Sisqual's `ShiftTypeCode` (M/T/N) — a different thing |
| `contracts.definitions[].constraints{…}` | Sisqual never emits per-contract limits; the nearest equivalent is the roster-wide `constraints.hard[].parameters`, under different names |
| the **expanded** form and `transform.py` | v4.0 has no synthesis step. Sisqual picks shifts from a catalogue rather than having them synthesised, so the expanded form has nothing to compile *into* until a v4 solver exists |
| the **solution** form and `merge.py` | replaced by the result form, which is Sisqual's own `OutRosterTeamDays` payload. Warm-start seeding has no consumer in v4.0 |
| `contractAssignments[].end: null` as the *only* open-ended spelling | still the canonical one; Sisqual's `"9999-12-31"` is not accepted |

## Re-admitted

v3.0 **removed** `constraints` and made a leftover block a validation *error*, on the principle that nothing enters the schema until a consumer reads it. v4.0 brings it back, because Sisqual now populates it with real labour law (`InpLabourLawCollection`) and the validator acts on two of its parameters.

This is a genuine reversal of a v3.0 decision, and worth naming as one. The discipline behind it is intact: the block returned only once it carried data a consumer reads. `constraints.soft[]` is still empty in every bundle, so its shape is left unconstrained rather than invented.

## The one that corrupts silently

**The demand triple's ordering is not established, and you must not assume it.**

- v3.0 was ascending: `minimum ≤ empiric ≤ maximum`.
- v2.6, whose header v4.0 now carries, was `minimum ≤ estimated ≤ ideal` — **`ideal` was the upper bound sitting in the middle column.**

Sisqual writes `0` in both `ideal` and `estimated` in every row of every bundle, so nothing in the data distinguishes the two conventions. The validator therefore enforces **no ordering at all** between the three, only non-negativity.

If you are migrating a v3.0 `demand.csv` by hand, **do not simply rename `empiric`→`ideal` and `maximum`→`estimated`.** Under the v2.6 reading those two exchange values, and a rename alone inverts them while still passing every check. Leave them at `0` until [next_meeting.md](../next_meeting.md) item 1 ("the ordering of") is answered.

## The other one: the grid

v4.0 inherits v3.0's rule that every duration must be a multiple of `timeGrid.slotMinutes`, and it now bites in practice. Sisqual emits `slotMinutes: 30`, and one of their two September scenarios has a contract of 432 minutes a day — not a multiple of 30, so nothing can be scheduled for anyone. Check this first on any new bundle; it is a one-line check and it invalidates everything downstream.

## Checklist

1. Split `demand.csv` into the three grains, and be clear which of yours is headcount and which is workload minutes.
2. Rename the demand `competency` column to `tableName` + `tableValue`, and decide your dimension names. Declare every pair in `demand.dimensions[]`.
3. **Leave `ideal`/`estimated` at `0`** unless you know the ordering. Do not swap, do not rename by hand.
4. Divide every schedule_input numeric cell by 60. A cell of `480` is now an error.
5. Check every contract's `workMinutesPerDay` against `slotMinutes` before anything else.
6. Move `demand.priorityOrder` to root `priorityHierarchy`, `order` → `rank`, `competency` → `tableName`/`tableValue`.
7. Delete `demand.organizationalUnits` and `demand.workPeriods`; fold the periods' `timeRange` into each demand row's `start`/`end`.
8. Add `metadata.rosterCode`, and `schedules.dataFile` if you have a catalogue.
9. Rename `form` to `"input"`.
10. Validate: `make validate DIR=<dir> ARGS=-v`.

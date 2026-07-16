# Scheduling Problem Schema v3.0

Hybrid **JSON + CSV** definition of an employee scheduling problem: JSON carries structure and
configuration, CSV carries the two large matrices (per-day demand, per-employee-per-day input).

Target mathematical model: **`MathematicalDefinition7.pdf`** ("Final formulation") in `reference/`.
Symbols in square brackets in the schema descriptions -- `[H_wd]`, `[alpha_dts]`, `[D_wk]` -- refer
to it.

## What is new in 3.0

| | v2.6 | v3.0 |
|---|---|---|
| Time unit | hours in contracts, minutes in breaks, HH:MM in periods, hours in `duration` | **minutes everywhere**, on a configurable `timeGrid.slotMinutes` (default 15) |
| Midnight crossing | bare HH:MM; readers inferred roll-over from `start > end` | minutes past 1440 (`22:00-06:30` -> `1320-1830`) |
| Problem forms | one | **two**: declarative + expanded (`H_wd`/`delta`), with a compiler between them |
| Solution | not describable | `schema-v3-solution.json` |
| Demand columns | `minimum,ideal,estimated` (`ideal` = upper bound, in the middle column) | `minimum,empiric,maximum`, ascending; `0` = unset |
| Hard/soft | fixed in the schema | per **algorithm phase** (`demandInterpretation`), so a pipeline can read the same demand differently |
| Contracts over time | date-ranged | date-ranged (unchanged) |
| Teams over time | **static** | date-ranged, symmetric with contracts |
| Holidays | none | `calendar.holidays`, with `hasEve` for the day before |
| Week start | `monday-sunday` \| `sunday-saturday`, buried under advanced constraints | `calendar.weekStart`, any of 7 days |
| Fill order | `{rank, team, level:"N>=2"}` -- a rank plus an unparseable string | `demand.priorityOrder`: ordered `{order, team, level?}`, first match wins; the solver derives the model's weights |
| Day-off kinds | one opaque code space | `preferable` (soft, `D_wk`) vs `unavailable` (hard, `U_wk`) |
| Competence level | schema said `1=junior`; the maths said `1=highest` | **`1` = highest**, matching the maths |

## The two forms

Both describe the same problem and share every section except one.

- **Declarative** (`schemas/schema-v3-declarative.json`) -- how a human or the wizard writes it:
  contracts, employees, work periods, and a per-employee-per-day CSV of requirements. What a worker
  *may* work is implied.
- **Expanded** (`schemas/schema-v3-expanded.json`) -- the pre-processed form: for each worker and day, the
  explicit set of daily working assignments they may take. This is the model's `H_wd`, and the
  timeslots each assignment covers is `delta_wdht`. V7 defines both; no schema before v3 stored them.

Only `scheduleInput` is swapped for `assignmentCatalog` + `availability`. `contracts`,
`employees`, `demand` (work periods included), `calendar`, `constraints` and `optimization` are
identical in both -- expanding changes how workable time is *expressed*, never what is asked for.

Each schema file is **standalone**: none references another, so each can be read, validated and
changed on its own. The duplication between them is deliberate.

```
declarative problem  --[ src/schema_v3/transform.py ]-->  expanded problem  -->  solver  -->  solution
```

## Quick start

```bash
python3 src/schema_v3/validator.py examples/sisqual_example/problem.json -v
python3 src/schema_v3/transform.py examples/sisqual_example/problem.json --stats
python3 src/schema_v3/validator.py examples/sisqual_example/problem.expanded.json -v
python3 tests/test_v3_conformance.py          # 65 checks
```

Requires `jsonschema>=4.18` (see `requirements.txt`). The validator degrades to
cross-reference and conformance checks only if it is absent.

The validator does three passes: JSON Schema, cross-references, and **feasibility** — it dry-runs
the expansion and rejects any cell that can never produce an assignment, naming the reason. That
last pass is what stops a problem being silently rewritten into a different one: an impossible cell
would otherwise just become a day off, shifting that week's working-day target while validating
clean.

## Work periods are demand buckets, not shifts

The single most common misreading. A row saying *one person on `CHECKOUT_1100_2100`* asks for
coverage across 11:00-21:00; it does **not** say anyone works a ten-hour shift. Work periods
define where demand sits and, together, the operating window.

What a worker may actually work is a **contiguous block of their contracted length, positioned
anywhere on the grid inside the operating window**. That is why the sisqual example can ask a
full-timer for 480 minutes when no declared period is 480 minutes long, and it is what the live
solver already does (`src/scheduler/algorithms/sisqual_hours_utils.py:build_assignments`).

## Layout

```
schemas/                     THE SPEC -- three standalone JSON Schemas
  schema-v3-declarative.json   Form A  (+ scheduleInput)
  schema-v3-expanded.json      Form B  (+ assignmentCatalog, availability)
  schema-v3-solution.json      solver output; the other half of a package
src/schema_v3/               the Python tooling (one package, flat sibling imports)
  core.py                      shared domain: time, cells, candidate generation
  transform.py                 declarative -> expanded
  validator.py                 schema + cross-reference + feasibility + V7 conformance
tests/                       conformance suite
docs/
  FORMAT.md                    CSV formats and cell semantics
  MIGRATION-2.6-to-3.0.md      what changed and what will bite you
examples/                    two worked examples, each in both forms
templates/                   commented starting points
reference/                   maths spec (MathematicalDefinition7.pdf), vendor docs, working notes
requirements.txt             jsonschema, for the schema-validation pass
```

## Scope of this release

Delivered: the spec, the reference transformer, the validator, examples, docs.

**Not** delivered: no consumer was migrated. `sisqual_hours_utils.py`, the four Sisqual solvers,
`ProblemService.java`, `RabbitMQClient.py` and the json-generator wizard still speak v2.2/v2.6.
This is deliberate -- but note the v2.5->v2.6 "upgrade" was a directory copy that changed no
consumer, which is why every bundle in `data/problems/` is still `schemaVersion: "2.2"`. v3.0 is
only worth having if something is migrated onto it.

Deferred by decision:

- **Per-employee rules** (notes.md L30, e.g. holiday entitlement by workplace vs residence). The
  `scope` field on rules is reserved for this; v3.0 accepts `"global"` only.
- **Holiday-driven availability.** `calendar` marks holidays so they can carry their own demand.
  It does not decide who works -- shops open on holidays, and entitlement is the per-employee rule
  above.
- **The org model** (notes.md L23-24, teams vs competencies vs responsibilities; the note marks
  itself *"perguntar e verificar"*). v3.0 keeps v2.6's team+level model. V7 makes this cheap: it
  removed V5's per-level demand `beta_dtsl`, so demand stays skill-keyed exactly as before.
- **Sisqual reconciliation** (notes.md L26) and the workflow/PM platform (L38).

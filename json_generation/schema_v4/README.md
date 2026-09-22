# Scheduling Problem Schema v4.0

A hybrid **JSON + CSV** definition of an employee scheduling problem, reconciled
with what SISQUAL's generator actually produces. JSON carries the structure; four
CSVs carry the matrices (three demand grains, one per-employee-per-day input), and
a fifth CSV carries the shift catalogue a result must pick from. The target
mathematical model is `../schema_v3/reference/MathematicalDefinition7.pdf`, whose
symbols the schema descriptions cite in square brackets (`[H_wd]`, `[alpha_dts]`, …).

## Why v4.0 exists

We sent Sisqual v3.0 in July 2026. They built an exporter against it and in
September delivered bundles that still stamp `"schemaVersion": "3.0"` but do not
validate against v3.0 at all. v4.0 is v3.0 reconciled with that reality — and it is
deliberately **not** a copy of their dialect:

```
SISQUAL bundle  --[ src/schema_v4/sisqual_adapt.py ]-->  canonical v4.0 problem
(their spelling)                                                    |
                                                                    v
                                                                  solver
                                                                    |
                                                                    v
                                                      result (OutRosterTeamDays)
                                                        --> imported back into WFM
```

The **problem** format is a specification we are writing together, so v4.0 spells
it correctly — their `contractAssigments`, `priorityHierachy` and
`inpUAHolidaysCollection` are fixed, and their raw files do not validate until the
adapter has run. The **result** format is their existing WFM import API, so v4.0
conforms to it verbatim, PascalCase and all. Assert on what we co-design; conform
on what we consume.

Every correction the adapter makes is printed, and the list is
[docs/next_meeting.md](docs/next_meeting.md) — the agenda to take to Sisqual.

## Quick start

```bash
pip install -r requirements.txt
export PYTHONPATH=src

# their bundle -> a canonical package, reporting everything it had to change
python3 -m schema_v4.sisqual_adapt \
  "IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_2" \
  -o /tmp/c2 --stats

python3 -m schema_v4.validator examples/cenario2_retail -v   # a package
python3 -m schema_v4.validator examples/cenario2_retail/result.json  # a result
python3 -m schema_v4.validator examples/                     # every package under it
python3 -m schema_v4.validator templates/                    # the templates too

pytest tests/                                                # the conformance suite
```

The validator takes a single file (form-aware — a result is cross-checked against a
sibling declarative problem, or one named with `--against`) or a **folder**, which
it validates package by package. Runtime needs `jsonschema>=4.18`; without it the
validator still runs its cross-reference and feasibility passes. Start a new
problem from `templates/`.

> **v4.0 is a real Python package**, unlike v3.0's flat-module layout, so run the
> tools with `python3 -m schema_v4.<tool>` and `src` on `PYTHONPATH`. v3.0's style
> registers top-level modules named `core`, `common` and `validator`, which would
> collide with v4's in one interpreter.

## Layout

```
schemas/          the spec -- two standalone JSON Schemas (declarative, result)
src/schema_v4/    core (domain + CSV I/O) -- validator (orchestrator + CLI) with the
                  layers common, validate_declarative, validate_result --
                  sisqual_adapt (their dialect -> canonical)
tests/            pytest suite, one file per module
docs/             FORMAT (formats + semantics), MIGRATION (3.0 -> 4.0),
                  DIALECT (their emission vs ours), FUTURE (what is deferred and
                  why), next_meeting (the agenda)
examples/         cenario2_retail -- a real SISQUAL bundle, adapted, with a worked
                  result and the sidecar catalogue naming the shifts it used
templates/        commented starting points; validates clean as a package
reference/        the raw vendor drop, and the ScheduleCode catalogue converted to CSV
```

`IntegracaoUA_SISQUAL/` is the untouched raw drop -- vendor documents, the
generated bundles, and the two screenshots; `reference/README.md` explains what
each piece is.

## The four things that differ most from v3.0

- **`schedule_input.csv` cells are hours, not minutes.** A contract says
  `workMinutesPerDay: 480` and the cell says `8`. One bundle, two units — Sisqual's
  choice, which we are asking them to reverse.
- **Coverage is keyed on a `(tableName, tableValue)` pair**, not a single competency
  code, and every pair must be declared in the new required `demand.dimensions[]`.
- **Three demand CSVs, two units.** `periods` and `shifts` are headcount; `days` is
  workload minutes, and its header is byte-identical to `periods`.
- **`constraints` is back.** v3.0 removed it and made a leftover an error; Sisqual
  now populates it with real labour law, so v4.0 re-admits it.

## More

- [docs/FORMAT.md](docs/FORMAT.md) — CSV formats, cell semantics, and what v4.0 leaves out.
- [docs/MIGRATION-3.0-to-4.0.md](docs/MIGRATION-3.0-to-4.0.md) — what changed and what will bite you.
- [docs/DIALECT.md](docs/DIALECT.md) — SISQUAL's emission vs canonical v4.0, field by field; the adapter's spec.
- [docs/FUTURE.md](docs/FUTURE.md) — what v4.0 does not carry and what each item is waiting on.
- [docs/next_meeting.md](docs/next_meeting.md) — the agenda: what is blocking, what we corrected, and what we are proposing.
- [../schema_v3/](../schema_v3/) — the previous version, still the reference for the two-form architecture and the transformer.

# Scheduling Problem Schema v4.0

A hybrid **JSON + CSV** definition of an employee scheduling problem. JSON carries the structure; four CSVs carry the matrices (three demand grains and one per-employee-per-day input), and a fifth carries the shift menu a result picks from. The target mathematical model is `../schema_v3/reference/MathematicalDefinition7.pdf`, whose symbols the schema descriptions cite in square brackets (`[H_wd]`, `[alpha_dts]`, …).

## Why v4.0 exists

We sent Sisqual v3.0 in July 2026. They built an exporter against it and in September delivered bundles that still stamp `"schemaVersion": "3.0"` but do not validate against v3.0 at all. v4.0 is v3.0 reconciled with that reality.

```
input problem  -->  solver  -->  result  +  result_schedules.csv
(JSON + 4 CSVs                 (OutRosterTeamDays)   the shifts it used
 + the shift menu)
```

**v4.0 ships no adapter, and that is deliberate.** The schema is the deliverable. Where Sisqual's export differs — three misspelled keys, three capitalised enums, a sentinel date, a bilingual dimension name — v4.0 spells it the corrected way and the correction becomes something to agree with them. Writing a translator now would mean building against a moving target; if they cannot align, we write it then. The full list is [next_meeting.md](next_meeting.md), which doubles as the agenda.

The one place v4.0 conforms rather than asserts is the **result**: `OutRosterTeamDays` is Sisqual's existing WFM import API, so `schema-v4-result.json` matches it verbatim, PascalCase and all.

## Quick start

```bash
make                                   # the target list
make install                           # .venv + requirements
make test                              # the conformance suite
make validate                          # examples/ and templates/
make validate DIR=path/ ARGS=-v        # anything else, with flags
make result                            # rebuild the worked example result
```

The validator takes a single file (form-aware — a result is cross-checked against a sibling input problem, or one named with `--against`) or a **folder**, which it validates package by package. Runtime needs `jsonschema>=4.18`; without it the validator still runs its cross-reference and feasibility passes. Start a new problem from `templates/`.

> Everything runs inside `.venv`, because this machine's Python is externally-managed (PEP 668) and installing pytest against it fails. `make` builds the venv on first use.

## Layout

```
schemas/          the spec -- two standalone JSON Schemas (input, result)
src/schema_v4/    core (domain + CSV I/O) -- validator (orchestrator + CLI) with the
                  layers common, validate_input, validate_result --
                  build_example_result (builds the worked example)
tests/            pytest suite, one file per module
docs/             FORMAT (formats + semantics), MIGRATION (3.0 -> 4.0),
                  FUTURE (what is deferred and why), next_meeting (the agenda)
examples/         cenario2_retail -- a real SISQUAL bundle corrected to v4.0, with a
                  worked result and the sidecar naming the shifts it used
templates/        commented starting points -- both forms, validating clean as a package
reference/        the untouched vendor drop -- documents, bundles, screenshots
```

## The five things that differ most from v3.0

- **Two forms, not three.** `input` and `result`. v3.0's expanded form and its transformer have no job here, because shifts come from a menu rather than being synthesised. `form` is `"input"`, not `"declarative"`.
- **`schedule_input.csv` cells are hours, not minutes.** A contract says `workMinutesPerDay: 480` and the cell says `8`. One bundle, two units — Sisqual's choice, which we are asking them to reverse.
- **Coverage is keyed on a `(tableName, tableValue)` pair**, not a single competency code, and every pair must be declared in the required `demand.dimensions[]`.
- **Three demand CSVs, two units.** `periods` and `shifts` are headcount; `days` is workload minutes, and its header is byte-identical to `periods`.
- **`constraints` is back.** v3.0 removed it and made a leftover an error; Sisqual now populates it with real labour law, so v4.0 re-admits it.

## More

- [docs/FORMAT.md](docs/FORMAT.md) — CSV formats, cell semantics, and what v4.0 leaves out.
- [docs/MIGRATION-3.0-to-4.0.md](docs/MIGRATION-3.0-to-4.0.md) — what changed and what will bite you.
- [docs/FUTURE.md](docs/FUTURE.md) — what v4.0 does not carry and what each item is waiting on.
- [next_meeting.md](next_meeting.md) — the agenda: what is blocking, what we corrected, and what we are proposing.
- [../schema_v3/](../schema_v3/) — the previous version, still the reference for the two-form architecture and the transformer.

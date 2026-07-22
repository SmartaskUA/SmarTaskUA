# Scheduling Problem Schema v3.0

A hybrid **JSON + CSV** definition of an employee scheduling problem: JSON carries the structure,
two CSVs carry the large matrices (per-day demand, per-employee-per-day input). The target
mathematical model is `reference/MathematicalDefinition7.pdf`, whose symbols the schema descriptions
cite in square brackets (`[H_wd]`, `[alpha_dts]`, …).

## The two forms

A problem exists in two interchangeable forms that share every section but one:

- **Declarative** — how a human or the wizard authors it. What a worker *may* work is implied.
- **Expanded** — the pre-processed form: for each worker and day, the explicit set of assignments
  they may take (the model's `H_wd`). The transformer compiles one into the other.

```
declarative problem  --[ src/schema_v3/transform.py ]-->  expanded problem  -->  solver  -->  solution
```

See [docs/FORMAT.md](docs/FORMAT.md) for the CSV formats and cell semantics — including the one
that trips everyone up: **work periods are demand buckets, not shifts** (a worker works a
contiguous block of their contracted length, not a named period).

## Quick start

```bash
python3 src/schema_v3/validator.py examples/sisqual_example/problem.json -v
python3 src/schema_v3/transform.py examples/sisqual_example/problem.json --stats
python3 src/schema_v3/validator.py examples/sisqual_example/problem.expanded.json -v
python3 tests/test_v3_conformance.py          # conformance suite
```

Needs `jsonschema>=4.18` (`requirements.txt`); without it the validator still runs its
cross-reference and feasibility passes. Start a new problem from `templates/`.

## Layout

```
schemas/          the spec — three standalone JSON Schemas (declarative, expanded, solution)
src/schema_v3/    the Python tooling — core (shared domain), transform, validator
tests/            conformance suite
docs/             FORMAT (formats + semantics), MIGRATION (2.6 -> 3.0), FUTURE (roadmap),
                  SISQUAL-MERGE (vendor-format comparison + merge proposal)
examples/         two worked examples, each in both forms
templates/        commented starting points
reference/        maths spec, vendor docs, working notes
```

## More

- [docs/FORMAT.md](docs/FORMAT.md) — CSV formats, cell semantics, and what v3.0 deliberately leaves out.
- [docs/MIGRATION-2.6-to-3.0.md](docs/MIGRATION-2.6-to-3.0.md) — what changed and what will bite you.
- [docs/FUTURE.md](docs/FUTURE.md) — what's next and why (break logic first).
- [docs/SISQUAL-MERGE.md](docs/SISQUAL-MERGE.md) — how the Sisqual import/export format maps onto v3.0, tiered easy/medium/hard, with a merge proposal.
- [docs/SISQUAL-MERGE-PROPOSAL.md](docs/SISQUAL-MERGE-PROPOSAL.md) — merged-schema proposal index: foundational decisions + per-tier decision files (easy/medium/hard/set-aside).

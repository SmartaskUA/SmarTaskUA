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
                                                                 ▲                              │
                                        seeded expanded  --[ src/schema_v3/merge.py ]------------┘
```

A solution doubles as a partial **warm-start seed**: `merge.py` folds its `locked` days into a problem
(declarative or expanded) as `forced` pins, producing a seeded — but otherwise ordinary — expanded.

See [docs/FORMAT.md](docs/FORMAT.md) for the CSV formats and cell semantics — including the one
that trips everyone up: **work periods are demand buckets, not shifts** (a worker works a
contiguous block of their contracted length, not a named period).

## Quick start

```bash
python3 src/schema_v3/validator.py examples/sisqual_example/problem.json -v
python3 src/schema_v3/transform.py examples/sisqual_example/problem.json --stats
python3 src/schema_v3/validator.py examples/sisqual_example/problem.expanded.json -v
python3 src/schema_v3/validator.py examples/                 # a folder -> every package
python3 src/schema_v3/merge.py examples/sisqual_example/problem.expanded.json \
        examples/sisqual_example/solution.json --stats       # seed's locks -> forced pins
pip install -r requirements.txt && pytest tests/             # the conformance suite
```

The validator takes a single file (form-aware — a solution is cross-checked against a sibling
`*.expanded.json`, or one named with `--against`) or a **folder**, which it validates package by
package (a directory's declarative/expanded/solution forms + their CSVs). Runtime needs
`jsonschema>=4.18` (`requirements.txt`); without it the validator still runs its cross-reference and
feasibility passes. Tests additionally need `pytest` (also in `requirements.txt`, marked test-only).
Start a new problem from `templates/`.

## Layout

```
schemas/          the spec — three standalone JSON Schemas (declarative, expanded, solution)
src/schema_v3/    core (shared domain) · transform · merge (seed's locks -> forced) · validator
                  (orchestrator + CLI) with the validation layers: common, validate_declarative,
                  validate_expanded, validate_solution
tests/            pytest suite, one file per type (schemas, core, transform, validator_*, packages, …)
docs/             FORMAT (formats + semantics), MIGRATION (2.6 -> 3.0), FUTURE (roadmap)
docs/sisqual/     Sisqual merge — tiered comparison, per-tier decisions, meeting guide
examples/         two worked examples, each in both forms
templates/        commented starting points
reference/        maths spec, vendor docs, working notes
```

## More

- [docs/FORMAT.md](docs/FORMAT.md) — CSV formats, cell semantics, and what v3.0 deliberately leaves out.
- [docs/MIGRATION-2.6-to-3.0.md](docs/MIGRATION-2.6-to-3.0.md) — what changed and what will bite you.
- [docs/FUTURE.md](docs/FUTURE.md) — what's next and why (break logic first).
- [docs/sisqual/SISQUAL-MERGE.md](docs/sisqual/SISQUAL-MERGE.md) — how the Sisqual import/export format maps onto v3.0, tiered easy/medium/hard, with a merge proposal.
- [docs/sisqual/SISQUAL-MERGE-PROPOSAL.md](docs/sisqual/SISQUAL-MERGE-PROPOSAL.md) — merged-schema proposal index: foundational decisions + per-tier decision files (easy/medium/hard/set-aside).
- [docs/sisqual/MEETING-GUIDE.md](docs/sisqual/MEETING-GUIDE.md) — slide-by-slide speaker guide for the merge meeting: decisions made, questions for Sisqual, and what's deferred to future work.

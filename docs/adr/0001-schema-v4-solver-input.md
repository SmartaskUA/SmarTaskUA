# 0001 – One parser for schema v4, shared by every solver

**Sprint:** September 2026

## Context

Schema v4 (`json_generation/schema_v4/`) is the problem format exchanged with Sisqual. A package may carry a
**partial** result: the employee-days it lists are fixed, the others open. No solver read v4. The scheduler had
three input contracts (v2.2 bundles, the GA's SMARTASK folders, legacy rows), and each place that interpreted
input on its own had drifted from the others. v2.2 is no longer a target.

## Decision

- **One parser, one instance.** `src/scheduler/problem_v4/load_package` is the only code that reads v4. Every
  v4 solver consumes its `V4Instance` directly and only reshapes it into variables. The parser reads with a
  byte-identical, drift-tested copy of the validator's `core.py`.
- **A partial result is a domain restriction.** A fixed day's candidate set is the one shift the result names.
  Every paradigm (ILP/CP variables, GA genes, greedy blocks) already chooses from such a set, so fixed days,
  and the labour law around them, need no per-solver code. The parser rejects a contradictory partial result
  before any solver runs.
- **The v4 validator is the arbiter.** The cell alone decides work versus rest. A preferable day off rests
  unless `allow_day_off_swap` is on, because a swap rests a work cell and the validator rejects that. Solvers
  decide which menu shift each work day gets and which skill each slot covers, one value per axis.
- **One scorer and one writer.** `problem_v4.evaluate` scores any solver's rows. `write_package` turns them
  into a complete `OutRosterTeamDays` result, which the validator accepts.
- **Weights are solve directives.** v4 carries no soft constraints, so the defaults are `w1=1000, w2=1, w3=10`.
  `w2` stays small: with v4's tiers p_sl reaches 31, and at the v2.2 value of 100 the solver would move
  shifts away from demand.

Benchmark on `examples/cenario2_partial` (105 of 465 employee-days fixed, one minute each):

| solver | shortage | p_sl cost | time |
|---|---|---|---|
| ILP / CP-SAT | 489 (optimal) | 55 397 | 2 s / 4 s |
| GA v4 | 490 | 57 521 | 30 s |
| Hybrid / Hybrid with levels | 506 / 510 | 61 308 / 58 137 | 4 s / 2 s |

## Consequences

**Positive:** every solver and the validator read a package the same way, so benchmarks compare like with
like. Partial results work in every paradigm, and every output is a valid v4 result.

**Negative:** v2.2 bundles no longer run under the MD7 and Hybrid names; the v2.2-only code awaits a separate
cleanup. A day off is never swapped by default, headcount is rounded up, and demand after midnight is not
covered by a shift that started the day before.

## Related

[how-to-solve](../how-to-solve.md) · [v4-parser](../architecture/v4-parser.md) · [algorithms](../algorithms/overview.md)
(what the other families would need) · `json_generation/schema_v4/next_meeting.md` items 29-32 (open questions).

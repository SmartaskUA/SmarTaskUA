# Quick wins — what we can build now

From all the merge decisions ([tiers](SISQUAL-MERGE-PROPOSAL.md)) and the roadmap
([`../FUTURE.md`](../FUTURE.md)), what is worth doing **right now**: small, sensible, and without
tripping v3's own discipline — **no stored-but-ignored fields.**

## The filter

An item qualifies as *do now* only if it passes all four:

1. **Small** — a contained change.
2. **Has a real consumer today** — something reads/uses it now, so it isn't dead data.
3. **Not gated on Sisqual** — doesn't wait on an answer only they can give.
4. **No deferred dependency** — doesn't need the solver, the registry, or the adapter to exist first.

Almost every merge item fails #2, #3, or #4 — which is *why* they're deferred. Only two pass cleanly.

---

## Do now

### W1 — A worked solution example + document the solution form  ·  effort: low

**The gap:** `schema-v3-solution.json` exists but has **zero instances** — no file anywhere is a
solution, so the third form is entirely un-exercised and undocumented.

**Do:** add `examples/sisqual_example/solution.json` — a plausible solved output whose `assignmentId`s
are drawn from the committed `problem.expanded.json`, with a couple of `shortfalls` and a `skillPerSlot`
entry. Add a conformance test that it validates. Add a short **"Solution form"** section to
[`../FORMAT.md`](../FORMAT.md) (what a solution is; the `assignmentId ↔ availability` and `problemId`
references; `shortfalls`).

**Consumer:** the conformance suite and the docs — it makes the solution contract real and catches
schema drift. **Touches:** one new example file, `tests/test_v3_conformance.py`, `FORMAT.md`.

### W2 — A solution cross-validator (`validate_solution`)  ·  effort: low–moderate

**The gap:** the validator gives `form: "solution"` **only** the JSON-Schema layer — it never
cross-checks a solution against its problem, even though the schema *prescribes* the references. So a
solution that assigns a worker a shift they can't take, on a date outside the horizon, still "validates."

**Do:** add `validate_solution()` (given the solution + its expanded problem via a `--problem` arg,
falling back to a sibling `*.expanded.json`) enforcing what the schema already states:

- `problemId` equals the problem's `metadata.problemId`;
- every `(employeeId, date)` exists and lies in the horizon;
- every non-null `assignmentId` ∈ that worker-day's `availability.assignmentIds` (the model's `H_wd`);
- `workedPreferableDayOff` is true only where that day's `dayOff == "preferable"`;
- each `skillPerSlot.team` is a team the worker actually holds, and its interval lies inside the chosen assignment;
- `shortfalls` dates/teams are known and on the grid;
- `status` `infeasible`/`error` carries no assignments.

It reuses the exact id-resolution pattern already in `validate_expanded`. **This is the FUTURE §7
package-validator's core, minus the one deferred piece (lock-agreement) — buildable today.**

**Consumer:** any solver that emits a v3 solution — it catches real solver bugs (assignments outside
`H_wd`, wrong dates, unknown teams). **Touches:** `validator.py` (new method + `run()` dispatch),
`tests/`. Pairs with W1 (the example gives it something to test against).

### W3 — Per-weekday contract weights  ·  *available, but hold*

Optional `workMinutesByWeekday` (+ holiday override) that the transform's synthesis consumes per date
(shorter Saturdays, etc.). It's the **one** `../FUTURE.md` §9 item that would **not** be dead data —
synthesis actually reads the per-day duration. But **no example needs it yet**, so building it now is
mild speculation. **Verdict: ready to build the moment a real contract requires it — not a today action.**

---

## One inconsistency to fix in the decisions (doc-only)

The decisions contradict themselves on one field:

- **M5** ([MEDIUM](SISQUAL-MERGE-MEDIUM.md)) says: *"Add `weeklyContractedMinutes` … The field is added
  **now** for lossless round-trip."*
- **SET-ASIDE** says monthly/yearly caps are *"held back … the same discipline applied to **M5's weekly
  target**"* — i.e. treats M5's field as **deferred**.

By the no-dead-data rule, **SET-ASIDE is right**: nothing reads `weeklyContractedMinutes` yet, so it
should wait for the round-trip consumer (the adapter), exactly like the monthly/yearly caps. **Fix:**
reword M5 to "added *with the adapter*," not "now." Small doc edit, worth making so the ruleset is
self-consistent.

---

## Explicitly NOT now — and the blocker for each

Nothing below is forgotten; each waits on a specific thing.

| item | why not now |
|---|---|
| S1 roster / org level · M4 skill-vs-team · M1 demand columns · M3 rest-types | **gated on a Sisqual answer** (see the [meeting guide](MEETING-GUIDE.md)) |
| S3 labour-law level · `locked` seed flag · tasks/responsibilities carriers · `weeklyContractedMinutes` · monthly/yearly caps | **would be dead data** — need the adapter or another consumer first |
| break logic (§1) · solve-directives registry (§2) · all enforcement · holiday entitlement (§5) · workload demand (§9) | **need the solver / a new formulation** |
| the adapter itself (§6) | a real build, not a quick win — but it's the key that unlocks every round-trip carrier above |

---

## Dependency chain — what unlocks what

- **Sisqual's answers** → unlock S1, M3, M4 (and M1's columns).
- **The adapter (§6)** → unlocks every round-trip carrier (`weeklyContractedMinutes`, monthly/yearly
  caps, tasks/responsibilities carriers, the `locked` seed).
- **The registry (§2)** → unlocks all enforcement (labour-law rules, pins-bypass-`T_d`, demand-bound
  interpretation).

**W1 and W2 depend on none of these** — which is exactly why they're the only true do-now items. They
also *pave the way*: W2 is the seed of the §7 package validator the adapter will need.

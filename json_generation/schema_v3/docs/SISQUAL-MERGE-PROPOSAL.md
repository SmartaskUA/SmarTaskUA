# Sisqual ↔ v3.0 — merged schema proposal (index)

A middle-ground **merged schema** both sides can adopt, decided tier by tier for the meeting. This page
is the index; the analysis and the foundational decisions live in the hub.

**Start here:** [SISQUAL-MERGE.md](SISQUAL-MERGE.md) — the field-by-field analysis **and** the
foundational decisions every tier assumes (v3.0 as the base, the JSON+CSV hybrid, canonical vocabulary,
code preservation).

### Reading legend (used across the tier files)

- **✅ Decision** — proposed representation, ready to confirm; an alternative may be noted inline.
- **🔀 Choice A / B** — a genuine fork with real trade-offs; the team picks in the meeting.
- **→ S# / M# / Tier** — a cross-reference to another decision.

### The tiers

| tier | what's in it | status |
|---|---|---|
| [Easy](SISQUAL-MERGE-EASY.md) | clean renames + three structural decisions (S1 roster, S2 datetime, S3 labour law) | decided |
| [Medium](SISQUAL-MERGE-MEDIUM.md) | demand tables, per-day state, rest taxonomy, team-vs-ability, weekly target, result bridge | decided — 4 open choices |
| [Hard](SISQUAL-MERGE-HARD.md) | shift catalog vs synthesis; the schema-form question | to build |
| [Set aside](SISQUAL-MERGE-SET-ASIDE.md) | Sisqual-only features (tasks, responsibilities, rules…) | to weigh |

### Open choices to settle in the meeting

- **N1** — canonical vocabulary (v3 names vs Sisqual names) — *foundational, in the hub*.
- **S1.a** — are team codes roster-scoped? *(needs Sisqual)* — plus the roster-vs-board semantics.
- **S2.a** — ✅ settled: full ISO datetime at the JSON layer.
- **M1.a** — demand value columns: three, or carry `estimated` for lossless round-trip.
- **M2.a** — a fixed shift: `EQUALS:` cell vs forced catalog id *(depends on Hard)*.
- **M3.a** — rest taxonomy: soft/hard + translation vs complementary/obligatory first-class.
- **M4.a** — team vs ability: conflate vs separate org from skill *(the org-model call)*.

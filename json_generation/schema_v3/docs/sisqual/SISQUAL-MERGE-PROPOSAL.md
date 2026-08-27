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
| [Easy](SISQUAL-MERGE-EASY.md) | clean renames + two structural decisions (S1 roster, S3 labour law) + one open question (S2 time representation) | decided — S2 open |
| [Medium](SISQUAL-MERGE-MEDIUM.md) | demand tables, per-day state, rest taxonomy, team-vs-ability, weekly target, result bridge | decided — 4 open choices |
| [Hard](SISQUAL-MERGE-HARD.md) | shift catalog vs synthesis; the schema-form question | decided (A) — 1 flagged limitation |
| [Set aside](SISQUAL-MERGE-SET-ASIDE.md) | Sisqual-only features (tasks, responsibilities, rules…) | decided — defer map + round-trip |

For the meeting itself — decisions to ratify, questions for Sisqual, and future work — see the
[meeting guide](MEETING-GUIDE.md).

### Open choices to settle in the meeting

- **N1** — canonical vocabulary (v3 names vs Sisqual names) — *foundational, in the hub*.
- **S1.a** — are team codes roster-scoped? *(needs Sisqual)* — plus the roster-vs-board semantics.
- **S2** — ❓ open, to settle with Sisqual: author-layer time boundary as `HH:MM` vs minutes, and the
  overnight marker (`end ≤ start` inference vs explicit `dayOffset`/`≥ 1440`). Day-anchor and `timeGrid`
  are settled; only the boundary *representation* is open. *(The earlier "full ISO datetime" call was
  withdrawn — it forced a date onto reusable work-period buckets.)*
- **M1.a** — demand value columns: three, or carry `estimated` for lossless round-trip.
- **M2.a** — ✅ settled: a fixed shift is an `EQUALS:` cell (split shifts now authorable); a whole
  Sisqual roster merges into one warm-start seed with a per-day `locked` flag (deferred build). T_d
  independence for pins is a FUTURE §2 solver directive, not a schema gap.
- **M3.a** — rest taxonomy: is soft/hard enough, or must Folga types be first-class? Gated on one
  question *(confirm with Sisqual)* — does labour law **count** Folga types over a time frame? If yes, it
  links to S3. Downstream of labour law.
- **M4.a** — team vs ability: v3's `team`=skill vs the three-concept model (skill dimension +
  configurable org hierarchy, demand on skill). Recommend B as target, A as interim. Bundles with S1 + M1
  → FUTURE §4. *(Confirm with Sisqual: is `TeamCode` purely org? is demand ever team-keyed?)*
- **H2** — ✅ decided: a Sisqual menu enters **expanded-only** (ingest into `assignmentCatalog`); the
  declarative catalog mode (B) was rejected for mixing concerns. ⚠️ **Flagged limitation:** imported
  menu problems have no declarative form. Reopens only if v3 must *author/edit* menus *(confirm with the
  team/Sisqual)*.
- **Set-aside round-trip** — ✅ decided: unmodeled Sisqual features stay out of the schema; lossless
  round-trip (if needed) is an adapter sidecar. *(Confirm with Sisqual: is lossless round-trip required,
  or is one-way lossy import acceptable?)*

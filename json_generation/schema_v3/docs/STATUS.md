# Status and scope

**Delivered:** the spec (three schemas), the reference transformer, the validator, examples,
templates, docs.

**Not delivered — no consumer was migrated.** `sisqual_hours_utils.py`, the four Sisqual solvers,
`ProblemService.java`, `RabbitMQClient.py` and the json-generator wizard still speak v2.2/v2.6.
This is deliberate — but note the v2.5→v2.6 "upgrade" was a directory copy that changed no
consumer, which is why every bundle in `data/problems/` is still `schemaVersion: "2.2"`. v3.0 is
only worth having once something is migrated onto it.

## Deferred by decision

- **Per-employee rules** (notes.md L30, e.g. holiday entitlement by workplace vs residence). The
  `scope` field on rules is reserved for this; v3.0 accepts `"global"` only.
- **Holiday-driven availability.** `calendar` marks holidays so they can carry their own demand.
  It does not decide who works — shops open on holidays, and entitlement is the per-employee rule
  above.
- **The org model** (notes.md L23-24, teams vs competencies vs responsibilities; the note marks
  itself *"perguntar e verificar"*). v3.0 keeps v2.6's team+level model. V7 makes this cheap: it
  removed V5's per-level demand `beta_dtsl`, so demand stays skill-keyed exactly as before.
- **Sisqual reconciliation** (notes.md L26) and the workflow/PM platform (L38).

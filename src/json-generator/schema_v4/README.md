# Vendored schema v4.0

`schema-v4-input.json` is a byte-for-byte copy of
`json_generation/schema_v4/schemas/schema-v4-input.json`, the canonical spec.

It lives here because the dev container mounts only `src/json-generator`, so the
wizard cannot import from `json_generation/` at runtime. `src/v4/schema.test.js`
fails the moment the two copies drift — to update, copy the canonical file over
this one, never edit this one by hand.

Everything else about v4 — the CSV formats, cell grammar and the traps — is
documented next to the canonical schema: `json_generation/schema_v4/docs/FORMAT.md`.

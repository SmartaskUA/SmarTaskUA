# Integration Plan: json-generator ↔ frontend (generate → publish → run)

> **Status:** Proposed (planning only — no implementation yet)
> **Scope:** Wire the problem-definition wizard (`src/json-generator`) into the main app
> (`src/frontend`) through the API (`src/api`); make creating, **storing, editing**, and running a
> scheduling problem one coherent loop; and bring the two apps to a **consistent UI**. Covers four
> dimensions: the publish/run **wire**, the **storage & data lifecycle**, the **end-to-end user
> flow**, and **UI integration**.
> **Related:** [`problem-json-flow.md`](./problem-json-flow.md), `docs/algorithms/overview.md`,
> `src/json-generator/schema_v2.6/`

---

## 1. Context & motivation

SmarTask is a polyglot Docker-Compose monorepo behind one nginx reverse proxy:

| Service | Tech | Role | URL (via nginx) |
|---|---|---|---|
| `frontend` | React + Vite | Main scheduling UI (managers) | `/` |
| `json-generator` | React + Vite | 10-step wizard → `problem.json` + CSVs | `/json-gen/` |
| `api` | Java Spring Boot | List/serve/solve problems | `/api/` |
| `scheduler` / `analyzer` | Python | Solver algorithms / KPIs (RabbitMQ consumers) | — |
| `mongo`, `rabbitmq` | — | Persistence, task queue | — |

Today the two front-end apps are **disconnected**. The wizard's only output is a downloadable ZIP;
to use a generated problem you must hand-copy it into `data/problems/{id}/` **and restart the API**
(problems are discovered only by a startup scan). The wizard's algorithm step is generic, its
constraint catalog doesn't match the solver, and — visually and navigationally — it looks and feels
like a separate product.

**Desired outcome:** a user builds a problem in the wizard, clicks **Publish to SmarTask**, the API
stores + registers it live (no restart), and the user lands back in the main app's Problems library
with the new problem selected, ready to solve. They can later **re-open a published problem to edit
and re-publish**. Throughout, the wizard looks and navigates like part of SmarTask.

### Decisions taken (with the user)
1. **Publish path:** add `POST /api/problems` (multipart) that saves files + registers at runtime.
2. **Algorithm source of truth:** expose `GET /api/algorithms`; wizard *and* frontend consume it.
3. **Post-publish UX:** redirect to the Problems library with the new problem preselected.
4. **Wizard "completion" scope:** real algorithm selection, constraints mirroring the backend,
   in-wizard guidance, pre-publish validation.

### Added after audit (this revision)
5. **Storage & lifecycle** made explicit, and **upgraded to a robust server-side model**:
   **Projects** and **Runs** persisted in **MongoDB** (the datastore already in the stack), not
   browser localStorage, with **download/upload** (§3).
6. **End-to-end user flow** mapped *bidirectionally* (not just create→publish).
7. **UI integration**: shared design language + unified shell/branding across both apps.

---

## 2. Current pipeline & the gaps

```
CURRENT
  wizard ──ZIP──▶ (manual unzip + API RESTART) ──▶ data/problems/ ──startup scan──▶ Mongo
                                                                                     │
  frontend Problems     ──GET /api/problems────────────────────────────────────────┘
  frontend CreateCalendar ──POST /api/problems/{id}/solve──▶ RabbitMQ ──▶ scheduler ──▶ Mongo ──▶ view
```

| # | Gap | Evidence |
|---|---|---|
| 1 | **No runtime publish** | `ProblemsController` has only `GET /problems[...]` + `POST /{id}/solve`; new problems need a file drop + API restart. |
| 2 | **Generic algorithm info** | Wizard `optimization.algorithm` defaults to `"ILP"` (matches no solver); real PROBLEM-mode set is `ILP/CSP General` (SHIFT) + `ILP/CSP_Sisqual_Hours` (HOURS). |
| 3 | **No cross-app link** | `frontend` and `json-generator` never reference each other. |
| 4 | **Missing display metadata** | Wizard `buildMetadata` emits `problemId/createdAt/description/source` but **no `metadata.name`**, yet `Problems.jsx`/`ProblemService` show `metadata.name` → published problems would list as a bare id. |
| 5 | **One-way data only** | Generators are `state → json` only; there is **no `problem.json → wizard state` importer**, and the API serves no CSV contents → a published problem can't be edited. |
| 6 | **Two disconnected storage tiers** | Drafts live in browser `localStorage` (`wizardState` + `wizardProjects`); published problems live server-side (files + Mongo). Nothing links them. |
| 7 | **Divergent UI** | Frontend has **no MUI theme** (`main.jsx` bare; empty Tailwind palette) and inconsistent CSS colors (mostly blue `#007bff`/`#1976d2`, teal `#0f766e` on the new Problems page). Wizard is a centralized MUI theme but **blue `#007bff`**, titled "JSON Generator - Schema v2.2", **no logo, no sidebar**. |

**Granularity fact driving the design:** the wizard's `jsonGenerator.buildDemand()` always emits
`demand.workPeriods` (never `demand.shifts`) → API maps `workPeriods → HOURS` → only
`ILP_Sisqual_Hours` / `CSP_Sisqual_Hours` apply. Algorithm UI must reflect this (filter on the actual
granularity so it stays correct if SHIFT output is added later).

**In our favour (no infra change needed):** nginx already routes `/json-gen/` + `/api/`;
`data/problems` is a shared bind mount across `api`+`scheduler`+`analyzer` (compose 56/91/148) so a
written problem is immediately visible to the solver; multipart is already enabled (compose 135–137).

---

## 3. Storage & data model (robust server-side)

The current storage is fragile: wizard projects live only in **browser localStorage** (per-browser,
unshareable, lost on cache clear), and a published problem's only DB footprint is a path pointer.
This plan moves to **durable, shareable, server-side persistence** for three first-class entities,
with **download/upload** preserved throughout.

### 3.1 Entities

| Entity | What it is | Where it lives | State today |
|---|---|---|---|
| **Project** | A wizard *definition* (the full wizard `state`) — the editable source of a problem | **DB** (`projects`), + export/import as JSON | localStorage only → **move to server** |
| **Problem** | The published, solver-consumable bundle (`problem.json` + CSVs) | **Files** (`data/problems/{id}/`) + **DB registry** (`problems`) | exists; registry enriched |
| **Run** | One algorithm *execution* against a problem (algorithm + params + status + result + KPIs) | **DB** (`runs`, linked to the existing schedule result) | implicit in `schedules` → **make first-class** |

A Project is the editable master; **publishing** a Project materializes a Problem bundle; **solving**
a Problem produces Runs. A Project can be published many times; a Problem can have many Runs (across
algorithms/params) — which is exactly the "different runs of different algorithms" goal.

### 3.2 Lifecycle

```
  PROJECT (DB, editable)            PROBLEM (files + DB registry)        RUN (DB) ── many per problem
  ─────────────────────            ────────────────────────────        ─────────────────────────────
  wizard state, status,    ─Publish─▶  problem.json + *.csv     ─Solve─▶  algo + params + status
  version, author, link      (POST     data/problems/{id}/        (one     → schedule result + KPIs
        ▲   │                /problems) + problems registry        Run per   ↘ compare across runs
        │   └──── edit = reload project (no reverse import needed for wizard-made problems)  algo)
        │
  Save-to-server / Load-from-server / Export(JSON) / Import(JSON or bundle ZIP)   ⇄  download/upload
```

Because a Project stores the wizard `state` verbatim, **editing a wizard-made problem is just
"load its Project"** — no `problem.json → state` reverse importer required. (A reverse importer is
only needed to edit *externally*-authored problems that have no Project; that's optional, §7 Phase 3.)

### 3.3 Data model — MongoDB collections

Each is a Spring Data Mongo `@Document` with a `MongoRepository` (mirroring the existing
`ProblemRepository` / `VacationTemplateRepository`), persisted to the current `mongo_data` volume —
no schema migrations, no new service.

- **`projects`**: `projectId`, `name`, `description`, `author`, `status` (`draft`|`published`),
  `wizardState` (the full definition), `publishedProblemId?`, `version` (+ optional `history[]`),
  `createdAt`, `updatedAt`, `tags?`.
- **`problems`** (enrich existing `ProblemDefinition`): keep `problemId`, `problemPath`; **add cached
  display fields** `name`, `description`, `source`, `granularity`, `createdAt`, `sourceProjectId?`
  (so the Problems list is fast/informative without re-parsing each file).
- **`runs`**: `runId` (= solve `taskId`), `problemId`, `projectId?`, `algorithm`, `params`
  (`maxTime`, `solver`, …), `status` (`queued`|`running`|`done`|`failed`), `requestedAt`,
  `completedAt`, `scheduleId`/result ref, `kpis`. Built on the data the existing solve flow already
  carries (`ScheduleRequest` + schedule metadata + task status) — mostly *linking + labeling*, not a
  new pipeline. Enables "Runs for this problem" + side-by-side comparison (extends `CompareCalendar`).

**Data-model alignments (independent of datastore):**
- **Add `metadata.name`** to the wizard (Step 1 + `buildMetadata`) — closes gap #4 (friendly names).
- **Keep `metadata.source="json-generator"`** so the app can badge "Created in wizard".
- **Link Project → published Problem → Runs** so each surface can navigate the lifecycle.

### 3.4 Datastore — extend MongoDB (decided)

**Decision: extend the existing MongoDB.** It delivers the robustness goals (durable, shareable
projects; first-class comparable runs; upload/download) with **no new infrastructure** and code that
mirrors patterns already in the repo. The document model fits the nested JSON of project state,
`problem.json`, and KPI blobs, and matches the API's schema-agnostic `Map<String,Object>` style.

**What this means concretely:**
- **No infra/compose change.** Reuse the Spring Data Mongo connection already configured via the
  `SPRING_DATA_MONGODB_*` env (compose 115–120); data persists to the existing `mongo_data` volume
  alongside today's `problems` / `schedules` / templates collections.
- **New collections + repositories** (mirroring `ProblemRepository`):
  - `projects` → `ProjectRepository extends MongoRepository<Project,String>`; `@Indexed(unique=true)`
    on `projectId`; `findByAuthor(...)`.
  - `runs` → `RunRepository extends MongoRepository<Run,String>`; `findByProblemId(...)` (+
    `findByProjectId`) for grouping/compare.
  - `problems` → enrich the existing `ProblemDefinition` doc with the cached display fields (§3.3).
- **New API layer**: `ProjectController/Service` + `RunController/Service`, following the existing
  `ProblemsController`/`ProblemService` structure. Aggregation handles "compare runs".
- **Querying for compare**: a Mongo aggregation/`find` over `runs` by `problemId` returns the set to
  diff; the frontend `CompareCalendar` renders it.

**Deferred (not now):** PostgreSQL / hybrid. If SQL/BI reporting across many runs ever becomes a
first-order requirement, add Postgres later as a **read-only analytics projection** fed from the
`runs` collection — without re-architecting Phase 1/2.

### 3.5 Download / upload (kept throughout)
- **Project:** Export as JSON (download) / Import JSON (upload) → server Project; "Save to server" /
  "Load from server". Extends the existing `ProjectManagerDialog` (which already does localStorage
  export/import) to the server.
- **Problem:** Export bundle ZIP (already in Step 10) / Import bundle ZIP or `problem.json` → creates
  a Problem (and optionally a Project).
- **Run:** Export a run's schedule/result (CSV/JSON) for sharing or offline analysis.

---

## 4. End-to-end user flow (bidirectional)

```
                     ┌─────────────────────── Main app (frontend, "/") ───────────────────────┐
                     │  Sidebar: Home · Schedule · Teams · Employees · Problems · ▶Generate    │
                     └───────────────┬───────────────────────────────────┬─────────────────────┘
                 "Generate Problem"  │                                    │  "Edit in wizard" (Phase 2)
                                     ▼                                    ▼
            ┌──────────────────── Wizard ("/json-gen/") ─────────────────────────────┐
            │ new draft / resume (localStorage)        hydrate from published bundle  │
            │ Step 1…9 build ▶ Step 10 Review ─ validateAll() gate ─ ▶ PUBLISH        │
            └───────────────────────────────────┬────────────────────────────────────┘
                                                 │ POST /api/problems (201) — no restart
                                                 ▼
            redirect ▶ /manager/problems?problemId=X  (preselected, ready)
                                                 │ "Use In Schedule"
                                                 ▼
            CreateCalendar (algorithms from GET /api/algorithms) ─ Solve ▶ schedule view
```

**Entry points into the wizard**
- **New problem:** frontend sidebar **"Generate Problem"** → `/json-gen/` (fresh, or resume the
  autosaved draft / a named project).
- **Edit existing (Phase 2):** Problems page **"Edit in wizard"** → `/json-gen/?problemId=X`; the
  wizard hydrates Tier-1 state from the Tier-2 bundle.

**Inside the wizard** → Steps 1–9, Step 10 validates (`validateAll`) and gates **Publish**.

**Publish** → `POST /api/problems` → on `201`, top-level redirect to
`/manager/problems?problemId=X`; on `409`, offer Overwrite.

**Return** → Problems preselects the new problem → **"Use In Schedule"** → CreateCalendar →
**Solve** → schedule view (existing flow).

**Lifecycle states:** `Draft → Published → Solved`, with `Published → (edit) → Draft' → Published'`.

**Navigation coherence:** the wizard must offer a way back into the app (shared sidebar or a
"← Back to Problems" affordance) so it never feels like a dead-end micro-app. (Note: `/manager/*` is
behind `ProtectedRoute`; an unauthenticated redirect lands on Login — existing behavior.)

---

## 5. UI integration & consistency

**Problem:** there is no shared design language. The frontend has **no MUI theme** and inconsistent
CSS (blue across most pages, teal on Problems); the wizard is themed but blue, with its own header
and no SmarTask branding. The goal is for the wizard to look and navigate like part of SmarTask, and
for the frontend's own MUI usage to stop drifting.

**Approach — establish one brand design language, applied to both apps:**

| Parity item | Today | Target |
|---|---|---|
| **Palette** | Wizard `#007bff`; frontend blue + teal mix, no theme | One brand palette (recommend the Problems-page **teal `#0f766e`** as the hand-off color), defined once and applied in both apps |
| **Theme mechanism** | Wizard: `theme.config.js` → MUI theme. Frontend: none | Frontend gains a small MUI `ThemeProvider` using the same tokens; wizard's `theme.config.js` updated to the brand palette |
| **App shell** | Wizard: `AppBar` "JSON Generator - Schema v2.2", no sidebar | Wizard adopts a SmarTask shell: same **logo** (`Logo.png`), app name (e.g. "SmarTask · Generate Problem"), and a **left sidebar matching `Sidebar_Manager`** with links back to Home/Problems/Schedules and "Generate" active |
| **Components** | Both use MUI (buttons/cards/chips/dialogs) | Aligned automatically once both share the theme (radius, button casing, elevations already defined in `componentOverrides`) |
| **Terminology** | "JSON Generator", "Generate Files" | Consistent product language: **Problem, Generate, Publish, Solve, Schedule** |
| **Branding** | No logo, schema version in title | SmarTask logo + name; drop the schema version from the title (keep it in a subtle status area) |

**Sharing tokens without a workspace:** the monorepo is not an npm workspace, so the pragmatic path
is a single small **design-tokens file duplicated in both apps** (the wizard's `theme.config.js`
structure is a good canonical shape) plus `:root` CSS variables for the frontend's legacy CSS — one
documented source of truth, copied. (A shared package via a workspace is the heavier alternative,
noted but not required.)

**Brand-color decision:** teal `#0f766e` (matches the Problems page the wizard hands off to) vs the
existing blue `#007bff`. Default to teal for a seamless hand-off; it's a one-file change in the
wizard and a token change in the frontend, so it's cheap to flip.

> Scope guard: this does **not** mean re-skinning every frontend page. The contained work is (a) one
> shared palette/theme applied via a frontend `ThemeProvider`, and (b) the wizard adopting the
> SmarTask shell + palette. Legacy per-page CSS can converge opportunistically later.

---

## 6. Workstreams

### A — API (Java): publish, algorithms, projects, runs
- **A1 `POST /api/problems` (multipart):** save `problem.json` + CSVs to `data/problems/{id}/`
  (reuse `resolveRepoRoot()`), register in Mongo by refactoring the per-file body of
  `buildProblemDefinitionsFromFiles()` (ProblemService.java:326–341) into a reusable
  `fromProblemFile(Path)` + existing `save()`. `409` on duplicate id unless `overwrite=true`. `201`
  with `{ problemId, problemPath }`. Files: `ProblemsController.java`, `ProblemService.java`.
- **A2 `GET /api/algorithms`:** expose `SchedulingAlgorithmRegistry` (`name/uiMode/granularity/
  inputKind` + friendly `label/description`), with `?uiMode`/`?granularity` filters. Files:
  new `AlgorithmsController.java`, registry accessor.
- **A3 Display-metadata enrichment:** cache `name/description/source/granularity/createdAt/
  sourceProjectId` on `ProblemDefinition` at publish for a fast, informative Problems list.
- **A5 Projects API (Phase 2 — storage):** new `ProjectController/Service` + Mongo `projects`
  collection with `ProjectRepository extends MongoRepository<Project,String>` (`@Indexed(unique)`
  `projectId`). CRUD (`POST/GET/GET{id}/PUT/DELETE /projects`) storing the wizard `state`; import
  (upload JSON/bundle) + export (download JSON). Reuses the existing Mongo config — no infra change.
- **A6 Runs API (Phase 2 — storage):** make runs first-class — on solve, persist/label a `run` in a
  new Mongo `runs` collection (`RunRepository.findByProblemId`): `runId`=taskId, `problemId`,
  `projectId?`, `algorithm`, `params`, `status`, result ref, `kpis`. Endpoints
  `GET /problems/{id}/runs`, `GET /runs/{id}`, + compare (or feed `CompareCalendar`). Reuses existing
  `ScheduleRequest`/schedule metadata/task status — mostly linking + labeling.
- **A4 Bundle file reads (Phase 3, optional):** `GET /problems/{id}/files/{name}` to serve CSV
  contents — only needed to edit *externally*-authored problems (those without a Project).

### B — json-generator (React): publish, algorithms, constraints, guidance, validation, metadata, import
- **B1 Publish action:** Step10 **Publish** button (validity-gated) + new `utils/api/publishProblem.js`
  (axios multipart to `/api`); on `201` redirect to `/manager/problems?problemId=…`; handle `409`.
- **B2 Real algorithm selection:** `AlgorithmSelector` fetches `GET /api/algorithms` filtered by
  granularity (HOURS); store a real id in `optimization.algorithm`; fix `buildOptimization` default.
- **B3 Constraints mirror backend:** align `constraintMetadata.js` to `general/constraints.py` +
  `sisqual_hours_utils.py` + `config/rules.json` — fix `max_special_days` params (`tag/cap`), add
  `team_eligibility` / `fixed_days_off_per_week|month` / `ideal_coverage`, badge/hide unsupported
  ones (`balance_workload`, `prefer_experienced`, …). Update the `initialState.constraints` defaults
  in `WizardContext.jsx` to match.
- **B4 Guidance:** algorithm descriptions (from A2 labels) + math-model summary + granularity hint.
- **B5 Pre-publish validation:** reuse existing `validateAll` + `ValidationPanel` to gate Publish.
- **B6 Add `metadata.name`:** Step 1 field + `buildMetadata` (storage alignment, gap #4).
- **B8 Server projects + upload/download (Phase 2):** extend `ProjectManagerDialog` to talk to the
  Projects API (A5) — Save-to-server, Load-from-server, list/delete, plus Export (download JSON) and
  Import (upload JSON/bundle). Keep localStorage autosave as an offline draft cache that syncs on
  save. Editing a wizard-made problem = Load-from-server (no reverse import).
- **B7 Import externally-authored problem (Phase 3, optional):** `problem.json (+CSVs) → state`
  hydrator reusing `demandCsvParser` / `scheduleInputCsvParser`; for problems with no Project.

### C — frontend (React): nav bridge, return flow, de-dupe algorithms, edit entry
- **C1** Sidebar **"Generate Problem"** link → `/json-gen/` (`Sidebar_Manager.jsx`).
- **C2** `Problems.jsx` reads `?problemId=` (via `useSearchParams`) and preselects it.
- **C3** `CreateCalendar.jsx` consumes `GET /api/algorithms` (drop the four hardcoded arrays at
  lines 269–300; keep the mode + granularity filter).
- **C4 (Phase 2)** `Problems.jsx` **"Edit in wizard"** → `/json-gen/?projectId=…` (load the source
  Project; falls back to `?problemId=` + reverse import for external problems).
- **C5 Runs view + compare (Phase 2)** `Problems.jsx`: "Runs for this problem" list (from A6) with a
  compare-across-algorithms action, extending the existing `CompareCalendar`.

### D — infra & docs
- **No compose/nginx edits required** — state explicitly. Verify the wizard reaches `/api` via nginx.
- Add an end-to-end flow doc; update `src/json-generator/README.md` + root `README.md`; note
  `GET /api/algorithms` as the single source of truth.

### E — UI integration (see §5)
- **E1** Define one brand palette + tokens; update wizard `theme.config.js`.
- **E2** Add an MUI `ThemeProvider` to the frontend (`main.jsx`/`App.jsx`) using the same tokens.
- **E3** Wizard SmarTask shell: logo + product name + a sidebar matching `Sidebar_Manager` (links
  back to the app; "Generate" active); replace the "JSON Generator - Schema v2.2" AppBar.
- **E4** Terminology pass (Problem / Generate / Publish / Solve / Schedule) across both surfaces.

---

## 7. Phasing

- **Phase 1 — the loop + cohesion:** A1, A2, A3, B1–B6, C1–C3, D, E1–E4.
  Outcome: generate → **publish (no restart)** → land in Problems → solve, in a unified UI with
  correct algorithms/constraints and friendly names. Uses today's filesystem + Mongo registry.
- **Phase 2 — storage robustness (MongoDB):** A5 (Projects), A6 (Runs),
  B8 (server projects + upload/download), C4 (edit via Project), C5 (Runs + compare).
  Outcome: durable, shareable server-side projects; first-class runs of different algorithms,
  grouped per problem and comparable; download/upload everywhere; editing = reload a Project.
- **Phase 3 — optional:** A4 + B7 (reverse import for *externally*-authored problems); SQL analytics
  projection if Postgres/hybrid is chosen in §3.4.

## 8. Key reuse (don't re-implement)
- `ProblemService.buildProblemDefinitionsFromFiles()` / `save()` / `resolveRepoRoot()` — A1/A3.
- `SchedulingAlgorithmRegistry` — A2.
- Existing Mongo repository pattern (`ProblemRepository`, `VacationTemplateRepository`) + the
  `SPRING_DATA_MONGODB_*` config — template/connection for the new `ProjectRepository` /
  `RunRepository` (A5/A6).
- Existing `schedules` docs + `ScheduleRequest` metadata + task status + `CompareCalendar` — A6/C5
  (Runs are mostly linking/labeling + a compare view, not a new pipeline).
- Wizard `ProjectManagerDialog` (localStorage save/load/export/import) — B8 (extend to server).
- Wizard `validateAll` + `ValidationPanel` + Step10 `generatedFiles` — B1/B5; `demandCsvParser` /
  `scheduleInputCsvParser` — B7.
- Wizard `theme.config.js` / `componentOverrides` — E1/E2 (canonical token shape).
- Frontend `Sidebar_Manager.jsx` + `Logo.png` — E3 (shell parity); `Problems.jsx` selection +
  "Use In Schedule" — C2.

## 9. Risks & decisions
| Topic | Decision / note |
|---|---|
| **Datastore (§3.4)** | **Decided: extend MongoDB** — no new infra, fits the document data, repo-consistent. Postgres can be added later as a read-only analytics projection if SQL/BI is required. |
| Project ownership / multi-user | Server projects imply an owner; current auth is hardcoded admin/manager. Phase 2 attributes by `author` string; a real user model is a later concern. |
| Duplicate `problemId` | Default `409` + explicit Overwrite (protects curated problems). |
| Brand color | Teal `#0f766e` (hand-off match) vs blue `#007bff`; default teal, cheap to flip. |
| Drafts vs server | localStorage stays an offline draft cache; "Save to server" / Publish make work shareable (Phase 2). |
| Runs vs schedules | Runs reuse existing schedule data + task status (linking/labeling), not a new solve pipeline. |
| External edit cost | Reverse import + CSV-serving only matter for problems without a Project → isolated in Phase 3. |
| Auth boundary | `/manager/*` behind `ProtectedRoute`; unauthenticated redirect → Login (existing). |
| Granularity | Wizard output is HOURS → only the two Sisqual algorithms; SHIFT output is a future extension. |
| Constraint honesty | Several wizard constraints aren't enforced by any solver — B3 makes the catalog truthful. |

## 10. Verification (end-to-end, once implemented)
1. `make build`; all services healthy.
2. `curl -s localhost/api/algorithms | jq` → registry; `?uiMode=PROBLEM&granularity=HOURS` → 2 Sisqual algos.
3. Open `localhost/json-gen`: UI shows SmarTask branding/sidebar/palette matching the main app.
4. Build a small valid HOURS problem (with a **name**); validation passes; **Publish** → `201`.
5. `curl -s localhost/api/problems | jq` shows the new id **with its name**, no API restart; files on disk.
6. Redirected to `/manager/problems?problemId=…`, preselected → **Use In Schedule** → algorithms
   from `/api/algorithms` → solve with `ILP_Sisqual_Hours` → view schedule.
7. Re-publish same id → `409` + Overwrite works.
8. **(Phase 2)** Problems → **Edit in wizard** → state hydrates from the bundle → change → re-publish.
9. `cd src/api && mvn -q -DskipTests package`; `npm run lint` in both React apps (CI parity).

## 11. Implementation checklist
**Phase 1**
- [ ] A1 `POST /api/problems` (+ `fromProblemFile` refactor, 409/overwrite)
- [ ] A2 `GET /api/algorithms` (+ labels) · [ ] A3 enrich `ProblemDefinition`
- [ ] B1 Publish + redirect/409 · [ ] B2 algorithm selection · [ ] B3 constraints align (+ `initialState`)
- [ ] B4 guidance · [ ] B5 gate on `validateAll` · [ ] B6 `metadata.name` (Step 1 + `buildMetadata`)
- [ ] C1 sidebar link · [ ] C2 `?problemId=` preselect · [ ] C3 `CreateCalendar` consumes `/api/algorithms`
- [ ] D docs/no-infra-change · [ ] E1 palette/tokens · [ ] E2 frontend `ThemeProvider` · [ ] E3 wizard shell · [ ] E4 terminology
**Phase 2 (storage robustness — MongoDB)**
- [ ] A5 Projects API (Mongo `projects` + CRUD + import/export) · [ ] A6 Runs API (Mongo `runs` + link/list/compare)
- [ ] B8 server projects + upload/download in `ProjectManagerDialog`
- [ ] C4 "Edit in wizard" via Project · [ ] C5 Runs list + compare
**Phase 3 (optional)**
- [ ] A4 bundle file reads · [ ] B7 external problem→state importer · [ ] SQL analytics (if Postgres/hybrid)

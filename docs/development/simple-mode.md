# Frontend simple mode (`VITE_SIMPLE_MODE`)

## What it is

`VITE_SIMPLE_MODE` is a Vite build/dev-server environment variable that
simplifies the "Generate Schedule" page (`src/frontend/src/Manager/CreateCalendar.jsx`)
for production use. It is read once at startup:

```js
const SIMPLE_MODE = import.meta.env.VITE_SIMPLE_MODE === "true";
```

## What changes when it's `"true"`

- **Manual scheduling mode is hidden entirely.** The Mode selector
  (Problem / Manual) doesn't render, and the page always behaves as if
  Problem mode were selected — every algorithm, template, and field that
  only applies to Manual mode (vacation templates, minimum templates,
  shift/hour counts, group selection, the legacy ILP/CSP/COP/Heuristic
  algorithm lists) becomes unreachable.
- **The Problem-mode algorithm picker is restricted to the two Mathematical
  Formulation (MD7) solvers**: `ILP_Sisqual_Hours_MathematicalDefinition7`
  and `CSP_Sisqual_Hours_MathematicalDefinition7`. The older
  `ILP_Sisqual_Hours` / `CSP_Sisqual_Hours` (non-MD7) options are hidden.
- **Shift-type problems are not solvable in this mode.** There is no
  shift-based Mathematical Formulation solver — `ILP General` / `CSP General`
  only exist as non-MD7 algorithms — so the shift-algorithm dropdown returns
  empty. Simple mode is scoped to hour-type Sisqual problems only.

When unset or `"false"` (the default), the page behaves exactly as before:
both Manual and Problem modes are available, and Problem mode's hour
algorithm picker offers all four Sisqual algorithms.

## Why

Production users should only be choosing between the two well-tested
Mathematical Formulation (MD7) solvers, driven entirely by `problem.json`
bundles — not the older experimental algorithms or the legacy
manually-configured scheduling flow, which stay available for development
and comparison work.

## How to set it

Copy `src/frontend/.env.example` to `.env` (or `.env.production`) inside
`src/frontend/`, and set:

```
VITE_SIMPLE_MODE=true
```

Vite only reads this at server start (`npm run dev`) or at build time
(`npm run build`) — restart the dev server / rebuild after changing it.

Local development should leave this unset (or `false`) to keep the full
algorithm list and Manual mode available.

## Where the logic lives

All of the branching is in `src/frontend/src/Manager/CreateCalendar.jsx`:
- `SIMPLE_MODE` constant, defined at module scope (top of the file).
- `initialMode` forces `"problem"` when `SIMPLE_MODE` is true.
- `problemShiftAlgorithms` / `problemHourAlgorithms` are filtered when
  `SIMPLE_MODE` is true.
- The Mode `<Select>` is wrapped in `{!SIMPLE_MODE && (...)}`.

No backend changes are involved — this only hides options in the UI. All
algorithms remain fully implemented and reachable via the API directly
(e.g. `POST /schedules/generate` with any algorithm name), so this is a UI
convenience, not an access-control mechanism.

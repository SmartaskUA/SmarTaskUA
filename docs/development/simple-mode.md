# Frontend simple mode (`VITE_SIMPLE_MODE`)

A Vite environment variable that trims the **Generate Schedule** page
(`src/frontend/src/Manager/CreateCalendar.jsx`) for production users.

## What `VITE_SIMPLE_MODE=true` changes

- **Manual mode is hidden.** The page always works in Problem mode, so templates, shift/hour counts and the
  legacy algorithm lists are unreachable.
- **Only the two Mathematical Formulation solvers are offered:** `ILP_Sisqual_Hours_MathematicalDefinition7`
  and `CSP_Sisqual_Hours_MathematicalDefinition7`, for schema v4 problems.
- **Legacy v2.x problems (shift or hourly) get no algorithm** in simple mode.

When unset or `false` (the default), both modes are available. A v4 problem then offers every v4 solver the
API lists for it; a v2.x problem offers its legacy solvers.

## Setting it

In `src/frontend/`, copy `.env.example` to `.env` (or `.env.production`) and set `VITE_SIMPLE_MODE=true`.
Vite reads it only at start-up or build time, so restart `npm run dev` or rebuild after changing it.
Leave it unset for local development.

## Where it lives

In `CreateCalendar.jsx`:
- the `SIMPLE_MODE` constant;
- the filter in `problemAlgorithmsFor` and the empty legacy lists;
- the Mode `<Select>`, wrapped in `{!SIMPLE_MODE && …}`.

It only hides options in the UI. Every algorithm stays reachable through the API, so it is not access control.

# upload_and_solve.py

Sends a problem to the SmarTask API, solves it with one algorithm, and saves the
schedule as the JSON that WFM imports.

## Before you start

- The SmarTask services are running (`make build`, or `make up` if already built),
  and the API answers at `http://localhost/api`. If it runs on another machine,
  change `API_BASE` near the end of the script.
- Python 3 with the script's one dependency:
  `pip install -r scripts/upload_and_solve_requirements.txt`.
- Run the script from the repository root: it writes to `exports/` there.

## The input: a ZIP of a schema v4 package

A flat ZIP, with no folder inside, holding the package's `problem.json` and every
CSV it names, for example:

```
problem.json
schedule_input.csv
periods_demand.csv
days_demand.csv
shifts_demand.csv
schedules.csv
```

`metadata.problemId` in `problem.json` names the problem in the API: letters,
digits, `_`, `.` and `-`, at most 64 characters. Uploading the same `problemId`
again replaces the earlier upload.

If the `problemId` is one the API already has built in (a folder in
`data/problems`, such as `V4_C2_January_2026`), the upload is refused and the
script solves the built-in copy instead, provided its `problem.json` is identical
to the one in the ZIP. If they differ, give the package another `problemId`.

## Running it

```bash
python scripts/upload_and_solve.py --zip path/to/package.zip
python scripts/upload_and_solve.py "Genetic Algorithm v4" --zip path/to/package.zip
```

| argument | meaning |
|---|---|
| `--zip` | the package ZIP |
| algorithm (optional) | which algorithm to run; by default the first the API lists, `ILP_Sisqual_Hours_MathematicalDefinition7` |

Algorithms the API offers for a v4 package:

- `ILP_Sisqual_Hours_MathematicalDefinition7`
- `CSP_Sisqual_Hours_MathematicalDefinition7`
- `Hybrid_Heuristic_Sisqual_Levels_Included`
- `Hybrid_Heuristic_Sisqual_3`
- `Genetic Algorithm v4`

Names with spaces go in quotes.

## What it does

1. Uploads the ZIP (`POST /api/problems/upload`).
2. Starts the algorithm (`POST /api/problems/{problemId}/solve`).
3. Checks the task every 5 seconds until it finishes, for at most 100 minutes.
4. Saves the WFM import JSON to `exports/<schedule title>.json`.

The schedule also appears in the web app (`http://localhost`, *Schedule*), with
its KPIs. *Download Sisqual JSON* there gives the same JSON as step 4, under the
schedule's id instead of its title.

## The output

One `OutRosterTeamDays` entry per employee per day, in the import format of
November 2026: worked days with `ScheduleStartDate`/`ScheduleEndDate`, days off
with `ScheduleCode`, a `TeamCode` on every day, the responsibilities covered in
`OutRosterTeamDayResponsibilities`, and no `OutScheduleUseds`.

```json
{
  "RosterCode": "C2",
  "TeamCode": "T1",
  "EmployeeCode": "20072412",
  "Date": "2026-01-02",
  "ScheduleStartDate": "2026-01-02T08:30:00",
  "ScheduleEndDate": "2026-01-02T12:30:00",
  "OutRosterTeamDayTasks": [],
  "OutRosterTeamDayResponsibilities": [{"ResponsibilityCode": "A"}]
}
```

## When it fails

| message | cause |
|---|---|
| `Upload failed (400): ...` | the ZIP is not a valid package; the message lists what is missing |
| `... differs from the built-in problem ...` | the `problemId` is built in with other contents; change `problemId` |
| `'X' cannot solve this problem` | the algorithm name is wrong; the message lists the valid ones |
| `Python worker reported FAILED...` | the algorithm could not solve it; see `make logs-scheduler` |
| `Polling timed out` | still running after 100 minutes; it keeps going, and the result appears in the web app |

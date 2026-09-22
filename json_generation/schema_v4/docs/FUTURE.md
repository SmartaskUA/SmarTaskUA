# Future work

What v4.0 deliberately does not carry, and what each item needs before it can.

The rule this list is governed by, inherited from v3.0: **nothing enters the schema
until a consumer reads it.** A field that is stored and ignored is worse than a
missing one — it looks authoritative, it gets filled in, and then it silently fails
to matter. Every item below therefore names the consumer it is waiting on.

Items 1 and 2 are the ones currently blocking real work.

---

## 1. Contracts with their own constraints

**The problem.** `workMinutesPerDay` is the only field v4.0 carries about a contract,
and it is not enough to identify one. In `examples/cenario2_retail/`, two pairs of
contracts collapse onto byte-identical schema objects:

| everything the schema carries | contracts sharing it |
|---|---|
| `{"workMinutesPerDay": 300}` | `PT_10` — 10h/week over **2 days** · `PT_25` — 25h/week over **5 days** |
| `{"workMinutesPerDay": 240}` | `PT_12` — 12h/week over **3 days** · `PT_20` — 20h/week over **5 days** |

A reader given only the JSON cannot tell a 10-hour contract from a 25-hour one. The
weekly obligation survives in exactly one place — the pre-filled day-off pattern in
`schedule_input.csv` — and that is *input data*, not a constraint. It happens to be
correct in the bundles Sisqual sent (every employee's weekly total does match their
contract name), but nothing requires it to be, and nothing would catch it if it were
not. A solver asked to *choose* the days off, rather than copy them, could not
honour the contract at all.

**What it needs.** A `constraints` object on each contract definition:

- `targetMinutesPerWeek` — what the generator aims to hit (Sisqual's `TotalWeeklyMinutes`)
- `maxMinutesPerWeek` — the cap, which is not always the same number
- `minWorkDaysPerWeek` / `maxWorkDaysPerWeek` (Sisqual's `TotalWeeklyWorkDays`) — the
  field that actually separates `PT_10` from `PT_25`
- `availableDays`, `minRestDaysPerWeek`, `maxConsecutiveDays`
- `totalMonthlyMinutes`, `totalYearMinutes` — Sisqual carries both
- per-weekday and per-holiday-type lengths (`WeightMonday`…`WeightSunday`,
  `WeightHolidayBusinessDay/Saturday/Sunday`) — our one `workMinutesPerDay` assumes
  every working day is the same length, which their model does not

**Where it stands.** v3.0 had exactly this block and v4.0 dropped it, because
Sisqual's exporter emits none of it — `InpContractCollection` defines all sixteen
fields and the export carries only `TotalDailyMinutes`. So this is blocked on *them*
first (agenda item 23) and on a v4 solver second. Today the validator reads
`MaxConsecutiveWorkDays` and `MaxConsecutiveWorkDaysInWeek` from the roster-wide
`constraints.hard[]`, which is the closest thing that exists and is not per-contract.

## 2. Break logic, and the with-meal catalogue

The `ScheduleCode` catalogue we hold is `Schedules_Without_meal.xlsx`, and its name
is load-bearing. Its dense, usable band is **180–360 minutes** (3–6 hours) in
15-minute steps, roughly 96 codes per duration. Above six hours there are only 19
one-off codes, mostly overnight or full-day blocks. Concretely:

- **420 minutes: zero codes.** A `PT_35` employee has no legal shift at all.
- **480 minutes: three codes**, of which only `1014` (08:00–16:00) suits a retail day.

Six hours is the Portuguese meal-break threshold, so this is not a gap in the file —
it is the file's boundary. Everything longer lives in a with-meal catalogue we have
never been sent (agenda item 5), and a shift with a break is two intervals plus an
unpaid gap, which v4.0 has no way to express: `scheduleWeightMinutes` is a single
number and paid time always equals clock time.

**What it needs:** the with-meal catalogue, and then a break model — most likely
`intervals[]` on a catalogue row rather than one `startMin`/`endMin` pair, with paid
minutes stated separately from the span.

## 3. The demand triple's semantics

`minimum`, `ideal`, `estimated` have no established ordering, because Sisqual writes
`0` into two of the three in every row of every bundle. v4.0 therefore enforces only
non-negativity — see `FORMAT.md` and agenda item 1. Until it is answered, no solver
can read anything but `minimum`, and no validator can catch a file where the two
upper columns were swapped.

## 4. Workload demand

`days_demand.csv` states minutes of work to be covered rather than a head count.
Nothing consumes it: the validator checks its grid alignment and stops there, and
every bundle so far ships it header-only. It becomes real when a solver can convert
a workload target into coverage, which is a genuinely different objective from
`alpha_dts`.

## 5. Tasks and responsibilities

`OutRosterTeamDayTasks` and `OutRosterTeamDayResponsibilities` are `[]` in every
sample we have. Sisqual models both properly — `InpTaskAbilityCollection`,
`InResponsabilityCollection` — as a second and third assignment axis inside a shift.
v4.0 carries the arrays in the result schema so a round-trip does not lose them, and
reads nothing from them. Whether intra-shift allocation is ours to do at all is
agenda item 25.

## 6. A solve-directives registry

`priorityHierarchy` is a nine-field projection of `InpGenerationRules`, which has
around forty. The rest — `AlgorithmStep`, `FindScheduleType`, `FollowLevelByLevel`,
the `Responsability*` waste/override/cover settings, the per-weekday `GenerateOn*`
flags — is *how to solve*, not *what to solve*, and v4.0 is the problem definition
only. When a v4 solver exists these belong in one explicit registry it reads, rather
than scattered through the problem.

The same applies to the things v4.0 currently leaves unsaid on purpose: which demand
bound is hard, what a soft day-off costs, and whether a pinned shift may ignore the
demand window.

## 7. An expanded form, and a v4 solver

v3.0 had three forms — declarative, expanded, solution — and a deterministic
transformer between the first two. v4.0 has two, because the middle one has nothing
to compile into: Sisqual picks shifts from a catalogue rather than having them
synthesised, so the set of assignments a worker may take is the catalogue filtered
by their contract, not a construction.

If a v4 solver is built, the expanded form returns as the natural seam — an ingested
menu, `ScheduleCode` as the catalogue id, and `forced` for a pinned day — and with
it `transform.py` and `merge.py` and warm-start seeding. None of that is worth
building before something reads it.

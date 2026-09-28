/**
 * Cross-checks for the result form.
 *
 * A port of json_generation/schema_v4/src/schema_v4/validate_result.py: same
 * checks, same order, same wording. A result does not restate the problem, it
 * references it - by RosterCode, EmployeeCode, Date and ScheduleCode - so these
 * checks need the problem and its files.
 *
 * A result may be **partial**. The entries it carries are fixed days - each is
 * held to its schedule_input cell and to the labour law as a hard rule - and a
 * day it leaves out is open for the solver. Nothing marks a result as partial and
 * nothing complains about a missing day; the stats say how much is left.
 *
 * A result ships a sidecar, `<stem>_schedules.csv`, defining the codes it used.
 * Every finding belongs to the wizard's Fixed days step.
 */

import * as core from './core';
import { WEEKDAYS } from './constants';
import { resultSchemaFindings } from './schema';
import { fileText, Report, reportGrouped } from './validate';

const { pyRepr, iso } = core;
const STEP = 'fixedDays';

/**
 * Rest codes assumed when no catalogue is in reach. With one, a sentinel is
 * recognised from the data instead. The descriptions never reach a message.
 */
export const FALLBACK_SENTINELS = { 1: 'Space', 3: 'Day off', 4: 'Empty' };

export const { SIDECAR_SUFFIX, sidecarName } = core;

const byNumber = (a, b) => a - b;

class ResultValidator {
  constructor(result, { problem, files = {}, resultName = 'result.json', problemName }) {
    this.result = result || {};
    this.problem = problem || null;
    this.files = files;
    this.name = core.sidecarName(resultName);
    this.problemName = problemName;
    this.report = new Report();
    this.grouped = [];
  }

  error(message) { this.report.error(message, STEP); }

  warn(message) { this.report.warn(message, STEP); }

  run() {
    const r = this.report;
    r.stats.form = 'result';
    for (const f of resultSchemaFindings(this.result)) this.error(f.message);

    const entries = Array.isArray(this.result.OutRosterTeamDays) ? this.result.OutRosterTeamDays : [];
    r.stats.rosterDays = entries.length;

    const sidecar = this.loadSidecar();
    const usedCodes = new Set(entries.map((e) => e?.ScheduleCode));

    const problem = this.problem;
    if (!problem) {
      this.warn('no input problem found beside this result (and no --against), so the ' +
        'cross-checks were skipped: only the schema layer ran');
      this.checkSidecar(sidecar, usedCodes, new Map());
      return r;
    }
    if (this.problemName) r.stats.crossCheckedAgainst = this.problemName;

    const roster = problem.metadata?.rosterCode;
    const days = core.horizon(problem);
    const span = new Set(days);
    const employees = new Map((problem.employees?.list || []).map((e) => [String(e?.id), e]));
    const contracts = core.contractsById(problem);
    const menu = this.loadMenu(problem);
    const cells = this.loadCells(problem);

    // A code's definition comes from the sidecar when there is one - it is what
    // the producer says it used - and from the problem's menu otherwise.
    const defined = sidecar !== null ? sidecar : menu;

    const seen = new Map();
    const fixed = new Map();
    let intCodes = 0;

    entries.forEach((e, index) => {
      const where = `OutRosterTeamDays[${index}]`;
      const empRaw = e?.EmployeeCode;
      if (Number.isInteger(empRaw)) intCodes += 1;
      const eid = empRaw === null || empRaw === undefined ? 'None' : String(empRaw);

      if (roster && e?.RosterCode !== roster) {
        this.error(`${where}: RosterCode ${pyRepr(e?.RosterCode)} does not match the ` +
          `problem's metadata.rosterCode ${pyRepr(roster)}`);
      }
      if (!employees.has(eid)) this.error(`${where}: EmployeeCode ${eid} is not in employees.list`);

      const day = iso(e?.Date ?? '');
      if (!day) {
        this.error(`${where}: Date ${pyRepr(e?.Date)} is not a date`);
        return;
      }
      if (span.size && !span.has(day)) this.error(`${where}: Date ${day} lies outside temporalScope`);

      const key = `${eid}\u001f${day}`;
      seen.set(key, (seen.get(key) || 0) + 1);
      if (seen.get(key) === 2) {
        this.error(`${where}: ${eid} already has an entry for ${day}`);
        return;
      }

      const code = e?.ScheduleCode;
      if (!Number.isInteger(code)) return;
      if (menu.size && !menu.has(code)) {
        this.grouped.push([`missing:${code}`, `${where}: ScheduleCode ${code} is not in the schedules catalogue`]);
        return;
      }
      const schedule = resolve(code, defined);
      if (employees.has(eid) && (!span.size || span.has(day))) {
        if (!fixed.has(eid)) fixed.set(eid, new Map());
        fixed.get(eid).set(day, schedule);
      }
      this.checkCell(where, code, schedule, employees.get(eid), eid, day, contracts, cells, problem);
    });

    reportGrouped((m) => this.error(m), this.grouped);
    this.checkFixedLaw(fixed, days, problem);

    let filled = 0;
    for (const key of seen.keys()) {
      const [eid, d] = key.split('\u001f');
      if (employees.has(eid) && (!span.size || span.has(d))) filled += 1;
    }
    const expected = employees.size * days.length;
    r.stats.rosterDaysExpected = expected;
    r.stats.rosterDaysLeft = Math.max(0, expected - filled);

    if (intCodes) {
      this.warn(`EmployeeCode is an integer in ${intCodes} of ${entries.length} entries, but a ` +
        'string in the problem. JSON-Import.docx says string - see next_meeting.md item 13 ' +
        "('EmployeeCode is an integer').");
    }
    this.checkSidecar(sidecar, usedCodes, menu);
    this.checkScheduleUseds(defined);
    return r;
  }

  // -- the sidecar ----------------------------------------------------------

  loadSidecar() {
    const text = fileText(this.files, this.name);
    if (text === null) return null;
    const { catalogue, problems } = core.readSchedules(text);
    for (const msg of problems) this.error(`${this.name}: ${msg}`);
    this.report.stats.sidecarCodes = catalogue.size;
    return catalogue;
  }

  checkSidecar(sidecar, used, menu) {
    const name = this.name;
    if (sidecar === null) {
      this.warn(`no ${name} beside this result, so its ScheduleCodes carry no definition. A ` +
        'result should ship the codes it used - see docs/FORMAT.md.');
      return;
    }
    for (const code of [...used].filter((c) => Number.isInteger(c) && !sidecar.has(c)).sort(byNumber)) {
      this.error(`${name}: ScheduleCode ${code} is used by the result but not defined here`);
    }
    for (const code of [...sidecar.keys()].filter((c) => !used.has(c)).sort(byNumber)) {
      this.warn(`${name}: defines ScheduleCode ${code}, which the result never uses (the sidecar is ` +
        'the used set, not a copy of the menu)');
    }
    if (!menu.size) return;
    for (const [code, entry] of [...sidecar.entries()].sort((a, b) => a[0] - b[0])) {
      const other = menu.get(code);
      if (!other) {
        this.error(`${name}: ScheduleCode ${code} is not in the problem's catalogue - a result may ` +
          'only use shifts the problem offers');
      } else if (entry.description !== other.description || entry.weightMinutes !== other.weightMinutes ||
        !sameInterval(entry.interval, other.interval)) {
        this.error(`${name}: ScheduleCode ${code} is defined as ${pyRepr(entry.description)}/` +
          `${entry.weightMinutes}min here but ${pyRepr(other.description)}/${other.weightMinutes}min ` +
          "in the problem's catalogue");
      }
    }
  }

  // -- per entry: the fixed day against its cell ----------------------------

  checkCell(where, code, schedule, emp, eid, day, contracts, cells, problem) {
    const raw = cells.get(eid)?.[day];
    if (!emp || raw === undefined) return;
    const { rule } = core.tryClassifyCell(raw, problem);
    if (!rule) return;      // a malformed cell is the problem's finding, not this result's
    const cid = core.activeContract(emp, day);
    const wanted = contracts.get(cid)?.workMinutesPerDay ?? null;
    const reason = core.cellConflict(rule, schedule, wanted);
    if (reason) {
      this.grouped.push([`cell:${reason}`,
        `${where}: ScheduleCode ${code} for ${eid} on ${day} contradicts the cell ${pyRepr(raw)}: ${reason}`]);
    }
  }

  // -- the fixed days against the labour law --------------------------------

  /**
   * The roster-wide caps, over the days the result fixes. A day left open breaks
   * a run, because the solver may yet rest it: only what is already decided can
   * be judged, so a finding here is a real violation.
   */
  checkFixedLaw(fixed, days, problem) {
    const limits = core.legislationLimits(problem);
    if (!Object.keys(limits).length || !days.length) return;
    let weekStart = String(problem.calendar?.weekStart ?? 'monday').toLowerCase();
    if (!WEEKDAYS.includes(weekStart)) weekStart = 'monday';
    const runCap = limits.MaxConsecutiveWorkDays;
    const weekCap = limits.MaxConsecutiveWorkDaysInWeek;
    const minRest = limits.MinDistanceBetweenShiftsInMinutes;
    const found = [];

    for (const eid of [...fixed.keys()].sort()) {
      const worked = new Map([...fixed.get(eid).entries()].filter(([, s]) => s === null || !s.isSentinel));

      if (runCap !== undefined) {
        let run = 0;
        for (const d of days) {
          run = worked.has(d) ? run + 1 : 0;
          if (run > runCap) {
            found.push(['MaxConsecutiveWorkDays', `${eid}: fixed to work ${run} days in a row ending ${d}, ` +
              `above MaxConsecutiveWorkDays of ${runCap}`]);
            break;
          }
        }
      }

      if (weekCap !== undefined) {
        const perWeek = new Map();
        for (const d of worked.keys()) {
          const wk = core.weekIndex(d, days[0], weekStart);
          perWeek.set(wk, (perWeek.get(wk) || 0) + 1);
        }
        for (const [wk, n] of [...perWeek.entries()].sort((a, b) => a[0] - b[0])) {
          if (n > weekCap) {
            found.push(['MaxConsecutiveWorkDaysInWeek', `${eid}, week ${wk}: ${n} fixed working days ` +
              `exceeds MaxConsecutiveWorkDaysInWeek of ${weekCap}`]);
          }
        }
      }

      if (minRest !== undefined) {
        for (const [d, before] of [...worked.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1))) {
          const after = worked.get(core.addDays(d, 1));
          if (!before || !after || !before.interval || !after.interval) continue;
          const rest = after.interval.start + core.MINUTES_PER_DAY - before.interval.end;
          if (rest < minRest) {
            found.push(['MinDistanceBetweenShiftsInMinutes', `${eid}: ${rest} min of rest between ` +
              `${core.intervalToString(before.interval)} on ${d} and ${core.intervalToString(after.interval)} ` +
              `the next day, below MinDistanceBetweenShiftsInMinutes of ${minRest}`]);
          }
        }
      }
    }
    reportGrouped((m) => this.error(m), found);
  }

  // -- loading the problem's own files ---------------------------------------

  /** The menu the problem offers. An unreadable menu is said out loud, not silently empty. */
  loadMenu(problem) {
    const name = problem.schedules?.dataFile;
    if (!name) {
      this.warn("the problem declares no shift menu, so this result's codes were not checked against one");
      return new Map();
    }
    const text = fileText(this.files, name);
    if (text === null) {
      this.warn(`the problem's menu (${name}) is missing, so this result's codes were not checked against it`);
      return new Map();
    }
    return core.readSchedules(text).catalogue;
  }

  loadCells(problem) {
    const text = fileText(this.files, problem.scheduleInput?.dataFile);
    return text === null ? new Map() : core.readScheduleInput(text).cells;
  }

  checkScheduleUseds(defined) {
    const useds = this.result.OutScheduleUseds;
    if (!Array.isArray(useds) || !useds.length) return;
    this.report.stats.scheduleUseds = useds.length;
    const seen = new Set();
    useds.forEach((s, n) => {
      const code = s?.ScheduleCode;
      if (seen.has(code)) this.error(`OutScheduleUseds[${n}]: ScheduleCode ${code} appears twice`);
      seen.add(code);
      const entry = defined?.get(code);
      const weight = s?.ScheduleWeight;
      if (entry && Number.isInteger(weight) && weight !== entry.weightMinutes) {
        this.error(`OutScheduleUseds[${n}]: ScheduleWeight ${weight} contradicts the catalogue's ` +
          `${entry.weightMinutes} for code ${code}`);
      }
    });
    const used = new Set((this.result.OutRosterTeamDays || []).map((e) => e?.ScheduleCode));
    const orphans = [...seen].filter((c) => !used.has(c))
      .sort((a, b) => (a === null || a === undefined) - (b === null || b === undefined) || a - b);
    for (const orphan of orphans) this.warn(`OutScheduleUseds defines ScheduleCode ${orphan}, which no roster day uses`);
  }
}

function sameInterval(a, b) {
  if (!a || !b) return a === b || (!a && !b);
  return a.start === b.start && a.end === b.end;
}

/** What a code stands for, or null for a worked code nobody defines. */
function resolve(code, defined) {
  const known = defined?.get(code);
  if (known) return known;
  if (code in FALLBACK_SENTINELS) {
    return { code, description: FALLBACK_SENTINELS[code], weightMinutes: 0, interval: null, isSentinel: true };
  }
  return null;
}

/**
 * Validate a result against its problem.
 *
 * @param {object} result   the parsed result document
 * @param {object} options  { problem, files: {name: text}, resultName, problemName }
 * @returns {{ok, errors: {message, step}[], warnings: {message, step}[], stats}}
 */
export function validateResult(result, options = {}) {
  const r = new ResultValidator(result, options).run();
  return { ok: r.ok, errors: r.errors, warnings: r.warnings, stats: r.stats };
}

/** One verdict for a problem and its result: the problem's findings first, the result's counts added to its stats. */
export function mergeReports(problemReport, resultReport) {
  if (!resultReport) return problemReport;
  const { rosterDays, rosterDaysExpected, rosterDaysLeft, sidecarCodes } = resultReport.stats;
  return {
    ok: problemReport.ok && resultReport.ok,
    errors: [...problemReport.errors, ...resultReport.errors],
    warnings: [...problemReport.warnings, ...resultReport.warnings],
    stats: { ...problemReport.stats, rosterDays, rosterDaysExpected, rosterDaysLeft, sidecarCodes }
  };
}

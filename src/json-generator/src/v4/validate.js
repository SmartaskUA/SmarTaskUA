/**
 * Semantic validation of a v4.0 input bundle.
 *
 * A port of json_generation/schema_v4/src/schema_v4/{common,validate_input}.py:
 * same checks, same order, same wording, so a finding reads identically here and
 * in `make validate`. It runs on the *generated files*, re-parsed through core,
 * so it checks exactly what gets downloaded rather than the wizard's state.
 *
 * Every finding carries the id of the wizard step that owns the fix.
 *
 *   Tier 1  feasibility  - a worker-day whose cell cannot be satisfied at all
 *   Tier 2  structural   - per-week arithmetic and the labour-law caps
 *   Tier 3  integrity    - the CSVs and the codes they use
 *   Tier 4  reachability - declared-but-unusable things, reported as warnings
 */

import * as core from './core';
import { GRAINS, WEEKDAYS } from './constants';
import { schemaFindings } from './schema';

const { pyRepr, formatNumber, iso } = core;

class Report {
  constructor() {
    this.errors = [];
    this.warnings = [];
    this.stats = {};
  }

  error(message, step) {
    this.errors.push({ message, step });
  }

  warn(message, step) {
    this.warnings.push({ message, step });
  }

  get ok() {
    return this.errors.length === 0;
  }
}

/**
 * Emit findings, collapsing repeats of one cause: the first `keep` of each,
 * then a count. `items` are [cause, message] pairs.
 */
function reportGrouped(emit, items, keep = 3) {
  const groups = new Map();
  for (const [cause, message] of items) {
    if (!groups.has(cause)) groups.set(cause, []);
    groups.get(cause).push(message);
  }
  for (const messages of groups.values()) {
    messages.slice(0, keep).forEach(emit);
    if (messages.length > keep) {
      emit(`... and ${messages.length - keep} more with the same cause (${messages.length} in total)`);
    }
  }
}

function compareTuples(a, b) {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  return a.length - b.length;
}

/**
 * Every pair of spans that overlap, not merely adjacent ones. Spans are arrays
 * whose first two elements are [start, end]. Date ranges are closed (the end
 * belongs to the span); time windows are half-open.
 */
function overlappingPairs(spans, closed = true) {
  const ordered = [...spans].sort(compareTuples);
  const out = [];
  ordered.forEach((a, i) => {
    for (const b of ordered.slice(i + 1)) {
      if (closed ? b[0] > a[1] : b[0] >= a[1]) break;
      out.push([a, b]);
    }
  });
  return out;
}

const OPEN_END = '9999-12-31';

function fileText(files, name) {
  if (!name) return null;
  if (Object.prototype.hasOwnProperty.call(files, name)) return files[name];
  const base = name.split('/').pop();
  return Object.prototype.hasOwnProperty.call(files, base) ? files[base] : null;
}

function splitPair(key) {
  return key.split('\u001f');
}

class BundleValidator {
  constructor(problem, files) {
    this.problem = problem;
    this.files = files;
    this.report = new Report();
  }

  get p() {
    return this.problem;
  }

  horizon() {
    return core.horizon(this.p);
  }

  slot() {
    return this.p.timeGrid?.slotMinutes ?? 30;
  }

  run() {
    const r = this.report;
    if (this.p?.form !== 'input') {
      r.error('cannot tell which form this is. A problem carries form: "input"; a result ' +
        'carries an OutRosterTeamDays array.', 'review');
      return r;
    }
    r.stats.form = 'input';
    for (const f of schemaFindings(this.p)) r.error(f.message, f.step);
    this.validateCommon();
    this.validateInput();
    return r;
  }

  // ======================================================================
  // common.py
  // ======================================================================

  validateCommon() {
    const { p, report: r } = this;

    const version = p.schemaVersion;
    if (version !== '4.0') {
      if (version === '3.0') {
        r.error(
          "schemaVersion is '3.0'. This is a v3.0 document, or a SISQUAL export - " +
          'their generator still stamps 3.0 on a payload that is neither v3.0 nor ' +
          'v4.0. See docs/MIGRATION-3.0-to-4.0.md for the field-by-field conversion.', 'setup');
      } else {
        r.error(`schemaVersion must be '4.0', found ${pyRepr(version)}`, 'setup');
      }
    }

    const slot = p.timeGrid?.slotMinutes;
    if (Number.isInteger(slot) && slot > 0 && core.MINUTES_PER_DAY % slot) {
      r.error(`timeGrid.slotMinutes ${slot} does not divide 1440`, 'setup');
    }

    const days = this.horizon();
    const scope = p.temporalScope || {};
    if (!days.length) {
      r.error(`temporalScope ${scope.start ?? 'None'}..${scope.end ?? 'None'} is empty or reversed`, 'setup');
    }
    r.stats.days = days.length;

    const weekStart = p.calendar?.weekStart ?? 'monday';
    if (!WEEKDAYS.includes(weekStart)) {
      r.error(`calendar.weekStart ${pyRepr(weekStart)} is not one of ${WEEKDAYS.join(', ')}`, 'setup');
    }

    this.checkHolidays(days);
    this.checkContracts();
    this.checkEmployees(days);
    this.checkDimensions();
  }

  checkHolidays(days) {
    const r = this.report;
    const span = new Set(days);
    const seen = new Set();
    for (const h of this.p.calendar?.holidays || []) {
      const raw = h?.date ?? '';
      const day = iso(raw);
      if (!day) {
        r.error(`calendar.holidays: ${pyRepr(raw)} is not a date`, 'setup');
        continue;
      }
      if (seen.has(raw)) r.error(`calendar.holidays: ${raw} appears twice`, 'setup');
      seen.add(raw);
      if (!span.has(day)) r.warn(`calendar.holidays: ${raw} lies outside temporalScope`, 'setup');
      if (h.hasEve && !span.has(core.addDays(day, -1))) {
        r.warn(`calendar.holidays: ${raw} has hasEve, but its eve lies outside temporalScope`, 'setup');
      }
    }
  }

  checkContracts() {
    const r = this.report;
    const defs = this.p.contracts?.definitions || [];
    const seen = new Set();
    const slot = this.slot();
    for (const c of defs) {
      const cid = c?.id;
      if (seen.has(cid)) r.error(`contracts.definitions: duplicate id ${pyRepr(cid)}`, 'contracts');
      seen.add(cid);
      const minutes = c?.workMinutesPerDay;
      if (Number.isInteger(minutes) && Number.isInteger(slot) && slot > 0 && !core.onGrid(minutes, slot)) {
        r.error(`contract ${cid}: workMinutesPerDay ${minutes} is not a multiple ` +
          `of the ${slot}-minute grid`, 'contracts');
      }
    }
    r.stats.contracts = defs.length;
    if (!defs.length) r.warn('contracts.definitions is empty', 'contracts');
  }

  checkEmployees(days) {
    const r = this.report;
    const known = core.contractsById(this.p);
    const declared = core.dimensionSet(this.p);
    const employees = this.p.employees?.list || [];
    const seen = new Set();

    for (const e of employees) {
      const eid = e?.id ?? '?';
      if (seen.has(eid)) r.error(`employees.list: duplicate id ${pyRepr(eid)}`, 'employees');
      seen.add(eid);

      const contracts = e.contractAssignments || [];
      for (const a of contracts) {
        const ct = a?.contractType;
        if (!known.has(ct)) {
          r.error(`employee ${eid}: contractAssignments references unknown contract ${pyRepr(ct)}`, 'employees');
        }
      }
      this.checkOverlaps(contracts, `employee ${eid}: contractAssignments`);
      if (days.length && !days.every((d) => contracts.some((a) => core.covers(a, d)))) {
        r.warn(`employee ${eid}: contract coverage has a gap inside temporalScope`, 'employees');
      }

      const comps = e.competencyAssignments || [];
      const byPair = new Map();
      for (const a of comps) {
        const key = core.pairKey(a?.tableName, a?.tableValue);
        if (declared.size && !declared.has(key)) {
          r.error(`employee ${eid}: competency ${a?.tableName}/${a?.tableValue} is not in demand.dimensions`, 'employees');
        }
        if (!byPair.has(key)) byPair.set(key, []);
        byPair.get(key).push(a);
      }
      for (const [key, entries] of byPair) this.checkCompetencyOverlaps(entries, eid, splitPair(key));
      if (!comps.length) {
        r.warn(`employee ${eid}: holds no competencies, so no demand row can be covered by them`, 'employees');
      }
    }
    r.stats.employees = employees.length;
  }

  checkCompetencyOverlaps(entries, eid, [tableName, tableValue]) {
    const spans = [];
    for (const a of entries) {
      const start = iso(a?.start ?? '');
      const end = a?.end ? iso(a.end) || OPEN_END : OPEN_END;
      if (start) spans.push([start, end, a.level]);
    }
    for (const [[s1, e1, l1], [s2, e2, l2]] of overlappingPairs(spans)) {
      const detail = l1 === l2
        ? `the same level ${l1} twice`
        : `levels ${l1} and ${l2} at once, so its competence level is ` +
          `ambiguous; take ${Math.min(l1, l2)}, the higher competence`;
      this.report.warn(
        `employee ${eid}: holds ${tableName}/${tableValue} over overlapping dates ` +
        `(${s1}..${e1} and ${s2}..${e2}) with ${detail}`, 'employees');
    }
  }

  checkOverlaps(entries, label) {
    const spans = [];
    for (const a of entries) {
      const start = iso(a?.start ?? '');
      const end = a?.end ? iso(a.end) || OPEN_END : OPEN_END;
      if (start) spans.push([start, end]);
    }
    for (const [a, b] of overlappingPairs(spans)) {
      this.report.error(`${label}: ${a[0]}..${a[1]} overlaps ${b[0]}..${b[1]}`, 'employees');
    }
  }

  checkDimensions() {
    const r = this.report;
    const dims = this.p.demand?.dimensions || [];
    const seen = new Set();
    for (const d of dims) {
      const key = core.pairKey(d?.tableName, d?.tableValue);
      if (seen.has(key)) {
        r.error(`demand.dimensions: duplicate coordinate ${d?.tableName}/${d?.tableValue}`, 'dimensions');
      }
      seen.add(key);
    }
    r.stats.dimensions = dims.length;
    if (!dims.length) {
      r.error(
        'demand.dimensions is empty. It is the only declaration of which ' +
        '(tableName, tableValue) coordinates exist, so without it nothing can be ' +
        'cross-checked - see docs/FORMAT.md.', 'dimensions');
    }
  }

  // ======================================================================
  // validate_input.py
  // ======================================================================

  validateInput() {
    const days = this.horizon();
    const { rowsByGrain, openDays } = this.validateDemandCsvs(days);
    const { cells, dateCols } = this.validateScheduleCsv(days);

    this.checkDayOffCodes();
    this.checkPriorityHierarchy(rowsByGrain);
    this.checkSchedulesCatalogue();
    this.feasibilityPreflight();
    this.checkStructural(openDays, cells, dateCols);
    this.checkReachability(openDays, cells, rowsByGrain);

    this.report.stats.openDays = openDays.size;
  }

  // -- Tier 3: the demand CSVs --------------------------------------------

  validateDemandCsvs(days) {
    const r = this.report;
    const demand = this.p.demand || {};
    const span = new Set(days);
    const declared = core.dimensionSet(this.p);
    const slot = this.slot();
    const rowsByGrain = {};
    const openDays = new Set();

    for (const { grain, key } of GRAINS) {
      const name = demand[key];
      if (!name) continue;
      const text = fileText(this.files, name);
      if (text === null) {
        r.error(`demand.${key}: file not found: ${name}`, 'demand');
        rowsByGrain[grain] = [];
        continue;
      }

      const { rows, problems } = core.readDemand(text, grain);
      for (const msg of problems) r.error(`${name}: ${msg}`, 'demand');
      rowsByGrain[grain] = rows;
      r.stats[`demandRows.${grain}`] = rows.length;

      const seen = new Set();
      for (const row of rows) {
        const where = `${name} row ${row.line}`;
        if (span.size && !span.has(row.date)) r.error(`${where}: date ${row.date} lies outside temporalScope`, 'demand');
        const pair = core.pairKey(row.tableName, row.tableValue);
        if (declared.size && !declared.has(pair)) {
          r.error(`${where}: ${row.tableName}/${row.tableValue} is not in demand.dimensions`, 'demand');
        }
        for (const label of ['minimum', 'ideal', 'estimated']) {
          if (row[label] < 0) r.error(`${where}: ${label} is negative (${formatNumber(row[label])})`, 'demand');
        }

        const win = row.window ? core.intervalToString(row.window) : '';
        if (grain === 'days') {
          // Workload minutes, not headcount: no window, and the value is a
          // duration that must land on the grid.
          if (row.window) {
            r.warn(`${where}: the days grain is whole-day workload; a start/end window here is ignored`, 'demand');
          }
          if (row.minimum && !core.onGrid(Math.trunc(row.minimum), slot)) {
            r.warn(`${where}: ${formatNumber(row.minimum)} workload minutes is not ` +
              `a multiple of the ${slot}-minute grid`, 'demand');
          }
        } else if (!row.window) {
          r.error(`${where}: start/end are mandatory on the ${grain} grain`, 'demand');
        } else {
          if (!core.onGrid(row.window.start, slot) || !core.onGrid(row.window.end, slot)) {
            r.error(`${where}: window ${win} does not land on the ${slot}-minute grid`, 'demand');
          }
          openDays.add(row.date);
        }

        const keyParts = grain === 'shifts' ? [row.date, row.workPeriod, pair, win] : [row.date, pair, win];
        const dupKey = keyParts.join('\u001e');
        if (seen.has(dupKey)) {
          r.error(`${where}: duplicate row for ${row.date} ${row.tableName}/${row.tableValue} ${win}`.trimEnd(), 'demand');
        }
        seen.add(dupKey);
      }

      if (grain === 'periods') this.checkTiling(rows, name);
    }

    if (!openDays.size) {
      r.warn('no demand row carries a window, so every day is closed and nothing needs staffing', 'demand');
    }
    return { rowsByGrain, openDays };
  }

  /** Overlapping windows for one (date, dimension) double-count the same slot. */
  checkTiling(rows, name) {
    const buckets = new Map();
    for (const row of rows) {
      if (!row.window) continue;
      const key = [row.date, row.tableName, row.tableValue];
      const k = key.join('\u001f');
      if (!buckets.has(k)) buckets.set(k, { key, group: [] });
      buckets.get(k).group.push(row);
    }
    const sorted = [...buckets.values()].sort((a, b) => compareTuples(a.key, b.key));
    for (const { key: [day, tn, tv], group } of sorted) {
      const spans = group.map((row) => [row.window.start, row.window.end, row.line, row]);
      for (const [a, b] of overlappingPairs(spans, false)) {
        this.report.warn(
          `${name}: ${day} ${tn}/${tv} has overlapping windows ${core.intervalToString(a[3].window)} ` +
          `(row ${a[2]}) and ${core.intervalToString(b[3].window)} (row ${b[2]}); a worker in the ` +
          'overlap counts toward both', 'demand');
      }
    }
  }

  // -- Tier 3: schedule_input.csv -----------------------------------------

  validateScheduleCsv(days) {
    const r = this.report;
    const name = this.p.scheduleInput?.dataFile;
    const none = { cells: new Map(), dateCols: [] };
    if (!name) return none;
    const text = fileText(this.files, name);
    if (text === null) {
      r.error(`scheduleInput.dataFile: file not found: ${name}`, 'scheduleInput');
      return none;
    }

    const { cells, dates: dateCols, problems } = core.readScheduleInput(text);
    for (const msg of problems) r.error(`${name}: ${msg}`, 'scheduleInput');

    if (days.length && dateCols.join(',') !== days.join(',')) {
      if (dateCols.length !== days.length) {
        r.error(`${name}: has ${dateCols.length} date columns but temporalScope spans ` +
          `${days.length} days`, 'scheduleInput');
      } else {
        r.error(`${name}: date columns do not match temporalScope ` +
          `(${dateCols[0]}..${dateCols[dateCols.length - 1]} vs ${days[0]}..${days[days.length - 1]})`, 'scheduleInput');
      }
    }

    const employees = this.p.employees?.list || [];
    const ids = new Set(employees.map((e) => e?.id));
    for (const missing of [...ids].filter((id) => !cells.has(id)).sort()) {
      r.error(`${name}: employee ${missing} has no row`, 'scheduleInput');
    }
    for (const extra of [...cells.keys()].filter((id) => !ids.has(id)).sort()) {
      r.error(`${name}: row ${extra} is not an employee in employees.list`, 'scheduleInput');
    }

    const contracts = core.contractsById(this.p);
    const mismatches = [];
    for (const emp of employees) {
      const eid = emp?.id;
      const row = cells.get(eid) || {};
      for (const col of dateCols) {
        const raw = row[col] ?? '';
        const { rule } = core.tryClassifyCell(raw, this.p);
        // A bad cell is reported once, by the feasibility preflight.
        if (!rule || rule.kind !== 'exact_hours') continue;
        const cid = core.activeContract(emp, iso(col));
        const wantedMin = contracts.get(cid)?.workMinutesPerDay;
        if (wantedMin !== undefined && wantedMin !== null && rule.minutes !== wantedMin) {
          mismatches.push([`${cid}:${rule.minutes}`,
            `${name}: ${eid} on ${col}: cell ${pyRepr(raw)} is ${rule.minutes} min but ` +
            `contract ${cid} states ${wantedMin}`]);
        }
      }
    }
    reportGrouped((m) => r.warn(m, 'scheduleInput'), mismatches);
    return { cells, dateCols, scheduleInput: { cells, dates: dateCols } };
  }

  // -- Tier 3: integrity ---------------------------------------------------

  checkDayOffCodes() {
    const r = this.report;
    const codes = this.p.scheduleInput?.dayOffCodes || {};
    if (!Object.keys(codes).length) {
      r.error('scheduleInput.dayOffCodes is empty: every non-numeric cell would be undeclared', 'scheduleInput');
    }
    for (const [code, entry] of Object.entries(codes)) {
      if (!code.trim()) r.error('scheduleInput.dayOffCodes: a code is blank', 'scheduleInput');
      if (!['preferable', 'unavailable'].includes(entry?.kind)) {
        r.error(`dayOffCodes[${pyRepr(code)}]: kind must be 'preferable' or 'unavailable', ` +
          `found ${pyRepr(entry?.kind)}`, 'scheduleInput');
      }
    }
  }

  checkPriorityHierarchy(rowsByGrain) {
    const r = this.report;
    const entries = this.p.priorityHierarchy || [];
    if (!entries.length) return;
    const declared = core.dimensionSet(this.p);
    const demanded = new Set(Object.values(rowsByGrain).flat().map((row) => core.pairKey(row.tableName, row.tableValue)));
    const seenRank = new Set();
    for (const e of entries) {
      const rank = e?.rank;
      if (seenRank.has(rank)) r.error(`priorityHierarchy: duplicate rank ${rank}`, 'rules');
      seenRank.add(rank);
      const pair = core.pairKey(e?.tableName, e?.tableValue);
      if (declared.size && !declared.has(pair)) {
        r.error(`priorityHierarchy rank ${rank}: ${e?.tableName}/${e?.tableValue} is not in ` +
          'demand.dimensions', 'rules');
      } else if (demanded.size && !demanded.has(pair)) {
        r.warn(`priorityHierarchy rank ${rank}: ${e?.tableName}/${e?.tableValue} is never demanded, ` +
          'so this rank fills nothing', 'rules');
      }
      const lo = e?.minAbilityLevel;
      const hi = e?.maxAbilityLevel;
      if (Number.isInteger(lo) && Number.isInteger(hi) && lo > hi) {
        r.error(`priorityHierarchy rank ${rank}: minAbilityLevel ${lo} is above ` +
          `maxAbilityLevel ${hi} (level 1 is the highest, so min must be the ` +
          'smaller number)', 'rules');
      }
    }
    r.stats.priorityRanks = entries.length;
  }

  checkSchedulesCatalogue() {
    const r = this.report;
    const name = this.p.schedules?.dataFile;
    if (!name) return;
    const text = fileText(this.files, name);
    if (text === null) {
      r.error(`schedules.dataFile: file not found: ${name}`, 'schedules');
      return;
    }
    const { catalogue, problems } = core.readSchedules(text);
    for (const msg of problems) r.error(`${name}: ${msg}`, 'schedules');
    const slot = this.slot();
    const schedules = [...catalogue.values()];
    const offGrid = schedules
      .filter((s) => s.interval && !(core.onGrid(s.interval.start, slot) && core.onGrid(s.interval.end, slot)))
      .map((s) => s.code);
    if (offGrid.length) {
      r.warn(`${name}: ${offGrid.length} schedule(s) do not land on the ${slot}-minute grid ` +
        `(e.g. ${offGrid[0]}); a solver on this grid cannot emit them`, 'schedules');
    }
    const mismatched = schedules
      .filter((s) => s.interval && s.interval.end - s.interval.start !== s.weightMinutes)
      .map((s) => s.code);
    if (mismatched.length) {
      r.warn(`${name}: ${mismatched.length} schedule(s) whose window length differs from ` +
        `scheduleWeightMinutes (e.g. ${mismatched[0]})`, 'schedules');
    }
    r.stats.schedules = catalogue.size;
  }

  // -- Tier 1: feasibility -------------------------------------------------

  feasibilityPreflight() {
    const r = this.report;
    const name = this.p.scheduleInput?.dataFile;
    const text = fileText(this.files, name);
    const scheduleInput = text === null ? null : core.readScheduleInput(text);
    let found;
    try {
      found = core.scanFeasibility(this.p, scheduleInput);
    } catch (exc) {
      if (exc instanceof core.DomainError) {
        r.error(`feasibility scan: ${exc.message}`, 'scheduleInput');
        return;
      }
      r.warn(`feasibility scan did not complete (${exc.message}); real errors may be hidden`, 'scheduleInput');
      return;
    }
    reportGrouped((m) => r.error(m, 'scheduleInput'), found.map((d) => [d.reason, core.diagnosticToString(d)]));
    r.stats.diagnostics = found.length;
  }

  // -- Tier 2: structural --------------------------------------------------

  checkStructural(openDays, cells, dateCols) {
    const r = this.report;
    if (!cells.size || !dateCols.length) return;
    const days = this.horizon();
    if (!days.length) return;
    let weekStart = String(this.p.calendar?.weekStart ?? 'monday').toLowerCase();
    if (!WEEKDAYS.includes(weekStart)) weekStart = 'monday';
    const origin = days[0];
    const { preferable, unavailable } = core.daySets(this.p.scheduleInput);
    const limits = this.legislationLimits();

    const weeks = new Map();
    for (const d of days) {
      if (!openDays.has(d)) continue;
      const wk = core.weekIndex(d, origin, weekStart);
      if (!weeks.has(wk)) weeks.set(wk, []);
      weeks.get(wk).push(d);
    }
    const sortedWeeks = [...weeks.entries()].sort((a, b) => a[0] - b[0]);

    let negative = 0;
    for (const emp of this.p.employees?.list || []) {
      const eid = emp?.id;
      const row = cells.get(eid) || {};
      for (const [wk, wdays] of sortedWeeks) {
        const u = wdays.filter((d) => unavailable.has(row[d])).length;
        const dpref = wdays.filter((d) => preferable.has(row[d])).length;
        const nWk = wdays.length - u - dpref;
        if (nWk < 0) {
          negative += 1;
          r.error(`employee ${eid}, week ${wk}: n_wk = ${wdays.length} open - ${u} ` +
            `unavailable - ${dpref} preferable = ${nWk}, which is impossible`, 'scheduleInput');
        }
        const cap = limits.MaxConsecutiveWorkDaysInWeek;
        if (cap !== undefined && nWk > cap) {
          r.error(`employee ${eid}, week ${wk}: ${nWk} working days exceeds ` +
            `MaxConsecutiveWorkDaysInWeek of ${cap}`, 'scheduleInput');
        }
      }

      const cap = limits.MaxConsecutiveWorkDays;
      if (cap !== undefined) {
        let run = 0;
        for (const d of days) {
          const cell = row[d] ?? '';
          const working = openDays.has(d) && !unavailable.has(cell) && !preferable.has(cell);
          run = working ? run + 1 : 0;
          if (run > cap) {
            r.error(`employee ${eid}: forced to work ${run} days in a row ending ` +
              `${d}, above MaxConsecutiveWorkDays of ${cap}`, 'scheduleInput');
            break;
          }
        }
      }
    }
    r.stats.negative_n_wk = negative;
  }

  /** The enabled hard constraints' integer parameters, flattened into one lookup. */
  legislationLimits() {
    return legislationLimits(this.p);
  }

  // -- Tier 4: reachability ------------------------------------------------

  checkReachability(openDays, cells, rowsByGrain) {
    const r = this.report;

    const used = new Set();
    for (const row of cells.values()) for (const c of Object.values(row)) if (c) used.add(c);
    for (const code of Object.keys(this.p.scheduleInput?.dayOffCodes || {})) {
      if (!used.has(code)) r.warn(`dayOffCodes declares ${pyRepr(code)}, which no cell uses`, 'scheduleInput');
    }

    const demanded = new Set(Object.values(rowsByGrain).flat().map((row) => core.pairKey(row.tableName, row.tableValue)));
    const held = new Map();
    for (const e of this.p.employees?.list || []) {
      for (const a of e?.competencyAssignments || []) {
        const key = core.pairKey(a?.tableName, a?.tableValue);
        held.set(key, (held.get(key) || 0) + 1);
      }
    }

    const declaredSorted = [...core.dimensionSet(this.p)].map(splitPair).sort(compareTuples);
    for (const [tn, tv] of declaredSorted) {
      const key = core.pairKey(tn, tv);
      if (!held.has(key)) r.warn(`dimension ${tn}/${tv} is declared but nobody holds it`, 'dimensions');
      if (demanded.size && !demanded.has(key)) r.warn(`dimension ${tn}/${tv} is declared but never demanded`, 'demand');
    }

    // Headcount only: the days grain states workload MINUTES.
    const worst = new Map();
    for (const grain of ['periods', 'shifts']) {
      for (const row of rowsByGrain[grain] || []) {
        const key = core.pairKey(row.tableName, row.tableValue);
        worst.set(key, Math.max(worst.get(key) ?? 0, row.minimum));
      }
    }
    const worstSorted = [...worst.entries()].map(([k, need]) => [...splitPair(k), need]).sort(compareTuples);
    for (const [tn, tv, need] of worstSorted) {
      const have = held.get(core.pairKey(tn, tv)) || 0;
      if (need > have) {
        r.warn(`dimension ${tn}/${tv} asks for up to ${formatNumber(need)} workers but only ${have} hold it`, 'demand');
      }
    }
  }
}

/** The enabled hard constraints' integer parameters, flattened into one lookup. */
export function legislationLimits(problem) {
  const out = {};
  for (const entry of problem?.constraints?.hard || []) {
    if (entry?.enabled === false) continue;
    for (const [k, v] of Object.entries(entry?.parameters || {})) {
      if (Number.isInteger(v)) out[k] = v;
    }
  }
  return out;
}

/**
 * Validate a v4.0 input bundle.
 *
 * @param {object} problem  the parsed problem.json
 * @param {object} files    { fileName: csvText } for every file the problem names
 * @returns {{ok, errors: {message, step}[], warnings: {message, step}[], stats}}
 */
export function validateBundle(problem, files = {}) {
  const report = new BundleValidator(problem || {}, files).run();
  return { ok: report.ok, errors: report.errors, warnings: report.warnings, stats: report.stats };
}

export { reportGrouped };

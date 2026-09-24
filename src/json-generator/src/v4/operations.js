/**
 * Pure state transforms the wizard steps share: cascading renames and
 * deletions, applying the weekly template, generating the shift menu, and the
 * derived views (open days, weekly load) the UI shows. Each takes a state and
 * returns a new one; nothing here touches React.
 */

import * as core from './core';
import { FIRST_MENU_CODE, WEEKDAYS } from './constants';
import { buildBundle } from './generate';
import { validateBundle, legislationLimits } from './validate';
import { newId } from './state';

// --------------------------------------------------------------------------
// validation of the whole state, the one source every step reads
// --------------------------------------------------------------------------

export function validateState(state) {
  const bundle = buildBundle(state);
  const report = validateBundle(bundle.problem, bundle.files);
  return { bundle, report };
}

export function findingsFor(report, stepId) {
  return {
    errors: (report?.errors || []).filter((f) => f.step === stepId),
    warnings: (report?.warnings || []).filter((f) => f.step === stepId)
  };
}

// --------------------------------------------------------------------------
// dimensions
// --------------------------------------------------------------------------

const samePair = (a, tableName, tableValue) => a.tableName === tableName && a.tableValue === tableValue;

function mapTemplate(template, fn) {
  return Object.fromEntries(WEEKDAYS.map((d) => [d, fn(template?.[d] || [])]));
}

/** How many records reference a coordinate, by kind. */
export function dimensionUsage(state, tableName, tableValue) {
  const match = (a) => samePair(a, tableName, tableValue);
  const blocks = WEEKDAYS.reduce((n, d) => n + (state.demand.weeklyTemplate?.[d] || []).filter(match).length, 0);
  return {
    periods: state.demand.periods.filter(match).length,
    days: state.demand.days.filter(match).length,
    shifts: state.demand.shifts.filter(match).length,
    blocks,
    competencies: state.employees.list.reduce((n, e) => n + (e.competencyAssignments || []).filter(match).length, 0),
    priority: state.priorityHierarchy.filter(match).length
  };
}

function reRank(entries) {
  return entries.map((e, i) => ({ ...e, rank: i + 1 }));
}

/** Remove a coordinate and everything that references it. */
export function removeDimension(state, tableName, tableValue) {
  const keep = (a) => !samePair(a, tableName, tableValue);
  return {
    ...state,
    demand: {
      ...state.demand,
      dimensions: state.demand.dimensions.filter(keep),
      periods: state.demand.periods.filter(keep),
      days: state.demand.days.filter(keep),
      shifts: state.demand.shifts.filter(keep),
      weeklyTemplate: mapTemplate(state.demand.weeklyTemplate, (blocks) => blocks.filter(keep))
    },
    employees: {
      ...state.employees,
      list: state.employees.list.map((e) => ({ ...e, competencyAssignments: (e.competencyAssignments || []).filter(keep) }))
    },
    priorityHierarchy: reRank(state.priorityHierarchy.filter(keep))
  };
}

/** Replace a coordinate (and its references) with `next` — {tableName, tableValue, name, description}. */
export function updateDimension(state, from, next) {
  const rename = (a) => (samePair(a, from.tableName, from.tableValue)
    ? { ...a, tableName: next.tableName, tableValue: next.tableValue } : a);
  return {
    ...state,
    demand: {
      ...state.demand,
      dimensions: state.demand.dimensions.map((d) => (samePair(d, from.tableName, from.tableValue) ? { ...next } : d)),
      periods: state.demand.periods.map(rename),
      days: state.demand.days.map(rename),
      shifts: state.demand.shifts.map(rename),
      weeklyTemplate: mapTemplate(state.demand.weeklyTemplate, (blocks) => blocks.map(rename))
    },
    employees: {
      ...state.employees,
      list: state.employees.list.map((e) => ({ ...e, competencyAssignments: (e.competencyAssignments || []).map(rename) }))
    },
    priorityHierarchy: state.priorityHierarchy.map(rename)
  };
}

// --------------------------------------------------------------------------
// contracts and employees
// --------------------------------------------------------------------------

export function contractUsage(state, id) {
  return state.employees.list.filter((e) => (e.contractAssignments || []).some((a) => a.contractType === id)).length;
}

export function renameContract(state, from, to) {
  return {
    ...state,
    employees: {
      ...state.employees,
      list: state.employees.list.map((e) => ({
        ...e,
        contractAssignments: (e.contractAssignments || []).map((a) => (a.contractType === from ? { ...a, contractType: to } : a))
      }))
    }
  };
}

/** Rename an employee, carrying their schedule_input row with them. */
export function renameEmployee(state, from, to) {
  if (from === to) return state;
  const { [from]: row, ...rest } = state.scheduleInput.dataMatrix || {};
  return {
    ...state,
    scheduleInput: { ...state.scheduleInput, dataMatrix: row ? { ...rest, [to]: row } : rest }
  };
}

export function removeEmployee(state, id) {
  const rest = { ...(state.scheduleInput.dataMatrix || {}) };
  delete rest[id];
  return {
    ...state,
    employees: { ...state.employees, list: state.employees.list.filter((e) => e.id !== id) },
    scheduleInput: { ...state.scheduleInput, dataMatrix: rest }
  };
}

// --------------------------------------------------------------------------
// day-off codes and the schedule matrix
// --------------------------------------------------------------------------

export function codeUsage(state, code) {
  let n = 0;
  for (const row of Object.values(state.scheduleInput.dataMatrix || {})) {
    for (const cell of Object.values(row)) if (cell === code) n += 1;
  }
  return n;
}

function mapCells(matrix, fn) {
  return Object.fromEntries(Object.entries(matrix || {}).map(([eid, row]) =>
    [eid, Object.fromEntries(Object.entries(row).map(([d, c]) => [d, fn(c)]))]));
}

/** Rename a day-off code, keeping its position in the palette, and its cells. */
export function renameDayOffCode(state, from, to, entry) {
  const codes = Object.fromEntries(Object.entries(state.scheduleInput.dayOffCodes).map(([c, e]) =>
    (c === from ? [to, entry ?? e] : [c, e])));
  return {
    ...state,
    scheduleInput: {
      ...state.scheduleInput,
      dayOffCodes: codes,
      dataMatrix: from === to ? state.scheduleInput.dataMatrix : mapCells(state.scheduleInput.dataMatrix, (c) => (c === from ? to : c))
    }
  };
}

/** Remove a day-off code; its cells become `replacement` (blank = no assignment). */
export function removeDayOffCode(state, code, replacement = '') {
  const codes = { ...state.scheduleInput.dayOffCodes };
  delete codes[code];
  return {
    ...state,
    scheduleInput: {
      ...state.scheduleInput,
      dayOffCodes: codes,
      dataMatrix: mapCells(state.scheduleInput.dataMatrix, (c) => (c === code ? replacement : c))
    }
  };
}

export function horizonOf(state) {
  return core.dateRange(state.temporalScope.start, state.temporalScope.end);
}

/** Demand rows and template-free records dated outside the scope, by kind. */
export function outsideScope(state) {
  const span = new Set(horizonOf(state));
  if (!span.size) return { rows: 0, holidays: 0 };
  const out = (r) => !span.has(r.date);
  return {
    rows: state.demand.periods.filter(out).length + state.demand.days.filter(out).length +
      state.demand.shifts.filter(out).length,
    holidays: (state.calendar.holidays || []).filter(out).length
  };
}

/** Drop demand rows, holidays and matrix cells that fall outside the scope. */
export function pruneOutsideScope(state) {
  const span = new Set(horizonOf(state));
  if (!span.size) return state;
  const inside = (r) => span.has(r.date);
  const matrix = Object.fromEntries(Object.entries(state.scheduleInput.dataMatrix || {}).map(([eid, row]) =>
    [eid, Object.fromEntries(Object.entries(row).filter(([d]) => span.has(d)))]));
  return {
    ...state,
    calendar: { ...state.calendar, holidays: (state.calendar.holidays || []).filter(inside) },
    demand: {
      ...state.demand,
      periods: state.demand.periods.filter(inside),
      days: state.demand.days.filter(inside),
      shifts: state.demand.shifts.filter(inside)
    },
    scheduleInput: { ...state.scheduleInput, dataMatrix: matrix }
  };
}

/**
 * Fill missing matrix cells: `A` where a contract covers the day, blank where
 * none does (asking for work there is an error). Existing cells, blank ones
 * included, are kept.
 */
export function fillMatrix(state, fill = 'A') {
  const dates = horizonOf(state);
  const matrix = { ...(state.scheduleInput.dataMatrix || {}) };
  let changed = false;
  for (const emp of state.employees.list) {
    const row = { ...(matrix[emp.id] || {}) };
    for (const d of dates) {
      if (row[d] === undefined) {
        row[d] = core.activeContract(emp, d) ? fill : '';
        changed = true;
      }
    }
    matrix[emp.id] = row;
  }
  return changed ? { ...state, scheduleInput: { ...state.scheduleInput, dataMatrix: matrix } } : state;
}

/**
 * What one matrix cell means and what is wrong with it, for the UI:
 * {kind, error, warning}. The same rules as core.scanFeasibility plus the
 * validator's contract-length warning, cell by cell.
 */
export function analyseCell(value, { problem, covered, contractMinutes, slotMinutes }) {
  if (value === '-') return { kind: 'pending', error: 'Type a number of hours', warning: '' };
  const { rule, error } = core.tryClassifyCell(value, problem);
  if (error) return { kind: 'invalid', error, warning: '' };
  if (!core.ASKS_FOR_WORK.has(rule.kind)) return { kind: rule.kind, dayOff: rule.dayOff, error: '', warning: '' };
  if (!covered) return { kind: rule.kind, error: 'Asks for work on a day no contract covers', warning: '' };
  const duration = rule.kind === 'exact_hours' ? rule.minutes : contractMinutes;
  if (duration !== null && duration !== undefined && !core.onGrid(duration, slotMinutes)) {
    return { kind: rule.kind, error: `${duration} min is not a multiple of the ${slotMinutes}-minute grid`, warning: '' };
  }
  const off = (rule.windows || []).find((w) => !core.onGrid(w.start, slotMinutes) || !core.onGrid(w.end, slotMinutes));
  if (off) return { kind: rule.kind, error: `Window ${core.intervalToString(off)} is off the ${slotMinutes}-minute grid`, warning: '' };
  const warning = rule.kind === 'exact_hours' && contractMinutes && rule.minutes !== contractMinutes
    ? `${rule.minutes} min, but the contract states ${contractMinutes}` : '';
  return { kind: rule.kind, error: '', warning };
}

/** Every covered cell set to `value`, uncovered ones blank. */
export function resetMatrix(state, value = 'A') {
  const dates = horizonOf(state);
  const matrix = {};
  for (const emp of state.employees.list) {
    matrix[emp.id] = Object.fromEntries(dates.map((d) => [d, core.activeContract(emp, d) ? value : '']));
  }
  return { ...state, scheduleInput: { ...state.scheduleInput, dataMatrix: matrix } };
}

// --------------------------------------------------------------------------
// demand
// --------------------------------------------------------------------------

/** Dates with at least one windowed headcount row: the open days. */
export function openDays(state) {
  const out = new Set();
  for (const row of [...state.demand.periods, ...state.demand.shifts]) {
    if (row.start || row.end) out.add(row.date);
  }
  return out;
}

export function holidayDates(state) {
  return new Set((state.calendar.holidays || []).map((h) => h.date));
}

function blockStart(block) {
  return core.tryHhmmToMin(block.start) ?? 0;
}

/**
 * Periods rows from the weekly template. Within a date, rows follow the
 * dimension declaration order, then start time. `holidays: 'skip'` leaves
 * holiday dates for manual editing.
 */
export function templateRows(state, { holidays = 'template', dates = horizonOf(state) } = {}) {
  const order = new Map(state.demand.dimensions.map((d, i) => [core.pairKey(d.tableName, d.tableValue), i]));
  const rank = (b) => order.get(core.pairKey(b.tableName, b.tableValue)) ?? Number.MAX_SAFE_INTEGER;
  const skip = holidays === 'skip' ? holidayDates(state) : new Set();
  const rows = [];
  for (const date of dates) {
    if (skip.has(date)) continue;
    const blocks = [...(state.demand.weeklyTemplate?.[core.weekdayName(date)] || [])]
      .sort((a, b) => rank(a) - rank(b) || blockStart(a) - blockStart(b));
    for (const b of blocks) {
      rows.push({
        id: newId('periods'),
        date,
        tableName: b.tableName,
        tableValue: b.tableValue,
        minimum: b.minimum,
        ideal: b.ideal,
        estimated: b.estimated,
        start: b.start,
        end: b.end
      });
    }
  }
  return rows;
}

/** Apply the weekly template: 'replace' all periods rows, or 'fill' only dates that have none. */
export function applyTemplate(state, { mode = 'replace', holidays = 'template' } = {}) {
  let dates = horizonOf(state);
  let keep = [];
  if (mode === 'fill') {
    const taken = new Set(state.demand.periods.map((r) => r.date));
    dates = dates.filter((d) => !taken.has(d));
    keep = state.demand.periods;
  }
  const rows = [...keep, ...templateRows(state, { holidays, dates })];
  return { ...state, demand: { ...state.demand, periods: rows } };
}

/** [{a, b}] pairs of rows for the same (date, dimension) whose windows overlap. */
export function overlappingRows(rows) {
  const out = [];
  const withWindow = rows
    .map((r) => ({ r, w: core.tryParseRange(r.start, r.end) }))
    .filter((x) => x.w);
  for (let i = 0; i < withWindow.length; i++) {
    for (let j = i + 1; j < withWindow.length; j++) {
      const a = withWindow[i];
      const b = withWindow[j];
      if (a.r.date !== b.r.date || !samePair(a.r, b.r.tableName, b.r.tableValue)) continue;
      if ((a.r.workPeriod ?? '') !== (b.r.workPeriod ?? '')) continue;
      if (core.overlaps(core.interval(...a.w), core.interval(...b.w))) out.push({ a: a.r, b: b.r });
    }
  }
  return out;
}

/** The earliest window start and latest window end across periods rows, in minutes. */
export function demandEnvelope(state) {
  let lo = null;
  let hi = null;
  for (const row of state.demand.periods) {
    const w = core.tryParseRange(row.start, row.end);
    if (!w) continue;
    lo = lo === null ? w[0] : Math.min(lo, w[0]);
    hi = hi === null ? w[1] : Math.max(hi, w[1]);
  }
  return lo === null ? null : { start: lo, end: hi };
}

// --------------------------------------------------------------------------
// the shift menu
// --------------------------------------------------------------------------

export function menuRow(code, startMin, endMin) {
  return {
    code,
    description: `${core.minToHhmm(startMin)}-${core.minToHhmm(endMin)}`,
    scheduleWeightMinutes: endMin - startMin,
    startMin,
    endMin
  };
}

export function nextMenuCode(rows) {
  const worked = rows.map((r) => Number(r.code)).filter((c) => Number.isInteger(c) && c >= FIRST_MENU_CODE);
  return worked.length ? Math.max(...worked) + 1 : FIRST_MENU_CODE;
}

/**
 * Candidate menu rows: for every distinct contract length, each start on a
 * `stride` inside the envelope that fits, skipping windows the menu already has.
 */
export function generateMenuRows(state, { stride = 60, envelope } = {}) {
  const env = envelope || demandEnvelope(state) || { start: 8 * 60, end: 20 * 60 };
  const lengths = [...new Set(state.contracts.definitions
    .map((c) => Number(c.workMinutesPerDay))
    .filter((m) => Number.isInteger(m) && m > 0))].sort((a, b) => a - b);
  const existing = new Set(state.schedules.rows
    .filter((r) => r.startMin !== null && r.startMin !== undefined)
    .map((r) => `${r.startMin}-${r.endMin}`));
  let code = nextMenuCode(state.schedules.rows);
  const out = [];
  for (const length of lengths) {
    for (let s = env.start; s + length <= env.end; s += stride) {
      const key = `${s}-${s + length}`;
      if (existing.has(key)) continue;
      existing.add(key);
      out.push(menuRow(code, s, s + length));
      code += 1;
    }
  }
  return out;
}

// --------------------------------------------------------------------------
// the weekly working-day load the structural pass checks
// --------------------------------------------------------------------------

/**
 * {employeeId: [{week, dates, nWk}]} for open days, counted the way the
 * validator's structural pass counts them, plus the cap from labour law.
 */
export function weeklyLoad(state) {
  const days = horizonOf(state);
  const open = openDays(state);
  const cap = legislationLimits({ constraints: state.constraints }).MaxConsecutiveWorkDaysInWeek;
  if (!days.length) return { cap, byEmployee: {} };
  const weekStart = WEEKDAYS.includes(state.calendar.weekStart) ? state.calendar.weekStart : 'monday';
  const weeks = new Map();
  for (const d of days) {
    if (!open.has(d)) continue;
    const wk = core.weekIndex(d, days[0], weekStart);
    if (!weeks.has(wk)) weeks.set(wk, []);
    weeks.get(wk).push(d);
  }
  const { preferable, unavailable } = core.daySets(state.scheduleInput);
  const byEmployee = {};
  for (const emp of state.employees.list) {
    const row = state.scheduleInput.dataMatrix?.[emp.id] || {};
    byEmployee[emp.id] = [...weeks.entries()].sort((a, b) => a[0] - b[0]).map(([week, dates]) => ({
      week,
      dates,
      nWk: dates.filter((d) => !unavailable.has(row[d]) && !preferable.has(row[d])).length
    }));
  }
  return { cap, byEmployee };
}

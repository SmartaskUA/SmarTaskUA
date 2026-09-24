/**
 * Wizard state -> a v4.0 input bundle: problem.json plus its CSVs.
 *
 * The one producer the preview, the download and the validator all read, so
 * what is validated is exactly what is downloaded. CSVs are plain UTF-8 with LF
 * line endings and no BOM, numbers use a dot and drop a trailing .0, and every
 * file ends with a newline.
 */

import * as core from './core';
import { FORM, PROBLEM_TYPE, SCHEMA_VERSION, FILES } from './constants';

// --------------------------------------------------------------------------
// CSV writing
// --------------------------------------------------------------------------

function csvField(value) {
  const s = value === null || value === undefined ? '' : String(value);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** CSV text for `columns` and `rows` (arrays of values), LF, trailing newline. */
export function writeCsv(columns, rows) {
  return [columns, ...rows].map((r) => r.map(csvField).join(',')).join('\n') + '\n';
}

/** A demand value as written: numbers normalised, blank as 0 ("0 means unset"). */
function demandValue(value) {
  if (value === null || value === undefined || value === '') return '0';
  if (typeof value === 'number') return core.formatNumber(value);
  const n = core.tryNumber(value);
  return n === null ? String(value).trim() : core.formatNumber(n);
}

/** Stable sort by date only: rows keep the order they were authored or imported in. */
function byDate(rows) {
  return [...rows].sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
}

export function periodsCsv(rows) {
  return writeCsv(core.DEMAND_COLUMNS, byDate(rows).map((r) => [
    r.date, r.tableName, r.tableValue,
    demandValue(r.minimum), demandValue(r.ideal), demandValue(r.estimated),
    r.start ?? '', r.end ?? ''
  ]));
}

/** days: whole-day workload in minutes; the window columns stay empty. */
export function daysCsv(rows) {
  return periodsCsv(rows);
}

export function shiftsCsv(rows) {
  return writeCsv(core.SHIFTS_COLUMNS, byDate(rows).map((r) => [
    r.date, r.workPeriod ?? '', r.tableName, r.tableValue,
    demandValue(r.minimum), demandValue(r.ideal), demandValue(r.estimated),
    r.start ?? '', r.end ?? ''
  ]));
}

/**
 * A cell as written to schedule_input.csv: trimmed, operator prefix uppercased,
 * a decimal comma turned into a dot, and the UI's '-' placeholder written blank.
 */
export function canonicalCell(value) {
  let text = String(value ?? '').trim();
  if (!text || text === '-') return '';
  const colon = text.indexOf(':');
  if (colon > 0) {
    const head = text.slice(0, colon).toUpperCase();
    if (['EQUALS', 'INCLUDE', 'WITHIN', 'EXCEPT'].includes(head)) {
      text = `${head}:${text.slice(colon + 1).replace(/\s+/g, '')}`;
    }
  } else if (/^[+-]?\d+,\d+$/.test(text)) {
    text = text.replace(',', '.');
  }
  return text;
}

export function scheduleInputCsv(employees, dataMatrix, dates) {
  return writeCsv(['employee_id', ...dates], employees.map((e) => [
    e.id, ...dates.map((d) => canonicalCell(dataMatrix?.[e.id]?.[d]))
  ]));
}

export function schedulesCsv(rows) {
  return writeCsv(core.SCHEDULE_COLUMNS, rows.map((r) => [
    r.code, r.description ?? '', r.scheduleWeightMinutes ?? 0,
    r.startMin ?? '', r.endMin ?? ''
  ]));
}

// --------------------------------------------------------------------------
// problem.json
// --------------------------------------------------------------------------

/** Copy `obj` keeping only the listed keys whose value is set (not undefined, null or ''). */
function pick(obj, keys) {
  const out = {};
  for (const k of keys) {
    const v = obj?.[k];
    if (v !== undefined && v !== null && v !== '') out[k] = v;
  }
  return out;
}

function assignment(a, extra) {
  return { ...extra, start: a.start, end: a.end ? a.end : null };
}

function asNumber(value) {
  if (typeof value === 'number') return value;
  const n = core.tryNumber(value);
  return n === null ? value : n;
}

export function buildProblem(state) {
  const files = { ...FILES, ...(state.files || {}) };
  const problem = {
    schemaVersion: SCHEMA_VERSION,
    form: FORM,
    problemType: PROBLEM_TYPE,
    metadata: pick(state.metadata, ['problemId', 'createdAt', 'description', 'source', 'rosterCode']),
    timeGrid: { slotMinutes: asNumber(state.timeGrid?.slotMinutes) },
    temporalScope: { start: state.temporalScope?.start ?? '', end: state.temporalScope?.end ?? '' }
  };
  if (problem.metadata.problemId === undefined) problem.metadata.problemId = '';

  const calendar = { weekStart: state.calendar?.weekStart || 'monday' };
  const holidays = (state.calendar?.holidays || []).map((h) => {
    const out = pick(h, ['date', 'code', 'name', 'description']);
    if (typeof h.hasEve === 'boolean') out.hasEve = h.hasEve;
    return out;
  });
  if (holidays.length) calendar.holidays = holidays;
  problem.calendar = calendar;

  problem.contracts = {
    definitions: (state.contracts?.definitions || []).map((c) => ({
      id: c.id,
      ...pick(c, ['name']),
      workMinutesPerDay: asNumber(c.workMinutesPerDay)
    }))
  };

  problem.employees = {
    list: (state.employees?.list || []).map((e) => ({
      id: e.id,
      ...pick(e, ['name']),
      contractAssignments: (e.contractAssignments || []).map((a) =>
        assignment(a, { contractType: a.contractType })),
      competencyAssignments: (e.competencyAssignments || []).map((a) =>
        assignment(a, { tableName: a.tableName, tableValue: a.tableValue, level: asNumber(a.level) }))
    }))
  };

  problem.demand = {
    dimensions: (state.demand?.dimensions || []).map((d) => ({
      tableName: d.tableName,
      tableValue: d.tableValue,
      ...pick(d, ['name', 'description'])
    })),
    dataFileDays: files.days,
    dataFilePeriods: files.periods,
    dataFileShifts: files.shifts
  };

  problem.scheduleInput = {
    dataFile: files.scheduleInput,
    dayOffCodes: Object.fromEntries(
      Object.entries(state.scheduleInput?.dayOffCodes || {}).map(([code, entry]) =>
        [code, { kind: entry.kind, ...pick(entry, ['name', 'description']) }])
    )
  };

  if (state.schedules?.enabled) problem.schedules = { dataFile: files.schedules };

  const priority = (state.priorityHierarchy || []).map((e) => ({
    rank: asNumber(e.rank),
    ...pick(e, ['label']),
    tableName: e.tableName,
    tableValue: e.tableValue,
    ...pick(e, ['maxAlarmTableType', 'generationSequenceType']),
    ...Object.fromEntries(['minAbilityLevel', 'maxAbilityLevel', 'alarmLevelPercentage']
      .filter((k) => e[k] !== undefined && e[k] !== null && e[k] !== '')
      .map((k) => [k, asNumber(e[k])]))
  }));
  if (priority.length) problem.priorityHierarchy = priority;

  const hard = (state.constraints?.hard || []).map((c) => {
    const out = {
      id: c.id,
      type: c.type,
      parameters: Object.fromEntries(Object.entries(c.parameters || {}).map(([k, v]) => [k, asNumber(v)])),
      ...pick(c, ['startDate', 'endDate'])
    };
    if (typeof c.enabled === 'boolean') out.enabled = c.enabled;
    return out;
  });
  const soft = state.constraints?.soft || [];
  if (hard.length || soft.length) problem.constraints = { hard, soft };

  return problem;
}

// --------------------------------------------------------------------------
// the bundle
// --------------------------------------------------------------------------

/**
 * { problem, problemName, files } — `files` maps every CSV name the problem
 * points at to its text.
 */
export function buildBundle(state) {
  const names = { ...FILES, ...(state.files || {}) };
  const problem = buildProblem(state);
  const dates = core.dateRange(state.temporalScope?.start, state.temporalScope?.end);
  const files = {
    [names.days]: daysCsv(state.demand?.days || []),
    [names.periods]: periodsCsv(state.demand?.periods || []),
    [names.shifts]: shiftsCsv(state.demand?.shifts || []),
    [names.scheduleInput]: scheduleInputCsv(state.employees?.list || [], state.scheduleInput?.dataMatrix, dates)
  };
  if (state.schedules?.enabled) files[names.schedules] = schedulesCsv(state.schedules.rows || []);
  return { problem, problemName: names.problem, files };
}

/** [[fileName, text]] for every file in the bundle, problem first — what the ZIP holds. */
export function bundleEntries(bundle) {
  return [
    [bundle.problemName, `${JSON.stringify(bundle.problem, null, 2)}\n`],
    ...Object.entries(bundle.files)
  ];
}

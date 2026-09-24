/**
 * Shared domain for schema v4.0: time, dates, cells, and all CSV reading.
 *
 * A port of json_generation/schema_v4/src/schema_v4/core.py. It decides nothing
 * about what counts as an error - that is validate.js's job - and exists so the
 * UI hints, the generator and the validator all agree on what the data says.
 * Parsers come in pairs: a `try*` one returning null and a strict one throwing
 * DomainError.
 *
 * Dates are plain 'YYYY-MM-DD' strings throughout: they compare correctly as
 * strings, and all arithmetic goes through UTC so no local timezone or DST
 * change can duplicate or skip a day.
 */

import Papa from 'papaparse';
import { OPERATORS, WEEKDAYS } from './constants';

export const MINUTES_PER_DAY = 1440;

/** Cell kinds that ask for a working day. */
export const ASKS_FOR_WORK = new Set(['auto', 'exact_hours', 'equals', 'include', 'within', 'except']);

export class DomainError extends Error {
  constructor(message) {
    super(message);
    this.name = 'DomainError';
  }
}

// --------------------------------------------------------------------------
// Python-compatible rendering, so messages read the same as the validator's
// --------------------------------------------------------------------------

/** repr() of a Python str, list or None. */
export function pyRepr(value) {
  if (value === null || value === undefined) return 'None';
  if (Array.isArray(value)) return `[${value.map(pyRepr).join(', ')}]`;
  const s = String(value);
  if (s.includes("'") && !s.includes('"')) return `"${s.replace(/\\/g, '\\\\')}"`;
  return `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
}

/** str() of a Python float: whole values keep their '.0'. */
function pyFloat(value) {
  return Number.isInteger(value) ? value.toFixed(1) : String(value);
}

// --------------------------------------------------------------------------
// numbers
//
// SISQUAL writes decimals with a comma and quotes the field: "7,2".
// --------------------------------------------------------------------------

const NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

/** Parse a number written with either a dot or a comma decimal separator. */
export function tryNumber(text) {
  if (text === null || text === undefined) return null;
  let s = String(text).trim().replace(/ /g, '');
  if (!s) return null;
  if ((s.match(/,/g) || []).length === 1 && !s.includes('.')) s = s.replace(',', '.');
  return NUMBER.test(s) ? parseFloat(s) : null;
}

export function number(text) {
  const value = tryNumber(text);
  if (value === null) throw new DomainError(`not a number: ${pyRepr(text)}`);
  return value;
}

/** Render a number with a dot separator and no trailing .0 on whole values. */
export function formatNumber(value) {
  if (Number.isInteger(value)) return String(value);
  return String(Math.round(value * 1e6) / 1e6);
}

// --------------------------------------------------------------------------
// time
// --------------------------------------------------------------------------

const HHMM = /^([01]\d|2[0-3]):([0-5]\d)$/;

export function tryHhmmToMin(text) {
  const m = HHMM.exec(String(text ?? '').trim());
  if (!m) return null;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}

export function hhmmToMin(text) {
  const value = tryHhmmToMin(text);
  if (value === null) throw new DomainError(`not a HH:MM clock time: ${pyRepr(text)}`);
  return value;
}

export function minToHhmm(value) {
  const h = Math.floor(value / 60) % 24;
  const m = value % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/**
 * [startMin, endMin] for a window, or null if either boundary is malformed.
 * A window whose end <= start crosses midnight, and the roll-over is resolved
 * here into minutes past 1440 so no later reader has to infer it.
 */
export function tryParseRange(start, end) {
  const a = tryHhmmToMin(start);
  let b = tryHhmmToMin(end);
  if (a === null || b === null) return null;
  if (b <= a) b += MINUTES_PER_DAY;
  return [a, b];
}

export function parseRange(start, end) {
  const value = tryParseRange(start, end);
  if (value === null) {
    throw new DomainError(`not a HH:MM-HH:MM window: ${pyRepr(start)}-${pyRepr(end)}`);
  }
  return value;
}

export function onGrid(value, slotMinutes) {
  return slotMinutes > 0 && value % slotMinutes === 0;
}

/**
 * A schedule_input cell's hours as whole minutes, or null if it is not whole.
 * v4.0 cells are HOURS while contracts state minutes (next_meeting.md item 16).
 */
export function hoursToMinutes(hours) {
  const minutes = hours * 60;
  if (Math.abs(minutes - Math.round(minutes)) > 1e-6) return null;
  return Math.round(minutes);
}

/** A time interval in minutes from 00:00, end exclusive. */
export function interval(start, end) {
  return { start, end };
}

export function overlaps(a, b) {
  return a.start < b.end && b.start < a.end;
}

export function contains(a, b) {
  return a.start <= b.start && b.end <= a.end;
}

export function intervalToString(iv) {
  return `${minToHhmm(iv.start)}-${minToHhmm(iv.end)}`;
}

/** Merge overlapping *or touching* intervals into their union, ascending. */
export function coalesce(intervals) {
  const ordered = [...intervals].sort((a, b) => a.start - b.start || a.end - b.end);
  if (!ordered.length) return [];
  const merged = [{ ...ordered[0] }];
  for (const iv of ordered.slice(1)) {
    const last = merged[merged.length - 1];
    if (iv.start <= last.end) last.end = Math.max(last.end, iv.end);
    else merged.push({ ...iv });
  }
  return merged;
}

// --------------------------------------------------------------------------
// dates
// --------------------------------------------------------------------------

const DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const DAY_MS = 86400000;

function toUtc(isoDate) {
  const [, y, m, d] = DATE.exec(isoDate);
  return Date.UTC(+y, +m - 1, +d);
}

function fromUtc(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}

/**
 * The 'YYYY-MM-DD' date at the head of `text`, or null if it is not a date.
 * Tolerates a trailing time, because SISQUAL mixes three datetime spellings.
 */
export function iso(text) {
  if (typeof text !== 'string') return null;
  const head = text.trim().replace(/ /g, 'T').split('T')[0];
  if (!DATE.test(head)) return null;
  return fromUtc(toUtc(head)) === head ? head : null;
}

export function addDays(isoDate, n) {
  return fromUtc(toUtc(isoDate) + n * DAY_MS);
}

export function daysBetween(a, b) {
  return Math.round((toUtc(b) - toUtc(a)) / DAY_MS);
}

/** Monday = 0 ... Sunday = 6, as Python's date.weekday(). */
export function weekday(isoDate) {
  return (new Date(toUtc(isoDate)).getUTCDay() + 6) % 7;
}

export function weekdayName(isoDate) {
  return WEEKDAYS[weekday(isoDate)];
}

/** Every date in start..end inclusive, or [] if the range is unusable. */
export function dateRange(start, end) {
  const a = iso(start ?? '');
  const b = iso(end ?? '');
  if (!a || !b || b < a) return [];
  const out = [];
  for (let d = a; d <= b; d = addDays(d, 1)) out.push(d);
  return out;
}

/** Every date in the problem's temporalScope, inclusive. */
export function horizon(problem) {
  const scope = problem?.temporalScope || {};
  return dateRange(scope.start, scope.end);
}

/** Which week `day` falls in, counting from the week containing `origin`. */
export function weekIndex(day, origin, weekStart) {
  const startIdx = WEEKDAYS.indexOf(String(weekStart || 'monday').trim().toLowerCase());
  if (startIdx < 0) throw new DomainError(`${pyRepr(weekStart)} is not a weekday name`);
  const shift = (((weekday(origin) - startIdx) % 7) + 7) % 7;
  const week0 = addDays(origin, -shift);
  return Math.floor(daysBetween(week0, day) / 7);
}

/** Whether a {start, end|null} assignment covers `day`. Inclusive; null end is open. */
export function covers(entry, day) {
  const start = iso(entry?.start ?? '');
  if (!start || day < start) return false;
  const end = entry.end ? iso(entry.end) : null;
  return end === null || day <= end;
}

/** The contractType covering `day`, or null. */
export function activeContract(employee, day) {
  if (!day) return null;
  for (const entry of employee?.contractAssignments || []) {
    if (covers(entry, day)) return entry.contractType ?? null;
  }
  return null;
}

/** The competencyAssignments covering `day`. */
export function activeCompetencies(employee, day) {
  if (!day) return [];
  return (employee?.competencyAssignments || []).filter((e) => covers(e, day));
}

export function contractsById(problem) {
  const out = new Map();
  for (const c of problem?.contracts?.definitions || []) {
    if (c && 'id' in c) out.set(c.id, c);
  }
  return out;
}

/** One string key per (tableName, tableValue) coordinate. */
export function pairKey(tableName, tableValue) {
  return `${tableName}\u001f${tableValue}`;
}

/** The declared coordinates as pair keys. */
export function dimensionSet(problem) {
  const out = new Set();
  for (const d of problem?.demand?.dimensions || []) {
    if (d && 'tableName' in d && 'tableValue' in d) out.add(pairKey(d.tableName, d.tableValue));
  }
  return out;
}

/** {preferable, unavailable} code sets from scheduleInput.dayOffCodes. */
export function daySets(section) {
  const preferable = new Set();
  const unavailable = new Set();
  for (const [code, entry] of Object.entries(section?.dayOffCodes || {})) {
    if (entry?.kind === 'preferable') preferable.add(code);
    if (entry?.kind === 'unavailable') unavailable.add(code);
  }
  return { preferable, unavailable };
}

// --------------------------------------------------------------------------
// CSV reading
//
// SISQUAL's files are UTF-8 with a BOM and CRLF line endings; the templates
// carry '#' comment lines. All of it is tolerated here, once.
// --------------------------------------------------------------------------

/** CSV lines, skipping blank lines and '#' comments. */
export function csvLines(text) {
  const body = String(text ?? '').replace(/^\uFEFF/, '');
  return body.split(/\r\n|\n|\r/).filter((ln) => ln.trim() && !ln.trimStart().startsWith('#'));
}

/** {header, rows} from CSV text, BOM- and comment-tolerant, like csv.DictReader. */
export function readRows(text) {
  const lines = csvLines(text);
  if (!lines.length) return { header: [], rows: [] };
  const parsed = Papa.parse(lines.join('\n'), { delimiter: ',', header: false, skipEmptyLines: false });
  const [header = [], ...data] = parsed.data;
  const rows = data
    .filter((r) => r.length && !(r.length === 1 && r[0] === ''))
    .map((r) => {
      const row = {};
      header.forEach((name, i) => { row[name] = r[i] ?? ''; });
      return row;
    });
  return { header, rows };
}

export const DEMAND_COLUMNS = ['date', 'tableName', 'tableValue', 'minimum', 'ideal', 'estimated', 'start', 'end'];
export const SHIFTS_COLUMNS = ['date', 'workPeriod', 'tableName', 'tableValue', 'minimum', 'ideal', 'estimated', 'start', 'end'];
export const SCHEDULE_COLUMNS = ['code', 'description', 'scheduleWeightMinutes', 'startMin', 'endMin'];

/**
 * {header, rows, problems} for one demand CSV. `grain` is days | periods |
 * shifts and is always passed in, never sniffed: days and periods have
 * byte-identical headers. A malformed row is reported and skipped.
 */
export function readDemand(text, grain) {
  const { header, rows: raw } = readRows(text);
  const wanted = grain === 'shifts' ? SHIFTS_COLUMNS : DEMAND_COLUMNS;
  const problems = [];
  const missing = wanted.filter((c) => !header.includes(c));
  if (missing.length) {
    problems.push(`missing column(s) ${missing.join(', ')}; expected ${wanted.join(',')}`);
    return { header, rows: [], problems };
  }

  const rows = [];
  raw.forEach((r, i) => {
    const n = i + 2;
    const date = iso(r.date);
    if (!date) {
      problems.push(`row ${n}: bad date ${pyRepr(r.date)}`);
      return;
    }
    const values = ['minimum', 'ideal', 'estimated'].map((col) => {
      const v = tryNumber(r[col]);
      if (v === null) {
        problems.push(`row ${n}: ${col} is not a number (${pyRepr(r[col])})`);
        return 0;
      }
      return v;
    });
    let window = null;
    if (r.start || r.end) {
      const pair = tryParseRange(r.start, r.end);
      if (pair === null) problems.push(`row ${n}: bad window ${pyRepr(r.start)}-${pyRepr(r.end)}`);
      else window = interval(pair[0], pair[1]);
    }
    rows.push({
      date,
      tableName: r.tableName.trim(),
      tableValue: r.tableValue.trim(),
      minimum: values[0],
      ideal: values[1],
      estimated: values[2],
      window,
      workPeriod: (r.workPeriod ?? '').trim(),
      line: n,
      raw: r
    });
  });
  return { header, rows, problems };
}

/** {cells: Map<employeeId, {date: cell}>, dates, problems}. */
export function readScheduleInput(text) {
  const { header, rows: raw } = readRows(text);
  const problems = [];
  if (!header.length || header[0] !== 'employee_id') {
    const found = header.length ? header.slice(0, 1) : ['(nothing)'];
    problems.push(`first column must be 'employee_id', found ${pyRepr(found)}`);
    return { cells: new Map(), dates: [], problems };
  }
  const dates = header.slice(1);
  for (const col of dates) {
    if (!iso(col)) problems.push(`header column ${pyRepr(col)} is not a YYYY-MM-DD date`);
  }
  const cells = new Map();
  raw.forEach((r, i) => {
    const eid = r.employee_id.trim();
    if (cells.has(eid)) problems.push(`row ${i + 2}: employee ${eid} appears twice`);
    const row = {};
    for (const d of dates) row[d] = (r[d] || '').trim();
    cells.set(eid, row);
  });
  return { cells, dates, problems };
}

const INTEGER = /^\s*[+-]?\d+\s*$/;

/**
 * {catalogue: Map<code, schedule>, problems} from the ScheduleCode menu CSV.
 * A row with no window and zero weight is a rest sentinel.
 */
export function readSchedules(text) {
  const { header, rows: raw } = readRows(text);
  const problems = [];
  const missing = SCHEDULE_COLUMNS.filter((c) => !header.includes(c));
  if (missing.length) {
    problems.push(`missing column(s) ${missing.join(', ')}; expected ${SCHEDULE_COLUMNS.join(',')}`);
    return { catalogue: new Map(), problems };
  }
  const catalogue = new Map();
  raw.forEach((r, i) => {
    const n = i + 2;
    if (!INTEGER.test(r.code)) {
      problems.push(`row ${n}: code ${pyRepr(r.code)} is not an integer`);
      return;
    }
    const code = parseInt(r.code, 10);
    const weight = tryNumber(r.scheduleWeightMinutes);
    const start = tryNumber(r.startMin);
    const end = tryNumber(r.endMin);
    const iv = start !== null && end !== null ? interval(Math.trunc(start), Math.trunc(end)) : null;
    if (catalogue.has(code)) problems.push(`row ${n}: code ${code} appears twice`);
    const weightMinutes = Math.trunc(weight || 0);
    catalogue.set(code, {
      code,
      description: r.description.trim(),
      weightMinutes,
      interval: iv,
      isSentinel: iv === null && weightMinutes === 0
    });
  });
  return { catalogue, problems };
}

// --------------------------------------------------------------------------
// schedule_input cell grammar
// --------------------------------------------------------------------------

function parseWindows(spec) {
  const out = [];
  for (let part of spec.split(',')) {
    part = part.trim();
    if (!part.includes('-')) throw new DomainError(`window ${pyRepr(part)} is not HH:MM-HH:MM`);
    const cut = part.indexOf('-');
    const [a, b] = parseRange(part.slice(0, cut), part.slice(cut + 1));
    out.push(interval(a, b));
  }
  if (!out.length) throw new DomainError('operator carries no window');
  return coalesce(out);
}

/**
 * What one schedule_input cell asks for. Throws DomainError on anything it
 * will not guess at.
 *
 * kind: auto | exact_hours | equals | include | within | except | dayoff | empty
 *
 * A numeric cell is HOURS in v4.0; a value above 24 is almost certainly v3.0
 * minutes that were never converted.
 */
export function classifyCell(raw, problem) {
  const text = String(raw ?? '').trim();
  if (!text) return { kind: 'empty', raw };

  const upper = text.toUpperCase();
  for (const op of OPERATORS) {
    if (upper.startsWith(`${op}:`)) {
      return { kind: op.toLowerCase(), windows: parseWindows(text.slice(op.length + 1)), raw };
    }
  }

  if (upper === 'A') return { kind: 'auto', raw };

  const hours = tryNumber(text);
  if (hours !== null) {
    if (hours <= 0) throw new DomainError(`cell ${pyRepr(text)}: a working day of ${pyFloat(hours)} hours`);
    if (hours > 24) {
      throw new DomainError(
        `cell ${pyRepr(text)}: cells are HOURS in v4.0, and ${formatNumber(hours)} hours ` +
        'is longer than a day. A value this size is usually v3.0 minutes that were ' +
        'never converted - divide by 60.'
      );
    }
    const minutes = hoursToMinutes(hours);
    if (minutes === null) {
      throw new DomainError(`cell ${pyRepr(text)}: ${formatNumber(hours)} hours is not a whole number of minutes`);
    }
    return { kind: 'exact_hours', minutes, raw };
  }

  const { preferable, unavailable } = daySets(problem?.scheduleInput);
  if (preferable.has(text)) return { kind: 'dayoff', dayOff: 'preferable', code: text, raw };
  if (unavailable.has(text)) return { kind: 'dayoff', dayOff: 'unavailable', code: text, raw };
  throw new DomainError(
    `cell ${pyRepr(text)} is not a number, not an ${OPERATORS.join('/')} window, and is not ` +
    'declared in scheduleInput.dayOffCodes'
  );
}

/** classifyCell that returns {rule} or {error} instead of throwing — for the UI. */
export function tryClassifyCell(raw, problem) {
  try {
    return { rule: classifyCell(raw, problem), error: null };
  } catch (exc) {
    if (exc instanceof DomainError) return { rule: null, error: exc.message };
    throw exc;
  }
}

// --------------------------------------------------------------------------
// feasibility
// --------------------------------------------------------------------------

/**
 * Worker-days whose cell cannot be satisfied: [{employee, date, cell, reason}].
 * The single source of these, so the validator and the UI cannot disagree
 * about what is impossible. `scheduleInput` is a readScheduleInput() result.
 */
export function scanFeasibility(problem, scheduleInput) {
  if (!scheduleInput) return [];
  const { cells, dates } = scheduleInput;
  const contracts = contractsById(problem);
  const slot = problem?.timeGrid?.slotMinutes ?? 30;
  const out = [];
  const push = (employee, date, cell, reason) => out.push({ employee, date, cell, reason });

  for (const emp of problem?.employees?.list || []) {
    const eid = emp?.id ?? '';
    const row = cells.get(eid);
    if (!row) continue;
    for (const col of dates) {
      const day = iso(col);
      const raw = row[col] ?? '';
      let rule;
      try {
        rule = classifyCell(raw, problem);
      } catch (exc) {
        if (!(exc instanceof DomainError)) throw exc;
        push(eid, col, raw, exc.message);
        continue;
      }
      if (!ASKS_FOR_WORK.has(rule.kind)) continue;

      const contractId = activeContract(emp, day);
      if (contractId === null) {
        push(eid, col, raw, 'asks for work on a day no contract covers');
        continue;
      }
      const contract = contracts.get(contractId);
      if (!contract) {
        push(eid, col, raw, `contract ${pyRepr(contractId)} is not in contracts.definitions`);
        continue;
      }
      const wanted = contract.workMinutesPerDay;
      const duration = rule.kind === 'exact_hours' ? rule.minutes : wanted;
      if (duration !== undefined && duration !== null && !onGrid(duration, slot)) {
        push(eid, col, raw, `${duration} min is not a multiple of the ${slot}-minute grid`);
      }
      for (const win of rule.windows || []) {
        if (!onGrid(win.start, slot) || !onGrid(win.end, slot)) {
          push(eid, col, raw, `window ${intervalToString(win)} does not land on the ${slot}-minute grid`);
        }
      }
    }
  }
  return out;
}

export function diagnosticToString(d) {
  return `${d.employee} on ${d.date}: cell ${pyRepr(d.cell)} - ${d.reason}`;
}

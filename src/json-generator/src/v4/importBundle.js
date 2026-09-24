/**
 * A v4.0 input bundle -> wizard state.
 *
 * Accepts a problem.json plus the CSVs it names, resolved by base name, so a
 * ZIP with folders works as well as a flat file selection. SISQUAL's current
 * export and v3.0 files are refused rather than adapted: v4 ships no adapter,
 * and the differences are the agenda in json_generation/schema_v4/next_meeting.md.
 */

import JSZip from 'jszip';
import * as core from './core';
import { GRAINS } from './constants';
import { createInitialState, emptyWeeklyTemplate, newId, sentinelRows, STATE_VERSION } from './state';
import { validateBundle } from './validate';

const SISQUAL_DIALECT_HINT =
  "This looks like SISQUAL's current export or a v3.0 file, not a v4.0 problem. " +
  'v4 ships no adapter; the differences are listed in json_generation/schema_v4/next_meeting.md ' +
  'under "Naming and format".';

export class ImportError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ImportError';
  }
}

function baseName(path) {
  return String(path).split('/').pop();
}

/** Every file's text, keyed by base name, from a ZIP's bytes. Directories and macOS metadata are skipped. */
export async function readZip(data) {
  const zip = await JSZip.loadAsync(data);
  const out = {};
  const entries = Object.values(zip.files).filter((f) => !f.dir && !f.name.includes('__MACOSX/'));
  for (const entry of entries) out[baseName(entry.name)] = await entry.async('string');
  return out;
}

/** Every file's text, keyed by base name, from an <input type=file> selection (ZIPs are expanded). */
export async function readFileList(fileList) {
  const out = {};
  for (const file of Array.from(fileList)) {
    if (/\.zip$/i.test(file.name)) Object.assign(out, await readZip(await file.arrayBuffer()));
    else out[baseName(file.name)] = await file.text();
  }
  return out;
}

function stripComments(doc) {
  const out = {};
  for (const [k, v] of Object.entries(doc)) if (!k.startsWith('_comment')) out[k] = v;
  return out;
}

function lookup(files, name) {
  if (!name) return null;
  const text = files[name] ?? files[baseName(name)];
  return text === undefined ? null : text;
}

/** The one input problem among `files`, or an ImportError that says why not. */
export function locateProblem(files) {
  const candidates = [];
  let result = null;
  let dialect = null;
  for (const [name, text] of Object.entries(files)) {
    if (!/\.json$/i.test(name)) continue;
    let doc;
    try {
      doc = JSON.parse(String(text).replace(/^\uFEFF/, ''));
    } catch {
      continue;
    }
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) continue;
    if (doc.form === 'input') candidates.push({ name, doc });
    else if ('OutRosterTeamDays' in doc) result = name;
    else if (doc.schemaVersion === '3.0' || 'contractAssigments' in (doc.employees?.list?.[0] || {}) ||
      'priorityHierachy' in doc || doc.form === 'declarative') dialect = name;
  }
  if (candidates.length === 1) return candidates[0];
  if (candidates.length > 1) {
    throw new ImportError(`Several input problems were selected (${candidates.map((c) => c.name).join(', ')}); import one at a time.`);
  }
  if (dialect) throw new ImportError(`${dialect}: ${SISQUAL_DIALECT_HINT}`);
  if (result) throw new ImportError(`${result} is a result (OutRosterTeamDays), not a problem. The wizard authors problems only.`);
  throw new ImportError('No v4.0 problem found: expected a .json file with "form": "input".');
}

function demandRows(text, grain) {
  if (text === null) return [];
  return core.readDemand(text, grain).rows.map((r) => {
    const row = {
      id: newId(grain),
      date: r.date,
      tableName: r.tableName,
      tableValue: r.tableValue,
      minimum: r.minimum,
      ideal: r.ideal,
      estimated: r.estimated,
      start: (r.raw.start || '').trim(),
      end: (r.raw.end || '').trim()
    };
    if (grain === 'shifts') row.workPeriod = r.workPeriod;
    return row;
  });
}

function menuRows(text) {
  if (text === null) return null;
  return [...core.readSchedules(text).catalogue.values()].map((s) => ({
    code: s.code,
    description: s.description,
    scheduleWeightMinutes: s.weightMinutes,
    startMin: s.interval ? s.interval.start : null,
    endMin: s.interval ? s.interval.end : null
  }));
}

const KNOWN_KEYS = new Set(['schemaVersion', 'form', 'problemType', 'metadata', 'timeGrid', 'temporalScope',
  'calendar', 'contracts', 'employees', 'demand', 'scheduleInput', 'schedules', 'priorityHierarchy', 'constraints']);

/** A complete wizard state from a parsed v4.0 problem and the files it names. */
export function stateFromDocument(doc, files, problemName = 'problem.json') {
  const state = createInitialState();
  const clone = (v) => JSON.parse(JSON.stringify(v));

  state.metadata = {
    problemId: doc.metadata?.problemId ?? '',
    createdAt: doc.metadata?.createdAt ?? '',
    description: doc.metadata?.description ?? '',
    source: doc.metadata?.source ?? '',
    rosterCode: doc.metadata?.rosterCode ?? ''
  };
  state.timeGrid = { slotMinutes: doc.timeGrid?.slotMinutes ?? state.timeGrid.slotMinutes };
  state.temporalScope = { start: doc.temporalScope?.start ?? '', end: doc.temporalScope?.end ?? '' };
  state.calendar = {
    weekStart: doc.calendar?.weekStart ?? 'monday',
    holidays: clone(doc.calendar?.holidays || [])
  };
  state.contracts = { definitions: clone(doc.contracts?.definitions || []) };
  state.employees = { list: clone(doc.employees?.list || []) };

  const demand = doc.demand || {};
  const text = Object.fromEntries(GRAINS.map(({ grain, key }) => [grain, lookup(files, demand[key])]));
  state.demand = {
    dimensions: clone(demand.dimensions || []),
    days: demandRows(text.days, 'days'),
    periods: demandRows(text.periods, 'periods'),
    shifts: demandRows(text.shifts, 'shifts'),
    weeklyTemplate: emptyWeeklyTemplate()
  };

  const dataMatrix = {};
  const scheduleText = lookup(files, doc.scheduleInput?.dataFile);
  if (scheduleText !== null) {
    for (const [eid, row] of core.readScheduleInput(scheduleText).cells) dataMatrix[eid] = { ...row };
  }
  state.scheduleInput = { dayOffCodes: clone(doc.scheduleInput?.dayOffCodes || {}), dataMatrix };

  const menu = doc.schedules?.dataFile ? menuRows(lookup(files, doc.schedules.dataFile)) : null;
  state.schedules = menu ? { enabled: true, rows: menu } : { enabled: false, rows: sentinelRows() };

  state.priorityHierarchy = clone(doc.priorityHierarchy || []);
  state.constraints = { hard: clone(doc.constraints?.hard || []), soft: clone(doc.constraints?.soft || []) };

  state.files = {
    problem: baseName(problemName),
    days: demand.dataFileDays || state.files.days,
    periods: demand.dataFilePeriods || state.files.periods,
    shifts: demand.dataFileShifts || state.files.shifts,
    scheduleInput: doc.scheduleInput?.dataFile || state.files.scheduleInput,
    schedules: doc.schedules?.dataFile || state.files.schedules
  };
  state.stateVersion = STATE_VERSION;
  return state;
}

/**
 * Import a bundle: { state, report, notes }. Throws ImportError when there is
 * no v4.0 problem to import. `report` is the validator's verdict on the files
 * as they arrived, so the user sees what they are loading before it replaces
 * their work.
 */
export function importBundle(files) {
  const { name, doc: raw } = locateProblem(files);
  if (raw.schemaVersion !== '4.0') {
    throw new ImportError(`${name}: schemaVersion is ${JSON.stringify(raw.schemaVersion)}, not "4.0". ${SISQUAL_DIALECT_HINT}`);
  }
  const doc = stripComments(raw);
  const notes = [];
  const ignored = Object.keys(doc).filter((k) => !KNOWN_KEYS.has(k));
  if (ignored.length) notes.push(`Ignored keys v4.0 does not define: ${ignored.join(', ')}.`);
  for (const [label, fileName] of [
    ...GRAINS.map(({ key }) => [`demand.${key}`, doc.demand?.[key]]),
    ['scheduleInput.dataFile', doc.scheduleInput?.dataFile],
    ['schedules.dataFile', doc.schedules?.dataFile]
  ]) {
    if (fileName && lookup(files, fileName) === null) notes.push(`${label} names ${fileName}, which was not selected; it imports empty.`);
  }

  const state = stateFromDocument(doc, files, name);
  if (state.demand.periods.length) {
    notes.push('Periods demand was loaded as concrete dates; the weekly template starts empty.');
  }
  const report = validateBundle(doc, files);
  return { state, report, notes, problemName: name };
}

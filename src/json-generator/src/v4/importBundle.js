/**
 * A v4.0 package -> wizard state.
 *
 * JSON documents are told apart by content: a problem carries "form": "input",
 * a result carries OutRosterTeamDays. A CSV's role comes first from the name
 * the problem gives it (or, for a result's sidecar, `<stem>_schedules.csv`),
 * and its columns must agree; when the named file is missing or has another
 * file's columns, the one selected CSV whose columns fit that role is used
 * instead and written back under the problem's name. Files are matched by base
 * name, so two different files sharing one are refused rather than one
 * silently winning. SISQUAL's current export and v3.0 files are refused rather
 * than adapted: v4 ships no adapter, and the differences are the agenda in
 * json_generation/schema_v4/next_meeting.md.
 */

import JSZip from 'jszip';
import * as core from './core';
import { DEFAULT_TEAM_CODE, FILES, GRAINS } from './constants';
import { createInitialState, emptyWeeklyTemplate, newId, sentinelRows, STATE_VERSION } from './state';
import { validateBundle } from './validate';
import { mergeReports, validateResult } from './validateResult';

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

/** Where readZip and readFileList leave the names they read more than once, identically. */
export const COPIES = Symbol('copies');

/**
 * The package's files (.json and .csv; nothing else is read) keyed by base
 * name, remembering every path read under each. Two different files under one
 * name are refused: a package is one folder, and one of them would otherwise
 * silently replace the other.
 */
class FileSet {
  constructor() {
    this.files = {};
    this.paths = {};
  }

  add(path, text) {
    const name = baseName(path);
    if (!/\.(json|csv)$/i.test(name)) return;
    (this.paths[name] = this.paths[name] || []).push(path);
    if (!(name in this.files)) this.files[name] = text;
    else if (this.files[name] !== text) this.files[name] = FileSet.CLASH;
  }

  done() {
    const clashes = Object.keys(this.files).filter((n) => this.files[n] === FileSet.CLASH);
    if (clashes.length) {
      throw new ImportError(clashes.map((n) => `Two different files are named ${n} (${this.paths[n].join(', ')}).`).join(' ') +
        ' A package is one folder: import one package at a time.');
    }
    const copies = Object.entries(this.paths).filter(([, p]) => p.length > 1).map(([name, p]) => ({ name, paths: p }));
    Object.defineProperty(this.files, COPIES, { value: copies, enumerable: false });
    return this.files;
  }
}
FileSet.CLASH = Symbol('clash');

async function addZip(set, data, prefix = '') {
  const zip = await JSZip.loadAsync(data);
  const entries = Object.values(zip.files).filter((f) => !f.dir && !f.name.includes('__MACOSX/'));
  for (const entry of entries) set.add(`${prefix}${entry.name}`, await entry.async('string'));
}

/** Every file's text, keyed by base name, from a ZIP's bytes. Directories and macOS metadata are skipped. */
export async function readZip(data) {
  const set = new FileSet();
  await addZip(set, data);
  return set.done();
}

/** Every file's text, keyed by base name, from an <input type=file> selection (ZIPs are expanded). */
export async function readFileList(fileList) {
  const set = new FileSet();
  for (const file of Array.from(fileList)) {
    if (/\.zip$/i.test(file.name)) await addZip(set, await file.arrayBuffer(), `${file.name}/`);
    else set.add(file.name, await file.text());
  }
  return set.done();
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

/** Every JSON object among `files`, parsed: [{name, doc}]. Unparseable files are skipped. */
function jsonDocs(files) {
  const out = [];
  for (const [name, text] of Object.entries(files)) {
    if (!/\.json$/i.test(name)) continue;
    let doc;
    try {
      doc = JSON.parse(String(text).replace(/^\uFEFF/, ''));
    } catch {
      continue;
    }
    if (doc && typeof doc === 'object' && !Array.isArray(doc)) out.push({ name, doc });
  }
  return out;
}

// --------------------------------------------------------------------------
// what each CSV is, by its columns
// --------------------------------------------------------------------------

const KIND_LABEL = {
  menu: 'a shift menu',
  scheduleInput: 'a schedule input',
  shifts: 'shifts demand',
  demand: 'days or periods demand',
  unknown: 'none of the v4 CSVs'
};

/** What a CSV is, by its header: 'menu', 'scheduleInput', 'shifts', 'demand' (days or periods) or 'unknown'. */
export function csvKind(text) {
  const { header } = core.readRows(String(text ?? ''));
  const has = (columns) => columns.every((c) => header.includes(c));
  if (has(core.SCHEDULE_COLUMNS)) return 'menu';
  if (header[0] === 'employee_id') return 'scheduleInput';
  if (has(core.SHIFTS_COLUMNS)) return 'shifts';
  if (has(core.DEMAND_COLUMNS)) return 'demand';
  return 'unknown';
}

/** Days and periods share a header; periods rows carry windows. 'windows', 'noWindows' or 'empty'. */
export function demandShape(text) {
  const { rows } = core.readRows(String(text ?? ''));
  if (!rows.length) return 'empty';
  return rows.some((r) => (r.start || '').trim() || (r.end || '').trim()) ? 'windows' : 'noWindows';
}

/** The CSVs a package may hold, what each must look like, and where the problem names it. */
function packageRoles(doc, result) {
  const roles = [
    { role: 'days', label: 'demand.dataFileDays', what: 'days demand', kind: 'demand', shapes: ['noWindows', 'empty'], name: doc.demand?.dataFileDays },
    { role: 'periods', label: 'demand.dataFilePeriods', what: 'periods demand', kind: 'demand', shapes: ['windows', 'empty'], name: doc.demand?.dataFilePeriods },
    { role: 'shifts', label: 'demand.dataFileShifts', what: 'shifts demand', kind: 'shifts', name: doc.demand?.dataFileShifts },
    { role: 'scheduleInput', label: 'scheduleInput.dataFile', what: 'schedule input', kind: 'scheduleInput', name: doc.scheduleInput?.dataFile },
    // A problem may name no menu; one found by its columns is still taken, and written as schedules.csv.
    { role: 'schedules', label: 'schedules.dataFile', what: 'shift menu', kind: 'menu', name: doc.schedules?.dataFile }
  ];
  for (const r of roles) r.says = `${r.label} names ${r.name}`;
  if (result) {
    const name = core.sidecarName(result.name);
    roles.push({ role: 'sidecar', what: 'result sidecar', kind: 'menu', name, says: `${result.name}'s sidecar would be ${name}` });
  }
  return roles;
}

const listed = (names) => names.join(', ');

/**
 * Decide which selected CSV plays each role: {files, doc, notes, bound}.
 *
 * The file the problem names comes first, when its columns fit. Otherwise the
 * one unclaimed CSV whose columns fit the role is used, and noted; two
 * candidates, or one file two roles want, bind nothing. The problem's roles
 * choose before the result's sidecar. `files` holds every JSON plus each bound
 * CSV under the name it is written as, so the rest of the import - and the
 * validator - read it by the problem's names. `doc` names the menu when one was
 * found for a problem that named none. Leftover CSVs are noted by what they are.
 */
export function resolveFiles(doc, files, result = null) {
  const notes = [];
  const csvs = Object.keys(files).filter((n) => /\.csv$/i.test(n));
  const kind = new Map(csvs.map((n) => [n, csvKind(files[n])]));
  const roles = packageRoles(doc, result);
  const bound = new Map();       // role -> source file name
  const used = new Set();
  const wrong = new Map();        // role -> the named file, whose columns are another file's

  for (const r of roles) {
    const named = r.name ? csvs.find((n) => n === r.name || n === baseName(r.name)) : undefined;
    if (!named) continue;
    if (kind.get(named) === r.kind) {
      bound.set(r.role, named);
      used.add(named);
    } else {
      wrong.set(r.role, named);
    }
  }

  // Unclaimed files bind by their columns: the problem's roles first, then the sidecar.
  const open = (phase) => roles.filter((r) => !bound.has(r.role) && ((r.role === 'sidecar') === (phase === 'sidecar')));
  const ambiguous = new Map();    // role -> candidate names
  for (const phase of ['problem', 'sidecar']) {
    const waiting = open(phase);
    const candidates = new Map(waiting.map((r) => [r.role, csvs.filter((n) => !used.has(n) && kind.get(n) === r.kind &&
      (!r.shapes || r.shapes.includes(demandShape(files[n]))))]));
    const claims = new Map();
    for (const list of candidates.values()) for (const n of list) claims.set(n, (claims.get(n) || 0) + 1);
    for (const r of waiting) {
      const list = candidates.get(r.role);
      if (list.length === 1 && claims.get(list[0]) === 1) {
        bound.set(r.role, list[0]);
        used.add(list[0]);
      } else if (list.length > 1 || list.some((n) => claims.get(n) > 1)) {
        ambiguous.set(r.role, list);
      }
    }
  }

  const out = Object.fromEntries(Object.entries(files).filter(([n]) => /\.json$/i.test(n)));
  let resolvedDoc = doc;
  for (const r of roles) {
    const source = bound.get(r.role);
    const target = r.name || FILES.schedules;
    const bad = wrong.get(r.role);
    if (bad) notes.push(`${r.says}, but ${bad} reads as ${KIND_LABEL[kind.get(bad)]}, not as the ${r.what}.`);
    if (source && !r.name) {
      out[target] = files[source];
      resolvedDoc = { ...resolvedDoc, schedules: { dataFile: target } };
      notes.push(`The problem names no shift menu, but ${source} reads as one, so it was loaded as the menu (written back as ${target}).`);
    } else if (source) {
      out[target] = files[source];
      if (source === baseName(target)) continue;
      notes.push(`${bad ? '' : `${r.says}, which was not selected; `}${source} reads as the ${r.what}, so it was loaded in its place ` +
        `(written back as ${target}).`);
    } else if (ambiguous.has(r.role)) {
      notes.push(`${r.name ? `${r.says}, which ${bad ? 'reads as something else' : 'was not selected'}` : `The problem names no ${r.what}`}; ` +
        `${listed(ambiguous.get(r.role))} could each be the ${r.what}, so none was used.`);
    }
  }

  const stray = csvs.filter((n) => !used.has(n));
  if (stray.length) {
    notes.push(`Nothing refers to ${listed(stray.map((n) => `${n} (${KIND_LABEL[kind.get(n)]})`))}: the problem names its CSVs, and ` +
      `a result's sidecar is <stem>${core.SIDECAR_SUFFIX}. ${stray.length > 1 ? 'They were' : 'It was'} not imported.`);
  }
  return { files: out, doc: resolvedDoc, notes, bound };
}

const isResult = (doc) => doc.form !== 'input' && 'OutRosterTeamDays' in doc;

/** The one input problem among `files`, or an ImportError that says why not. */
export function locateProblem(files) {
  const docs = jsonDocs(files);
  const candidates = docs.filter(({ doc }) => doc.form === 'input');
  const result = docs.find(({ doc }) => isResult(doc));
  const dialect = docs.find(({ doc }) => doc.form !== 'input' && !isResult(doc) &&
    (doc.schemaVersion === '3.0' || 'contractAssigments' in (doc.employees?.list?.[0] || {}) ||
      'priorityHierachy' in doc || doc.form === 'declarative'));
  if (candidates.length === 1) return candidates[0];
  if (candidates.length > 1) {
    throw new ImportError(`A package carries one input problem, but ${candidates.length} were selected ` +
      `(${candidates.map((c) => c.name).join(', ')}); import one at a time.`);
  }
  if (dialect) throw new ImportError(`${dialect.name}: ${SISQUAL_DIALECT_HINT}`);
  if (result) {
    throw new ImportError(`${result.name} is a result (OutRosterTeamDays) with no input problem beside it. ` +
      'Select it together with the problem.json it answers, and that problem\'s CSVs.');
  }
  throw new ImportError('No v4.0 problem found: expected a .json file with "form": "input".');
}

/** The package's result, or null. Two results is an ImportError: each fixes days, so they would disagree. */
export function locateResult(files) {
  const results = jsonDocs(files).filter(({ doc }) => isResult(doc));
  if (results.length > 1) {
    throw new ImportError(`A package carries at most one result, but ${results.length} were selected ` +
      `(${results.map((r) => r.name).join(', ')}); each fixes days, so two would disagree about which stand.`);
  }
  return results[0] || null;
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

/** Two menu rows define a code the same way: description, weight and window - what the validator compares. */
function sameDefinition(a, b) {
  return a.description === b.description && Number(a.scheduleWeightMinutes) === Number(b.scheduleWeightMinutes) &&
    (a.startMin ?? null) === (b.startMin ?? null) && (a.endMin ?? null) === (b.endMin ?? null);
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

  // The menu switch starts on, as for a new problem: a bundle without a menu
  // gets the default rest codes, and the user may switch it off.
  const menu = doc.schedules?.dataFile ? menuRows(lookup(files, doc.schedules.dataFile)) : null;
  state.schedules = { enabled: true, rows: menu || sentinelRows() };

  state.priorityHierarchy = clone(doc.priorityHierarchy || []);
  state.constraints = { hard: clone(doc.constraints?.hard || []), soft: clone(doc.constraints?.soft || []) };

  state.files = {
    problem: baseName(problemName),
    days: demand.dataFileDays || state.files.days,
    periods: demand.dataFilePeriods || state.files.periods,
    shifts: demand.dataFileShifts || state.files.shifts,
    scheduleInput: doc.scheduleInput?.dataFile || state.files.scheduleInput,
    schedules: doc.schedules?.dataFile || state.files.schedules,
    result: state.files.result
  };
  state.stateVersion = STATE_VERSION;
  return state;
}

/** The TeamCode most entries carry, for the days the user fixes next. */
function commonTeamCode(entries) {
  const counts = new Map();
  for (const e of entries) if (typeof e?.TeamCode === 'string') counts.set(e.TeamCode, (counts.get(e.TeamCode) || 0) + 1);
  const [best] = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  return best ? best[0] : DEFAULT_TEAM_CODE;
}

/**
 * Load a result's entries into `state` as its fixed days, and say what changed
 * on the way: {notes, conflicts}. Integer EmployeeCodes become strings, and the
 * problem's rosterCode will be written on every entry. Codes only the sidecar
 * defines join the menu; `conflicts` are the codes the sidecar and the menu
 * define differently, which the user settles with applyMenuChoices.
 */
function loadResult(state, name, raw, files, { menuMissing }) {
  const notes = [];
  const doc = stripComments(raw);
  const { OutRosterTeamDays: list, ...extra } = doc;
  const entries = (Array.isArray(list) ? list : []).map((e) => {
    if (!e || typeof e !== 'object' || Array.isArray(e)) return e;
    const copy = JSON.parse(JSON.stringify(e));
    if (Number.isInteger(copy.EmployeeCode)) copy.EmployeeCode = String(copy.EmployeeCode);
    return copy;
  });
  const valid = entries.filter((e) => e && typeof e === 'object' && !Array.isArray(e));
  state.result = { teamCode: commonTeamCode(valid), entries: valid, ...(Object.keys(extra).length ? { extra } : {}) };
  state.files.result = baseName(name);
  if (valid.length < entries.length) notes.push(`${name}: ${entries.length - valid.length} entries are not objects; they were dropped.`);

  const ints = (Array.isArray(list) ? list : []).filter((e) => Number.isInteger(e?.EmployeeCode)).length;
  if (ints) notes.push(`${name}: EmployeeCode is an integer in ${ints} entries; they are written back as strings, like the problem's ids.`);
  const roster = state.metadata.rosterCode;
  const others = [...new Set(valid.map((e) => e.RosterCode).filter((c) => c !== roster))];
  if (roster && others.length) {
    notes.push(`${name}: RosterCode ${others.map((c) => JSON.stringify(c)).join(', ')} will be written as the problem's ${JSON.stringify(roster)}.`);
  }

  // No menu to define the codes, but the result's sidecar does: start the menu from it.
  const sidecarFile = core.sidecarName(name);
  const sidecar = lookup(files, sidecarFile);
  const conflicts = [];
  if (menuMissing && sidecar !== null) {
    const rows = menuRows(sidecar);
    const sentinels = sentinelRows().filter((s) => !rows.some((r) => r.code === s.code));
    state.schedules = { enabled: true, rows: [...sentinels, ...rows].sort((a, b) => a.code - b.code) };
    notes.push(`The menu starts from ${sidecarFile}, the codes ${name} used, since the problem brings none.`);
  } else if (sidecar !== null) {
    // Both define codes. Nothing either defines is dropped: a code only the sidecar
    // has joins the menu, and a code the two define differently waits for the user.
    const mine = new Map(state.schedules.rows.map((r) => [Number(r.code), r]));
    const added = [];
    for (const row of menuRows(sidecar)) {
      const own = mine.get(row.code);
      if (!own) added.push(row);
      else if (!sameDefinition(own, row)) {
        conflicts.push({ code: row.code, menu: own, result: row, fixedDays: valid.filter((e) => e.ScheduleCode === row.code).length });
      }
    }
    const menuFile = state.files.schedules;
    if (added.length) {
      state.schedules = { ...state.schedules, rows: [...state.schedules.rows, ...added] };
      notes.push(`${sidecarFile} defines ScheduleCode ${listed(added.map((r) => r.code))}, which ${menuFile} does not; ` +
        `${added.length > 1 ? 'they were' : 'it was'} added to the menu, so nothing ${name} uses is lost.`);
    }
    if (conflicts.length) {
      notes.push(`${sidecarFile} and ${menuFile} define ScheduleCode ${listed(conflicts.map((c) => c.code))} differently; ` +
        'choose which definition to keep for each.');
    }
  }
  const menu = new Set(state.schedules.rows.map((r) => Number(r.code)));
  const unknown = [...new Set(valid.map((e) => e.ScheduleCode).filter((c) => !menu.has(c)))];
  if (unknown.length) {
    notes.push(`${name} uses ScheduleCode ${unknown.sort((a, b) => a - b).join(', ')}, which the menu does not define; ` +
      'add them in Shift Menu or change those days in Fixed days.');
  }
  return { notes, conflicts };
}

/**
 * Import a package: { state, report, notes, conflicts, problemName, resultName }.
 * Throws ImportError when there is no v4.0 problem to import, or more than one
 * problem or result. `report` is the validator's verdict on the files as they
 * will be loaded - each CSV in the role resolveFiles gave it - the problem's
 * findings, then the result's, so the user sees what they are loading before it
 * replaces their work. `notes` say what happened to every file. `conflicts` are
 * the codes the menu and the result's sidecar define differently
 * [{code, menu, result, fixedDays}]: `state` holds the menu's definitions until
 * the user's choices are applied with applyMenuChoices.
 */
export function importBundle(selected) {
  const { name, doc: raw } = locateProblem(selected);
  const found = locateResult(selected);
  if (raw.schemaVersion !== '4.0') {
    throw new ImportError(`${name}: schemaVersion is ${JSON.stringify(raw.schemaVersion)}, not "4.0". ${SISQUAL_DIALECT_HINT}`);
  }
  const notes = [];
  for (const { name: copy, paths } of selected[COPIES] || []) {
    notes.push(`${copy} was selected ${paths.length} times (${listed(paths)}) with the same content; it was read once.`);
  }
  const ignored = Object.keys(stripComments(raw)).filter((k) => !KNOWN_KEYS.has(k));
  if (ignored.length) notes.push(`Ignored keys v4.0 does not define: ${ignored.join(', ')}.`);
  const known = new Set([name, found?.name]);
  for (const other of Object.keys(selected).filter((n) => /\.json$/i.test(n) && !known.has(n))) {
    notes.push(`${other} is neither a v4.0 problem nor a result; it was not imported.`);
  }

  const resolved = resolveFiles(stripComments(raw), selected, found);
  const { files, doc } = resolved;
  notes.push(...resolved.notes);
  const fate = (fileName) => (lookup(selected, fileName) === null ? 'was not selected' : 'was not loaded');
  for (const [role, label, fileName] of [
    ...GRAINS.map(({ grain, key }) => [grain, `demand.${key}`, doc.demand?.[key]]),
    ['scheduleInput', 'scheduleInput.dataFile', doc.scheduleInput?.dataFile]
  ]) {
    if (fileName && !resolved.bound.has(role)) notes.push(`${label} names ${fileName}, which ${fate(fileName)}; it imports empty.`);
  }
  const menuFile = doc.schedules?.dataFile;
  const menuMissing = !resolved.bound.has('schedules');
  const seeded = menuMissing && resolved.bound.has('sidecar');
  if (!seeded && !menuFile) {
    notes.push('The problem has no shift menu; the wizard starts one with the default rest codes (switch it off in Shift Menu to omit schedules.csv).');
  } else if (!seeded && menuMissing) {
    notes.push(`schedules.dataFile names ${menuFile}, which ${fate(menuFile)}; the menu starts with the default rest codes.`);
  }

  const state = stateFromDocument(doc, files, name);
  if (state.demand.periods.length) {
    notes.push('Periods demand was loaded as concrete dates; the weekly template starts empty.');
  }
  let conflicts = [];
  if (found) {
    const loaded = loadResult(state, found.name, found.doc, files, { menuMissing });
    notes.push(...loaded.notes);
    conflicts = loaded.conflicts;
  }

  const report = mergeReports(validateBundle(doc, files), found && validateResult(found.doc, {
    problem: doc, files, resultName: found.name, problemName: name
  }));
  if (found) {
    const { rosterDays, rosterDaysLeft } = report.stats;
    notes.unshift(`${found.name}: ${rosterDays} fixed days, ${rosterDaysLeft} left open for the solver.`);
  }
  return { state, report, notes, conflicts, problemName: name, resultName: found?.name ?? null };
}

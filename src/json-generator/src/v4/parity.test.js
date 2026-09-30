// @vitest-environment node
/**
 * Parity with the Python validator, and the import -> generate round trip,
 * against the packages shipped in json_generation/schema_v4. The expected
 * findings are the Python validator's own output
 * (`python -m schema_v4.validator <dir> -v`, captured 2026-09-23).
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateBundle } from './validate';
import JSZip from 'jszip';
import { importBundle, locateProblem, readFileList, readZip } from './importBundle';
import { buildBundle, bundleEntries } from './generate';
import { csvLines } from './core';
import { schemaFindings } from './schema';
import { validateResult } from './validateResult';
import { applyMenuChoices } from './operations';

const V4 = fileURLToPath(new URL('../../../../json_generation/schema_v4/', import.meta.url));
const TEMPLATES = path.join(V4, 'templates');
const C2 = path.join(V4, 'examples', 'cenario2_retail');
const C2_PARTIAL = path.join(V4, 'examples', 'cenario2_partial');
const C2_INPUT_ONLY = path.join(V4, 'examples', 'cenario2_input_only');

/** Every .json and .csv in a package directory, keyed by file name. */
function readDir(dir) {
  const out = {};
  for (const name of fs.readdirSync(dir)) {
    if (/\.(json|csv)$/.test(name)) out[name] = fs.readFileSync(path.join(dir, name), 'utf-8');
  }
  return out;
}

function validateDir(dir, mutate) {
  const files = readDir(dir);
  const { name, doc } = locateProblem(files);
  if (mutate) mutate(doc, files, name);
  return validateBundle(doc, files);
}

const messages = (findings) => findings.map((f) => f.message);

const C2_WARNINGS = [
  ['20067009', 1, 3], ['20054956', 2, 4], ['20062688', 3, 4]
].flatMap(([eid, a, b]) => ['Team/T1', 'Responsibility/A', 'Responsibility/C', 'Responsibility/G'].map((pair) =>
  `employee ${eid}: holds ${pair} over overlapping dates (2026-01-01..2026-01-31 and ` +
  `2026-01-01..2026-01-31) with levels ${a} and ${b} at once, so its competence level is ` +
  `ambiguous; take ${a}, the higher competence`
)).concat(["dayOffCodes declares 'NOT', which no cell uses"]);

describe('parity with the Python validator', () => {
  it('finds the templates package clean', () => {
    const r = validateDir(TEMPLATES);
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual([]);
    expect(r.stats).toMatchObject({
      days: 7, contracts: 2, employees: 4, dimensions: 2,
      'demandRows.days': 5, 'demandRows.periods': 18, 'demandRows.shifts': 4,
      priorityRanks: 2, schedules: 6, diagnostics: 0, negative_n_wk: 0, openDays: 7
    });
  });

  it('reports exactly the 13 known warnings on cenario2_retail', () => {
    const r = validateDir(C2);
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual(C2_WARNINGS);
    expect(r.stats).toMatchObject({
      days: 31, contracts: 6, employees: 15, dimensions: 4,
      'demandRows.days': 0, 'demandRows.periods': 313, 'demandRows.shifts': 0,
      priorityRanks: 4, schedules: 22, diagnostics: 0, negative_n_wk: 0, openDays: 31
    });
  });

  it('tags every finding with the step that owns the fix', () => {
    const r = validateDir(C2);
    expect(new Set(r.warnings.map((w) => w.step))).toEqual(new Set(['employees', 'scheduleInput']));
  });
});

/**
 * One broken thing per case, appended to the clean templates package — the
 * JS twin of tests/test_validator_input.py.
 */
describe('one finding per broken fixture', () => {
  const addDemand = (row) => (doc, files) => {
    files['periods_demand_template.csv'] += `${row}\n`;
  };
  const setCell = (emp, date, value) => (doc, files) => {
    const lines = csvLines(files['schedule_input_template.csv']);
    const header = lines[0].split(',');
    const col = header.indexOf(date);
    files['schedule_input_template.csv'] = lines.map((line) => {
      const cells = line.split(',');
      if (cells[0] === emp) cells[col] = value;
      return cells.join(',');
    }).join('\n') + '\n';
  };

  it.each([
    ['2026-03-02,Floor,T1,1,0,0,17:00,21:00', 'Floor/T1 is not in demand.dimensions', true],
    ['2026-03-02,Team,T1,1,0,0,,', 'start/end are mandatory', true],
    ['2026-03-02,Team,T1,1,0,0,17:10,21:00', 'does not land on the 30-minute grid', true],
    ['2026-04-02,Team,T1,1,0,0,09:00,13:00', 'lies outside temporalScope', true],
    ['2026-03-02,Team,T1,-1,0,0,17:00,21:00', 'minimum is negative', true],
    ['2026-03-02,Team,T1,1,0,0,09:00,13:00', 'duplicate row', true],
    ['2026-03-02,Team,T1,1,0,0,12:00,13:00', 'counts toward both', false]
  ])('reports the demand row %s', (row, needle, wantError) => {
    const r = validateDir(TEMPLATES, addDemand(row));
    const pool = messages(wantError ? r.errors : r.warnings);
    expect(pool.filter((m) => m.includes(needle))).toHaveLength(1);
  });

  it('enforces no ordering between minimum, ideal and estimated', () => {
    const r = validateDir(TEMPLATES, addDemand('2026-03-02,Team,T1,3,1,2,17:00,21:00'));
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings).some((m) => m.includes('ideal') || m.includes('estimated'))).toBe(false);
  });

  it('reports a missing demand file once', () => {
    const r = validateDir(TEMPLATES, (doc) => { doc.demand.dataFileDays = 'absent.csv'; });
    expect(messages(r.errors)).toEqual(['demand.dataFileDays: file not found: absent.csv']);
  });

  it('rejects a v3 minute cell exactly once', () => {
    const r = validateDir(TEMPLATES, setCell('EMP001', '2026-03-02', '480'));
    expect(r.errors).toHaveLength(1);
    expect(r.errors[0].message).toContain('never converted');
  });

  it('rejects an undeclared cell code', () => {
    const r = validateDir(TEMPLATES, setCell('EMP001', '2026-03-02', 'FDO'));
    expect(messages(r.errors).filter((m) => m.includes('not declared in scheduleInput.dayOffCodes'))).toHaveLength(1);
  });

  it('warns, not errors, on hours that contradict the contract', () => {
    const r = validateDir(TEMPLATES, setCell('EMP001', '2026-03-02', '6'));
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual([
      "schedule_input_template.csv: EMP001 on 2026-03-02: cell '6' is 360 min but contract FT_8h states 480"
    ]);
  });

  it('reports a schedule_input with the wrong number of columns', () => {
    const r = validateDir(TEMPLATES, (doc) => { doc.temporalScope.end = '2026-03-09'; });
    expect(messages(r.errors).some((m) => m.includes('date columns but temporalScope spans'))).toBe(true);
  });

  it('errors on a contract off the grid (Scenario 1)', () => {
    const r = validateDir(TEMPLATES, (doc) => { doc.contracts.definitions[0].workMinutesPerDay = 432; });
    expect(messages(r.errors)[0]).toBe('contract FT_8h: workMinutesPerDay 432 is not a multiple of the 30-minute grid');
  });

  it('errors on an empty dimensions catalogue', () => {
    const r = validateDir(TEMPLATES, (doc) => { doc.demand.dimensions = []; });
    expect(messages(r.errors).some((m) => m.startsWith('demand.dimensions is empty'))).toBe(true);
  });

  it('enforces the labour-law caps', () => {
    const r = validateDir(TEMPLATES, (doc) => {
      doc.constraints.hard[0].parameters.MaxConsecutiveWorkDaysInWeek = 4;
    });
    expect(messages(r.errors).some((m) => m.includes('exceeds MaxConsecutiveWorkDaysInWeek of 4'))).toBe(true);
  });

  it('flags a v3.0 document at the schema and version layers', () => {
    const r = validateDir(TEMPLATES, (doc) => { doc.schemaVersion = '3.0'; });
    expect(messages(r.errors).some((m) => m.startsWith("schemaVersion is '3.0'"))).toBe(true);
  });
});

describe('the JSON Schema layer', () => {
  it.each(['schema-v4-input.json', 'schema-v4-result.json'])('uses a vendored %s identical to the canonical one', (name) => {
    const vendored = fs.readFileSync(fileURLToPath(new URL(`../../schema_v4/${name}`, import.meta.url)), 'utf-8');
    const canonical = fs.readFileSync(path.join(V4, 'schemas', name), 'utf-8');
    expect(vendored).toBe(canonical);
  });

  it('names the key a v2.6 leftover would add', () => {
    const { doc } = locateProblem(readDir(TEMPLATES));
    doc.scheduleInput.enabled = true;
    expect(schemaFindings(doc)).toEqual([{
      message: "schema: scheduleInput: additional property 'enabled' is not allowed",
      step: 'scheduleInput'
    }]);
  });
});

/** CSV text as the generator would write it: no comments, no blank lines, LF. */
function normalised(text) {
  return `${csvLines(text).join('\n')}\n`;
}

function stripComments(doc) {
  return JSON.parse(JSON.stringify(doc, (k, v) => (k.startsWith('_comment') ? undefined : v)));
}

describe('import -> generate round trip', () => {
  it.each([['templates', TEMPLATES], ['cenario2_retail', C2], ['cenario2_partial', C2_PARTIAL]])('reproduces %s', (label, dir) => {
    const files = readDir(dir);
    const { state, report, resultName } = importBundle(files);
    expect(messages(report.errors)).toEqual([]);

    const bundle = buildBundle(state);
    const original = stripComments(locateProblem(files).doc);
    expect(bundle.problem).toEqual(original);
    expect(bundle.resultName).toBe(resultName);
    expect(bundle.result).toEqual(stripComments(JSON.parse(files[resultName])));

    for (const [name, text] of Object.entries(bundle.files)) {
      expect(text, name).toBe(normalised(files[name]));
    }
    expect(Object.keys(bundle.files).sort()).toEqual(Object.keys(files).filter((n) => n.endsWith('.csv')).sort());
  });

  it('keeps a partial result partial', () => {
    const { state, notes } = importBundle(readDir(C2_PARTIAL));
    expect(notes[0]).toBe('result.json: 105 fixed days, 360 left open for the solver.');
    expect(state.result.entries).toHaveLength(105);
    expect(state.result.teamCode).toBe('1');
    const r = validateResult(buildBundle(state).result, {
      problem: buildBundle(state).problem, files: buildBundle(state).files, resultName: 'result.json'
    });
    expect(r.stats).toMatchObject({ rosterDays: 105, rosterDaysExpected: 465, rosterDaysLeft: 360, sidecarCodes: 11 });
  });

  it('generates a bundle that validates the same as the original', () => {
    const { state } = importBundle(readDir(C2));
    const bundle = buildBundle(state);
    const r = validateBundle(bundle.problem, bundle.files);
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual(C2_WARNINGS);
    expect(bundleEntries(bundle).map(([n]) => n)).toEqual([
      'problem.json', 'result.json', 'days_demand.csv', 'periods_demand.csv', 'shifts_demand.csv',
      'schedule_input.csv', 'schedules.csv', 'result_schedules.csv'
    ]);
  });

  it('refuses SISQUAL\'s current export with a pointer to the agenda', () => {
    const files = { 'demo.json': JSON.stringify({ schemaVersion: '3.0', form: 'declarative', priorityHierachy: [] }) };
    expect(() => importBundle(files)).toThrow(/next_meeting.md/);
  });

  it('starts the menu switch on when the bundle has no menu', () => {
    const files = readDir(TEMPLATES);
    const { name, doc } = locateProblem(files);
    delete doc.schedules;
    files[name] = JSON.stringify(doc);
    delete files['schedules_template.csv'];
    delete files['result_template.json'];
    delete files['result_template_schedules.csv'];
    const { state, notes } = importBundle(files);
    expect(state.schedules.enabled).toBe(true);
    expect(state.schedules.rows.map((r) => `${r.code} ${r.description}`)).toEqual(['1 Space', '3 Day off', '4 Empty']);
    expect(notes.some((n) => n.includes('no shift menu'))).toBe(true);
  });

  it('refuses a result with no problem beside it', () => {
    const files = { 'result.json': JSON.stringify({ OutRosterTeamDays: [] }) };
    expect(() => importBundle(files)).toThrow(/is a result \(OutRosterTeamDays\) with no input problem beside it/);
  });

  it('refuses two results, as the package rule does', () => {
    const files = readDir(TEMPLATES);
    files['other.json'] = files['result_template.json'];
    expect(() => importBundle(files)).toThrow(/at most one result, but 2 were selected \(result_template.json, other.json\)/);
  });

  it('starts the menu from the result\'s sidecar when the problem has none', () => {
    const files = readDir(TEMPLATES);
    const { name, doc } = locateProblem(files);
    delete doc.schedules;
    files[name] = JSON.stringify(doc);
    delete files['schedules_template.csv'];
    const { state, notes } = importBundle(files);
    expect(state.schedules.rows.map((r) => r.code)).toEqual([1, 3, 4, 9001, 9002, 9003]);
    expect(notes).toContain('The menu starts from result_template_schedules.csv, the codes result_template.json used, since the problem brings none.');
    expect(notes.some((n) => n.includes('default rest codes'))).toBe(false);
    expect(messages(validateResultOf(state).errors)).toEqual([]);
  });

  it('writes integer EmployeeCodes back as strings, and says so', () => {
    const files = readDir(C2_PARTIAL);
    const result = JSON.parse(files['result.json']);
    result.OutRosterTeamDays[0].EmployeeCode = 20072412;
    files['result.json'] = JSON.stringify(result);
    const { state, notes, report } = importBundle(files);
    expect(state.result.entries[0].EmployeeCode).toBe('20072412');
    expect(notes).toContain("result.json: EmployeeCode is an integer in 1 entries; they are written back as strings, like the problem's ids.");
    expect(messages(report.warnings).some((m) => m.startsWith('EmployeeCode is an integer in 1 of 105 entries'))).toBe(true);
    expect(messages(validateResultOf(state).warnings).some((m) => m.startsWith('EmployeeCode is an integer'))).toBe(false);
  });

  it('says which CSVs nothing refers to', () => {
    const files = { ...readDir(C2_INPUT_ONLY), 'stray.csv': 'a,b\n' };
    const { notes, resultName } = importBundle(files);
    expect(resultName).toBeNull();
    expect(notes.some((n) => n.startsWith('Nothing refers to stray.csv'))).toBe(true);
  });
});

describe('which file is which', () => {
  /** The templates package, with its result unless `result` is false, after `mutate(files)`. */
  function templates(mutate, { result = true } = {}) {
    const files = readDir(TEMPLATES);
    if (!result) {
      delete files['result_template.json'];
      delete files['result_template_schedules.csv'];
    }
    mutate(files);
    return files;
  }
  const rename = (files, from, to) => {
    files[to] = files[from];
    delete files[from];
  };
  const original = importBundle(readDir(TEMPLATES)).state;
  const MENU = 'code,description,scheduleWeightMinutes,startMin,endMin\n';

  it('refuses two different files under one name, from different folders', async () => {
    const zip = new JSZip();
    zip.file('pkgA/schedules.csv', `${MENU}3,Day off,0,,\n`);
    zip.file('pkgB/schedules.csv', `${MENU}1,Space,0,,\n`);
    zip.file('pkgA/README.md', 'one');
    zip.file('pkgB/README.md', 'two');   // not a package file, so not a clash
    await expect(readZip(await zip.generateAsync({ type: 'uint8array' }))).rejects.toThrow(
      'Two different files are named schedules.csv (pkgA/schedules.csv, pkgB/schedules.csv). ' +
      'A package is one folder: import one package at a time.');
  });

  it('refuses two problems that share a name, before either is read', async () => {
    const zip = new JSZip();
    const problem = readDir(TEMPLATES)['problem_template.json'];
    zip.file('a/problem.json', problem);
    zip.file('b/problem.json', problem.replace('"4.0"', '"4.0" '));
    await expect(readZip(await zip.generateAsync({ type: 'uint8array' }))).rejects.toThrow(/Two different files are named problem.json/);
  });

  it('refuses a ZIP and a loose file that disagree, and reads identical copies once', async () => {
    const zip = new JSZip();
    zip.file('pkg/schedules.csv', `${MENU}3,Day off,0,,\n`);
    const bytes = await zip.generateAsync({ type: 'uint8array' });
    await expect(readFileList([new File([bytes], 'bundle.zip'), new File([`${MENU}1,Space,0,,\n`], 'schedules.csv')]))
      .rejects.toThrow('Two different files are named schedules.csv (bundle.zip/pkg/schedules.csv, schedules.csv).');

    const all = new JSZip();
    for (const [n, text] of Object.entries(readDir(TEMPLATES))) all.file(`a/${n}`, text);
    all.file('b/schedules_template.csv', readDir(TEMPLATES)['schedules_template.csv']);
    const files = await readZip(await all.generateAsync({ type: 'uint8array' }));
    const { notes, report } = importBundle(files);
    expect(notes).toContain('schedules_template.csv was selected 2 times (a/schedules_template.csv, ' +
      'b/schedules_template.csv) with the same content; it was read once.');
    expect(messages(report.errors)).toEqual([]);
  });

  it('loads a menu under another name by its columns', () => {
    const { state, notes, report } = importBundle(templates((f) => rename(f, 'schedules_template.csv', 'menu_v2.csv')));
    expect(state.schedules.rows).toEqual(original.schedules.rows);
    expect(notes).toContain('schedules.dataFile names schedules_template.csv, which was not selected; menu_v2.csv reads as ' +
      'the shift menu, so it was loaded in its place (written back as schedules_template.csv).');
    expect(notes.some((n) => n.startsWith('Nothing refers to'))).toBe(false);
    expect(messages(report.errors)).toEqual([]);
    expect(messages(report.warnings)).toEqual([]);
  });

  it('puts swapped files back in their roles', () => {
    const files = readDir(TEMPLATES);
    const swapped = templates((f) => {
      f['schedules_template.csv'] = files['schedule_input_template.csv'];
      f['schedule_input_template.csv'] = files['schedules_template.csv'];
    });
    const { state, notes, report } = importBundle(swapped);
    expect(notes).toEqual(expect.arrayContaining([
      'scheduleInput.dataFile names schedule_input_template.csv, but schedule_input_template.csv reads as a shift menu, not as the schedule input.',
      'schedules_template.csv reads as the schedule input, so it was loaded in its place (written back as schedule_input_template.csv).',
      'schedules.dataFile names schedules_template.csv, but schedules_template.csv reads as a schedule input, not as the shift menu.',
      'schedule_input_template.csv reads as the shift menu, so it was loaded in its place (written back as schedules_template.csv).'
    ]));
    expect(messages(report.errors)).toEqual([]);
    const bundle = buildBundle(state);
    for (const name of ['schedules_template.csv', 'schedule_input_template.csv']) {
      expect(bundle.files[name], name).toBe(normalised(files[name]));
    }
  });

  it('tells days from periods by their windows', () => {
    const { state, notes, report } = importBundle(templates((f) => {
      rename(f, 'days_demand_template.csv', 'a.csv');
      rename(f, 'periods_demand_template.csv', 'b.csv');
    }));
    expect(state.demand.days.map((r) => r.date)).toEqual(original.demand.days.map((r) => r.date));
    expect(state.demand.periods).toHaveLength(original.demand.periods.length);
    expect(notes).toEqual(expect.arrayContaining([
      'demand.dataFileDays names days_demand_template.csv, which was not selected; a.csv reads as the days demand, so it was ' +
        'loaded in its place (written back as days_demand_template.csv).',
      'demand.dataFilePeriods names periods_demand_template.csv, which was not selected; b.csv reads as the periods demand, so ' +
        'it was loaded in its place (written back as periods_demand_template.csv).'
    ]));
    expect(messages(report.errors)).toEqual([]);
  });

  it('binds nothing when two files could fill one role', () => {
    const { state, notes } = importBundle(templates((f) => {
      f['m1.csv'] = f['schedules_template.csv'];
      rename(f, 'schedules_template.csv', 'm2.csv');
    }, { result: false }));
    expect(state.schedules.rows.map((r) => r.code)).toEqual([1, 3, 4]);
    expect(notes).toEqual(expect.arrayContaining([
      'schedules.dataFile names schedules_template.csv, which was not selected; m1.csv, m2.csv could each be the shift menu, so none was used.',
      'Nothing refers to m1.csv (a shift menu), m2.csv (a shift menu): the problem names its CSVs, and a result\'s sidecar is ' +
        '<stem>_schedules.csv. They were not imported.',
      'schedules.dataFile names schedules_template.csv, which was not selected; the menu starts with the default rest codes.'
    ]));
  });

  it('finds a renamed sidecar by its columns', () => {
    const { notes, report } = importBundle(templates((f) => rename(f, 'result_template_schedules.csv', 'codes.csv')));
    expect(notes).toContain('result_template.json\'s sidecar would be result_template_schedules.csv, which was not selected; ' +
      'codes.csv reads as the result sidecar, so it was loaded in its place (written back as result_template_schedules.csv).');
    expect(messages(report.errors)).toEqual([]);
    expect(messages(report.warnings)).toEqual([]);
  });

  it('loads a menu the problem forgot to name', () => {
    const files = templates(() => {}, { result: false });
    const { name, doc } = locateProblem(files);
    delete doc.schedules;
    files[name] = JSON.stringify(doc);
    const { state, notes } = importBundle(files);
    expect(state.schedules.rows).toEqual(original.schedules.rows);
    expect(buildBundle(state).problem.schedules).toEqual({ dataFile: 'schedules.csv' });
    expect(notes).toContain('The problem names no shift menu, but schedules_template.csv reads as one, so it was loaded ' +
      'as the menu (written back as schedules.csv).');
    expect(notes.some((n) => n.includes('default rest codes'))).toBe(false);
  });

  it('adds the codes only the result\'s sidecar defines to the menu', () => {
    const { state, notes, conflicts } = importBundle(templates((f) => {
      f['result_template_schedules.csv'] += '9100,10:00-14:00,240,600,840\n';
      const result = JSON.parse(f['result_template.json']);
      result.OutRosterTeamDays.find((e) => e.ScheduleCode === 9001).ScheduleCode = 9100;
      f['result_template.json'] = JSON.stringify(result);
    }));
    expect(conflicts).toEqual([]);
    expect(state.schedules.rows.slice(0, -1)).toEqual(original.schedules.rows);
    expect(state.schedules.rows.at(-1)).toEqual({ code: 9100, description: '10:00-14:00', scheduleWeightMinutes: 240, startMin: 600, endMin: 840 });
    expect(notes).toContain('result_template_schedules.csv defines ScheduleCode 9100, which schedules_template.csv does not; ' +
      'it was added to the menu, so nothing result_template.json uses is lost.');
    const bundle = buildBundle(state);
    expect(bundle.files['schedules_template.csv']).toContain('\n9100,10:00-14:00,240,600,840\n');
    expect(bundle.files['result_template_schedules.csv']).toContain('\n9100,10:00-14:00,240,600,840\n');
  });

  describe('a code the menu and the sidecar define differently', () => {
    const files = templates((f) => {
      f['result_template_schedules.csv'] = f['result_template_schedules.csv']
        .replace('9001,09:00-13:00,240,540,780', '9001,10:00-14:00,240,600,840');
    });
    const imported = importBundle(files);
    const menuRow = { code: 9001, description: '09:00-13:00', scheduleWeightMinutes: 240, startMin: 540, endMin: 780 };
    const resultRow = { code: 9001, description: '10:00-14:00', scheduleWeightMinutes: 240, startMin: 600, endMin: 840 };
    const row = (st, code) => st.schedules.rows.find((r) => r.code === code);
    const using = (st, code) => st.result.entries.filter((e) => e.ScheduleCode === code).length;

    it('is left for the user to settle', () => {
      expect(imported.conflicts).toEqual([{ code: 9001, menu: menuRow, result: resultRow, fixedDays: 6 }]);
      expect(imported.notes).toContain('result_template_schedules.csv and schedules_template.csv define ScheduleCode 9001 ' +
        'differently; choose which definition to keep for each.');
      expect(row(imported.state, 9001)).toEqual(menuRow);
      expect(() => applyMenuChoices(imported.state, imported.conflicts, {})).toThrow('no choice for ScheduleCode 9001');
    });

    it('keeps the menu\'s, or takes the result\'s, as chosen', () => {
      const menu = applyMenuChoices(imported.state, imported.conflicts, { 9001: 'menu' });
      expect(menu.schedules.rows).toEqual(original.schedules.rows);
      const result = applyMenuChoices(imported.state, imported.conflicts, { 9001: 'result' });
      expect(row(result, 9001)).toEqual(resultRow);
      expect(result.schedules.rows).toHaveLength(original.schedules.rows.length);
      expect(using(result, 9001)).toBe(6);
    });

    it('keeps both, moving the fixed days to the result\'s definition under a new code', () => {
      const both = applyMenuChoices(imported.state, imported.conflicts, { 9001: 'both' });
      const fresh = Math.max(...original.schedules.rows.map((r) => r.code)) + 1;
      expect(both.schedules.rows).toEqual([...original.schedules.rows, { ...resultRow, code: fresh }]);
      expect(using(both, 9001)).toBe(0);
      expect(using(both, fresh)).toBe(6);
      const sidecar = buildBundle(both).files['result_template_schedules.csv'];
      expect(sidecar).toContain(`\n${fresh},10:00-14:00,240,600,840\n`);
      expect(sidecar).not.toContain('\n9001,');
    });
  });

  it('says which JSON it could not use', () => {
    const { notes } = importBundle(templates((f) => {
      f['notes.json'] = '{"hello": 1}';
      f['broken.json'] = '{';
    }));
    expect(notes).toEqual(expect.arrayContaining([
      'notes.json is neither a v4.0 problem nor a result; it was not imported.',
      'broken.json is neither a v4.0 problem nor a result; it was not imported.'
    ]));
  });
});

/** The regenerated result's verdict. */
function validateResultOf(state) {
  const bundle = buildBundle(state);
  return validateResult(bundle.result, { problem: bundle.problem, files: bundle.files, resultName: bundle.resultName });
}

/** The one result document in a package, and its file name. */
function resultOf(files) {
  const name = Object.keys(files).find((n) => n.endsWith('.json') && 'OutRosterTeamDays' in JSON.parse(files[n]));
  return { resultName: name, result: JSON.parse(files[name]) };
}

/** Validate a package's result against its problem, after optional mutations. */
function validateResultDir(dir, mutate) {
  const files = readDir(dir);
  const { name: problemName, doc: problem } = locateProblem(files);
  const { resultName, result } = resultOf(files);
  if (mutate) mutate({ problem, result, files });
  return validateResult(result, { problem, files, resultName, problemName });
}

describe('result parity with the Python validator', () => {
  it.each([
    ['cenario2_partial', C2_PARTIAL, { rosterDays: 105, rosterDaysExpected: 465, rosterDaysLeft: 360, sidecarCodes: 11 }],
    ['cenario2_retail', C2, { rosterDays: 465, rosterDaysExpected: 465, rosterDaysLeft: 0, sidecarCodes: 11 }],
    ['templates', TEMPLATES, { rosterDays: 28, rosterDaysExpected: 28, rosterDaysLeft: 0, sidecarCodes: 4 }]
  ])('finds the %s result clean, counting what is left', (label, dir, stats) => {
    const r = validateResultDir(dir);
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual([]);
    expect(r.stats).toMatchObject({ form: 'result', ...stats });
  });

  it('has no result in the input-only example', () => {
    expect(Object.keys(readDir(C2_INPUT_ONLY)).filter((n) => n.startsWith('result'))).toEqual([]);
  });
});

/**
 * The fixed-day cases of tests/test_validator_result.py, on the templates
 * package: each breaks one thing, so exactly one finding must come back.
 */
describe('one finding per broken fixed day', () => {
  const RESULT = 'result_template.json';
  const INPUT = 'schedule_input_template.csv';

  function fixed({ codes = {}, drop = [], cells = {}, cap = null, extraSidecar = '' } = {}) {
    return validateResultDir(TEMPLATES, ({ problem, result, files }) => {
      const dropped = new Set(drop.map(([e, d]) => `${e}|${d}`));
      result.OutRosterTeamDays = result.OutRosterTeamDays
        .filter((e) => !dropped.has(`${e.EmployeeCode}|${e.Date.slice(0, 10)}`))
        .map((e) => {
          const code = codes[`${e.EmployeeCode}|${e.Date.slice(0, 10)}`];
          return code === undefined ? e : { ...e, ScheduleCode: code };
        });
      files[RESULT] = JSON.stringify(result);
      if (Object.keys(cells).length) {
        const lines = csvLines(files[INPUT]);
        const header = lines[0].split(',');
        files[INPUT] = `${lines.map((line) => {
          const row = line.split(',');
          for (const [key, value] of Object.entries(cells)) {
            const [emp, date] = key.split('|');
            // quote like csv.writer: a split window carries commas
            if (row[0] === emp) row[header.indexOf(date)] = value.includes(',') ? `"${value}"` : value;
          }
          return row.join(',');
        }).join('\n')}\n`;
      }
      if (cap) problem.constraints.hard[0].parameters[cap[0]] = cap[1];
      if (extraSidecar) files['result_template_schedules.csv'] += extraSidecar;
    });
  }

  const isolated = (r, needle) => {
    expect(messages(r.warnings)).toEqual([]);
    expect(r.errors).toHaveLength(1);
    expect(r.errors[0].message).toContain(needle);
  };

  it.each([
    ['EQUALS:09:00-17:00', 9001, 'is not the 09:00-17:00 the cell asks for'],
    ['EQUALS:09:00-12:00,13:00-17:00', 9003, 'split shift'],
    ['INCLUDE:07:00-10:00', 9003, 'does not cover 07:00-10:00'],
    ['WITHIN:13:00-17:00', 9001, 'fits inside none of 13:00-17:00'],
    ['EXCEPT:09:00-10:00', 9003, 'overlaps 09:00-10:00'],
    ['4', 9003, '480 min but the cell asks for 240'],
    ['A', 9001, '240 min but the cell asks for 480'],
    ['', 9003, 'the cell is blank']
  ])('reports a fixed day that contradicts its cell %j', (cell, code, needle) => {
    const key = 'EMP001|2026-03-02';
    isolated(fixed({ codes: { [key]: code }, cells: { [key]: cell } }), needle);
  });

  it('lets a fixed day work a preferable day off', () => {
    const r = fixed({ codes: { 'EMP001|2026-03-06': 9003 } });
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual([]);
  });

  it('finds a partial result clean and counts what is left', () => {
    const r = fixed({ drop: ['EMP001', 'EMP002', 'EMP003', 'EMP004'].map((e) => [e, '2026-03-08']) });
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual([]);
    expect(r.stats).toMatchObject({ rosterDaysExpected: 28, rosterDaysLeft: 4 });
  });

  it('reports fixed days above MaxConsecutiveWorkDays', () => {
    isolated(fixed({ cap: ['MaxConsecutiveWorkDays', 3] }), 'EMP001: fixed to work 4 days in a row ending 2026-03-05');
  });

  it('lets an open day break a run', () => {
    const r = fixed({ drop: [['EMP001', '2026-03-04']], cap: ['MaxConsecutiveWorkDays', 3] });
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual([]);
  });

  it('reports fixed days above the weekly cap', () => {
    isolated(fixed({ codes: { 'EMP001|2026-03-06': 9003 }, cap: ['MaxConsecutiveWorkDaysInWeek', 5] }),
      'EMP001, week 0: 6 fixed working days exceeds MaxConsecutiveWorkDaysInWeek of 5');
  });

  it('reports too little rest between fixed shifts', () => {
    isolated(fixed({ codes: { 'EMP001|2026-03-02': 9004 }, extraSidecar: '9004,22:00-06:00,480,1320,1800\n' }),
      '180 min of rest between 22:00-06:00 on 2026-03-02');
  });
});

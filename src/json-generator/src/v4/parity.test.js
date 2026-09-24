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
import { importBundle, locateProblem } from './importBundle';
import { buildBundle, bundleEntries } from './generate';
import { csvLines } from './core';
import { schemaFindings } from './schema';

const V4 = fileURLToPath(new URL('../../../../json_generation/schema_v4/', import.meta.url));
const TEMPLATES = path.join(V4, 'templates');
const C2 = path.join(V4, 'examples', 'cenario2_retail');

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
    ['2026-03-02,Piso,T1,1,0,0,17:00,21:00', 'Piso/T1 is not in demand.dimensions', true],
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

  it('errors on a contract off the grid (Cenario 1)', () => {
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
  it('uses a vendored schema identical to the canonical one', () => {
    const vendored = fs.readFileSync(fileURLToPath(new URL('../../schema_v4/schema-v4-input.json', import.meta.url)), 'utf-8');
    const canonical = fs.readFileSync(path.join(V4, 'schemas', 'schema-v4-input.json'), 'utf-8');
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
  it.each([['templates', TEMPLATES], ['cenario2_retail', C2]])('reproduces %s', (label, dir) => {
    const files = readDir(dir);
    const { state, report } = importBundle(files);
    expect(messages(report.errors)).toEqual([]);

    const bundle = buildBundle(state);
    const original = stripComments(locateProblem(files).doc);
    expect(bundle.problem).toEqual(original);

    for (const [name, text] of Object.entries(bundle.files)) {
      expect(text, name).toBe(normalised(files[name]));
    }
  });

  it('generates a bundle that validates the same as the original', () => {
    const { state } = importBundle(readDir(C2));
    const bundle = buildBundle(state);
    const r = validateBundle(bundle.problem, bundle.files);
    expect(messages(r.errors)).toEqual([]);
    expect(messages(r.warnings)).toEqual(C2_WARNINGS);
    expect(bundleEntries(bundle).map(([n]) => n)).toEqual([
      'problem.json', 'days_demand.csv', 'periods_demand.csv', 'shifts_demand.csv',
      'schedule_input.csv', 'schedules.csv'
    ]);
  });

  it('refuses SISQUAL\'s current export with a pointer to the agenda', () => {
    const files = { 'demo.json': JSON.stringify({ schemaVersion: '3.0', form: 'declarative', priorityHierachy: [] }) };
    expect(() => importBundle(files)).toThrow(/next_meeting.md/);
  });

  it('refuses a result', () => {
    const files = { 'result.json': JSON.stringify({ OutRosterTeamDays: [] }) };
    expect(() => importBundle(files)).toThrow(/is a result/);
  });
});

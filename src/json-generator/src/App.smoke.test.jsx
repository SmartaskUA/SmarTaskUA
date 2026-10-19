// @vitest-environment jsdom
/**
 * Render every wizard step, with a problem authored in the wizard and with the
 * real Scenario 2 packages (cenario2_retail, and cenario2_partial with its first
 * week fixed) imported, and fail on any render error or React warning. The
 * logic has its own tests; this one guards the screens.
 */
import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import App from './App';
import { WIZARD_STEPS } from './constants/wizardSteps';
import { STATE_KEY } from './v4/persistence';
import { sampleState } from './v4/fixtures/sampleState';
import { importBundle } from './v4/importBundle';

const EXAMPLES = path.resolve(process.cwd(), '../../json_generation/schema_v4/examples');

function imported(name) {
  const dir = path.join(EXAMPLES, name);
  const files = Object.fromEntries(fs.readdirSync(dir)
    .filter((n) => /\.(json|csv)$/.test(n))
    .map((n) => [n, fs.readFileSync(path.join(dir, n), 'utf-8')]));
  return importBundle(files).state;
}

const cenario2State = () => imported('cenario2_retail');
const partialState = () => imported('cenario2_partial');

const TITLES = {
  setup: 'Setup',
  contracts: 'Contracts',
  dimensions: 'Coverage dimensions',
  employees: 'Employees',
  scheduleInput: 'Schedule input',
  demand: 'Demand',
  schedules: 'Shift menu',
  fixedDays: 'Fixed days',
  rules: 'Rules',
  review: 'Review & download'
};

let container;
let root;
let problems;

beforeAll(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  window.matchMedia = window.matchMedia || ((query) => ({
    matches: false, media: query, onchange: null,
    addListener: () => {}, removeListener: () => {}, addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false
  }));
});

beforeEach(() => {
  problems = [];
  // MUI's enter/exit transitions settle on timers after a test's last act();
  // React reports those as "not wrapped in act", which is harness noise, not an app defect.
  vi.spyOn(console, 'error').mockImplementation((...args) => {
    const text = args.map(String).join(' ');
    if (!text.includes('not wrapped in act(')) problems.push(text);
  });
  container = document.createElement('div');
  document.body.appendChild(container);
});

afterEach(() => {
  if (root) act(() => root.unmount());
  root = null;
  container.remove();
  localStorage.clear();
  vi.restoreAllMocks();
});

function renderAt(state, index) {
  if (root) act(() => root.unmount());
  localStorage.setItem(STATE_KEY, JSON.stringify({ ...state, currentStep: index }));
  act(() => {
    root = createRoot(container);
    root.render(<App />);
  });
}

describe.each([
  ['a problem authored in the wizard', sampleState],
  ['cenario2_retail, imported', cenario2State],
  ['cenario2_partial, imported', partialState]
])('%s', (_, makeState) => {
  const state = makeState();
  it.each(WIZARD_STEPS.map((s, i) => [s.id, i]))('renders the %s step cleanly', (id, index) => {
    renderAt(state, index);
    expect(container.textContent).toContain(TITLES[id]);
    expect(container.textContent).toContain('Schema v4.0');
    expect(problems).toEqual([]);
  });
});

/** Click the first button-like element whose text contains `text` (dialogs render in portals, so search the whole body). */
function click(text, index = 0) {
  const matches = [...document.body.querySelectorAll('button, [role="button"], [role="tab"], [role="option"], [role="menuitem"]')]
    .filter((el) => el.textContent.includes(text));
  if (!matches[index]) throw new Error(`no button "${text}" among: ${[...document.body.querySelectorAll('button')].map((b) => b.textContent).filter(Boolean).join(' | ')}`);
  act(() => matches[index].click());
}

describe('dialogs and views, on cenario2_retail', () => {
  const state = cenario2State();
  const at = (id) => WIZARD_STEPS.findIndex((s) => s.id === id);

  it('opens the schedule matrix with every cell and the weekly load', () => {
    renderAt(state, at('scheduleInput'));
    click('Open matrix');
    const body = document.body.textContent;
    expect(body).toContain('15 employees × 31 days');
    expect(body).toContain('W0');
    expect(document.body.querySelectorAll('td').length).toBeGreaterThan(15 * 31);
    expect(problems).toEqual([]);
  });

  it('opens the time-window dialog from a cell', () => {
    renderAt(state, at('scheduleInput'));
    click('Open matrix');
    const select = document.body.querySelector('[role="combobox"]');
    act(() => select.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })));
    click('Time window');
    expect(document.body.textContent).toContain('WITHIN');
    click('Add range');
    expect(problems).toEqual([]);
  });

  it('shows the calendar with closed days and a day detail', () => {
    renderAt(state, at('demand'));
    click('Calendar');
    expect(document.body.textContent).toContain('Week 0');
    expect(document.body.textContent).toContain('Team/T1 3');
    click('Thu 01/01');  // a day cell is a role="button"
    expect(document.body.textContent).toContain('Responsibility/G');
    click('Add row');
    expect(document.body.textContent).toContain('Add periods row');
    expect(problems).toEqual([]);
  });

  it('opens the block dialog and the apply-template dialog', () => {
    renderAt(sampleState(), at('demand'));
    click('Apply weekly template');
    expect(document.body.textContent).toContain('row(s) will be generated');
    click('Cancel');
    const block = document.body.querySelector('[role="button"][aria-label^="Team/T1 09:00–13:00"]');
    act(() => block.click());
    expect(document.body.textContent).toContain('Edit Monday block');
    expect(problems).toEqual([]);
  });

  it('shows the days and shifts grains, and bulk add', () => {
    renderAt(state, at('demand'));
    click('Days — workload minutes');
    expect(document.body.textContent).toContain('Minutes of work, not people');
    click('Bulk add');
    expect(document.body.textContent).toContain('Add days rows in bulk');
    click('Cancel');
    click('Shifts — headcount');
    expect(document.body.textContent).toContain('v4 defines no shift types');
    click('Add row');
    const dialog = document.body.querySelector('[role="dialog"]');
    expect(dialog.textContent).toContain('Add shifts row');
    expect(dialog.textContent).not.toMatch(/workPeriod|work period|shift type/i);
    expect(problems).toEqual([]);
  });

  it('edits an employee with both kinds of assignment', () => {
    renderAt(state, at('employees'));
    click('Add employee');
    expect(document.body.textContent).toContain('Contract periods');
    click('Cancel');
    const edit = document.body.querySelector('[data-testid="EditIcon"]').closest('button');
    act(() => edit.click());
    expect(document.body.textContent).toContain('Edit 20072412');
    expect(document.body.textContent).toContain('Responsibility/G');
    expect(problems).toEqual([]);
  });

  it('generates a menu and edits a dimension', () => {
    renderAt(state, at('schedules'));
    click('Generate from contracts');
    expect(document.body.textContent).toContain('new row(s)');
    click('Cancel');
    renderAt(state, at('dimensions'));
    click('Add dimension');
    expect(document.body.textContent).toContain('Comma-separate to add several');
    expect(problems).toEqual([]);
  });

  it('keeps a menu row that fixed days use', () => {
    renderAt(state, at('schedules'));
    expect(document.body.querySelector('[aria-label="delete 9016"]').disabled).toBe(true);
    expect([...document.body.querySelectorAll('[aria-label^="delete "]')].some((b) => !b.disabled)).toBe(true);
    expect(problems).toEqual([]);
  });

  it('opens the bundle importer and the project manager', () => {
    renderAt(state, at('setup'));
    click('Start from a v4 bundle');
    expect(document.body.textContent).toContain('Choose files');
    click('Cancel');
    const projects = document.body.querySelector('[data-testid="FolderSpecialIcon"]').closest('button');
    act(() => projects.click());
    expect(document.body.textContent).toContain('Import v4 bundle');
    expect(problems).toEqual([]);
  });

  it('reports the known warnings and unlocks the download', () => {
    renderAt(state, at('review'));
    const body = document.body.textContent;
    expect(body).toContain('Valid, with warnings');
    expect(body).toContain('313 periods rows');
    expect([...document.body.querySelectorAll('button')].find((b) => b.textContent.includes('Download ZIP')).disabled).toBe(false);
    expect(problems).toEqual([]);
  });
});

describe('fixed days, on cenario2_partial', () => {
  const state = partialState();
  const at = WIZARD_STEPS.findIndex((s) => s.id === 'fixedDays');
  const cell = (label) => document.body.querySelector(`[role="button"][aria-label^="${label}"]`);
  const open = (label) => act(() => cell(label).click());

  it('shows the imported days, and fixes, contradicts and opens one in the grid', () => {
    renderAt(state, at);
    expect(container.textContent).toContain('105 fixed');
    expect(container.textContent).toContain('360 open');
    click('Open grid');
    expect(document.body.textContent).toContain('105 fixed · 360 open of 465 employee-days');
    expect(cell('20072412 2026-01-07').getAttribute('aria-label')).toBe('20072412 2026-01-07: ScheduleCode 9016');
    expect(cell('20072412 2026-01-08').getAttribute('aria-label')).toBe('20072412 2026-01-08: open');

    // The cell asks for exactly 8 hours: the menu says which codes contradict it, and why.
    open('20072412 2026-01-08');
    const menu = document.body.querySelector('[role="menu"]');
    expect(menu.textContent).toContain('20072412 · 2026-01-08 · cell 8');
    expect(menu.textContent).toContain('3 · Day offcontradicts the cell: the cell asks for work, but the day is a rest');
    expect(menu.textContent).toContain('9001 · 09:00-13:00 · 240 mincontradicts the cell: the shift is 240 min but the cell asks for 480');
    expect(menu.textContent).toMatch(/9016 · 09:00-17:00 · 480 min(?!contradicts)/);
    click('9016 · 09:00-17:00');
    expect(document.body.textContent).toContain('106 fixed · 359 open of 465 employee-days');
    expect(cell('20072412 2026-01-08').getAttribute('aria-label')).toBe('20072412 2026-01-08: ScheduleCode 9016');

    open('20072412 2026-01-08');
    click('3 · Day off');
    // The contradiction is counted on the employee's row.
    expect([...document.body.querySelectorAll('td')].some((td) => td.textContent === '8 / 311 ✗')).toBe(true);

    open('20072412 2026-01-08');
    click('· Open');
    expect(document.body.textContent).toContain('105 fixed · 360 open of 465 employee-days');
    expect(problems).toEqual([]);
  });

  it('writes the result and its sidecar into the preview', () => {
    renderAt(state, WIZARD_STEPS.length - 1);
    const tabs = [...document.body.querySelectorAll('[role="tab"]')].map((t) => t.textContent);
    expect(tabs).toEqual(expect.arrayContaining(['result.json', 'result_schedules.csv']));
    expect(document.body.textContent).toContain('105 fixed days');
    expect(document.body.textContent).toContain('360 employee-days left open');
    expect(problems).toEqual([]);
  });

  it('asks for the menu when it is off', () => {
    renderAt({ ...state, schedules: { ...state.schedules, enabled: false } }, at);
    expect(container.textContent).toContain('The 105 fixed day(s) are kept, but result.json is not written until the menu is back on.');
    expect([...document.body.querySelectorAll('button')].find((b) => b.textContent.includes('Open grid')).disabled).toBe(true);
    expect(problems).toEqual([]);
  });
});

describe('a fresh wizard', () => {
  it('starts on Setup with nothing saved, ignoring a v2.x save', () => {
    localStorage.setItem('wizardState', JSON.stringify({ schemaVersion: '2.2', currentStep: 5 }));
    act(() => {
      root = createRoot(container);
      root.render(<App />);
    });
    expect(container.textContent).toContain('Start from a v4 bundle');
    expect(localStorage.getItem('wizardState')).toBeNull();
    expect(problems).toEqual([]);
  });
});

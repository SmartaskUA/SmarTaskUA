// @vitest-environment jsdom
/**
 * Render every wizard step, with a problem authored in the wizard and with the
 * real Cenário 2 bundle imported, and fail on any render error or React
 * warning. The logic has its own tests; this one guards the screens.
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

const C2 = path.resolve(process.cwd(), '../../json_generation/schema_v4/examples/cenario2_retail');

function cenario2State() {
  const files = Object.fromEntries(fs.readdirSync(C2)
    .filter((n) => /\.(json|csv)$/.test(n))
    .map((n) => [n, fs.readFileSync(path.join(C2, n), 'utf-8')]));
  return importBundle(files).state;
}

const TITLES = {
  setup: 'Setup',
  contracts: 'Contracts',
  dimensions: 'Coverage dimensions',
  employees: 'Employees',
  scheduleInput: 'Schedule input',
  demand: 'Demand',
  schedules: 'Shift menu',
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
  ['cenario2_retail, imported', cenario2State]
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
  const matches = [...document.body.querySelectorAll('button, [role="button"], [role="tab"], [role="option"]')]
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
    click('Shifts — headcount by type');
    expect(document.body.textContent).toContain('ShiftTypeCode');
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

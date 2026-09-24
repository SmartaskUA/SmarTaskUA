/**
 * The wizard's state, shaped like the v4.0 document it produces so the
 * generator is a near-projection. UI-only fields: `id` on demand rows and
 * template blocks, `demand.weeklyTemplate`, `scheduleInput.dataMatrix` (becomes
 * schedule_input.csv), `schedules.enabled/rows` (become schedules.csv) and
 * `files` (the bundle's file names, kept so an imported bundle round-trips).
 */

import {
  DEFAULT_DAY_OFF_CODES, DEFAULT_SLOT_MINUTES, FILES, REST_SENTINELS, WEEKDAYS
} from './constants';

export const STATE_VERSION = 4;

let counter = 0;

/** A unique id for a demand row, template block or other UI-only record. */
export function newId(prefix = 'row') {
  counter += 1;
  return `${prefix}_${Date.now().toString(36)}_${counter.toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

export function emptyWeeklyTemplate() {
  return Object.fromEntries(WEEKDAYS.map((d) => [d, []]));
}

/** The locked rest rows every menu starts with. */
export function sentinelRows() {
  return REST_SENTINELS.map(({ code, description }) => ({
    code, description, scheduleWeightMinutes: 0, startMin: null, endMin: null
  }));
}

/** ISO instant at seconds precision, the way the template writes createdAt. */
export function nowIso() {
  return `${new Date().toISOString().slice(0, 19)}Z`;
}

export function createInitialState() {
  return {
    stateVersion: STATE_VERSION,
    currentStep: 0,
    stepCompleted: {},

    metadata: {
      problemId: '',
      createdAt: nowIso(),
      description: '',
      source: 'json-generator',
      rosterCode: ''
    },
    timeGrid: { slotMinutes: DEFAULT_SLOT_MINUTES },
    temporalScope: { start: '', end: '' },
    calendar: { weekStart: 'monday', holidays: [] },

    contracts: { definitions: [] },
    employees: { list: [] },

    demand: {
      dimensions: [],
      periods: [],
      days: [],
      shifts: [],
      weeklyTemplate: emptyWeeklyTemplate()
    },

    scheduleInput: {
      dayOffCodes: JSON.parse(JSON.stringify(DEFAULT_DAY_OFF_CODES)),
      dataMatrix: {}
    },

    schedules: { enabled: true, rows: sentinelRows() },

    priorityHierarchy: [],
    constraints: { hard: [], soft: [] },

    files: { ...FILES }
  };
}

/** A state from a stored or imported object: every missing key takes its default. */
export function withDefaults(partial) {
  const base = createInitialState();
  const out = { ...base, ...partial };
  for (const key of ['metadata', 'timeGrid', 'temporalScope', 'calendar', 'contracts', 'employees',
    'demand', 'scheduleInput', 'schedules', 'constraints', 'files']) {
    out[key] = { ...base[key], ...(partial?.[key] || {}) };
  }
  out.demand.weeklyTemplate = { ...emptyWeeklyTemplate(), ...(partial?.demand?.weeklyTemplate || {}) };
  out.stateVersion = STATE_VERSION;
  return out;
}

/** The dimension label used across the UI: Team/T1. */
export function pairLabel(tableName, tableValue) {
  return `${tableName}/${tableValue}`;
}

/** The leading `_` segment of a problemId — SISQUAL's <RosterCode>_<Month>_<Year>. */
export function rosterCodeFromProblemId(problemId) {
  return String(problemId || '').split('_')[0];
}

/** The v4 problem's view of the state, enough for core.* helpers that take a problem. */
export function problemView(state) {
  return {
    timeGrid: state.timeGrid,
    temporalScope: state.temporalScope,
    calendar: state.calendar,
    contracts: state.contracts,
    employees: state.employees,
    demand: { dimensions: state.demand.dimensions },
    scheduleInput: { dayOffCodes: state.scheduleInput.dayOffCodes },
    constraints: state.constraints
  };
}

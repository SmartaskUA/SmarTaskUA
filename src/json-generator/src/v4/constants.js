/**
 * Schema v4.0 constants shared by the domain, the generator, the validator and
 * the UI. See json_generation/schema_v4/docs/FORMAT.md for the semantics.
 */

export const SCHEMA_VERSION = '4.0';
export const FORM = 'input';
export const PROBLEM_TYPE = 'employee_scheduling';

/** The timeGrid.slotMinutes enum from schema-v4-input.json: every divisor of 1440. */
export const SLOT_OPTIONS = [
  1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24, 30, 32, 36, 40, 45, 48,
  60, 72, 80, 90, 96, 120, 144, 160, 180, 240, 288, 360, 480, 720, 1440
];
export const DEFAULT_SLOT_MINUTES = 30;

export const WEEKDAYS = [
  'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
];

/** schedule_input operators; each takes one or more comma-separated HH:MM-HH:MM ranges. */
export const OPERATORS = ['EQUALS', 'INCLUDE', 'WITHIN', 'EXCEPT'];

export const OPERATOR_HELP = {
  EQUALS: 'Work exactly this block; several ranges make one split shift.',
  INCLUDE: 'One block covering all listed windows (shift ⊇ window).',
  WITHIN: 'One block fitting inside one listed window (shift ⊆ window).',
  EXCEPT: 'Unavailable during all listed windows.'
};

/**
 * The day-off palette a new problem starts with. There are no implicit codes in
 * v4: every one used in schedule_input.csv must be declared, and each kind moves
 * the week's working-day target n_wk.
 */
export const DEFAULT_DAY_OFF_CODES = {
  DO: { kind: 'preferable', name: 'Day off', description: 'May be swapped, at a penalty' },
  VAC: { kind: 'unavailable', name: 'Vacation', description: 'Cannot work' },
  NOT: { kind: 'unavailable', name: 'Unavailable', description: 'Cannot work' }
};

export const DAY_OFF_KINDS = ['preferable', 'unavailable'];

/** Rest codes that keep the numbers WFM uses on import. */
export const REST_SENTINELS = [
  { code: 1, description: 'Espaço' },
  { code: 3, description: 'Day off' },
  { code: 4, description: 'Vazio' }
];
export const FIRST_MENU_CODE = 9001;

/** File names inside a generated bundle, matching examples/cenario2_retail. */
export const FILES = {
  problem: 'problem.json',
  days: 'days_demand.csv',
  periods: 'periods_demand.csv',
  shifts: 'shifts_demand.csv',
  scheduleInput: 'schedule_input.csv',
  schedules: 'schedules.csv'
};

/** The three demand grains, in the order the validator reads them. */
export const GRAINS = [
  { grain: 'days', key: 'dataFileDays' },
  { grain: 'periods', key: 'dataFilePeriods' },
  { grain: 'shifts', key: 'dataFileShifts' }
];

export const PRIORITY_DEFAULTS = {
  maxAlarmTableType: 'MaxAlarmLevel_Estimate_Ideal_Minimum',
  generationSequenceType: 'BY_LEVEL',
  minAbilityLevel: 1,
  maxAbilityLevel: 9,
  alarmLevelPercentage: 100
};
export const MAX_ALARM_TABLE_TYPE_SUGGESTIONS = ['MaxAlarmLevel_Estimate_Ideal_Minimum'];
export const GENERATION_SEQUENCE_SUGGESTIONS = ['BY_LEVEL', 'BY_ALARM_TABLE'];

/** The labour-law parameters observed in SISQUAL's RosterLegislation. */
export const LEGISLATION_KEYS = [
  { key: 'MaxConsecutiveWorkDays', label: 'Max consecutive work days', enforced: true },
  { key: 'MaxConsecutiveWorkDaysInWeek', label: 'Max work days in a week', enforced: true },
  { key: 'MinDistanceBetweenShiftsInMinutes', label: 'Min rest between shifts (minutes)', enforced: false }
];
export const DEFAULT_CONSTRAINT_TYPE = 'RosterLegislation';

/** SISQUAL's ShiftTypeCode vocabulary, per JSON-Export.docx — unconfirmed (agenda item 3). */
export const SHIFT_TYPE_SUGGESTIONS = ['M', 'T', 'N'];

export const DIMENSION_NAME_SUGGESTIONS = ['Team', 'Responsibility'];

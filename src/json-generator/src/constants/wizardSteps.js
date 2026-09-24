import {
  Info,
  Assignment,
  Category,
  People,
  CalendarMonth,
  EventNote,
  AccessTime,
  Rule,
  Preview
} from '@mui/icons-material';

/**
 * Single source of truth for the wizard's steps. The `id` is what validation
 * findings are tagged with (see src/v4/validate.js), so a finding always knows
 * which step owns its fix.
 */
export const WIZARD_STEPS = [
  { id: 'setup',         label: 'Setup',          description: 'Problem, grid & dates',     icon: Info },
  { id: 'contracts',     label: 'Contracts',      description: 'Minutes per day',           icon: Assignment },
  { id: 'dimensions',    label: 'Dimensions',     description: 'Coverage coordinates',      icon: Category },
  { id: 'employees',     label: 'Employees',      description: 'Contracts & competencies',  icon: People },
  { id: 'scheduleInput', label: 'Schedule Input', description: 'Day-off codes & matrix',    icon: CalendarMonth },
  { id: 'demand',        label: 'Demand',         description: 'Periods, days, shifts',     icon: EventNote },
  { id: 'schedules',     label: 'Shift Menu',     description: 'schedules.csv',             icon: AccessTime },
  { id: 'rules',         label: 'Rules',          description: 'Priority & labour law',     icon: Rule },
  { id: 'review',        label: 'Review',         description: 'Validate & download',       icon: Preview }
];

export const STEP_COUNT = WIZARD_STEPS.length;
export const LAST_STEP_INDEX = STEP_COUNT - 1;

/** The index of the step with this id, or -1. */
export function stepIndex(id) {
  return WIZARD_STEPS.findIndex((s) => s.id === id);
}

export function stepLabel(id) {
  const i = stepIndex(id);
  return i < 0 ? id : `${i + 1}. ${WIZARD_STEPS[i].label}`;
}

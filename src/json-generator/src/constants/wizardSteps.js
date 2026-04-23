import {
  Info,
  Assignment,
  Business,
  People,
  CalendarMonth,
  AccessTime,
  EventNote,
  Rule,
  Settings,
  Preview
} from '@mui/icons-material';

/**
 * Single source of truth for wizard step definitions.
 * hidden: true  → not shown in the stepper or summary; still reachable via Next/Prev.
 */
export const WIZARD_STEPS = [
  { label: 'Setup',          description: 'Metadata & models & dates', icon: Info },
  { label: 'Contracts',      description: 'Contract types',             icon: Assignment },
  { label: 'Org Units',      description: 'Teams/Competencies',         icon: Business },
  { label: 'Employees',      description: 'Employee roster',            icon: People },
  { label: 'Schedule Input', description: 'Availability matrix',        icon: CalendarMonth },
  { label: 'Work Periods',   description: 'Work period definitions',    icon: AccessTime },
  { label: 'Demand',         description: 'Coverage requirements',      icon: EventNote },
  { label: 'Constraints',    description: 'Rules & constraints',        icon: Rule,     hidden: true },
  { label: 'Optimization',   description: 'Solver settings',            icon: Settings, hidden: true },
  { label: 'Review',         description: 'Generate files',             icon: Preview },
];

/** Steps that appear in the stepper UI, each annotated with its real index. */
export const VISIBLE_STEPS = WIZARD_STEPS
  .map((step, index) => ({ ...step, realIndex: index }))
  .filter(step => !step.hidden);

/** Total number of steps shown in the UI. */
export const TOTAL_VISIBLE = VISIBLE_STEPS.length;

/** Last real step index (used by NavigationButtons to detect the final step). */
export const LAST_STEP_INDEX = WIZARD_STEPS.length - 1;

/**
 * Returns the 1-based display number for a given real step index.
 * Hidden steps resolve to the next visible step's number (so the counter
 * advances smoothly when passing through them).
 */
export function getVisibleStepNumber(realIndex) {
  const exact = VISIBLE_STEPS.findIndex(s => s.realIndex === realIndex);
  if (exact >= 0) return exact + 1;

  // Hidden step: find the first visible step that comes after it
  const next = VISIBLE_STEPS.find(s => s.realIndex > realIndex);
  if (next) return VISIBLE_STEPS.indexOf(next) + 1;

  // Fallback: last visible step
  return TOTAL_VISIBLE;
}

/**
 * Returns the real index of the next non-hidden step after `currentIndex`.
 * Skips over any hidden steps automatically.
 */
export function getNextStepIndex(currentIndex) {
  for (let i = currentIndex + 1; i < WIZARD_STEPS.length; i++) {
    if (!WIZARD_STEPS[i].hidden) return i;
  }
  return currentIndex; // already at last visible step
}

/**
 * Returns the real index of the previous non-hidden step before `currentIndex`.
 * Skips over any hidden steps automatically.
 */
export function getPrevStepIndex(currentIndex) {
  for (let i = currentIndex - 1; i >= 0; i--) {
    if (!WIZARD_STEPS[i].hidden) return i;
  }
  return currentIndex; // already at first visible step
}

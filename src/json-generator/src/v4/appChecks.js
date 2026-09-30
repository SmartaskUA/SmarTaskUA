/**
 * Checks for the SmarTask app that go beyond the v4 validator. A package can be
 * valid v4 and still be refused by the app's upload, or rejected by its solvers
 * before they run; these say so while the problem is being written.
 *
 * Findings use the validator's {message, step} shape and are always warnings:
 * the package is valid v4 and stays downloadable. validate.js and
 * validateResult.js stay pure ports of the Python validator.
 */

import * as core from './core';
import { canonicalCell, schedulesCsv } from './generate';

/** The problemIds the app's upload accepts: ProblemPackageImporter.PROBLEM_ID in src/api. */
export const UPLOADABLE_PROBLEM_ID = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;

/**
 * Work days no menu shift can cover: [{employee, day, cell, minutes}].
 *
 * The solver's own rule (src/scheduler/problem_v4/loader.py, _usable and
 * _build_candidates): with a menu, a working day picks a menu row with a window,
 * a positive weight and both ends on the grid that its cell accepts
 * (core.cellConflict); a split EQUALS fits no single row. Without a menu the
 * solver builds its own shifts, so nothing is checked.
 */
export function uncoveredWorkDays(state) {
  if (!state.schedules?.enabled) return [];
  const slot = Number(state.timeGrid?.slotMinutes);
  const menu = core.readSchedules(schedulesCsv(state.schedules.rows || [])).catalogue;
  const shifts = [...menu.values()].filter((s) => s.interval && !s.isSentinel && s.weightMinutes > 0 &&
    core.onGrid(s.interval.start, slot) && core.onGrid(s.interval.end, slot));
  const problem = { scheduleInput: { dayOffCodes: state.scheduleInput?.dayOffCodes || {} } };
  const minutesOf = new Map((state.contracts?.definitions || []).map((c) => [c.id, Number(c.workMinutesPerDay)]));
  const days = core.dateRange(state.temporalScope?.start, state.temporalScope?.end);
  const out = [];
  for (const employee of state.employees?.list || []) {
    for (const day of days) {
      const cell = canonicalCell(state.scheduleInput?.dataMatrix?.[employee.id]?.[day]);
      const { rule } = core.tryClassifyCell(cell, problem);
      if (!rule || !core.ASKS_FOR_WORK.has(rule.kind)) continue;
      const minutes = minutesOf.get(core.activeContract(employee, day)) ?? null;
      const split = rule.kind === 'equals' && rule.windows.length > 1;
      if (split || !shifts.some((s) => core.cellConflict(rule, s, minutes) === null)) {
        out.push({ employee: employee.id, day, cell, minutes });
      }
    }
  }
  return out;
}

/** [{message, step}] warnings about what the SmarTask app would refuse. */
export function appFindings(state) {
  const warnings = [];
  const id = state.metadata?.problemId ?? '';
  if (id.trim() && !UPLOADABLE_PROBLEM_ID.test(id)) {
    warnings.push({
      message: `app: metadata.problemId ${core.pyRepr(id)} cannot be uploaded to the SmarTask app, which takes ` +
        "letters, digits, '_', '-' and '.', starting with a letter or digit, at most 64 characters",
      step: 'setup'
    });
  }
  const uncovered = uncoveredWorkDays(state);
  if (uncovered.length) {
    const [first] = uncovered;
    warnings.push({
      message: `solver: ${uncovered.length} work day(s) have no menu shift that fits their cell (e.g. ` +
        `${first.employee} on ${first.day}, cell ${core.pyRepr(first.cell)}` +
        `${first.minutes ? `, contract ${first.minutes} min` : ''}), so SmarTask's solvers would reject the package: ` +
        'add shifts in Shift Menu (Generate from contracts) or switch the menu off to let the solver build them',
      step: 'schedules'
    });
  }
  return warnings;
}

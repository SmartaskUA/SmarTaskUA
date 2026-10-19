/**
 * How the Fixed days grid shows a day: a colour per kind of fixed day, the
 * schedule_input cell as a short caption, and a menu code as a label. Kept out
 * of the .jsx files so each exports only components, for React Fast Refresh.
 */

import { intervalToString } from '../../v4/core';

export const FIXED_COLORS = {
  open: '#ffffff',
  rest: '#eeeeee',
  worked: '#e3f2fd',
  unknown: '#fff3e0'
};

/** The schedule_input cell, short enough for a caption: EQUALS:09:00-13:00 -> EQU 09:00-13:00. */
export function cellCaption(cell) {
  const text = String(cell ?? '').trim();
  if (!text) return 'blank';
  const colon = text.indexOf(':');
  const head = colon > 0 ? text.slice(0, colon).toUpperCase() : '';
  if (['EQUALS', 'INCLUDE', 'WITHIN', 'EXCEPT'].includes(head)) return `${head.slice(0, 3)} ${text.slice(colon + 1)}`;
  return text;
}

/** What a menu code reads as in a cell: its window for a shift, its description for a rest. */
export function scheduleLabel(schedule) {
  if (!schedule) return 'not in menu';
  return schedule.interval ? intervalToString(schedule.interval) : (schedule.description || String(schedule.code));
}

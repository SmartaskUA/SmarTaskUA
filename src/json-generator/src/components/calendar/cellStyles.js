/**
 * The schedule-input cell vocabulary the matrix, its legend, the day-off
 * palette and the step summary share: a colour for each kind of cell, and how
 * an operator cell reads. Kept out of the .jsx files so each exports only
 * components, which React Fast Refresh needs to hot-reload them.
 */

import { OPERATORS } from '../../v4/constants';

export const CELL_COLORS = {
  auto: '#e8f5e9',
  hours: '#e3f2fd',
  blank: '#ffffff',
  uncovered: '#eeeeee'
};

export const KIND_COLORS = { preferable: '#fff59d', unavailable: '#ffcdd2' };

export const OPERATOR_COLORS = {
  EQUALS: '#e1bee7',
  INCLUDE: '#ffe0b2',
  WITHIN: '#b2dfdb',
  EXCEPT: '#f8bbd0'
};

/** {type, ranges: [{start, end}]} from an operator cell, or null. */
export function parseOperatorCell(value) {
  const text = String(value || '').trim();
  const colon = text.indexOf(':');
  if (colon < 0) return null;
  const type = text.slice(0, colon).toUpperCase();
  if (!OPERATORS.includes(type)) return null;
  const ranges = text.slice(colon + 1).split(',').map((part) => {
    const cut = part.indexOf('-');
    return cut < 0 ? { start: part.trim(), end: '' } : { start: part.slice(0, cut).trim(), end: part.slice(cut + 1).trim() };
  });
  return { type, ranges };
}

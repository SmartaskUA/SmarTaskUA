/**
 * Time Window Constraint Validator (Schema v2.2)
 *
 * Validates time window constraints in schedule_input.csv using Allen Interval Algebra:
 * - EQUALS:HH:MM-HH:MM - Must work exactly this time range
 * - INCLUDE:HH:MM-HH:MM - Must cover this entire range minimum
 * - EXCEPT:HH:MM-HH:MM - Unavailable during this time window
 */

/**
 * Validates time format (HH:MM)
 */
export function isValidTimeFormat(time) {
  if (typeof time !== 'string') return false;
  const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
  return timeRegex.test(time);
}

/**
 * Parses time string to minutes since midnight
 */
export function parseTimeToMinutes(time) {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * Validates a time range (start < end)
 */
export function validateTimeRange(start, end) {
  if (!isValidTimeFormat(start)) {
    return { valid: false, error: `Invalid start time: "${start}"` };
  }
  if (!isValidTimeFormat(end)) {
    return { valid: false, error: `Invalid end time: "${end}"` };
  }
  const startMin = parseTimeToMinutes(start);
  const endMin = parseTimeToMinutes(end);
  if (startMin >= endMin) {
    return { valid: false, error: `Start (${start}) must be before end (${end})` };
  }
  return { valid: true };
}

/**
 * Parses a time window constraint string
 */
export function parseTimeWindowConstraint(constraint) {
  if (typeof constraint !== 'string') return null;
  const match = constraint.match(/^(EQUALS|INCLUDE|EXCEPT):(\d{2}:\d{2})-(\d{2}:\d{2})$/);
  if (!match) return null;
  return { type: match[1], start: match[2], end: match[3] };
}

/**
 * Validates a time window constraint
 */
export function validateTimeWindowConstraint(constraint) {
  const parsed = parseTimeWindowConstraint(constraint);
  if (!parsed) {
    return { valid: false, error: `Invalid format: "${constraint}"` };
  }
  const rangeValidation = validateTimeRange(parsed.start, parsed.end);
  if (!rangeValidation.valid) {
    return { valid: false, error: `${rangeValidation.error} in "${constraint}"` };
  }
  return { valid: true, parsed };
}

/**
 * Checks if a cell value is a time window constraint
 */
export function isTimeWindowConstraint(value) {
  if (typeof value !== 'string') return false;
  return /^(EQUALS|INCLUDE|EXCEPT):\d{2}:\d{2}-\d{2}:\d{2}$/.test(value);
}

/**
 * Alias for isTimeWindowConstraint (backward compatibility)
 */
export function isTimeConstraint(value) {
  return isTimeWindowConstraint(value);
}

/**
 * Extracts the constraint type from a time window constraint string
 * @param {string} constraint - Constraint string (e.g., "EQUALS:08:00-16:00")
 * @returns {string|null} - Constraint type ('EQUALS', 'INCLUDE', 'EXCEPT') or null
 */
export function getConstraintType(constraint) {
  const parsed = parseTimeWindowConstraint(constraint);
  return parsed ? parsed.type : null;
}

/**
 * Formats a time window constraint for display
 */
export function formatTimeWindowConstraint(constraint) {
  const parsed = parseTimeWindowConstraint(constraint);
  if (!parsed) return constraint;
  const { type, start, end } = parsed;
  switch (type) {
    case 'EQUALS': return `Must work exactly ${start} to ${end}`;
    case 'INCLUDE': return `Must cover ${start} to ${end} (minimum)`;
    case 'EXCEPT': return `Unavailable ${start} to ${end}`;
    default: return constraint;
  }
}

export default {
  isValidTimeFormat,
  parseTimeToMinutes,
  validateTimeRange,
  parseTimeWindowConstraint,
  validateTimeWindowConstraint,
  isTimeWindowConstraint,
  isTimeConstraint,
  getConstraintType,
  formatTimeWindowConstraint
};

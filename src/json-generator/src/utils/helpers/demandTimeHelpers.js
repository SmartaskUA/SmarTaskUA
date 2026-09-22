/**
 * Demand Time Helpers
 *
 * Per-day work-period time overrides for the Demand step (schema v2.6).
 *
 * In v2.6, demand.csv carries optional `start`/`end` columns that override a
 * work period's default `timeRange` for a specific date+workPeriod+team row.
 * These helpers centralize the "is this an override?" logic so the CSV
 * generator and the Phase 2 editors agree on when a time is a real override
 * (written to the CSV) versus the work-period default (written empty).
 */

const TIME_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)$/;

/**
 * Get a work period's default time range by code.
 * @param {Array} workPeriods - work period definitions ({ code, timeRange })
 * @param {string} code - work period code
 * @returns {{start: string, end: string} | null}
 */
export function getWorkPeriodTimeRange(workPeriods = [], code) {
  const wp = workPeriods.find((w) => w.code === code);
  return wp?.timeRange || null;
}

/**
 * True when the entry's time range differs from the work period's default
 * (i.e. it is a genuine per-day override that must be written to demand.csv).
 * @param {{start?: string, end?: string} | undefined} timeRange
 * @param {{start: string, end: string} | null} wpDefault
 * @returns {boolean}
 */
export function isTimeOverride(timeRange, wpDefault) {
  if (!timeRange || !timeRange.start || !timeRange.end) return false;
  // No known default to compare against → can't assert a difference, so don't
  // treat it as an override (avoids spuriously writing start/end everywhere).
  if (!wpDefault) return false;
  return timeRange.start !== wpDefault.start || timeRange.end !== wpDefault.end;
}

/**
 * Validate a per-day time override. Only enforced when the time is an override
 * (differs from the WP default); the default itself may be cross-midnight
 * (night shift) and is exported empty, so it is always allowed here.
 *
 * The shipped v2.6 validator rejects cross-midnight overrides, so an override
 * must be same-day (start < end).
 * @param {{start?: string, end?: string} | undefined} timeRange
 * @param {{start: string, end: string} | null} wpDefault
 * @returns {string | null} error message, or null if valid
 */
export function validateOverrideTime(timeRange, wpDefault) {
  if (!isTimeOverride(timeRange, wpDefault)) return null;

  const { start, end } = timeRange;
  if (!TIME_PATTERN.test(start) || !TIME_PATTERN.test(end)) {
    return 'Time must be in HH:MM (24h) format';
  }
  if (start >= end) {
    return 'Overnight per-day overrides aren’t supported — start must be before end';
  }
  return null;
}

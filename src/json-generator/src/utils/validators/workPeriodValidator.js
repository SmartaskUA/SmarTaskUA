/**
 * Work Period Validator - Validation logic for work periods (shifts) and breaks
 *
 * Validates:
 * - Work period codes, names, orders
 * - Time ranges (fixed model) and durations (flexible model)
 * - Break configurations
 * - Uniqueness constraints
 */

import {
  validateTimeFormat,
  isStartBeforeEnd,
  validateTimeWindow,
  timeToMinutes,
  calculateDuration
} from '../helpers/timeHelpers';

/**
 * Validates work period code
 * @param {string} code - Work period code to validate
 * @param {Array} existingWorkPeriods - Existing work periods
 * @param {string} currentCode - Current code (for edit mode, to exclude self)
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateWorkPeriodCode(code, existingWorkPeriods = [], currentCode = null) {
  // Required
  if (!code || code.trim() === '') {
    return { valid: false, error: 'Work period code is required' };
  }

  // Alphanumeric + underscore only
  const codeRegex = /^[A-Za-z0-9_]+$/;
  if (!codeRegex.test(code)) {
    return { valid: false, error: 'Code must be alphanumeric (A-Z, 0-9, _)' };
  }

  // Length check
  if (code.length > 10) {
    return { valid: false, error: 'Code must be 10 characters or less' };
  }

  // Uniqueness check
  const isDuplicate = existingWorkPeriods.some(
    wp => wp.code === code && wp.code !== currentCode
  );

  if (isDuplicate) {
    return { valid: false, error: 'Work period code must be unique' };
  }

  return { valid: true, error: null };
}

/**
 * Validates work period name
 * @param {string} name - Work period name to validate
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateWorkPeriodName(name) {
  // Required
  if (!name || name.trim() === '') {
    return { valid: false, error: 'Work period name is required' };
  }

  // Length check
  if (name.length > 50) {
    return { valid: false, error: 'Name must be 50 characters or less' };
  }

  return { valid: true, error: null };
}

/**
 * Validates fixed model time range
 * @param {string} start - Start time (HH:MM)
 * @param {string} end - End time (HH:MM)
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateFixedTimeRange(start, end) {
  // Validate format
  if (!validateTimeFormat(start)) {
    return { valid: false, error: 'Invalid start time format (use HH:MM, 24-hour)' };
  }

  if (!validateTimeFormat(end)) {
    return { valid: false, error: 'Invalid end time format (use HH:MM, 24-hour)' };
  }

  // Start and end cannot be the same
  if (start === end) {
    return { valid: false, error: 'Start and end time cannot be the same' };
  }

  // Overnight shifts are supported (e.g., 22:00-06:00 means 10 PM to 6 AM next day)

  return { valid: true, error: null };
}

/**
 * Validates flexible model configuration
 * @param {number} duration - Duration in hours
 * @param {Array} allowedStartTimes - Array of allowed start times (HH:MM)
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateFlexibleConfig(duration, allowedStartTimes) {
  // Validate duration
  if (duration === null || duration === undefined || duration === '') {
    return { valid: false, error: 'Duration is required' };
  }

  const durationNum = Number(duration);
  if (isNaN(durationNum)) {
    return { valid: false, error: 'Duration must be a number' };
  }

  if (durationNum <= 0 || durationNum > 24) {
    return { valid: false, error: 'Duration must be between 1 and 24 hours' };
  }

  // Validate allowed start times
  if (!allowedStartTimes || allowedStartTimes.length === 0) {
    return { valid: false, error: 'At least one allowed start time is required' };
  }

  // Validate each start time format
  for (const time of allowedStartTimes) {
    if (!validateTimeFormat(time)) {
      return { valid: false, error: `Invalid time format: ${time}` };
    }
  }

  return { valid: true, error: null };
}

/**
 * Validates a break configuration
 * @param {object} breakConfig - Break configuration object
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateBreak(breakConfig) {
  const { type, duration, timingMode, startTime, windowStart, windowEnd, afterWorkHours } = breakConfig;

  // Type validation
  const validTypes = ['meal', 'rest', 'other'];
  if (!type || !validTypes.includes(type)) {
    return { valid: false, error: 'Break type must be: meal, rest, or other' };
  }

  // Duration validation
  if (duration === null || duration === undefined || duration === '') {
    return { valid: false, error: 'Break duration is required' };
  }

  const durationNum = Number(duration);
  if (isNaN(durationNum) || !Number.isInteger(durationNum)) {
    return { valid: false, error: 'Break duration must be an integer' };
  }

  if (durationNum <= 0 || durationNum > 480) {
    return { valid: false, error: 'Break duration must be between 1 and 480 minutes (8 hours)' };
  }

  // Timing mode validation
  const validTimingModes = ['fixed', 'window', 'afterWork'];
  if (!timingMode || !validTimingModes.includes(timingMode)) {
    return { valid: false, error: 'Timing mode must be: fixed, window, or afterWork' };
  }

  // Mode-specific validation
  if (timingMode === 'fixed') {
    if (!validateTimeFormat(startTime)) {
      return { valid: false, error: 'Invalid break start time format (use HH:MM)' };
    }
  } else if (timingMode === 'window') {
    const windowValidation = validateTimeWindow(windowStart, windowEnd);
    if (!windowValidation.valid) {
      return { valid: false, error: `Break window: ${windowValidation.error}` };
    }
  } else if (timingMode === 'afterWork') {
    if (afterWorkHours === null || afterWorkHours === undefined || afterWorkHours === '') {
      return { valid: false, error: '"After work hours" value is required' };
    }

    const hoursNum = Number(afterWorkHours);
    if (isNaN(hoursNum) || hoursNum <= 0 || hoursNum > 24) {
      return { valid: false, error: '"After work hours" must be between 0 and 24' };
    }
  }

  return { valid: true, error: null };
}

/**
 * Validates all breaks for a work period
 * @param {Array} breaks - Array of break configurations
 * @param {object} workPeriod - Work period configuration (to check breaks fit within work period)
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateBreaks(breaks, workPeriod) {
  if (!breaks || breaks.length === 0) {
    return { valid: true, error: null }; // Breaks are optional
  }

  // Validate each break
  for (let i = 0; i < breaks.length; i++) {
    const breakValidation = validateBreak(breaks[i]);
    if (!breakValidation.valid) {
      return { valid: false, error: `Break ${i + 1}: ${breakValidation.error}` };
    }
  }

  // Check total break duration doesn't exceed work period duration
  const totalBreakMinutes = breaks.reduce((sum, b) => sum + Number(b.duration), 0);

  if (workPeriod.workPeriodModel === 'fixed' && workPeriod.timeRange) {
    const { start, end } = workPeriod.timeRange;
    const workDuration = calculateDuration(start, end); // Handles overnight shifts

    if (totalBreakMinutes >= workDuration) {
      return {
        valid: false,
        error: `Total break time (${totalBreakMinutes}m) must be less than work period duration (${workDuration}m)`
      };
    }
  } else if (workPeriod.workPeriodModel === 'flexible' && workPeriod.duration) {
    const workDurationMinutes = Number(workPeriod.duration) * 60;

    if (totalBreakMinutes >= workDurationMinutes) {
      return {
        valid: false,
        error: `Total break time (${totalBreakMinutes}m) must be less than work period duration (${workDurationMinutes}m)`
      };
    }
  }

  return { valid: true, error: null };
}

/**
 * Validates an entire work period
 * @param {object} workPeriod - Work period configuration
 * @param {string} model - Work period model ('fixed' or 'flexible')
 * @param {Array} existingWorkPeriods - Existing work periods
 * @param {string} currentCode - Current code (for edit mode)
 * @returns {object} {valid: boolean, errors: object}
 */
export function validateWorkPeriod(workPeriod, model, existingWorkPeriods = [], currentCode = null) {
  const errors = {};

  // Code validation
  const codeValidation = validateWorkPeriodCode(
    workPeriod.code,
    existingWorkPeriods,
    currentCode
  );
  if (!codeValidation.valid) {
    errors.code = codeValidation.error;
  }

  // Name validation
  const nameValidation = validateWorkPeriodName(workPeriod.name);
  if (!nameValidation.valid) {
    errors.name = nameValidation.error;
  }

  // Model-specific validation
  if (model === 'fixed') {
    const timeRangeValidation = validateFixedTimeRange(
      workPeriod.timeRange?.start,
      workPeriod.timeRange?.end
    );
    if (!timeRangeValidation.valid) {
      errors.timeRange = timeRangeValidation.error;
    }
  } else if (model === 'flexible') {
    const flexibleValidation = validateFlexibleConfig(
      workPeriod.duration,
      workPeriod.allowedStartTimes
    );
    if (!flexibleValidation.valid) {
      errors.flexible = flexibleValidation.error;
    }
  }

  // Breaks validation
  if (workPeriod.breaks && workPeriod.breaks.length > 0) {
    const breaksValidation = validateBreaks(workPeriod.breaks, {
      workPeriodModel: model,
      ...workPeriod
    });
    if (!breaksValidation.valid) {
      errors.breaks = breaksValidation.error;
    }
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors
  };
}

/**
 * Validates that at least one work period exists
 * @param {Array} workPeriods - Array of work periods
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateWorkPeriodsExist(workPeriods) {
  if (!workPeriods || workPeriods.length === 0) {
    return {
      valid: false,
      error: 'At least one work period is required to proceed'
    };
  }

  return { valid: true, error: null };
}

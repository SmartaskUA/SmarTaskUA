/**
 * Time Helpers - Utilities for time validation, formatting, and manipulation
 *
 * Used by Work Period components for time range validation and display
 */

/**
 * Validates if a string is in valid HH:MM format (24-hour)
 * @param {string} time - Time string to validate
 * @returns {boolean} True if valid HH:MM format
 */
export function validateTimeFormat(time) {
  if (!time || typeof time !== 'string') return false;

  const timeRegex = /^([0-1][0-9]|2[0-3]):([0-5][0-9])$/;
  return timeRegex.test(time);
}

/**
 * Compares two time strings in HH:MM format
 * @param {string} start - Start time (HH:MM)
 * @param {string} end - End time (HH:MM)
 * @returns {number} -1 if start < end, 0 if equal, 1 if start > end, null if invalid
 */
export function compareTimeStrings(start, end) {
  if (!validateTimeFormat(start) || !validateTimeFormat(end)) {
    return null;
  }

  const [startHours, startMinutes] = start.split(':').map(Number);
  const [endHours, endMinutes] = end.split(':').map(Number);

  const startTotalMinutes = startHours * 60 + startMinutes;
  const endTotalMinutes = endHours * 60 + endMinutes;

  if (startTotalMinutes < endTotalMinutes) return -1;
  if (startTotalMinutes > endTotalMinutes) return 1;
  return 0;
}

/**
 * Checks if start time is before end time
 * @param {string} start - Start time (HH:MM)
 * @param {string} end - End time (HH:MM)
 * @returns {boolean} True if start < end
 */
export function isStartBeforeEnd(start, end) {
  return compareTimeStrings(start, end) === -1;
}

/**
 * Generates array of time options in HH:MM format
 * @param {number} intervalMinutes - Interval between times (default: 30)
 * @returns {string[]} Array of time strings
 */
export function generateTimeOptions(intervalMinutes = 30) {
  const times = [];

  for (let hours = 0; hours < 24; hours++) {
    for (let minutes = 0; minutes < 60; minutes += intervalMinutes) {
      const timeString = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
      times.push(timeString);
    }
  }

  return times;
}

/**
 * Generates hourly time options (00:00, 01:00, ..., 23:00)
 * @returns {string[]} Array of hourly time strings
 */
export function generateHourlyTimeOptions() {
  return generateTimeOptions(60);
}

/**
 * Generates 30-minute interval time options
 * @returns {string[]} Array of time strings with 30-min intervals
 */
export function generateHalfHourlyTimeOptions() {
  return generateTimeOptions(30);
}

/**
 * Generates 15-minute interval time options
 * @returns {string[]} Array of time strings with 15-min intervals
 */
export function generateQuarterHourlyTimeOptions() {
  return generateTimeOptions(15);
}

/**
 * Formats duration in minutes to human-readable string
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration (e.g., "1h 30m", "45m")
 */
export function formatDuration(minutes) {
  if (!minutes || minutes <= 0) return '0m';

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (hours === 0) {
    return `${remainingMinutes}m`;
  } else if (remainingMinutes === 0) {
    return `${hours}h`;
  } else {
    return `${hours}h ${remainingMinutes}m`;
  }
}

/**
 * Converts time string to minutes since midnight
 * @param {string} time - Time in HH:MM format
 * @returns {number|null} Minutes since midnight, or null if invalid
 */
export function timeToMinutes(time) {
  if (!validateTimeFormat(time)) return null;

  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * Converts minutes since midnight to HH:MM format
 * @param {number} minutes - Minutes since midnight
 * @returns {string} Time in HH:MM format
 */
export function minutesToTime(minutes) {
  if (minutes < 0 || minutes >= 1440) {
    throw new Error('Minutes must be between 0 and 1439');
  }

  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
}

/**
 * Calculates duration between two times in minutes
 * @param {string} start - Start time (HH:MM)
 * @param {string} end - End time (HH:MM)
 * @returns {number|null} Duration in minutes, or null if invalid
 */
export function calculateDuration(start, end) {
  const startMinutes = timeToMinutes(start);
  const endMinutes = timeToMinutes(end);

  if (startMinutes === null || endMinutes === null) return null;

  // Handle overnight shifts (end < start)
  if (endMinutes < startMinutes) {
    return (1440 - startMinutes) + endMinutes;
  }

  return endMinutes - startMinutes;
}

/**
 * Formats time range for display
 * @param {string} start - Start time (HH:MM)
 * @param {string} end - End time (HH:MM)
 * @returns {string} Formatted range (e.g., "08:00 - 16:00 (8h)")
 */
export function formatTimeRange(start, end) {
  if (!validateTimeFormat(start) || !validateTimeFormat(end)) {
    return 'Invalid time range';
  }

  const duration = calculateDuration(start, end);
  const durationStr = formatDuration(duration);

  return `${start} - ${end} (${durationStr})`;
}

/**
 * Validates a time window (used for breaks)
 * @param {string} windowStart - Window start time (HH:MM)
 * @param {string} windowEnd - Window end time (HH:MM)
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateTimeWindow(windowStart, windowEnd) {
  if (!validateTimeFormat(windowStart)) {
    return { valid: false, error: 'Invalid window start time format (use HH:MM)' };
  }

  if (!validateTimeFormat(windowEnd)) {
    return { valid: false, error: 'Invalid window end time format (use HH:MM)' };
  }

  if (!isStartBeforeEnd(windowStart, windowEnd)) {
    return { valid: false, error: 'Window start must be before window end' };
  }

  return { valid: true, error: null };
}

/**
 * Checks if a time falls within a time window
 * @param {string} time - Time to check (HH:MM)
 * @param {string} windowStart - Window start (HH:MM)
 * @param {string} windowEnd - Window end (HH:MM)
 * @returns {boolean} True if time is within window
 */
export function isTimeInWindow(time, windowStart, windowEnd) {
  const timeMinutes = timeToMinutes(time);
  const startMinutes = timeToMinutes(windowStart);
  const endMinutes = timeToMinutes(windowEnd);

  if (timeMinutes === null || startMinutes === null || endMinutes === null) {
    return false;
  }

  // Handle overnight windows
  if (endMinutes < startMinutes) {
    return timeMinutes >= startMinutes || timeMinutes <= endMinutes;
  }

  return timeMinutes >= startMinutes && timeMinutes <= endMinutes;
}

/**
 * Creates a default time object for forms
 * @returns {object} Default time values
 */
export function getDefaultTimes() {
  return {
    morning: '08:00',
    afternoon: '16:00',
    night: '00:00',
    lunchStart: '12:00',
    lunchEnd: '13:00'
  };
}

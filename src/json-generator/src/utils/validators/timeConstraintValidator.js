/**
 * Time Constraint Validator
 *
 * Validates and parses time window constraints in the format:
 * MODIFIER:HH:MM-HH:MM
 *
 * Where:
 * - MODIFIER: ONLY | ATLEAST | NOT
 * - HH: 00-23 (hours)
 * - MM: 00-59 (minutes)
 * - Constraint: startTime < endTime
 */

// Valid constraint modifiers
export const CONSTRAINT_MODIFIERS = {
  ONLY: 'ONLY',
  ATLEAST: 'ATLEAST',
  NOT: 'NOT'
};

// Regex pattern for time constraint format
const TIME_CONSTRAINT_REGEX = /^(ONLY|ATLEAST|NOT):(\d{2}):(\d{2})-(\d{2}):(\d{2})$/;

/**
 * Check if a value is a time constraint
 * @param {string} value - The value to check
 * @returns {boolean} True if value matches time constraint pattern
 */
export function isTimeConstraint(value) {
  if (!value || typeof value !== 'string') return false;
  return TIME_CONSTRAINT_REGEX.test(value.trim());
}

/**
 * Parse a time constraint string into components
 * @param {string} value - Time constraint string (e.g., "ONLY:08:00-16:00")
 * @returns {Object|null} Parsed components or null if invalid
 * Returns: { modifier, startHour, startMinute, endHour, endMinute, startTime, endTime }
 */
export function parseTimeConstraint(value) {
  if (!value || typeof value !== 'string') return null;

  const match = value.trim().match(TIME_CONSTRAINT_REGEX);
  if (!match) return null;

  const [, modifier, startHH, startMM, endHH, endMM] = match;

  return {
    modifier,
    startHour: parseInt(startHH, 10),
    startMinute: parseInt(startMM, 10),
    endHour: parseInt(endHH, 10),
    endMinute: parseInt(endMM, 10),
    startTime: `${startHH}:${startMM}`,
    endTime: `${endHH}:${endMM}`
  };
}

/**
 * Validate time constraint format and logic
 * @param {string} value - Time constraint string to validate
 * @returns {Object} { valid: boolean, error: string|null, parsed: Object|null }
 */
export function validateTimeConstraint(value) {
  // Check if empty
  if (!value || typeof value !== 'string') {
    return {
      valid: false,
      error: 'Time constraint cannot be empty',
      parsed: null
    };
  }

  const trimmed = value.trim();

  // Check format
  if (!TIME_CONSTRAINT_REGEX.test(trimmed)) {
    return {
      valid: false,
      error: 'Invalid format. Expected: MODIFIER:HH:MM-HH:MM (e.g., ONLY:08:00-16:00)',
      parsed: null
    };
  }

  // Parse components
  const parsed = parseTimeConstraint(trimmed);
  if (!parsed) {
    return {
      valid: false,
      error: 'Failed to parse time constraint',
      parsed: null
    };
  }

  const { modifier, startHour, startMinute, endHour, endMinute, startTime, endTime } = parsed;

  // Validate modifier
  if (!Object.values(CONSTRAINT_MODIFIERS).includes(modifier)) {
    return {
      valid: false,
      error: `Invalid modifier "${modifier}". Must be one of: ONLY, ATLEAST, NOT`,
      parsed: null
    };
  }

  // Validate hour ranges
  if (startHour < 0 || startHour > 23) {
    return {
      valid: false,
      error: `Invalid start hour "${startHour}". Must be 00-23`,
      parsed: null
    };
  }

  if (endHour < 0 || endHour > 23) {
    return {
      valid: false,
      error: `Invalid end hour "${endHour}". Must be 00-23`,
      parsed: null
    };
  }

  // Validate minute ranges
  if (startMinute < 0 || startMinute > 59) {
    return {
      valid: false,
      error: `Invalid start minute "${startMinute}". Must be 00-59`,
      parsed: null
    };
  }

  if (endMinute < 0 || endMinute > 59) {
    return {
      valid: false,
      error: `Invalid end minute "${endMinute}". Must be 00-59`,
      parsed: null
    };
  }

  // Validate time logic: start < end
  const startMinutes = startHour * 60 + startMinute;
  const endMinutes = endHour * 60 + endMinute;

  if (startMinutes >= endMinutes) {
    return {
      valid: false,
      error: `Start time (${startTime}) must be before end time (${endTime})`,
      parsed: null
    };
  }

  // All validations passed
  return {
    valid: true,
    error: null,
    parsed
  };
}

/**
 * Format a time constraint from components
 * @param {string} modifier - Constraint modifier (ONLY, ATLEAST, NOT)
 * @param {string} startTime - Start time HH:MM
 * @param {string} endTime - End time HH:MM
 * @returns {string} Formatted constraint string
 */
export function formatTimeConstraint(modifier, startTime, endTime) {
  return `${modifier}:${startTime}-${endTime}`;
}

/**
 * Get constraint type from value
 * @param {string} value - Time constraint string
 * @returns {string|null} Modifier type or null if not a valid constraint
 */
export function getConstraintType(value) {
  const parsed = parseTimeConstraint(value);
  return parsed ? parsed.modifier : null;
}

/**
 * Get user-friendly description for constraint type
 * @param {string} modifier - Constraint modifier (ONLY, ATLEAST, NOT)
 * @returns {string} Human-readable description
 */
export function getConstraintDescription(modifier) {
  const descriptions = {
    ONLY: 'Must work exactly this time range (no earlier/later)',
    ATLEAST: 'Must work entire range minimum (can start earlier or end later)',
    NOT: 'Completely unavailable during this time window'
  };

  return descriptions[modifier] || 'Unknown constraint type';
}

/**
 * Validate time format HH:MM
 * @param {string} time - Time string to validate
 * @returns {boolean} True if valid HH:MM format
 */
export function isValidTimeFormat(time) {
  if (!time || typeof time !== 'string') return false;

  const match = time.match(/^(\d{2}):(\d{2})$/);
  if (!match) return false;

  const [, hour, minute] = match;
  const h = parseInt(hour, 10);
  const m = parseInt(minute, 10);

  return h >= 0 && h <= 23 && m >= 0 && m <= 59;
}

/**
 * Check if two times are in valid order (start before end)
 * @param {string} startTime - Start time HH:MM
 * @param {string} endTime - End time HH:MM
 * @returns {boolean} True if start < end
 */
export function isValidTimeOrder(startTime, endTime) {
  if (!isValidTimeFormat(startTime) || !isValidTimeFormat(endTime)) return false;

  const [startH, startM] = startTime.split(':').map(n => parseInt(n, 10));
  const [endH, endM] = endTime.split(':').map(n => parseInt(n, 10));

  const startMinutes = startH * 60 + startM;
  const endMinutes = endH * 60 + endM;

  return startMinutes < endMinutes;
}

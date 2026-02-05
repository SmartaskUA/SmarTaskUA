import { addDays, format } from 'date-fns';

/**
 * Generate an array of date strings for the scheduling period
 * @param {string} startDate - ISO date string (YYYY-MM-DD)
 * @param {number} numDays - Number of days
 * @returns {string[]} Array of date strings in YYYY-MM-DD format
 */
export function generateDateRange(startDate, numDays) {
  if (!startDate || !numDays) return [];

  const dates = [];
  const start = new Date(startDate);

  for (let i = 0; i < numDays; i++) {
    const date = addDays(start, i);
    dates.push(format(date, 'yyyy-MM-dd'));
  }

  return dates;
}

/**
 * Format a date string for display in matrix headers
 * @param {string} dateStr - ISO date string (YYYY-MM-DD)
 * @returns {string} Formatted date (e.g., "Mon 1/15")
 */
export function formatDateHeader(dateStr) {
  const date = new Date(dateStr);
  const dayOfWeek = format(date, 'EEE'); // Mon, Tue, etc.
  const monthDay = format(date, 'M/d'); // 1/15
  return `${dayOfWeek} ${monthDay}`;
}

/**
 * Check if a date string is a weekend
 * @param {string} dateStr - ISO date string (YYYY-MM-DD)
 * @returns {boolean}
 */
export function isWeekend(dateStr) {
  const date = new Date(dateStr);
  const day = date.getDay();
  return day === 0 || day === 6; // Sunday or Saturday
}

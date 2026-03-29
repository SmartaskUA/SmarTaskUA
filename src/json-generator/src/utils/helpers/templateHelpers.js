/**
 * Template Helpers
 *
 * Utilities for applying weekly templates to full calendar
 */

/**
 * Get day of week name from date string
 *
 * @param {string} dateStr - ISO date string (YYYY-MM-DD)
 * @returns {string} - Day name in lowercase (monday, tuesday, etc.)
 */
export function getDayOfWeek(dateStr) {
  const date = new Date(dateStr);
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  return days[date.getDay()];
}

/**
 * Apply weekly template to generate full calendar demand data
 *
 * @param {Object} weeklyTemplate - Weekly template with day keys (monday, tuesday, etc.)
 * @param {Array<string>} dates - Array of date strings (YYYY-MM-DD) from temporal scope
 * @param {string} employeeModel - 'team' or 'competency'
 * @returns {Array} - Demand data array for all dates
 */
export function applyWeeklyTemplate(weeklyTemplate, dates, employeeModel = 'team') {
  const demandData = [];

  dates.forEach((date) => {
    const dayOfWeek = getDayOfWeek(date);
    const templateBlocks = weeklyTemplate[dayOfWeek] || [];

    // Convert each template block to demand entry
    templateBlocks.forEach((block) => {
      const teamField = employeeModel === 'team' ? 'team' : 'competency';

      demandData.push({
        date,
        workPeriod: block.workPeriod,
        [teamField]: block.team, // Keep 'team' in block but map to correct field
        minimum: block.coverage.minimum,
        ideal: block.coverage.ideal,
        estimated: block.coverage.estimated,
        timeRange: block.timeRange // Include time range for flexible periods
      });
    });
  });

  return demandData;
}

/**
 * Merge template-generated data with existing demand data
 * Keeps existing entries, adds template entries for dates without data
 *
 * @param {Array} existingDemandData - Current demand data
 * @param {Object} weeklyTemplate - Weekly template
 * @param {Array<string>} dates - All dates from temporal scope
 * @param {string} employeeModel - 'team' or 'competency'
 * @returns {Array} - Merged demand data
 */
export function mergeTemplateWithExisting(existingDemandData, weeklyTemplate, dates, employeeModel = 'team') {
  // Create a map of existing data by date
  const existingByDate = {};
  existingDemandData.forEach((entry) => {
    if (!existingByDate[entry.date]) {
      existingByDate[entry.date] = [];
    }
    existingByDate[entry.date].push(entry);
  });

  const mergedData = [...existingDemandData];

  // Add template data for dates without entries
  dates.forEach((date) => {
    if (!existingByDate[date] || existingByDate[date].length === 0) {
      const dayOfWeek = getDayOfWeek(date);
      const templateBlocks = weeklyTemplate[dayOfWeek] || [];
      const teamField = employeeModel === 'team' ? 'team' : 'competency';

      templateBlocks.forEach((block) => {
        mergedData.push({
          date,
          workPeriod: block.workPeriod,
          [teamField]: block.team,
          minimum: block.coverage.minimum,
          ideal: block.coverage.ideal,
          estimated: block.coverage.estimated,
          timeRange: block.timeRange
        });
      });
    }
  });

  return mergedData;
}

/**
 * Check if weekly template is empty
 *
 * @param {Object} weeklyTemplate - Weekly template
 * @returns {boolean} - True if template has no blocks
 */
export function isTemplateEmpty(weeklyTemplate) {
  if (!weeklyTemplate) return true;

  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  return days.every((day) => !weeklyTemplate[day] || weeklyTemplate[day].length === 0);
}

/**
 * Get summary statistics for weekly template
 *
 * @param {Object} weeklyTemplate - Weekly template
 * @returns {Object} - Stats about the template
 */
export function getTemplateSummary(weeklyTemplate) {
  if (!weeklyTemplate) {
    return { totalBlocks: 0, daysWithData: 0, emptyDays: 7 };
  }

  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  let totalBlocks = 0;
  let daysWithData = 0;

  days.forEach((day) => {
    const blocks = weeklyTemplate[day] || [];
    if (blocks.length > 0) {
      totalBlocks += blocks.length;
      daysWithData++;
    }
  });

  return {
    totalBlocks,
    daysWithData,
    emptyDays: 7 - daysWithData
  };
}

/**
 * Clear weekly template (returns empty template structure)
 *
 * @returns {Object} - Empty weekly template
 */
export function getEmptyWeeklyTemplate() {
  return {
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: []
  };
}

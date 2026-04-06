/**
 * Demand CSV Generator - Generate demand.csv from demand data
 *
 * Output CSV format:
 * date,workPeriod,team,minimum,ideal,estimated
 * 2025-10-01,MORNING,TeamA,2,3,2
 */

import Papa from 'papaparse';

/**
 * Generates demand CSV content from demand data
 * @param {Array} demandData - Array of demand entries
 * @param {string} employeeModel - 'team' or 'competency' to determine column name
 * @returns {string} CSV content
 */
export function generateDemandCsv(demandData, employeeModel = 'team') {
  if (!demandData || demandData.length === 0) {
    // Return empty CSV with just headers
    const teamField = employeeModel === 'team' ? 'team' : 'competency';
    return `date,workPeriod,${teamField},minimum,ideal,estimated\n`;
  }

  const teamField = employeeModel === 'team' ? 'team' : 'competency';

  // Sort by date, then work period, then team
  const sorted = [...demandData].sort((a, b) => {
    // Sort by date first
    if (a.date !== b.date) {
      return a.date.localeCompare(b.date);
    }
    // Then by work period
    if (a.workPeriod !== b.workPeriod) {
      return a.workPeriod.localeCompare(b.workPeriod);
    }
    // Then by team/competency
    return (a[teamField] || '').localeCompare(b[teamField] || '');
  });

  // Prepare data for CSV generation
  const csvData = sorted.map(entry => ({
    date: entry.date,
    workPeriod: entry.workPeriod,
    [teamField]: entry[teamField],
    minimum: entry.minimum,
    ideal: entry.ideal,
    estimated: entry.estimated
  }));

  // Generate CSV
  const csv = Papa.unparse(csvData, {
    columns: ['date', 'workPeriod', teamField, 'minimum', 'ideal', 'estimated'],
    header: true
  });

  return csv;
}

/**
 * Downloads demand CSV as a file
 * @param {Array} demandData - Array of demand entries
 * @param {string} employeeModel - 'team' or 'competency'
 * @param {string} filename - Filename for download (default: 'demand.csv')
 */
export function downloadDemandCsv(demandData, employeeModel = 'team', filename = 'demand.csv') {
  const csv = generateDemandCsv(demandData, employeeModel);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Generates demand data from all combinations with defaults
 * @param {Array} dates - Array of date strings (YYYY-MM-DD)
 * @param {Array} workPeriods - Array of work period objects {code, name}
 * @param {Array} teams - Array of team/competency objects {code, name}
 * @param {object} defaults - Default values {minimum, ideal, estimated}
 * @param {string} employeeModel - 'team' or 'competency'
 * @returns {Array} Array of demand entries
 */
export function generateDefaultDemandData(dates, workPeriods, teams, defaults, employeeModel = 'team') {
  const demandData = [];
  const teamField = employeeModel === 'team' ? 'team' : 'competency';

  dates.forEach(date => {
    workPeriods.forEach(wp => {
      teams.forEach(team => {
        demandData.push({
          date,
          workPeriod: wp.code,
          [teamField]: team.code,
          minimum: defaults.minimum || 1,
          ideal: defaults.ideal || 1,
          estimated: defaults.estimated || 1
        });
      });
    });
  });

  return demandData;
}

/**
 * Fills missing demand entries with defaults
 * @param {Array} existingData - Existing demand data
 * @param {Array} dates - All dates in temporal scope
 * @param {Array} workPeriods - All work periods
 * @param {Array} teams - All teams/competencies
 * @param {object} defaults - Default values
 * @param {string} employeeModel - 'team' or 'competency'
 * @returns {Array} Complete demand data with defaults filled
 */
export function fillMissingDemandEntries(existingData, dates, workPeriods, teams, defaults, employeeModel = 'team') {
  const teamField = employeeModel === 'team' ? 'team' : 'competency';
  const existingKeys = new Set(
    existingData.map(entry => `${entry.date}|${entry.workPeriod}|${entry[teamField]}`)
  );

  const allEntries = [...existingData];

  dates.forEach(date => {
    workPeriods.forEach(wp => {
      teams.forEach(team => {
        const key = `${date}|${wp.code}|${team.code}`;
        if (!existingKeys.has(key)) {
          allEntries.push({
            date,
            workPeriod: wp.code,
            [teamField]: team.code,
            minimum: defaults.minimum || 1,
            ideal: defaults.ideal || 1,
            estimated: defaults.estimated || 1
          });
        }
      });
    });
  });

  return allEntries;
}

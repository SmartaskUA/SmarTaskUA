/**
 * Demand CSV Parser - Parse demand.csv file into demand data structure
 *
 * Expected CSV format:
 * date,workPeriod,team,minimum,ideal,estimated
 * 2025-10-01,MORNING,TeamA,2,3,2
 */

import Papa from 'papaparse';

/**
 * Parses demand CSV file
 * @param {File} file - CSV file to parse
 * @param {string} employeeModel - 'team' or 'competency' to determine column name
 * @returns {Promise<{data: Array, errors: Array}>}
 */
export async function parseDemandCsv(file, employeeModel = 'team') {
  return new Promise((resolve) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const demandData = [];
        const errors = [];

        // Expected columns
        const teamField = employeeModel === 'team' ? 'team' : 'competency';
        const requiredColumns = ['date', 'workPeriod', teamField, 'minimum', 'ideal', 'estimated'];

        // Check if all required columns exist
        if (results.data.length > 0) {
          const actualColumns = Object.keys(results.data[0]);
          const missingColumns = requiredColumns.filter(col => !actualColumns.includes(col));

          if (missingColumns.length > 0) {
            errors.push(`Missing required columns: ${missingColumns.join(', ')}`);
            resolve({ data: [], errors });
            return;
          }
        }

        // Parse each row
        results.data.forEach((row, index) => {
          const lineNumber = index + 2; // +2 because index is 0-based and CSV has header

          // Skip completely empty rows
          if (!row.date && !row.workPeriod && !row[teamField]) {
            return;
          }

          try {
            const entry = {
              date: row.date?.trim(),
              workPeriod: row.workPeriod?.trim(),
              [teamField]: row[teamField]?.trim(),
              minimum: row.minimum ? parseInt(row.minimum, 10) : 0,
              ideal: row.ideal ? parseInt(row.ideal, 10) : 0,
              estimated: row.estimated ? parseInt(row.estimated, 10) : 0
            };

            // Basic validation
            if (!entry.date) {
              errors.push(`Line ${lineNumber}: Missing date`);
            }
            if (!entry.workPeriod) {
              errors.push(`Line ${lineNumber}: Missing work period`);
            }
            if (!entry[teamField]) {
              errors.push(`Line ${lineNumber}: Missing ${teamField}`);
            }

            // Validate date format (ISO YYYY-MM-DD)
            if (entry.date && !/^\d{4}-\d{2}-\d{2}$/.test(entry.date)) {
              errors.push(`Line ${lineNumber}: Invalid date format '${entry.date}'. Use YYYY-MM-DD`);
            }

            // Validate numbers
            if (isNaN(entry.minimum)) {
              errors.push(`Line ${lineNumber}: Invalid minimum value '${row.minimum}'`);
            }
            if (isNaN(entry.ideal)) {
              errors.push(`Line ${lineNumber}: Invalid ideal value '${row.ideal}'`);
            }
            if (isNaN(entry.estimated)) {
              errors.push(`Line ${lineNumber}: Invalid estimated value '${row.estimated}'`);
            }

            demandData.push(entry);
          } catch (error) {
            errors.push(`Line ${lineNumber}: ${error.message}`);
          }
        });

        resolve({ data: demandData, errors });
      },
      error: (error) => {
        resolve({ data: [], errors: [`CSV parsing error: ${error.message}`] });
      }
    });
  });
}

/**
 * Parses demand CSV from text content
 * @param {string} csvContent - CSV content as string
 * @param {string} employeeModel - 'team' or 'competency'
 * @returns {Promise<{data: Array, errors: Array}>}
 */
export async function parseDemandCsvFromText(csvContent, employeeModel = 'team') {
  return new Promise((resolve) => {
    Papa.parse(csvContent, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const demandData = [];
        const errors = [];

        const teamField = employeeModel === 'team' ? 'team' : 'competency';
        const requiredColumns = ['date', 'workPeriod', teamField, 'minimum', 'ideal', 'estimated'];

        if (results.data.length > 0) {
          const actualColumns = Object.keys(results.data[0]);
          const missingColumns = requiredColumns.filter(col => !actualColumns.includes(col));

          if (missingColumns.length > 0) {
            errors.push(`Missing required columns: ${missingColumns.join(', ')}`);
            resolve({ data: [], errors });
            return;
          }
        }

        results.data.forEach((row, index) => {
          const lineNumber = index + 2;

          if (!row.date && !row.workPeriod && !row[teamField]) {
            return;
          }

          try {
            const entry = {
              date: row.date?.trim(),
              workPeriod: row.workPeriod?.trim(),
              [teamField]: row[teamField]?.trim(),
              minimum: row.minimum ? parseInt(row.minimum, 10) : 0,
              ideal: row.ideal ? parseInt(row.ideal, 10) : 0,
              estimated: row.estimated ? parseInt(row.estimated, 10) : 0
            };

            demandData.push(entry);
          } catch (error) {
            errors.push(`Line ${lineNumber}: ${error.message}`);
          }
        });

        resolve({ data: demandData, errors });
      },
      error: (error) => {
        resolve({ data: [], errors: [`CSV parsing error: ${error.message}`] });
      }
    });
  });
}

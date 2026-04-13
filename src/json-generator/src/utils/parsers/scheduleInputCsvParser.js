import Papa from 'papaparse';

/**
 * Parse schedule_input.csv and convert to dataMatrix format
 * @param {string} csvText - CSV content
 * @param {Array} employees - Employee list for validation
 * @param {Array} dateRange - Expected date range for validation
 * @returns {Object} { dataMatrix, errors }
 */
export function parseScheduleInputCsv(csvText, employees, dateRange) {
  return new Promise((resolve, reject) => {
    Papa.parse(csvText, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const errors = [];
        const dataMatrix = {};

        // Get employee IDs for validation
        const validEmployeeIds = new Set(employees.map(e => e.id));

        // Get date columns (all columns except employee_id)
        const dateColumns = results.meta.fields.filter(field => field !== 'employee_id');

        // Validate that we have the employee_id column
        if (!results.meta.fields.includes('employee_id')) {
          errors.push('CSV must have an "employee_id" column');
          return resolve({ dataMatrix: null, errors });
        }

        // Process each row
        results.data.forEach((row, index) => {
          const employeeId = row.employee_id?.trim();

          if (!employeeId) {
            errors.push(`Row ${index + 1}: Missing employee ID`);
            return;
          }

          // Check if employee exists
          if (!validEmployeeIds.has(employeeId)) {
            errors.push(`Row ${index + 1}: Unknown employee ID "${employeeId}"`);
            return;
          }

          // Initialize employee data
          if (!dataMatrix[employeeId]) {
            dataMatrix[employeeId] = {};
          }

          // Process each date column
          dateColumns.forEach(date => {
            const value = row[date]?.trim() || '';

            // Validate date format (basic check)
            if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
              errors.push(`Row ${index + 1}: Invalid date format "${date}". Expected YYYY-MM-DD`);
              return;
            }

            // Store value
            if (value) {
              dataMatrix[employeeId][date] = value;
            }
          });
        });

        resolve({ dataMatrix, errors });
      },
      error: (error) => {
        reject(new Error(`CSV parsing error: ${error.message}`));
      }
    });
  });
}

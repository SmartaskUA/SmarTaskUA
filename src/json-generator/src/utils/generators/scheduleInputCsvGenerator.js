import Papa from 'papaparse';

/**
 * Generate schedule_input.csv from dataMatrix
 * @param {Array} employees - Employee list
 * @param {Object} dataMatrix - Nested object { employeeId: { date: value } }
 * @param {Array} dateRange - Array of date strings (YYYY-MM-DD)
 * @returns {string} CSV string
 */
export function generateScheduleInputCsv(employees, dataMatrix, dateRange) {
  if (!employees || employees.length === 0) {
    throw new Error('No employees defined');
  }

  if (!dateRange || dateRange.length === 0) {
    throw new Error('No date range defined');
  }

  // Build rows
  const rows = employees.map(employee => {
    const row = { employee_id: employee.id };

    // Add value for each date
    dateRange.forEach(date => {
      const value = dataMatrix?.[employee.id]?.[date] || '';
      row[date] = value;
    });

    return row;
  });

  // Generate CSV with explicit column order
  const headers = ['employee_id', ...dateRange];

  return Papa.unparse({
    fields: headers,
    data: rows
  });
}

/**
 * Download schedule_input.csv as a file
 */
export function downloadScheduleInputCsv(employees, dataMatrix, dateRange, filename = 'schedule_input.csv') {
  const csv = generateScheduleInputCsv(employees, dataMatrix, dateRange);

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}

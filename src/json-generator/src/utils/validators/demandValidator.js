/**
 * Demand Validator - Validation logic for demand coverage requirements
 *
 * Validates:
 * - Demand entries (date, workPeriod, team, minimum, ideal, estimated)
 * - Coverage value relationships (minimum ≤ estimated ≤ ideal)
 * - References to work periods and teams/competencies
 * - Date range validation
 */

/**
 * Validates a single demand entry
 * @param {object} entry - Demand entry to validate
 * @param {Array} workPeriods - Available work periods from Step 6
 * @param {Array} teams - Available teams (team model) or competencies (competency model)
 * @param {object} temporalScope - Temporal scope from Step 1
 * @param {string} employeeModel - 'team' or 'competency'
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateDemandEntry(entry, workPeriods, teams, temporalScope, employeeModel) {
  const errors = [];

  // Date validation
  if (!entry.date) {
    errors.push('Date is required');
  } else {
    // Check if date is within temporal scope
    const entryDate = new Date(entry.date);
    const startDate = new Date(temporalScope.targetPeriod.start);
    const endDate = new Date(temporalScope.targetPeriod.end);

    if (entryDate < startDate || entryDate > endDate) {
      errors.push(`Date ${entry.date} is outside temporal scope (${temporalScope.targetPeriod.start} to ${temporalScope.targetPeriod.end})`);
    }
  }

  // Work period validation
  if (!entry.workPeriod) {
    errors.push('Work period is required');
  } else {
    const workPeriodExists = workPeriods.some(wp => wp.code === entry.workPeriod);
    if (!workPeriodExists) {
      errors.push(`Work period '${entry.workPeriod}' does not exist in work period definitions`);
    }
  }

  // Team/Competency validation
  const teamField = employeeModel === 'team' ? 'team' : 'competency';
  if (!entry[teamField]) {
    errors.push(`${employeeModel === 'team' ? 'Team' : 'Competency'} is required`);
  } else {
    const teamExists = teams.some(t => t.code === entry[teamField]);
    if (!teamExists) {
      errors.push(`${employeeModel === 'team' ? 'Team' : 'Competency'} '${entry[teamField]}' does not exist`);
    }
  }

  // Coverage values validation
  const { minimum, ideal, estimated } = entry;

  // Check all values are present
  if (minimum === undefined || minimum === null) {
    errors.push('Minimum coverage is required');
  }
  if (ideal === undefined || ideal === null) {
    errors.push('Ideal coverage is required');
  }
  if (estimated === undefined || estimated === null) {
    errors.push('Estimated coverage is required');
  }

  // Check all values are non-negative integers
  if (minimum !== undefined && minimum !== null) {
    const minNum = Number(minimum);
    if (isNaN(minNum) || !Number.isInteger(minNum) || minNum < 0) {
      errors.push('Minimum must be a non-negative integer');
    }
  }

  if (ideal !== undefined && ideal !== null) {
    const idealNum = Number(ideal);
    if (isNaN(idealNum) || !Number.isInteger(idealNum) || idealNum < 0) {
      errors.push('Ideal must be a non-negative integer');
    }
  }

  if (estimated !== undefined && estimated !== null) {
    const estNum = Number(estimated);
    if (isNaN(estNum) || !Number.isInteger(estNum) || estNum < 0) {
      errors.push('Estimated must be a non-negative integer');
    }
  }

  // Check logical order: minimum ≤ estimated ≤ ideal
  const minNum = Number(minimum);
  const idealNum = Number(ideal);
  const estNum = Number(estimated);

  if (!isNaN(minNum) && !isNaN(estNum) && minNum > estNum) {
    errors.push(`Minimum (${minNum}) cannot be greater than estimated (${estNum})`);
  }

  if (!isNaN(estNum) && !isNaN(idealNum) && estNum > idealNum) {
    errors.push(`Estimated (${estNum}) cannot be greater than ideal (${idealNum})`);
  }

  if (!isNaN(minNum) && !isNaN(idealNum) && minNum > idealNum) {
    errors.push(`Minimum (${minNum}) cannot be greater than ideal (${idealNum})`);
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates all demand entries
 * @param {Array} demandData - Array of demand entries
 * @param {Array} workPeriods - Available work periods
 * @param {Array} teams - Available teams or competencies
 * @param {object} temporalScope - Temporal scope
 * @param {string} employeeModel - 'team' or 'competency'
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateDemandData(demandData, workPeriods, teams, temporalScope, employeeModel) {
  const errors = [];

  // At least one entry required
  if (!demandData || demandData.length === 0) {
    errors.push('At least one demand entry is required');
    return { valid: false, errors };
  }

  // Validate each entry
  demandData.forEach((entry, index) => {
    const entryValidation = validateDemandEntry(entry, workPeriods, teams, temporalScope, employeeModel);
    if (!entryValidation.valid) {
      entryValidation.errors.forEach(error => {
        errors.push(`Entry ${index + 1}: ${error}`);
      });
    }
  });

  // Check for duplicates (same date + workPeriod + team combination)
  const seen = new Set();
  const teamField = employeeModel === 'team' ? 'team' : 'competency';

  demandData.forEach((entry, index) => {
    const key = `${entry.date}|${entry.workPeriod}|${entry[teamField]}`;
    if (seen.has(key)) {
      errors.push(`Entry ${index + 1}: Duplicate entry for ${entry.date}, ${entry.workPeriod}, ${entry[teamField]}`);
    }
    seen.add(key);
  });

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates that at least one demand entry exists
 * @param {Array} demandData - Array of demand entries
 * @returns {object} {valid: boolean, error: string|null}
 */
export function validateDemandExists(demandData) {
  if (!demandData || demandData.length === 0) {
    return {
      valid: false,
      error: 'At least one demand entry is required to proceed'
    };
  }

  return { valid: true, error: null };
}

/**
 * Validates demand default values
 * @param {object} defaults - Default values {minimum, ideal, estimated}
 * @returns {object} {valid: boolean, errors: object}
 */
export function validateDemandDefaults(defaults) {
  const errors = {};

  if (defaults.minimum === undefined || defaults.minimum === null || defaults.minimum === '') {
    errors.minimum = 'Default minimum is required';
  } else {
    const minNum = Number(defaults.minimum);
    if (isNaN(minNum) || !Number.isInteger(minNum) || minNum < 0) {
      errors.minimum = 'Default minimum must be a non-negative integer';
    }
  }

  if (defaults.ideal === undefined || defaults.ideal === null || defaults.ideal === '') {
    errors.ideal = 'Default ideal is required';
  } else {
    const idealNum = Number(defaults.ideal);
    if (isNaN(idealNum) || !Number.isInteger(idealNum) || idealNum < 0) {
      errors.ideal = 'Default ideal must be a non-negative integer';
    }
  }

  if (defaults.estimated === undefined || defaults.estimated === null || defaults.estimated === '') {
    errors.estimated = 'Default estimated is required';
  } else {
    const estNum = Number(defaults.estimated);
    if (isNaN(estNum) || !Number.isInteger(estNum) || estNum < 0) {
      errors.estimated = 'Default estimated must be a non-negative integer';
    }
  }

  // Check logical order
  const minNum = Number(defaults.minimum);
  const idealNum = Number(defaults.ideal);
  const estNum = Number(defaults.estimated);

  if (!isNaN(minNum) && !isNaN(estNum) && minNum > estNum) {
    errors.estimated = 'Default estimated cannot be less than default minimum';
  }

  if (!isNaN(estNum) && !isNaN(idealNum) && estNum > idealNum) {
    errors.ideal = 'Default ideal cannot be less than default estimated';
  }

  if (!isNaN(minNum) && !isNaN(idealNum) && minNum > idealNum) {
    errors.ideal = 'Default ideal cannot be less than default minimum';
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors
  };
}

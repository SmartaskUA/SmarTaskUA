/**
 * Step Validators - Validation functions for each wizard step
 *
 * Used by:
 * - Clickable stepper to determine if navigation warning is needed
 * - Step components to validate before proceeding
 * - Review step to show overall validation status
 */

import { validateWorkPeriodsExist } from './workPeriodValidator';

/**
 * Validates Step 1: Quick Setup
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep1(state) {
  const errors = [];

  // Problem ID required
  if (!state.metadata.problemId || state.metadata.problemId.trim() === '') {
    errors.push('Problem ID is required');
  }

  // Year required and valid
  if (!state.temporalScope.year) {
    errors.push('Year is required');
  } else if (state.temporalScope.year < 2020 || state.temporalScope.year > 2100) {
    errors.push('Year must be between 2020 and 2100');
  }

  // NumDays required
  if (!state.temporalScope.numDays || state.temporalScope.numDays < 1) {
    errors.push('Number of days must be at least 1');
  }

  // Date range required
  if (!state.temporalScope.targetPeriod.start || !state.temporalScope.targetPeriod.end) {
    errors.push('Target period start and end dates are required');
  }

  // Employee model required
  if (!state.employees.model || !['team', 'competency'].includes(state.employees.model)) {
    errors.push('Employee model (Team or Competency) must be selected');
  }

  // Work period model required
  if (!state.demand.workPeriodModel || !['fixed', 'flexible'].includes(state.demand.workPeriodModel)) {
    errors.push('Work period model (Fixed or Flexible) must be selected');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 2: Contracts
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep2(state) {
  const errors = [];

  // At least one contract required
  if (!state.contracts.definitions || state.contracts.definitions.length === 0) {
    errors.push('At least one contract is required');
  }

  // Validate each contract
  if (state.contracts.definitions) {
    state.contracts.definitions.forEach((contract, index) => {
      if (!contract.id) {
        errors.push(`Contract ${index + 1}: ID is required`);
      }
      if (!contract.name) {
        errors.push(`Contract ${index + 1}: Name is required`);
      }
      if (!contract.workHoursPerDay || contract.workHoursPerDay <= 0 || contract.workHoursPerDay > 24) {
        errors.push(`Contract ${index + 1}: Work hours per day must be between 0 and 24`);
      }
    });
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 3: Organizational Units
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep3(state) {
  const errors = [];

  if (state.employees.model === 'team') {
    // Team model: at least one team required
    if (!state.organizationalUnits.teams || state.organizationalUnits.teams.length === 0) {
      errors.push('At least one team is required');
    }
  } else if (state.employees.model === 'competency') {
    // Competency model: at least one competency required
    if (!state.organizationalUnits.competencies || state.organizationalUnits.competencies.length === 0) {
      errors.push('At least one competency is required');
    }
  } else {
    errors.push('Employee model not selected (required for organizational units)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 4: Employees
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep4(state) {
  const errors = [];

  if (state.employees.model === 'team') {
    // Team model validation
    if (!state.employees.simple || state.employees.simple.length === 0) {
      errors.push('At least one employee is required');
    } else {
      state.employees.simple.forEach((emp, index) => {
        if (!emp.id) {
          errors.push(`Employee ${index + 1}: ID is required`);
        }
        if (!emp.teams || emp.teams.length === 0) {
          errors.push(`Employee ${index + 1}: At least one team is required`);
        }
        if (!emp.contractType) {
          errors.push(`Employee ${index + 1}: Contract type is required`);
        }
      });
    }
  } else if (state.employees.model === 'competency') {
    // Competency model validation
    if (!state.employees.competency || state.employees.competency.length === 0) {
      errors.push('At least one employee is required');
    } else {
      state.employees.competency.forEach((emp, index) => {
        if (!emp.id) {
          errors.push(`Employee ${index + 1}: ID is required`);
        }
        if (!emp.competencies || emp.competencies.length === 0) {
          errors.push(`Employee ${index + 1}: At least one competency is required`);
        }
        if (!emp.contractType) {
          errors.push(`Employee ${index + 1}: Contract type is required`);
        }
      });
    }
  } else {
    errors.push('Employee model not selected (required for employees)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 5: Schedule Input
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep5(state) {
  const errors = [];

  // Optional validation: Check if schedule matrix has data
  // For now, schedule input is optional, so we just warn if empty
  if (!state.scheduleInput.dataMatrix || Object.keys(state.scheduleInput.dataMatrix).length === 0) {
    errors.push('Schedule input matrix is empty (this is optional, but you may want to add employee availability)');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 6: Work Periods
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep6(state) {
  const errors = [];

  // At least one work period required
  const validation = validateWorkPeriodsExist(state.demand.workPeriods);
  if (!validation.valid) {
    errors.push(validation.error);
  }

  // Validate each work period has required fields
  if (state.demand.workPeriods) {
    state.demand.workPeriods.forEach((wp, index) => {
      if (!wp.code) {
        errors.push(`Work period ${index + 1}: Code is required`);
      }
      if (!wp.name) {
        errors.push(`Work period ${index + 1}: Name is required`);
      }
    });
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 7: Demand
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep7(state) {
  const errors = [];

  // Optional: Demand data is optional
  // Could add validation here if demand becomes required

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 8: Constraints
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep8(state) {
  const errors = [];

  // Constraints are optional, no strict validation needed
  // Could add validation for constraint parameters if needed

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 9: Optimization
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep9(state) {
  const errors = [];

  // Optional: Check if optimization settings are configured
  // For now, optimization has defaults, so no strict validation

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validates Step 10: Review & Generate
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep10(state) {
  const errors = [];

  // Step 10 is the review step, validation happens by calling all previous steps
  const step1 = validateStep1(state);
  const step2 = validateStep2(state);
  const step3 = validateStep3(state);
  const step4 = validateStep4(state);
  const step6 = validateStep6(state);

  // Collect all critical errors
  if (!step1.valid) errors.push(...step1.errors.map(e => `Step 1: ${e}`));
  if (!step2.valid) errors.push(...step2.errors.map(e => `Step 2: ${e}`));
  if (!step3.valid) errors.push(...step3.errors.map(e => `Step 3: ${e}`));
  if (!step4.valid) errors.push(...step4.errors.map(e => `Step 4: ${e}`));
  if (!step6.valid) errors.push(...step6.errors.map(e => `Step 6: ${e}`));

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Main validation function - validates any step by number
 * @param {number} stepNumber - Step number (0-9)
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[]}
 */
export function validateStep(stepNumber, state) {
  switch (stepNumber) {
    case 0: return validateStep1(state);
    case 1: return validateStep2(state);
    case 2: return validateStep3(state);
    case 3: return validateStep4(state);
    case 4: return validateStep5(state);
    case 5: return validateStep6(state);
    case 6: return validateStep7(state);
    case 7: return validateStep8(state);
    case 8: return validateStep9(state);
    case 9: return validateStep10(state);
    default:
      return {
        valid: false,
        errors: [`Invalid step number: ${stepNumber}`]
      };
  }
}

/**
 * Validates all critical steps (required for generation)
 * @param {object} state - Wizard state
 * @returns {object} {valid: boolean, errors: string[], criticalSteps: number[]}
 */
export function validateAllCriticalSteps(state) {
  const criticalSteps = [0, 1, 2, 3, 5]; // Steps 1, 2, 3, 4, 6 are critical
  const allErrors = [];

  criticalSteps.forEach((stepNum) => {
    const validation = validateStep(stepNum, state);
    if (!validation.valid) {
      allErrors.push(...validation.errors.map(e => `Step ${stepNum + 1}: ${e}`));
    }
  });

  return {
    valid: allErrors.length === 0,
    errors: allErrors,
    criticalSteps
  };
}

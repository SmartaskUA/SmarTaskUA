/**
 * Master Validator - Central validation system
 *
 * This module consolidates all validation logic and provides a single
 * entry point for validating the entire wizard state.
 *
 * It runs:
 * - Individual step validators (from stepValidators.js)
 * - Cross-step validators (from crossStepValidator.js)
 * - Generates statistics and summary
 */

import {
  validateStep1,
  validateStep2,
  validateStep3,
  validateStep4,
  validateStep5,
  validateStep6,
  validateStep7,
  validateStep8,
  validateStep9
} from './stepValidators';
import { validateCrossStep } from './crossStepValidator';

/**
 * Main validation function - validates entire wizard state
 *
 * @param {object} state - Complete wizard state
 * @returns {object} Validation results
 *   {
 *     valid: boolean,
 *     errors: Array<{step, field, message, severity}>,
 *     warnings: Array<{step, field, message, severity}>,
 *     stats: {totalEmployees, totalContracts, totalWorkPeriods, dateRange}
 *   }
 */
export function validateAll(state) {
  const errors = [];
  const warnings = [];

  // Run each step validator
  const step1Result = validateStep1(state);
  const step2Result = validateStep2(state);
  const step3Result = validateStep3(state);
  const step4Result = validateStep4(state);
  const step5Result = validateStep5(state);
  const step6Result = validateStep6(state);
  const step7Result = validateStep7(state);
  const step8Result = validateStep8(state);
  const step9Result = validateStep9(state);

  // Collect errors from each step
  if (!step1Result.valid) {
    errors.push(...step1Result.errors.map(msg => createError(1, null, msg, 'error')));
  }
  if (!step2Result.valid) {
    errors.push(...step2Result.errors.map(msg => createError(2, null, msg, 'error')));
  }
  if (!step3Result.valid) {
    errors.push(...step3Result.errors.map(msg => createError(3, null, msg, 'error')));
  }
  if (!step4Result.valid) {
    errors.push(...step4Result.errors.map(msg => createError(4, null, msg, 'error')));
  }
  if (!step5Result.valid) {
    // Step 5 validation errors are usually warnings (schedule input is optional)
    warnings.push(...step5Result.errors.map(msg => createError(5, null, msg, 'warning')));
  }
  if (!step6Result.valid) {
    errors.push(...step6Result.errors.map(msg => createError(6, null, msg, 'error')));
  }
  if (!step7Result.valid) {
    errors.push(...step7Result.errors.map(msg => createError(7, null, msg, 'error')));
  }
  if (!step8Result.valid) {
    // Step 8 validation errors are usually warnings (constraints are optional)
    warnings.push(...step8Result.errors.map(msg => createError(8, null, msg, 'warning')));
  }
  if (!step9Result.valid) {
    // Step 9 validation errors are usually warnings (optimization has defaults)
    warnings.push(...step9Result.errors.map(msg => createError(9, null, msg, 'warning')));
  }

  // Run cross-step validation
  try {
    const crossStepResult = validateCrossStep(state);
    if (crossStepResult.errors && crossStepResult.errors.length > 0) {
      errors.push(...crossStepResult.errors);
    }
    if (crossStepResult.warnings && crossStepResult.warnings.length > 0) {
      warnings.push(...crossStepResult.warnings);
    }
  } catch (error) {
    console.error('Cross-step validation error:', error);
    errors.push(createError(0, 'cross-validation', `Cross-validation failed: ${error.message}`, 'error'));
  }

  // Calculate statistics
  const stats = calculateStats(state);

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    stats
  };
}

/**
 * Create standardized error/warning object
 *
 * @param {number} step - Step number (1-10)
 * @param {string} field - Field name (optional)
 * @param {string} message - Error message
 * @param {string} severity - 'error' or 'warning'
 * @returns {object} Error object
 */
export function createError(step, field, message, severity = 'error') {
  return {
    step,
    field,
    message,
    severity,
    timestamp: new Date().toISOString()
  };
}

/**
 * Calculate statistics from wizard state
 *
 * @param {object} state - Wizard state
 * @returns {object} Statistics
 */
function calculateStats(state) {
  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;

  const totalEmployees = employees?.length || 0;
  const totalContracts = state.contracts?.definitions?.length || 0;
  const totalWorkPeriods = state.demand?.workPeriods?.length || 0;
  const dateRange = state.temporalScope?.numDays || 0;

  // Calculate organizational units
  const totalTeams = state.organizationalUnits?.teams?.length || 0;
  const totalCompetencies = state.organizationalUnits?.competencies?.length || 0;

  // Calculate demand entries
  const totalDemandEntries = state.demand?.demandData?.length || 0;

  // Calculate schedule input coverage
  let scheduleInputCoverage = 0;
  if (state.scheduleInput?.dataMatrix) {
    const matrix = state.scheduleInput.dataMatrix;
    const totalCells = totalEmployees * dateRange;
    let filledCells = 0;

    Object.values(matrix).forEach(empData => {
      Object.values(empData).forEach(value => {
        if (value && value !== '' && value !== '-') {
          filledCells++;
        }
      });
    });

    if (totalCells > 0) {
      scheduleInputCoverage = Math.round((filledCells / totalCells) * 100);
    }
  }

  // Calculate enabled constraints
  const hardConstraintsEnabled = state.constraints?.hard?.filter(c => c.enabled).length || 0;
  const softConstraintsEnabled = state.constraints?.soft?.filter(c => c.enabled).length || 0;

  return {
    totalEmployees,
    totalContracts,
    totalWorkPeriods,
    dateRange,
    totalTeams,
    totalCompetencies,
    totalDemandEntries,
    scheduleInputCoverage,
    hardConstraintsEnabled,
    softConstraintsEnabled,
    model: state.employees?.model || 'team'
  };
}

/**
 * Validate specific step by number
 *
 * @param {number} stepNumber - Step number (1-10)
 * @param {object} state - Wizard state
 * @returns {object} Validation result {valid, errors}
 */
export function validateSpecificStep(stepNumber, state) {
  switch (stepNumber) {
    case 1:
      return validateStep1(state);
    case 2:
      return validateStep2(state);
    case 3:
      return validateStep3(state);
    case 4:
      return validateStep4(state);
    case 5:
      return validateStep5(state);
    case 6:
      return validateStep6(state);
    case 7:
      return validateStep7(state);
    case 8:
      return validateStep8(state);
    case 9:
      return validateStep9(state);
    case 10:
      return validateAll(state); // Step 10 validates everything
    default:
      return {
        valid: false,
        errors: [`Invalid step number: ${stepNumber}`]
      };
  }
}

/**
 * Check if state is ready for generation (all critical steps valid)
 *
 * @param {object} state - Wizard state
 * @returns {object} {ready: boolean, missingSteps: Array<number>}
 */
export function isReadyForGeneration(state) {
  const criticalSteps = [1, 2, 3, 4, 6, 7]; // Steps 1-4, 6-7 are critical
  const missingSteps = [];

  criticalSteps.forEach(stepNum => {
    const result = validateSpecificStep(stepNum, state);
    if (!result.valid) {
      missingSteps.push(stepNum);
    }
  });

  return {
    ready: missingSteps.length === 0,
    missingSteps
  };
}

/**
 * Export all validators for direct access
 */
export {
  validateStep1,
  validateStep2,
  validateStep3,
  validateStep4,
  validateStep5,
  validateStep6,
  validateStep7,
  validateStep8,
  validateStep9,
  validateCrossStep
};

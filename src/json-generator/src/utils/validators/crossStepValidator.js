/**
 * Cross-Step Validator
 *
 * Validates references between different steps to ensure consistency.
 * Examples:
 * - Employees reference valid contracts
 * - Demand references valid teams/competencies
 * - Schedule input references valid employees
 * - Demand references valid work periods
 */

import { createError } from './index';

/**
 * Main cross-step validation function
 *
 * @param {object} state - Complete wizard state
 * @returns {object} {errors: Array, warnings: Array}
 */
export function validateCrossStep(state) {
  const errors = [];
  const warnings = [];

  // 1. Validate employee contract references
  validateEmployeeContracts(state, errors);

  // 2. Validate demand team/competency references
  validateDemandOrganizationalUnits(state, errors);

  // 3. Validate demand work period references
  validateDemandWorkPeriods(state, errors);

  // 4. Validate schedule input employee references
  validateScheduleInputEmployees(state, warnings);

  // 5. Validate employees using 'A' have valid contracts
  validateAutoAllocateContracts(state, errors);

  // 6. Validate date ranges are consistent
  validateDateRanges(state, errors);

  return { errors, warnings };
}

/**
 * Validate that all employees reference valid contracts
 */
function validateEmployeeContracts(state, errors) {
  const contractIds = new Set(
    (state.contracts?.definitions || []).map(c => c.id)
  );

  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;

  if (!employees || employees.length === 0) return;

  employees.forEach((emp, index) => {
    if (emp.contractType && !contractIds.has(emp.contractType)) {
      errors.push(
        createError(
          4,
          `employees[${index}].contractType`,
          `Employee "${emp.id}" references non-existent contract: "${emp.contractType}"`,
          'error'
        )
      );
    }
  });
}

/**
 * Validate that all demand entries reference valid teams/competencies
 */
function validateDemandOrganizationalUnits(state, errors) {
  const teamField = state.employees?.model === 'team' ? 'team' : 'competency';
  const units = state.employees?.model === 'team'
    ? state.organizationalUnits?.teams || []
    : state.organizationalUnits?.competencies || [];

  // Create set of valid unit codes
  const unitCodes = new Set(
    units.map(u => (typeof u === 'string' ? u : u.code))
  );

  const demandData = state.demand?.demandData || [];

  demandData.forEach((entry, index) => {
    const unitValue = entry[teamField];
    if (unitValue && !unitCodes.has(unitValue)) {
      errors.push(
        createError(
          7,
          `demand.demandData[${index}].${teamField}`,
          `Demand entry references non-existent ${teamField}: "${unitValue}"`,
          'error'
        )
      );
    }
  });
}

/**
 * Validate that all demand entries reference valid work periods
 */
function validateDemandWorkPeriods(state, errors) {
  const workPeriodCodes = new Set(
    (state.demand?.workPeriods || []).map(wp => wp.code)
  );

  const demandData = state.demand?.demandData || [];

  demandData.forEach((entry, index) => {
    if (entry.workPeriod && !workPeriodCodes.has(entry.workPeriod)) {
      errors.push(
        createError(
          7,
          `demand.demandData[${index}].workPeriod`,
          `Demand entry references non-existent work period: "${entry.workPeriod}"`,
          'error'
        )
      );
    }
  });
}

/**
 * Validate that schedule input only contains data for valid employees
 * (This is a warning, not an error, as extra data can be ignored)
 */
function validateScheduleInputEmployees(state, warnings) {
  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;

  const employeeIds = new Set((employees || []).map(e => e.id));
  const scheduleMatrix = state.scheduleInput?.dataMatrix || {};

  Object.keys(scheduleMatrix).forEach(empId => {
    if (!employeeIds.has(empId)) {
      warnings.push(
        createError(
          5,
          'scheduleInput.dataMatrix',
          `Schedule contains data for non-existent employee: "${empId}"`,
          'warning'
        )
      );
    }
  });
}

/**
 * Validate that employees using 'A' (auto-allocate) have contracts with workHoursPerDay
 */
function validateAutoAllocateContracts(state, errors) {
  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;

  const contractMap = new Map(
    (state.contracts?.definitions || []).map(c => [c.id, c])
  );

  const scheduleMatrix = state.scheduleInput?.dataMatrix || {};

  Object.entries(scheduleMatrix).forEach(([empId, dates]) => {
    Object.entries(dates).forEach(([date, value]) => {
      if (value === 'A' || value === 'a') {
        const emp = (employees || []).find(e => e.id === empId);
        if (emp) {
          const contract = contractMap.get(emp.contractType);
          if (!contract) {
            errors.push(
              createError(
                5,
                `scheduleInput.dataMatrix[${empId}][${date}]`,
                `Employee "${empId}" uses 'A' on ${date} but has no contract assigned`,
                'error'
              )
            );
          } else if (!contract.workHoursPerDay || contract.workHoursPerDay <= 0) {
            errors.push(
              createError(
                5,
                `scheduleInput.dataMatrix[${empId}][${date}]`,
                `Employee "${empId}" uses 'A' on ${date} but contract "${contract.id}" has no workHoursPerDay defined`,
                'error'
              )
            );
          }
        }
      }
    });
  });
}

/**
 * Validate that dates in demand and schedule input fall within temporal scope
 */
function validateDateRanges(state, errors) {
  const startDate = state.temporalScope?.targetPeriod?.start;
  const endDate = state.temporalScope?.targetPeriod?.end;

  if (!startDate || !endDate) {
    // Can't validate without date range
    return;
  }

  const start = new Date(startDate);
  const end = new Date(endDate);

  // Validate demand dates
  const demandData = state.demand?.demandData || [];
  demandData.forEach((entry, index) => {
    if (entry.date) {
      const entryDate = new Date(entry.date);
      if (entryDate < start || entryDate > end) {
        errors.push(
          createError(
            7,
            `demand.demandData[${index}].date`,
            `Demand date ${entry.date} falls outside temporal scope (${startDate} to ${endDate})`,
            'error'
          )
        );
      }
    }
  });

  // Validate schedule input dates
  const scheduleMatrix = state.scheduleInput?.dataMatrix || {};
  Object.entries(scheduleMatrix).forEach(([empId, dates]) => {
    Object.keys(dates).forEach(date => {
      const entryDate = new Date(date);
      if (entryDate < start || entryDate > end) {
        errors.push(
          createError(
            5,
            `scheduleInput.dataMatrix[${empId}][${date}]`,
            `Schedule input date ${date} for employee "${empId}" falls outside temporal scope (${startDate} to ${endDate})`,
            'error'
          )
        );
      }
    });
  });
}

/**
 * Validate employee team assignments exist in organizational units
 */
export function validateEmployeeTeamAssignments(state, errors) {
  const teams = state.organizationalUnits?.teams || [];
  const teamCodes = new Set(teams.map(t => (typeof t === 'string' ? t : t.code)));

  const employees = state.employees?.model === 'team'
    ? state.employees.simple
    : state.employees.competency;

  if (!employees || employees.length === 0) return;

  employees.forEach((emp, index) => {
    const empTeams = emp.teams || [];
    empTeams.forEach(team => {
      const teamCode = typeof team === 'string' ? team : team.code;
      if (!teamCodes.has(teamCode)) {
        errors.push(
          createError(
            4,
            `employees[${index}].teams`,
            `Employee "${emp.id}" assigned to non-existent team: "${teamCode}"`,
            'error'
          )
        );
      }
    });
  });
}

/**
 * Validate that work period time ranges don't overlap (for fixed model)
 */
export function validateWorkPeriodOverlaps(state, warnings) {
  const workPeriods = state.demand?.workPeriods || [];

  if (state.demand?.workPeriodModel !== 'fixed') {
    // Only validate overlaps for fixed model
    return;
  }

  for (let i = 0; i < workPeriods.length; i++) {
    for (let j = i + 1; j < workPeriods.length; j++) {
      const wp1 = workPeriods[i];
      const wp2 = workPeriods[j];

      if (!wp1.timeRange || !wp2.timeRange) continue;

      const start1 = timeToMinutes(wp1.timeRange.start);
      const end1 = timeToMinutes(wp1.timeRange.end);
      const start2 = timeToMinutes(wp2.timeRange.start);
      const end2 = timeToMinutes(wp2.timeRange.end);

      // Check for overlap
      if (start1 < end2 && start2 < end1) {
        warnings.push(
          createError(
            6,
            'demand.workPeriods',
            `Work periods "${wp1.code}" and "${wp2.code}" have overlapping time ranges`,
            'warning'
          )
        );
      }
    }
  }
}

/**
 * Helper: Convert time string "HH:MM" to minutes
 */
function timeToMinutes(timeStr) {
  if (!timeStr) return 0;
  const [hours, minutes] = timeStr.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * Constraint Metadata
 *
 * Defines human-readable names, descriptions, and parameter configurations
 * for all constraint types used in the scheduling problem.
 */

export const CONSTRAINT_METADATA = {
  // ========================================
  // HARD CONSTRAINTS
  // ========================================

  max_consecutive_days: {
    name: 'Max Consecutive Days',
    description: 'Limits the maximum number of consecutive days an employee can work within a given window',
    params: {
      window: {
        label: 'Window (days)',
        type: 'number',
        min: 1,
        max: 365,
        defaultValue: 7
      },
      max_worked: {
        label: 'Max Worked Days',
        type: 'number',
        min: 1,
        max: 365,
        defaultValue: 6
      }
    }
  },

  min_rest_hours: {
    name: 'Minimum Rest Hours',
    description: 'Ensures a minimum rest period (in hours) between consecutive shifts for employee wellbeing',
    params: {
      hours: {
        label: 'Rest Hours',
        type: 'number',
        min: 0,
        max: 24,
        defaultValue: 11
      }
    }
  },

  vacation_block: {
    name: 'Vacation Blocks',
    description: 'Respects vacation blocks marked in schedule input with "VAC" marking',
    params: {}
  },

  total_workdays: {
    name: 'Total Workdays Limit',
    description: 'Limits the total number of workdays per employee within the scheduling period',
    params: {
      min: {
        label: 'Minimum Workdays',
        type: 'number',
        min: 0,
        max: 365,
        defaultValue: 0
      },
      max: {
        label: 'Maximum Workdays',
        type: 'number',
        min: 0,
        max: 365,
        defaultValue: 365
      }
    }
  },

  max_special_days: {
    name: 'Max Special Days',
    description: 'Limits work assignments on special days such as Sundays and holidays',
    params: {
      max_sundays: {
        label: 'Max Sundays',
        type: 'number',
        min: 0,
        max: 52,
        defaultValue: 52
      },
      max_holidays: {
        label: 'Max Holidays',
        type: 'number',
        min: 0,
        max: 365,
        defaultValue: 10
      }
    }
  },

  no_earlier_shift_next_day: {
    name: 'No Earlier Shift Next Day',
    description: 'Prevents assigning an earlier shift on the next day (e.g., night shift followed by morning shift)',
    params: {}
  },

  respect_contract_constraints: {
    name: 'Respect Contract Constraints',
    description: 'Enforces contract-specific rules such as weekends-only or weekdays-only assignments',
    params: {}
  },

  employee_availability: {
    name: 'Employee Availability',
    description: 'Respects employee availability constraints marked in schedule input with "NOT" marking',
    params: {}
  },

  // ========================================
  // SOFT CONSTRAINTS
  // ========================================

  min_coverage: {
    name: 'Minimum Coverage',
    description: 'Penalizes when minimum coverage requirement is not met for any work period',
    params: {
      penalty_per_missing: {
        label: 'Penalty Per Missing Employee',
        type: 'number',
        min: 1,
        max: 10000,
        defaultValue: 1000
      }
    }
  },

  ideal_coverage: {
    name: 'Ideal Coverage',
    description: 'Encourages meeting ideal coverage levels (softer than minimum coverage)',
    params: {
      penalty_per_missing: {
        label: 'Penalty Per Missing Employee',
        type: 'number',
        min: 1,
        max: 10000,
        defaultValue: 100
      }
    }
  },

  balance_workload: {
    name: 'Balance Workload',
    description: 'Distributes work hours evenly across all employees to prevent overwork or underutilization',
    params: {}
  },

  minimize_shortages: {
    name: 'Minimize Coverage Shortages',
    description: 'Reduces gaps between estimated and actual coverage across all periods',
    params: {}
  },

  prefer_experienced: {
    name: 'Prefer Experienced Employees',
    description: 'Favors assigning employees with higher competency levels (only applies to competency model)',
    params: {}
  },

  minimize_split_shifts: {
    name: 'Minimize Split Shifts',
    description: 'Reduces assignments with non-contiguous work periods on the same day',
    params: {}
  },

  respect_preferred_work_periods: {
    name: 'Respect Preferred Work Periods',
    description: 'Considers employee preferences for specific work periods when making assignments',
    params: {}
  }
};

/**
 * Get metadata for a constraint by ID or type
 * @param {string} idOrType - Constraint ID or type
 * @returns {Object|null} Metadata object or null if not found
 */
export function getConstraintMetadata(idOrType) {
  return CONSTRAINT_METADATA[idOrType] || null;
}

/**
 * Get all hard constraint IDs
 * @returns {Array<string>}
 */
export function getHardConstraintIds() {
  return [
    'max_consecutive_days',
    'min_rest_hours',
    'vacation_block',
    'total_workdays',
    'max_special_days',
    'no_earlier_shift_next_day',
    'respect_contract_constraints',
    'employee_availability'
  ];
}

/**
 * Get all soft constraint IDs
 * @returns {Array<string>}
 */
export function getSoftConstraintIds() {
  return [
    'min_coverage',
    'ideal_coverage',
    'balance_workload',
    'minimize_shortages',
    'prefer_experienced',
    'minimize_split_shifts',
    'respect_preferred_work_periods'
  ];
}

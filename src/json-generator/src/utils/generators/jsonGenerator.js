/**
 * JSON Generator - Converts wizard state to problem.json
 *
 * This module handles the conversion of the wizard's state object into
 * a valid problem.json file according to the SmarTask schema v2.2/v2.5.
 *
 * Supports:
 * - Both team and competency models
 * - Auto-detection of feature flags
 * - Optional sections (breaks, priority hierarchy, etc.)
 * - Schema v2.2 and v2.5 (with operating hours)
 */

/**
 * Main entry point: Generate complete problem.json from wizard state
 *
 * @param {object} state - Complete wizard state from WizardContext
 * @param {string} schemaVersion - "2.2" or "2.5" (default: "2.2")
 * @returns {object} Valid problem.json object
 */
export function generateProblemJson(state, schemaVersion = '2.2') {
  const problemJson = {
    schemaVersion: schemaVersion,
    problemType: state.problemType || 'employee_scheduling',
    metadata: buildMetadata(state.metadata),
    features: detectFeatures(state),
    temporalScope: buildTemporalScope(state.temporalScope),
    contracts: buildContracts(state.contracts),
    employees: buildEmployees(state.employees),
    scheduleInput: buildScheduleInputRef(state.scheduleInput),
    demand: buildDemand(state.demand, state.organizationalUnits, state.employees),
    constraints: buildConstraints(state.constraints),
    optimization: buildOptimization(state.optimization)
  };

  // v2.5 specific: Operating hours (if available)
  if (schemaVersion === '2.5' && state.operatingHours?.enabled) {
    problemJson.operatingHours = buildOperatingHours(state.operatingHours);
  }

  return problemJson;
}

/**
 * Build metadata section
 * @param {object} metadata - State metadata object
 * @returns {object} Formatted metadata
 */
function buildMetadata(metadata) {
  return {
    problemId: metadata.problemId || 'untitled_problem',
    createdAt: metadata.createdAt || new Date().toISOString(),
    description: metadata.description || '',
    source: metadata.source || 'json-generator'
  };
}

/**
 * Auto-detect feature flags from configuration
 * This eliminates the need for manual feature selection in Step 1.
 *
 * @param {object} state - Wizard state
 * @returns {object} Feature flags
 */
function detectFeatures(state) {
  return {
    useWorkPeriodBasedScheduling: (state.demand?.workPeriods?.length || 0) > 0,
    useAdvancedConstraints: state.constraints?.advanced?.dayOffSwapping?.enabled ||
                           state.constraints?.advanced?.breaks?.enabled ||
                           false,
    usePriorityHierarchy: (state.demand?.priorityHierarchy?.length || 0) > 0
  };
}

/**
 * Build temporal scope section
 * @param {object} scope - Temporal scope object
 * @returns {object} Formatted temporal scope
 */
function buildTemporalScope(scope) {
  return {
    year: scope.year || new Date().getFullYear(),
    numDays: scope.numDays || 31,
    targetPeriod: {
      start: scope.targetPeriod.start || '',
      end: scope.targetPeriod.end || ''
    }
  };
}

/**
 * Build contracts section
 * @param {object} contracts - Contracts object with definitions array
 * @returns {object} Formatted contracts
 */
function buildContracts(contracts) {
  const definitions = (contracts.definitions || []).map(contract => {
    const formatted = {
      id: contract.id,
      name: contract.name,
      workHoursPerDay: contract.workHoursPerDay
    };

    // Add optional constraints if present
    if (contract.constraints) {
      formatted.constraints = {};

      if (contract.constraints.weekendsOnly !== undefined) {
        formatted.constraints.weekendsOnly = contract.constraints.weekendsOnly;
      }
      if (contract.constraints.weekdaysOnly !== undefined) {
        formatted.constraints.weekdaysOnly = contract.constraints.weekdaysOnly;
      }
      if (contract.constraints.availableDays !== undefined) {
        formatted.constraints.availableDays = contract.constraints.availableDays;
      }
      if (contract.constraints.maxHoursPerWeek !== undefined) {
        formatted.constraints.maxHoursPerWeek = contract.constraints.maxHoursPerWeek;
      }
      if (contract.constraints.maxConsecutiveDays !== undefined) {
        formatted.constraints.maxConsecutiveDays = contract.constraints.maxConsecutiveDays;
      }
      if (contract.constraints.minRestDaysPerWeek !== undefined) {
        formatted.constraints.minRestDaysPerWeek = contract.constraints.minRestDaysPerWeek;
      }
      if (contract.constraints.flexibleHours !== undefined) {
        formatted.constraints.flexibleHours = contract.constraints.flexibleHours;
      }
    }

    return formatted;
  });

  return { definitions };
}

/**
 * Build employees section
 * Handles both team and competency models
 *
 * @param {object} employees - Employees object with model and data
 * @returns {object} Formatted employees
 */
function buildEmployees(employees) {
  const result = {
    model: employees.model || 'team'
  };

  if (employees.model === 'team') {
    // Team model: simple array of employees with team assignments
    result.simple = (employees.simple || []).map(emp => ({
      id: emp.id,
      name: emp.name || '',
      teams: emp.teams || [],
      contractType: emp.contractType
    }));
  } else if (employees.model === 'competency') {
    // Competency model: employees with competency levels
    result.competency = (employees.competency || []).map(emp => {
      const formatted = {
        id: emp.id,
        name: emp.name || '',
        teams: emp.teams || [], // Still has teams array, but with competency levels
        contractType: emp.contractType
      };

      // Add optional fields for competency model
      if (emp.contractPeriods && emp.contractPeriods.length > 0) {
        formatted.contractPeriods = emp.contractPeriods;
      }
      if (emp.restrictions) {
        formatted.restrictions = emp.restrictions;
      }

      return formatted;
    });
  }

  return result;
}

/**
 * Build schedule input reference section
 * @param {object} scheduleInput - Schedule input object
 * @returns {object} Formatted schedule input reference
 */
function buildScheduleInputRef(scheduleInput) {
  const result = {
    enabled: true,
    dataFile: scheduleInput.dataFile || 'schedule_input.csv'
  };

  // Add marking types if custom ones are defined
  const markingTypes = scheduleInput.markingTypes || {};
  const customMarkings = {};

  // Filter out standard markings (A, VAC, NOT, EQUALS, INCLUDE, EXCEPT)
  const standardMarkings = ['A', 'VAC', 'NOT', 'EQUALS', 'INCLUDE', 'EXCEPT'];

  Object.keys(markingTypes).forEach(key => {
    if (!standardMarkings.includes(key) && !key.includes(':')) {
      customMarkings[key] = markingTypes[key];
    }
  });

  if (Object.keys(customMarkings).length > 0) {
    result.markingTypes = customMarkings;
  }

  return result;
}

/**
 * Build demand section with organizational units
 *
 * @param {object} demand - Demand object
 * @param {object} organizationalUnits - Organizational units object
 * @param {object} employees - Employees object (needed to determine model)
 * @returns {object} Formatted demand
 */
function buildDemand(demand, organizationalUnits, employees) {
  const result = {
    workPeriodModel: demand.workPeriodModel || 'fixed',
    dataFile: demand.dataFile || 'demand.csv',
    workPeriods: buildWorkPeriods(demand.workPeriods || []),
    organizationalUnits: {}
  };

  // Add teams (used by both models)
  if (organizationalUnits.teams && organizationalUnits.teams.length > 0) {
    result.organizationalUnits.teams = organizationalUnits.teams.map(team => ({
      code: team.code || team,
      name: team.name || team
    }));
  }

  // Add competencies if using competency model
  if (employees.model === 'competency' && organizationalUnits.competencies && organizationalUnits.competencies.length > 0) {
    result.organizationalUnits.competencies = organizationalUnits.competencies.map(comp => ({
      code: comp.code || comp,
      name: comp.name || comp,
      level: comp.level
    }));
  }

  // Add priority hierarchy if present
  if (demand.priorityHierarchy && demand.priorityHierarchy.length > 0) {
    result.priorityHierarchy = demand.priorityHierarchy;
  }

  return result;
}

/**
 * Build work periods array
 * @param {Array} workPeriods - Array of work period objects
 * @returns {Array} Formatted work periods
 */
function buildWorkPeriods(workPeriods) {
  return workPeriods.map(wp => {
    const formatted = {
      code: wp.code,
      name: wp.name,
      order: wp.order !== undefined ? wp.order : 0
    };

    // Add time range for fixed model
    if (wp.timeRange) {
      formatted.timeRange = {
        start: wp.timeRange.start,
        end: wp.timeRange.end
      };
    }

    // Add flexible model properties
    if (wp.duration !== undefined) {
      formatted.duration = wp.duration;
    }
    if (wp.allowedStartTimes && wp.allowedStartTimes.length > 0) {
      formatted.allowedStartTimes = wp.allowedStartTimes;
    }

    // Add breaks if present
    if (wp.breaks && wp.breaks.length > 0) {
      formatted.breaks = wp.breaks.map(brk => {
        const formattedBreak = {
          type: brk.type || 'rest',
          duration: brk.duration,
          paid: brk.paid !== undefined ? brk.paid : false,
          required: brk.required !== undefined ? brk.required : true
        };

        // Add timing information based on timing mode
        if (brk.timing === 'fixed' && brk.start) {
          formattedBreak.timing = 'fixed';
          formattedBreak.start = brk.start;
        } else if (brk.timing === 'window' && brk.window) {
          formattedBreak.timing = 'window';
          formattedBreak.window = {
            start: brk.window.start,
            end: brk.window.end
          };
        } else if (brk.timing === 'after_work') {
          formattedBreak.timing = 'after_work';
          if (brk.afterHours !== undefined) {
            formattedBreak.afterHours = brk.afterHours;
          }
        }

        return formattedBreak;
      });
    }

    return formatted;
  });
}

/**
 * Build constraints section
 * @param {object} constraints - Constraints object
 * @returns {object} Formatted constraints
 */
function buildConstraints(constraints) {
  const result = {
    hard: [],
    soft: []
  };

  // Filter and format hard constraints (only enabled ones)
  if (constraints.hard && Array.isArray(constraints.hard)) {
    result.hard = constraints.hard
      .filter(c => c.enabled)
      .map(c => {
        const formatted = {
          id: c.id,
          type: c.type
        };

        // Add params if present and not empty
        if (c.params && Object.keys(c.params).length > 0) {
          formatted.params = c.params;
        }

        return formatted;
      });
  }

  // Filter and format soft constraints (only enabled ones)
  if (constraints.soft && Array.isArray(constraints.soft)) {
    result.soft = constraints.soft
      .filter(c => c.enabled)
      .map(c => {
        const formatted = {
          id: c.id,
          type: c.type,
          weight: c.weight !== undefined ? c.weight : 1
        };

        // Add params if present and not empty
        if (c.params && Object.keys(c.params).length > 0) {
          formatted.params = c.params;
        }

        return formatted;
      });
  }

  // Add advanced constraints if enabled
  if (constraints.advanced) {
    // Day off swapping
    if (constraints.advanced.dayOffSwapping?.enabled) {
      result.advanced = result.advanced || {};
      result.advanced.dayOffSwapping = {
        enabled: true,
        rules: constraints.advanced.dayOffSwapping.rules || [],
        weekDefinition: constraints.advanced.dayOffSwapping.weekDefinition || 'monday-sunday'
      };
    }

    // Breaks
    if (constraints.advanced.breaks?.enabled) {
      result.advanced = result.advanced || {};
      result.advanced.breaks = {
        enabled: true,
        mode: constraints.advanced.breaks.mode || 'with_breaks',
        rules: constraints.advanced.breaks.rules || []
      };
    }
  }

  return result;
}

/**
 * Build optimization section
 * @param {object} optimization - Optimization object
 * @returns {object} Formatted optimization
 */
function buildOptimization(optimization) {
  return {
    algorithm: optimization.algorithm || 'ILP',
    maxTimeMinutes: optimization.maxTimeMinutes !== undefined ? optimization.maxTimeMinutes : 10,
    objectives: (optimization.objectives || []).map(obj => ({
      goal: obj.goal,
      weight: obj.weight !== undefined ? obj.weight : 1,
      priority: obj.priority !== undefined ? obj.priority : 1
    }))
  };
}

/**
 * Build operating hours section (v2.5 only)
 * @param {object} operatingHours - Operating hours object
 * @returns {object} Formatted operating hours
 */
function buildOperatingHours(operatingHours) {
  return {
    enabled: true,
    dataFile: operatingHours.dataFile || 'operating_hours.csv',
    enforcement: operatingHours.enforcement || 'hard',
    validation: operatingHours.validation || {},
    options: operatingHours.options || {}
  };
}

/**
 * Export helper functions for testing
 */
export {
  buildMetadata,
  detectFeatures,
  buildTemporalScope,
  buildContracts,
  buildEmployees,
  buildScheduleInputRef,
  buildDemand,
  buildWorkPeriods,
  buildConstraints,
  buildOptimization,
  buildOperatingHours
};

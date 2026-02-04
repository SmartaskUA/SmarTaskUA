import React, { createContext, useContext, useState, useEffect } from 'react';
import { detectAllFeatures, applyAutoDetectedFeatures } from '../utils/featureDetector';

/**
 * Wizard Context - Central state management for all wizard steps
 *
 * This context manages the entire wizard state including:
 * - metadata, features, temporal scope
 * - contracts, employees, organizational units
 * - schedule input, shifts, demand
 * - constraints and optimization settings
 *
 * Feature flags are automatically detected based on user configuration,
 * eliminating the need for manual selection in Step 1.
 */

const WizardContext = createContext(null);

// Initial state structure matching schema v2.2
const initialState = {
  // Current step (0-9)
  currentStep: 0,

  // Step completion status
  stepCompleted: {
    0: false,  // Setup (Metadata + Employee Model + Dates)
    1: false,  // Contracts
    2: false,  // Organizational Units
    3: false,  // Employees
    4: false,  // Schedule Input
    5: false,  // Shifts
    6: false,  // Demand
    7: false,  // Constraints
    8: false,  // Optimization
    9: false   // Review & Generate
  },

  // Schema v2.2 data structure
  schemaVersion: '2.2',
  problemType: 'employee_scheduling',
  
  // Step 1: Quick Setup
  metadata: {
    problemId: '',
    createdAt: new Date().toISOString(),
    description: '',
    source: 'json-generator'
  },
  
  features: {
    useShiftBasedScheduling: true,
    useAdvancedConstraints: false,
    usePriorityHierarchy: false
  },
  
  temporalScope: {
    year: new Date().getFullYear(),
    numDays: 31,
    targetPeriod: {
      start: '',
      end: ''
    }
  },
  
  // Step 2: Contracts
  contracts: {
    definitions: []
    // Each definition: { id, name, workHoursPerDay, constraints }
  },
  
  // Step 3: Organizational Units (depends on model)
  employees: {
    model: 'team', // 'team' or 'competency'
    simple: [],    // for team model
    competency: [] // for competency model
  },
  
  organizationalUnits: {
    teams: [],        // for team model: ['A', 'B', 'C']
    competencies: []  // for competency model: [{code, name}]
  },
  
  // Step 4: Employees
  // (stored in employees.simple or employees.competency above)
  
  // Step 5: Schedule Input
  scheduleInput: {
    dataFile: 'schedule_input.csv',
    markingTypes: {
      'A': 'Auto-allocate from contract',
      'VAC': 'Vacation',
      'DL': 'Day off',
      'DLF': 'Fixed day off',
      'DLV': 'Variable day off',
      'EnfD': 'Sick day',
      'DO': 'Day off',
      'NOT': 'Not available',
      'Med': 'Medical',
      'DC-E': 'Special leave'
    },
    dataMatrix: {} // { employeeId: { 'YYYY-MM-DD': 'A' | '1-16' | marking } }
  },
  
  // Step 6: Shifts
  demand: {
    shiftModel: 'fixed', // 'fixed' or 'flexible'
    shifts: [],
    // Each shift: { code, name, order, timeRange: {start, end} } or { duration, allowedStartTimes }
    organizationalUnits: {
      teams: [],
      competencies: []
    },
    dataFile: 'demand.csv',
    demandData: [], // Array of { date, shift, team, minimum, ideal, estimated }
    priorityHierarchy: [] // Optional priority ordering
  },
  
  // Step 7: Demand Calendar
  // (stored in demand.demandData above)
  
  // Step 8: Constraints
  constraints: {
    hard: [],
    // Each: { id, type, params, enabled: true }
    soft: [],
    // Each: { id, type, params, weight, enabled: true }
    advanced: {
      dayOffSwapping: {
        enabled: false,
        rules: [],
        weekDefinition: 'monday-sunday'
      },
      breaks: {
        enabled: false,
        mode: 'with_breaks',
        rules: []
      }
    }
  },
  
  // Step 9: Optimization
  optimization: {
    algorithm: 'ILP',
    maxTimeMinutes: 10,
    objectives: []
    // Each: { goal, weight, priority }
  }
};

export const WizardProvider = ({ children }) => {
  // Load state from localStorage if available
  const [state, setState] = useState(() => {
    const saved = localStorage.getItem('wizardState');
    return saved ? JSON.parse(saved) : initialState;
  });

  // Auto-save to localStorage
  useEffect(() => {
    const timer = setTimeout(() => {
      localStorage.setItem('wizardState', JSON.stringify(state));
    }, 1000); // Debounce saves by 1 second

    return () => clearTimeout(timer);
  }, [state]);

  // Update specific section of state
  const updateState = (path, value) => {
    setState(prev => {
      const keys = path.split('.');
      const newState = { ...prev };
      let current = newState;
      
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      
      current[keys[keys.length - 1]] = value;
      return newState;
    });
  };

  // Navigate to step
  const goToStep = (step) => {
    if (step >= 0 && step <= 9) {
      updateState('currentStep', step);
    }
  };

  // Mark step as completed
  const completeStep = (step) => {
    setState(prev => ({
      ...prev,
      stepCompleted: {
        ...prev.stepCompleted,
        [step]: true
      }
    }));
  };

  // Reset wizard
  const resetWizard = () => {
    localStorage.removeItem('wizardState');
    setState(initialState);
  };

  // Auto-detect and update feature flags based on configuration
  const updateFeatureFlags = () => {
    const detectedFeatures = applyAutoDetectedFeatures(state, updateState);
    return detectedFeatures;
  };

  // Export data for generation
  const exportData = () => {
    // Auto-detect feature flags before exporting
    const detectedFeatures = detectAllFeatures(state);

    return {
      schemaVersion: state.schemaVersion,
      problemType: state.problemType,
      metadata: state.metadata,
      features: detectedFeatures, // Use auto-detected features
      temporalScope: state.temporalScope,
      contracts: state.contracts,
      employees: state.employees,
      scheduleInput: {
        dataFile: state.scheduleInput.dataFile,
        markingTypes: state.scheduleInput.markingTypes
      },
      demand: {
        shiftModel: state.demand.shiftModel,
        shifts: state.demand.shifts,
        organizationalUnits: state.employees.model === 'team'
          ? { teams: state.organizationalUnits.teams }
          : { competencies: state.organizationalUnits.competencies },
        dataFile: state.demand.dataFile,
        priorityHierarchy: state.demand.priorityHierarchy
      },
      constraints: state.constraints,
      optimization: state.optimization
    };
  };

  const value = {
    state,
    setState,
    updateState,
    goToStep,
    completeStep,
    resetWizard,
    exportData,
    updateFeatureFlags
  };

  return (
    <WizardContext.Provider value={value}>
      {children}
    </WizardContext.Provider>
  );
};

// Custom hook to use wizard context
export const useWizard = () => {
  const context = useContext(WizardContext);
  if (!context) {
    throw new Error('useWizard must be used within WizardProvider');
  }
  return context;
};

export default WizardContext;

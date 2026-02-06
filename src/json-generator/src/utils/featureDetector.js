/**
 * Feature Detector Utility
 *
 * Automatically detects which feature flags should be enabled based on
 * the actual configuration the user has created in the wizard.
 *
 * This eliminates the need for users to manually select feature flags upfront.
 */

/**
 * Auto-detect if work period-based scheduling should be enabled
 * @param {Object} state - The wizard state
 * @returns {boolean} - True if work periods are defined
 */
export const detectWorkPeriodBasedScheduling = (state) => {
  // If user has defined any work periods in Step 6, enable work period-based scheduling
  return state.demand?.workPeriods?.length > 0;
};

/**
 * Auto-detect if advanced constraints should be enabled
 * @param {Object} state - The wizard state
 * @returns {boolean} - True if day-off swapping or break rules are configured
 */
export const detectAdvancedConstraints = (state) => {
  // Check if day-off swapping is enabled
  const dayOffSwappingEnabled = state.constraints?.advanced?.dayOffSwapping?.enabled || false;

  // Check if break rules are enabled
  const breakRulesEnabled = state.constraints?.advanced?.breaks?.enabled || false;

  // Check if any work period has breaks defined
  const workPeriodsWithBreaks = state.demand?.workPeriods?.some(workPeriod =>
    workPeriod.breaks && workPeriod.breaks.length > 0
  ) || false;

  return dayOffSwappingEnabled || breakRulesEnabled || workPeriodsWithBreaks;
};

/**
 * Auto-detect if priority hierarchy should be enabled
 * @param {Object} state - The wizard state
 * @returns {boolean} - True if priority hierarchy is defined
 */
export const detectPriorityHierarchy = (state) => {
  // Check if priority hierarchy is defined in demand
  return (state.demand?.priorityHierarchy?.length > 0) || false;
};

/**
 * Detect all feature flags at once and return updated feature object
 * @param {Object} state - The wizard state
 * @returns {Object} - Updated features object with auto-detected values
 */
export const detectAllFeatures = (state) => {
  return {
    useWorkPeriodBasedScheduling: detectWorkPeriodBasedScheduling(state),
    useAdvancedConstraints: detectAdvancedConstraints(state),
    usePriorityHierarchy: detectPriorityHierarchy(state)
  };
};

/**
 * Update state with auto-detected feature flags
 * @param {Object} state - The current wizard state
 * @param {Function} updateState - The updateState function from WizardContext
 */
export const applyAutoDetectedFeatures = (state, updateState) => {
  const detectedFeatures = detectAllFeatures(state);

  // Update each feature flag individually
  Object.keys(detectedFeatures).forEach(featureName => {
    updateState(`features.${featureName}`, detectedFeatures[featureName]);
  });

  return detectedFeatures;
};

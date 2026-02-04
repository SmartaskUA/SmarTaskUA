/**
 * Feature Detector Utility
 *
 * Automatically detects which feature flags should be enabled based on
 * the actual configuration the user has created in the wizard.
 *
 * This eliminates the need for users to manually select feature flags upfront.
 */

/**
 * Auto-detect if shift-based scheduling should be enabled
 * @param {Object} state - The wizard state
 * @returns {boolean} - True if shifts are defined
 */
export const detectShiftBasedScheduling = (state) => {
  // If user has defined any shifts in Step 6, enable shift-based scheduling
  return state.demand?.shifts?.length > 0;
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

  // Check if any shift has breaks defined
  const shiftsWithBreaks = state.demand?.shifts?.some(shift =>
    shift.breaks && shift.breaks.length > 0
  ) || false;

  return dayOffSwappingEnabled || breakRulesEnabled || shiftsWithBreaks;
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
    useShiftBasedScheduling: detectShiftBasedScheduling(state),
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

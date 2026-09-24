import React, {
  createContext, useCallback, useContext, useDeferredValue, useEffect, useMemo, useState
} from 'react';
import { createInitialState, withDefaults } from '../v4/state';
import * as persistence from '../v4/persistence';
import { findingsFor, validateState } from '../v4/operations';
import { STEP_COUNT } from '../constants/wizardSteps';

/**
 * Wizard Context - the one store every step reads and writes.
 *
 * The state is shaped like the v4.0 document (see src/v4/state.js). Validation
 * runs on the bundle the state generates, so every step, the stepper and the
 * Review step read the same findings.
 */

const WizardContext = createContext(null);

/** Immutably set the value at a dotted path; `value` may be a function of the old value. */
function setIn(obj, keys, value) {
  const [key, ...rest] = keys;
  const current = obj?.[key];
  const next = rest.length ? setIn(current, rest, value) : (typeof value === 'function' ? value(current) : value);
  return Array.isArray(obj)
    ? Object.assign([...obj], { [key]: next })
    : { ...obj, [key]: next };
}

export const WizardProvider = ({ children }) => {
  const [state, setState] = useState(() => persistence.loadState() ?? createInitialState());

  // Auto-save, debounced.
  useEffect(() => {
    const timer = setTimeout(() => persistence.saveState(state), 800);
    return () => clearTimeout(timer);
  }, [state]);

  const updateState = useCallback((path, value) => {
    setState((prev) => setIn(prev, path.split('.'), value));
  }, []);

  /** Apply a pure (state) => state transform, e.g. from src/v4/operations.js. */
  const transform = useCallback((fn) => setState((prev) => fn(prev)), []);

  const replaceState = useCallback((next) => setState(withDefaults(next)), []);

  const goToStep = useCallback((step) => {
    if (step >= 0 && step < STEP_COUNT) updateState('currentStep', step);
  }, [updateState]);

  const completeStep = useCallback((step) => {
    updateState('stepCompleted', (prev) => ({ ...(prev || {}), [step]: true }));
  }, [updateState]);

  const resetWizard = useCallback(() => {
    persistence.clearState();
    setState(createInitialState());
  }, []);

  // Validation lags typing by a frame instead of blocking it.
  const deferred = useDeferredValue(state);
  const validation = useMemo(() => {
    try {
      return validateState(deferred);
    } catch (exc) {
      console.error('Validation failed', exc);
      return {
        bundle: null,
        report: { ok: false, errors: [{ message: `internal error while validating: ${exc.message}`, step: 'review' }], warnings: [], stats: {} }
      };
    }
  }, [deferred]);

  const findings = useCallback((stepId) => findingsFor(validation.report, stepId), [validation]);

  const value = useMemo(() => ({
    state,
    setState,
    updateState,
    transform,
    replaceState,
    goToStep,
    completeStep,
    resetWizard,
    validation,
    findings,
    listProjects: () => persistence.listProjects(),
    saveProject: (name) => persistence.saveProject(name, state),
    deleteProject: (name) => persistence.deleteProject(name),
    loadProject: (projectState) => replaceState(projectState)
  }), [state, updateState, transform, replaceState, goToStep, completeStep, resetWizard, validation, findings]);

  return <WizardContext.Provider value={value}>{children}</WizardContext.Provider>;
};

export const useWizard = () => {
  const context = useContext(WizardContext);
  if (!context) throw new Error('useWizard must be used within WizardProvider');
  return context;
};

export default WizardContext;

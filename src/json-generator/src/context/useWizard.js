import { createContext, useContext } from 'react';

// Kept apart from WizardProvider so WizardContext.jsx exports only a component,
// which is what React Fast Refresh needs to hot-reload it.
export const WizardContext = createContext(null);

export const useWizard = () => {
  const context = useContext(WizardContext);
  if (!context) throw new Error('useWizard must be used within WizardProvider');
  return context;
};

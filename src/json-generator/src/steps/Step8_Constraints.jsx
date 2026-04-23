import React from 'react';
import { Typography, Box, Alert } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import ConstraintsList from '../components/constraints/ConstraintsList';
import { useWizard } from '../context/WizardContext';

/**
 * Step 8: Constraints & Rules
 *
 * Configure hard constraints, soft constraints, and advanced scheduling rules.
 *
 * - Hard constraints: Must be satisfied (errors if violated)
 * - Soft constraints: Preferences with configurable weights
 * - Advanced: Day-off swapping, break rules
 */
const Step8_Constraints = () => {
  const { state, updateState } = useWizard();

  const constraints = state.constraints || {
    hard: [],
    soft: [],
    advanced: {}
  };

  // Handle constraints change
  const handleConstraintsChange = (newConstraints) => {
    updateState('constraints', newConstraints);
  };

  // Count enabled constraints for summary
  const enabledHardCount = constraints.hard?.filter(c => c.enabled).length || 0;
  const enabledSoftCount = constraints.soft?.filter(c => c.enabled).length || 0;

  return (
    <Box
      sx={{
        height: 'calc(100vh - 280px)',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Constraints & Rules
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configure hard constraints, soft constraints, and advanced scheduling rules.
          These constraints control how the solver generates schedules.
        </Typography>

        {/* Quick summary */}
        {(enabledHardCount > 0 || enabledSoftCount > 0) && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Currently active: <strong>{enabledHardCount} hard</strong> and{' '}
              <strong>{enabledSoftCount} soft</strong> constraints
            </Typography>
          </Alert>
        )}
      </Box>

      {/* CONTENT - Scrollable */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          pr: 1
        }}
      >
        <StepCard>
          <ConstraintsList
            constraints={constraints}
            onChange={handleConstraintsChange}
          />
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons />
      </Box>
    </Box>
  );
};

export default Step8_Constraints;

import React, { useState, useMemo } from 'react';
import { Typography, Box, Alert } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import OrganizationalUnitTable from '../components/organizational/OrganizationalUnitTable';
import { useWizard } from '../context/WizardContext';

/**
 * Step 3: Organizational Units
 *
 * Define teams (team model) or competencies (competency model).
 * Since both now share the same {code, name} structure, we use a
 * configuration-based approach to minimize conditional logic.
 */
const Step3_OrganizationalUnits = () => {
  const { state, updateState } = useWizard();
  const [error, setError] = useState('');

  const employeeModel = state.employees.model;

  // Compute configuration based on employee model
  // This eliminates the need for if/else throughout the component
  const config = useMemo(() => {
    const isTeamModel = employeeModel === 'team';

    return {
      // State management
      stateKey: isTeamModel ? 'organizationalUnits.teams' : 'organizationalUnits.competencies',
      data: isTeamModel ? state.organizationalUnits.teams : state.organizationalUnits.competencies,

      // Labels
      labelLower: isTeamModel ? 'teams' : 'competencies',
      labelSingular: isTeamModel ? 'team' : 'competency',

      // Entity type for the generic component
      entityType: employeeModel
    };
  }, [employeeModel, state.organizationalUnits.teams, state.organizationalUnits.competencies]);

  // Single unified handler for both teams and competencies
  const handleDataChange = (newData) => {
    updateState(config.stateKey, newData);
    if (error) setError('');
  };

  // Unified validation
  const validate = () => {
    if (config.data.length === 0) {
      setError(`At least one ${config.labelSingular} is required`);
      return false;
    }
    return true;
  };

  const handleNext = () => validate();

  // Guard clause for no model selected
  if (!employeeModel) {
    return (
      <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <Typography variant="h4" gutterBottom fontWeight={600}>
            Organizational Units
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <StepCard>
            <Alert severity="warning">
              Employee model not selected. Please go back to Step 1 and select an employee model (Team or Competency).
            </Alert>
          </StepCard>
        </Box>
        <Box sx={{ flexShrink: 0, mt: 2 }}>
          <NavigationButtons nextDisabled />
        </Box>
      </Box>
    );
  }

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
          Organizational Units
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define {config.labelLower} for your organization.
        </Typography>
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
          {/* Single table component rendered dynamically */}
          <OrganizationalUnitTable
            items={config.data}
            onChange={handleDataChange}
            error={error}
            entityType={config.entityType}
          />
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons
          onNext={handleNext}
          nextDisabled={config.data.length === 0}
        />
      </Box>
    </Box>
  );
};

export default Step3_OrganizationalUnits;

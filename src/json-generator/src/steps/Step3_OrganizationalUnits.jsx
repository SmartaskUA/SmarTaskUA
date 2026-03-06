import React, { useState } from 'react';
import { Typography, Box, Alert } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import OrganizationalUnitTable from '../components/organizational/OrganizationalUnitTable';
import { useWizard } from '../context/WizardContext';

/**
 * Step 3: Organizational Units (Teams)
 *
 * Define teams for your organization. Teams are used in both employee models:
 * - Team-based model: Employees are assigned to teams
 * - Competency-based model: Employees are assigned to teams with competency levels
 */
const Step3_OrganizationalUnits = () => {
  const { state, updateState } = useWizard();
  const [error, setError] = useState('');

  const employeeModel = state.employees.model;
  const teams = state.organizationalUnits.teams || [];

  // Handler for team data changes
  const handleDataChange = (newData) => {
    updateState('organizationalUnits.teams', newData);
    if (error) setError('');
  };

  // Validation
  const validate = () => {
    if (teams.length === 0) {
      setError('At least one team is required');
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
          Teams
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define teams for your organization.
          {employeeModel === 'competency' && ' In Step 4, you will assign employees to teams with competency levels.'}
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
          {/* Single table component for teams */}
          <OrganizationalUnitTable
            items={teams}
            onChange={handleDataChange}
            error={error}
          />
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons
          onNext={handleNext}
          nextDisabled={teams.length === 0}
        />
      </Box>
    </Box>
  );
};

export default Step3_OrganizationalUnits;

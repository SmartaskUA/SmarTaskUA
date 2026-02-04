import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step3_OrganizationalUnits = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Organizational Units
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Define teams (team model) or competencies (competency model) for your organization.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Organizational Units implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step3_OrganizationalUnits;

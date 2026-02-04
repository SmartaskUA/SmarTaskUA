import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step4_Employees = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Employees
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Define your employee roster with manual entry or CSV import.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Employees implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step4_Employees;

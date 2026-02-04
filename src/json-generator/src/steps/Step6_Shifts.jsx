import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step6_Shifts = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Shift Definitions
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Define shift types, time ranges, and break rules.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Shifts implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step6_Shifts;

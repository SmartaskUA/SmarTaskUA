import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step5_ScheduleInput = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Schedule Input Matrix
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Define employee availability and work requirements in a visual matrix.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Schedule Input implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step5_ScheduleInput;

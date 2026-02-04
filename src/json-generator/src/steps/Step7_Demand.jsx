import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step7_Demand = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Demand Calendar
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Define coverage requirements for each date, shift, and team/competency.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Demand Calendar implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step7_Demand;

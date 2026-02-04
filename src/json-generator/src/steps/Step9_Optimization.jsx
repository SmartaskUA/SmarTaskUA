import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step9_Optimization = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Optimization Settings
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Configure solver algorithm, objectives, and optimization parameters.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Optimization implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step9_Optimization;

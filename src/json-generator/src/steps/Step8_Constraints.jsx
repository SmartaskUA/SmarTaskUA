import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step8_Constraints = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Constraints & Rules
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Configure hard constraints, soft constraints, and advanced scheduling rules.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Constraints implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step8_Constraints;

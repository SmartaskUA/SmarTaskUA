import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step10_ReviewGenerate = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Review & Generate
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Review your configuration, validate, and generate the JSON + CSV files.
      </Typography>
      <StepCard>
        <Typography>
          This step is coming soon! 
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Placeholder for Review & Generate implementation.
        </Typography>
      </StepCard>
      <NavigationButtons />
    </Box>
  );
};

export default Step10_ReviewGenerate;

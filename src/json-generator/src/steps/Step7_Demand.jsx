import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step7_Demand = () => {
  return (
    <Box sx={{
      height: 'calc(100vh - 280px)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Demand Calendar
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define coverage requirements for each date, shift, and team/competency.
        </Typography>
      </Box>

      {/* CONTENT - Scrollable */}
      <Box sx={{
        flexGrow: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        pr: 1
      }}>
        <StepCard>
          <Typography>
            This step is coming soon!
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 2 }}>
            Placeholder for Demand Calendar implementation.
          </Typography>
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons />
      </Box>
    </Box>
  );
};

export default Step7_Demand;

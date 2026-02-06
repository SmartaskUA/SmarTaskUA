import React from 'react';
import { Typography, Box } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';

const Step6_WorkPeriods = () => {
  return (
    <Box sx={{
      height: 'calc(100vh - 280px)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Work Period Definitions
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define work period types, time ranges, and break rules.
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
            Placeholder for Work Periods implementation.
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

export default Step6_WorkPeriods;

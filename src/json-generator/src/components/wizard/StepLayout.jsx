import React from 'react';
import { Box, Typography } from '@mui/material';
import NavigationButtons from './NavigationButtons';
import StepFindings from './StepFindings';

/**
 * The frame every step shares: a fixed header, the step's validation findings,
 * a scrolling body, and the navigation buttons pinned at the bottom.
 */
const StepLayout = ({
  stepId,
  title,
  subtitle,
  actions,
  children,
  showFindings = true,
  ...navigation
}) => (
  <Box sx={{ height: 'calc(100vh - 260px)', minHeight: 480, display: 'flex', flexDirection: 'column' }}>
    <Box sx={{ flexShrink: 0, mb: 2, display: 'flex', alignItems: 'flex-start', gap: 2 }}>
      <Box sx={{ flexGrow: 1 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>{title}</Typography>
        {subtitle && <Typography variant="body1" color="text.secondary">{subtitle}</Typography>}
      </Box>
      {actions && <Box sx={{ flexShrink: 0, display: 'flex', gap: 1 }}>{actions}</Box>}
    </Box>

    <Box sx={{ flexGrow: 1, overflowY: 'auto', overflowX: 'hidden', pr: 1 }}>
      {showFindings && stepId && <StepFindings stepId={stepId} />}
      {children}
    </Box>

    <Box sx={{ flexShrink: 0 }}>
      <NavigationButtons {...navigation} />
    </Box>
  </Box>
);

export default StepLayout;

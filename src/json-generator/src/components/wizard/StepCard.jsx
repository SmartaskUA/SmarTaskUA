import React from 'react';
import { Paper, Typography, Box } from '@mui/material';

/**
 * StepCard - Consistent card wrapper for wizard steps
 * 
 * Provides a consistent look and feel for all wizard steps
 */
const StepCard = ({ title, description, children, ...props }) => {
  return (
    <Paper
      elevation={2}
      sx={{
        p: 3,
        mb: 2,
        borderRadius: 2,
        ...props.sx
      }}
      {...props}
    >
      {(title || description) && (
        <Box mb={3}>
          {title && (
            <Typography variant="h5" gutterBottom fontWeight={600}>
              {title}
            </Typography>
          )}
          {description && (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>
      )}
      {children}
    </Paper>
  );
};

export default StepCard;

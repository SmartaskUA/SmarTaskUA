import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon
} from '@mui/icons-material';

/**
 * DayDemandSummary Component
 *
 * Collapsed view of a single day's demand in the calendar grid
 * Shows summary stats and status indicator
 * Click to expand for details
 *
 * @param {string} date - ISO date string (YYYY-MM-DD)
 * @param {Array} demandEntries - Demand entries for this date
 * @param {Array} workPeriods - Expected work periods
 * @param {Function} onClick - Called when cell is clicked
 */
const DayDemandSummary = ({ date, demandEntries = [], workPeriods = [], onClick }) => {
  // Calculate stats
  const totalMinimum = demandEntries.reduce((sum, entry) => sum + (entry.minimum || 0), 0);
  const totalIdeal = demandEntries.reduce((sum, entry) => sum + (entry.ideal || 0), 0);
  const totalEstimated = demandEntries.reduce((sum, entry) => sum + (entry.estimated || 0), 0);

  // Determine status
  const expectedEntries = workPeriods.length; // one entry per work period minimum
  const actualEntries = demandEntries.length;

  let status = 'complete'; // green
  let statusIcon = CheckIcon;
  let statusColor = '#4CAF50';
  let statusText = 'Complete';

  if (actualEntries === 0) {
    status = 'empty';
    statusIcon = ErrorIcon;
    statusColor = '#F44336';
    statusText = 'No demand';
  } else if (actualEntries < expectedEntries) {
    status = 'partial';
    statusIcon = WarningIcon;
    statusColor = '#FF9800';
    statusText = 'Partial';
  }

  // Heat map color based on total demand
  const getHeatMapColor = () => {
    if (totalMinimum === 0) return 'rgba(0,0,0,0.02)';

    // Color intensity based on total minimum coverage
    const intensity = Math.min(totalMinimum / 20, 1); // normalize to 0-1 (20 = high demand)

    if (status === 'complete') {
      return `rgba(76, 175, 80, ${0.1 + intensity * 0.3})`; // green
    } else if (status === 'partial') {
      return `rgba(255, 152, 0, ${0.1 + intensity * 0.3})`; // orange
    } else {
      return 'rgba(244, 67, 54, 0.1)'; // red
    }
  };

  const StatusIcon = statusIcon;

  return (
    <Box
      onClick={onClick}
      sx={{
        padding: 1.5,
        cursor: 'pointer',
        backgroundColor: getHeatMapColor(),
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '4px',
        transition: 'all 0.2s',
        minHeight: '80px',
        display: 'flex',
        flexDirection: 'column',
        gap: 0.5,
        '&:hover': {
          boxShadow: 2,
          transform: 'translateY(-2px)',
          borderColor: 'primary.main'
        }
      }}
    >
      {/* Date Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" fontWeight={600} color="text.secondary">
          {new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </Typography>
        <StatusIcon sx={{ fontSize: '16px', color: statusColor }} />
      </Box>

      {/* Summary Stats */}
      {actualEntries > 0 ? (
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            <Chip
              label={`Min: ${totalMinimum}`}
              size="small"
              sx={{
                height: '20px',
                fontSize: '0.7rem',
                backgroundColor: 'rgba(255,255,255,0.8)',
                fontWeight: 600
              }}
            />
            <Chip
              label={`Ideal: ${totalIdeal}`}
              size="small"
              sx={{
                height: '20px',
                fontSize: '0.7rem',
                backgroundColor: 'rgba(255,255,255,0.8)',
                fontWeight: 600
              }}
            />
          </Box>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
            {actualEntries} {actualEntries === 1 ? 'entry' : 'entries'}
          </Typography>
        </Box>
      ) : (
        <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            Click to add
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default DayDemandSummary;

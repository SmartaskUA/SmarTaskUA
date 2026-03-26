import React from 'react';
import { Box, Typography } from '@mui/material';

/**
 * TimeAxis Component
 *
 * Renders a vertical time axis from 00:00 to 24:00
 * - 30-minute slot granularity for precise positioning
 * - 1-hour visual divisions to reduce clutter
 * - Used in WeeklyTemplateBuilder
 */

const TimeAxis = ({ slotHeight = 30 }) => {
  // Generate time slots (30-minute intervals)
  const timeSlots = [];
  for (let hour = 0; hour < 24; hour++) {
    timeSlots.push({ hour, minute: 0, label: `${hour.toString().padStart(2, '0')}:00` });
    timeSlots.push({ hour, minute: 30, label: `${hour.toString().padStart(2, '0')}:30` });
  }
  // Add final 24:00 marker
  timeSlots.push({ hour: 24, minute: 0, label: '24:00' });

  return (
    <Box
      sx={{
        width: '60px',
        borderRight: '2px solid',
        borderColor: 'divider',
        backgroundColor: 'background.paper',
        flexShrink: 0
      }}
    >
      {/* Header spacer to align with day headers */}
      <Box
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 6,
          backgroundColor: 'primary.main',
          color: 'white',
          padding: '8px',
          borderBottom: '2px solid',
          borderColor: 'primary.dark',
          height: '40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600 }}>
          Time
        </Typography>
      </Box>

      {/* Time slots */}
      {timeSlots.map((slot, index) => {
        const isHourMark = slot.minute === 0;

        return (
          <Box
            key={`${slot.hour}-${slot.minute}`}
            sx={{
              height: `${slotHeight}px`,
              borderTop: isHourMark ? '1px solid' : '1px dashed',
              borderColor: isHourMark ? 'divider' : 'rgba(0,0,0,0.1)',
              position: 'relative',
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'center',
              pt: 0.5
            }}
          >
            {/* Only show label for hour marks */}
            {isHourMark && (
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.7rem',
                  color: 'text.secondary',
                  fontWeight: 500,
                  position: 'absolute',
                  top: '-8px',
                  backgroundColor: 'background.paper',
                  px: 0.5
                }}
              >
                {slot.label}
              </Typography>
            )}
          </Box>
        );
      })}
    </Box>
  );
};

export default TimeAxis;

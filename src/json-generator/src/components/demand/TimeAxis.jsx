import React from 'react';
import { Box, Typography } from '@mui/material';

export const PX_PER_MINUTE = 0.75;
export const DAY_HEIGHT = 1440 * PX_PER_MINUTE;
export const HEADER_HEIGHT = 44;

/** Hour labels down the left of the weekly template. */
const TimeAxis = () => (
  <Box sx={{ width: 56, flexShrink: 0, position: 'sticky', left: 0, zIndex: 6, bgcolor: 'background.paper', borderRight: '1px solid', borderColor: 'divider' }}>
    <Box sx={{ height: HEADER_HEIGHT, position: 'sticky', top: 0, bgcolor: 'background.paper', zIndex: 7, borderBottom: '2px solid', borderColor: 'divider' }} />
    <Box sx={{ position: 'relative', height: DAY_HEIGHT }}>
      {Array.from({ length: 24 }, (_, h) => (
        <Typography
          key={h}
          variant="caption"
          sx={{ position: 'absolute', top: h ? h * 60 * PX_PER_MINUTE - 7 : 2, right: 6, fontSize: 11, color: 'text.secondary', fontFamily: 'monospace' }}
        >
          {String(h).padStart(2, '0')}:00
        </Typography>
      ))}
    </Box>
  </Box>
);

export default TimeAxis;

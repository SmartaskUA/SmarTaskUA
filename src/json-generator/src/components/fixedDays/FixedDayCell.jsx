import React, { memo } from 'react';
import { Box, Typography, Tooltip } from '@mui/material';
import { FIXED_COLORS, cellCaption } from './fixedDayLabels';

const CONFLICT_BORDER = '2px solid #d32f2f';

/**
 * One employee-day of the fixed-days grid: the schedule_input cell it answers,
 * as a caption, and the ScheduleCode fixed there - or '·' when the day is open.
 * A click opens the grid's shared code menu.
 */
const FixedDayCell = ({ employeeId, date, cell, code, label, kind, reason, onOpen }) => {
  const open = (e) => onOpen(e.currentTarget, employeeId, date);
  const tip = kind === 'unknown' ? `ScheduleCode ${code} is not in the menu` : reason;
  const body = (
    <Box
      role="button"
      tabIndex={0}
      aria-label={`${employeeId} ${date}: ${code === null ? 'open' : `ScheduleCode ${code}`}`}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          open(e);
        }
      }}
      sx={{
        minHeight: 40,
        px: 0.75,
        py: 0.25,
        bgcolor: FIXED_COLORS[kind],
        border: reason || kind === 'unknown' ? CONFLICT_BORDER : '1px solid #e0e0e0',
        boxSizing: 'border-box',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        '&:hover': { filter: 'brightness(0.95)' },
        '&:focus-visible': { outline: '2px solid #1976d2', outlineOffset: -2 }
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 0.5 }}>
        <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary', fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {cellCaption(cell)}
        </Typography>
        {code !== null && <Typography sx={{ fontSize: '0.6rem', fontWeight: 700, color: 'text.secondary' }}>{code}</Typography>}
      </Box>
      <Typography sx={{ fontSize: 12, fontWeight: 600, textAlign: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: kind === 'open' ? 'text.disabled' : 'text.primary' }}>
        {label}
      </Typography>
    </Box>
  );
  return tip ? <Tooltip title={tip} placement="top">{body}</Tooltip> : body;
};

export default memo(FixedDayCell, (a, b) => a.cell === b.cell && a.code === b.code && a.label === b.label &&
  a.kind === b.kind && a.reason === b.reason && a.onOpen === b.onOpen);

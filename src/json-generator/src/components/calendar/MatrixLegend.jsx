import React from 'react';
import { Box, Chip, Typography, Paper } from '@mui/material';
import { KIND_COLORS } from '../scheduleInput/DayOffCodesPanel';
import { OPERATOR_COLORS } from './TimeConstraintDialog';
import { CELL_COLORS } from './MatrixCell';
import { OPERATOR_HELP } from '../../v4/constants';

const item = (label, bgcolor, key = label) => (
  <Chip key={key} size="small" label={label} sx={{ m: 0.5, bgcolor, fontWeight: 600 }} />
);

/** The cell vocabulary, built from the problem's own day-off palette. */
const MatrixLegend = ({ dayOffCodes }) => (
  <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#fafafa' }}>
    <Typography variant="subtitle2" fontWeight={600}>Legend</Typography>
    <Box sx={{ display: 'flex', flexWrap: 'wrap' }}>
      {item('A: work the contract length', CELL_COLORS.auto)}
      {item('8: exactly 8 hours (hours, not minutes)', CELL_COLORS.hours)}
      {item('blank: no assignment', CELL_COLORS.blank)}
      {item('grey: no contract covers the day', CELL_COLORS.uncovered)}
      {Object.entries(dayOffCodes).map(([code, e]) => item(`${code}: ${e.name || e.kind} (${e.kind})`, KIND_COLORS[e.kind], code))}
    </Box>
    <Box sx={{ display: 'flex', flexWrap: 'wrap' }}>
      {Object.entries(OPERATOR_HELP).map(([op, help]) => item(`${op}: ${help}`, OPERATOR_COLORS[op], op))}
    </Box>
  </Paper>
);

export default MatrixLegend;

import React from 'react';
import { Dialog, AppBar, Toolbar, IconButton, Typography, Box } from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import ScheduleMatrix from './ScheduleMatrix';
import MatrixToolbar from './MatrixToolbar';
import MatrixLegend from './MatrixLegend';

/** The schedule-input matrix, full screen. */
const ScheduleMatrixModal = ({ open, onClose, state, dates, openDays, holidays, load, onCellChange, toolbar }) => (
  <Dialog fullScreen open={open} onClose={onClose} sx={{ '& .MuiDialog-paper': { bgcolor: '#f5f5f5' } }}>
    <AppBar position="relative" elevation={1}>
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>schedule_input.csv</Typography>
        <Typography variant="body2" sx={{ mr: 2, opacity: 0.9 }}>
          {state.employees.list.length} employees × {dates.length} days · numeric cells are HOURS
        </Typography>
        <IconButton edge="end" color="inherit" onClick={onClose}><CloseIcon /></IconButton>
      </Toolbar>
    </AppBar>
    <Box sx={{ p: 2, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column', gap: 1.5, overflow: 'hidden' }}>
      <MatrixToolbar {...toolbar} />
      <Box sx={{ flexGrow: 1, overflow: 'hidden', bgcolor: 'white', borderRadius: 1, boxShadow: 1 }}>
        <ScheduleMatrix state={state} dates={dates} openDays={openDays} holidays={holidays} load={load} onCellChange={onCellChange} />
      </Box>
      <MatrixLegend dayOffCodes={state.scheduleInput.dayOffCodes} />
    </Box>
  </Dialog>
);

export default ScheduleMatrixModal;

import React from 'react';
import {
  Dialog,
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Box,
  Container
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import ScheduleMatrix from './ScheduleMatrix';
import MatrixToolbar from './MatrixToolbar';
import MatrixLegend from './MatrixLegend';

/**
 * ScheduleMatrixModal - Fullscreen modal for schedule input matrix
 *
 * Provides a larger view for easier data entry and visibility
 */
const ScheduleMatrixModal = ({
  open,
  onClose,
  employees,
  dateRange,
  dataMatrix,
  contracts,
  employeeModel,
  onChange,
  onImportCsv,
  onExportCsv,
  onClearAll
}) => {
  return (
    <Dialog
      fullScreen
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDialog-paper': {
          backgroundColor: '#f5f5f5'
        }
      }}
    >
      {/* Header AppBar */}
      <AppBar
        position="relative"
        elevation={1}
        sx={{ bgcolor: 'primary.main' }}
      >
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
            Schedule Input Calendar
          </Typography>
          <Typography variant="body2" sx={{ mr: 2, opacity: 0.9 }}>
            {employees.length} employees × {dateRange.length} days
          </Typography>
          <IconButton
            edge="end"
            color="inherit"
            onClick={onClose}
            aria-label="close"
          >
            <CloseIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Content */}
      <Container
        maxWidth={false}
        sx={{
          py: 3,
          px: 4,
          height: 'calc(100vh - 64px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Toolbar */}
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <MatrixToolbar
            onImportCsv={onImportCsv}
            onExportCsv={onExportCsv}
            onClearAll={onClearAll}
          />
        </Box>

        {/* Matrix - Scrollable */}
        <Box
          sx={{
            flexGrow: 1,
            overflow: 'auto',
            mb: 2,
            bgcolor: 'white',
            borderRadius: 1,
            boxShadow: 1
          }}
        >
          <ScheduleMatrix
            employees={employees}
            dateRange={dateRange}
            dataMatrix={dataMatrix}
            contracts={contracts}
            onChange={onChange}
            employeeModel={employeeModel}
          />
        </Box>

        {/* Legend - Fixed at bottom */}
        <Box sx={{ flexShrink: 0 }}>
          <MatrixLegend />
        </Box>
      </Container>
    </Dialog>
  );
};

export default ScheduleMatrixModal;

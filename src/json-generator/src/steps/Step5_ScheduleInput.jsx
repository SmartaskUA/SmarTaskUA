import React, { useState, useMemo, useEffect } from 'react';
import { Typography, Box, Alert, Button, Paper, Chip } from '@mui/material';
import { CalendarMonth as CalendarIcon } from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import ScheduleMatrixModal from '../components/calendar/ScheduleMatrixModal';
import { useWizard } from '../context/WizardContext';
import { generateDateRange } from '../utils/helpers/dateHelpers';
import { downloadScheduleInputCsv } from '../utils/generators/scheduleInputCsvGenerator';
import { parseScheduleInputCsv } from '../utils/parsers/scheduleInputCsvParser';

/**
 * Step 5: Schedule Input Matrix
 *
 * Define employee availability and work requirements in a visual matrix.
 * Supports 4 options:
 * - 'A' for auto-allocate from contract
 * - Specific hours (from employee's contract)
 * - 'VAC' for vacation
 * - 'NOT' for not available
 */
const Step5_ScheduleInput = () => {
  const { state, updateState } = useWizard();
  const [modalOpen, setModalOpen] = useState(false);

  // Get required data from state
  const employeeModel = state.employees.model;
  const employees = employeeModel === 'team' ? state.employees.simple : state.employees.competency;
  const dataMatrix = state.scheduleInput.dataMatrix || {};
  const contracts = state.contracts.definitions || [];

  // Generate date range from temporal scope
  const dateRange = useMemo(() => {
    const { start } = state.temporalScope.targetPeriod;
    const { numDays } = state.temporalScope;

    if (!start || !numDays) return [];

    return generateDateRange(start, numDays);
  }, [state.temporalScope]);

  // Auto-fill matrix with 'A' when component mounts or when employees/dates change
  useEffect(() => {
    if (employees.length > 0 && dateRange.length > 0) {
      // Check if matrix is empty or incomplete
      const existingData = Object.keys(dataMatrix).length;

      if (existingData === 0) {
        // Matrix is empty - auto-fill with 'A'
        const filled = {};
        employees.forEach(emp => {
          filled[emp.id] = {};
          dateRange.forEach(date => {
            filled[emp.id][date] = 'A'; // Default to auto-allocate
          });
        });
        updateState('scheduleInput.dataMatrix', filled);
      } else {
        // Matrix has some data - fill in missing cells
        const updated = { ...dataMatrix };
        let hasChanges = false;

        employees.forEach(emp => {
          if (!updated[emp.id]) {
            updated[emp.id] = {};
            hasChanges = true;
          }

          dateRange.forEach(date => {
            if (!updated[emp.id][date]) {
              updated[emp.id][date] = 'A';
              hasChanges = true;
            }
          });
        });

        if (hasChanges) {
          updateState('scheduleInput.dataMatrix', updated);
        }
      }
    }
  }, [employees.length, dateRange.length]); // Only run when employee count or date range changes

  // Handle cell value change
  const handleCellChange = (employeeId, date, value) => {
    const updated = {
      ...dataMatrix,
      [employeeId]: {
        ...(dataMatrix[employeeId] || {}),
        [date]: value
      }
    };

    updateState('scheduleInput.dataMatrix', updated);
  };

  // Handle export CSV
  const handleExportCsv = () => {
    try {
      downloadScheduleInputCsv(employees, dataMatrix, dateRange);
    } catch (error) {
      alert(`Export error: ${error.message}`);
    }
  };

  // Handle import CSV
  const handleImportCsv = () => {
    // For now, just show alert - full implementation would open file picker
    alert('CSV Import: Please use the browser file picker (implementation pending)');
  };

  // Handle clear all
  const handleClearAll = () => {
    // Re-fill with 'A'
    const filled = {};
    employees.forEach(emp => {
      filled[emp.id] = {};
      dateRange.forEach(date => {
        filled[emp.id][date] = 'A';
      });
    });
    updateState('scheduleInput.dataMatrix', filled);
  };

  // Validation
  const validate = () => {
    // Matrix should be auto-filled, so always valid
    return true;
  };

  const handleNext = () => {
    return validate();
  };

  // Calculate summary statistics
  const stats = useMemo(() => {
    let autoAllocate = 0;
    let specificHours = 0;
    let vacation = 0;
    let notAvailable = 0;

    Object.values(dataMatrix).forEach(empData => {
      Object.values(empData).forEach(value => {
        const val = value.toString().toUpperCase();
        if (val === 'A') autoAllocate++;
        else if (val === 'VAC') vacation++;
        else if (val === 'NOT') notAvailable++;
        else specificHours++;
      });
    });

    return { autoAllocate, specificHours, vacation, notAvailable };
  }, [dataMatrix]);

  // Guard: Check prerequisites
  if (employees.length === 0) {
    return (
      <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <Typography variant="h4" gutterBottom fontWeight={600}>
            Schedule Input Matrix
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <StepCard>
            <Alert severity="warning">
              No employees defined. Please go back to Step 4 and add employees before continuing.
            </Alert>
          </StepCard>
        </Box>
        <Box sx={{ flexShrink: 0, mt: 2 }}>
          <NavigationButtons nextDisabled />
        </Box>
      </Box>
    );
  }

  if (dateRange.length === 0) {
    return (
      <Box sx={{ height: 'calc(100vh - 280px)', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <Typography variant="h4" gutterBottom fontWeight={600}>
            Schedule Input Matrix
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <StepCard>
            <Alert severity="warning">
              No date range defined. Please go back to Step 1 and set the temporal scope (start date and number of days).
            </Alert>
          </StepCard>
        </Box>
        <Box sx={{ flexShrink: 0, mt: 2 }}>
          <NavigationButtons nextDisabled />
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{
      height: 'calc(100vh - 280px)',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Schedule Input Matrix
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define employee availability using a simplified dropdown interface. Matrix auto-filled with 'Auto-allocate'.
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
          {/* Info Alert */}
          <Alert severity="success" sx={{ mb: 3 }}>
            <Typography variant="body2" fontWeight={600} gutterBottom>
              Matrix Auto-Filled!
            </Typography>
            <Typography variant="body2">
              All cells have been automatically filled with "A - Auto-allocate". Click "Open Calendar" below to review and make changes.
            </Typography>
          </Alert>

          {/* Summary Stats */}
          <Paper sx={{ p: 2, mb: 3, bgcolor: '#fafafa' }}>
            <Typography variant="subtitle2" gutterBottom fontWeight={600}>
              Summary Statistics
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
              <Chip label={`Auto-allocate: ${stats.autoAllocate}`} color="success" size="small" />
              <Chip label={`Specific hours: ${stats.specificHours}`} color="info" size="small" />
              <Chip label={`Vacation: ${stats.vacation}`} color="warning" size="small" />
              <Chip label={`Not available: ${stats.notAvailable}`} color="error" size="small" />
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Total cells: {employees.length} employees × {dateRange.length} days = {employees.length * dateRange.length}
            </Typography>
          </Paper>

          {/* Open Calendar Button */}
          <Box sx={{ textAlign: 'center' }}>
            <Button
              variant="contained"
              size="large"
              startIcon={<CalendarIcon />}
              onClick={() => setModalOpen(true)}
              sx={{ minWidth: '250px', py: 1.5 }}
            >
              Open Calendar
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              Opens fullscreen calendar for easier viewing and editing
            </Typography>
          </Box>
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons onNext={handleNext} />
      </Box>

      {/* Schedule Matrix Modal */}
      <ScheduleMatrixModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        employees={employees}
        dateRange={dateRange}
        dataMatrix={dataMatrix}
        contracts={contracts}
        employeeModel={employeeModel}
        onChange={handleCellChange}
        onImportCsv={handleImportCsv}
        onExportCsv={handleExportCsv}
        onClearAll={handleClearAll}
      />
    </Box>
  );
};

export default Step5_ScheduleInput;

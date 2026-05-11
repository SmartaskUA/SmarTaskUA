import React, { useState, useMemo, useEffect } from 'react';
import { Typography, Box, Alert, Button, Paper, Chip } from '@mui/material';
import { CalendarMonth as CalendarIcon } from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import ScheduleMatrixModal from '../components/calendar/ScheduleMatrixModal';
import ImportPreviewModal from '../components/shared/ImportPreviewModal';
import { useWizard } from '../context/WizardContext';
import { generateDateRange } from '../utils/helpers/dateHelpers';
import { downloadScheduleInputCsv } from '../utils/generators/scheduleInputCsvGenerator';
import { parseScheduleInputCsv } from '../utils/parsers/scheduleInputCsvParser';
import { isTimeConstraint, getConstraintType } from '../utils/validators/timeConstraintValidator';

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
  const [importPreview, setImportPreview] = useState(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

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

  // Handle import CSV — receives a File object from MatrixToolbar
  const handleImportCsv = (file) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const text = e.target.result;
        const { dataMatrix: parsed, errors } = await parseScheduleInputCsv(text, employees, dateRange);

        if (!parsed && errors.length > 0) {
          alert(`CSV import failed:\n${errors.join('\n')}`);
          return;
        }

        const dateSet = new Set(dateRange);
        const empIds = new Set(employees.map(emp => emp.id));
        const previewRows = [];
        let changedCells = 0;
        let unchangedCells = 0;

        Object.entries(parsed || {}).forEach(([empId, empData]) => {
          if (!empIds.has(empId)) return;
          Object.entries(empData).forEach(([date, value]) => {
            if (!dateSet.has(date)) return;
            const current = dataMatrix[empId]?.[date];
            if (current !== value) {
              changedCells++;
              if (previewRows.length < 10) {
                const emp = employees.find(e => e.id === empId);
                previewRows.push({
                  employee: emp?.name || empId,
                  date,
                  from: current || '—',
                  to: value
                });
              }
            } else {
              unchangedCells++;
            }
          });
        });

        const summary = `${changedCells} cells will be updated, ${unchangedCells} cells unchanged.`;
        setImportPreview({ parsed, previewRows, summary, warnings: errors });
        setImportModalOpen(true);
      } catch (err) {
        alert(`Import failed: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  const handleImportConfirm = () => {
    if (!importPreview?.parsed) return;
    const merged = { ...dataMatrix };
    Object.entries(importPreview.parsed).forEach(([empId, empData]) => {
      merged[empId] = { ...(merged[empId] || {}), ...empData };
    });
    updateState('scheduleInput.dataMatrix', merged);
    setImportModalOpen(false);
    setImportPreview(null);
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

  // Calculate summary statistics — scoped to current employees × current dateRange only
  const stats = useMemo(() => {
    const dateSet = new Set(dateRange);
    const employeeIds = new Set(employees.map(e => e.id));

    let autoAllocate = 0;
    let specificHours = 0;
    let vacation = 0;
    let notAvailable = 0;
    let timeConstraints = { equals: 0, include: 0, except: 0 };
    let invalid = 0;

    Object.entries(dataMatrix).forEach(([empId, empData]) => {
      if (!employeeIds.has(empId)) return; // employee no longer in roster

      Object.entries(empData).forEach(([date, value]) => {
        if (!dateSet.has(date)) return; // date outside current range

        if (value === null || value === undefined) { invalid++; return; }

        const val = value.toString().trim();
        if (val === '' || val === '-') { invalid++; return; }

        if (isTimeConstraint(val)) {
          const type = getConstraintType(val);
          if (type === 'EQUALS') timeConstraints.equals++;
          else if (type === 'INCLUDE') timeConstraints.include++;
          else if (type === 'EXCEPT') timeConstraints.except++;
          return;
        }

        const valUpper = val.toUpperCase();
        if (valUpper === 'A') {
          autoAllocate++;
        } else if (valUpper === 'VAC') {
          vacation++;
        } else if (valUpper === 'NOT') {
          notAvailable++;
        } else {
          const numVal = parseFloat(val);
          if (!isNaN(numVal) && numVal > 0 && numVal <= 24) {
            specificHours++;
          } else {
            invalid++;
          }
        }
      });
    });

    return { autoAllocate, specificHours, vacation, notAvailable, timeConstraints, invalid };
  }, [dataMatrix, dateRange, employees]);

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
              {stats.timeConstraints.equals > 0 && (
                <Chip label={`EQUALS: ${stats.timeConstraints.equals}`} size="small" sx={{ bgcolor: '#e1bee7', color: '#4a148c' }} />
              )}
              {stats.timeConstraints.include > 0 && (
                <Chip label={`INCLUDE: ${stats.timeConstraints.include}`} size="small" sx={{ bgcolor: '#ffe0b2', color: '#e65100' }} />
              )}
              {stats.timeConstraints.except > 0 && (
                <Chip label={`EXCEPT: ${stats.timeConstraints.except}`} size="small" sx={{ bgcolor: '#f8bbd0', color: '#880e4f' }} />
              )}
              {stats.invalid > 0 && (
                <Chip label={`Pending: ${stats.invalid}`} size="small" sx={{ bgcolor: '#bdbdbd', color: '#424242' }} />
              )}
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

      {/* Import Preview Confirmation Modal */}
      <ImportPreviewModal
        open={importModalOpen}
        title={`Import Preview — Schedule Matrix`}
        summary={importPreview?.summary}
        warnings={importPreview?.warnings || []}
        rows={importPreview?.previewRows || []}
        columns={[
          { field: 'employee', label: 'Employee' },
          { field: 'date', label: 'Date' },
          { field: 'from', label: 'Current Value' },
          { field: 'to', label: 'New Value' }
        ]}
        onConfirm={handleImportConfirm}
        onCancel={() => { setImportModalOpen(false); setImportPreview(null); }}
      />
    </Box>
  );
};

export default Step5_ScheduleInput;

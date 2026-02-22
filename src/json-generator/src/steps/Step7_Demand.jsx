import React, { useState, useMemo } from 'react';
import { Typography, Box, Alert, Snackbar } from '@mui/material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import DemandFilters from '../components/demand/DemandFilters';
import DemandTable from '../components/demand/DemandTable';
import DemandDefaultsDialog from '../components/demand/DemandDefaultsDialog';
import { useWizard } from '../context/WizardContext';
import { parseDemandCsv } from '../utils/parsers/demandCsvParser';
import { downloadDemandCsv, fillMissingDemandEntries } from '../utils/generators/demandCsvGenerator';
import { validateDemandExists } from '../utils/validators/demandValidator';

/**
 * Step 7: Demand Calendar
 *
 * Define coverage requirements for each date, work period, and team/competency.
 * Supports:
 * - Filter by team/competency
 * - Inline editing of demand values
 * - CSV import/export
 * - Auto-fill missing entries with defaults
 */
const Step7_Demand = () => {
  const { state, updateState } = useWizard();

  const [selectedTeam, setSelectedTeam] = useState('');
  const [defaultsDialogOpen, setDefaultsDialogOpen] = useState(false);
  const [error, setError] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  // Get data from state
  const employeeModel = state.employees.model;
  const workPeriods = state.demand.workPeriods || [];
  const demandData = state.demand.demandData || [];
  const temporalScope = state.temporalScope;

  // Get teams or competencies based on employee model
  const teams = employeeModel === 'team'
    ? state.organizationalUnits.teams || []
    : state.organizationalUnits.competencies || [];

  const teamField = employeeModel === 'team' ? 'team' : 'competency';

  // Filter demand data by selected team
  const filteredData = useMemo(() => {
    if (!selectedTeam) return demandData; // Show all when no team selected
    return demandData.filter(entry => entry[teamField] === selectedTeam);
  }, [demandData, selectedTeam, teamField]);

  // Generate all dates in temporal scope
  const allDates = useMemo(() => {
    const dates = [];
    const start = new Date(temporalScope.targetPeriod.start);
    const end = new Date(temporalScope.targetPeriod.end);

    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      dates.push(d.toISOString().split('T')[0]);
    }

    return dates;
  }, [temporalScope]);

  // Calculate missing entries count
  const missingCount = useMemo(() => {
    const totalPossible = allDates.length * workPeriods.length * teams.length;
    return totalPossible - demandData.length;
  }, [allDates, workPeriods, teams, demandData]);

  // Handle team selection change
  const handleTeamChange = (teamCode) => {
    setSelectedTeam(teamCode);
    if (error) setError('');
  };

  // Handle update demand entry
  const handleUpdate = (entry, field, value) => {
    const updatedData = demandData.map(item => {
      if (item.date === entry.date &&
          item.workPeriod === entry.workPeriod &&
          item[teamField] === entry[teamField]) {
        return { ...item, [field]: value };
      }
      return item;
    });

    updateState('demand.demandData', updatedData);
    setSnackbar({ open: true, message: 'Entry updated successfully', severity: 'success' });
  };

  // Handle delete demand entry
  const handleDelete = (entry) => {
    const updatedData = demandData.filter(item =>
      !(item.date === entry.date &&
        item.workPeriod === entry.workPeriod &&
        item[teamField] === entry[teamField])
    );

    updateState('demand.demandData', updatedData);
    setSnackbar({ open: true, message: 'Entry deleted', severity: 'info' });
  };

  // Handle add new entry (placeholder - would open a dialog)
  const handleAdd = () => {
    // For now, just show a message
    setSnackbar({
      open: true,
      message: 'Use "Auto-fill Remaining" to add entries for all combinations, or import from CSV',
      severity: 'info'
    });
  };

  // Handle CSV import
  const handleImport = async (file) => {
    try {
      const result = await parseDemandCsv(file, employeeModel);

      if (result.errors.length > 0) {
        setError(`CSV import errors:\n${result.errors.join('\n')}`);
        return;
      }

      updateState('demand.demandData', result.data);
      setSnackbar({
        open: true,
        message: `Successfully imported ${result.data.length} demand entries`,
        severity: 'success'
      });
      setError('');
    } catch (err) {
      setError(`Failed to import CSV: ${err.message}`);
    }
  };

  // Handle CSV export
  const handleExport = () => {
    downloadDemandCsv(demandData, employeeModel, 'demand.csv');
    setSnackbar({ open: true, message: 'Demand CSV exported successfully', severity: 'success' });
  };

  // Handle auto-fill button click
  const handleAutoFillClick = () => {
    if (missingCount === 0) {
      setSnackbar({
        open: true,
        message: 'No missing entries to fill. All combinations already have demand data.',
        severity: 'info'
      });
      return;
    }
    setDefaultsDialogOpen(true);
  };

  // Handle apply defaults
  const handleApplyDefaults = (defaults) => {
    const filledData = fillMissingDemandEntries(
      demandData,
      allDates,
      workPeriods,
      teams,
      defaults,
      employeeModel
    );

    updateState('demand.demandData', filledData);
    setDefaultsDialogOpen(false);
    setSnackbar({
      open: true,
      message: `Added ${missingCount} demand entries with default values`,
      severity: 'success'
    });
  };

  // Validate before allowing Next
  const handleNext = () => {
    const validation = validateDemandExists(demandData);
    if (!validation.valid) {
      setError(validation.error);
      return false;
    }
    return true;
  };

  return (
    <Box
      sx={{
        height: 'calc(100vh - 280px)',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Demand Calendar
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define coverage requirements for each date, work period, and {employeeModel === 'team' ? 'team' : 'competency'}.
        </Typography>
      </Box>

      {/* CONTENT - Scrollable */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          pr: 1
        }}
      >
        <StepCard>
          {/* Filters and actions */}
          <DemandFilters
            selectedTeam={selectedTeam}
            onTeamChange={handleTeamChange}
            teams={teams}
            workPeriods={workPeriods}
            onImport={handleImport}
            onExport={handleExport}
            onAutoFill={handleAutoFillClick}
            onAdd={handleAdd}
            employeeModel={employeeModel}
            demandDataCount={demandData.length}
          />

          {/* Demand table */}
          <DemandTable
            demandData={demandData}
            filteredData={filteredData}
            workPeriods={workPeriods}
            selectedTeam={selectedTeam}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
            onAdd={handleAdd}
            employeeModel={employeeModel}
          />

          {/* Error message */}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}

          {/* Help text */}
          <Box sx={{ mt: 3 }}>
            <Alert severity="info">
              <Typography variant="body2">
                <strong>Tip:</strong> Demand specifies <strong>how many people</strong> are needed for each work period.
                The three values represent: <strong>minimum</strong> (hard constraint), <strong>ideal</strong> (soft constraint),
                and <strong>estimated</strong> (expected). Rule: minimum ≤ estimated ≤ ideal.
              </Typography>
            </Alert>
          </Box>
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons
          onNext={handleNext}
          nextDisabled={demandData.length === 0}
        />
      </Box>

      {/* Defaults dialog */}
      <DemandDefaultsDialog
        open={defaultsDialogOpen}
        onClose={() => setDefaultsDialogOpen(false)}
        onApply={handleApplyDefaults}
        missingCount={missingCount}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
};

export default Step7_Demand;

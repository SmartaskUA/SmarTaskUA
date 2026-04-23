import React, { useState, useMemo } from 'react';
import {
  Typography,
  Box,
  Tabs,
  Tab,
  Alert,
  Snackbar,
  Chip
} from '@mui/material';
import {
  CalendarViewWeek as WeekIcon,
  CalendarMonth as MonthIcon
} from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import WeeklyTemplateBuilder from '../components/demand/WeeklyTemplateBuilder';
import DemandCalendarGrid from '../components/demand/DemandCalendarGrid';
import DemandCalendarToolbar from '../components/demand/DemandCalendarToolbar';
import ImportPreviewModal from '../components/shared/ImportPreviewModal';
import { useWizard } from '../context/WizardContext';
import { parseDemandCsv } from '../utils/parsers/demandCsvParser';
import { downloadDemandCsv } from '../utils/generators/demandCsvGenerator';
import { validateDemandExists } from '../utils/validators/demandValidator';
import {
  applyWeeklyTemplate,
  isTemplateEmpty,
  getTemplateSummary
} from '../utils/helpers/templateHelpers';

/**
 * Step 7: Demand Calendar (COMPLETE REMAKE)
 *
 * Two-phase visual calendar system:
 * - Phase 1 (Weekly Template): Build visual weekly demand pattern
 * - Phase 2 (Full Calendar): Apply template to all dates and customize
 *
 * Features:
 * - Visual time-based blocks with drag-drop
 * - Color-coded by team
 * - Min/Ideal/Estimated coverage values
 * - Smart time snapping (fixed vs flexible work periods)
 * - CSV import/export
 */
const Step7_Demand = () => {
  const { state, updateState } = useWizard();

  const [activeTab, setActiveTab] = useState(0); // 0 = Phase 1, 1 = Phase 2
  const [error, setError] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [pendingDemand, setPendingDemand] = useState(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  // Get data from state
  const employeeModel = state.employees.model;
  const workPeriods = state.demand.workPeriods || [];
  const workPeriodModel = state.demand.workPeriodModel;
  const weeklyTemplate = state.demand.weeklyTemplate || {};
  const demandData = state.demand.demandData || [];
  const temporalScope = state.temporalScope;

  // Get teams (always use teams for both models)
  const teams = state.organizationalUnits.teams || [];

  // Generate all dates in temporal scope
  const allDates = useMemo(() => {
    const dates = [];
    if (!temporalScope.targetPeriod.start || !temporalScope.targetPeriod.end) {
      return [];
    }

    const start = new Date(temporalScope.targetPeriod.start);
    const end = new Date(temporalScope.targetPeriod.end);

    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      dates.push(d.toISOString().split('T')[0]);
    }

    return dates;
  }, [temporalScope]);

  // Template summary
  const templateSummary = useMemo(() => getTemplateSummary(weeklyTemplate), [weeklyTemplate]);
  const hasTemplate = !isTemplateEmpty(weeklyTemplate);

  // Handle weekly template change
  const handleTemplateChange = (newTemplate) => {
    updateState('demand.weeklyTemplate', newTemplate);
    if (error) setError('');
  };

  // Handle applying template to calendar
  const handleApplyTemplate = () => {
    if (!hasTemplate) {
      setSnackbar({
        open: true,
        message: 'No weekly template defined. Please create a template in Phase 1 first.',
        severity: 'warning'
      });
      return;
    }

    const generatedData = applyWeeklyTemplate(weeklyTemplate, allDates, employeeModel);

    updateState('demand.demandData', generatedData);
    setSnackbar({
      open: true,
      message: `Applied template to ${allDates.length} dates, generated ${generatedData.length} demand entries`,
      severity: 'success'
    });
  };

  // Handle demand update from calendar grid
  const handleUpdateDemand = (updatedEntry) => {
    const updatedData = demandData.map(entry => {
      const teamField = employeeModel === 'team' ? 'team' : 'competency';
      if (
        entry.date === updatedEntry.date &&
        entry.workPeriod === updatedEntry.workPeriod &&
        entry[teamField] === updatedEntry[teamField]
      ) {
        return updatedEntry;
      }
      return entry;
    });

    updateState('demand.demandData', updatedData);
  };

  // Handle demand deletion from calendar grid
  const handleDeleteDemand = (entryToDelete) => {
    const teamField = employeeModel === 'team' ? 'team' : 'competency';
    const updatedData = demandData.filter(entry =>
      !(entry.date === entryToDelete.date &&
        entry.workPeriod === entryToDelete.workPeriod &&
        entry[teamField] === entryToDelete[teamField])
    );

    updateState('demand.demandData', updatedData);
    setSnackbar({ open: true, message: 'Demand entry deleted', severity: 'info' });
  };

  // Handle CSV import — shows preview modal before applying
  const handleImportCSV = async (file) => {
    try {
      const result = await parseDemandCsv(file, employeeModel);

      if (result.errors.length > 0 && result.data.length === 0) {
        setError(`CSV import errors:\n${result.errors.join('\n')}`);
        return;
      }

      const teamField = employeeModel === 'team' ? 'team' : 'competency';
      const existingMap = new Map(demandData.map(e => [`${e.date}|${e.workPeriod}|${e[teamField]}`, e]));
      let newEntries = 0, modifiedEntries = 0, unchangedEntries = 0;

      result.data.forEach(entry => {
        const key = `${entry.date}|${entry.workPeriod}|${entry[teamField]}`;
        const existing = existingMap.get(key);
        if (!existing) {
          newEntries++;
        } else if (existing.minimum !== entry.minimum || existing.ideal !== entry.ideal || existing.estimated !== entry.estimated) {
          modifiedEntries++;
        } else {
          unchangedEntries++;
        }
      });

      const summary = `${newEntries} new entries, ${modifiedEntries} modified, ${unchangedEntries} unchanged. ${result.data.length} total entries in file.`;

      const previewColumns = [
        { field: 'date', label: 'Date' },
        { field: teamField, label: employeeModel === 'team' ? 'Team' : 'Competency' },
        { field: 'workPeriod', label: 'Work Period' },
        { field: 'minimum', label: 'Min' },
        { field: 'ideal', label: 'Ideal' },
        { field: 'estimated', label: 'Est.' }
      ];

      setPendingDemand({ data: result.data, columns: previewColumns, summary, warnings: result.errors });
      setImportModalOpen(true);
      setError('');
    } catch (err) {
      setError(`Failed to import CSV: ${err.message}`);
    }
  };

  const handleImportConfirm = () => {
    if (!pendingDemand) return;
    updateState('demand.demandData', pendingDemand.data);
    setSnackbar({
      open: true,
      message: `Successfully imported ${pendingDemand.data.length} demand entries`,
      severity: 'success'
    });
    setImportModalOpen(false);
    setPendingDemand(null);
  };

  // Handle CSV export
  const handleExportCSV = () => {
    downloadDemandCsv(demandData, employeeModel, 'demand.csv');
    setSnackbar({ open: true, message: 'Demand CSV exported successfully', severity: 'success' });
  };

  // Handle clear all
  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all demand data? This cannot be undone.')) {
      updateState('demand.demandData', []);
      setSnackbar({ open: true, message: 'All demand data cleared', severity: 'info' });
    }
  };

  // Validate before allowing Next
  const handleNext = () => {
    // For now, we allow proceeding even with no demand data (optional)
    // But show a warning
    if (demandData.length === 0) {
      const proceed = window.confirm(
        'You have not defined any demand requirements. This means the scheduler will not have coverage targets. Do you want to proceed anyway?'
      );
      return proceed;
    }

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
          Define coverage requirements using a two-phase approach: create a weekly template, then apply it to your full schedule.
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
          {/* Phase Tabs */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
              <Tab
                icon={<WeekIcon />}
                iconPosition="start"
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    Phase 1: Weekly Template
                    {hasTemplate && (
                      <Chip
                        label={`${templateSummary.totalBlocks} blocks`}
                        size="small"
                        color="success"
                        sx={{ height: '20px', fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                }
              />
              <Tab
                icon={<MonthIcon />}
                iconPosition="start"
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    Phase 2: Full Calendar
                    {demandData.length > 0 && (
                      <Chip
                        label={`${demandData.length} entries`}
                        size="small"
                        color="primary"
                        sx={{ height: '20px', fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                }
              />
            </Tabs>
          </Box>

          {/* Phase 1: Weekly Template Builder */}
          {activeTab === 0 && (
            <Box>
              <WeeklyTemplateBuilder
                weeklyTemplate={weeklyTemplate}
                onTemplateChange={handleTemplateChange}
                teams={teams}
                workPeriods={workPeriods}
                workPeriodModel={workPeriodModel}
                employeeModel={employeeModel}
              />

              {hasTemplate && (
                <Box sx={{ mt: 2, p: 2, backgroundColor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                    Template Summary
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip label={`${templateSummary.daysWithData} days configured`} size="small" color="primary" />
                    <Chip label={`${templateSummary.totalBlocks} total blocks`} size="small" color="primary" />
                    <Chip label={`${templateSummary.emptyDays} days empty`} size="small" variant="outlined" />
                  </Box>
                </Box>
              )}
            </Box>
          )}

          {/* Phase 2: Full Calendar */}
          {activeTab === 1 && (
            <Box>
              {/* Toolbar with template apply button */}
              <DemandCalendarToolbar
                onApplyTemplate={handleApplyTemplate}
                onImportCSV={handleImportCSV}
                onExportCSV={handleExportCSV}
                onClearAll={handleClearAll}
                totalEntries={demandData.length}
                hasTemplate={hasTemplate}
              />

              {/* Calendar Grid */}
              {allDates.length > 0 ? (
                <DemandCalendarGrid
                  dates={allDates}
                  demandData={demandData}
                  workPeriods={workPeriods}
                  onUpdate={handleUpdateDemand}
                  onDelete={handleDeleteDemand}
                  employeeModel={employeeModel}
                />
              ) : (
                <Alert severity="warning">
                  No dates defined in temporal scope. Please complete Step 1 first.
                </Alert>
              )}
            </Box>
          )}

          {/* Error message */}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons onNext={handleNext} />
      </Box>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />

      {/* Import Preview Confirmation Modal */}
      <ImportPreviewModal
        open={importModalOpen}
        title={`Import Preview — ${pendingDemand?.data?.length ?? 0} demand entries`}
        summary={pendingDemand?.summary}
        warnings={pendingDemand?.warnings || []}
        rows={pendingDemand?.data?.slice(0, 10) || []}
        columns={pendingDemand?.columns || []}
        onConfirm={handleImportConfirm}
        onCancel={() => { setImportModalOpen(false); setPendingDemand(null); }}
      />
    </Box>
  );
};

export default Step7_Demand;

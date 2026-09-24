import React, { useMemo, useState } from 'react';
import {
  Grid, TextField, Box, Typography, Alert, Paper, Chip, Divider, MenuItem, Button, Table, TableHead,
  TableRow, TableCell, TableBody, IconButton, Checkbox, Tooltip
} from '@mui/material';
import { Add, Delete, UploadFile } from '@mui/icons-material';
import { StaticDatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format, parseISO } from 'date-fns';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import BundleImportDialog from '../components/import/BundleImportDialog';
import { DateField } from '../components/shared/fields';
import { useWizard } from '../context/WizardContext';
import { SLOT_OPTIONS, WEEKDAYS } from '../v4/constants';
import { rosterCodeFromProblemId } from '../v4/state';
import { dateRange, weekdayName } from '../v4/core';
import { outsideScope, pruneOutsideScope } from '../v4/operations';

const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * Step 1: Setup — metadata, the slot grid, the horizon and the calendar.
 */
const Step1_Setup = () => {
  const { state, updateState, transform } = useWizard();
  const { metadata, timeGrid, temporalScope, calendar } = state;
  const [importOpen, setImportOpen] = useState(false);
  const [selectingStart, setSelectingStart] = useState(!temporalScope.start || !!temporalScope.end);

  const days = useMemo(() => dateRange(temporalScope.start, temporalScope.end), [temporalScope]);
  const stray = useMemo(() => outsideScope(state), [state]);
  const derivedRoster = rosterCodeFromProblemId(metadata.problemId);

  const handleProblemId = (value) => {
    // Keep rosterCode tracking problemId until the user sets their own.
    const tracking = !metadata.rosterCode || metadata.rosterCode === rosterCodeFromProblemId(metadata.problemId);
    updateState('metadata', { ...metadata, problemId: value, ...(tracking && { rosterCode: rosterCodeFromProblemId(value) }) });
  };

  const handleDate = (date) => {
    if (!date) return;
    const iso = format(date, 'yyyy-MM-dd');
    if (selectingStart || !temporalScope.start) {
      updateState('temporalScope', { start: iso, end: temporalScope.end && temporalScope.end >= iso ? temporalScope.end : '' });
      setSelectingStart(false);
    } else if (iso >= temporalScope.start) {
      updateState('temporalScope', { ...temporalScope, end: iso });
      setSelectingStart(true);
    }
  };

  const setHoliday = (i, patch) => updateState('calendar.holidays', (list) =>
    list.map((h, j) => (j === i ? { ...h, ...patch } : h)));

  const addHoliday = () => updateState('calendar.holidays', (list) =>
    [...(list || []), { date: temporalScope.start || '', code: '', name: '', hasEve: false }]);

  const handleNext = () => !!metadata.problemId.trim() && days.length > 0;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <StepLayout
        stepId="setup"
        title="Setup"
        subtitle="The problem's identity, the time grid every duration must fit, the horizon and its calendar."
        actions={(
          <Button variant="outlined" startIcon={<UploadFile />} onClick={() => setImportOpen(true)}>
            Start from a v4 bundle…
          </Button>
        )}
        onNext={handleNext}
        nextDisabled={!metadata.problemId.trim() || !days.length}
      >
        <StepCard>
          <Grid container spacing={4}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Typography variant="h6" fontWeight={600} gutterBottom>Problem</Typography>
              <TextField
                fullWidth
                label="Problem ID"
                value={metadata.problemId}
                onChange={(e) => handleProblemId(e.target.value)}
                required
                error={!metadata.problemId.trim()}
                helperText="SISQUAL writes <RosterCode>_<Month>_<Year>, e.g. C2_January_2026"
                placeholder="C2_January_2026"
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Roster code"
                value={metadata.rosterCode}
                onChange={(e) => updateState('metadata.rosterCode', e.target.value)}
                placeholder={derivedRoster}
                helperText="A result's RosterCode must equal this. Defaults to the Problem ID's leading segment."
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Description"
                value={metadata.description}
                onChange={(e) => updateState('metadata.description', e.target.value)}
                sx={{ mb: 3 }}
              />

              <Divider sx={{ mb: 3 }} />
              <Typography variant="h6" fontWeight={600} gutterBottom>Time grid & week</Typography>
              <Grid container spacing={2}>
                <Grid size={6}>
                  <TextField
                    select
                    fullWidth
                    label="Slot minutes"
                    value={timeGrid.slotMinutes}
                    onChange={(e) => updateState('timeGrid.slotMinutes', Number(e.target.value))}
                    helperText="Must divide 1440. SISQUAL uses 30."
                  >
                    {SLOT_OPTIONS.map((m) => <MenuItem key={m} value={m}>{m} min</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid size={6}>
                  <TextField
                    select
                    fullWidth
                    label="Week starts on"
                    value={calendar.weekStart}
                    onChange={(e) => updateState('calendar.weekStart', e.target.value)}
                    helperText="Buckets the per-week working-day target"
                  >
                    {WEEKDAYS.map((d) => <MenuItem key={d} value={d}>{capital(d)}</MenuItem>)}
                  </TextField>
                </Grid>
              </Grid>
              <Alert severity="info" sx={{ mt: 2 }}>
                Every duration must be a multiple of the slot — contract lengths, demand windows, cell
                hours and menu boundaries. A 432-minute contract on a 30-minute grid can never be scheduled.
              </Alert>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Typography variant="h6" fontWeight={600} gutterBottom>Horizon</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {!temporalScope.start ? 'Click the first day'
                  : !selectingStart ? 'Now click the last day (inclusive)'
                    : 'Range chosen — click a day to start a new one'}
              </Typography>
              <Paper variant="outlined">
                <StaticDatePicker
                  displayStaticWrapperAs="desktop"
                  value={temporalScope.start ? parseISO(selectingStart ? temporalScope.start : temporalScope.end || temporalScope.start) : null}
                  onChange={handleDate}
                  minDate={!selectingStart && temporalScope.start ? parseISO(temporalScope.start) : undefined}
                  slotProps={{ actionBar: { actions: [] } }}
                />
              </Paper>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                {temporalScope.start && <Chip color="primary" variant="outlined" label={`Start ${temporalScope.start} (${weekdayName(temporalScope.start)})`} />}
                {temporalScope.end && <Chip color="primary" variant="outlined" label={`End ${temporalScope.end}`} />}
                {days.length > 0 && <Chip color="success" size="small" label={`${days.length} days`} />}
              </Box>
              {stray.rows + stray.holidays > 0 && (
                <Alert
                  severity="warning"
                  sx={{ mt: 2 }}
                  action={<Button color="inherit" size="small" onClick={() => transform(pruneOutsideScope)}>Remove</Button>}
                >
                  {stray.rows} demand row(s) and {stray.holidays} holiday(s) fall outside this horizon.
                </Alert>
              )}
            </Grid>
          </Grid>
        </StepCard>

        <StepCard>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Box>
              <Typography variant="h6" fontWeight={600}>Holidays</Typography>
              <Typography variant="body2" color="text.secondary">
                A holiday may carry its own demand rows; marking one makes nobody unavailable.
                &quot;Has eve&quot; says the preceding day is its eve.
              </Typography>
            </Box>
            <Button startIcon={<Add />} onClick={addHoliday} disabled={!days.length}>Add holiday</Button>
          </Box>
          {(calendar.holidays || []).length > 0 && (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Code</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell align="center">Has eve</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {calendar.holidays.map((h, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <DateField value={h.date} min={temporalScope.start} max={temporalScope.end} onChange={(v) => setHoliday(i, { date: v })} />
                    </TableCell>
                    <TableCell><TextField size="small" value={h.code || ''} onChange={(e) => setHoliday(i, { code: e.target.value })} sx={{ width: 90 }} /></TableCell>
                    <TableCell><TextField size="small" value={h.name || ''} onChange={(e) => setHoliday(i, { name: e.target.value })} /></TableCell>
                    <TableCell><TextField size="small" value={h.description || ''} onChange={(e) => setHoliday(i, { description: e.target.value })} /></TableCell>
                    <TableCell align="center">
                      <Checkbox checked={!!h.hasEve} onChange={(e) => setHoliday(i, { hasEve: e.target.checked })} />
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Remove">
                        <IconButton size="small" color="error" onClick={() => updateState('calendar.holidays', (list) => list.filter((_, j) => j !== i))}>
                          <Delete fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </StepCard>

        <BundleImportDialog open={importOpen} onClose={() => setImportOpen(false)} />
      </StepLayout>
    </LocalizationProvider>
  );
};

export default Step1_Setup;

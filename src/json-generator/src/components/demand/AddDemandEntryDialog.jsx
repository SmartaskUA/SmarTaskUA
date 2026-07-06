import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Grid,
  Alert,
  Typography,
  Box
} from '@mui/material';
import { getWorkPeriodTimeRange, validateOverrideTime } from '../../utils/helpers/demandTimeHelpers';

const AddDemandEntryDialog = ({
  open,
  onClose,
  onSave,
  date,
  workPeriods = [],
  teams = [],
  employeeModel = 'team',
  existingEntries = []
}) => {
  const teamField = employeeModel === 'team' ? 'team' : 'competency';
  const teamLabel = employeeModel === 'team' ? 'Team' : 'Competency';

  const [formData, setFormData] = useState({
    team: '',
    workPeriod: '',
    timeRange: { start: '', end: '' },
    minimum: '',
    ideal: '',
    estimated: ''
  });

  const [error, setError] = useState('');

  // Initialize on open
  useEffect(() => {
    if (!open) return;

    const firstTeam = teams.length > 0
      ? (typeof teams[0] === 'string' ? teams[0] : teams[0].code)
      : '';
    const firstWp = workPeriods.length > 0 ? workPeriods[0] : null;
    const initialTimeRange = firstWp?.timeRange
      ? { start: firstWp.timeRange.start, end: firstWp.timeRange.end }
      : { start: '', end: '' };

    setFormData({
      team: firstTeam,
      workPeriod: firstWp ? firstWp.code : '',
      timeRange: initialTimeRange,
      minimum: '',
      ideal: '',
      estimated: ''
    });
    setError('');
  }, [open]);

  // Auto-fill timeRange when work period changes
  useEffect(() => {
    if (!formData.workPeriod) return;
    const selected = workPeriods.find(wp => wp.code === formData.workPeriod);
    if (selected?.timeRange) {
      setFormData(prev => ({
        ...prev,
        timeRange: { start: selected.timeRange.start, end: selected.timeRange.end }
      }));
    }
  }, [formData.workPeriod, workPeriods]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (error) setError('');
  };

  const handleTimeChange = (field, value) => {
    setFormData(prev => ({ ...prev, timeRange: { ...prev.timeRange, [field]: value } }));
    if (error) setError('');
  };

  const handleSave = () => {
    const { team, workPeriod, timeRange, minimum, ideal, estimated } = formData;

    if (!team) { setError('Team is required'); return; }
    if (!workPeriod) { setError('Work period is required'); return; }
    if (!timeRange.start || !timeRange.end) { setError('Time range is required'); return; }

    // A per-day time that differs from the work-period default is an override —
    // it must be a valid same-day window (schema v2.6).
    const timeError = validateOverrideTime(timeRange, getWorkPeriodTimeRange(workPeriods, workPeriod));
    if (timeError) { setError(timeError); return; }

    const min = Number(minimum);
    const idl = Number(ideal);
    const est = Number(estimated);

    if (minimum === '' || ideal === '' || estimated === '') {
      setError('All coverage values are required');
      return;
    }
    if (min < 0 || idl < 0 || est < 0) {
      setError('Coverage values must be non-negative');
      return;
    }
    if (!(min <= est && est <= idl)) {
      setError('Must satisfy: minimum ≤ estimated ≤ ideal');
      return;
    }

    const isDuplicate = existingEntries.some(
      e => e.workPeriod === workPeriod && e[teamField] === team
    );
    if (isDuplicate) {
      setError('This combination already exists for this date');
      return;
    }

    onSave({
      date,
      workPeriod,
      [teamField]: team,
      minimum: min,
      ideal: idl,
      estimated: est,
      timeRange
    });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Demand Entry</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Grid container spacing={2}>
            {/* Team / Competency */}
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label={teamLabel}
                value={formData.team}
                onChange={(e) => handleChange('team', e.target.value)}
              >
                {teams.map((team) => {
                  const code = typeof team === 'string' ? team : team.code;
                  const name = typeof team === 'string' ? team : (team.name || team.code);
                  return (
                    <MenuItem key={code} value={code}>
                      {name}
                    </MenuItem>
                  );
                })}
              </TextField>
            </Grid>

            {/* Work Period */}
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label="Work Period"
                value={formData.workPeriod}
                onChange={(e) => handleChange('workPeriod', e.target.value)}
              >
                {workPeriods.map((wp) => (
                  <MenuItem key={wp.code} value={wp.code}>
                    {wp.name} ({wp.code}){wp.timeRange ? ` – ${wp.timeRange.start} to ${wp.timeRange.end}` : ''}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            {/* Time Range */}
            <Grid item xs={6}>
              <TextField
                fullWidth
                type="time"
                label="Start Time"
                value={formData.timeRange.start}
                onChange={(e) => handleTimeChange('start', e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                type="time"
                label="End Time"
                value={formData.timeRange.end}
                onChange={(e) => handleTimeChange('end', e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12}>
              <Alert severity="info" sx={{ fontSize: '0.85rem' }}>
                Auto-filled from the work period. Change it to set a per-day time override for this
                date, or leave it to use the default. Overrides must be same-day (start before end).
              </Alert>
            </Grid>

            {/* Coverage */}
            <Grid item xs={12}>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
                Coverage Requirements
              </Typography>
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                type="number"
                label="Minimum"
                value={formData.minimum}
                onChange={(e) => handleChange('minimum', e.target.value)}
                inputProps={{ min: 0, step: 1 }}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                type="number"
                label="Ideal"
                value={formData.ideal}
                onChange={(e) => handleChange('ideal', e.target.value)}
                inputProps={{ min: 0, step: 1 }}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                type="number"
                label="Estimated"
                value={formData.estimated}
                onChange={(e) => handleChange('estimated', e.target.value)}
                inputProps={{ min: 0, step: 1 }}
              />
            </Grid>

            <Grid item xs={12}>
              <Alert severity="info" sx={{ fontSize: '0.85rem' }}>
                Rule: <strong>minimum ≤ estimated ≤ ideal</strong>
              </Alert>
            </Grid>

            {error && (
              <Grid item xs={12}>
                <Alert severity="error">{error}</Alert>
              </Grid>
            )}
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="outlined">Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          Add Entry
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddDemandEntryDialog;

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
import { getTeamColor } from '../../utils/helpers/colorHelpers';

// Simple ID generator
const generateId = () => `block_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

/**
 * Calculate duration between two times (handles overnight shifts)
 */
const calculateDuration = (startTime, endTime) => {
  if (!startTime || !endTime) return 0;

  const [startHour, startMin] = startTime.split(':').map(Number);
  const [endHour, endMin] = endTime.split(':').map(Number);

  let startMinutes = startHour * 60 + startMin;
  let endMinutes = endHour * 60 + endMin;

  // If end is before start, it's an overnight shift - add 24 hours
  if (endMinutes < startMinutes) {
    endMinutes += 24 * 60;
  }

  const durationMinutes = endMinutes - startMinutes;
  const hours = Math.floor(durationMinutes / 60);
  const minutes = durationMinutes % 60;

  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
};

/**
 * DemandBlockDialog Component
 *
 * Dialog for adding or editing a demand block in the weekly template
 *
 * @param {boolean} open - Whether dialog is open
 * @param {Function} onClose - Called when dialog should close
 * @param {Function} onSave - Called with block data when saved
 * @param {Object} editBlock - Existing block to edit (null for new block)
 * @param {string} dayOfWeek - Day of week for new block (monday-sunday)
 * @param {Array} teams - Available teams/competencies
 * @param {Array} workPeriods - Available work periods from Step 6
 * @param {string} workPeriodModel - 'fixed' or 'flexible'
 * @param {string} employeeModel - 'team' or 'competency'
 */
const DemandBlockDialog = ({
  open,
  onClose,
  onSave,
  editBlock = null,
  dayOfWeek = 'monday',
  teams = [],
  workPeriods = [],
  workPeriodModel = 'fixed',
  employeeModel = 'team'
}) => {
  const isEdit = !!editBlock;

  // Form state
  const [formData, setFormData] = useState({
    team: '',
    workPeriod: '',
    timeRange: { start: '', end: '' },
    coverage: {
      minimum: '',
      ideal: '',
      estimated: ''
    }
  });

  const [errors, setErrors] = useState({});

  // Initialize form when editBlock changes or dialog opens
  useEffect(() => {
    if (editBlock) {
      setFormData({
        team: editBlock.team || '',
        workPeriod: editBlock.workPeriod || '',
        timeRange: editBlock.timeRange || { start: '', end: '' },
        coverage: editBlock.coverage || { minimum: '', ideal: '', estimated: '' }
      });
    } else {
      // Reset for new block - auto-fill time range from first work period
      const firstWorkPeriod = workPeriods.length > 0 ? workPeriods[0] : null;
      const initialTimeRange = firstWorkPeriod && firstWorkPeriod.timeRange
        ? { start: firstWorkPeriod.timeRange.start, end: firstWorkPeriod.timeRange.end }
        : { start: '', end: '' };

      setFormData({
        team: teams.length > 0 ? (typeof teams[0] === 'string' ? teams[0] : teams[0].code) : '',
        workPeriod: firstWorkPeriod ? firstWorkPeriod.code : '',
        timeRange: initialTimeRange,
        coverage: { minimum: '', ideal: '', estimated: '' }
      });
    }
    setErrors({});
  }, [editBlock, open, teams, workPeriods]);

  // Auto-fill time range when work period is selected (for both fixed and flexible)
  useEffect(() => {
    if (formData.workPeriod) {
      const selectedPeriod = workPeriods.find(wp => wp.code === formData.workPeriod);
      if (selectedPeriod && selectedPeriod.timeRange) {
        setFormData(prev => ({
          ...prev,
          timeRange: {
            start: selectedPeriod.timeRange.start,
            end: selectedPeriod.timeRange.end
          }
        }));
      }
    }
  }, [formData.workPeriod, workPeriods]);

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleCoverageChange = (field, value) => {
    const numValue = value === '' ? '' : parseInt(value, 10);
    setFormData(prev => ({
      ...prev,
      coverage: {
        ...prev.coverage,
        [field]: numValue
      }
    }));
    // Clear error for coverage
    if (errors.coverage) {
      setErrors(prev => ({ ...prev, coverage: null }));
    }
  };

  const handleTimeChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      timeRange: {
        ...prev.timeRange,
        [field]: value
      }
    }));
    if (errors.timeRange) {
      setErrors(prev => ({ ...prev, timeRange: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.team) {
      newErrors.team = 'Team is required';
    }

    if (!formData.workPeriod) {
      newErrors.workPeriod = 'Work period is required';
    }

    if (!formData.timeRange.start || !formData.timeRange.end) {
      newErrors.timeRange = 'Time range is required';
    } else if (formData.timeRange.start === formData.timeRange.end) {
      newErrors.timeRange = 'Start and end time cannot be the same';
    }
    // Note: We allow end < start for overnight shifts (e.g., 22:00-06:00 next day)

    const { minimum, ideal, estimated } = formData.coverage;
    if (minimum === '' || ideal === '' || estimated === '') {
      newErrors.coverage = 'All coverage values are required';
    } else if (minimum < 0 || ideal < 0 || estimated < 0) {
      newErrors.coverage = 'Coverage values must be non-negative';
    } else if (!(minimum <= estimated && estimated <= ideal)) {
      newErrors.coverage = 'Must satisfy: minimum ≤ estimated ≤ ideal';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;

    const blockData = {
      id: editBlock?.id || generateId(),
      dayOfWeek: editBlock?.dayOfWeek || dayOfWeek,
      team: formData.team,
      workPeriod: formData.workPeriod,
      timeRange: formData.timeRange,
      coverage: formData.coverage,
      color: getTeamColor(formData.team)
    };

    onSave(blockData);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {isEdit ? 'Edit Demand Block' : 'Add Demand Block'}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Grid container spacing={2}>
            {/* Team Selection */}
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label="Team"
                value={formData.team}
                onChange={(e) => handleChange('team', e.target.value)}
                error={!!errors.team}
                helperText={errors.team}
              >
                {teams.map((team) => {
                  const teamCode = typeof team === 'string' ? team : team.code;
                  const teamName = typeof team === 'string' ? team : team.name;
                  return (
                    <MenuItem key={teamCode} value={teamCode}>
                      {teamName || teamCode}
                    </MenuItem>
                  );
                })}
              </TextField>
            </Grid>

            {/* Work Period Selection */}
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label="Work Period"
                value={formData.workPeriod}
                onChange={(e) => handleChange('workPeriod', e.target.value)}
                error={!!errors.workPeriod}
                helperText={errors.workPeriod}
              >
                {workPeriods.map((wp) => (
                  <MenuItem key={wp.code} value={wp.code}>
                    {wp.name} ({wp.code})
                    {wp.timeRange && ` - ${wp.timeRange.start} to ${wp.timeRange.end}`}
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
                disabled={workPeriodModel === 'fixed'}
                error={!!errors.timeRange}
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
                disabled={workPeriodModel === 'fixed'}
                error={!!errors.timeRange}
                helperText={errors.timeRange}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            {/* Overnight shift indicator */}
            {formData.timeRange.start && formData.timeRange.end && formData.timeRange.start > formData.timeRange.end && (
              <Grid item xs={12}>
                <Alert severity="warning" sx={{ fontSize: '0.85rem' }}>
                  <strong>Overnight Shift:</strong> This shift spans across midnight (ends next day). Duration: {calculateDuration(formData.timeRange.start, formData.timeRange.end)} hours.
                </Alert>
              </Grid>
            )}

            <Grid item xs={12}>
              {workPeriodModel === 'fixed' ? (
                <Alert severity="info" sx={{ fontSize: '0.85rem' }}>
                  <strong>Fixed Work Periods:</strong> Time range is automatically set by the selected work period and cannot be edited.
                </Alert>
              ) : (
                <Alert severity="success" sx={{ fontSize: '0.85rem' }}>
                  <strong>Flexible Work Periods:</strong> Time range is auto-filled from the selected work period, but you can edit it to any 30-minute slot. Overnight shifts (e.g., 22:00-06:00) are supported.
                </Alert>
              )}
            </Grid>

            {/* Coverage Values */}
            <Grid item xs={12}>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                Coverage Requirements
              </Typography>
            </Grid>

            <Grid item xs={4}>
              <TextField
                fullWidth
                type="number"
                label="Minimum"
                value={formData.coverage.minimum}
                onChange={(e) => handleCoverageChange('minimum', e.target.value)}
                inputProps={{ min: 0, step: 1 }}
                error={!!errors.coverage}
              />
            </Grid>

            <Grid item xs={4}>
              <TextField
                fullWidth
                type="number"
                label="Ideal"
                value={formData.coverage.ideal}
                onChange={(e) => handleCoverageChange('ideal', e.target.value)}
                inputProps={{ min: 0, step: 1 }}
                error={!!errors.coverage}
              />
            </Grid>

            <Grid item xs={4}>
              <TextField
                fullWidth
                type="number"
                label="Estimated"
                value={formData.coverage.estimated}
                onChange={(e) => handleCoverageChange('estimated', e.target.value)}
                inputProps={{ min: 0, step: 1 }}
                error={!!errors.coverage}
              />
            </Grid>

            {errors.coverage && (
              <Grid item xs={12}>
                <Alert severity="error">{errors.coverage}</Alert>
              </Grid>
            )}

            <Grid item xs={12}>
              <Alert severity="info" sx={{ fontSize: '0.85rem' }}>
                Rule: <strong>minimum ≤ estimated ≤ ideal</strong>
              </Alert>
            </Grid>
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          {isEdit ? 'Save Changes' : 'Add Block'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DemandBlockDialog;

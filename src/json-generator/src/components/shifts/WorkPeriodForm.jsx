import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  FormControl,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
  Grid
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { parse } from 'date-fns';
import BreakBuilder from './BreakBuilder';
import { validateWorkPeriod } from '../../utils/validators/workPeriodValidator';
import { generateHourlyTimeOptions } from '../../utils/helpers/timeHelpers';

/**
 * WorkPeriodForm Component - Add/Edit work period dialog
 *
 * Adaptive form that changes based on work period model (Fixed vs Flexible)
 * - Fixed: Time range with start/end pickers
 * - Flexible: Duration + allowed start times checkboxes
 * - Both: Breaks configuration (optional, in accordion)
 */
const WorkPeriodForm = ({
  open,
  onClose,
  onSave,
  workPeriodModel,
  existingWorkPeriods = [],
  editWorkPeriod = null // If provided, we're in edit mode
}) => {
  const isEditMode = !!editWorkPeriod;

  // Form state
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    // Fixed model fields
    timeRange: {
      start: '08:00',
      end: '16:00'
    },
    // Flexible model fields
    duration: 8,
    allowedStartTimes: ['06:00', '07:00', '08:00'],
    // Breaks (optional for both models)
    breaks: []
  });

  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Initialize form data when dialog opens or edit work period changes
  useEffect(() => {
    if (editWorkPeriod) {
      setFormData(editWorkPeriod);
    } else {
      // Reset to defaults when opening for new work period
      setFormData({
        code: '',
        name: '',
        timeRange: {
          start: '08:00',
          end: '16:00'
        },
        duration: 8,
        allowedStartTimes: ['06:00', '07:00', '08:00'],
        breaks: []
      });
    }
    setErrors({});
    setTouched({});
  }, [open, editWorkPeriod, existingWorkPeriods.length]);

  // Handle text field changes
  const handleChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value
    }));
    setTouched((prev) => ({
      ...prev,
      [field]: true
    }));
  };

  // Handle time range changes (Fixed model)
  const handleTimeRangeChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      timeRange: {
        ...prev.timeRange,
        [field]: value
      }
    }));
    setTouched((prev) => ({
      ...prev,
      timeRange: true
    }));
  };

  // Parse HH:MM string to Date object for TimePicker
  const parseTime = (timeString) => {
    if (!timeString) return null;
    return parse(timeString, 'HH:mm', new Date());
  };

  // Format Date object to HH:MM string
  const formatTime = (date) => {
    if (!date) return '';
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  // Handle allowed start times checkboxes (Flexible model)
  const handleAllowedTimeToggle = (time) => {
    const currentTimes = formData.allowedStartTimes || [];
    const newTimes = currentTimes.includes(time)
      ? currentTimes.filter((t) => t !== time)
      : [...currentTimes, time].sort();

    setFormData((prev) => ({
      ...prev,
      allowedStartTimes: newTimes
    }));
    setTouched((prev) => ({
      ...prev,
      allowedStartTimes: true
    }));
  };

  // Select all allowed start times
  const handleSelectAllTimes = () => {
    setFormData((prev) => ({
      ...prev,
      allowedStartTimes: generateHourlyTimeOptions()
    }));
  };

  // Clear all allowed start times
  const handleClearAllTimes = () => {
    setFormData((prev) => ({
      ...prev,
      allowedStartTimes: []
    }));
  };

  // Handle breaks changes
  const handleBreaksChange = (newBreaks) => {
    setFormData((prev) => ({
      ...prev,
      breaks: newBreaks
    }));
  };

  // Validate form
  const validate = () => {
    const validation = validateWorkPeriod(
      formData,
      workPeriodModel,
      existingWorkPeriods,
      isEditMode ? editWorkPeriod.code : null
    );

    setErrors(validation.errors);
    return validation.valid;
  };

  // Handle save
  const handleSave = () => {
    if (!validate()) {
      return;
    }

    // Prepare work period data based on model
    const workPeriodData = {
      code: formData.code,
      name: formData.name,
      breaks: formData.breaks || []
    };

    if (workPeriodModel === 'fixed') {
      workPeriodData.timeRange = formData.timeRange;
    } else {
      workPeriodData.duration = Number(formData.duration);
      workPeriodData.allowedStartTimes = formData.allowedStartTimes;
    }

    onSave(workPeriodData);
    handleClose();
  };

  // Handle close
  const handleClose = () => {
    setFormData({
      code: '',
      name: '',
      timeRange: { start: '08:00', end: '16:00' },
      duration: 8,
      allowedStartTimes: ['06:00', '07:00', '08:00'],
      breaks: []
    });
    setErrors({});
    setTouched({});
    onClose();
  };

  // Generate hourly time options for checkboxes
  const timeOptions = generateHourlyTimeOptions();

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: '70vh' }
      }}
    >
      <DialogTitle>
        {isEditMode ? `Edit Work Period: ${editWorkPeriod?.code}` : 'Add Work Period'}
      </DialogTitle>

      <DialogContent dividers>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Model indicator */}
          <Alert severity="info">
            Model: <strong>{workPeriodModel === 'fixed' ? 'Fixed Time Ranges' : 'Flexible Duration'}</strong>
          </Alert>

          {/* Code and Name */}
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 2 }}>
            <TextField
              label="Code"
              value={formData.code}
              onChange={(e) => handleChange('code', e.target.value.toUpperCase())}
              error={touched.code && !!errors.code}
              helperText={touched.code && errors.code ? errors.code : 'e.g., M, T, N'}
              required
              inputProps={{ maxLength: 10 }}
            />
            <TextField
              label="Name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              error={touched.name && !!errors.name}
              helperText={touched.name && errors.name ? errors.name : 'e.g., Morning, Afternoon, Night'}
              required
              inputProps={{ maxLength: 50 }}
            />
          </Box>

          {/* Fixed Model: Time Range */}
          {workPeriodModel === 'fixed' && (
            <Box>
              <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                Time Range
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <TimePicker
                    label="Start Time"
                    value={parseTime(formData.timeRange.start)}
                    onChange={(newValue) => handleTimeRangeChange('start', formatTime(newValue))}
                    ampm={false}
                    slotProps={{
                      textField: {
                        error: touched.timeRange && !!errors.timeRange,
                        helperText: touched.timeRange && errors.timeRange ? errors.timeRange : '24-hour format'
                      }
                    }}
                  />
                  <TimePicker
                    label="End Time"
                    value={parseTime(formData.timeRange.end)}
                    onChange={(newValue) => handleTimeRangeChange('end', formatTime(newValue))}
                    ampm={false}
                    slotProps={{
                      textField: {
                        error: touched.timeRange && !!errors.timeRange,
                        helperText: touched.timeRange && errors.timeRange ? errors.timeRange : '24-hour format'
                      }
                    }}
                  />
                </LocalizationProvider>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Overnight shifts are supported (e.g., 22:00-06:00 means 10 PM to 6 AM next day)
              </Typography>
            </Box>
          )}

          {/* Flexible Model: Duration and Allowed Start Times */}
          {workPeriodModel === 'flexible' && (
            <Box>
              {/* Duration */}
              <TextField
                label="Duration (hours)"
                type="number"
                value={formData.duration}
                onChange={(e) => handleChange('duration', e.target.value)}
                error={touched.duration && !!errors.flexible}
                helperText={touched.duration && errors.flexible ? errors.flexible : 'How many hours this shift lasts'}
                required
                inputProps={{ min: 1, max: 24, step: 0.5 }}
                sx={{ maxWidth: '200px', mb: 3 }}
              />

              {/* Allowed Start Times */}
              <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                Allowed Start Times
              </Typography>
              <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                Select all possible times when this work period can start
              </Typography>

              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Button size="small" variant="outlined" onClick={handleSelectAllTimes}>
                  Select All
                </Button>
                <Button size="small" variant="outlined" onClick={handleClearAllTimes}>
                  Clear All
                </Button>
                {formData.allowedStartTimes?.length > 0 && (
                  <Chip
                    label={`${formData.allowedStartTimes.length} selected`}
                    color="primary"
                    size="small"
                  />
                )}
              </Box>

              <Box
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  p: 2,
                  maxHeight: '200px',
                  overflowY: 'auto'
                }}
              >
                <FormGroup row>
                  <Grid container spacing={1}>
                    {timeOptions.map((time) => (
                      <Grid item xs={3} sm={2} key={time}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={formData.allowedStartTimes?.includes(time) || false}
                              onChange={() => handleAllowedTimeToggle(time)}
                              size="small"
                            />
                          }
                          label={time}
                          sx={{ m: 0 }}
                        />
                      </Grid>
                    ))}
                  </Grid>
                </FormGroup>
              </Box>

              {touched.allowedStartTimes && errors.flexible && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {errors.flexible}
                </Alert>
              )}
            </Box>
          )}

          {/* Breaks (Optional) */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography fontWeight={600}>
                  Breaks (Optional)
                </Typography>
                {formData.breaks?.length > 0 && (
                  <Chip label={`${formData.breaks.length} break${formData.breaks.length > 1 ? 's' : ''}`} size="small" />
                )}
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <BreakBuilder
                breaks={formData.breaks}
                onChange={handleBreaksChange}
              />
            </AccordionDetails>
          </Accordion>

          {/* Breaks validation error */}
          {errors.breaks && (
            <Alert severity="error">
              {errors.breaks}
            </Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} color="inherit">
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained">
          {isEditMode ? 'Save Changes' : 'Add Work Period'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default WorkPeriodForm;

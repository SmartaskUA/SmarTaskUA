import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Button,
  IconButton,
  Paper,
  Divider,
  Alert,
  Tooltip
} from '@mui/material';
import { Delete as DeleteIcon, Add as AddIcon, Info as InfoIcon } from '@mui/icons-material';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { parse } from 'date-fns';
import { validateBreak } from '../../utils/validators/workPeriodValidator';
import { formatDuration } from '../../utils/helpers/timeHelpers';

/**
 * BreakBuilder Component - Configure breaks for work periods
 *
 * Allows adding/editing/removing breaks with:
 * - Type (meal/rest/other)
 * - Duration (minutes)
 * - Timing mode (fixed/window/afterWork)
 * - Flags (paid/required/canStagger)
 */
const BreakBuilder = ({ breaks = [], onChange }) => {
  const [errors, setErrors] = useState({});

  // Create a default break
  const createDefaultBreak = () => ({
    type: 'meal',
    duration: 30,
    timingMode: 'window',
    startTime: '12:00',
    windowStart: '12:00',
    windowEnd: '13:00',
    afterWorkHours: 4,
    paid: true,
    required: true,
    canStagger: false
  });

  // Add a new break
  const handleAddBreak = () => {
    const newBreak = createDefaultBreak();
    onChange([...breaks, newBreak]);
  };

  // Remove a break
  const handleRemoveBreak = (index) => {
    const newBreaks = breaks.filter((_, i) => i !== index);
    onChange(newBreaks);

    // Clear error for this index
    const newErrors = { ...errors };
    delete newErrors[index];
    setErrors(newErrors);
  };

  // Update a break field
  const handleBreakChange = (index, field, value) => {
    const newBreaks = [...breaks];
    newBreaks[index] = {
      ...newBreaks[index],
      [field]: value
    };
    onChange(newBreaks);

    // Validate the break
    const validation = validateBreak(newBreaks[index]);
    const newErrors = { ...errors };
    if (!validation.valid) {
      newErrors[index] = validation.error;
    } else {
      delete newErrors[index];
    }
    setErrors(newErrors);
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

  // Render timing mode fields based on selected mode
  const renderTimingFields = (breakItem, index) => {
    switch (breakItem.timingMode) {
      case 'fixed':
        return (
          <FormControl fullWidth sx={{ mt: 2 }}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <TimePicker
                label="Break Start Time"
                value={parseTime(breakItem.startTime)}
                onChange={(newValue) => handleBreakChange(index, 'startTime', formatTime(newValue))}
                ampm={false}
                slotProps={{
                  textField: {
                    size: 'small',
                    helperText: 'Fixed time for break to start'
                  }
                }}
              />
            </LocalizationProvider>
          </FormControl>
        );

      case 'window':
        return (
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mt: 2 }}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <TimePicker
                label="Window Start"
                value={parseTime(breakItem.windowStart)}
                onChange={(newValue) => handleBreakChange(index, 'windowStart', formatTime(newValue))}
                ampm={false}
                slotProps={{
                  textField: {
                    size: 'small',
                    helperText: 'Earliest break start'
                  }
                }}
              />
              <TimePicker
                label="Window End"
                value={parseTime(breakItem.windowEnd)}
                onChange={(newValue) => handleBreakChange(index, 'windowEnd', formatTime(newValue))}
                ampm={false}
                slotProps={{
                  textField: {
                    size: 'small',
                    helperText: 'Latest break start'
                  }
                }}
              />
            </LocalizationProvider>
          </Box>
        );

      case 'afterWork':
        return (
          <TextField
            fullWidth
            size="small"
            type="number"
            label="After Work Hours"
            value={breakItem.afterWorkHours}
            onChange={(e) => handleBreakChange(index, 'afterWorkHours', Number(e.target.value))}
            inputProps={{ min: 0, max: 24, step: 0.5 }}
            helperText="Break occurs after this many hours of work"
            sx={{ mt: 2 }}
          />
        );

      default:
        return null;
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            Breaks
          </Typography>
          <Tooltip title="Configure meal breaks, rest breaks, and other breaks during the work period">
            <InfoIcon fontSize="small" color="action" />
          </Tooltip>
        </Box>
        <Button
          startIcon={<AddIcon />}
          onClick={handleAddBreak}
          size="small"
          variant="outlined"
        >
          Add Break
        </Button>
      </Box>

      {/* Breaks list */}
      {breaks.length === 0 ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          No breaks configured. Breaks are optional but recommended for compliance.
        </Alert>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {breaks.map((breakItem, index) => (
            <Paper
              key={index}
              elevation={1}
              sx={{
                p: 2,
                border: errors[index] ? '1px solid' : 'none',
                borderColor: 'error.main'
              }}
            >
              {/* Break header with delete button */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle2" fontWeight={600}>
                  Break {index + 1}
                  {breakItem.duration && ` (${formatDuration(breakItem.duration)})`}
                </Typography>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => handleRemoveBreak(index)}
                  aria-label="Remove break"
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>

              {/* Break type and duration */}
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 2 }}>
                <FormControl fullWidth size="small">
                  <InputLabel>Break Type</InputLabel>
                  <Select
                    value={breakItem.type}
                    label="Break Type"
                    onChange={(e) => handleBreakChange(index, 'type', e.target.value)}
                  >
                    <MenuItem value="meal">Meal Break</MenuItem>
                    <MenuItem value="rest">Rest Break</MenuItem>
                    <MenuItem value="other">Other</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  size="small"
                  type="number"
                  label="Duration (minutes)"
                  value={breakItem.duration}
                  onChange={(e) => handleBreakChange(index, 'duration', Number(e.target.value))}
                  inputProps={{ min: 1, max: 480 }}
                  helperText="1-480 minutes"
                />
              </Box>

              {/* Timing mode */}
              <FormControl fullWidth size="small">
                <InputLabel>Timing Mode</InputLabel>
                <Select
                  value={breakItem.timingMode}
                  label="Timing Mode"
                  onChange={(e) => handleBreakChange(index, 'timingMode', e.target.value)}
                >
                  <MenuItem value="fixed">Fixed Time</MenuItem>
                  <MenuItem value="window">Time Window</MenuItem>
                  <MenuItem value="afterWork">After Work Hours</MenuItem>
                </Select>
              </FormControl>

              {/* Timing mode fields */}
              {renderTimingFields(breakItem, index)}

              <Divider sx={{ my: 2 }} />

              {/* Flags */}
              <FormGroup row>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={breakItem.paid}
                      onChange={(e) => handleBreakChange(index, 'paid', e.target.checked)}
                      size="small"
                    />
                  }
                  label="Paid"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={breakItem.required}
                      onChange={(e) => handleBreakChange(index, 'required', e.target.checked)}
                      size="small"
                    />
                  }
                  label="Required"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={breakItem.canStagger}
                      onChange={(e) => handleBreakChange(index, 'canStagger', e.target.checked)}
                      size="small"
                    />
                  }
                  label="Can Stagger"
                />
              </FormGroup>

              {/* Error message */}
              {errors[index] && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {errors[index]}
                </Alert>
              )}
            </Paper>
          ))}
        </Box>
      )}

      {/* Help text */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          <strong>Timing Modes:</strong><br />
          • <strong>Fixed Time</strong>: Break at specific time (e.g., 12:00)<br />
          • <strong>Time Window</strong>: Break can start within time range (e.g., 12:00-13:00)<br />
          • <strong>After Work Hours</strong>: Break after working certain hours (e.g., after 4h)
        </Typography>
      </Box>
    </Box>
  );
};

export default BreakBuilder;

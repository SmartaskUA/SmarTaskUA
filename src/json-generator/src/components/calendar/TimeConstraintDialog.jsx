import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Alert
} from '@mui/material';
import { TimePicker } from '@mui/x-date-pickers/TimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { parse } from 'date-fns';
import { validateTimeRange } from '../../utils/validators/timeConstraintValidator';

const TYPE_CONFIG = {
  EQUALS: {
    label: 'EQUALS',
    color: '#ce93d8',
    bg: '#e1bee7',
    description: 'Employee must work exactly this time window — no earlier, no later.'
  },
  INCLUDE: {
    label: 'INCLUDE',
    color: '#ffb74d',
    bg: '#ffe0b2',
    description: 'Employee must cover at least this entire time range (can work longer).'
  },
  EXCEPT: {
    label: 'EXCEPT',
    color: '#f48fb1',
    bg: '#f8bbd0',
    description: 'Employee is unavailable during this window — cannot be scheduled here.'
  }
};

const parseTime = (timeString) => {
  if (!timeString) return null;
  return parse(timeString, 'HH:mm', new Date());
};

const formatTime = (date) => {
  if (!date) return '';
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
};

/**
 * TimeConstraintDialog - Pick EQUALS / INCLUDE / EXCEPT time window constraints
 *
 * Props:
 *   open          - boolean
 *   initialType   - 'EQUALS' | 'INCLUDE' | 'EXCEPT'
 *   initialStart  - 'HH:MM' string or ''
 *   initialEnd    - 'HH:MM' string or ''
 *   onSave        - (constraintString) => void  e.g. "EQUALS:08:00-16:00"
 *   onClose       - () => void
 */
const TimeConstraintDialog = ({
  open,
  initialType = 'EQUALS',
  initialStart = '',
  initialEnd = '',
  onSave,
  onClose
}) => {
  const [type, setType] = useState(initialType);
  const [start, setStart] = useState(initialStart);
  const [end, setEnd] = useState(initialEnd);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      setType(initialType || 'EQUALS');
      setStart(initialStart || '');
      setEnd(initialEnd || '');
      setError('');
    }
  }, [open, initialType, initialStart, initialEnd]);

  const handleApply = () => {
    if (!start) {
      setError('Start time is required.');
      return;
    }
    if (!end) {
      setError('End time is required.');
      return;
    }
    const validation = validateTimeRange(start, end);
    if (!validation.valid) {
      setError(validation.error);
      return;
    }
    onSave(`${type}:${start}-${end}`);
    onClose();
  };

  const cfg = TYPE_CONFIG[type] || TYPE_CONFIG.EQUALS;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>Time Window Constraint</DialogTitle>

      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, pt: 1 }}>
          {/* Type selector */}
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Constraint type
            </Typography>
            <ToggleButtonGroup
              value={type}
              exclusive
              onChange={(_, val) => { if (val) { setType(val); setError(''); } }}
              fullWidth
              size="small"
            >
              {Object.entries(TYPE_CONFIG).map(([key, c]) => (
                <ToggleButton
                  key={key}
                  value={key}
                  sx={{
                    fontWeight: 700,
                    fontSize: '12px',
                    '&.Mui-selected': {
                      backgroundColor: c.bg,
                      color: 'text.primary',
                      borderColor: c.color,
                      '&:hover': { backgroundColor: c.bg }
                    }
                  }}
                >
                  {c.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              {cfg.description}
            </Typography>
          </Box>

          {/* Time pickers */}
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TimePicker
                label="Start time"
                value={parseTime(start)}
                onChange={(val) => { setStart(formatTime(val)); setError(''); }}
                ampm={false}
                slotProps={{
                  textField: {
                    size: 'small',
                    fullWidth: true,
                    helperText: '24-hour format'
                  }
                }}
              />
              <TimePicker
                label="End time"
                value={parseTime(end)}
                onChange={(val) => { setEnd(formatTime(val)); setError(''); }}
                ampm={false}
                slotProps={{
                  textField: {
                    size: 'small',
                    fullWidth: true,
                    helperText: 'Must be after start'
                  }
                }}
              />
            </Box>
          </LocalizationProvider>

          {/* Preview */}
          {start && end && !error && (
            <Box
              sx={{
                p: 1.5,
                borderRadius: 1,
                backgroundColor: cfg.bg,
                border: `1px solid ${cfg.color}`,
                fontFamily: 'monospace',
                fontSize: 13,
                fontWeight: 700,
                textAlign: 'center'
              }}
            >
              {`${type}:${start}-${end}`}
            </Box>
          )}

          {error && <Alert severity="error" sx={{ py: 0 }}>{error}</Alert>}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} color="inherit">Cancel</Button>
        <Button onClick={handleApply} variant="contained">Apply</Button>
      </DialogActions>
    </Dialog>
  );
};

export default TimeConstraintDialog;

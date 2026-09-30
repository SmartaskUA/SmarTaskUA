import React from 'react';
import {
  TextField, Dialog, DialogTitle, DialogContent, DialogActions, Button, DialogContentText
} from '@mui/material';
import { onGrid, tryHhmmToMin } from '../../v4/core';

/**
 * A clock time HH:MM, stepping on the problem's slot grid. Off-grid or
 * malformed values are shown as errors rather than refused, so a user can
 * type through an intermediate value.
 */
export function TimeField({ value, onChange, slotMinutes = 30, helperText, error, ...rest }) {
  const minutes = tryHhmmToMin(value);
  const offGrid = value && minutes !== null && !onGrid(minutes, slotMinutes);
  const malformed = value && minutes === null;
  let message = helperText;
  if (malformed) message = 'Use HH:MM';
  else if (offGrid) message = `Not on the ${slotMinutes}-minute grid`;
  return (
    <TextField
      type="time"
      size="small"
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      error={!!error || !!offGrid || !!malformed}
      helperText={message}
      InputLabelProps={{ shrink: true }}
      inputProps={{ step: Math.min(slotMinutes, 60) * 60 }}
      {...rest}
    />
  );
}

/** A calendar date YYYY-MM-DD, optionally bounded. */
export function DateField({ value, onChange, min, max, ...rest }) {
  return (
    <TextField
      type="date"
      size="small"
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      InputLabelProps={{ shrink: true }}
      inputProps={{ min, max }}
      {...rest}
    />
  );
}

/** A number field that reports '' while empty and a number otherwise. */
export function NumberField({ value, onChange, min, max, step, ...rest }) {
  return (
    <TextField
      type="number"
      size="small"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
      inputProps={{ min, max, step }}
      {...rest}
    />
  );
}

export function ConfirmDialog({
  open, title, children, confirmLabel = 'Confirm', confirmColor = 'primary', onConfirm, onCancel
}) {
  return (
    <Dialog open={open} onClose={onCancel} maxWidth="sm" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        {typeof children === 'string' ? <DialogContentText>{children}</DialogContentText> : children}
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} color="inherit">Cancel</Button>
        <Button onClick={onConfirm} variant="contained" color={confirmColor}>{confirmLabel}</Button>
      </DialogActions>
    </Dialog>
  );
}

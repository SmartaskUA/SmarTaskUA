import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, Typography, ToggleButton,
  ToggleButtonGroup, Alert, IconButton, Chip
} from '@mui/material';
import { Add, Delete } from '@mui/icons-material';
import { TimeField } from '../shared/fields';
import { OPERATORS, OPERATOR_HELP } from '../../v4/constants';
import { classifyCell, coalesce, interval, intervalToString, onGrid, tryParseRange, DomainError } from '../../v4/core';

export const OPERATOR_COLORS = {
  EQUALS: '#e1bee7',
  INCLUDE: '#ffe0b2',
  WITHIN: '#b2dfdb',
  EXCEPT: '#f8bbd0'
};

/** {type, ranges: [{start, end}]} from an operator cell, or null. */
export function parseOperatorCell(value) {
  const text = String(value || '').trim();
  const colon = text.indexOf(':');
  if (colon < 0) return null;
  const type = text.slice(0, colon).toUpperCase();
  if (!OPERATORS.includes(type)) return null;
  const ranges = text.slice(colon + 1).split(',').map((part) => {
    const cut = part.indexOf('-');
    return cut < 0 ? { start: part.trim(), end: '' } : { start: part.slice(0, cut).trim(), end: part.slice(cut + 1).trim() };
  });
  return { type, ranges };
}

/**
 * Build an EQUALS / INCLUDE / WITHIN / EXCEPT cell. Several ranges make one
 * split shift (EQUALS), one block covering all (INCLUDE), one block inside one
 * of them (WITHIN), or unavailability during all (EXCEPT). A range whose end is
 * not after its start crosses midnight.
 */
const TimeConstraintDialog = ({ open, value, slotMinutes = 30, onSave, onClose }) => {
  const [type, setType] = useState('EQUALS');
  const [ranges, setRanges] = useState([{ start: '', end: '' }]);

  useEffect(() => {
    if (!open) return;
    const parsed = parseOperatorCell(value);
    setType(parsed?.type || 'EQUALS');
    setRanges(parsed?.ranges?.length ? parsed.ranges : [{ start: '09:00', end: '17:00' }]);
  }, [open, value]);

  const cell = `${type}:${ranges.map((r) => `${r.start}-${r.end}`).join(',')}`;
  let problem = '';
  let merged = [];
  try {
    merged = classifyCell(cell, {}).windows;
    const off = merged.find((w) => !onGrid(w.start, slotMinutes) || !onGrid(w.end, slotMinutes));
    if (off) problem = `${intervalToString(off)} does not land on the ${slotMinutes}-minute grid`;
  } catch (exc) {
    problem = exc instanceof DomainError ? 'Every range needs a start and an end (HH:MM)' : exc.message;
  }
  const coalesced = merged.length && merged.length < ranges.length;

  const setRange = (i, patch) => setRanges((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Time window</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <ToggleButtonGroup value={type} exclusive fullWidth size="small" onChange={(_, v) => v && setType(v)}>
            {OPERATORS.map((op) => (
              <ToggleButton key={op} value={op} sx={{ fontWeight: 700, '&.Mui-selected': { bgcolor: OPERATOR_COLORS[op] } }}>{op}</ToggleButton>
            ))}
          </ToggleButtonGroup>
          <Typography variant="body2" color="text.secondary">{OPERATOR_HELP[type]}</Typography>

          {ranges.map((r, i) => {
            const w = tryParseRange(r.start, r.end);
            return (
              <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <TimeField label="From" value={r.start} slotMinutes={slotMinutes} onChange={(v) => setRange(i, { start: v })} />
                <TimeField label="To" value={r.end} slotMinutes={slotMinutes} onChange={(v) => setRange(i, { end: v })} />
                {w && w[1] > 1440 && <Chip size="small" label="crosses midnight" />}
                {ranges.length > 1 && (
                  <IconButton size="small" onClick={() => setRanges((rs) => rs.filter((_, j) => j !== i))}><Delete fontSize="small" /></IconButton>
                )}
              </Box>
            );
          })}
          <Box>
            <Button size="small" startIcon={<Add />} onClick={() => setRanges((rs) => [...rs, { start: '', end: '' }])}>Add range</Button>
          </Box>

          {coalesced ? (
            <Alert severity="info">Overlapping or touching ranges merge into {coalesce(merged.map((w) => interval(w.start, w.end))).map(intervalToString).join(', ')}.</Alert>
          ) : null}
          {problem ? <Alert severity="error">{problem}</Alert> : (
            <Box sx={{ p: 1.5, borderRadius: 1, bgcolor: OPERATOR_COLORS[type], fontFamily: 'monospace', fontWeight: 700, textAlign: 'center' }}>
              {cell}
            </Box>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">Cancel</Button>
        <Button variant="contained" disabled={!!problem} onClick={() => { onSave(cell); onClose(); }}>Apply</Button>
      </DialogActions>
    </Dialog>
  );
};

export default TimeConstraintDialog;

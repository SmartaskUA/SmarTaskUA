import React, { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem, Grid, Alert } from '@mui/material';
import { NumberField, TimeField } from '../shared/fields';
import { ORDERING_NOTE } from './DemandRowDialog';
import { pairKey, tryParseRange } from '../../v4/core';
import { newId, pairLabel } from '../../v4/state';
import { overlappingRows } from '../../v4/operations';

const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/**
 * Add or edit a weekly-template block: a dimension, a free window on the slot
 * grid (it may cross midnight), and the demand triple. "Save & add next"
 * starts the following window where this one ends, which makes tiling a day fast.
 */
const DemandBlockDialog = ({ open, block, day, dimensions, slotMinutes, siblings, onSave, onDelete, onClose }) => {
  const [form, setForm] = useState(block);
  const [error, setError] = useState('');
  useEffect(() => {
    if (open) {
      setForm(block);
      setError('');
    }
  }, [open, block]);

  const overlap = useMemo(() => {
    if (!form) return false;
    const probe = { ...form, date: day };
    const others = siblings.filter((b) => b.id !== form.id).map((b) => ({ ...b, date: day }));
    return overlappingRows([probe, ...others]).some((p) => p.a === probe || p.b === probe);
  }, [form, siblings, day]);

  if (!form) return null;
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const w = tryParseRange(form.start, form.end);

  const save = (addNext) => {
    if (!form.tableName) return setError('Pick a dimension');
    if (!w) return setError('A start and an end (HH:MM) are required');
    if (form.minimum === '' || Number(form.minimum) < 0 || Number(form.ideal) < 0 || Number(form.estimated) < 0) {
      return setError('Values must be non-negative, and minimum is required');
    }
    const saved = {
      ...form,
      id: form.id || newId('block'),
      minimum: Number(form.minimum),
      ideal: form.ideal === '' ? 0 : Number(form.ideal),
      estimated: form.estimated === '' ? 0 : Number(form.estimated)
    };
    onSave(saved, addNext ? { ...saved, id: '', start: saved.end, end: '' } : null);
    return null;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{form.id ? 'Edit' : 'Add'} {capital(day)} block</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ pt: 1 }}>
          <Grid size={12}>
            <TextField
              select fullWidth size="small" label="Dimension"
              value={form.tableName ? pairKey(form.tableName, form.tableValue) : ''}
              onChange={(e) => {
                const d = dimensions.find((x) => pairKey(x.tableName, x.tableValue) === e.target.value);
                set({ tableName: d.tableName, tableValue: d.tableValue });
              }}
            >
              {dimensions.map((d) => (
                <MenuItem key={pairKey(d.tableName, d.tableValue)} value={pairKey(d.tableName, d.tableValue)}>
                  {pairLabel(d.tableName, d.tableValue)}{d.name ? ` — ${d.name}` : ''}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid size={6}><TimeField fullWidth label="Start" value={form.start} slotMinutes={slotMinutes} onChange={(v) => set({ start: v })} /></Grid>
          <Grid size={6}>
            <TimeField fullWidth label="End" value={form.end} slotMinutes={slotMinutes} onChange={(v) => set({ end: v })}
              helperText={w && w[1] > 1440 ? 'Crosses midnight into the next day' : undefined}
            />
          </Grid>
          <Grid size={4}><NumberField fullWidth label="minimum (workers)" value={form.minimum} min={0} step={0.5} onChange={(v) => set({ minimum: v })} helperText="may be fractional" /></Grid>
          <Grid size={4}><NumberField fullWidth label="ideal" value={form.ideal} min={0} step={0.5} onChange={(v) => set({ ideal: v })} helperText="0 = unset" /></Grid>
          <Grid size={4}><NumberField fullWidth label="estimated" value={form.estimated} min={0} step={0.5} onChange={(v) => set({ estimated: v })} helperText="0 = unset" /></Grid>
        </Grid>
        <Alert severity="info" sx={{ mt: 2 }}>{ORDERING_NOTE}</Alert>
        {overlap && (
          <Alert severity="warning" sx={{ mt: 1 }}>
            Overlaps another {pairLabel(form.tableName, form.tableValue)} window on {capital(day)}: a worker in the overlap would count toward both.
          </Alert>
        )}
        {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
      </DialogContent>
      <DialogActions>
        {form.id && <Button color="error" onClick={() => onDelete(form)} sx={{ mr: 'auto' }}>Delete</Button>}
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={() => save(true)}>Save &amp; add next window</Button>
        <Button variant="contained" onClick={() => save(false)}>Save</Button>
      </DialogActions>
    </Dialog>
  );
};

export default DemandBlockDialog;

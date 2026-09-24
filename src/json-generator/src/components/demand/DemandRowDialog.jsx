import React, { useEffect, useMemo, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem, Alert, Grid, Autocomplete, Typography
} from '@mui/material';
import { DateField, NumberField, TimeField } from '../shared/fields';
import { pairKey, tryParseRange, onGrid } from '../../v4/core';
import { pairLabel } from '../../v4/state';
import { SHIFT_TYPE_SUGGESTIONS } from '../../v4/constants';
import { overlappingRows } from '../../v4/operations';

export const GRAIN_INFO = {
  periods: { title: 'Periods', unit: 'workers', windowed: true, help: 'Headcount wanted in a window.' },
  shifts: { title: 'Shifts', unit: 'workers', windowed: true, help: 'Headcount wanted per shift type.' },
  days: { title: 'Days', unit: 'minutes of work', windowed: false, help: 'Whole-day WORKLOAD in minutes — not headcount.' }
};

export const ORDERING_NOTE = 'minimum, ideal and estimated have no established ordering (agenda item 1): only '
  + 'non-negative is checked, and 0 means unset. Leave ideal and estimated at 0 unless you know what the solver reads.';

/**
 * Add or edit one demand row of any grain. `siblings` are the other rows of
 * the grain, used to warn about a window overlapping the same dimension.
 */
const DemandRowDialog = ({
  open, grain, row, dimensions, slotMinutes, dateMin, dateMax, fixedDate, siblings = [], onSave, onClose
}) => {
  const info = GRAIN_INFO[grain];
  const [form, setForm] = useState(row);
  const [error, setError] = useState('');
  useEffect(() => {
    if (open) {
      setForm(row);
      setError('');
    }
  }, [open, row]);

  const overlap = useMemo(() => {
    if (!form || !info.windowed) return false;
    return overlappingRows([form, ...siblings.filter((r) => r.id !== form.id)]).some((p) => p.a === form || p.b === form);
  }, [form, siblings, info.windowed]);

  if (!form) return null;
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const dimKey = form.tableName ? pairKey(form.tableName, form.tableValue) : '';

  const save = () => {
    if (!form.date) return setError('A date is required');
    if (!form.tableName) return setError('Pick a dimension');
    if (['minimum', 'ideal', 'estimated'].some((k) => form[k] !== '' && Number(form[k]) < 0)) return setError('Values must be non-negative');
    if (form.minimum === '' || form.minimum === undefined) return setError('minimum is required');
    if (info.windowed) {
      if (!tryParseRange(form.start, form.end)) return setError(`A start and end (HH:MM) are mandatory on the ${grain} grain`);
    }
    if (grain === 'shifts' && !form.workPeriod) return setError('The shift type (workPeriod) is required');
    onSave({
      ...form,
      minimum: Number(form.minimum),
      ideal: form.ideal === '' ? 0 : Number(form.ideal),
      estimated: form.estimated === '' ? 0 : Number(form.estimated)
    });
    return null;
  };

  const window = tryParseRange(form.start, form.end);
  const daysOffGrid = grain === 'days' && form.minimum !== '' && !onGrid(Math.trunc(Number(form.minimum)), slotMinutes);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{row.id ? 'Edit' : 'Add'} {info.title.toLowerCase()} row</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{info.help}</Typography>
        <Grid container spacing={2}>
          <Grid size={6}>
            <DateField fullWidth label="Date" value={form.date} min={dateMin} max={dateMax} disabled={!!fixedDate} onChange={(v) => set({ date: v })} />
          </Grid>
          {grain === 'shifts' && (
            <Grid size={6}>
              <Autocomplete
                freeSolo
                options={SHIFT_TYPE_SUGGESTIONS}
                value={form.workPeriod || ''}
                inputValue={form.workPeriod || ''}
                onInputChange={(_, v) => set({ workPeriod: v })}
                renderInput={(params) => <TextField {...params} size="small" label="workPeriod (shift type)" helperText="SISQUAL's ShiftTypeCode M/T/N — unconfirmed" />}
              />
            </Grid>
          )}
          <Grid size={grain === 'shifts' ? 12 : 6}>
            <TextField
              select size="small" fullWidth label="Dimension" value={dimKey}
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
          {info.windowed && (
            <>
              <Grid size={6}><TimeField fullWidth label="Start" value={form.start} slotMinutes={slotMinutes} onChange={(v) => set({ start: v })} /></Grid>
              <Grid size={6}>
                <TimeField
                  fullWidth label="End" value={form.end} slotMinutes={slotMinutes} onChange={(v) => set({ end: v })}
                  helperText={window && window[1] > 1440 ? 'Crosses midnight' : undefined}
                />
              </Grid>
            </>
          )}
          <Grid size={4}>
            <NumberField fullWidth label={`minimum (${info.unit})`} value={form.minimum} min={0} step={grain === 'days' ? slotMinutes : 0.5}
              onChange={(v) => set({ minimum: v })} error={daysOffGrid}
              helperText={daysOffGrid ? `Not a multiple of ${slotMinutes}` : grain === 'days' ? 'minutes' : 'may be fractional'}
            />
          </Grid>
          <Grid size={4}><NumberField fullWidth label="ideal" value={form.ideal} min={0} step={0.5} onChange={(v) => set({ ideal: v })} helperText="0 = unset" /></Grid>
          <Grid size={4}><NumberField fullWidth label="estimated" value={form.estimated} min={0} step={0.5} onChange={(v) => set({ estimated: v })} helperText="0 = unset" /></Grid>
        </Grid>
        <Alert severity="info" sx={{ mt: 2 }}>{ORDERING_NOTE}</Alert>
        {overlap && (
          <Alert severity="warning" sx={{ mt: 1 }}>
            This window overlaps another {pairLabel(form.tableName, form.tableValue)} row on {form.date}: a worker in the overlap counts toward both.
          </Alert>
        )}
        {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={save}>Save</Button>
      </DialogActions>
    </Dialog>
  );
};

export default DemandRowDialog;

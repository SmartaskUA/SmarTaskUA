import React, { useEffect, useMemo, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Grid, FormGroup, FormControlLabel, Checkbox,
  Typography, Alert, Autocomplete, TextField
} from '@mui/material';
import { DateField, NumberField, TimeField } from '../shared/fields';
import { GRAIN_INFO, ORDERING_NOTE } from './DemandRowDialog';
import { dateRange, pairKey, tryParseRange, weekdayName } from '../../v4/core';
import { newId, pairLabel } from '../../v4/state';
import { SHIFT_TYPE_SUGGESTIONS, WEEKDAYS } from '../../v4/constants';

/**
 * One row per (date, dimension) across a date range and a set of weekdays —
 * the quick way to fill the days and shifts grains.
 */
const BulkAddRowsDialog = ({ open, grain, dimensions, slotMinutes, dateMin, dateMax, onAdd, onClose }) => {
  const info = GRAIN_INFO[grain];
  const [form, setForm] = useState(null);

  useEffect(() => {
    if (open) {
      setForm({
        from: dateMin || '', to: dateMax || '', weekdays: [...WEEKDAYS], dims: [],
        workPeriod: 'M', start: '09:00', end: '17:00',
        minimum: grain === 'days' ? 480 : 1, ideal: 0, estimated: 0
      });
    }
  }, [open, grain, dateMin, dateMax]);

  const dates = useMemo(() => (form ? dateRange(form.from, form.to).filter((d) => form.weekdays.includes(weekdayName(d))) : []), [form]);
  if (!form) return null;
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const count = dates.length * form.dims.length;
  const windowOk = !info.windowed || tryParseRange(form.start, form.end);

  const add = () => {
    const rows = [];
    for (const date of dates) {
      for (const key of form.dims) {
        const d = dimensions.find((x) => pairKey(x.tableName, x.tableValue) === key);
        rows.push({
          id: newId(grain), date, tableName: d.tableName, tableValue: d.tableValue,
          minimum: Number(form.minimum) || 0, ideal: Number(form.ideal) || 0, estimated: Number(form.estimated) || 0,
          ...(info.windowed && { start: form.start, end: form.end }),
          ...(grain === 'shifts' && { workPeriod: form.workPeriod })
        });
      }
    }
    onAdd(rows);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add {info.title.toLowerCase()} rows in bulk</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ pt: 1 }}>
          <Grid size={6}><DateField fullWidth label="From" value={form.from} min={dateMin} max={dateMax} onChange={(v) => set({ from: v })} /></Grid>
          <Grid size={6}><DateField fullWidth label="To" value={form.to} min={form.from || dateMin} max={dateMax} onChange={(v) => set({ to: v })} /></Grid>
          <Grid size={12}>
            <FormGroup row>
              {WEEKDAYS.map((d) => (
                <FormControlLabel
                  key={d}
                  label={d.slice(0, 3)}
                  control={<Checkbox size="small" checked={form.weekdays.includes(d)}
                    onChange={(e) => set({ weekdays: e.target.checked ? [...form.weekdays, d] : form.weekdays.filter((x) => x !== d) })}
                  />}
                />
              ))}
            </FormGroup>
          </Grid>
          <Grid size={12}>
            <Typography variant="subtitle2">Dimensions</Typography>
            <FormGroup row>
              {dimensions.map((d) => {
                const key = pairKey(d.tableName, d.tableValue);
                return (
                  <FormControlLabel
                    key={key}
                    label={pairLabel(d.tableName, d.tableValue)}
                    control={<Checkbox size="small" checked={form.dims.includes(key)}
                      onChange={(e) => set({ dims: e.target.checked ? [...form.dims, key] : form.dims.filter((x) => x !== key) })}
                    />}
                  />
                );
              })}
            </FormGroup>
          </Grid>
          {grain === 'shifts' && (
            <Grid size={12}>
              <Autocomplete freeSolo options={SHIFT_TYPE_SUGGESTIONS} value={form.workPeriod} inputValue={form.workPeriod}
                onInputChange={(_, v) => set({ workPeriod: v })}
                renderInput={(params) => <TextField {...params} size="small" label="workPeriod (shift type)" />}
              />
            </Grid>
          )}
          {info.windowed && (
            <>
              <Grid size={6}><TimeField fullWidth label="Start" value={form.start} slotMinutes={slotMinutes} onChange={(v) => set({ start: v })} /></Grid>
              <Grid size={6}><TimeField fullWidth label="End" value={form.end} slotMinutes={slotMinutes} onChange={(v) => set({ end: v })} /></Grid>
            </>
          )}
          <Grid size={4}><NumberField fullWidth label={`minimum (${info.unit})`} value={form.minimum} min={0} onChange={(v) => set({ minimum: v })} /></Grid>
          <Grid size={4}><NumberField fullWidth label="ideal" value={form.ideal} min={0} onChange={(v) => set({ ideal: v })} helperText="0 = unset" /></Grid>
          <Grid size={4}><NumberField fullWidth label="estimated" value={form.estimated} min={0} onChange={(v) => set({ estimated: v })} helperText="0 = unset" /></Grid>
        </Grid>
        <Alert severity="info" sx={{ mt: 2 }}>{ORDERING_NOTE}</Alert>
      </DialogContent>
      <DialogActions>
        <Typography variant="body2" color="text.secondary" sx={{ mr: 'auto', ml: 2 }}>{count} row(s)</Typography>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={add} disabled={!count || !windowOk}>Add</Button>
      </DialogActions>
    </Dialog>
  );
};

export default BulkAddRowsDialog;

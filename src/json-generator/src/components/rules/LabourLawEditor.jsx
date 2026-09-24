import React from 'react';
import {
  Box, Typography, Paper, Grid, TextField, Switch, FormControlLabel, IconButton, Button, Chip, Autocomplete, Tooltip
} from '@mui/material';
import { Add, Delete } from '@mui/icons-material';
import { DateField, NumberField } from '../shared/fields';
import { DEFAULT_CONSTRAINT_TYPE, LEGISLATION_KEYS } from '../../v4/constants';
import { tryNumber } from '../../v4/core';

const KNOWN = new Set(LEGISLATION_KEYS.map((k) => k.key));
const dateOf = (dt) => (dt ? String(dt).slice(0, 10) : '');
const naive = (date) => (date ? `${date}T00:00:00` : '');

/**
 * constraints.hard: rules above the contract — SISQUAL's labour law. The
 * parameters are an open vendor bag; the validator enforces the two
 * MaxConsecutive* keys and carries the rest.
 */
const LabourLawEditor = ({ entries, scopeStart, onChange }) => {
  const set = (i, patch) => onChange(entries.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  const setParam = (i, key, value) => {
    const parameters = { ...entries[i].parameters };
    if (value === '' || value === undefined) delete parameters[key];
    else parameters[key] = value;
    set(i, { parameters });
  };
  const renameParam = (i, from, to) => {
    const parameters = Object.fromEntries(Object.entries(entries[i].parameters).map(([k, v]) => (k === from ? [to, v] : [k, v])));
    set(i, { parameters });
  };

  const add = () => onChange([...entries, {
    id: `LEGISLATION-${entries.length + 1}`,
    type: DEFAULT_CONSTRAINT_TYPE,
    parameters: { MaxConsecutiveWorkDays: 5, MaxConsecutiveWorkDaysInWeek: 5, MinDistanceBetweenShiftsInMinutes: 660 },
    startDate: naive(scopeStart),
    enabled: true
  }]);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
        <Box>
          <Typography variant="h6" fontWeight={600}>Labour law</Typography>
          <Typography variant="body2" color="text.secondary">
            Optional, roster-wide. The validator enforces MaxConsecutiveWorkDays and MaxConsecutiveWorkDaysInWeek
            against the schedule-input matrix; other parameters are carried unread.
            <code> constraints.soft</code> is always written empty — its shape is unknown.
          </Typography>
        </Box>
        <Button size="small" startIcon={<Add />} onClick={add} sx={{ flexShrink: 0 }}>Add rule set</Button>
      </Box>

      {entries.map((e, i) => {
        const extra = Object.entries(e.parameters || {}).filter(([k]) => !KNOWN.has(k));
        return (
          <Paper key={i} variant="outlined" sx={{ p: 2, mb: 2, opacity: e.enabled === false ? 0.6 : 1 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid size={{ xs: 12, md: 3 }}>
                <TextField fullWidth size="small" label="id" value={e.id} onChange={(ev) => set(i, { id: ev.target.value })} error={!e.id} />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <Autocomplete freeSolo options={[DEFAULT_CONSTRAINT_TYPE]} value={e.type || ''} inputValue={e.type || ''}
                  onInputChange={(_, v) => set(i, { type: v })}
                  renderInput={(params) => <TextField {...params} size="small" label="type" error={!e.type} />}
                />
              </Grid>
              <Grid size={{ xs: 6, md: 2 }}>
                <DateField fullWidth label="startDate" value={dateOf(e.startDate)} onChange={(v) => set(i, { startDate: naive(v) })} />
              </Grid>
              <Grid size={{ xs: 6, md: 2 }}>
                <DateField fullWidth label="endDate" value={dateOf(e.endDate)} onChange={(v) => set(i, { endDate: naive(v) || undefined })} />
              </Grid>
              <Grid size={{ xs: 12, md: 2 }} sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                <FormControlLabel
                  control={<Switch checked={e.enabled !== false} onChange={(ev) => set(i, { enabled: ev.target.checked })} />}
                  label="enabled"
                />
                <IconButton color="error" onClick={() => onChange(entries.filter((_, j) => j !== i))}><Delete /></IconButton>
              </Grid>

              {LEGISLATION_KEYS.map(({ key, label, enforced }) => (
                <Grid key={key} size={{ xs: 12, md: 4 }}>
                  <NumberField
                    fullWidth label={label} value={e.parameters?.[key] ?? ''} min={0} step={1}
                    onChange={(v) => setParam(i, key, v)}
                    helperText={<>{key} {enforced ? <Chip component="span" size="small" label="checked" sx={{ height: 16, fontSize: 10 }} /> : '(carried)'}</>}
                  />
                </Grid>
              ))}

              <Grid size={12}>
                <Typography variant="caption" color="text.secondary">Other parameters (the vendor bag)</Typography>
                {extra.map(([k, v]) => (
                  <Box key={k} sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <TextField size="small" label="key" value={k} onChange={(ev) => renameParam(i, k, ev.target.value)} />
                    <TextField size="small" label="value" value={v}
                      onChange={(ev) => {
                        const n = tryNumber(ev.target.value);
                        setParam(i, k, n !== null && String(n) === ev.target.value.trim() ? n : ev.target.value);
                      }}
                    />
                    <Tooltip title="Remove"><IconButton size="small" onClick={() => setParam(i, k, '')}><Delete fontSize="small" /></IconButton></Tooltip>
                  </Box>
                ))}
                <Button size="small" sx={{ mt: 1 }} onClick={() => setParam(i, `Parameter${extra.length + 1}`, 0)}>Add parameter</Button>
              </Grid>
            </Grid>
          </Paper>
        );
      })}
    </Box>
  );
};

export default LabourLawEditor;

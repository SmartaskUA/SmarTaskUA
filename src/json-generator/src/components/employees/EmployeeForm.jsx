import React, { useEffect, useMemo, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Alert, MenuItem, Box, Typography,
  Table, TableHead, TableRow, TableCell, TableBody, IconButton, Tooltip, Divider, Grid
} from '@mui/material';
import { Add, Delete } from '@mui/icons-material';
import { DateField, NumberField } from '../shared/fields';
import { pairKey } from '../../v4/core';
import { pairLabel } from '../../v4/state';

const OPEN = '9999-12-31';

/** Pairs of indices whose closed date ranges overlap. */
function overlaps(rows) {
  const out = [];
  rows.forEach((a, i) => rows.slice(i + 1).forEach((b, k) => {
    if (!a.start || !b.start) return;
    if (a.start <= (b.end || OPEN) && b.start <= (a.end || OPEN)) out.push([i, i + 1 + k]);
  }));
  return out;
}

export function newEmployee(state) {
  return {
    id: '',
    name: '',
    contractAssignments: [{ contractType: state.contracts.definitions[0]?.id || '', start: state.temporalScope.start || '', end: null }],
    competencyAssignments: []
  };
}

/**
 * Add or edit one employee: identity, date-ranged contract membership, and
 * date-ranged, levelled competencies. Level 1 is the highest.
 */
const EmployeeForm = ({ open, onClose, onSave, employee, existingIds, state }) => {
  const [form, setForm] = useState(employee);
  const [errors, setErrors] = useState({});
  const [pick, setPick] = useState({ pair: '', level: 1 });

  useEffect(() => {
    if (open) {
      setForm(JSON.parse(JSON.stringify(employee)));
      setErrors({});
      setPick({ pair: '', level: 1 });
    }
  }, [open, employee]);

  const contracts = state.contracts.definitions;
  const dims = state.demand.dimensions;
  const scope = state.temporalScope;

  const contractOverlaps = useMemo(() => overlaps(form?.contractAssignments || []), [form]);
  const competencyClashes = useMemo(() => {
    const byPair = new Map();
    (form?.competencyAssignments || []).forEach((a, i) => {
      const k = pairKey(a.tableName, a.tableValue);
      if (!byPair.has(k)) byPair.set(k, []);
      byPair.get(k).push({ ...a, i });
    });
    return [...byPair.values()].flatMap((rows) => overlaps(rows).map(([x, y]) => [rows[x], rows[y]]));
  }, [form]);

  if (!form) return null;

  const setContract = (i, patch) => setForm((f) => ({
    ...f, contractAssignments: f.contractAssignments.map((a, j) => (j === i ? { ...a, ...patch } : a))
  }));
  const setCompetency = (i, patch) => setForm((f) => ({
    ...f, competencyAssignments: f.competencyAssignments.map((a, j) => (j === i ? { ...a, ...patch } : a))
  }));

  const addCompetency = () => {
    const d = dims.find((x) => pairKey(x.tableName, x.tableValue) === pick.pair);
    if (!d) return;
    setForm((f) => ({
      ...f,
      competencyAssignments: [...f.competencyAssignments, {
        tableName: d.tableName, tableValue: d.tableValue, level: Number(pick.level) || 1, start: scope.start || '', end: null
      }]
    }));
    setPick({ pair: '', level: pick.level });
  };

  const addAllCompetencies = () => {
    const held = new Set(form.competencyAssignments.map((a) => pairKey(a.tableName, a.tableValue)));
    setForm((f) => ({
      ...f,
      competencyAssignments: [...f.competencyAssignments, ...dims
        .filter((d) => !held.has(pairKey(d.tableName, d.tableValue)))
        .map((d) => ({ tableName: d.tableName, tableValue: d.tableValue, level: Number(pick.level) || 1, start: scope.start || '', end: null }))]
    }));
  };

  const save = () => {
    const id = form.id.trim();
    const e = {};
    if (!id) e.id = 'Required';
    else if (existingIds.includes(id)) e.id = 'Another employee has this ID';
    if (!form.contractAssignments.length) e.contracts = 'Assign at least one contract';
    else if (form.contractAssignments.some((a) => !a.contractType || !a.start)) e.contracts = 'Every contract period needs a contract and a start date';
    else if (contractOverlaps.length) e.contracts = 'Contract periods overlap';
    if (form.competencyAssignments.some((a) => !a.start || !(Number(a.level) >= 1))) e.competencies = 'Every competency needs a level ≥ 1 and a start date';
    setErrors(e);
    if (Object.keys(e).length) return;
    const clean = (a) => ({ ...a, end: a.end || null });
    onSave({
      id,
      name: form.name.trim(),
      contractAssignments: form.contractAssignments.map(clean),
      competencyAssignments: form.competencyAssignments.map((a) => ({ ...clean(a), level: Number(a.level) }))
    });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{employee.id ? `Edit ${employee.id}` : 'Add employee'}</DialogTitle>
      <DialogContent dividers>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              fullWidth label="Employee ID" value={form.id} required autoFocus
              onChange={(e) => setForm({ ...form, id: e.target.value })}
              error={!!errors.id} helperText={errors.id || 'A string, even when it looks numeric'}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField fullWidth label="Name (optional)" value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Grid>
        </Grid>

        <Divider sx={{ my: 2 }} />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="subtitle1" fontWeight={600}>Contract periods</Typography>
          <Button size="small" startIcon={<Add />} onClick={() => setForm((f) => ({
            ...f, contractAssignments: [...f.contractAssignments, { contractType: contracts[0]?.id || '', start: '', end: null }]
          }))}
          >
            Add period
          </Button>
        </Box>
        <Typography variant="caption" color="text.secondary">
          Leave the end empty for an open-ended contract. Asking for work on a day no period covers is an error.
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow><TableCell>Contract</TableCell><TableCell>From</TableCell><TableCell>To (empty = open)</TableCell><TableCell /></TableRow>
          </TableHead>
          <TableBody>
            {form.contractAssignments.map((a, i) => (
              <TableRow key={i}>
                <TableCell>
                  <TextField select size="small" value={a.contractType} onChange={(e) => setContract(i, { contractType: e.target.value })} sx={{ minWidth: 160 }}>
                    {contracts.map((c) => <MenuItem key={c.id} value={c.id}>{c.id} · {c.workMinutesPerDay} min</MenuItem>)}
                  </TextField>
                </TableCell>
                <TableCell><DateField value={a.start} onChange={(v) => setContract(i, { start: v })} /></TableCell>
                <TableCell><DateField value={a.end || ''} min={a.start} onChange={(v) => setContract(i, { end: v || null })} /></TableCell>
                <TableCell>
                  <IconButton size="small" color="error" onClick={() => setForm((f) => ({ ...f, contractAssignments: f.contractAssignments.filter((_, j) => j !== i) }))}>
                    <Delete fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {errors.contracts && <Alert severity="error" sx={{ mt: 1 }}>{errors.contracts}</Alert>}

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle1" fontWeight={600}>Competencies</Typography>
        <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
          <strong>Level 1 is the highest</strong> — your most senior person is level 1; level 5 is more junior than level 2.
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start', mb: 1 }}>
          <TextField select size="small" label="Dimension" value={pick.pair} onChange={(e) => setPick({ ...pick, pair: e.target.value })} sx={{ minWidth: 220 }}>
            {dims.length === 0 && <MenuItem value="" disabled>Declare dimensions first</MenuItem>}
            {dims.map((d) => <MenuItem key={pairKey(d.tableName, d.tableValue)} value={pairKey(d.tableName, d.tableValue)}>{pairLabel(d.tableName, d.tableValue)}{d.name ? ` — ${d.name}` : ''}</MenuItem>)}
          </TextField>
          <NumberField label="Level" value={pick.level} min={1} step={1} onChange={(v) => setPick({ ...pick, level: v })} sx={{ width: 130 }} helperText="1 = most senior" />
          <Button variant="outlined" onClick={addCompetency} disabled={!pick.pair}>Add</Button>
          <Tooltip title="Add every declared dimension this employee does not hold yet, at this level">
            <span><Button onClick={addAllCompetencies} disabled={!dims.length}>Add all</Button></span>
          </Tooltip>
        </Box>
        {form.competencyAssignments.length > 0 && (
          <Table size="small">
            <TableHead>
              <TableRow><TableCell>Dimension</TableCell><TableCell>Level</TableCell><TableCell>From</TableCell><TableCell>To (empty = open)</TableCell><TableCell /></TableRow>
            </TableHead>
            <TableBody>
              {form.competencyAssignments.map((a, i) => (
                <TableRow key={i}>
                  <TableCell>{pairLabel(a.tableName, a.tableValue)}</TableCell>
                  <TableCell><NumberField value={a.level} min={1} step={1} onChange={(v) => setCompetency(i, { level: v })} sx={{ width: 80 }} /></TableCell>
                  <TableCell><DateField value={a.start} onChange={(v) => setCompetency(i, { start: v })} /></TableCell>
                  <TableCell><DateField value={a.end || ''} min={a.start} onChange={(v) => setCompetency(i, { end: v || null })} /></TableCell>
                  <TableCell>
                    <IconButton size="small" color="error" onClick={() => setForm((f) => ({ ...f, competencyAssignments: f.competencyAssignments.filter((_, j) => j !== i) }))}>
                      <Delete fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
        {!form.competencyAssignments.length && (
          <Alert severity="warning" sx={{ mt: 1 }}>No competencies: this employee cannot cover any demand row.</Alert>
        )}
        {competencyClashes.map(([a, b]) => (
          <Alert key={`${a.i}-${b.i}`} severity="warning" sx={{ mt: 1 }}>
            {pairLabel(a.tableName, a.tableValue)} is held twice over overlapping dates
            {Number(a.level) !== Number(b.level) ? ` at levels ${a.level} and ${b.level}, so the level is ambiguous` : ''}.
          </Alert>
        ))}
        {errors.competencies && <Alert severity="error" sx={{ mt: 1 }}>{errors.competencies}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={save}>{employee.id ? 'Save' : 'Add'}</Button>
      </DialogActions>
    </Dialog>
  );
};

export default EmployeeForm;

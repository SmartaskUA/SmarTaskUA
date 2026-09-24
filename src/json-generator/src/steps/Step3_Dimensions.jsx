import React, { useMemo, useState } from 'react';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Chip, Alert, Autocomplete
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import { ConfirmDialog } from '../components/shared/fields';
import { useWizard } from '../context/WizardContext';
import { DIMENSION_NAME_SUGGESTIONS } from '../v4/constants';
import { dimensionUsage, removeDimension, updateDimension } from '../v4/operations';
import { getTeamColor } from '../utils/helpers/colorHelpers';

const EMPTY = { tableName: '', tableValue: '', name: '', description: '' };

const usageText = (u) => [
  u.periods && `${u.periods} periods row(s)`,
  u.days && `${u.days} days row(s)`,
  u.shifts && `${u.shifts} shifts row(s)`,
  u.blocks && `${u.blocks} template block(s)`,
  u.competencies && `${u.competencies} competency assignment(s)`,
  u.priority && `${u.priority} priority rank(s)`
].filter(Boolean);

/**
 * Step 3: Dimensions — the catalogue of (tableName, tableValue) coverage
 * coordinates. Required, and the only thing that makes a coordinate checkable.
 */
const Step3_Dimensions = () => {
  const { state, updateState, transform } = useWizard();
  const dims = state.demand.dimensions;

  const [editing, setEditing] = useState(null); // null | 'new' | {tableName, tableValue}
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(null);

  const grouped = useMemo(() => {
    const out = new Map();
    for (const d of dims) {
      if (!out.has(d.tableName)) out.set(d.tableName, []);
      out.get(d.tableName).push(d);
    }
    return [...out.entries()];
  }, [dims]);
  const nameOptions = [...new Set([...DIMENSION_NAME_SUGGESTIONS, ...dims.map((d) => d.tableName)])];

  const open = (d) => {
    setEditing(d ? { tableName: d.tableName, tableValue: d.tableValue } : 'new');
    setForm(d ? { ...EMPTY, ...d } : { ...EMPTY, tableName: dims[dims.length - 1]?.tableName || '' });
    setError('');
  };

  const taken = (tn, tv) => dims.some((d) => d.tableName === tn && d.tableValue === tv &&
    !(editing !== 'new' && editing.tableName === tn && editing.tableValue === tv));

  const save = () => {
    const tableName = form.tableName.trim();
    if (!tableName) return setError('Give the dimension a name, e.g. Team');
    if (editing === 'new') {
      // Several values at once: "A, C, G".
      const values = form.tableValue.split(',').map((v) => v.trim()).filter(Boolean);
      if (!values.length) return setError('Give at least one value');
      const clash = values.find((v) => taken(tableName, v));
      if (clash) return setError(`${tableName}/${clash} is already declared`);
      const single = values.length === 1;
      updateState('demand.dimensions', (list) => [...list, ...values.map((tableValue) => ({
        tableName, tableValue, name: single ? form.name.trim() : '', description: single ? form.description.trim() : ''
      }))]);
    } else {
      const tableValue = form.tableValue.trim();
      if (!tableValue) return setError('Give a value');
      if (taken(tableName, tableValue)) return setError(`${tableName}/${tableValue} is already declared`);
      transform((s) => updateDimension(s, editing, {
        tableName, tableValue, name: form.name.trim(), description: form.description.trim()
      }));
    }
    setEditing(null);
    return null;
  };

  const deletingUsage = deleting ? usageText(dimensionUsage(state, deleting.tableName, deleting.tableValue)) : [];

  return (
    <StepLayout
      stepId="dimensions"
      title="Coverage dimensions"
      subtitle="Demand is keyed on a (tableName, tableValue) pair — Team/T1, Responsibility/A. A worker can hold several, and each demand row on each axis is satisfied independently."
      actions={<Button variant="contained" startIcon={<Add />} onClick={() => open(null)}>Add dimension</Button>}
      nextDisabled={!dims.length}
    >
      <StepCard>
        <Alert severity="info" sx={{ mb: 2 }}>
          Every pair used by an employee, a demand row or a priority rank must be declared here.
          SISQUAL&apos;s export names the axes <code>Equipa</code>/<code>Piso</code> on employees but
          <code> Team</code>/<code>Responsibility</code> elsewhere — v4 uses the English names throughout (agenda item 11).
        </Alert>
        {!dims.length ? (
          <Alert severity="warning">No dimensions declared. At least one is required.</Alert>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>tableName</TableCell>
                  <TableCell>tableValue</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell align="center">Employees holding it</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {grouped.map(([tableName, values]) => values.map((d, i) => {
                  const holders = state.employees.list.filter((e) => (e.competencyAssignments || [])
                    .some((a) => a.tableName === d.tableName && a.tableValue === d.tableValue)).length;
                  return (
                    <TableRow key={`${d.tableName}/${d.tableValue}`} hover>
                      <TableCell sx={{ fontWeight: 600, borderBottom: i < values.length - 1 ? 'none' : undefined }}>
                        {i === 0 ? tableName : ''}
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={d.tableValue} sx={{ bgcolor: getTeamColor(`${d.tableName}/${d.tableValue}`), color: '#fff' }} />
                      </TableCell>
                      <TableCell>{d.name}</TableCell>
                      <TableCell>{d.description}</TableCell>
                      <TableCell align="center">{holders}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => open(d)}><Edit fontSize="small" /></IconButton>
                        <IconButton size="small" color="error" onClick={() => setDeleting(d)}><Delete fontSize="small" /></IconButton>
                      </TableCell>
                    </TableRow>
                  );
                }))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </StepCard>

      <Dialog open={editing !== null} onClose={() => setEditing(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing === 'new' ? 'Add dimension' : 'Edit dimension'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Autocomplete
              freeSolo
              options={nameOptions}
              value={form.tableName}
              inputValue={form.tableName}
              onInputChange={(_, v) => setForm((f) => ({ ...f, tableName: v }))}
              renderInput={(params) => <TextField {...params} label="tableName (the axis)" required autoFocus />}
            />
            <TextField
              label={editing === 'new' ? 'tableValue(s)' : 'tableValue'}
              value={form.tableValue}
              onChange={(e) => setForm({ ...form, tableValue: e.target.value })}
              helperText={editing === 'new' ? 'Comma-separate to add several: A, C, G' : 'Renaming updates every reference to this pair'}
              required
            />
            <TextField label="Name (optional)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <TextField label="Description (optional)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            {error && <Alert severity="error">{error}</Alert>}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={save}>{editing === 'new' ? 'Add' : 'Save'}</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={!!deleting}
        title={`Delete ${deleting?.tableName}/${deleting?.tableValue}?`}
        confirmLabel="Delete everywhere"
        confirmColor="error"
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          transform((s) => removeDimension(s, deleting.tableName, deleting.tableValue));
          setDeleting(null);
        }}
      >
        {deletingUsage.length ? (
          <>
            <Typography gutterBottom>This also removes:</Typography>
            <Box component="ul" sx={{ mt: 0 }}>{deletingUsage.map((t) => <li key={t}>{t}</li>)}</Box>
          </>
        ) : 'Nothing references it.'}
      </ConfirmDialog>
    </StepLayout>
  );
};

export default Step3_Dimensions;

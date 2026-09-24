import React, { useState } from 'react';
import {
  Box, Typography, Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Chip, Alert, InputAdornment, Stack
} from '@mui/material';
import { Add, Edit, Delete } from '@mui/icons-material';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import { ConfirmDialog } from '../components/shared/fields';
import { useWizard } from '../context/WizardContext';
import { onGrid, formatNumber } from '../v4/core';
import { contractUsage, renameContract } from '../v4/operations';

const hours = (minutes) => formatNumber(Math.round((minutes / 60) * 100) / 100);

const EMPTY = { id: '', name: '', workMinutesPerDay: 480 };

/**
 * Step 2: Contracts — v4 carries only a contract's length, in minutes.
 */
const Step2_Contracts = () => {
  const { state, updateState, transform } = useWizard();
  const contracts = state.contracts.definitions;
  const slot = state.timeGrid.slotMinutes;

  const [editing, setEditing] = useState(null); // null | 'new' | original id
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [deleting, setDeleting] = useState(null);

  const open = (contract) => {
    setEditing(contract ? contract.id : 'new');
    setForm(contract ? { ...EMPTY, ...contract } : EMPTY);
    setErrors({});
  };

  const save = () => {
    const id = form.id.trim();
    const minutes = Number(form.workMinutesPerDay);
    const e = {};
    if (!id) e.id = 'Required';
    else if (id !== editing && contracts.some((c) => c.id === id)) e.id = 'Already used';
    if (!Number.isInteger(minutes) || minutes < 0 || minutes > 1440) e.minutes = 'A whole number of minutes, 0–1440';
    setErrors(e);
    if (Object.keys(e).length) return;

    const contract = { id, name: form.name.trim(), workMinutesPerDay: minutes };
    transform((s) => {
      const renamed = editing !== 'new' && editing !== id ? renameContract(s, editing, id) : s;
      const definitions = editing === 'new'
        ? [...s.contracts.definitions, contract]
        : s.contracts.definitions.map((c) => (c.id === editing ? contract : c));
      return { ...renamed, contracts: { ...renamed.contracts, definitions } };
    });
    setEditing(null);
  };

  const minutes = Number(form.workMinutesPerDay);
  const formOffGrid = Number.isInteger(minutes) && !onGrid(minutes, slot);

  return (
    <StepLayout
      stepId="contracts"
      title="Contracts"
      subtitle="Each contract states the length of one working day, in minutes. A schedule-input cell of A works exactly this."
      actions={<Button variant="contained" startIcon={<Add />} onClick={() => open(null)}>Add contract</Button>}
      nextDisabled={!contracts.length}
    >
      <StepCard>
        <Alert severity="info" sx={{ mb: 2 }}>
          In v4 a contract carries only its daily length. Weekly hours, working days per week and per-weekday
          lengths are not in the format yet (FUTURE.md §1, agenda item 7), so two contracts with the same
          minutes are indistinguishable to a solver.
        </Alert>
        {!contracts.length ? (
          <Alert severity="warning">No contracts yet. Every employee needs one to be scheduled.</Alert>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align="right">Minutes / day</TableCell>
                  <TableCell align="center">Employees</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {contracts.map((c) => {
                  const offGrid = !onGrid(Number(c.workMinutesPerDay), slot);
                  return (
                    <TableRow key={c.id} hover>
                      <TableCell><Chip size="small" label={c.id} /></TableCell>
                      <TableCell>{c.name || <Typography variant="body2" color="text.disabled">—</Typography>}</TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end" alignItems="center">
                          {offGrid && <Chip size="small" color="error" label={`off the ${slot}-min grid`} />}
                          <Typography fontWeight={600}>{c.workMinutesPerDay} min</Typography>
                          <Typography variant="body2" color="text.secondary">({hours(c.workMinutesPerDay)} h)</Typography>
                        </Stack>
                      </TableCell>
                      <TableCell align="center">{contractUsage(state, c.id)}</TableCell>
                      <TableCell align="right">
                        <IconButton size="small" onClick={() => open(c)}><Edit fontSize="small" /></IconButton>
                        <IconButton size="small" color="error" onClick={() => setDeleting(c)}><Delete fontSize="small" /></IconButton>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </StepCard>

      <Dialog open={editing !== null} onClose={() => setEditing(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing === 'new' ? 'Add contract' : 'Edit contract'}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Contract ID"
              value={form.id}
              onChange={(e) => setForm({ ...form, id: e.target.value })}
              error={!!errors.id}
              helperText={errors.id || (editing !== 'new' ? 'Renaming updates every employee assignment' : 'e.g. PT_40')}
              required
              autoFocus
            />
            <TextField
              label="Name (optional)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              helperText="SISQUAL's names state WEEKLY hours ('[PT] 40h Semanais'). Never derive the daily minutes from them."
            />
            <TextField
              type="number"
              label="Work minutes per day"
              value={form.workMinutesPerDay}
              onChange={(e) => setForm({ ...form, workMinutesPerDay: e.target.value === '' ? '' : Number(e.target.value) })}
              error={!!errors.minutes || formOffGrid}
              helperText={errors.minutes || (formOffGrid
                ? `Not a multiple of the ${slot}-minute grid: no shift of this length can be placed`
                : 'Minutes — the matching schedule-input cell states the same length in hours')}
              inputProps={{ min: 0, max: 1440, step: slot }}
              InputProps={{
                endAdornment: <InputAdornment position="end">{Number.isFinite(minutes) ? `= ${hours(minutes)} h` : ''}</InputAdornment>
              }}
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={save}>{editing === 'new' ? 'Add' : 'Save'}</Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={!!deleting}
        title={`Delete contract ${deleting?.id}?`}
        confirmLabel="Delete"
        confirmColor="error"
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          updateState('contracts.definitions', contracts.filter((c) => c.id !== deleting.id));
          setDeleting(null);
        }}
      >
        {deleting && contractUsage(state, deleting.id)
          ? `${contractUsage(state, deleting.id)} employee(s) are assigned to it. Their assignments will point at a missing contract until you change them.`
          : 'No employee uses it.'}
      </ConfirmDialog>
    </StepLayout>
  );
};

export default Step2_Contracts;

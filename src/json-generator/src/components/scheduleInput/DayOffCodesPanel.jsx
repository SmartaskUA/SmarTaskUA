import React, { useState } from 'react';
import {
  Box, Typography, Table, TableHead, TableRow, TableCell, TableBody, TextField, IconButton, Button,
  ToggleButtonGroup, ToggleButton, Chip, Tooltip, Alert, Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import { Add, Delete, Edit } from '@mui/icons-material';
import { ConfirmDialog } from '../shared/fields';
import { useWizard } from '../../context/WizardContext';
import { OPERATORS } from '../../v4/constants';
import { tryNumber } from '../../v4/core';
import { codeUsage, removeDayOffCode, renameDayOffCode } from '../../v4/operations';

export const KIND_COLORS = { preferable: '#fff59d', unavailable: '#ffcdd2' };

/** Why `code` cannot be a day-off code, or '' when it can. */
function codeProblem(code, codes, current) {
  const c = code.trim();
  if (!c) return 'Give the code a name';
  if (c !== code) return 'No leading or trailing spaces';
  if (c.toUpperCase() === 'A') return '"A" already means "work the contract length"';
  if (tryNumber(c) !== null) return 'A number is read as hours';
  if (OPERATORS.some((op) => c.toUpperCase().startsWith(`${op}:`))) return 'That prefix is an operator';
  if (c.includes(',')) return 'Commas are not allowed';
  if (c !== current && c in codes) return 'Already declared';
  return '';
}

function KindToggle({ value, onChange }) {
  return (
    <ToggleButtonGroup size="small" exclusive value={value} onChange={(_, v) => v && onChange(v)}>
      <ToggleButton value="preferable" sx={{ '&.Mui-selected': { bgcolor: KIND_COLORS.preferable } }}>
        <Tooltip title="Soft (D_wk): the solver may schedule over it at a penalty"><span>Preferable</span></Tooltip>
      </ToggleButton>
      <ToggleButton value="unavailable" sx={{ '&.Mui-selected': { bgcolor: KIND_COLORS.unavailable } }}>
        <Tooltip title="Hard (U_wk): no assignment permitted"><span>Unavailable</span></Tooltip>
      </ToggleButton>
    </ToggleButtonGroup>
  );
}

/**
 * The palette of non-working cell codes. There are no implicit codes in v4:
 * every one a cell uses must be declared here, and its kind moves that week's
 * working-day target n_wk = open days − unavailable − preferable.
 */
const DayOffCodesPanel = () => {
  const { state, updateState, transform } = useWizard();
  const codes = state.scheduleInput.dayOffCodes;
  const [draft, setDraft] = useState({ code: '', kind: 'preferable', name: '', description: '' });
  const [renaming, setRenaming] = useState(null);
  const [newName, setNewName] = useState('');
  const [deleting, setDeleting] = useState(null);

  const draftProblem = draft.code ? codeProblem(draft.code, codes) : '';
  const setEntry = (code, patch) => updateState('scheduleInput.dayOffCodes', (all) => ({ ...all, [code]: { ...all[code], ...patch } }));

  const add = () => {
    if (codeProblem(draft.code, codes)) return;
    const { code, ...entry } = draft;
    updateState('scheduleInput.dayOffCodes', (all) => ({ ...all, [code]: entry }));
    setDraft({ code: '', kind: 'preferable', name: '', description: '' });
  };

  const renameProblem = renaming ? codeProblem(newName, codes, renaming) : '';

  return (
    <Box>
      <Typography variant="h6" fontWeight={600}>Day-off codes</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Any cell that is not <code>A</code>, a number of hours or a time window must be one of these. Codes may be
        non-ASCII (SISQUAL uses <code>Fér</code>). Classifying a code wrongly still validates — and moves every
        week&apos;s working-day target.
      </Typography>
      {!Object.keys(codes).length && <Alert severity="error" sx={{ mb: 1 }}>At least one day-off code is required.</Alert>}
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Code</TableCell>
            <TableCell>Kind</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Description</TableCell>
            <TableCell align="center">Cells</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {Object.entries(codes).map(([code, entry]) => {
            const used = codeUsage(state, code);
            return (
              <TableRow key={code}>
                <TableCell><Chip label={code} size="small" sx={{ bgcolor: KIND_COLORS[entry.kind], fontWeight: 700 }} /></TableCell>
                <TableCell><KindToggle value={entry.kind} onChange={(kind) => setEntry(code, { kind })} /></TableCell>
                <TableCell><TextField size="small" value={entry.name || ''} onChange={(e) => setEntry(code, { name: e.target.value })} /></TableCell>
                <TableCell><TextField size="small" fullWidth value={entry.description || ''} onChange={(e) => setEntry(code, { description: e.target.value })} /></TableCell>
                <TableCell align="center">
                  {used ? used : <Tooltip title="Declared but no cell uses it (a warning)"><Chip size="small" color="warning" variant="outlined" label="unused" /></Tooltip>}
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  <IconButton size="small" onClick={() => { setRenaming(code); setNewName(code); }}><Edit fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => setDeleting(code)}><Delete fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            );
          })}
          <TableRow>
            <TableCell>
              <TextField size="small" placeholder="New code" value={draft.code} error={!!draftProblem} helperText={draftProblem}
                onChange={(e) => setDraft({ ...draft, code: e.target.value })} sx={{ width: 130 }}
              />
            </TableCell>
            <TableCell><KindToggle value={draft.kind} onChange={(kind) => setDraft({ ...draft, kind })} /></TableCell>
            <TableCell><TextField size="small" placeholder="Name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></TableCell>
            <TableCell><TextField size="small" fullWidth placeholder="Description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} /></TableCell>
            <TableCell />
            <TableCell>
              <Button size="small" startIcon={<Add />} onClick={add} disabled={!draft.code || !!draftProblem}>Add</Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>

      <Dialog open={!!renaming} onClose={() => setRenaming(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Rename {renaming}</DialogTitle>
        <DialogContent>
          <TextField autoFocus fullWidth sx={{ mt: 1 }} value={newName} onChange={(e) => setNewName(e.target.value)}
            error={!!renameProblem} helperText={renameProblem || `Every cell using ${renaming} is renamed too`}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenaming(null)}>Cancel</Button>
          <Button variant="contained" disabled={!!renameProblem}
            onClick={() => { transform((s) => renameDayOffCode(s, renaming, newName)); setRenaming(null); }}
          >
            Rename
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={!!deleting}
        title={`Delete ${deleting}?`}
        confirmLabel="Delete"
        confirmColor="error"
        onCancel={() => setDeleting(null)}
        onConfirm={() => { transform((s) => removeDayOffCode(s, deleting, '')); setDeleting(null); }}
      >
        {deleting && codeUsage(state, deleting)
          ? `${codeUsage(state, deleting)} cell(s) use it. They become blank — no assignment on that day.`
          : 'No cell uses it.'}
      </ConfirmDialog>
    </Box>
  );
};

export default DayOffCodesPanel;

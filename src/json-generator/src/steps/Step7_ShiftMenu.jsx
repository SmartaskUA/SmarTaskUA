import React, { useMemo, useState } from 'react';
import {
  Box, Typography, Button, Switch, FormControlLabel, Table, TableHead, TableRow, TableCell, TableBody, TableContainer,
  Paper, IconButton, Chip, Alert, Dialog, DialogTitle, DialogContent, DialogActions, TextField, MenuItem, Grid, Tooltip
} from '@mui/material';
import { Add, Edit, Delete, AutoFixHigh, Lock } from '@mui/icons-material';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import { NumberField, TimeField } from '../components/shared/fields';
import { useWizard } from '../context/WizardContext';
import { REST_SENTINELS } from '../v4/constants';
import { hhmmToMin, minToHhmm, onGrid, tryParseRange } from '../v4/core';
import { demandEnvelope, generateMenuRows, menuRow, nextMenuCode } from '../v4/operations';

const SENTINEL_CODES = new Set(REST_SENTINELS.map((s) => s.code));
const isRest = (r) => (r.startMin === null || r.startMin === undefined) && !Number(r.scheduleWeightMinutes);
const locked = (r) => SENTINEL_CODES.has(Number(r.code)) && isRest(r);

/**
 * Step 7: Shift menu — schedules.csv, the ScheduleCodes a result may pick
 * from. A code means a grouping of hours and nothing else; this file is the
 * translation, and the codes are ours to mint.
 */
const Step7_ShiftMenu = () => {
  const { state, updateState } = useWizard();
  const { schedules, timeGrid, contracts } = state;
  const slot = timeGrid.slotMinutes;
  const rows = schedules.rows;

  const [editing, setEditing] = useState(null); // {index, code, kind, start, end, description}
  const [error, setError] = useState('');
  const [generate, setGenerate] = useState(null);

  const envelope = useMemo(() => demandEnvelope(state), [state]);
  const lengths = [...new Set(contracts.definitions.map((c) => Number(c.workMinutesPerDay)).filter((m) => m > 0))];
  const worked = rows.filter((r) => !isRest(r));
  const missingLengths = lengths.filter((m) => !worked.some((r) => Number(r.scheduleWeightMinutes) === m));
  const codeCounts = rows.reduce((m, r) => m.set(Number(r.code), (m.get(Number(r.code)) || 0) + 1), new Map());
  const hasSentinels = REST_SENTINELS.every((s) => rows.some((r) => Number(r.code) === s.code));

  const setRows = (next) => updateState('schedules.rows', next);

  const openEditor = (row, index) => {
    setError('');
    setEditing(row
      ? {
        index, code: row.code, kind: isRest(row) ? 'rest' : 'work', description: row.description,
        start: row.startMin !== null && row.startMin !== undefined ? minToHhmm(row.startMin) : '09:00',
        end: row.endMin !== null && row.endMin !== undefined ? minToHhmm(row.endMin) : '17:00'
      }
      : { index: -1, code: nextMenuCode(rows), kind: 'work', description: '', start: '09:00', end: '17:00' });
  };

  const saveEditor = () => {
    const code = Number(editing.code);
    if (!Number.isInteger(code)) return setError('The code must be a whole number');
    if (rows.some((r, i) => Number(r.code) === code && i !== editing.index)) return setError(`Code ${code} is already used`);
    let row;
    if (editing.kind === 'rest') {
      if (!editing.description.trim()) return setError('Describe the rest code');
      row = { code, description: editing.description.trim(), scheduleWeightMinutes: 0, startMin: null, endMin: null };
    } else {
      const w = tryParseRange(editing.start, editing.end);
      if (!w) return setError('A start and an end are required');
      row = menuRow(code, w[0], w[1]);
    }
    setRows(editing.index < 0 ? [...rows, row] : rows.map((r, i) => (i === editing.index ? row : r)));
    setEditing(null);
    return null;
  };

  const candidates = useMemo(() => {
    if (!generate) return [];
    const start = hhmmToMinSafe(generate.start);
    const end = hhmmToMinSafe(generate.end);
    if (start === null || end === null) return [];
    return generateMenuRows(state, { stride: generate.stride, envelope: { start, end: end <= start ? end + 1440 : end } });
  }, [generate, state]);

  return (
    <StepLayout
      stepId="schedules"
      title="Shift menu"
      subtitle="The ScheduleCodes a result may use. A result names numeric codes only, so this file is what they mean."
      actions={(
        <FormControlLabel
          control={<Switch checked={schedules.enabled} onChange={(e) => updateState('schedules.enabled', e.target.checked)} />}
          label="Include schedules.csv"
        />
      )}
    >
      {!schedules.enabled ? (
        <StepCard>
          <Alert severity="info">
            The menu is optional. Without it, a result&apos;s ScheduleCodes cannot be checked against the shifts this
            problem offers. Switch it on to author one.
          </Alert>
        </StepCard>
      ) : (
        <StepCard>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
            <Button variant="contained" startIcon={<Add />} onClick={() => openEditor(null)}>Add row</Button>
            <Button variant="outlined" startIcon={<AutoFixHigh />} disabled={!lengths.length}
              onClick={() => setGenerate({
                stride: 60,
                start: envelope ? minToHhmm(envelope.start) : '08:00',
                end: envelope ? minToHhmm(envelope.end) : '20:00'
              })}
            >
              Generate from contracts
            </Button>
            {!hasSentinels && (
              <Button onClick={() => setRows([...REST_SENTINELS.filter((s) => !rows.some((r) => Number(r.code) === s.code))
                .map((s) => ({ code: s.code, description: s.description, scheduleWeightMinutes: 0, startMin: null, endMin: null })), ...rows])}
              >
                Add WFM rest codes 1, 3, 4
              </Button>
            )}
          </Box>
          <Alert severity="info" sx={{ mb: 2 }}>
            Codes 1 (Espaço), 3 (Day off) and 4 (Vazio) keep WFM&apos;s rest semantics; every other number is ours and
            arbitrary. A row with no window and zero weight is a rest code. v4 has no break model, so a shift&apos;s paid
            length is its clock length (FUTURE.md §2). Whether WFM accepts codes it does not already hold is agenda item 5.
          </Alert>
          {missingLengths.length > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              No shift matches the contract length(s) {missingLengths.map((m) => `${m} min`).join(', ')} — a result
              could not give those employees a shift of exactly their contracted length.
            </Alert>
          )}
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>code</TableCell>
                  <TableCell>description</TableCell>
                  <TableCell align="right">scheduleWeightMinutes</TableCell>
                  <TableCell>startMin–endMin</TableCell>
                  <TableCell />
                  <TableCell align="right" />
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((r, i) => {
                  const offGrid = !isRest(r) && (!onGrid(Number(r.startMin), slot) || !onGrid(Number(r.endMin), slot));
                  return (
                    <TableRow key={`${r.code}-${i}`} hover>
                      <TableCell sx={{ fontWeight: 600 }}>
                        {r.code}
                        {codeCounts.get(Number(r.code)) > 1 && <Chip size="small" color="error" label="duplicate" sx={{ ml: 1 }} />}
                      </TableCell>
                      <TableCell>{r.description}</TableCell>
                      <TableCell align="right">{r.scheduleWeightMinutes}</TableCell>
                      <TableCell sx={{ fontFamily: 'monospace' }}>
                        {isRest(r) ? '—' : `${r.startMin}–${r.endMin}`}
                        {!isRest(r) && Number(r.endMin) > 1440 && <Chip size="small" label="+1 day" sx={{ ml: 1, height: 18 }} />}
                      </TableCell>
                      <TableCell>
                        {isRest(r) ? <Chip size="small" label="rest" /> : <Chip size="small" color="primary" variant="outlined" label={`${Math.round(r.scheduleWeightMinutes / 6) / 10} h`} />}
                        {offGrid && <Chip size="small" color="warning" label="off grid" sx={{ ml: 1 }} />}
                      </TableCell>
                      <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                        {locked(r) ? (
                          <Tooltip title="WFM rest code — kept as is"><Lock fontSize="small" color="disabled" /></Tooltip>
                        ) : (
                          <>
                            <IconButton size="small" onClick={() => openEditor(r, i)}><Edit fontSize="small" /></IconButton>
                            <IconButton size="small" color="error" onClick={() => setRows(rows.filter((_, j) => j !== i))}><Delete fontSize="small" /></IconButton>
                          </>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </StepCard>
      )}

      <Dialog open={!!editing} onClose={() => setEditing(null)} maxWidth="xs" fullWidth>
        <DialogTitle>{editing?.index >= 0 ? 'Edit' : 'Add'} menu row</DialogTitle>
        {editing && (
          <DialogContent>
            <Grid container spacing={2} sx={{ pt: 1 }}>
              <Grid size={6}><NumberField fullWidth label="code" value={editing.code} step={1} onChange={(v) => setEditing({ ...editing, code: v })} /></Grid>
              <Grid size={6}>
                <TextField select fullWidth size="small" label="kind" value={editing.kind} onChange={(e) => setEditing({ ...editing, kind: e.target.value })}>
                  <MenuItem value="work">worked shift</MenuItem>
                  <MenuItem value="rest">rest (no window)</MenuItem>
                </TextField>
              </Grid>
              {editing.kind === 'work' ? (
                <>
                  <Grid size={6}><TimeField fullWidth label="Start" value={editing.start} slotMinutes={slot} onChange={(v) => setEditing({ ...editing, start: v })} /></Grid>
                  <Grid size={6}><TimeField fullWidth label="End" value={editing.end} slotMinutes={slot} onChange={(v) => setEditing({ ...editing, end: v })} /></Grid>
                  <Grid size={12}>
                    {tryParseRange(editing.start, editing.end) && (() => {
                      const w = tryParseRange(editing.start, editing.end);
                      const row = menuRow(editing.code, w[0], w[1]);
                      return <Alert severity="info">{row.description} · {row.scheduleWeightMinutes} min · {row.startMin}–{row.endMin}</Alert>;
                    })()}
                  </Grid>
                </>
              ) : (
                <Grid size={12}>
                  <TextField fullWidth size="small" label="description" value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} />
                </Grid>
              )}
            </Grid>
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
          </DialogContent>
        )}
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={saveEditor}>Save</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!generate} onClose={() => setGenerate(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Generate shifts from contract lengths</DialogTitle>
        {generate && (
          <DialogContent>
            <Typography variant="body2" color="text.secondary" paragraph>
              For each contract length ({lengths.map((m) => `${m} min`).join(', ')}), one shift per start time inside the
              window below, stepping by the stride. Windows the menu already has are skipped.
              {envelope && ` The window defaults to the demand's envelope, ${minToHhmm(envelope.start)}–${minToHhmm(envelope.end)}.`}
            </Typography>
            <Grid container spacing={2}>
              <Grid size={4}><TimeField fullWidth label="Earliest start" value={generate.start} slotMinutes={slot} onChange={(v) => setGenerate({ ...generate, start: v })} /></Grid>
              <Grid size={4}><TimeField fullWidth label="Latest end" value={generate.end} slotMinutes={slot} onChange={(v) => setGenerate({ ...generate, end: v })} /></Grid>
              <Grid size={4}>
                <TextField select fullWidth size="small" label="Stride" value={generate.stride} onChange={(e) => setGenerate({ ...generate, stride: Number(e.target.value) })}>
                  {[slot, 30, 60, 120, 240].filter((m, i, a) => m % slot === 0 && a.indexOf(m) === i).map((m) => <MenuItem key={m} value={m}>{m} min</MenuItem>)}
                </TextField>
              </Grid>
            </Grid>
            <Typography variant="subtitle2" sx={{ mt: 2 }}>{candidates.length} new row(s)</Typography>
            <Box sx={{ maxHeight: 220, overflow: 'auto', display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
              {candidates.map((r) => <Chip key={r.code} size="small" label={`${r.code} ${r.description}`} />)}
            </Box>
          </DialogContent>
        )}
        <DialogActions>
          <Button onClick={() => setGenerate(null)}>Cancel</Button>
          <Button variant="contained" disabled={!candidates.length} onClick={() => { setRows([...rows, ...candidates]); setGenerate(null); }}>
            Add {candidates.length}
          </Button>
        </DialogActions>
      </Dialog>
    </StepLayout>
  );
};

function hhmmToMinSafe(text) {
  try {
    return hhmmToMin(text);
  } catch {
    return null;
  }
}

export default Step7_ShiftMenu;

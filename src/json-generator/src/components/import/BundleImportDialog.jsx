import React, { useRef, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Alert, AlertTitle, Box,
  Typography, Chip, Stack, CircularProgress
} from '@mui/material';
import { UploadFile } from '@mui/icons-material';
import MenuConflictChooser from './MenuConflictChooser';
import { useWizard } from '../../context/useWizard';
import { sidecarName } from '../../v4/core';
import { importBundle, ImportError, readFileList } from '../../v4/importBundle';
import { applyMenuChoices } from '../../v4/operations';

/**
 * Load an existing v4.0 package — a ZIP, or problem.json plus its CSVs, and
 * optionally a result with its sidecar — into the wizard. Shows the
 * validator's verdict on the files before replacing the current work, and asks
 * which definition to keep wherever the menu and the result's sidecar define a
 * code differently.
 */
const BundleImportDialog = ({ open, onClose }) => {
  const { replaceState, goToStep } = useWizard();
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [choices, setChoices] = useState({});

  const reset = () => {
    setError('');
    setResult(null);
    setChoices({});
    setBusy(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleFiles = async (e) => {
    const { files } = e.target;
    if (!files?.length) return;
    reset();
    setBusy(true);
    try {
      setResult(importBundle(await readFileList(files)));
    } catch (exc) {
      setError(exc instanceof ImportError ? exc.message : `Could not read the files: ${exc.message}`);
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  };

  const handleConfirm = () => {
    replaceState(applyMenuChoices(result.state, result.conflicts, choices));
    goToStep(0);
    handleClose();
  };

  const s = result?.state;
  const conflicts = result?.conflicts || [];
  const undecided = conflicts.some((c) => !choices[c.code]);
  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Start from a v4.0 bundle</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" paragraph>
          Select a ZIP, or <code>problem.json</code> together with the CSVs it names. The CSVs are matched by file
          name. A <code>result.json</code> beside it, partial or complete, and its{' '}
          <code>result_schedules.csv</code> load as fixed days. Only v4.0 problems can be loaded: SISQUAL&apos;s
          current export (stamped <code>3.0</code>) is refused, because v4 ships no adapter.
        </Typography>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".zip,.json,.csv"
          style={{ display: 'none' }}
          onChange={handleFiles}
        />
        <Button variant="outlined" startIcon={<UploadFile />} onClick={() => inputRef.current?.click()} disabled={busy}>
          Choose files…
        </Button>
        {busy && <CircularProgress size={20} sx={{ ml: 2, verticalAlign: 'middle' }} />}

        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

        {result && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1" fontWeight={600}>{result.problemName}</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ my: 1 }}>
              <Chip size="small" label={s.metadata.problemId || '(no problemId)'} color="primary" />
              <Chip size="small" label={`${s.temporalScope.start} → ${s.temporalScope.end}`} />
              <Chip size="small" label={`${s.employees.list.length} employees`} />
              <Chip size="small" label={`${s.demand.dimensions.length} dimensions`} />
              <Chip size="small" label={`${s.demand.periods.length} periods rows`} />
              <Chip size="small" label={`${s.demand.days.length} days rows`} />
              <Chip size="small" label={`${s.demand.shifts.length} shifts rows`} />
              <Chip size="small" label={s.schedules.enabled ? `${s.schedules.rows.length} menu rows` : 'no menu'} />
              {result.resultName && (
                <Chip
                  size="small"
                  color="secondary"
                  label={`${result.resultName}: ${result.report.stats.rosterDays} fixed · ${result.report.stats.rosterDaysLeft} open`}
                />
              )}
            </Stack>
            {result.notes.map((n) => <Alert key={n} severity="info" sx={{ mb: 1 }}>{n}</Alert>)}
            {conflicts.length > 0 && (
              <MenuConflictChooser
                conflicts={conflicts}
                menuFile={s.files.schedules}
                sidecarFile={sidecarName(result.resultName)}
                choices={choices}
                onChange={setChoices}
              />
            )}
            <Alert severity={result.report.errors.length ? 'error' : result.report.warnings.length ? 'warning' : 'success'}>
              <AlertTitle>
                Validator: {result.report.errors.length} errors, {result.report.warnings.length} warnings
              </AlertTitle>
              {conflicts.length > 0 && (
                <Typography variant="body2" sx={{ mb: 1 }}>
                  On the files as selected: the ScheduleCode definitions settled above are consistent once imported.
                </Typography>
              )}
              {[...result.report.errors, ...result.report.warnings].slice(0, 8).map((f, i) => (
                <Typography key={i} variant="body2" sx={{ fontFamily: 'monospace', fontSize: 12 }}>{f.message}</Typography>
              ))}
              {result.report.errors.length + result.report.warnings.length > 8 && (
                <Typography variant="caption">…and more; every step lists its own.</Typography>
              )}
            </Alert>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} color="inherit">Cancel</Button>
        <Button onClick={handleConfirm} variant="contained" disabled={!result || undecided}>
          Replace current work
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BundleImportDialog;

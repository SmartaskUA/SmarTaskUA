import React, { useRef, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Alert, AlertTitle, Box,
  Typography, Chip, Stack, CircularProgress
} from '@mui/material';
import { UploadFile } from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';
import { importBundle, ImportError, readFileList } from '../../v4/importBundle';

/**
 * Load an existing v4.0 bundle — a ZIP, or problem.json plus its CSVs — into
 * the wizard. Shows the validator's verdict on the files before replacing the
 * current work.
 */
const BundleImportDialog = ({ open, onClose }) => {
  const { replaceState, goToStep } = useWizard();
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const reset = () => {
    setError('');
    setResult(null);
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
    replaceState(result.state);
    goToStep(0);
    handleClose();
  };

  const s = result?.state;
  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Start from a v4.0 bundle</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" paragraph>
          Select a ZIP, or <code>problem.json</code> together with the CSVs it names. The CSVs are matched by file
          name. Only v4.0 problems can be loaded: SISQUAL&apos;s current export (stamped <code>3.0</code>) is
          refused, because v4 ships no adapter.
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
            </Stack>
            {result.notes.map((n) => <Alert key={n} severity="info" sx={{ mb: 1 }}>{n}</Alert>)}
            <Alert severity={result.report.errors.length ? 'error' : result.report.warnings.length ? 'warning' : 'success'}>
              <AlertTitle>
                Validator: {result.report.errors.length} errors, {result.report.warnings.length} warnings
              </AlertTitle>
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
        <Button onClick={handleConfirm} variant="contained" disabled={!result}>
          Replace current work
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BundleImportDialog;

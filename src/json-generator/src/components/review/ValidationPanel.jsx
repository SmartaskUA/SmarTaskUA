import React, { useState } from 'react';
import {
  Card, CardHeader, CardContent, Alert, AlertTitle, Box, Chip, Button, Typography, Collapse, Stack
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, Warning } from '@mui/icons-material';
import { WIZARD_STEPS, stepIndex } from '../../constants/wizardSteps';

const STAT_LABELS = {
  days: 'days', openDays: 'open days', contracts: 'contracts', employees: 'employees', dimensions: 'dimensions',
  'demandRows.periods': 'periods rows', 'demandRows.days': 'days rows', 'demandRows.shifts': 'shifts rows',
  schedules: 'menu codes', priorityRanks: 'priority ranks'
};

function StepGroup({ step, errors, warnings, onJump }) {
  const [open, setOpen] = useState(errors.length > 0);
  return (
    <Box sx={{ mb: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Button size="small" onClick={() => setOpen(!open)} sx={{ textTransform: 'none', fontWeight: 600 }}>
          {stepIndex(step.id) + 1}. {step.label}
        </Button>
        {errors.length > 0 && <Chip size="small" color="error" label={`${errors.length} error(s)`} />}
        {warnings.length > 0 && <Chip size="small" color="warning" label={`${warnings.length} warning(s)`} />}
        <Box sx={{ flexGrow: 1 }} />
        <Button size="small" variant="outlined" onClick={() => onJump(stepIndex(step.id))}>Go to step</Button>
      </Box>
      <Collapse in={open}>
        <Box component="ul" sx={{ mt: 0.5, mb: 0, pl: 4 }}>
          {[...errors.map((f) => ['error', f]), ...warnings.map((f) => ['warning', f])].map(([sev, f], i) => (
            <Typography key={i} component="li" variant="body2" color={sev === 'error' ? 'error.main' : 'warning.dark'}
              sx={{ fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-word' }}
            >
              {f.message}
            </Typography>
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}

/**
 * The validator's verdict on the generated bundle — the same checks, and the
 * same wording, as `make validate` in json_generation/schema_v4.
 */
const ValidationPanel = ({ report, onJump }) => {
  const { errors, warnings, stats } = report;
  const icon = errors.length ? <ErrorIcon color="error" /> : warnings.length ? <Warning color="warning" /> : <CheckCircle color="success" />;
  const byStep = WIZARD_STEPS.map((step) => ({
    step,
    errors: errors.filter((f) => f.step === step.id),
    warnings: warnings.filter((f) => f.step === step.id)
  })).filter((g) => g.errors.length || g.warnings.length);

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardHeader avatar={icon} title="Validation" subheader="JSON Schema + the v4.0 validator's semantic checks, run on the files below" />
      <CardContent sx={{ pt: 0 }}>
        {errors.length === 0 ? (
          <Alert severity={warnings.length ? 'warning' : 'success'} sx={{ mb: 2 }}>
            <AlertTitle>{warnings.length ? 'Valid, with warnings' : 'Valid'}</AlertTitle>
            The bundle passes every check. {warnings.length > 0 && 'Warnings do not block the download.'}
          </Alert>
        ) : (
          <Alert severity="error" sx={{ mb: 2 }}>
            <AlertTitle>{errors.length} error(s)</AlertTitle>
            Fix them before downloading; a solver would reject or misread this bundle.
          </Alert>
        )}
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
          {Object.entries(STAT_LABELS).filter(([k]) => stats[k] !== undefined).map(([k, label]) => (
            <Chip key={k} size="small" variant="outlined" label={`${stats[k]} ${label}`} />
          ))}
        </Stack>
        {byStep.map((g) => <StepGroup key={g.step.id} {...g} onJump={onJump} />)}
      </CardContent>
    </Card>
  );
};

export default ValidationPanel;

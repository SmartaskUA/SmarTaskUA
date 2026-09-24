import React, { useState } from 'react';
import { Alert, Box, Button, Typography } from '@mui/material';
import { useWizard } from '../../context/WizardContext';
import { stepIndex } from '../../constants/wizardSteps';

const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** One severity's findings: a one-line summary that expands to the full list. */
function FindingList({ items, severity, initiallyOpen }) {
  const [open, setOpen] = useState(initiallyOpen);
  if (!items.length) return null;
  return (
    <Alert
      severity={severity}
      sx={{ mb: 1, py: 0.25, '& .MuiAlert-message': { width: '100%' } }}
      action={<Button size="small" color="inherit" onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'}</Button>}
    >
      <Typography variant="body2" fontWeight={600}>{plural(items.length, severity === 'error' ? 'error' : 'warning')}</Typography>
      {open && (
        <Box component="ul" sx={{ m: 0, mt: 0.5, pl: 2, maxHeight: 240, overflowY: 'auto' }}>
          {items.map((f, i) => (
            <Typography component="li" variant="body2" key={i} sx={{ fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-word' }}>
              {f.message}
            </Typography>
          ))}
        </Box>
      )}
    </Alert>
  );
}

/**
 * The validator's findings for one step, read from the bundle the whole state
 * generates — the same findings the Review step shows. Warnings start as a
 * one-line summary; errors start open once the step has been visited, so a
 * fresh form is not greeted by a wall of red.
 */
const StepFindings = ({ stepId }) => {
  const { findings, state } = useWizard();
  const { errors, warnings } = findings(stepId);
  if (!errors.length && !warnings.length) return null;
  const visited = !!state.stepCompleted?.[stepIndex(stepId)];
  return (
    <Box sx={{ mb: 2 }}>
      <FindingList items={errors} severity="error" initiallyOpen={visited} />
      <FindingList items={warnings} severity="warning" initiallyOpen={false} />
    </Box>
  );
};

export default StepFindings;

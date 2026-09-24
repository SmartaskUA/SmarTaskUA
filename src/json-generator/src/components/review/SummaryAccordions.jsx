import React from 'react';
import { Accordion, AccordionSummary, AccordionDetails, Typography, Box, Chip, Button, Stack } from '@mui/material';
import { ExpandMore, CheckCircle, Warning, Error as ErrorIcon } from '@mui/icons-material';
import { WIZARD_STEPS } from '../../constants/wizardSteps';
import { dateRange } from '../../v4/core';
import { pairLabel } from '../../v4/state';

const chips = (items) => (
  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
    {items.map((t) => <Chip key={t} size="small" label={t} />)}
  </Stack>
);

function summary(id, s) {
  switch (id) {
    case 'setup':
      return (
        <>
          <Typography variant="body2"><strong>{s.metadata.problemId || '(no problem id)'}</strong> · roster {s.metadata.rosterCode || '—'}</Typography>
          <Typography variant="body2">{s.temporalScope.start} → {s.temporalScope.end} ({dateRange(s.temporalScope.start, s.temporalScope.end).length} days), {s.timeGrid.slotMinutes}-minute slots, weeks start {s.calendar.weekStart}</Typography>
          <Typography variant="body2">{(s.calendar.holidays || []).length} holiday(s)</Typography>
        </>
      );
    case 'contracts':
      return chips(s.contracts.definitions.map((c) => `${c.id} · ${c.workMinutesPerDay} min`));
    case 'dimensions':
      return chips(s.demand.dimensions.map((d) => pairLabel(d.tableName, d.tableValue)));
    case 'employees':
      return <Typography variant="body2">{s.employees.list.length} employee(s)</Typography>;
    case 'scheduleInput':
      return chips(Object.entries(s.scheduleInput.dayOffCodes).map(([c, e]) => `${c} · ${e.kind}`));
    case 'demand':
      return <Typography variant="body2">{s.demand.periods.length} periods, {s.demand.days.length} days, {s.demand.shifts.length} shifts row(s)</Typography>;
    case 'schedules':
      return <Typography variant="body2">{s.schedules.enabled ? `${s.schedules.rows.length} menu row(s)` : 'No menu (schedules omitted)'}</Typography>;
    case 'rules':
      return <Typography variant="body2">{s.priorityHierarchy.length} priority rank(s), {s.constraints.hard.length} labour-law rule set(s)</Typography>;
    default:
      return null;
  }
}

/** One line per step, with its validation status and a jump back. */
const SummaryAccordions = ({ state, findings, onJump }) => (
  <Box sx={{ mb: 3 }}>
    {WIZARD_STEPS.filter((s) => s.id !== 'review').map((step, i) => {
      const { errors, warnings } = findings(step.id);
      const icon = errors.length ? <ErrorIcon color="error" /> : warnings.length ? <Warning color="warning" /> : <CheckCircle color="success" />;
      return (
        <Accordion key={step.id} disableGutters variant="outlined">
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {icon}
              <Typography fontWeight={600}>{i + 1}. {step.label}</Typography>
              {errors.length > 0 && <Chip size="small" color="error" label={errors.length} />}
              {warnings.length > 0 && <Chip size="small" color="warning" label={warnings.length} />}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            {summary(step.id, state)}
            <Button size="small" variant="outlined" sx={{ mt: 1 }} onClick={() => onJump(i)}>Edit step {i + 1}</Button>
          </AccordionDetails>
        </Accordion>
      );
    })}
  </Box>
);

export default SummaryAccordions;

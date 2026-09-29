import React, { useCallback, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography
} from '@mui/material';
import { EventAvailable } from '@mui/icons-material';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import FixedDaysMatrix from '../components/fixedDays/FixedDaysMatrix';
import { FIXED_COLORS } from '../components/fixedDays/fixedDayLabels';
import { useWizard } from '../context/useWizard';
import { stepIndex } from '../constants/wizardSteps';
import { activeContract } from '../v4/core';
import {
  analyseFixedDay, entryDay, entryEmployee, holidayDates, horizonOf, menuCatalogue,
  openDays as openDaysOf, resultCounts, setFixedDay
} from '../v4/operations';

/**
 * Step 8: Fixed days — result.json. The days already decided: each is an
 * OutRosterTeamDays entry the solver must keep, and every day without one is
 * left open. An imported result, partial or complete, lands here. Days are
 * fixed, changed and opened again in the grid, one cell at a time.
 */
const Step8_FixedDays = () => {
  const { state, transform, goToStep } = useWizard();
  const [open, setOpen] = useState(false);

  const employees = state.employees.list;
  const entries = state.result.entries;
  const dates = useMemo(() => horizonOf(state), [state.temporalScope]); // eslint-disable-line react-hooks/exhaustive-deps
  const openDays = useMemo(() => openDaysOf(state), [state.demand.periods, state.demand.shifts]); // eslint-disable-line react-hooks/exhaustive-deps
  const holidays = useMemo(() => holidayDates(state), [state.calendar.holidays]); // eslint-disable-line react-hooks/exhaustive-deps
  const counts = useMemo(() => resultCounts(state), [entries, employees, dates]); // eslint-disable-line react-hooks/exhaustive-deps
  const menu = useMemo(() => menuCatalogue(state), [state.schedules.rows]); // eslint-disable-line react-hooks/exhaustive-deps

  // Per employee: how many days are fixed, worked, rest, and how many contradict their cell.
  const perEmployee = useMemo(() => {
    const problem = { scheduleInput: { dayOffCodes: state.scheduleInput.dayOffCodes } };
    const minutesOf = new Map(state.contracts.definitions.map((c) => [c.id, Number(c.workMinutesPerDay)]));
    const byId = new Map(employees.map((e) => [e.id, e]));
    const rows = new Map(employees.map((e) => [e.id, { id: e.id, name: e.name, fixed: 0, worked: 0, rest: 0, conflicts: 0 }]));
    for (const entry of entries) {
      const eid = entryEmployee(entry);
      const day = entryDay(entry);
      const emp = byId.get(eid);
      if (!emp || !day) continue;
      const a = analyseFixedDay(entry.ScheduleCode, {
        menu, cell: state.scheduleInput.dataMatrix?.[eid]?.[day] ?? '', problem,
        contractMinutes: minutesOf.get(activeContract(emp, day)) ?? null
      });
      const r = rows.get(eid);
      r.fixed += 1;
      if (a.schedule?.isSentinel) r.rest += 1;
      else r.worked += 1;
      if (a.reason || a.unknown) r.conflicts += 1;
    }
    return [...rows.values()];
  }, [entries, employees, menu, state.scheduleInput, state.contracts]);

  const totals = perEmployee.reduce((t, r) => ({
    worked: t.worked + r.worked, rest: t.rest + r.rest, conflicts: t.conflicts + r.conflicts
  }), { worked: 0, rest: 0, conflicts: 0 });

  const onSet = useCallback((eid, date, code) => transform((s) => setFixedDay(s, eid, date, code)), [transform]);

  const menuOff = !state.schedules.enabled;
  const noRoster = !state.metadata.rosterCode;
  const blocked = !employees.length || !dates.length || menuOff || noRoster;
  const resultFile = state.files.result;

  return (
    <StepLayout
      stepId="fixedDays"
      title="Fixed days"
      subtitle="Days already decided. Each becomes an entry in the result, and the solver only fills the days left open."
      actions={<Button variant="contained" startIcon={<EventAvailable />} onClick={() => setOpen(true)} disabled={blocked}>Open grid</Button>}
    >
      {!employees.length && <Alert severity="warning" sx={{ mb: 2 }}>Add employees first (step 4).</Alert>}
      {!dates.length && <Alert severity="warning" sx={{ mb: 2 }}>Set the horizon first (step 1).</Alert>}
      {menuOff && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={<Button color="inherit" size="small" onClick={() => goToStep(stepIndex('schedules'))}>Shift Menu</Button>}
        >
          A fixed day names a ScheduleCode, and the codes are defined by the shift menu, which is switched off.
          {entries.length > 0 && ` The ${entries.length} fixed day(s) are kept, but ${resultFile} is not written until the menu is back on.`}
        </Alert>
      )}
      {noRoster && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={<Button color="inherit" size="small" onClick={() => goToStep(stepIndex('setup'))}>Setup</Button>}
        >
          Set a roster code in Setup first: every fixed day carries it as its RosterCode.
        </Alert>
      )}

      <StepCard>
        <Typography variant="h6" fontWeight={600} gutterBottom>{resultFile}</Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Chip color="primary" label={`${counts.fixed} fixed`} />
          <Chip variant="outlined" label={`${counts.open} open`} />
          <Chip variant="outlined" label={`of ${counts.expected} employee-days`} />
          <Chip size="small" label={`${totals.worked} worked`} sx={{ bgcolor: FIXED_COLORS.worked }} />
          <Chip size="small" label={`${totals.rest} rest`} sx={{ bgcolor: FIXED_COLORS.rest }} />
          {totals.conflicts > 0 && <Chip size="small" color="error" label={`${totals.conflicts} contradict their cell`} />}
        </Box>
        <Alert severity="info">
          A result may be partial. Every entry is a fixed day, held as a hard rule to its schedule_input cell: a blank
          or unavailable cell must be a rest, <code>A</code> the contract&apos;s length, <code>8</code> exactly
          8 hours, and a window the shift&apos;s interval. The labour law (max consecutive work days, max work days in a
          week, min rest between shifts) is checked over the fixed days, where an open day breaks a run. A day with no
          entry is open.
        </Alert>
      </StepCard>

      {entries.length > 0 && (
        <StepCard>
          <Typography variant="h6" fontWeight={600} gutterBottom>By employee</Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Employee</TableCell>
                  <TableCell align="right">Fixed</TableCell>
                  <TableCell align="right">Worked</TableCell>
                  <TableCell align="right">Rest</TableCell>
                  <TableCell align="right">Contradict their cell</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {perEmployee.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell>
                      <strong>{r.id}</strong>
                      {r.name && r.name !== r.id && <Typography component="span" variant="caption" color="text.secondary"> · {r.name}</Typography>}
                    </TableCell>
                    <TableCell align="right">{r.fixed} / {dates.length}</TableCell>
                    <TableCell align="right">{r.worked}</TableCell>
                    <TableCell align="right">{r.rest}</TableCell>
                    <TableCell align="right">{r.conflicts > 0 ? <Chip size="small" color="error" label={r.conflicts} /> : 0}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </StepCard>
      )}

      {!blocked && (
        <FixedDaysMatrix
          open={open}
          onClose={() => setOpen(false)}
          state={state}
          dates={dates}
          openDays={openDays}
          holidays={holidays}
          counts={counts}
          onSet={onSet}
        />
      )}
    </StepLayout>
  );
};

export default Step8_FixedDays;

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, Alert, Button, Paper, Chip, Typography } from '@mui/material';
import { CalendarMonth } from '@mui/icons-material';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import DayOffCodesPanel, { KIND_COLORS } from '../components/scheduleInput/DayOffCodesPanel';
import ScheduleMatrixModal from '../components/calendar/ScheduleMatrixModal';
import ImportPreviewModal from '../components/shared/ImportPreviewModal';
import { CELL_COLORS } from '../components/calendar/MatrixCell';
import { OPERATOR_COLORS, parseOperatorCell } from '../components/calendar/TimeConstraintDialog';
import { useWizard } from '../context/WizardContext';
import { readScheduleInput } from '../v4/core';
import { scheduleInputCsv } from '../v4/generate';
import { fillMatrix, holidayDates, horizonOf, openDays as openDaysOf, resetMatrix, weeklyLoad } from '../v4/operations';
import { downloadText } from '../utils/download';

/**
 * Step 5: Schedule Input — the day-off palette and the per-employee,
 * per-day matrix that becomes schedule_input.csv.
 */
const Step5_ScheduleInput = () => {
  const { state, updateState, transform } = useWizard();
  const [open, setOpen] = useState(false);
  const [pendingImport, setPendingImport] = useState(null);

  const employees = state.employees.list;
  const dates = useMemo(() => horizonOf(state), [state.temporalScope]); // eslint-disable-line react-hooks/exhaustive-deps
  const open_ = useMemo(() => openDaysOf(state), [state.demand.periods, state.demand.shifts]); // eslint-disable-line react-hooks/exhaustive-deps
  const holidays = useMemo(() => holidayDates(state), [state.calendar.holidays]); // eslint-disable-line react-hooks/exhaustive-deps
  const load = useMemo(() => weeklyLoad(state), [state]);
  const matrix = state.scheduleInput.dataMatrix;

  // New employees and a changed horizon get their missing cells: A where a
  // contract covers the day, blank where none does.
  useEffect(() => {
    transform(fillMatrix);
  }, [employees.length, dates.length, transform]);

  const onCellChange = useCallback((employeeId, date, value) => {
    updateState('scheduleInput.dataMatrix', (m) => ({ ...m, [employeeId]: { ...(m?.[employeeId] || {}), [date]: value } }));
  }, [updateState]);

  const stats = useMemo(() => {
    const counts = { A: 0, hours: 0, blank: 0, windows: 0, codes: {} };
    for (const emp of employees) {
      for (const d of dates) {
        const v = matrix?.[emp.id]?.[d] ?? '';
        if (!v) counts.blank += 1;
        else if (v.toUpperCase() === 'A') counts.A += 1;
        else if (parseOperatorCell(v)) counts.windows += 1;
        else if (/^[\d.,-]+$/.test(v)) counts.hours += 1;
        else counts.codes[v] = (counts.codes[v] || 0) + 1;
      }
    }
    return counts;
  }, [employees, dates, matrix]);

  const exportCsv = () => downloadText(state.files.scheduleInput, scheduleInputCsv(employees, matrix, dates));

  const importCsv = async (file) => {
    const { cells, dates: cols, problems } = readScheduleInput(await file.text());
    const known = new Set(employees.map((e) => e.id));
    const inScope = new Set(dates);
    const warnings = [...problems];
    const unknown = [...cells.keys()].filter((id) => !known.has(id));
    if (unknown.length) warnings.push(`Rows for unknown employees are ignored: ${unknown.join(', ')}`);
    const outside = cols.filter((d) => !inScope.has(d));
    if (outside.length) warnings.push(`${outside.length} date column(s) outside the horizon are ignored`);
    const changes = [];
    for (const [eid, row] of cells) {
      if (!known.has(eid)) continue;
      for (const [d, v] of Object.entries(row)) {
        if (inScope.has(d) && (matrix?.[eid]?.[d] ?? '') !== v) changes.push({ employee: eid, date: d, from: matrix?.[eid]?.[d] ?? '', to: v });
      }
    }
    setPendingImport({ changes, warnings });
  };

  const confirmImport = () => {
    updateState('scheduleInput.dataMatrix', (m) => {
      const next = { ...m };
      for (const { employee, date, to } of pendingImport.changes) next[employee] = { ...(next[employee] || {}), [date]: to };
      return next;
    });
    setPendingImport(null);
  };

  const blocked = !employees.length || !dates.length;

  return (
    <StepLayout
      stepId="scheduleInput"
      title="Schedule input"
      subtitle="What each employee is asked to do each day. Numeric cells are HOURS (8 = 480 minutes); a blank cell means no assignment, not 'anything goes'."
      actions={<Button variant="contained" startIcon={<CalendarMonth />} onClick={() => setOpen(true)} disabled={blocked}>Open matrix</Button>}
    >
      <StepCard>
        <DayOffCodesPanel />
      </StepCard>

      <StepCard>
        {!employees.length && <Alert severity="warning">Add employees first (step 4).</Alert>}
        {!dates.length && <Alert severity="warning">Set the horizon first (step 1).</Alert>}
        {!blocked && (
          <>
            <Typography variant="h6" fontWeight={600} gutterBottom>Matrix</Typography>
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip size="small" label={`A: ${stats.A}`} sx={{ bgcolor: CELL_COLORS.auto }} />
                <Chip size="small" label={`hours: ${stats.hours}`} sx={{ bgcolor: CELL_COLORS.hours }} />
                <Chip size="small" label={`windows: ${stats.windows}`} sx={{ bgcolor: OPERATOR_COLORS.EQUALS }} />
                {Object.entries(stats.codes).map(([code, n]) => {
                  const entry = state.scheduleInput.dayOffCodes[code];
                  return <Chip key={code} size="small" label={`${code}: ${n}`} sx={{ bgcolor: entry ? KIND_COLORS[entry.kind] : undefined }} color={entry ? 'default' : 'error'} />;
                })}
                <Chip size="small" variant="outlined" label={`blank: ${stats.blank}`} />
              </Box>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                {employees.length} employees × {dates.length} days = {employees.length * dates.length} cells.
                {load.cap !== undefined && ` Labour law caps working days at ${load.cap} a week; the matrix shows each week's count.`}
              </Typography>
            </Paper>
            <Alert severity="info">
              SISQUAL&apos;s exporter only writes hours and day-off codes; the EQUALS / INCLUDE / WITHIN / EXCEPT
              windows remain authorable. Closed days (no demand) are marked in the matrix header and sit outside every week.
            </Alert>
          </>
        )}
      </StepCard>

      {!blocked && (
        <ScheduleMatrixModal
          open={open}
          onClose={() => setOpen(false)}
          state={state}
          dates={dates}
          openDays={open_}
          holidays={holidays}
          load={load}
          onCellChange={onCellChange}
          toolbar={{
            onImportCsv: importCsv,
            onExportCsv: exportCsv,
            onResetAuto: () => transform((s) => resetMatrix(s, 'A')),
            onClearBlank: () => transform((s) => resetMatrix(s, ''))
          }}
        />
      )}

      <ImportPreviewModal
        open={!!pendingImport}
        title="Import schedule_input.csv"
        summary={pendingImport ? `${pendingImport.changes.length} cell(s) will change.` : ''}
        warnings={pendingImport?.warnings || []}
        rows={(pendingImport?.changes || []).map((c) => ({ ...c, from: c.from || '(blank)', to: c.to || '(blank)' }))}
        columns={[{ field: 'employee', label: 'Employee' }, { field: 'date', label: 'Date' }, { field: 'from', label: 'Now' }, { field: 'to', label: 'Imported' }]}
        onConfirm={confirmImport}
        onCancel={() => setPendingImport(null)}
      />
    </StepLayout>
  );
};

export default Step5_ScheduleInput;

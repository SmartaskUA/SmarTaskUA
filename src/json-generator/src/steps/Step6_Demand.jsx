import React, { useMemo, useRef, useState } from 'react';
import {
  Box, Tabs, Tab, Alert, Button, ButtonGroup, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  RadioGroup, FormControlLabel, Radio, Typography, FormLabel
} from '@mui/material';
import { CalendarViewWeek, CalendarMonth, FileUpload, FileDownload, DeleteSweep, PlaylistAdd, PlayArrow } from '@mui/icons-material';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import WeeklyTemplateBuilder from '../components/demand/WeeklyTemplateBuilder';
import DemandCalendarGrid from '../components/demand/DemandCalendarGrid';
import DemandRowTable from '../components/demand/DemandRowTable';
import BulkAddRowsDialog from '../components/demand/BulkAddRowsDialog';
import { GRAIN_INFO } from '../components/demand/DemandRowDialog';
import ImportPreviewModal from '../components/shared/ImportPreviewModal';
import { ConfirmDialog } from '../components/shared/fields';
import { useWizard } from '../context/WizardContext';
import { readDemand, formatNumber } from '../v4/core';
import { daysCsv, periodsCsv, shiftsCsv } from '../v4/generate';
import { applyTemplate, horizonOf, templateRows } from '../v4/operations';
import { emptyWeeklyTemplate, newId, pairLabel } from '../v4/state';
import { downloadText } from '../utils/download';

const WRITERS = { periods: periodsCsv, days: daysCsv, shifts: shiftsCsv };

/** Import / export / clear for one grain. The grain is always passed, never sniffed from the header. */
function GrainToolbar({ grain, rows, fileName, onImport, onClear, extra }) {
  const fileRef = useRef(null);
  return (
    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center', mb: 2 }}>
      {extra}
      <ButtonGroup size="small" variant="outlined">
        <Button startIcon={<FileUpload />} onClick={() => fileRef.current?.click()}>Import {fileName}</Button>
        <Button startIcon={<FileDownload />} onClick={() => downloadText(fileName, WRITERS[grain](rows))}>Export</Button>
      </ButtonGroup>
      <Button size="small" color="error" startIcon={<DeleteSweep />} disabled={!rows.length} onClick={onClear}>Clear</Button>
      <Chip size="small" label={`${rows.length} row(s)`} />
      <input
        ref={fileRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (file) onImport(grain, await file.text(), file.name);
          e.target.value = '';
        }}
      />
    </Box>
  );
}

/**
 * Step 6: Demand — three CSVs at three grains. Periods (headcount per window)
 * carries the data in every bundle seen so far; days (workload minutes) and
 * shifts (headcount per shift type) are header-only unless you fill them.
 */
const Step6_Demand = () => {
  const { state, updateState, transform } = useWizard();
  const { demand, timeGrid, calendar, files } = state;
  const [tab, setTab] = useState(0);
  const [periodsView, setPeriodsView] = useState(0);
  const [applyOpen, setApplyOpen] = useState(false);
  const [applyOptions, setApplyOptions] = useState({ mode: 'replace', holidays: 'template' });
  const [pending, setPending] = useState(null);
  const [clearing, setClearing] = useState(null);
  const [bulk, setBulk] = useState(null);

  const dates = useMemo(() => horizonOf(state), [state.temporalScope]); // eslint-disable-line react-hooks/exhaustive-deps
  const holidays = useMemo(() => new Map((calendar.holidays || []).map((h) => [h.date, h])), [calendar.holidays]);
  const blockCount = Object.values(demand.weeklyTemplate || {}).reduce((n, b) => n + b.length, 0);
  const dims = demand.dimensions;
  const slot = timeGrid.slotMinutes;
  const dateMin = dates[0];
  const dateMax = dates[dates.length - 1];

  const setRows = (grain) => (rows) => updateState(`demand.${grain}`, rows);

  const importGrain = (grain, text, fileName) => {
    const { rows, problems } = readDemand(text, grain);
    setPending({
      grain,
      fileName,
      warnings: problems,
      rows: rows.map((r) => ({
        id: newId(grain), date: r.date, tableName: r.tableName, tableValue: r.tableValue,
        minimum: r.minimum, ideal: r.ideal, estimated: r.estimated,
        start: (r.raw.start || '').trim(), end: (r.raw.end || '').trim(),
        ...(grain === 'shifts' && { workPeriod: r.workPeriod })
      }))
    });
  };

  const preview = useMemo(() => (applyOpen ? templateRows(state, {
    holidays: applyOptions.holidays,
    dates: applyOptions.mode === 'fill' ? dates.filter((d) => !demand.periods.some((r) => r.date === d)) : dates
  }).length : 0), [applyOpen, applyOptions, state, dates, demand.periods]);

  return (
    <StepLayout
      stepId="demand"
      title="Demand"
      subtitle="Coverage wanted per (tableName, tableValue) coordinate. A missing row means that coordinate is not operating in that window."
    >
      <StepCard>
        {!dims.length && <Alert severity="warning" sx={{ mb: 2 }}>Declare dimensions first (step 3).</Alert>}
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tab label={`Periods — headcount (${demand.periods.length})`} />
          <Tab label={`Days — workload minutes (${demand.days.length})`} />
          <Tab label={`Shifts — headcount by type (${demand.shifts.length})`} />
        </Tabs>

        {tab === 0 && (
          <Box>
            <GrainToolbar
              grain="periods"
              rows={demand.periods}
              fileName={files.periods}
              onImport={importGrain}
              onClear={() => setClearing('periods')}
              extra={(
                <Button variant="contained" size="small" startIcon={<PlayArrow />} disabled={!blockCount || !dates.length} onClick={() => setApplyOpen(true)}>
                  Apply weekly template ({blockCount} blocks)
                </Button>
              )}
            />
            <Tabs value={periodsView} onChange={(_, v) => setPeriodsView(v)} sx={{ mb: 1 }}>
              <Tab icon={<CalendarViewWeek />} iconPosition="start" label="Weekly template" />
              <Tab icon={<CalendarMonth />} iconPosition="start" label="Calendar" />
            </Tabs>
            {periodsView === 0 && (
              <WeeklyTemplateBuilder
                template={demand.weeklyTemplate || emptyWeeklyTemplate()}
                dimensions={dims}
                slotMinutes={slot}
                weekStart={calendar.weekStart}
                onChange={(t) => updateState('demand.weeklyTemplate', t)}
              />
            )}
            {periodsView === 1 && (dates.length ? (
              <DemandCalendarGrid
                dates={dates}
                rows={demand.periods}
                dimensions={dims}
                slotMinutes={slot}
                weekStart={calendar.weekStart}
                holidays={holidays}
                onChange={setRows('periods')}
              />
            ) : <Alert severity="warning">Set the horizon first (step 1).</Alert>)}
          </Box>
        )}

        {tab > 0 && (() => {
          const grain = tab === 1 ? 'days' : 'shifts';
          return (
            <Box>
              {grain === 'days' ? (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  <strong>Minutes of work, not people.</strong> This file has a header byte-identical to periods but a
                  different unit — only the JSON key says which is which. Nothing consumes it yet (FUTURE.md §4), and
                  every SISQUAL bundle ships it header-only.
                </Alert>
              ) : (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Headcount per shift type. <code>workPeriod</code> is SISQUAL&apos;s ShiftTypeCode (M/T/N per their
                  docs, never seen in data — agenda item 3), not a named work period. Every SISQUAL bundle ships it header-only.
                </Alert>
              )}
              <GrainToolbar
                grain={grain}
                rows={demand[grain]}
                fileName={files[grain]}
                onImport={importGrain}
                onClear={() => setClearing(grain)}
                extra={(
                  <Button size="small" variant="outlined" startIcon={<PlaylistAdd />} disabled={!dims.length || !dates.length} onClick={() => setBulk(grain)}>
                    Bulk add
                  </Button>
                )}
              />
              <DemandRowTable
                grain={grain}
                rows={demand[grain]}
                dimensions={dims}
                slotMinutes={slot}
                dateMin={dateMin}
                dateMax={dateMax}
                onChange={setRows(grain)}
              />
            </Box>
          );
        })()}
      </StepCard>

      <Dialog open={applyOpen} onClose={() => setApplyOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Apply the weekly template</DialogTitle>
        <DialogContent>
          <FormLabel>Periods rows already there</FormLabel>
          <RadioGroup value={applyOptions.mode} onChange={(e) => setApplyOptions({ ...applyOptions, mode: e.target.value })}>
            <FormControlLabel value="replace" control={<Radio />} label={`Replace all ${demand.periods.length} rows`} />
            <FormControlLabel value="fill" control={<Radio />} label="Keep them; only fill dates that have none" />
          </RadioGroup>
          {(calendar.holidays || []).length > 0 && (
            <>
              <FormLabel sx={{ mt: 1, display: 'block' }}>Holidays ({calendar.holidays.length})</FormLabel>
              <RadioGroup value={applyOptions.holidays} onChange={(e) => setApplyOptions({ ...applyOptions, holidays: e.target.value })}>
                <FormControlLabel value="template" control={<Radio />} label="Use their weekday's template" />
                <FormControlLabel value="skip" control={<Radio />} label="Leave them empty to edit by hand (their own demand)" />
              </RadioGroup>
            </>
          )}
          <Typography variant="body2" sx={{ mt: 1 }}>{preview} row(s) will be generated.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApplyOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={() => { transform((s) => applyTemplate(s, applyOptions)); setApplyOpen(false); setPeriodsView(1); }}>
            Apply
          </Button>
        </DialogActions>
      </Dialog>

      <ImportPreviewModal
        open={!!pending}
        title={pending ? `Import ${pending.fileName} as the ${pending.grain} grain` : ''}
        summary={pending ? `${pending.rows.length} row(s) read as ${GRAIN_INFO[pending.grain].unit}. They replace the ${demand[pending.grain].length} current ${pending.grain} row(s).` : ''}
        warnings={pending?.warnings || []}
        rows={(pending?.rows || []).map((r) => ({
          date: r.date, dim: pairLabel(r.tableName, r.tableValue), window: r.start ? `${r.start}-${r.end}` : '',
          minimum: formatNumber(r.minimum), workPeriod: r.workPeriod || ''
        }))}
        columns={[
          { field: 'date', label: 'Date' }, ...(pending?.grain === 'shifts' ? [{ field: 'workPeriod', label: 'workPeriod' }] : []),
          { field: 'dim', label: 'Dimension' }, { field: 'window', label: 'Window' }, { field: 'minimum', label: 'minimum' }
        ]}
        onConfirm={() => { updateState(`demand.${pending.grain}`, pending.rows); setPending(null); }}
        onCancel={() => setPending(null)}
      />

      <ConfirmDialog
        open={!!clearing}
        title={`Clear every ${clearing} row?`}
        confirmLabel="Clear"
        confirmColor="error"
        onCancel={() => setClearing(null)}
        onConfirm={() => { updateState(`demand.${clearing}`, []); setClearing(null); }}
      >
        {clearing === 'periods' ? 'With no windowed row, every day is closed and nothing needs staffing.' : 'The file will be written header-only.'}
      </ConfirmDialog>

      {bulk && (
        <BulkAddRowsDialog
          open
          grain={bulk}
          dimensions={dims}
          slotMinutes={slot}
          dateMin={dateMin}
          dateMax={dateMax}
          onAdd={(rows) => { updateState(`demand.${bulk}`, (current) => [...current, ...rows]); setBulk(null); }}
          onClose={() => setBulk(null)}
        />
      )}
    </StepLayout>
  );
};

export default Step6_Demand;

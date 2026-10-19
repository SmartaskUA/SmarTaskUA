import React, { useMemo, useState } from 'react';
import {
  Box, Paper, Typography, Chip, Dialog, DialogTitle, DialogContent, DialogActions, Button, Tooltip
} from '@mui/material';
import DemandRowTable from './DemandRowTable';
import { weekIndex, weekday, tryParseRange, formatNumber } from '../../v4/core';
import { pairLabel } from '../../v4/state';
import { getTeamColor } from '../../utils/helpers/colorHelpers';

const DAY = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/**
 * The most workers a dimension asks for at any one moment on a date. Summing
 * minimums across windows would be meaningless: windows follow each other.
 */
function peaks(rows) {
  const byDim = new Map();
  for (const r of rows) {
    const w = tryParseRange(r.start, r.end);
    if (!w) continue;
    const label = pairLabel(r.tableName, r.tableValue);
    if (!byDim.has(label)) byDim.set(label, []);
    byDim.get(label).push({ start: w[0], end: w[1], n: Number(r.minimum) || 0 });
  }
  return [...byDim.entries()].map(([label, spans]) => {
    let peak = 0;
    for (const s of spans) {
      const concurrent = spans.filter((o) => o.start < s.start + 1 && o.end > s.start).reduce((t, o) => t + o.n, 0);
      peak = Math.max(peak, concurrent);
    }
    return { label, peak, count: spans.length };
  });
}

/**
 * Phase 2 of demand: the periods rows date by date. A date with no windowed
 * row is closed — it sits outside every week.
 */
const DemandCalendarGrid = ({ dates, rows, dimensions, slotMinutes, weekStart, holidays, onChange }) => {
  const [selected, setSelected] = useState(null);
  const byDate = useMemo(() => {
    const out = new Map();
    for (const r of rows) {
      if (!out.has(r.date)) out.set(r.date, []);
      out.get(r.date).push(r);
    }
    return out;
  }, [rows]);

  const weeks = useMemo(() => {
    const out = new Map();
    for (const d of dates) {
      const wk = weekIndex(d, dates[0], weekStart);
      if (!out.has(wk)) out.set(wk, []);
      out.get(wk).push(d);
    }
    return [...out.entries()];
  }, [dates, weekStart]);

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Click a day to edit its rows. Numbers are the peak concurrent minimum per dimension.
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {weeks.map(([wk, days]) => (
          <Paper key={wk} variant="outlined" sx={{ p: 1 }}>
            <Typography variant="caption" color="text.secondary">Week {wk}</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: 1 }}>
              {days.map((d) => {
                const dayRows = byDate.get(d) || [];
                const closed = !dayRows.some((r) => r.start || r.end);
                const holiday = holidays.get(d);
                return (
                  <Paper
                    key={d}
                    role="button"
                    tabIndex={0}
                    aria-label={`Edit ${d}`}
                    onClick={() => setSelected(d)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(d); } }}
                    variant="outlined"
                    sx={{
                      p: 1, cursor: 'pointer', minHeight: 96, bgcolor: closed ? '#fafafa' : 'background.paper',
                      borderColor: holiday ? 'secondary.main' : 'divider', '&:hover': { boxShadow: 2 }
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="caption" fontWeight={700}>{DAY[weekday(d)]} {d.slice(8)}/{d.slice(5, 7)}</Typography>
                      <Typography variant="caption" color="text.secondary">{dayRows.length || ''}</Typography>
                    </Box>
                    {holiday && (
                      <Tooltip title={holiday.name || holiday.code || 'Holiday'}>
                        <Chip size="small" color="secondary" label="holiday" sx={{ height: 16, fontSize: 10, mb: 0.5 }} />
                      </Tooltip>
                    )}
                    {closed ? (
                      <Typography variant="caption" color="text.disabled" display="block">closed</Typography>
                    ) : peaks(dayRows).map((p) => (
                      <Box key={p.label} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: getTeamColor(p.label), flexShrink: 0 }} />
                        <Typography variant="caption" noWrap>{p.label} {formatNumber(p.peak)}</Typography>
                      </Box>
                    ))}
                  </Paper>
                );
              })}
            </Box>
          </Paper>
        ))}
      </Box>

      <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth="md" fullWidth>
        <DialogTitle>
          {selected} {selected && `(${DAY[weekday(selected)]})`}
          {selected && holidays.get(selected) && <Chip size="small" color="secondary" label={holidays.get(selected).name || 'holiday'} sx={{ ml: 1 }} />}
        </DialogTitle>
        <DialogContent dividers>
          {selected && (
            <DemandRowTable
              grain="periods"
              rows={rows}
              dimensions={dimensions}
              slotMinutes={slotMinutes}
              fixedDate={selected}
              dense
              onChange={onChange}
            />
          )}
        </DialogContent>
        <DialogActions><Button onClick={() => setSelected(null)} variant="contained">Close</Button></DialogActions>
      </Dialog>
    </Box>
  );
};

export default DemandCalendarGrid;

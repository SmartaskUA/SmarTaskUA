import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Box, Typography, Paper, Tooltip, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, Button,
  FormGroup, FormControlLabel, Checkbox
} from '@mui/material';
import { Add, ContentCopy } from '@mui/icons-material';
import TimeAxis, { DAY_HEIGHT, HEADER_HEIGHT, PX_PER_MINUTE } from './TimeAxis';
import DemandBlock from './DemandBlock';
import DemandBlockDialog from './DemandBlockDialog';
import { WEEKDAYS } from '../../v4/constants';
import { pairKey, tryParseRange } from '../../v4/core';
import { newId, pairLabel } from '../../v4/state';
import { overlappingRows } from '../../v4/operations';
import { getTeamColor } from '../../utils/helpers/colorHelpers';

const capital = (s) => s.charAt(0).toUpperCase() + s.slice(1);

/** The week's days in calendar order, starting on `weekStart`. */
function orderedDays(weekStart) {
  const i = Math.max(0, WEEKDAYS.indexOf(weekStart));
  return [...WEEKDAYS.slice(i), ...WEEKDAYS.slice(0, i)];
}

const previousDay = (day) => WEEKDAYS[(WEEKDAYS.indexOf(day) + 6) % 7];

/**
 * Phase 1 of demand: a weekly pattern of windows per dimension. Each day column
 * is split into one lane per dimension, because Team and Responsibility rows
 * overlap in time by design and must stay visible side by side.
 */
const WeeklyTemplateBuilder = ({ template, dimensions, slotMinutes, weekStart, onChange }) => {
  const [dialog, setDialog] = useState(null); // {day, block}
  const [copyFrom, setCopyFrom] = useState(null);
  const [copyTo, setCopyTo] = useState([]);
  const days = orderedDays(weekStart);
  const scroller = useRef(null);

  // Open on the working day, not on midnight: an hour before the earliest
  // block, or 08:00 when the template is empty. Only on mount.
  useEffect(() => {
    const starts = Object.values(template || {}).flat()
      .map((b) => tryParseRange(b.start, b.end)?.[0]).filter((m) => m !== undefined);
    const first = starts.length ? Math.min(...starts) : 9 * 60;
    if (scroller.current) scroller.current.scrollTop = Math.max(0, (first - 60) * PX_PER_MINUTE);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const order = useMemo(() => new Map(dimensions.map((d, i) => [pairKey(d.tableName, d.tableValue), i])), [dimensions]);

  const emptyBlock = (day) => {
    const blocks = template[day] || [];
    const last = blocks[blocks.length - 1];
    const d = last || dimensions[0];
    return { id: '', tableName: d?.tableName || '', tableValue: d?.tableValue || '', start: last?.end || '09:00', end: '', minimum: 1, ideal: 0, estimated: 0 };
  };

  const save = (saved, next) => {
    const { day } = dialog;
    const blocks = template[day] || [];
    const exists = blocks.some((b) => b.id === saved.id);
    onChange({ ...template, [day]: exists ? blocks.map((b) => (b.id === saved.id ? saved : b)) : [...blocks, saved] });
    setDialog(next ? { day, block: next } : null);
  };

  const remove = (block) => {
    const { day } = dialog;
    onChange({ ...template, [day]: (template[day] || []).filter((b) => b.id !== block.id) });
    setDialog(null);
  };

  const copy = () => {
    const source = template[copyFrom] || [];
    const next = { ...template };
    for (const d of copyTo) next[d] = source.map((b) => ({ ...b, id: newId('block') }));
    onChange(next);
    setCopyFrom(null);
  };

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Click a column (or +) to add a window. Each dimension gets its own lane; a block crossing midnight continues
        on the next day&apos;s column. Blocks show the minimum headcount — an asterisk means ideal or estimated is set.
      </Typography>
      <Paper ref={scroller} variant="outlined" sx={{ height: 'calc(100vh - 470px)', minHeight: 420, overflow: 'auto' }}>
        <Box sx={{ display: 'flex', minWidth: 56 + 7 * 150 }}>
          <TimeAxis />
          {days.map((day) => {
            const blocks = template[day] || [];
            const carried = (template[previousDay(day)] || []).filter((b) => (tryParseRange(b.start, b.end)?.[1] ?? 0) > 1440);
            const lanes = [...new Set([...blocks, ...carried].map((b) => pairKey(b.tableName, b.tableValue)))]
              .sort((a, b) => (order.get(a) ?? 99) - (order.get(b) ?? 99));
            if (!lanes.length) lanes.push('');
            const flagged = new Set(overlappingRows(blocks.map((b) => ({ ...b, date: day }))).flatMap(({ a, b }) => [a.id, b.id]));
            return (
              <Box key={day} sx={{ flex: 1, minWidth: 150, borderRight: '1px solid', borderColor: 'divider' }}>
                <Box sx={{
                  height: HEADER_HEIGHT, position: 'sticky', top: 0, zIndex: 5, bgcolor: 'primary.main', color: '#fff',
                  px: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between'
                }}
                >
                  <Typography variant="subtitle2" fontWeight={700}>{capital(day).slice(0, 3)} {blocks.length ? `(${blocks.length})` : ''}</Typography>
                  <Box>
                    <Tooltip title="Copy this day to…">
                      <span>
                        <IconButton size="small" sx={{ color: '#fff' }} disabled={!blocks.length} onClick={() => { setCopyFrom(day); setCopyTo([]); }}>
                          <ContentCopy sx={{ fontSize: 16 }} />
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title="Add a window">
                      <IconButton size="small" sx={{ color: '#fff' }} disabled={!dimensions.length} onClick={() => setDialog({ day, block: emptyBlock(day) })}>
                        <Add sx={{ fontSize: 18 }} />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
                <Box
                  sx={{ position: 'relative', height: DAY_HEIGHT, display: 'flex', cursor: dimensions.length ? 'copy' : 'default' }}
                  onClick={() => dimensions.length && setDialog({ day, block: emptyBlock(day) })}
                >
                  {Array.from({ length: Math.floor(1440 / slotMinutes) }, (_, i) => {
                    const minute = i * slotMinutes;
                    if (slotMinutes < 15 && minute % 60) return null;
                    return (
                      <Box key={i} sx={{
                        position: 'absolute', left: 0, right: 0, top: minute * PX_PER_MINUTE,
                        borderTop: minute % 60 ? '1px dashed rgba(0,0,0,0.06)' : '1px solid rgba(0,0,0,0.12)'
                      }}
                      />
                    );
                  })}
                  {lanes.map((lane) => (
                    <Box key={lane || 'empty'} sx={{ position: 'relative', flex: 1, borderRight: lanes.length > 1 ? '1px dotted rgba(0,0,0,0.1)' : 'none' }}>
                      {blocks.filter((b) => pairKey(b.tableName, b.tableValue) === lane).map((b) => (
                        <DemandBlock key={b.id} block={b} overlapping={flagged.has(b.id)} onEdit={(block) => setDialog({ day, block })} />
                      ))}
                      {carried.filter((b) => pairKey(b.tableName, b.tableValue) === lane).map((b) => (
                        <DemandBlock key={`carry-${b.id}`} block={b} continuation onEdit={(block) => setDialog({ day: previousDay(day), block })} />
                      ))}
                    </Box>
                  ))}
                </Box>
              </Box>
            );
          })}
        </Box>
      </Paper>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
        {dimensions.map((d) => (
          <Typography key={pairKey(d.tableName, d.tableValue)} variant="caption" sx={{ px: 1, borderRadius: 1, color: '#fff', bgcolor: getTeamColor(pairLabel(d.tableName, d.tableValue)) }}>
            {pairLabel(d.tableName, d.tableValue)}
          </Typography>
        ))}
      </Box>

      {dialog && (
        <DemandBlockDialog
          open
          block={dialog.block}
          day={dialog.day}
          dimensions={dimensions}
          slotMinutes={slotMinutes}
          siblings={template[dialog.day] || []}
          onSave={save}
          onDelete={remove}
          onClose={() => setDialog(null)}
        />
      )}

      <Dialog open={!!copyFrom} onClose={() => setCopyFrom(null)}>
        <DialogTitle>Copy {copyFrom && capital(copyFrom)} to…</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">The chosen days&apos; blocks are replaced.</Typography>
          <FormGroup>
            {WEEKDAYS.filter((d) => d !== copyFrom).map((d) => (
              <FormControlLabel key={d} label={capital(d)} control={(
                <Checkbox checked={copyTo.includes(d)} onChange={(e) => setCopyTo(e.target.checked ? [...copyTo, d] : copyTo.filter((x) => x !== d))} />
              )}
              />
            ))}
          </FormGroup>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCopyFrom(null)}>Cancel</Button>
          <Button variant="contained" disabled={!copyTo.length} onClick={copy}>Copy</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WeeklyTemplateBuilder;

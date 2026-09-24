import React, { useMemo, useState } from 'react';
import {
  Box, Table, TableHead, TableRow, TableCell, TableBody, TableContainer, Paper, IconButton, Chip, Tooltip,
  TablePagination, TextField, MenuItem, Button, Typography
} from '@mui/material';
import { Edit, Delete, Add, Warning } from '@mui/icons-material';
import DemandRowDialog, { GRAIN_INFO } from './DemandRowDialog';
import { DateField } from '../shared/fields';
import { formatNumber, pairKey, tryParseRange } from '../../v4/core';
import { newId, pairLabel } from '../../v4/state';
import { overlappingRows } from '../../v4/operations';
import { getTeamColor } from '../../utils/helpers/colorHelpers';

const fmt = (v) => (typeof v === 'number' ? formatNumber(v) : v === '' || v === undefined ? '0' : String(v));

/**
 * Rows of one demand grain, editable one at a time. With `fixedDate` it shows
 * a single day (the calendar's day detail); otherwise it pages through them all.
 */
const DemandRowTable = ({
  grain, rows, dimensions, slotMinutes, dateMin, dateMax, fixedDate, onChange, dense = false
}) => {
  const info = GRAIN_INFO[grain];
  const [editing, setEditing] = useState(null);
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(25);
  const [dateFilter, setDateFilter] = useState('');
  const [dimFilter, setDimFilter] = useState('');

  const flagged = useMemo(() => {
    const out = new Set();
    for (const { a, b } of overlappingRows(rows)) { out.add(a.id); out.add(b.id); }
    return out;
  }, [rows]);

  const shown = useMemo(() => rows.filter((r) =>
    (fixedDate ? r.date === fixedDate : !dateFilter || r.date === dateFilter) &&
    (!dimFilter || pairKey(r.tableName, r.tableValue) === dimFilter)), [rows, fixedDate, dateFilter, dimFilter]);
  const paged = fixedDate ? shown : shown.slice(page * perPage, page * perPage + perPage);

  const blank = () => {
    const last = shown[shown.length - 1];
    const d = dimensions[0];
    return {
      id: '',
      date: fixedDate || dateFilter || dateMin || '',
      tableName: last?.tableName || d?.tableName || '',
      tableValue: last?.tableValue || d?.tableValue || '',
      minimum: 1,
      ideal: 0,
      estimated: 0,
      ...(info.windowed && { start: last?.end || '09:00', end: '' }),
      ...(grain === 'shifts' && { workPeriod: last?.workPeriod || 'M' })
    };
  };

  const save = (row) => {
    if (row.id) onChange(rows.map((r) => (r.id === row.id ? row : r)));
    else onChange([...rows, { ...row, id: newId(grain) }]);
    setEditing(null);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1, flexWrap: 'wrap' }}>
        {!fixedDate && (
          <DateField label="Date" value={dateFilter} min={dateMin} max={dateMax} onChange={(v) => { setDateFilter(v); setPage(0); }} />
        )}
        <TextField select size="small" label="Dimension" value={dimFilter} onChange={(e) => { setDimFilter(e.target.value); setPage(0); }} sx={{ minWidth: 180 }}>
          <MenuItem value="">All</MenuItem>
          {dimensions.map((d) => <MenuItem key={pairKey(d.tableName, d.tableValue)} value={pairKey(d.tableName, d.tableValue)}>{pairLabel(d.tableName, d.tableValue)}</MenuItem>)}
        </TextField>
        <Box sx={{ flexGrow: 1 }} />
        <Button size="small" variant="outlined" startIcon={<Add />} onClick={() => setEditing(blank())} disabled={!dimensions.length}>Add row</Button>
      </Box>

      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: dense ? 360 : 520 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {!fixedDate && <TableCell>Date</TableCell>}
              {grain === 'shifts' && <TableCell>workPeriod</TableCell>}
              <TableCell>Dimension</TableCell>
              {info.windowed && <TableCell>Window</TableCell>}
              <TableCell align="right">minimum{grain === 'days' ? ' (min)' : ''}</TableCell>
              <TableCell align="right">ideal</TableCell>
              <TableCell align="right">estimated</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {paged.map((r) => {
              const w = tryParseRange(r.start, r.end);
              return (
                <TableRow key={r.id} hover>
                  {!fixedDate && <TableCell sx={{ whiteSpace: 'nowrap' }}>{r.date}</TableCell>}
                  {grain === 'shifts' && <TableCell>{r.workPeriod}</TableCell>}
                  <TableCell>
                    <Chip size="small" label={pairLabel(r.tableName, r.tableValue)} sx={{ bgcolor: getTeamColor(pairLabel(r.tableName, r.tableValue)), color: '#fff' }} />
                  </TableCell>
                  {info.windowed && (
                    <TableCell sx={{ whiteSpace: 'nowrap', fontFamily: 'monospace' }}>
                      {r.start || '—'}–{r.end || '—'}
                      {w && w[1] > 1440 && <Chip size="small" label="+1 day" sx={{ ml: 0.5, height: 18 }} />}
                      {flagged.has(r.id) && (
                        <Tooltip title="Overlaps another window of this dimension on this date: a worker in the overlap counts toward both">
                          <Warning color="warning" sx={{ fontSize: 16, ml: 0.5, verticalAlign: 'middle' }} />
                        </Tooltip>
                      )}
                    </TableCell>
                  )}
                  <TableCell align="right" sx={{ fontWeight: 600 }}>{fmt(r.minimum)}</TableCell>
                  <TableCell align="right">{fmt(r.ideal)}</TableCell>
                  <TableCell align="right">{fmt(r.estimated)}</TableCell>
                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                    <IconButton size="small" onClick={() => setEditing(r)}><Edit fontSize="small" /></IconButton>
                    <IconButton size="small" color="error" onClick={() => onChange(rows.filter((x) => x.id !== r.id))}><Delete fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              );
            })}
            {!paged.length && (
              <TableRow>
                <TableCell colSpan={8}>
                  <Typography variant="body2" color="text.secondary" sx={{ py: 1, textAlign: 'center' }}>
                    {fixedDate ? 'No rows: this dimension set is not operating on this date.' : 'No rows.'}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      {!fixedDate && shown.length > perPage && (
        <TablePagination
          component="div"
          count={shown.length}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={perPage}
          onRowsPerPageChange={(e) => { setPerPage(Number(e.target.value)); setPage(0); }}
          rowsPerPageOptions={[25, 50, 100]}
        />
      )}

      {editing && (
        <DemandRowDialog
          open
          grain={grain}
          row={editing}
          dimensions={dimensions}
          slotMinutes={slotMinutes}
          dateMin={dateMin}
          dateMax={dateMax}
          fixedDate={fixedDate}
          siblings={rows}
          onSave={save}
          onClose={() => setEditing(null)}
        />
      )}
    </Box>
  );
};

export default DemandRowTable;

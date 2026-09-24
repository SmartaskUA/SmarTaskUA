import React, { memo, useState } from 'react';
import { Select, MenuItem, TextField, Box, Typography, IconButton, Tooltip, ListSubheader } from '@mui/material';
import { Edit as EditIcon, Close as CloseIcon, ArrowDropDown } from '@mui/icons-material';
import TimeConstraintDialog, { OPERATOR_COLORS, parseOperatorCell } from './TimeConstraintDialog';
import { KIND_COLORS } from '../scheduleInput/DayOffCodesPanel';

export const CELL_COLORS = {
  auto: '#e8f5e9',
  hours: '#e3f2fd',
  blank: '#ffffff',
  uncovered: '#eeeeee'
};

const BLANK = '__blank__';
const HOURS = '__hours__';
const WINDOW = '__window__';

function background(value, analysis, dayOffCodes, covered) {
  if (parseOperatorCell(value)) return OPERATOR_COLORS[parseOperatorCell(value).type];
  if (!value) return covered ? CELL_COLORS.blank : CELL_COLORS.uncovered;
  if (String(value).toUpperCase() === 'A') return CELL_COLORS.auto;
  if (dayOffCodes[value]) return KIND_COLORS[dayOffCodes[value].kind];
  if (analysis.kind === 'exact_hours' || analysis.kind === 'pending') return CELL_COLORS.hours;
  return CELL_COLORS.blank;
}

/**
 * One schedule-input cell: A, hours, a declared day-off code, a time window,
 * or blank (no assignment). `analysis` comes from operations.analyseCell.
 */
const MatrixCell = ({ employeeId, date, value = '', analysis, dayOffCodes, covered, slotMinutes, onCellChange }) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const onChange = (v) => onCellChange(employeeId, date, v);
  const text = String(value ?? '');
  const bg = background(text, analysis, dayOffCodes, covered);
  const border = analysis.error ? '2px solid #d32f2f' : analysis.warning ? '2px solid #ed6c02' : '1px solid #e0e0e0';
  const tip = analysis.error || analysis.warning || (!covered ? 'No contract covers this day' : '');
  const operator = parseOperatorCell(text);
  const isHours = analysis.kind === 'exact_hours' || analysis.kind === 'pending' || /^[\d.,]+$/.test(text);

  let body;
  if (operator) {
    body = (
      <Box sx={{ height: '100%', minHeight: 40, px: 0.75, bgcolor: bg, border, display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxSizing: 'border-box' }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ fontSize: '0.6rem', fontWeight: 700, color: 'text.secondary' }}>{operator.type}</Typography>
          <Typography sx={{ fontSize: '0.65rem', fontFamily: 'monospace', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {operator.ranges.map((r) => `${r.start}–${r.end}`).join(', ')}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
          <IconButton size="small" sx={{ p: 0.25 }} onClick={() => setDialogOpen(true)}><EditIcon sx={{ fontSize: 14 }} /></IconButton>
          <IconButton size="small" sx={{ p: 0.25 }} onClick={() => onChange(covered ? 'A' : '')}><CloseIcon sx={{ fontSize: 14 }} /></IconButton>
        </Box>
      </Box>
    );
  } else if (isHours) {
    body = (
      <TextField
        size="small"
        value={text === '-' ? '' : text}
        placeholder="hours"
        onChange={(e) => {
          const v = e.target.value;
          if (v === '' || /^\d*[.,]?\d*$/.test(v)) onChange(v || '-');
        }}
        onKeyDown={(e) => { if (e.key === 'Escape') onChange(covered ? 'A' : ''); }}
        inputProps={{ size: 3, step: slotMinutes / 60, style: { textAlign: 'center', fontSize: 13, fontWeight: 600, padding: '9px 4px', minWidth: 0 } }}
        InputProps={{
          endAdornment: (
            <IconButton size="small" sx={{ p: 0.25 }} onClick={() => onChange(covered ? 'A' : '')}>
              <ArrowDropDown sx={{ fontSize: 16 }} />
            </IconButton>
          )
        }}
        sx={{
          width: '100%',
          minWidth: 0,
          '& .MuiInputBase-root': { bgcolor: bg, borderRadius: 0, pr: 0 },
          '& fieldset': { border, borderRadius: 0 }
        }}
      />
    );
  } else {
    const undeclared = text && text.toUpperCase() !== 'A' && !dayOffCodes[text];
    const selectValue = !text ? BLANK : (text.toUpperCase() === 'A' ? 'A' : text);
    body = (
      <Select
        size="small"
        value={selectValue}
        onChange={(e) => {
          const v = e.target.value;
          if (v === HOURS) onChange('-');
          else if (v === WINDOW) setDialogOpen(true);
          else onChange(v === BLANK ? '' : v);
        }}
        renderValue={(v) => (v === BLANK ? '·' : v)}
        sx={{
          width: '100%',
          minHeight: 40,
          bgcolor: bg,
          borderRadius: 0,
          '& .MuiSelect-select': { py: 1, px: 1, fontSize: 13, fontWeight: 600, textAlign: 'center' },
          '& fieldset': { border, borderRadius: 0 }
        }}
      >
        <MenuItem value="A">A — work the contract length</MenuItem>
        <MenuItem value={HOURS}>Hours…</MenuItem>
        <MenuItem value={WINDOW}>Time window…</MenuItem>
        <MenuItem value={BLANK}>Blank — no assignment</MenuItem>
        <ListSubheader>Day-off codes</ListSubheader>
        {Object.entries(dayOffCodes).map(([code, entry]) => (
          <MenuItem key={code} value={code} sx={{ bgcolor: KIND_COLORS[entry.kind] }}>
            {code}{entry.name ? ` — ${entry.name}` : ''} ({entry.kind})
          </MenuItem>
        ))}
        {undeclared && <MenuItem value={text} sx={{ color: 'error.main' }}>{text} (not declared)</MenuItem>}
      </Select>
    );
  }

  return (
    <>
      {tip ? <Tooltip title={tip} placement="top"><Box>{body}</Box></Tooltip> : body}
      <TimeConstraintDialog
        open={dialogOpen}
        value={operator ? text : ''}
        slotMinutes={slotMinutes}
        onSave={onChange}
        onClose={() => setDialogOpen(false)}
      />
    </>
  );
};

export default memo(MatrixCell, (a, b) => a.value === b.value && a.covered === b.covered &&
  a.analysis.error === b.analysis.error && a.analysis.warning === b.analysis.warning &&
  a.dayOffCodes === b.dayOffCodes && a.slotMinutes === b.slotMinutes && a.onCellChange === b.onCellChange);

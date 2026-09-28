import React, { useCallback, useMemo, useState } from 'react';
import {
  Dialog, AppBar, Toolbar, IconButton, Typography, Box, Chip, Tooltip, Paper, Menu, MenuItem, ListItemText,
  ListSubheader, Table, TableBody, TableCell, TableContainer, TableHead, TableRow
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { Close as CloseIcon } from '@mui/icons-material';
import FixedDayCell, { FIXED_COLORS, cellCaption } from './FixedDayCell';
import { activeContract, intervalToString, weekday } from '../../v4/core';
import { analyseFixedDay, fixedIndex, menuCatalogue } from '../../v4/operations';

const DAY = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const HeaderCell = styled(TableCell)(({ theme }) => ({
  position: 'sticky',
  top: 0,
  zIndex: 3,
  backgroundColor: theme.palette.background.paper,
  borderBottom: `2px solid ${theme.palette.divider}`,
  borderRight: `1px solid ${theme.palette.divider}`,
  padding: '6px',
  minWidth: 96,
  textAlign: 'center',
  fontWeight: 600,
  fontSize: 12
}));

const FirstCell = styled(TableCell)(({ theme }) => ({
  position: 'sticky',
  left: 0,
  zIndex: 2,
  backgroundColor: theme.palette.background.paper,
  borderRight: `2px solid ${theme.palette.divider}`,
  padding: '6px 12px',
  minWidth: 140
}));

/** What a menu code reads as in a cell: its window for a shift, its description for a rest. */
export function scheduleLabel(schedule) {
  if (!schedule) return 'not in menu';
  return schedule.interval ? intervalToString(schedule.interval) : (schedule.description || String(schedule.code));
}

function kindOf(analysis) {
  if (analysis.unknown) return 'unknown';
  return analysis.schedule.isSentinel ? 'rest' : 'worked';
}

const legend = [
  ['· open: the solver decides', FIXED_COLORS.open],
  ['rest code', FIXED_COLORS.rest],
  ['worked shift', FIXED_COLORS.worked],
  ['code not in the menu', FIXED_COLORS.unknown]
];

/**
 * Employees × dates, one fixed day per cell. Each cell shows the
 * schedule_input value it must agree with; a red border marks a contradiction
 * (the tooltip gives the validator's reason). One menu serves every cell and
 * judges each code against the clicked cell only while it is open.
 */
const FixedDaysMatrix = ({ open, onClose, state, dates, openDays, holidays, counts, onSet }) => {
  const { employees, scheduleInput, contracts } = state;
  const menu = useMemo(() => menuCatalogue(state), [state.schedules.rows]); // eslint-disable-line react-hooks/exhaustive-deps
  const codes = useMemo(() => [...menu.values()].sort((a, b) => a.code - b.code), [menu]);
  const problem = useMemo(() => ({ scheduleInput: { dayOffCodes: scheduleInput.dayOffCodes } }), [scheduleInput.dayOffCodes]);
  const minutesOf = useMemo(() => new Map(contracts.definitions.map((c) => [c.id, Number(c.workMinutesPerDay)])), [contracts]);
  const index = useMemo(() => fixedIndex(state), [state.result.entries]); // eslint-disable-line react-hooks/exhaustive-deps
  const [anchor, setAnchor] = useState(null); // {el, eid, date}

  const onOpen = useCallback((el, eid, date) => setAnchor({ el, eid, date }), []);
  const context = (emp, d) => ({
    menu,
    cell: scheduleInput.dataMatrix?.[emp.id]?.[d] ?? '',
    problem,
    contractMinutes: minutesOf.get(activeContract(emp, d)) ?? null
  });

  const choose = (code) => {
    onSet(anchor.eid, anchor.date, code);
    setAnchor(null);
  };

  const options = useMemo(() => {
    if (!anchor) return null;
    const emp = employees.list.find((e) => e.id === anchor.eid);
    if (!emp) return null;
    const ctx = context(emp, anchor.date);
    const current = index[anchor.eid]?.[anchor.date]?.ScheduleCode ?? null;
    // Codes that fit the cell come first; the ones that contradict it follow, with the reason.
    const judged = codes.map((s) => ({ schedule: s, reason: analyseFixedDay(s.code, ctx).reason }))
      .sort((a, b) => Boolean(a.reason) - Boolean(b.reason));
    return {
      ctx,
      current,
      rest: judged.filter((o) => o.schedule.isSentinel),
      worked: judged.filter((o) => !o.schedule.isSentinel),
      stray: current !== null && !menu.has(current) ? current : null
    };
  }, [anchor]); // eslint-disable-line react-hooks/exhaustive-deps

  const option = ({ schedule, reason }) => (
    <MenuItem key={schedule.code} selected={options.current === schedule.code} onClick={() => choose(schedule.code)} dense>
      <ListItemText
        primary={`${schedule.code} · ${scheduleLabel(schedule)}${schedule.isSentinel ? '' : ` · ${schedule.weightMinutes} min`}`}
        secondary={reason ? `contradicts the cell: ${reason}` : null}
        secondaryTypographyProps={{ color: 'error', fontSize: 11 }}
      />
    </MenuItem>
  );

  return (
    <Dialog fullScreen open={open} onClose={onClose} sx={{ '& .MuiDialog-paper': { bgcolor: '#f5f5f5' } }}>
      <AppBar position="relative" elevation={1}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>{state.files.result} · fixed days</Typography>
          <Typography variant="body2" sx={{ mr: 2, opacity: 0.9 }}>
            {counts.fixed} fixed · {counts.open} open of {counts.expected} employee-days
          </Typography>
          <IconButton edge="end" color="inherit" onClick={onClose} aria-label="close"><CloseIcon /></IconButton>
        </Toolbar>
      </AppBar>
      <Box sx={{ p: 2, height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column', gap: 1.5, overflow: 'hidden' }}>
        <Box sx={{ flexGrow: 1, overflow: 'hidden', bgcolor: 'white', borderRadius: 1, boxShadow: 1 }}>
          <TableContainer sx={{ height: '100%', overflow: 'auto', '& .MuiTable-root': { borderCollapse: 'separate', borderSpacing: 0 } }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <HeaderCell sx={{ left: 0, zIndex: 5, bgcolor: 'primary.main', color: 'primary.contrastText', minWidth: 140 }}>Employee</HeaderCell>
                  {dates.map((d) => {
                    const wd = weekday(d);
                    return (
                      <HeaderCell key={d} sx={{ bgcolor: wd >= 5 ? '#f5f5f5' : undefined }}>
                        <Box>{DAY[wd]} {d.slice(8)}/{d.slice(5, 7)}</Box>
                        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', minHeight: 18 }}>
                          {holidays.has(d) && <Chip size="small" color="secondary" label="holiday" sx={{ height: 16, fontSize: 10 }} />}
                          {!openDays.has(d) && (
                            <Tooltip title="No demand row with a window on this date: closed">
                              <Chip size="small" variant="outlined" label="closed" sx={{ height: 16, fontSize: 10 }} />
                            </Tooltip>
                          )}
                        </Box>
                      </HeaderCell>
                    );
                  })}
                  <HeaderCell sx={{ minWidth: 110 }}>Fixed</HeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {employees.list.map((emp) => {
                  const row = index[emp.id] || {};
                  let fixed = 0;
                  let conflicts = 0;
                  const cells = dates.map((d) => {
                    const entry = row[d];
                    const cell = scheduleInput.dataMatrix?.[emp.id]?.[d] ?? '';
                    if (!entry) {
                      return <TableCell key={d} sx={{ p: 0, borderRight: '1px solid #eee', width: 96, minWidth: 96, maxWidth: 96 }}>
                        <FixedDayCell employeeId={emp.id} date={d} cell={cell} code={null} label="·" kind="open" reason="" onOpen={onOpen} />
                      </TableCell>;
                    }
                    fixed += 1;
                    const code = entry.ScheduleCode;
                    const analysis = analyseFixedDay(code, context(emp, d));
                    if (analysis.reason || analysis.unknown) conflicts += 1;
                    return (
                      <TableCell key={d} sx={{ p: 0, borderRight: '1px solid #eee', width: 96, minWidth: 96, maxWidth: 96 }}>
                        <FixedDayCell
                          employeeId={emp.id}
                          date={d}
                          cell={cell}
                          code={code}
                          label={scheduleLabel(analysis.schedule)}
                          kind={kindOf(analysis)}
                          reason={analysis.reason}
                          onOpen={onOpen}
                        />
                      </TableCell>
                    );
                  });
                  return (
                    <TableRow key={emp.id} hover>
                      <FirstCell>
                        <Typography variant="body2" fontWeight={600}>{emp.id}</Typography>
                        {emp.name && emp.name !== emp.id && <Typography variant="caption" color="text.secondary">{emp.name}</Typography>}
                      </FirstCell>
                      {cells}
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>
                        <Chip size="small" label={`${fixed} / ${dates.length}`} sx={{ mr: 0.5 }} />
                        {conflicts > 0 && <Chip size="small" color="error" label={`${conflicts} ✗`} />}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
        <Paper variant="outlined" sx={{ p: 1.5, bgcolor: '#fafafa' }}>
          <Typography variant="subtitle2" fontWeight={600}>Legend</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap' }}>
            {legend.map(([label, bgcolor]) => <Chip key={label} size="small" label={label} sx={{ m: 0.5, bgcolor, fontWeight: 600, border: '1px solid #e0e0e0' }} />)}
            <Chip size="small" label="red border: contradicts the schedule_input cell" sx={{ m: 0.5, bgcolor: 'white', border: '2px solid #d32f2f', fontWeight: 600 }} />
            <Chip size="small" label="caption: the schedule_input cell (hours)" sx={{ m: 0.5, fontWeight: 600 }} variant="outlined" />
          </Box>
        </Paper>
      </Box>

      <Menu
        open={!!options}
        anchorEl={anchor?.el}
        onClose={() => setAnchor(null)}
        slotProps={{ paper: { sx: { maxHeight: '60vh', minWidth: 300 } } }}
      >
        {options && [
          <ListSubheader key="head" sx={{ lineHeight: 1.4, py: 1 }}>
            {anchor.eid} · {anchor.date} · cell {cellCaption(options.ctx.cell)}
            {options.ctx.contractMinutes !== null && ` · contract ${options.ctx.contractMinutes} min`}
          </ListSubheader>,
          <MenuItem key="open" selected={options.current === null} onClick={() => choose(null)} dense>
            <ListItemText primary="· Open" secondary="No entry: the solver decides this day" />
          </MenuItem>,
          options.stray !== null && (
            <MenuItem key="stray" selected dense disabled>
              <ListItemText primary={`${options.stray} · not in menu`} secondary="Pick a code the menu defines" />
            </MenuItem>
          ),
          <ListSubheader key="rest">Rest</ListSubheader>,
          ...options.rest.map(option),
          <ListSubheader key="worked">Worked shifts</ListSubheader>,
          ...options.worked.map(option)
        ].filter(Boolean)}
      </Menu>
    </Dialog>
  );
};

export default FixedDaysMatrix;

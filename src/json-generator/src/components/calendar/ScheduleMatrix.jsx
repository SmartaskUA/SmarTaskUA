import React, { useMemo } from 'react';
import { Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Chip, Tooltip } from '@mui/material';
import { styled } from '@mui/material/styles';
import MatrixCell from './MatrixCell';
import { activeContract, weekday } from '../../v4/core';
import { analyseCell } from '../../v4/operations';

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

/**
 * Employees × dates. Header badges mark holidays and closed days (no demand
 * row with a window); grey cells are days no contract covers. The last column
 * is each week's working-day count n_wk against the labour-law cap.
 */
const ScheduleMatrix = ({ state, dates, openDays, holidays, load, onCellChange }) => {
  const { employees, scheduleInput, contracts, timeGrid } = state;
  const problem = useMemo(() => ({ scheduleInput: { dayOffCodes: scheduleInput.dayOffCodes } }), [scheduleInput.dayOffCodes]);
  const minutesOf = useMemo(() => new Map(contracts.definitions.map((c) => [c.id, Number(c.workMinutesPerDay)])), [contracts]);
  const slot = timeGrid.slotMinutes;

  return (
    <TableContainer sx={{ height: '100%', overflow: 'auto', '& .MuiTable-root': { borderCollapse: 'separate', borderSpacing: 0 } }}>
      <Table stickyHeader size="small">
        <TableHead>
          <TableRow>
            <HeaderCell sx={{ left: 0, zIndex: 5, bgcolor: 'primary.main', color: 'primary.contrastText', minWidth: 140 }}>Employee</HeaderCell>
            {dates.map((d) => {
              const wd = weekday(d);
              const closed = !openDays.has(d);
              return (
                <HeaderCell key={d} sx={{ bgcolor: wd >= 5 ? '#f5f5f5' : undefined }}>
                  <Box>{DAY[wd]} {d.slice(8)}/{d.slice(5, 7)}</Box>
                  <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center', minHeight: 18 }}>
                    {holidays.has(d) && <Chip size="small" color="secondary" label="holiday" sx={{ height: 16, fontSize: 10 }} />}
                    {closed && (
                      <Tooltip title="No demand row with a window on this date: closed, outside every week">
                        <Chip size="small" variant="outlined" label="closed" sx={{ height: 16, fontSize: 10 }} />
                      </Tooltip>
                    )}
                  </Box>
                </HeaderCell>
              );
            })}
            <HeaderCell sx={{ minWidth: 150 }}>
              Working days / week
              {load.cap !== undefined && <Typography variant="caption" display="block">cap {load.cap}</Typography>}
            </HeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {employees.list.map((emp) => {
            const row = scheduleInput.dataMatrix?.[emp.id] || {};
            return (
              <TableRow key={emp.id} hover>
                <FirstCell>
                  <Typography variant="body2" fontWeight={600}>{emp.id}</Typography>
                  {emp.name && emp.name !== emp.id && <Typography variant="caption" color="text.secondary">{emp.name}</Typography>}
                </FirstCell>
                {dates.map((d) => {
                  const contract = activeContract(emp, d);
                  const covered = !!contract;
                  const value = row[d] ?? '';
                  const analysis = analyseCell(value, {
                    problem, covered, contractMinutes: minutesOf.get(contract) ?? null, slotMinutes: slot
                  });
                  return (
                    <TableCell key={d} sx={{ p: 0, borderRight: '1px solid #eee', width: 96, minWidth: 96, maxWidth: 96 }}>
                      <MatrixCell
                        employeeId={emp.id}
                        date={d}
                        value={value}
                        analysis={analysis}
                        dayOffCodes={scheduleInput.dayOffCodes}
                        covered={covered}
                        slotMinutes={slot}
                        onCellChange={onCellChange}
                      />
                    </TableCell>
                  );
                })}
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  {(load.byEmployee[emp.id] || []).map((w) => (
                    <Tooltip key={w.week} title={`Week ${w.week}: ${w.dates.length} open day(s), ${w.nWk} asked to work`}>
                      <Chip
                        size="small"
                        label={`W${w.week} ${w.nWk}`}
                        color={load.cap !== undefined && w.nWk > load.cap ? 'error' : 'default'}
                        sx={{ mr: 0.5, mb: 0.5 }}
                      />
                    </Tooltip>
                  ))}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ScheduleMatrix;

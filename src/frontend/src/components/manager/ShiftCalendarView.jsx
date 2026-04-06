import React, { useMemo } from "react";
import { Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import LegendBox from "./LegendBox";
import {
  buildTeamPalette,
  classifyScheduleCell,
  getShiftMeta,
  getTeamColor,
  isHolidayColumn,
  resolveEmployeeDisplay,
} from "../../utils/scheduleCalendar";

const statusStyles = {
  off: { bg: "#f8fafc", border: "#cbd5e1", text: "#475569" },
  vacation: { bg: "#fee2e2", border: "#fca5a5", text: "#991b1b" },
  unavailable: { bg: "#fef3c7", border: "#fcd34d", text: "#92400e" },
  warning: { bg: "#ffe4e6", border: "#fb7185", text: "#9f1239" },
  text: { bg: "#f1f5f9", border: "#cbd5e1", text: "#0f172a" },
};

const ShiftCalendarView = ({ data = [], monthColumns = [], holidayMap = {}, employees = [] }) => {
  const rows = data.slice(1);

  const teamPalette = useMemo(() => {
    const teams = [];
    rows.forEach((row) => {
      monthColumns.forEach((column) => {
        const cell = classifyScheduleCell(row?.[column.index + 1]);
        if (cell.kind === "shift" && cell.team) {
          teams.push(cell.team);
        }
      });
    });
    return buildTeamPalette(teams);
  }, [rows, monthColumns]);

  const teamLegends = Object.entries(teamPalette).map(([team, palette]) => ({
    label: `Team ${team}`,
    color: palette.bg,
  }));

  const renderCell = (value) => {
    const cell = classifyScheduleCell(value);
    if (cell.kind === "shift") {
      const shiftMeta = getShiftMeta(cell.shift);
      const teamColor = getTeamColor(cell.team, teamPalette);
      return (
        <Box display="flex" flexDirection="column" alignItems="center" gap={0.5}>
          <Box
            sx={{
              px: 1,
              py: 0.5,
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 800,
              backgroundColor: shiftMeta.bg,
              color: shiftMeta.text,
              border: `1px solid ${shiftMeta.border}`,
              minWidth: 38,
            }}
          >
            {shiftMeta.short}
          </Box>
          <Box
            sx={{
              px: 1,
              py: 0.3,
              borderRadius: 999,
              fontSize: 10,
              fontWeight: 700,
              backgroundColor: teamColor.bg,
              color: teamColor.text,
              border: `1px solid ${teamColor.border}`,
            }}
          >
            {cell.team}
          </Box>
        </Box>
      );
    }

    const style = statusStyles[cell.kind] || statusStyles.text;
    return (
      <Box
        sx={{
          px: 1,
          py: 0.7,
          borderRadius: 2,
          fontSize: 10,
          fontWeight: 700,
          backgroundColor: style.bg,
          color: style.text,
          border: `1px solid ${style.border}`,
        }}
      >
        {cell.label}
      </Box>
    );
  };

  return (
    <Box mt={3}>
      <TableContainer
        component={Paper}
        sx={{
          borderRadius: 3,
          border: "1px solid #dbe4f0",
          boxShadow: "0 18px 40px rgba(15, 23, 42, 0.08)",
          overflowX: "auto",
        }}
      >
        <Table sx={{ minWidth: 980 }}>
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  position: "sticky",
                  left: 0,
                  zIndex: 3,
                  minWidth: 180,
                  backgroundColor: "#0f172a",
                  color: "#f8fafc",
                  borderRight: "1px solid #1e293b",
                }}
              >
                Employee
              </TableCell>
              {monthColumns.map((column) => {
                const isHoliday = isHolidayColumn(column, holidayMap);
                const isSunday = column.weekday === "Sun";
                return (
                  <TableCell
                    key={column.key}
                    align="center"
                    sx={{
                      minWidth: 64,
                      px: 0.5,
                      py: 1,
                      backgroundColor: isHoliday
                        ? "#7c3aed"
                        : isSunday
                          ? "#1d4ed8"
                          : "#2563eb",
                      color: "#fff",
                    }}
                  >
                    <Typography fontSize={11} fontWeight={800}>
                      {column.day}
                    </Typography>
                    <Typography fontSize={10} sx={{ opacity: 0.9 }}>
                      {column.weekday}
                    </Typography>
                  </TableCell>
                );
              })}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, rowIndex) => {
              const employee = resolveEmployeeDisplay(row?.[0], rowIndex, employees);
              return (
                <TableRow key={`${employee.id}-${rowIndex}`} hover>
                  <TableCell
                    sx={{
                      position: "sticky",
                      left: 0,
                      zIndex: 2,
                      backgroundColor: "#fff",
                      borderRight: "1px solid #e2e8f0",
                    }}
                  >
                    <Typography fontSize={13} fontWeight={800} color="#0f172a">
                      {employee.name}
                    </Typography>
                    {employee.subtitle && (
                      <Typography fontSize={11} color="#64748b">
                        {employee.subtitle}
                      </Typography>
                    )}
                  </TableCell>
                  {monthColumns.map((column) => {
                    const cellValue = row?.[column.index + 1];
                    const isHoliday = isHolidayColumn(column, holidayMap);
                    return (
                      <TableCell
                        key={`${employee.id}-${column.key}`}
                        align="center"
                        sx={{
                          px: 0.5,
                          py: 0.75,
                          backgroundColor: isHoliday ? "#faf5ff" : "#fff",
                        }}
                        title={String(cellValue || "")}
                      >
                        {renderCell(cellValue)}
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <LegendBox scheduleType="Turno" teamLegends={teamLegends} />
    </Box>
  );
};

export default ShiftCalendarView;

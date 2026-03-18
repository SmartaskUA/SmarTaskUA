import React, { useMemo } from "react";
import { Box, Chip, Paper, Typography } from "@mui/material";
import LegendBox from "./LegendBox";
import {
  buildTeamPalette,
  classifyScheduleCell,
  getTeamColor,
  resolveEmployeeDisplay,
} from "../../utils/scheduleCalendar";

const statusPalette = {
  off: { bg: "#f8fafc", border: "#cbd5e1", text: "#475569" },
  vacation: { bg: "#fee2e2", border: "#fca5a5", text: "#991b1b" },
  unavailable: { bg: "#fef3c7", border: "#fcd34d", text: "#92400e" },
  warning: { bg: "#ffe4e6", border: "#fb7185", text: "#9f1239" },
  text: { bg: "#f1f5f9", border: "#cbd5e1", text: "#0f172a" },
};

const dayCellWidth = 170;
const employeeColumnWidth = 250;

const HourlyCalendarView = ({ data = [], monthColumns = [], employees = [] }) => {
  const rows = data.slice(1);

  const teamPalette = useMemo(() => {
    const teams = [];
    rows.forEach((row) => {
      monthColumns.forEach((column) => {
        const cell = classifyScheduleCell(row?.[column.index + 1]);
        if (cell.kind === "hourly") {
          cell.segments.forEach((segment) => {
            if (segment.team) teams.push(segment.team);
          });
        }
      });
    });
    return buildTeamPalette(teams);
  }, [rows, monthColumns]);

  const teamLegends = Object.entries(teamPalette).map(([team, palette]) => ({
    label: team,
    color: palette.bg,
  }));

  const scheduleRows = useMemo(
    () =>
      rows.map((row, rowIndex) => {
        const employee = resolveEmployeeDisplay(row?.[0], rowIndex, employees);
        const dayCards = monthColumns.map((column) => {
          const cell = classifyScheduleCell(row?.[column.index + 1]);
          return { column, cell };
        });
        const workDays = dayCards.filter(({ cell }) => cell.kind === "hourly").length;
        const offDays = dayCards.filter(({ cell }) => cell.kind === "off").length;
        const vacationDays = dayCards.filter(({ cell }) => cell.kind === "vacation").length;
        const unavailableDays = dayCards.filter(({ cell }) => cell.kind === "unavailable").length;
        return {
          employee,
          dayCards,
          workDays,
          offDays,
          vacationDays,
          unavailableDays,
        };
      }),
    [rows, monthColumns, employees]
  );

  const renderStatusCell = (cell) => {
    const palette = statusPalette[cell.kind] || statusPalette.text;
    return (
      <Box
        sx={{
          px: 1,
          py: 1.2,
          borderRadius: 2,
          border: `1px solid ${palette.border}`,
          backgroundColor: palette.bg,
          color: palette.text,
          textAlign: "center",
          fontWeight: 700,
          fontSize: 12,
          minHeight: 48,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {cell.label}
      </Box>
    );
  };

  return (
    <Box mt={3}>
      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          border: "1px solid #dbe4f0",
          background:
            "linear-gradient(180deg, rgba(248,250,252,1) 0%, rgba(255,255,255,1) 100%)",
          boxShadow: "0 18px 36px rgba(15, 23, 42, 0.06)",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            overflowX: "auto",
            overflowY: "hidden",
            scrollbarWidth: "thin",
            "&::-webkit-scrollbar": {
              height: 10,
            },
            "&::-webkit-scrollbar-track": {
              backgroundColor: "#e2e8f0",
            },
            "&::-webkit-scrollbar-thumb": {
              backgroundColor: "#94a3b8",
              borderRadius: 999,
            },
          }}
        >
          <Box sx={{ minWidth: employeeColumnWidth + monthColumns.length * dayCellWidth }}>
            <Box display="flex" sx={{ borderBottom: "1px solid #dbe4f0", backgroundColor: "#0f172a" }}>
              <Box
                sx={{
                  position: "sticky",
                  left: 0,
                  zIndex: 4,
                  width: employeeColumnWidth,
                  flex: `0 0 ${employeeColumnWidth}px`,
                  px: 2,
                  py: 1.5,
                  borderRight: "1px solid #1e293b",
                  backgroundColor: "#0f172a",
                  color: "#f8fafc",
                }}
              >
                <Typography fontSize={14} fontWeight={800}>
                  Employee
                </Typography>
              </Box>
              {monthColumns.map((column) => (
                <Box
                  key={column.key}
                  sx={{
                    width: dayCellWidth,
                    flex: `0 0 ${dayCellWidth}px`,
                    px: 1,
                    py: 1.25,
                    textAlign: "center",
                    color: "#fff",
                    backgroundColor: column.weekday === "Sun" ? "#1d4ed8" : "#2563eb",
                    borderLeft: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  <Typography fontSize={12} fontWeight={800}>
                    {column.day}
                  </Typography>
                  <Typography fontSize={10} sx={{ opacity: 0.9 }}>
                    {column.weekday}
                  </Typography>
                </Box>
              ))}
            </Box>

            {scheduleRows.map(({ employee, dayCards, workDays, offDays, vacationDays, unavailableDays }, rowIndex) => (
              <Box
                key={`${employee.id}-${rowIndex}`}
                display="flex"
                sx={{
                  borderBottom: rowIndex === scheduleRows.length - 1 ? "none" : "1px solid #e2e8f0",
                  backgroundColor: rowIndex % 2 === 0 ? "#fff" : "#f8fafc",
                }}
              >
                <Box
                  sx={{
                    position: "sticky",
                    left: 0,
                    zIndex: 3,
                    width: employeeColumnWidth,
                    flex: `0 0 ${employeeColumnWidth}px`,
                    px: 2,
                    py: 1.5,
                    borderRight: "1px solid #e2e8f0",
                    backgroundColor: rowIndex % 2 === 0 ? "#fff" : "#f8fafc",
                  }}
                >
                  <Typography fontSize={15} fontWeight={800} color="#0f172a">
                    {employee.name}
                  </Typography>
                  {employee.subtitle && (
                    <Typography fontSize={12} color="#64748b" mb={0.75}>
                      {employee.subtitle}
                    </Typography>
                  )}
                  {employee.teams.length > 0 && (
                    <Box display="flex" gap={0.5} flexWrap="wrap" mb={1}>
                      {employee.teams.map((team) => {
                        const palette = getTeamColor(team, teamPalette);
                        return (
                          <Box
                            key={`${employee.id}-${team}`}
                            sx={{
                              px: 0.85,
                              py: 0.25,
                              borderRadius: 999,
                              backgroundColor: palette.bg,
                              border: `1px solid ${palette.border}`,
                              color: palette.text,
                              fontSize: 10,
                              fontWeight: 700,
                              lineHeight: 1.2,
                            }}
                          >
                            {team}
                          </Box>
                        );
                      })}
                    </Box>
                  )}
                  <Box display="flex" gap={0.75} flexWrap="wrap">
                    <Chip label={`${workDays} work`} size="small" color="info" variant="outlined" />
                    <Chip label={`${offDays} off`} size="small" variant="outlined" />
                    {vacationDays > 0 && (
                      <Chip label={`${vacationDays} vac`} size="small" color="error" variant="outlined" />
                    )}
                    {unavailableDays > 0 && (
                      <Chip label={`${unavailableDays} unavailable`} size="small" color="warning" variant="outlined" />
                    )}
                  </Box>
                </Box>

                {dayCards.map(({ column, cell }) => (
                  <Box
                    key={`${employee.id}-${column.key}`}
                    sx={{
                      width: dayCellWidth,
                      flex: `0 0 ${dayCellWidth}px`,
                      p: 1,
                      backgroundColor: column.weekday === "Sun" ? "#eff6ff" : "transparent",
                      borderLeft: "1px solid #eef2f7",
                    }}
                  >
                    {cell.kind === "hourly" ? (
                      <Box display="flex" flexDirection="column" gap={0.6}>
                        {cell.segments.map((segment, index) => {
                          const palette = getTeamColor(segment.team, teamPalette);
                          return (
                            <Box
                              key={`${column.key}-${index}`}
                              sx={{
                                px: 0.9,
                                py: 0.75,
                                borderRadius: 2,
                                backgroundColor: palette.bg,
                                border: `1px solid ${palette.border}`,
                              }}
                            >
                              <Typography fontSize={11} fontWeight={700} color="#0f172a">
                                {segment.time}
                              </Typography>
                              <Typography fontSize={10} color={palette.text} fontWeight={700}>
                                {segment.team}
                              </Typography>
                            </Box>
                          );
                        })}
                      </Box>
                    ) : (
                      renderStatusCell(cell)
                    )}
                  </Box>
                ))}
              </Box>
            ))}
          </Box>
        </Box>
      </Paper>

      <LegendBox scheduleType="Horas" teamLegends={teamLegends} />
    </Box>
  );
};

export default HourlyCalendarView;

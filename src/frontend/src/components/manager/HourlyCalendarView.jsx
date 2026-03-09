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

  const renderStatusCard = (cell) => {
    const palette = statusPalette[cell.kind] || statusPalette.text;
    return (
      <Box
        sx={{
          mt: 1,
          px: 1,
          py: 1.5,
          borderRadius: 2,
          border: `1px solid ${palette.border}`,
          backgroundColor: palette.bg,
          color: palette.text,
          textAlign: "center",
          fontWeight: 700,
          fontSize: 12,
        }}
      >
        {cell.label}
      </Box>
    );
  };

  return (
    <Box mt={3}>
      <Box display="flex" flexDirection="column" gap={2.5}>
        {rows.map((row, rowIndex) => {
          const employee = resolveEmployeeDisplay(row?.[0], rowIndex, employees);
          const dayCards = monthColumns.map((column) => {
            const cell = classifyScheduleCell(row?.[column.index + 1]);
            return { column, cell };
          });
          const workDays = dayCards.filter(({ cell }) => cell.kind === "hourly").length;
          const offDays = dayCards.filter(({ cell }) => cell.kind === "off").length;
          const vacationDays = dayCards.filter(({ cell }) => cell.kind === "vacation").length;
          const unavailableDays = dayCards.filter(({ cell }) => cell.kind === "unavailable").length;

          return (
            <Paper
              key={`${employee.id}-${rowIndex}`}
              elevation={0}
              sx={{
                p: 2,
                borderRadius: 3,
                border: "1px solid #dbe4f0",
                background:
                  "linear-gradient(180deg, rgba(248,250,252,1) 0%, rgba(255,255,255,1) 100%)",
                boxShadow: "0 18px 36px rgba(15, 23, 42, 0.06)",
              }}
            >
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="flex-start"
                flexWrap="wrap"
                gap={1.5}
                mb={2}
              >
                <Box>
                  <Typography fontSize={16} fontWeight={800} color="#0f172a">
                    {employee.name}
                  </Typography>
                  {employee.subtitle && (
                    <Typography fontSize={12} color="#64748b">
                      {employee.subtitle}
                    </Typography>
                  )}
                  {employee.teams.length > 0 && (
                    <Box display="flex" gap={0.75} flexWrap="wrap" mt={0.75}>
                      {employee.teams.map((team) => {
                        const palette = getTeamColor(team, teamPalette);
                        return (
                          <Box
                            key={`${employee.id}-${team}`}
                            sx={{
                              px: 1,
                              py: 0.35,
                              borderRadius: 999,
                              backgroundColor: palette.bg,
                              border: `1px solid ${palette.border}`,
                              color: palette.text,
                              fontSize: 11,
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
                </Box>
                <Box display="flex" gap={1} flexWrap="wrap">
                  <Chip label={`${workDays} work days`} size="small" color="info" variant="outlined" />
                  <Chip label={`${offDays} off`} size="small" variant="outlined" />
                  {vacationDays > 0 && (
                    <Chip label={`${vacationDays} vacation`} size="small" color="error" variant="outlined" />
                  )}
                  {unavailableDays > 0 && (
                    <Chip label={`${unavailableDays} unavailable`} size="small" color="warning" variant="outlined" />
                  )}
                </Box>
              </Box>

              <Box
                sx={{
                  display: "flex",
                  flexWrap: "nowrap",
                  gap: 1.25,
                  overflowX: "auto",
                  overflowY: "hidden",
                  pb: 1,
                  pr: 0.5,
                  scrollbarWidth: "thin",
                  "&::-webkit-scrollbar": {
                    height: 10,
                  },
                  "&::-webkit-scrollbar-track": {
                    backgroundColor: "#e2e8f0",
                    borderRadius: 999,
                  },
                  "&::-webkit-scrollbar-thumb": {
                    backgroundColor: "#94a3b8",
                    borderRadius: 999,
                  },
                }}
              >
                {dayCards.map(({ column, cell }) => (
                  <Box
                    key={`${employee.id}-${column.key}`}
                    sx={{
                      flex: "0 0 150px",
                      borderRadius: 2.5,
                      border: "1px solid #e2e8f0",
                      backgroundColor: column.weekday === "Sun" ? "#eff6ff" : "#fff",
                      p: 1.25,
                      minHeight: 112,
                    }}
                  >
                    <Box display="flex" justifyContent="space-between" alignItems="baseline">
                      <Typography fontSize={13} fontWeight={800} color="#0f172a">
                        {column.day}
                      </Typography>
                      <Typography fontSize={10} color="#64748b">
                        {column.weekday}
                      </Typography>
                    </Box>

                    {cell.kind === "hourly" ? (
                      <Box mt={1} display="flex" flexDirection="column" gap={0.75}>
                        {cell.segments.map((segment, index) => {
                          const palette = getTeamColor(segment.team, teamPalette);
                          return (
                            <Box
                              key={`${column.key}-${index}`}
                              sx={{
                                px: 1,
                                py: 0.8,
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
                      renderStatusCard(cell)
                    )}
                  </Box>
                ))}
              </Box>
            </Paper>
          );
        })}
      </Box>

      <LegendBox scheduleType="Horas" teamLegends={teamLegends} />
    </Box>
  );
};

export default HourlyCalendarView;

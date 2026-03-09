import React, { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Chip,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { classifyScheduleCell, isHolidayColumn } from "../../utils/scheduleCalendar";

const metricConfig = {
  minimum: {
    label: "Minimum",
    activeBg: "#dbeafe",
    activeBorder: "#60a5fa",
    activeText: "#1d4ed8",
    cellBg: "#eff6ff",
    cellBorder: "#bfdbfe",
  },
  estimated: {
    label: "Estimated",
    activeBg: "#fef3c7",
    activeBorder: "#f59e0b",
    activeText: "#92400e",
    cellBg: "#fffbeb",
    cellBorder: "#fde68a",
  },
  ideal: {
    label: "Ideal",
    activeBg: "#dcfce7",
    activeBorder: "#4ade80",
    activeText: "#166534",
    cellBg: "#f0fdf4",
    cellBorder: "#bbf7d0",
  },
};

const parseMinutes = (value) => {
  const text = String(value || "").trim();
  if (!text.includes(":")) {
    const hours = Number(text);
    return Number.isFinite(hours) ? hours * 60 : Number.MAX_SAFE_INTEGER;
  }
  const [hour, minute] = text.split(":").map((part) => Number(part));
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
    return Number.MAX_SAFE_INTEGER;
  }
  return hour * 60 + minute;
};

const normalizeTeamOption = (team) => {
  if (typeof team === "string") {
    return { code: team.trim(), label: team.trim() };
  }
  const code = String(team?.code || team?.name || team?.id || "").trim();
  const label = String(team?.name || team?.code || team?.id || "").trim();
  return { code, label: label || code };
};

const parseRange = (value) => {
  const text = String(value || "").trim();
  const [startText, endText] = text.split("-");
  if (!startText || !endText) {
    return null;
  }
  const start = parseMinutes(startText);
  const end = parseMinutes(endText);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return null;
  }
  return { start, end };
};

const buildHalfHourSlots = (start, end) => {
  const slots = [];
  for (let minute = start; minute < end; minute += 30) {
    slots.push(minute);
  }
  return slots;
};

const diffPalette = (delta) => {
  if (delta === null || delta === undefined) {
    return {
      bg: "#f8fafc",
      border: "#e2e8f0",
      text: "#94a3b8",
      accent: "#64748b",
    };
  }
  if (delta < 0) {
    return {
      bg: "#fef2f2",
      border: "#fca5a5",
      text: "#991b1b",
      accent: "#dc2626",
    };
  }
  if (delta > 0) {
    return {
      bg: "#f0fdf4",
      border: "#86efac",
      text: "#166534",
      accent: "#16a34a",
    };
  }
  return {
    bg: "#eff6ff",
    border: "#93c5fd",
    text: "#1d4ed8",
    accent: "#2563eb",
  };
};

const ProblemDemandTable = ({
  demandData = [],
  workPeriods = [],
  teams = [],
  monthColumns = [],
  holidayMap = {},
  scheduleData = [],
}) => {
  const [selectedTeam, setSelectedTeam] = useState("");
  const [selectedMetric, setSelectedMetric] = useState("minimum");

  const teamOptions = useMemo(() => {
    const byCode = new Map();
    teams.map(normalizeTeamOption).forEach((option) => {
      if (option.code) {
        byCode.set(option.code, option);
      }
    });
    demandData.forEach((row) => {
      const code = String(row?.team || "").trim();
      if (code && !byCode.has(code)) {
        byCode.set(code, { code, label: code });
      }
    });
    return Array.from(byCode.values()).sort((left, right) =>
      left.label.localeCompare(right.label)
    );
  }, [teams, demandData]);

  useEffect(() => {
    if (!teamOptions.length) {
      setSelectedTeam("");
      return;
    }
    if (!teamOptions.some((option) => option.code === selectedTeam)) {
      setSelectedTeam(teamOptions[0].code);
    }
  }, [teamOptions, selectedTeam]);

  const selectedMetricConfig = metricConfig[selectedMetric] || metricConfig.minimum;
  const monthDateKeys = useMemo(
    () => monthColumns.map((column) => column.date.toISOString().slice(0, 10)),
    [monthColumns]
  );

  const workPeriodMap = useMemo(() => {
    const mapped = new Map();
    workPeriods.forEach((period) => {
      if (period?.code) {
        mapped.set(period.code, period);
      }
    });
    return mapped;
  }, [workPeriods]);

  const filteredRows = useMemo(
    () =>
      demandData.filter(
        (row) =>
          String(row?.team || "").trim() === selectedTeam &&
          monthDateKeys.includes(String(row?.date || "").trim())
      ),
    [demandData, monthDateKeys, selectedTeam]
  );

  const demandIndex = useMemo(() => {
    const mapped = new Map();
    filteredRows.forEach((row) => {
      const workPeriodCode = String(row?.workPeriod || "").trim();
      const date = String(row?.date || "").trim();
      if (workPeriodCode && date) {
        mapped.set(`${workPeriodCode}|${date}`, row);
      }
    });
    return mapped;
  }, [filteredRows]);

  const coverageIndex = useMemo(() => {
    const mapped = new Map();
    const rows = Array.isArray(scheduleData) ? scheduleData.slice(1) : [];

    rows.forEach((row) => {
      monthColumns.forEach((column) => {
        const dateKey = column.date.toISOString().slice(0, 10);
        const cell = classifyScheduleCell(row?.[column.index + 1]);
        if (cell.kind !== "hourly") {
          return;
        }
        cell.segments.forEach((segment) => {
          if (!segment?.team || !segment?.time) {
            return;
          }
          const range = parseRange(segment.time);
          if (!range) {
            return;
          }
          buildHalfHourSlots(range.start, range.end).forEach((slotStart) => {
            const key = `${dateKey}|${segment.team}|${slotStart}`;
            mapped.set(key, (mapped.get(key) || 0) + 1);
          });
        });
      });
    });

    return mapped;
  }, [scheduleData, monthColumns]);

  const visibleWorkPeriods = useMemo(() => {
    const codes = Array.from(
      new Set(filteredRows.map((row) => String(row?.workPeriod || "").trim()).filter(Boolean))
    );
    return codes
      .map((code) => {
        const config = workPeriodMap.get(code);
        const start = parseMinutes(config?.timeRange?.start);
        const end = parseMinutes(config?.timeRange?.end);
        return {
          code,
          label: config?.name || code,
          startLabel: config?.timeRange?.start || null,
          endLabel: config?.timeRange?.end || null,
          start,
          end,
          slots:
            Number.isFinite(start) && Number.isFinite(end) && end > start
              ? buildHalfHourSlots(start, end)
              : [],
        };
      })
      .sort((left, right) => {
        if (left.start !== right.start) {
          return left.start - right.start;
        }
        if (left.end !== right.end) {
          return left.end - right.end;
        }
        return left.label.localeCompare(right.label);
      });
  }, [filteredRows, workPeriodMap]);

  const activeTeam = teamOptions.find((option) => option.code === selectedTeam) || null;
  const coverageSummary = useMemo(() => {
    let exact = 0;
    let over = 0;
    let under = 0;

    visibleWorkPeriods.forEach((period) => {
      monthColumns.forEach((column) => {
        const dateKey = column.date.toISOString().slice(0, 10);
        const row = demandIndex.get(`${period.code}|${dateKey}`);
        if (!row) {
          return;
        }
        const required = Number(row?.[selectedMetric]);
        if (!Number.isFinite(required)) {
          return;
        }
        const actual = period.slots.length
          ? Math.min(
              ...period.slots.map(
                (slotStart) =>
                  coverageIndex.get(`${dateKey}|${selectedTeam}|${slotStart}`) || 0
              )
            )
          : 0;
        const delta = actual - required;
        if (delta < 0) {
          under += 1;
        } else if (delta > 0) {
          over += 1;
        } else {
          exact += 1;
        }
      });
    });

    return { exact, over, under };
  }, [coverageIndex, demandIndex, monthColumns, selectedMetric, selectedTeam, visibleWorkPeriods]);

  if (!monthColumns.length) {
    return null;
  }

  return (
    <Box mt={3}>
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 2,
          borderRadius: 2,
          border: "1px solid #dbe4f0",
          backgroundColor: "#f8fafc",
        }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
          <Box>
            <Typography variant="subtitle1" fontWeight={800}>
              Demand View
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {activeTeam
                ? `${selectedMetricConfig.label} demand for ${activeTeam.label}`
                : "Select a team to inspect demand by day and work period."}
            </Typography>
            {activeTeam && (
              <Box display="flex" gap={1} flexWrap="wrap" mt={1}>
                <Chip
                  size="small"
                  label={`${coverageSummary.exact} exact`}
                  sx={{ backgroundColor: "#eff6ff", color: "#1d4ed8" }}
                />
                <Chip
                  size="small"
                  label={`${coverageSummary.over} over`}
                  sx={{ backgroundColor: "#f0fdf4", color: "#166534" }}
                />
                <Chip
                  size="small"
                  label={`${coverageSummary.under} under`}
                  sx={{ backgroundColor: "#fef2f2", color: "#991b1b" }}
                />
              </Box>
            )}
          </Box>
          <Box display="flex" alignItems="center" flexWrap="wrap" gap={1.5}>
            <Select
              size="small"
              value={selectedTeam}
              onChange={(event) => setSelectedTeam(event.target.value)}
              displayEmpty
              sx={{ minWidth: 180, backgroundColor: "#fff" }}
            >
              {teamOptions.map((option) => (
                <MenuItem key={option.code} value={option.code}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
            {Object.entries(metricConfig).map(([metric, config]) => {
              const isActive = metric === selectedMetric;
              return (
                <Button
                  key={metric}
                  size="small"
                  variant={isActive ? "contained" : "outlined"}
                  onClick={() => setSelectedMetric(metric)}
                  sx={
                    isActive
                      ? {
                          backgroundColor: config.activeBg,
                          color: config.activeText,
                          borderColor: config.activeBorder,
                          boxShadow: "none",
                          "&:hover": {
                            backgroundColor: config.activeBg,
                            boxShadow: "none",
                          },
                        }
                      : {}
                  }
                >
                  {config.label}
                </Button>
              );
            })}
          </Box>
        </Box>
      </Paper>

      {selectedTeam && !visibleWorkPeriods.length ? (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            borderRadius: 2,
            border: "1px dashed #cbd5e1",
            backgroundColor: "#fff",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            No demand rows were found for this team in the selected month.
          </Typography>
        </Paper>
      ) : (
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
                    minWidth: 220,
                    backgroundColor: "#0f172a",
                    color: "#f8fafc",
                    borderRight: "1px solid #1e293b",
                  }}
                >
                  Work Period
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
              {visibleWorkPeriods.map((period) => (
                <TableRow key={period.code} hover>
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
                      {period.startLabel && period.endLabel
                        ? `${period.startLabel}-${period.endLabel}`
                        : period.label}
                    </Typography>
                    <Typography fontSize={11} color="#64748b">
                      {period.label}
                    </Typography>
                  </TableCell>
                  {monthColumns.map((column) => {
                    const dateKey = column.date.toISOString().slice(0, 10);
                    const row = demandIndex.get(`${period.code}|${dateKey}`);
                    const rawValue = row?.[selectedMetric];
                    const required =
                      rawValue === undefined || rawValue === null || rawValue === ""
                        ? null
                        : Number(rawValue);
                    const actual =
                      row && period.slots.length
                        ? Math.min(
                            ...period.slots.map(
                              (slotStart) =>
                                coverageIndex.get(`${dateKey}|${selectedTeam}|${slotStart}`) || 0
                            )
                          )
                        : row
                          ? 0
                          : null;
                    const delta =
                      required === null || actual === null ? null : actual - required;
                    const palette = diffPalette(delta);
                    const isHoliday = isHolidayColumn(column, holidayMap);
                    return (
                      <TableCell
                        key={`${period.code}-${column.key}`}
                        align="center"
                        sx={{
                          px: 0.5,
                          py: 0.75,
                          backgroundColor: isHoliday ? "#faf5ff" : "#fff",
                        }}
                        title={row ? `${selectedMetricConfig.label}: ${rawValue}` : "No demand"}
                      >
                        <Box
                          sx={{
                            px: 1,
                            py: 0.7,
                            borderRadius: 2,
                            minHeight: 64,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 0.15,
                            backgroundColor:
                              required === null ? "#f8fafc" : palette.bg,
                            color: required === null ? "#94a3b8" : palette.text,
                            border: `1px solid ${
                              required === null ? "#e2e8f0" : palette.border
                            }`,
                          }}
                        >
                          <Typography fontSize={12} fontWeight={800}>
                            {required === null ? "-" : required}
                          </Typography>
                          {required !== null && (
                            <>
                              <Typography fontSize={10} color="#64748b" fontWeight={700}>
                                actual {actual}
                              </Typography>
                              <Typography fontSize={10} color={palette.accent} fontWeight={800}>
                                {delta > 0 ? `+${delta}` : String(delta)}
                              </Typography>
                            </>
                          )}
                        </Box>
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default ProblemDemandTable;

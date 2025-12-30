import React, { useMemo } from "react";
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";

const getRowColor = (index, type) => {
  const isEvenBlock = Math.floor(index / 4) % 2 === 0;
  const base = isEvenBlock ? "#f9f9f9" : "#eef4ff";
  if (type === "Minimum" || type === "min") return "#e0f7fa";
  if (type === "Ideal" || type === "ideal") return "#f1f8e9";
  return base;
};

const monthLabels = [
  { name: "January", days: 31 },
  { name: "February", days: 28 },
  { name: "March", days: 31 },
  { name: "April", days: 30 },
  { name: "May", days: 31 },
  { name: "June", days: 30 },
  { name: "July", days: 31 },
  { name: "August", days: 31 },
  { name: "September", days: 30 },
  { name: "October", days: 31 },
  { name: "November", days: 30 },
  { name: "December", days: 31 },
];

const startMonth = "November"; // Add
const startIndex = monthLabels.findIndex((m) => m.name === startMonth);
const rotatedMonths = [
  ...monthLabels.slice(startIndex),
  ...monthLabels.slice(0, startIndex),
];

const monthBoundaries = rotatedMonths.reduce((acc, month, idx) => {
  const start = acc.length === 0 ? 0 : acc[idx - 1].end;
  acc.push({ start, end: start + month.days });
  return acc;
}, []);


const detectSlotPrecision = (label) => {
  const text = String(label || "").trim();
  if (!text) return null;
  if (text.includes(":")) {
    const parts = text.split("-");
    const hasMinutes = parts.some((part) => {
      const time = String(part).trim();
      const pieces = time.split(":");
      const minutes = pieces[1] ? Number(pieces[1]) : 0;
      return Number.isFinite(minutes) && minutes !== 0;
    });
    return hasMinutes ? "30min" : "hour";
  }
  if (text.includes(".")) {
    const parts = text.split("-");
    const hasHalf = parts.some((part) => {
      const value = Number(String(part).trim());
      return Number.isFinite(value) && value % 1 !== 0;
    });
    return hasHalf ? "30min" : "hour";
  }
  return "hour";
};

const MinimumsTemplate = ({
  name,
  data,
  scheduleData = [],
  scheduleType,
  mode = "all",
  showDiff = false,
  selectedMonth,
}) => {
  if (!data || data.length === 0) return null;

  const shiftCodePattern = /^[MTN]$/i;
  const hourSlotPattern = /^\s*\d{1,2}(?::\d{2})?(?:\.\d+)?\s*-\s*\d{1,2}(?::\d{2})?(?:\.\d+)?\s*$/;

  const parsedTemplate = useMemo(() => {
    let currentTeam = null;
    const rows = [];
    let hasIdeals = false;
    let hasHourlySlots = false;
    let slotPrecision = "hour";

    data.forEach((row) => {
      const teamLabel = String(row?.[0] || "").trim();
      if (teamLabel) {
        currentTeam = teamLabel;
      }
      const teamName = currentTeam;
      if (!teamName) return;

      const col1 = String(row?.[1] || "").trim();
      const col2 = String(row?.[2] || "").trim();
      let type = "min";
      let slot = col1;
      let valuesStart = 2;

      if (/ideal/i.test(col1)) {
        type = "ideal";
        slot = col2;
        valuesStart = 3;
        hasIdeals = true;
      } else if (/min/i.test(col1)) {
        type = "min";
        slot = col2;
        valuesStart = 3;
      } else if (hourSlotPattern.test(col1) || shiftCodePattern.test(col1)) {
        type = "min";
        slot = col1;
        valuesStart = 2;
      }

      const trimmedSlot = String(slot || "").trim();
      if (hourSlotPattern.test(trimmedSlot)) {
        hasHourlySlots = true;
        const detectedPrecision = detectSlotPrecision(trimmedSlot);
        if (detectedPrecision === "30min") {
          slotPrecision = "30min";
        }
      }

      rows.push({
        teamName,
        type,
        slot: String(slot || "").trim(),
        values: row.slice(valuesStart),
        rawRow: row,
      });
    });

    const normalizedType = String(scheduleType || "").toLowerCase();
    if (normalizedType.includes("hora") || normalizedType.includes("hour")) {
      hasHourlySlots = true;
    }

    return {
      rows,
      hasIdeals,
      isHourlyFormat: hasHourlySlots,
      slotPrecision,
    };
  }, [data, scheduleType]);

  const { rows, hasIdeals, isHourlyFormat, slotPrecision } = parsedTemplate;
  const normalizedMode =
    mode === "ideal" ? "ideal" : mode === "min" ? "min" : "all";
  const showTypeColumn = hasIdeals && normalizedMode === "all";
  const leadingColumns = showTypeColumn ? 3 : 2;
  const monthIndex =
    Number.isFinite(Number(selectedMonth)) && Number(selectedMonth) > 0
      ? Number(selectedMonth) - 1
      : null;
  const isMonthScoped = monthIndex !== null && monthIndex < rotatedMonths.length;
  const monthStartOffset = isMonthScoped
    ? rotatedMonths.slice(0, monthIndex).reduce((sum, month) => sum + month.days, 0)
    : 0;
  const activeMonths = isMonthScoped ? [rotatedMonths[monthIndex]] : rotatedMonths;

  const formatSlot = (startMin, endMin) => {
    const pad = (value) => String(value).padStart(2, "0");
    const h1 = Math.floor(startMin / 60);
    const m1 = startMin % 60;
    const h2 = Math.floor(endMin / 60);
    const m2 = endMin % 60;
    if (slotPrecision === "30min") {
      return `${pad(h1)}:${pad(m1)}-${pad(h2)}:${pad(m2)}`;
    }
    return `${pad(h1)}-${pad(h2)}`;
  };

  const parseSlotLabel = (label) => {
    const cleaned = String(label || "").trim();
    if (!cleaned) return null;
    const parts = cleaned.split("-");
    if (parts.length < 2) return null;
    const toMinutes = (value) => {
      const text = String(value || "").trim();
      if (text.includes(":")) {
        const [h, m] = text.split(":").map((v) => Number(v));
        return h * 60 + (Number.isFinite(m) ? m : 0);
      }
      if (text.includes(".")) {
        const num = Number(text);
        const hours = Math.floor(num);
        const minutes = Math.round((num - hours) * 60);
        return hours * 60 + minutes;
      }
      return Number(text) * 60;
    };
    const startMin = toMinutes(parts[0]);
    const endMin = toMinutes(parts[1]);
    if (!Number.isFinite(startMin) || !Number.isFinite(endMin)) return null;
    return formatSlot(startMin, endMin);
  };

  const actualCounts = useMemo(() => {
    if (!showDiff || !scheduleData || scheduleData.length === 0) {
      return { shift: new Map(), hour: new Map() };
    }

    const shiftMap = new Map();
    const hourMap = new Map();
    const shiftPattern = /^\s*([MTN])\s*[_-]\s*([A-Za-z])\s*$/i;
    const hourBlockPattern =
      /^\s*(\d{1,2}(?:\.\d+)?)\s*-\s*(\d{1,2}(?:\.\d+)?)(?:\s*-\s*(\d{1,2}(?:\.\d+)?))?\s*[_-]\s*([A-Za-z])\s*$/;

    const toMinutes = (value) => {
      const num = Number(value);
      const hours = Math.floor(num);
      const minutes = Math.round((num - hours) * 60);
      return hours * 60 + minutes;
    };

    const slotStep = slotPrecision === "30min" ? 30 : 60;

    scheduleData.slice(1).forEach((row) => {
      row.slice(1).forEach((cell, index) => {
        const day = index + 1;
        const text = String(cell || "").trim();
        if (!text) return;
        const upper = text.toUpperCase();
        if (upper === "0" || upper === "OFF" || upper === "F" || upper === "VACATION") {
          return;
        }

        const shiftMatch = text.match(shiftPattern);
        if (shiftMatch) {
          const shift = shiftMatch[1].toUpperCase();
          const team = shiftMatch[2].toUpperCase();
          const key = `${day}|${shift}|${team}`;
          shiftMap.set(key, (shiftMap.get(key) || 0) + 1);
          return;
        }

        const hourMatch = text.match(hourBlockPattern);
        if (hourMatch) {
          const start = Number(hourMatch[1]);
          const mid = Number(hourMatch[2]);
          const end = hourMatch[3] !== undefined ? Number(hourMatch[3]) : null;
          const team = hourMatch[4].toUpperCase();
          const segments = [];

          if (Number.isFinite(start) && Number.isFinite(mid)) {
            segments.push([toMinutes(start), toMinutes(mid)]);
          }
          if (end !== null && Number.isFinite(end)) {
            segments.push([toMinutes(mid) + 60, toMinutes(end)]);
          }

          segments.forEach(([segStart, segEnd]) => {
            for (let t = segStart; t < segEnd; t += slotStep) {
              const slotKey = formatSlot(t, t + slotStep);
              const key = `${day}|${slotKey}|${team}`;
              hourMap.set(key, (hourMap.get(key) || 0) + 1);
            }
          });
        }
      });
    });

    return { shift: shiftMap, hour: hourMap };
  }, [scheduleData, slotPrecision, showDiff]);

  const rowsByMode =
    normalizedMode === "all"
      ? rows
      : rows.filter((row) => row.type === normalizedMode);

  const teams = [];
  let currentTeam = null;
  rowsByMode.forEach((row) => {
    const teamName = row.teamName || currentTeam;
    if (teamName && teamName !== currentTeam) {
      currentTeam = teamName;
      teams.push({ team: currentTeam, rows: [row] });
    } else {
      teams[teams.length - 1]?.rows.push(row);
    }
  });

  const getMonthHeader = () => {
    const cells = Array.from({ length: leadingColumns }, (_, index) => (
      <TableCell key={`empty-${index}`} />
    ));
    activeMonths.forEach((month, i) => { // Month labels
      cells.push(
        <TableCell
          key={`month-${i}`}
          align="center"
          colSpan={month.days}
          sx={{
            fontWeight: "bold",
            backgroundColor: "#d3eaf2",
            borderRight: "2px solid #000",
          }}
        >
          {month.name}
        </TableCell>
      );
    });
    return <TableRow>{cells}</TableRow>;
  };

  const getDayNumbersRow = () => {
    const cells = Array.from({ length: leadingColumns }, (_, index) => (
      <TableCell key={`empty-${index}`} />
    ));
  
    activeMonths.forEach((month, monthIndex) => {
      for (let i = 1; i <= month.days; i++) {

        const originalIndex = monthLabels.findIndex(m => m.name === month.name);
        // 👉 Define o ano correto consoante o mês
        const year =
          month.name === "November" || month.name === "December" ? 2021 : 2022;
      
        // 👉 Usa o índice correto (monthIndex) e o ano definido
        const date = new Date(year, originalIndex, i);
        const weekday = date
          .toLocaleDateString("pt-PT", { weekday: "short" })
          .replace(".", ""); // remove o ponto final
      
        const isLastDay = i === month.days;
      
        cells.push(
          <TableCell
            key={`day-${month.name}-${i}`}
            align="center"
            sx={{
              fontWeight: "bold",
              borderRight: isLastDay ? "2px solid #000" : undefined,
            }}
          >
            <Box>
              <Typography variant="body2">{i}</Typography>
              <Typography variant="caption" color="text.secondary">
                {weekday.charAt(0).toUpperCase() + weekday.slice(1)}
              </Typography>
            </Box>
          </TableCell>
        );
      }
    });
  
    return <TableRow>{cells}</TableRow>;
  };
  

  

  const isMonthEndIndex = (index) => {
    return monthBoundaries.some((boundary) => index === boundary.end - 1);
  };

  const titleLabel =
    normalizedMode === "ideal"
      ? "Ideals"
      : normalizedMode === "min"
        ? "Minimums"
        : "Minimums & Ideals";

  return (
    <Box mt={4}>
      <Typography variant="h6" gutterBottom>
        {titleLabel}
        {showDiff ? " Differences" : ""} - Template: {name}
      </Typography>
      <TableContainer component={Paper} sx={{ overflowX: "auto", borderRadius: 2 }}>
        <Table size="small" sx={{ minWidth: 1200 }}>
          <TableHead sx={{ backgroundColor: "#e3f2fd" }}>
            {getMonthHeader()}
            {getDayNumbersRow()}
          </TableHead>
          <TableBody>
            {teams.map(({ team, rows }, teamIndex) =>
              rows.map((row, rowIndex) => {
                const bgColor = getRowColor(teamIndex * 4 + rowIndex, row.type);
                const dayValues = row.values;
                const teamCodeMatch = String(row.teamName || "").match(/([A-Za-z])\s*$/);
                const teamCode = teamCodeMatch ? teamCodeMatch[1].toUpperCase() : row.teamName;
                const slotKey = isHourlyFormat
                  ? parseSlotLabel(row.slot)
                  : String(row.slot || "").trim().toUpperCase();
                const dayOffset = isMonthScoped ? monthStartOffset : 0;
                const dayCount = isMonthScoped
                  ? activeMonths[0].days
                  : dayValues.length;
                const daySlice = dayValues.slice(dayOffset, dayOffset + dayCount);
                return (
                  <TableRow key={`${teamIndex}-${rowIndex}`} sx={{ backgroundColor: bgColor }}>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      {rowIndex === 0 ? team : ""}
                    </TableCell>
                    {showTypeColumn && (
                      <TableCell>
                        {row.type === "ideal" ? "Ideal" : "Minimum"}
                      </TableCell>
                    )}
                    <TableCell>
                      {isHourlyFormat
                        ? showDiff
                          ? slotKey || row.slot
                          : row.slot
                        : String(row.slot || "").toUpperCase()}
                    </TableCell>
                    {daySlice.map((val, i) => {
                      const globalDayIndex = dayOffset + i;
                      const raw = String(val ?? "").trim();
                      const required =
                        raw === "" ? null : Number.isFinite(Number(raw)) ? Number(raw) : null;
                      if (required === null || required === -1) {
                        return (
                          <TableCell
                            key={i}
                            align="center"
                            sx={{
                              borderLeft: !isMonthScoped && isMonthEndIndex(globalDayIndex) ? "2px solid #000" : undefined,
                              borderRight: isMonthScoped && i === dayCount - 1 ? "2px solid #000" : undefined,
                              color: "text.secondary",
                            }}
                          >
                            —
                          </TableCell>
                        );
                      }

                      if (!showDiff) {
                        return (
                          <TableCell
                            key={i}
                            align="center"
                            sx={{
                              borderLeft: !isMonthScoped && isMonthEndIndex(globalDayIndex) ? "2px solid #000" : undefined,
                              borderRight: isMonthScoped && i === dayCount - 1 ? "2px solid #000" : undefined,
                              fontWeight: 500,
                            }}
                          >
                            {required}
                          </TableCell>
                        );
                      }

                      let actual = 0;
                      if (isHourlyFormat && slotKey) {
                        actual =
                          actualCounts.hour.get(`${globalDayIndex + 1}|${slotKey}|${teamCode}`) || 0;
                      } else {
                        actual =
                          actualCounts.shift.get(`${globalDayIndex + 1}|${slotKey}|${teamCode}`) || 0;
                      }
                      const diff = actual - required;
                      const formatted =
                        diff > 0 ? `+${diff}` : diff < 0 ? `-${Math.abs(diff)}` : "0";
                      let cellStyle = {};
                      if (diff === 0) {
                        cellStyle = { backgroundColor: "#dcfce7", color: "#166534" };
                      } else if (diff > 0) {
                        cellStyle = { backgroundColor: "#e0f2fe", color: "#0f172a" };
                      } else {
                        cellStyle = { backgroundColor: "#fee2e2", color: "#9f1239" };
                      }
                      return (
                        <TableCell
                          key={i}
                          align="center"
                          sx={{
                            borderLeft: !isMonthScoped && isMonthEndIndex(globalDayIndex) ? "2px solid #000" : undefined,
                            borderRight: isMonthScoped && i === dayCount - 1 ? "2px solid #000" : undefined,
                            fontWeight: 600,
                            ...cellStyle,
                          }}
                        >
                          {formatted}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default MinimumsTemplate;

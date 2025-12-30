import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";
import LegendBox from "./LegendBox";

const CalendarTable = ({
  data,
  selectedMonth,
  daysInMonth,
  startDay,
  endDay,
  firstDayOfYear,
  holidayMap = {},
  scheduleType,
}) => {
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const normalizedType = String(scheduleType || "").toLowerCase();
  const hourBlockPattern =
    /^\s*\d{1,2}(?:\.\d+)?\s*-\s*\d{1,2}(?:\.\d+)?(?:\s*-\s*\d{1,2}(?:\.\d+)?)?\s*[_-]\s*[A-Za-z]\s*$/;

  const looksHourlyValue = (value) => hourBlockPattern.test(String(value || "").trim());

  const formatHour = (value) => {
    if (!Number.isFinite(value)) return "";
    const hours = Math.floor(value);
    const minutes = Math.round((value - hours) * 60);
    const pad = (num) => String(num).padStart(2, "0");
    return `${pad(hours)}:${pad(minutes)}`;
  };

  const parseHourBlock = (value) => {
    const text = String(value || "").trim();
    const match = text.match(
      /^\s*(\d{1,2}(?:\.\d+)?)\s*-\s*(\d{1,2}(?:\.\d+)?)(?:\s*-\s*(\d{1,2}(?:\.\d+)?))?\s*[_-]\s*([A-Za-z])\s*$/
    );
    if (!match) return null;
    const start = Number(match[1]);
    const mid = Number(match[2]);
    const end = match[3] !== undefined ? Number(match[3]) : null;
    const team = match[4].toUpperCase();
    return { start, mid, end, team };
  };

  const abbreviateValue = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "0") return "";
    if (normalized === "F") return "V"; 
    if (normalized === "VACATION") return "V";
    if (normalized === "OFF") return "";
    if (normalized === "T_A") return "A_A";
    if (normalized === "T_B") return "A_B";
    if (normalized === "T_C") return "A_C";
    return value;
  };

  const getCellStyle = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "0") return { backgroundColor: "#ffffff", color: "#000" };
    if (normalized === "F" || normalized === "VACATION") {
      return { backgroundColor: "#ffcccb", color: "#000" };
    }
    if (normalized.includes("M")) return { backgroundColor: "#f9e79f", color: "#000" }; // Afternoon
    if (normalized.includes("T")) return { backgroundColor: "#d4edda", color: "#000" }; // Morning
    if (normalized.includes("N")) return { backgroundColor: "#9eb3caff", color: "#000" }; // Night
    return {};
  };

  const getDisplayedData = () => {
    const offset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
    const start = offset + startDay;
    const end = offset + endDay + 1;
    return data.map((row) => [row[0], ...row.slice(start, end)]);
  };

  const isFixedHoliday = (month, day) => {
    return holidayMap[month]?.includes(day);
  };

  const displayedData = getDisplayedData();
  const numDays = displayedData[0]?.length - 1 || 0;
  const monthOffset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
  const firstDayOfMonth = (firstDayOfYear + monthOffset) % 7;
  const isHourly =
    normalizedType === "horas" ||
    normalizedType === "hours" ||
    displayedData
      .slice(1, 6)
      .some((row) => row.slice(1, 12).some((cell) => looksHourlyValue(cell)));

  const teamPalette = {
    A: { bg: "#e3f2fd", border: "#90caf9", text: "#0f172a" },
    B: { bg: "#e8f5e9", border: "#a5d6a7", text: "#0f172a" },
    C: { bg: "#fff3e0", border: "#ffcc80", text: "#0f172a" },
    D: { bg: "#fce4ec", border: "#f8bbd0", text: "#0f172a" },
    default: { bg: "#f1f5f9", border: "#cbd5f5", text: "#0f172a" },
  };

  const getHourlyCellStyle = (value) => {
    const normalized = String(value || "").trim().toUpperCase();
    if (!normalized || normalized === "OFF" || normalized === "0") {
      return {
        backgroundColor: "#f5f7fa",
        color: "#64748b",
        border: "1px dashed #cbd5f5",
      };
    }
    if (normalized === "F" || normalized === "VACATION") {
      return {
        backgroundColor: "#ffe5e5",
        color: "#7f1d1d",
        border: "1px solid #fecaca",
      };
    }
    const parsed = parseHourBlock(value);
    const team = parsed?.team || "default";
    const palette = teamPalette[team] || teamPalette.default;
    return {
      backgroundColor: palette.bg,
      color: palette.text,
      border: `1px solid ${palette.border}`,
      boxShadow: "inset 0 0 0 1px rgba(15, 23, 42, 0.04)",
    };
  };

  const renderHourlyCell = (value) => {
    const normalized = String(value || "").trim().toUpperCase();
    if (!normalized || normalized === "OFF" || normalized === "0") {
      return <span style={{ fontSize: "10px", fontWeight: 600 }}>OFF</span>;
    }
    if (normalized === "F" || normalized === "VACATION") {
      return <span style={{ fontSize: "10px", fontWeight: 600 }}>VAC</span>;
    }

    const parsed = parseHourBlock(value);
    if (!parsed) {
      return <span style={{ fontSize: "10px" }}>{value}</span>;
    }

    const segments = [];
    if (parsed.end !== null) {
      segments.push(`${formatHour(parsed.start)}-${formatHour(parsed.mid)}`);
      segments.push(`${formatHour(parsed.mid + 1)}-${formatHour(parsed.end)}`);
    } else {
      segments.push(`${formatHour(parsed.start)}-${formatHour(parsed.mid)}`);
    }

    const palette = teamPalette[parsed.team] || teamPalette.default;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "2px", alignItems: "center" }}>
        {segments.map((segment, index) => (
          <span key={index} style={{ fontSize: "10px", fontWeight: 600 }}>
            {segment}
          </span>
        ))}
        <span
          style={{
            marginTop: "2px",
            padding: "1px 6px",
            borderRadius: "999px",
            fontSize: "9px",
            fontWeight: 700,
            backgroundColor: palette.border,
            color: "#0f172a",
          }}
        >
          Team {parsed.team}
        </span>
      </div>
    );
  };

  const detectedTeams = new Set();
  if (isHourly) {
    displayedData.slice(1).forEach((row) => {
      row.slice(1).forEach((cell) => {
        const parsed = parseHourBlock(cell);
        if (parsed?.team) detectedTeams.add(parsed.team);
      });
    });
  }
  const teamLegends = Array.from(detectedTeams)
    .sort()
    .map((team) => ({
      label: `Team ${team}`,
      color: (teamPalette[team] || teamPalette.default).bg,
    }));

  return (
    <div>
      <TableContainer
        component={Paper}
        style={{
          marginTop: "15px",
          maxWidth: "100%",
          borderRadius: "12px",
          border: isHourly ? "1px solid #e2e8f0" : undefined,
          boxShadow: isHourly ? "0 12px 24px rgba(15, 23, 42, 0.08)" : undefined,
          background: isHourly ? "linear-gradient(180deg, #f8fafc 0%, #ffffff 100%)" : undefined,
        }}
      >
        <Table sx={{ minWidth: 450 }} aria-label="calendar table">
          <TableHead>
            <TableRow style={{ backgroundColor: "#007bff", color: "white" }}>
              <TableCell
                style={{
                  fontSize: "11.5px",
                  padding: "4px",
                  color: "white",
                  whiteSpace: "nowrap",
                  textAlign: "center",
                  verticalAlign: "middle",
                }}
              >
                Employee
              </TableCell>
              {Array.from({ length: numDays }, (_, index) => {
                const currentDay = startDay + index;
                const isHoliday = isFixedHoliday(selectedMonth, currentDay);
                return (
                  <TableCell
                    key={index}
                    style={{
                      fontSize: "11.5px",
                      padding: "4px",
                      whiteSpace: "nowrap",
                      textAlign: "center",
                      verticalAlign: "middle",
                      backgroundColor: isHoliday ? "#800080" : "#007bff",
                      color: isHoliday ? "#fff" : "white",
                      fontWeight: isHoliday ? "bold" : undefined,
                    }}
                  >
                    Day {currentDay}
                  </TableCell>
                );
              })}
            </TableRow>
            <TableRow>
              <TableCell
                style={{
                  fontSize: "11.5px",
                  padding: "4px",
                  backgroundColor: "#6fa8dc",
                  color: "white",
                  whiteSpace: "nowrap",
                  textAlign: "center",
                  verticalAlign: "middle",
                }}
              ></TableCell>
              {Array.from({ length: numDays }, (_, i) => {
                const dayOfWeekIndex = (firstDayOfMonth + startDay + i - 1) % 7;
                const isSunday = dayOfWeekIndex === 0;
                const bgColor = isSunday ? "#b0c4de" : "#6fa8dc";
                return (
                  <TableCell
                    key={i}
                    style={{
                      fontSize: "11.5px",
                      padding: "4px",
                      whiteSpace: "nowrap",
                      textAlign: "center",
                      verticalAlign: "middle",
                      color: "white",
                      backgroundColor: bgColor,
                    }}
                  >
                    {dayNames[dayOfWeekIndex]}
                  </TableCell>
                );
              })}
            </TableRow>
          </TableHead>
          <TableBody>
            {displayedData.slice(1).map((row, rowIndex) => (
              <TableRow key={rowIndex} style={{ height: "30px" }}>
                {row.map((cell, cellIndex) => {
                  const baseStyle = {
                    fontSize: isHourly ? "10px" : "11.5px",
                    padding: isHourly ? "6px 4px" : "4px",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    textAlign: "center",
                    verticalAlign: "middle",
                  };

                  if (cellIndex === 0) {
                    return (
                      <TableCell
                        key={cellIndex}
                        style={{
                          ...baseStyle,
                          fontWeight: "bold",
                          backgroundColor: "#007bff",
                          color: "white",
                        }}
                      >
                        Employee {rowIndex + 1}
                      </TableCell>
                    );
                  }

                  return (
                    <TableCell
                      key={cellIndex}
                      style={{
                        ...baseStyle,
                        backgroundColor: "#ffffff",
                        ...(isHourly ? getHourlyCellStyle(cell || "") : getCellStyle(cell || "")),
                      }}
                      title={isHourly && cell ? String(cell) : undefined}
                    >
                      {isHourly ? renderHourlyCell(cell || "") : abbreviateValue(cell || "")}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <LegendBox scheduleType={scheduleType} teamLegends={teamLegends} />
    </div>
  );
};

export default CalendarTable;

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
}) => {
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const abbreviateValue = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "0") return "";
    if (normalized === "F") return "V"; 
    if (normalized === "T_A") return "A_A";
    if (normalized === "T_B") return "A_B";
    if (normalized === "N_A") return "A_N";
    if (normalized === "N_B") return "A_N";
    return value;
  };

  const getCellStyle = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "0") return { backgroundColor: "#ffffff", color: "#000" };
    if (normalized === "F") return { backgroundColor: "#ffcccb", color: "#000" }; // Vacation
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

  return (
    <div>
      <TableContainer component={Paper} style={{ marginTop: "15px", maxWidth: "100%" }}>
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
                    fontSize: "11.5px",
                    padding: "4px",
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
                        ...getCellStyle(cell || ""),
                      }}
                    >
                      {abbreviateValue(cell || "")}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <LegendBox
        style={{
          marginTop: "1rem",
          padding: "2%",
          borderRadius: "10px",
          display: "flex",
          justifyContent: "flex-start",
          alignItems: "center",
          gap: "20px",
        }}
      />
    </div>
  );
};

export default CalendarTable;

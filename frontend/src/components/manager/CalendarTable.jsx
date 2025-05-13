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

const CalendarTable = ({ data, selectedMonth, daysInMonth, startDay, endDay }) => {
  const dayNames = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

  const abbreviateValue = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "F") return "Fe"; 
    if (normalized === "0") return "";   
    return value;
  };

  const getCellStyle = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "0") return { backgroundColor: "#ffffff", color: "#000" }; 
    if (normalized === "F") return { backgroundColor: "#ffcccb", color: "#000" }; 
    if (["T", "T_A", "T_B"].includes(normalized)) return { backgroundColor: "#f9e79f", color: "#000" }; 
    if (["M", "M_A", "M_B"].includes(normalized)) return { backgroundColor: "#d4edda", color: "#000" }; 
    return {};
  };

  const getDisplayedData = () => {
    const offset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
    const start = offset + startDay;
    const end = offset + endDay + 1;
    return data.map((row) => [row[0], ...row.slice(start, end)]);
  };

  const displayedData = getDisplayedData();
  const numDays = displayedData[0]?.length - 1 || 0;

  const firstDayOfYear = 3;
  const monthOffset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
  const firstDayOfMonth = firstDayOfYear + monthOffset;

  const holidays2025 = [
    { month: 1, day: 1 },   
    { month: 4, day: 18 },  
    { month: 4, day: 20 },  
    { month: 4, day: 25 },  
    { month: 5, day: 1 },   
    { month: 6, day: 10 },  
    { month: 8, day: 15 },  
    { month: 10, day: 5 },  
    { month: 11, day: 1 },  
    { month: 12, day: 1 },  
    { month: 12, day: 8 },  
    { month: 12, day: 25 }, 
  ];

  const isHoliday = (month, day) => holidays2025.some(h => h.month === month && h.day === day);

  return (
    <div>
      <TableContainer component={Paper} style={{ marginTop: "15px", maxWidth: "100%" }}>
        <Table sx={{ minWidth: 450 }} aria-label="calendar table">
          <TableHead>
            <TableRow style={{ backgroundColor: "#007bff" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px", color: "white" }}>Funcionário</TableCell>
              {Array.from({ length: numDays }, (_, i) => {
                const dayNumber = startDay + i;
                const holiday = isHoliday(selectedMonth, dayNumber);
                return (
                  <TableCell
                    key={i}
                    style={{
                      fontSize: "12px",
                      padding: "6px",
                      color: holiday ? "#fff" : "white",
                      backgroundColor: holiday ? "#800080" : "#007bff",
                      fontWeight: holiday ? "bold" : "normal",
                    }}
                  >
                    Dia {dayNumber}
                  </TableCell>
                );
              })}
            </TableRow>

            <TableRow style={{ backgroundColor: "#6fa8dc" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px", color: "white" }}></TableCell>
              {Array.from({ length: numDays }, (_, i) => {
                const absoluteDayIndex = firstDayOfMonth + startDay + i - 1;
                const dayOfWeekIndex = (absoluteDayIndex) % 7; 
                return (
                  <TableCell key={i} style={{ fontSize: "12px", padding: "6px", color: "white" }}>
                    {dayNames[dayOfWeekIndex]}
                  </TableCell>
                );
              })}
            </TableRow>
          </TableHead>

          <TableBody>
            {displayedData.slice(1).map((row, rowIndex) => (
              <TableRow key={rowIndex} style={{ height: "30px" }}>
                {row.map((cell, cellIndex) => (
                  <TableCell
                    key={cellIndex}
                    style={{
                      fontSize: "12px",
                      padding: "6px",
                      backgroundColor:
                        cellIndex === 0
                          ? "#cce5ff"
                          : rowIndex % 2 === 0
                          ? "#ffffff"
                          : "#f1f1f1",
                      ...(cellIndex !== 0 ? getCellStyle(cell || "") : {}),
                      fontWeight: cellIndex === 0 ? "bold" : "normal",
                    }}
                  >
                    {cellIndex === 0 ? `Funcionário ${rowIndex + 1}` : abbreviateValue(cell || "")}
                  </TableCell>
                ))}
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

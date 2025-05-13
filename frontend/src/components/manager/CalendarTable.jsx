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

  const getCellStyle = (value, absoluteDay) => {
    const normalized = value.toUpperCase();

    const holidayDays = [
      1, 47, 88, 90, 115, 126, 157, 176, 226,
      274, 305, 335, 340, 359 // feriados nacionais PT 2025
    ];

    const isHoliday = holidayDays.includes(absoluteDay);

    if (normalized === "0") {
      return { backgroundColor: "#ffffff", color: "#000" };
    }

    if (isHoliday) {
      return { backgroundColor: "#ffe0b2", color: "#000" }; // destaque só na célula do feriado
    }

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

  const firstDayOfYearIndex = 2; // 1 Jan 2025 é Quarta-feira
  const monthOffset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
  const firstDayOfMonth = monthOffset + 1;

  return (
    <div>
      <TableContainer component={Paper} style={{ marginTop: "15px", maxWidth: "100%" }}>
        <Table sx={{ minWidth: 450 }} aria-label="calendar table">
          <TableHead>
            {/* Linha dos dias */}
            <TableRow style={{ backgroundColor: "#007bff" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px", color: "white" }}>Funcionário</TableCell>
              {Array.from({ length: numDays }, (_, i) => (
                <TableCell key={i} style={{ fontSize: "12px", padding: "6px", color: "white" }}>
                  Dia {startDay + i}
                </TableCell>
              ))}
            </TableRow>

            {/* Linha dos dias da semana */}
            <TableRow style={{ backgroundColor: "#6fa8dc" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px", color: "white" }}></TableCell>
              {Array.from({ length: numDays }, (_, i) => {
                const absoluteDay = monthOffset + startDay + i;
                const dayOfWeekIndex = (firstDayOfYearIndex + absoluteDay - 1) % 7;
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
                {row.map((cell, cellIndex) => {
                  const absoluteDay = monthOffset + startDay + cellIndex - 1;
                  return (
                    <TableCell
                      key={cellIndex}
                      style={{
                        fontSize: "12px",
                        padding: "6px",
                        ...(cellIndex === 0
                          ? {
                              backgroundColor: "#cce5ff",
                              fontWeight: "bold",
                            }
                          : {
                              ...getCellStyle(cell || "", absoluteDay),
                              backgroundColor: getCellStyle(cell || "", absoluteDay).backgroundColor || (rowIndex % 2 === 0 ? "#ffffff" : "#f1f1f1"),
                            }),
                      }}
                    >
                      {cellIndex === 0 ? `Funcionário ${rowIndex + 1}` : abbreviateValue(cell || "")}
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

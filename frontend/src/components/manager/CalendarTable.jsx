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

  const abbreviateValue = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "0") return "F"; 
    if (normalized === "F") return "Fe"; 
    if (["T", "TA", "TB"].includes(normalized)) return "T"; 
    if (["M", "MA", "MB"].includes(normalized)) return "M"; 
    return value;
  };

  const getCellStyle = (value) => {
    const normalized = value.toUpperCase();
    if (normalized === "0") return { backgroundColor: "#a0d8ef", color: "#000" }; 
    if (normalized === "F") return { backgroundColor: "#ffcccb", color: "#000" }; 
    if (["T", "TA", "TB"].includes(normalized)) return { backgroundColor: "#f9e79f", color: "#000" };
    if (["M", "MA", "MB"].includes(normalized)) return { backgroundColor: "#d4edda", color: "#000" }; 
    return {};
  };

  const getDisplayedData = () => {
    const offset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
    const start = offset + startDay;
    const end = offset + endDay + 1;
    return data.map((row) => [row[0], ...row.slice(start, end)]);
  };

  return (
    <div>
      <TableContainer component={Paper} style={{ marginTop: "15px", maxWidth: "100%" }}>
        <Table sx={{ minWidth: 450 }} aria-label="calendar table">
          <TableHead>
            <TableRow style={{ backgroundColor: "#007bff", color: "white" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px" }}>Funcionário</TableCell>
              {getDisplayedData()[0]?.slice(1).map((_, index) => (
                <TableCell key={index} style={{ fontSize: "12px", padding: "6px" }}>
                  Dia {startDay + index}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {getDisplayedData().slice(1).map((row, rowIndex) => (
              <TableRow key={rowIndex} style={{ height: "30px" }}>
                {row.map((cell, cellIndex) => (
                  <TableCell
                    key={cellIndex}
                    style={{
                      fontSize: "12px",
                      padding: "6px",
                      backgroundColor: rowIndex % 2 === 0 ? "#ffffff" : "#f1f1f1",
                      ...getCellStyle(cell || ""),
                    }}
                  >
                    {abbreviateValue(cell || "")}
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

import React from "react";
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography } from "@mui/material";

const CalendarTable = ({ data, selectedMonth, daysInMonth }) => {
  const abbreviateValue = (value) => {
    switch (value.toLowerCase()) {
      case "folga":
        return "F";
      case "férias":
        return "Fe";
      case "manhã":
        return "M";
      case "tarde":
        return "T";
      default:
        return value;
    }
  };

  const getCellStyle = (value) => {
    switch (value.toLowerCase()) {
      case "folga":
        return { backgroundColor: "#a0d8ef", color: "#000" };
      case "férias":
        return { backgroundColor: "#ffcccb", color: "#000" };
      case "manhã":
        return { backgroundColor: "#d4edda", color: "#000" };
      case "tarde":
        return { backgroundColor: "#f9e79f", color: "#000" };
      default:
        return {};
    }
  };

  const getDisplayedData = () => {
    const startDay = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0) + 1;
    const endDay = startDay + daysInMonth[selectedMonth - 1] - 1;
    return data.map((row) => [row[0], ...row.slice(startDay, endDay + 1)]);
  };

  return (
    <div>
      <TableContainer component={Paper} style={{ marginTop: "15px", maxWidth: "100%" }}>
        <Table sx={{ minWidth: 450 }} aria-label="simple table">
          <TableHead>
            <TableRow style={{ backgroundColor: "#007bff", color: "white" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px" }}>Funcionário</TableCell>
              {getDisplayedData()[0]?.slice(1).map((_, index) => (
                <TableCell key={index} style={{ fontSize: "12px", padding: "6px" }}>Dia {index + 1}</TableCell>
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

      <div style={{ marginTop: "3rem", padding: "2%", backgroundColor: "#f1f1f1", borderRadius: "10px" }}>
        <Typography variant="body2" style={{ marginBottom: "5px" }}>
          <strong>Legenda:</strong>
        </Typography>
        <Typography variant="body2" style={{ marginBottom: "5px", color: "#a0d8ef" }}>
          <span style={{ fontWeight: "bold" }}>F</span>: Folga
        </Typography>
        <Typography variant="body2" style={{ marginBottom: "5px", color: "#ffcccb" }}>
          <span style={{ fontWeight: "bold" }}>Fe</span>: Férias
        </Typography>
        <Typography variant="body2" style={{ marginBottom: "5px", color: "#d4edda" }}>
          <span style={{ fontWeight: "bold" }}>M</span>: Manhã
        </Typography>
        <Typography variant="body2" style={{ marginBottom: "5px", color: "#f9e79f" }}>
          <span style={{ fontWeight: "bold" }}>T</span>: Tarde
        </Typography>
      </div>
    </div>
  );
};

export default CalendarTable;

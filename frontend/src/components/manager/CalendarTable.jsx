import React from "react";
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from "@mui/material";

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
                <TableCell key={index} style={{ fontSize: "12px", padding: "6px" }}>
                  Dia {index + 1}
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

      <div
        style={{
          marginTop: "1rem",
          padding: "2%",
          // backgroundColor: "#f1f1f1",
          borderRadius: "10px",
          display: "flex",
          justifyContent: "flex-start",
          alignItems: "center",
          gap: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{ fontWeight: "bold", marginRight: "5px" }}>Folga</span> -{" "}
          <span
            style={{
              display: "inline-block",
              width: "25px",
              height: "25px",
              backgroundColor: "#a0d8ef",
            }}
          ></span>
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{ fontWeight: "bold", marginRight: "5px" }}>Férias</span> -{" "}
          <span
            style={{
              display: "inline-block",
              width: "25px",
              height: "25px",
              backgroundColor: "#ffcccb",
            }}
          ></span>
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{ fontWeight: "bold", marginRight: "5px" }}>Manhã</span> -{" "}
          <span
            style={{
              display: "inline-block",
              width: "25px",
              height: "25px",
              backgroundColor: "#d4edda",
            }}
          ></span>
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <span style={{ fontWeight: "bold", marginRight: "5px" }}>Tarde</span> -{" "}
          <span
            style={{
              display: "inline-block",
              width: "25px",
              height: "25px",
              backgroundColor: "#f9e79f",
            }}
          ></span>
        </div>
      </div>
    </div>
  );
};

export default CalendarTable;

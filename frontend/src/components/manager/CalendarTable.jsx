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

const CalendarTable = ({ data, selectedMonth, daysInMonth, startDay, endDay, firstDayOfYear }) => {
  // Prepara os dados exibidos
  const getDisplayedData = () => {
    const offset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
    const start = offset + startDay;
    const end = offset + endDay + 1;
    return data.map((row) => [row[0], ...row.slice(start, end)]);
  };

  const displayedData = getDisplayedData();
  const monthOffset = daysInMonth.slice(0, selectedMonth - 1).reduce((a, b) => a + b, 0);
  // Deslocamento do dia da semana para o primeiro dia mostrado (startDay)
  const baseOffset = (firstDayOfYear + monthOffset + (startDay - 1)) % 7;
  const numDays = (displayedData[0]?.length || 1) - 1;
  const dayNames = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

  // Abrevia valores e estilos de célula
  const abbreviateValue = (value) => {
    const v = (value || "").toUpperCase();
    if (v === "0") return "";
    if (v === "F") return "Fe";
    if (["T", "T_A", "T_B"].includes(v)) return "T";
    if (["M", "M_A", "M_B"].includes(v)) return "M";
    return value;
  };

  const getCellStyle = (value) => {
    const v = (value || "").toUpperCase();
    if (v === "F") return { backgroundColor: "#ffcccb", color: "#000" }; 
    if (["T", "T_A", "T_B"].includes(v)) return { backgroundColor: "#f9e79f", color: "#000" };
    if (["M", "M_A", "M_B"].includes(v)) return { backgroundColor: "#d4edda", color: "#000" };
    return {};
  };

  return (
    <div>
      <TableContainer component={Paper} style={{ marginTop: "15px", maxWidth: "100%" }}>
        <Table sx={{ minWidth: 450 }} aria-label="calendar table">
          <TableHead>
            {/* Cabeçalho com Dia X */}
            <TableRow style={{ backgroundColor: "#007bff" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px", backgroundColor: "#007bff", color: "white" }}>
                Funcionário
              </TableCell>
              {displayedData[0]?.slice(1).map((_, i) => (
                <TableCell key={i} style={{ fontSize: "12px", padding: "6px", backgroundColor: "#007bff", color: "white" }}>
                  Dia {startDay + i}
                </TableCell>
              ))}
            </TableRow>
            {/* Cabeçalho com dias da semana */}
            <TableRow style={{ backgroundColor: "#6fa8dc" }}>
              <TableCell style={{ fontSize: "12px", padding: "6px", backgroundColor: "#6fa8dc", color: "white" }}></TableCell>
              {Array.from({ length: numDays }, (_, i) => (
                <TableCell key={i} style={{ fontSize: "12px", padding: "6px", backgroundColor: "#6fa8dc", color: "white" }}>
                  {dayNames[(baseOffset + i) % 7]}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {displayedData.slice(1).map((row, rowIndex) => (
              <TableRow key={rowIndex} style={{ height: "30px" }}>
                {row.map((cell, cellIndex) => {
                  // Primeira coluna: nomes/índice de Funcionário em azul
                  if (cellIndex === 0) {
                    return (
                      <TableCell
                        key={cellIndex}
                        style={{
                          fontSize: "12px",
                          padding: "6px",
                          fontWeight: "bold",
                          backgroundColor: "#007bff",
                          color: "white",
                        }}
                      >
                        Funcionário {rowIndex + 1}
                      </TableCell>
                    );
                  }

                  // Detecta fim de semana
                  const isWeekend = [0, 6].includes((baseOffset + (cellIndex - 1)) % 7);
                  const bgColor = isWeekend ? "#f0f8ff" : "#ffffff"; // branco para dias úteis

                  return (
                    <TableCell
                      key={cellIndex}
                      style={{
                        fontSize: "12px",
                        padding: "6px",
                        backgroundColor: bgColor,
                        ...getCellStyle(cell),
                      }}
                    >
                      {abbreviateValue(cell)}
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
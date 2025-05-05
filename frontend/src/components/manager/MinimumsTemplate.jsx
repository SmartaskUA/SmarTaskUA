import React from "react";
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
  if (type === "Minimo") return "#e0f7fa";
  if (type === "Ideal") return "#f1f8e9";
  return base;
};

const MinimumsTemplate = ({ name, data }) => {
  if (!data || data.length === 0) return null;

  const teams = [];
  let currentTeam = null;
  data.forEach((row) => {
    const teamName = row[0] || currentTeam;
    if (row[0]) {
      currentTeam = row[0];
      teams.push({ team: currentTeam, rows: [row] });
    } else {
      teams[teams.length - 1]?.rows.push(row);
    }
  });

  const totalDays = data[0].length - 3;
  const dayHeaders = Array.from({ length: totalDays }, (_, i) => `${i + 1}`);

  return (
    <Box mt={4}>
      <Typography variant="h6" gutterBottom>
        Visualização dos Mínimos - Template: {name}
      </Typography>
      <TableContainer component={Paper} sx={{ overflowX: "auto", borderRadius: 2 }}>
        <Table size="small" sx={{ minWidth: 1200 }}>
          <TableHead sx={{ backgroundColor: "#e3f2fd" }}>
            <TableRow>
              <TableCell sx={{ fontWeight: "bold" }}></TableCell>
              <TableCell sx={{ fontWeight: "bold" }}></TableCell>
              <TableCell sx={{ fontWeight: "bold" }}></TableCell>
              {dayHeaders.map((day, i) => (
                <TableCell key={i} align="center" sx={{ fontWeight: "bold" }}>
                  {day}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {teams.map(({ team, rows }, teamIndex) =>
              rows.map((row, rowIndex) => {
                const bgColor = getRowColor(teamIndex * 4 + rowIndex, row[1]);
                return (
                  <TableRow key={`${teamIndex}-${rowIndex}`} sx={{ backgroundColor: bgColor }}>
                    <TableCell>
                      {rowIndex === 0 ? team : ""}
                    </TableCell>
                    <TableCell>{row[1]}</TableCell>
                    <TableCell>{row[2]}</TableCell>
                    {row.slice(3).map((val, i) => (
                      <TableCell key={i} align="center">
                        {val}
                      </TableCell>
                    ))}
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

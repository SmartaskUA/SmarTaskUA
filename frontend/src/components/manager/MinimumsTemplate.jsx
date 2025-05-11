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

const monthLabels = [
  { name: "Janeiro", days: 31 },
  { name: "Fevereiro", days: 28 },
  { name: "Março", days: 31 },
  { name: "Abril", days: 30 },
  { name: "Maio", days: 31 },
  { name: "Junho", days: 30 },
  { name: "Julho", days: 31 },
  { name: "Agosto", days: 31 },
  { name: "Setembro", days: 30 },
  { name: "Outubro", days: 31 },
  { name: "Novembro", days: 30 },
  { name: "Dezembro", days: 31 },
];

const monthBoundaries = monthLabels.reduce((acc, month, idx) => {
  const start = acc.length === 0 ? 0 : acc[idx - 1].end;
  acc.push({ start, end: start + month.days });
  return acc;
}, []);

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

  const getMonthHeader = () => {
    const cells = [
      <TableCell key="empty-1" />, <TableCell key="empty-2" />, <TableCell key="empty-3" />
    ];
    monthLabels.forEach((month, i) => {
      cells.push(
        <TableCell
          key={`month-${i}`}
          align="center"
          colSpan={month.days}
          sx={{
            fontWeight: "bold",
            backgroundColor: "#d3eaf2",
            borderRight: "2px solid #000"
          }}
        >
          {month.name}
        </TableCell>
      );
    });
    return <TableRow>{cells}</TableRow>;
  };

  const getDayNumbersRow = () => {
    const cells = [<TableCell key="empty-1" />, <TableCell key="empty-2" />, <TableCell key="empty-3" />];
    monthLabels.forEach((month) => {
      for (let i = 1; i <= month.days; i++) {
        const isLastDay = i === month.days;
        cells.push(
          <TableCell
            key={`day-${month.name}-${i}`}
            align="center"
            sx={{
              fontWeight: "bold",
              borderRight: isLastDay ? "2px solid #000" : undefined
            }}
          >
            {i}
          </TableCell>
        );
      }
    });
    return <TableRow>{cells}</TableRow>;
  };

  const isMonthEndIndex = (index) => {
    return monthBoundaries.some((boundary) => index === boundary.end - 1);
  };

  return (
    <Box mt={4}>
      <Typography variant="h6" gutterBottom>
        Visualização dos Mínimos - Template: {name}
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
                const bgColor = getRowColor(teamIndex * 4 + rowIndex, row[1]);
                return (
                  <TableRow key={`${teamIndex}-${rowIndex}`} sx={{ backgroundColor: bgColor }}>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>{rowIndex === 0 ? team : ""}</TableCell>
                    <TableCell>{row[1]}</TableCell>
                    <TableCell>{row[2]}</TableCell>
                    {row.slice(3).map((val, i) => (
                      <TableCell
                        key={i}
                        align="center"
                        sx={{
                          borderRight: isMonthEndIndex(i) ? "2px solid #000" : undefined
                        }}
                      >
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

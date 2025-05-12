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

const VacationsTemplate = ({ name, data }) => {
  if (!data || Object.keys(data).length === 0) return null;

  let sampleRow = Object.values(data)[0] || [];
  if (sampleRow.length > 365) sampleRow = sampleRow.slice(0, 365);
  const maxDay = sampleRow.length;

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

  const monthBoundaries = [];
  let cumulative = 0;
  for (let month of monthLabels) {
    if (cumulative >= maxDay) break;
    const days = Math.min(month.days, maxDay - cumulative);
    monthBoundaries.push({ name: month.name, start: cumulative + 1, end: cumulative + days });
    cumulative += days;
  }

  const sortedRows = Object.entries(data)
    .sort(([a], [b]) => {
      const numA = parseInt(a.match(/\d+/)?.[0] || 0);
      const numB = parseInt(b.match(/\d+/)?.[0] || 0);
      return numA - numB;
    })
    .map(([, days], index) => ({ label: index + 1, days: days.slice(0, 365) }));

  const getMonthHeaderCells = () => {
    const cells = [<TableCell key="label" sx={{ border: '1px solid #ddd', fontWeight: 'bold' }}>Meses</TableCell>];
    monthBoundaries.forEach((month) => {
      cells.push(
        <TableCell
          key={month.name}
          align="center"
          colSpan={month.end - month.start + 1}
          sx={{ border: '1px solid #ddd', fontWeight: 'bold', backgroundColor: '#f0f0f0' }}
        >
          {month.name}
        </TableCell>
      );
    });
    return cells;
  };

  const getDayNumberCells = () => {
    const cells = [<TableCell key="label" sx={{ border: '1px solid #ddd', fontWeight: 'bold' }}>Funcionário</TableCell>];
    for (let i = 1; i <= maxDay; i++) {
      cells.push(
        <TableCell
          key={`day-${i}`}
          align="center"
          sx={{ border: '1px solid #ddd', padding: '6px' }}
        >
          {i}
        </TableCell>
      );
    }
    return cells;
  };

  return (
    <Box mt={4}>
      <Typography variant="h6" gutterBottom>
        Visualização das Férias - Template: {name}
      </Typography>
      <TableContainer component={Paper} style={{ overflowX: "auto" }}>
        <Table size="small" sx={{ borderCollapse: 'collapse', tableLayout: 'fixed', minWidth: 1200 }}>
          <colgroup>
            <col style={{ width: '120px' }} />
            {Array.from({ length: maxDay }, (_, i) => (
              <col key={i} style={{ width: '30px' }} />
            ))}
          </colgroup>
          <TableHead>
            <TableRow>{getMonthHeaderCells()}</TableRow>
            <TableRow>{getDayNumberCells()}</TableRow>
          </TableHead>
          <TableBody>
            {sortedRows.map(({ label, days }, index) => (
              <TableRow key={index} sx={{ height: 40 }}>
                <TableCell sx={{ border: '1px solid #ddd', whiteSpace: 'nowrap' }}>{label}</TableCell>
                {days.map((val, i) => (
                  <TableCell
                    key={i}
                    align="center"
                    sx={{
                      border: '1px solid #ddd',
                      backgroundColor: val === 1 || val === '1' ? "#ffcccb" : "#fff",
                      padding: '6px'
                    }}
                  >
                    {val === 1 || val === '1' ? "F" : ""}
                  </TableCell>
                )).slice(1).concat(<TableCell key={-1} />)}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default VacationsTemplate;

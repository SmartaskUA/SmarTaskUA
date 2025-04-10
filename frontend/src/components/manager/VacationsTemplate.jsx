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

  const maxDay = 365;
  const rows = Object.entries(data);

  const getMonthHeaderCells = () => {
    const cells = [<TableCell key="label" sx={{ border: '1px solid #ddd', fontWeight: 'bold' }}>Meses</TableCell>];
    monthLabels.forEach((month) => {
      cells.push(
        <TableCell
          key={month.name}
          align="center"
          colSpan={month.days}
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
    monthLabels.forEach((month) => {
      for (let i = 1; i <= month.days; i++) {
        cells.push(
          <TableCell
            key={`${month.name}-${i}`}
            align="center"
            sx={{ border: '1px solid #ddd', padding: '6px' }}
          >
            {i}
          </TableCell>
        );
      }
    });
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
            {[...Array(maxDay).keys()].map((_, i) => (
              <col key={i} style={{ width: '30px' }} />
            ))}
          </colgroup>
          <TableHead>
            <TableRow>{getMonthHeaderCells()}</TableRow>
            <TableRow>{getDayNumberCells()}</TableRow>
          </TableHead>
          <TableBody>
            {rows.map(([employee, days]) => (
              <TableRow key={employee} sx={{ height: 40 }}>
                <TableCell sx={{ border: '1px solid #ddd', whiteSpace: 'nowrap' }}>{employee}</TableCell>
                {[...Array(maxDay).keys()].map((i) => (
                  <TableCell
                    key={i}
                    align="center"
                    sx={{
                      border: '1px solid #ddd',
                      backgroundColor: days.includes((i + 1).toString()) ? "#ffcccb" : "#fff",
                      padding: '6px'
                    }}
                  >
                    {days.includes((i + 1).toString()) ? "F" : ""}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default VacationsTemplate;

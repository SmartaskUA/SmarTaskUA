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

const isLeapYear = (year) => {
  if (!year) return false;
  return (year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0);
};

const VacationsTemplate = ({ name, data, year }) => {
  if (!data || Object.keys(data).length === 0) return null;

  const febDays = isLeapYear(year) ? 29 : 28;

  const monthLabels = [
    { name: "Janeiro", days: 31 },
    { name: "Fevereiro", days: febDays },
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

  let sampleRow = Object.values(data)[0] || [];
  if (sampleRow.length > 365) sampleRow = sampleRow.slice(0, 365);
  const maxDay = sampleRow.length;

  const months = [];
  let daysCounted = 0;
  for (const month of monthLabels) {
    if (daysCounted >= maxDay) break;
    const daysThisMonth = Math.min(month.days, maxDay - daysCounted);
    months.push({ ...month, days: daysThisMonth });
    daysCounted += daysThisMonth;
  }

  const monthBoundaries = months.reduce((acc, month, idx) => {
    const start = acc.length === 0 ? 0 : acc[idx - 1].end;
    acc.push({ start, end: start + month.days });
    return acc;
  }, []);

  const isMonthEndIndex = (index) => {
    return monthBoundaries.some((b) => index === b.end - 1);
  };

  const sortedRows = Object.entries(data)
    .sort(([a], [b]) => {
      const numA = parseInt(a.match(/\d+/)?.[0] || 0);
      const numB = parseInt(b.match(/\d+/)?.[0] || 0);
      return numA - numB;
    })
    .map(([, days], index) => ({ label: index + 1, days: days.slice(0, maxDay) }));

  const getMonthHeaderCells = () => {
    return months.map((month) => (
      <TableCell
        key={month.name}
        align="center"
        colSpan={month.days}
        sx={{
          backgroundColor: "#ffe5d0",
          fontWeight: "bold",
          borderRight: "2px solid #000",
          padding: "8px 0",
          userSelect: "none",
          fontSize: "0.875rem",
        }}
      >
        {month.name}
      </TableCell>
    ));
  };

  const getDayNumberCells = () => {
    const cells = [];
    months.forEach((month) => {
      for (let day = 1; day <= month.days; day++) {
        const isLastDay = day === month.days;
        cells.push(
          <TableCell
            key={`${month.name}-${day}`}
            align="center"
            sx={{
              fontWeight: "bold",
              fontSize: "0.75rem",
              borderRight: isLastDay ? "2px solid #000" : undefined,
              borderBottom: "1px solid #ccc",
              borderTop: "1px solid #ccc",
              padding: "4px 6px",
              color: "#555",
              userSelect: "none",
            }}
          >
            {day}
          </TableCell>
        );
      }
    });
    return cells;
  };

  return (
    <Box mt={4} style={{ paddingRight: "6%" }}>
      <Typography variant="h6" gutterBottom>
        Visualização das Férias - Template: {name}
      </Typography>
      <TableContainer component={Paper} sx={{ overflowX: "auto", borderRadius: 2 }}>
        <Table
          size="small"
          sx={{
            borderCollapse: "collapse",
            minWidth: 1200,
          }}
        >
          <colgroup>
            <col style={{ width: "120px" }} />
            {Array.from({ length: maxDay }, (_, i) => (
              <col key={i} style={{ width: "30px" }} />
            ))}
          </colgroup>
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  backgroundColor: "#ffe5d0",
                  borderBottom: "none",
                  padding: 0,
                  margin: 0,
                  width: "120px",
                  userSelect: "none",
                }}
              />
              {getMonthHeaderCells()}
            </TableRow>
            <TableRow>
              <TableCell
                sx={{
                  fontWeight: "bold",
                  padding: "6px 12px",
                  whiteSpace: "nowrap",
                  backgroundColor: "#fff",
                  borderBottom: "1px solid #ccc", // adicionada borda inferior leve
                  borderTop: "1px solid #ccc",    // adicionada borda superior leve
                }}
              >
                Funcionário
              </TableCell>
              {getDayNumberCells()}
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedRows.map(({ label, days }, index) => {
              const rowBg = index % 2 === 0 ? "#ffffff" : "#f9f9f9";
              return (
                <TableRow
                  key={index}
                  sx={{ backgroundColor: rowBg }}
                >
                  <TableCell
                    sx={{
                      whiteSpace: "nowrap",
                      fontWeight: "bold",
                      backgroundColor: rowBg,
                    }}
                  >
                    {label}
                  </TableCell>
                  {days.map((val, i) => (
                    <TableCell
                      key={i}
                      align="center"
                      sx={{
                        backgroundColor:
                          val === 1 || val === "1" ? "#fde2e2" : rowBg,
                        color: val === 1 || val === "1" ? "#000" : "inherit",
                        fontWeight: val === 1 || val === "1" ? "600" : "normal",
                        borderRight: isMonthEndIndex(i) ? "2px solid #000" : undefined,
                      }}
                    >
                      {val === 1 || val === "1" ? "F" : ""}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default VacationsTemplate;

import React, { useMemo } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography
} from '@mui/material';
import { styled } from '@mui/material/styles';
import MatrixCell from './MatrixCell';
import { formatDateHeader, isWeekend } from '../../utils/helpers/dateHelpers';

const StyledTableContainer = styled(TableContainer)(({ theme }) => ({
  maxHeight: '60vh',
  overflow: 'auto',
  '& .MuiTable-root': {
    borderCollapse: 'separate',
    borderSpacing: 0
  }
}));

const StickyHeaderCell = styled(TableCell)(({ theme, isweekend }) => ({
  position: 'sticky',
  top: 0,
  zIndex: 3,
  backgroundColor: theme.palette.background.paper,
  borderBottom: `2px solid ${theme.palette.divider}`,
  borderRight: `1px solid ${theme.palette.divider}`,
  padding: '8px',
  minWidth: '100px',
  textAlign: 'center',
  fontWeight: 600,
  fontSize: '12px',
  ...(isweekend === 'true' && {
    backgroundColor: '#fafafa'
  })
}));

const StickyFirstCell = styled(TableCell)(({ theme }) => ({
  position: 'sticky',
  left: 0,
  zIndex: 4,
  backgroundColor: theme.palette.background.paper,
  borderRight: `2px solid ${theme.palette.divider}`,
  fontWeight: 600,
  padding: '8px 16px',
  minWidth: '120px'
}));

const StickyCornerCell = styled(TableCell)(({ theme }) => ({
  position: 'sticky',
  top: 0,
  left: 0,
  zIndex: 5,
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
  borderBottom: `2px solid ${theme.palette.divider}`,
  borderRight: `2px solid ${theme.palette.divider}`,
  fontWeight: 700,
  padding: '8px 16px',
  minWidth: '120px'
}));

const StyledTableRow = styled(TableRow)(({ theme }) => ({
  '&:nth-of-type(even)': {
    backgroundColor: theme.palette.action.hover
  },
  '&:hover': {
    backgroundColor: theme.palette.action.selected
  }
}));

/**
 * ScheduleMatrix - Main matrix grid for schedule input
 *
 * Displays employees as rows and dates as columns with dropdown cells
 */
const ScheduleMatrix = ({
  employees,
  dateRange,
  dataMatrix,
  contracts,
  onChange,
  employeeModel
}) => {
  // Generate dates if not provided
  const dates = useMemo(() => {
    if (dateRange && dateRange.length > 0) {
      return dateRange;
    }
    return [];
  }, [dateRange]);

  // Get cell value from dataMatrix
  const getCellValue = (employeeId, date) => {
    return dataMatrix?.[employeeId]?.[date] || '';
  };

  // Handle cell change
  const handleCellChange = (employeeId, date, value) => {
    onChange(employeeId, date, value);
  };

  // If no data, show empty state
  if (employees.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body1" color="text.secondary">
          No employees defined. Please go back to Step 4 and add employees.
        </Typography>
      </Box>
    );
  }

  if (dates.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body1" color="text.secondary">
          No date range defined. Please go back to Step 1 and set the temporal scope.
        </Typography>
      </Box>
    );
  }

  return (
    <StyledTableContainer component={Paper} elevation={1}>
      <Table stickyHeader size="small">
        <TableHead>
          <TableRow>
            {/* Top-left corner cell */}
            <StickyCornerCell>
              Employee ID
            </StickyCornerCell>

            {/* Date header cells */}
            {dates.map((date) => (
              <StickyHeaderCell
                key={date}
                isweekend={isWeekend(date) ? 'true' : 'false'}
              >
                <Box>
                  {formatDateHeader(date)}
                </Box>
                <Box sx={{ fontSize: '10px', opacity: 0.7, mt: 0.5 }}>
                  {date.split('-')[2]}
                </Box>
              </StickyHeaderCell>
            ))}
          </TableRow>
        </TableHead>

        <TableBody>
          {employees.map((employee) => (
            <StyledTableRow key={employee.id}>
              {/* Employee ID cell (sticky first column) */}
              <StickyFirstCell>
                <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                  <Typography variant="body2" fontWeight={600}>
                    {employee.id}
                  </Typography>
                  {employee.name && (
                    <Typography variant="caption" color="text.secondary">
                      {employee.name}
                    </Typography>
                  )}
                </Box>
              </StickyFirstCell>

              {/* Date cells */}
              {dates.map((date) => (
                <TableCell
                  key={`${employee.id}-${date}`}
                  sx={{
                    padding: 0,
                    borderRight: '1px solid #e0e0e0',
                    ...(isWeekend(date) && {
                      backgroundColor: '#fafafa'
                    })
                  }}
                >
                  <MatrixCell
                    value={getCellValue(employee.id, date)}
                    onChange={handleCellChange}
                    employeeId={employee.id}
                    date={date}
                    employee={employee}
                    contracts={contracts}
                  />
                </TableCell>
              ))}
            </StyledTableRow>
          ))}
        </TableBody>
      </Table>
    </StyledTableContainer>
  );
};

export default ScheduleMatrix;

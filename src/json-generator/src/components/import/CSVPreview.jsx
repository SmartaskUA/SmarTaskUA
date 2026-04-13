import React from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip
} from '@mui/material';

/**
 * CSVPreview Component
 *
 * Displays a preview of CSV data in a table format.
 * Shows first N rows (default: 10) with column headers.
 */
const CSVPreview = ({ data, maxRows = 10 }) => {
  if (!data || !data.columns || !data.rows || data.rows.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">
          No data to preview
        </Typography>
      </Box>
    );
  }

  const { columns, rows } = data;
  const previewRows = rows.slice(0, maxRows);
  const hasMore = rows.length > maxRows;

  return (
    <Box>
      {/* Info Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          CSV Preview
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Chip
            label={`${rows.length} row${rows.length !== 1 ? 's' : ''}`}
            size="small"
            color="primary"
          />
          <Chip
            label={`${columns.length} column${columns.length !== 1 ? 's' : ''}`}
            size="small"
          />
        </Box>
      </Box>

      {/* Table */}
      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ bgcolor: 'action.hover', fontWeight: 600 }}>
                #
              </TableCell>
              {columns.map((col, idx) => (
                <TableCell key={idx} sx={{ bgcolor: 'action.hover', fontWeight: 600 }}>
                  {col}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {previewRows.map((row, rowIdx) => (
              <TableRow key={rowIdx} hover>
                <TableCell sx={{ color: 'text.secondary', fontWeight: 500 }}>
                  {rowIdx + 1}
                </TableCell>
                {columns.map((col, colIdx) => (
                  <TableCell key={colIdx}>
                    {row[col] !== undefined && row[col] !== null ? String(row[col]) : '-'}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* More Rows Indicator */}
      {hasMore && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Showing first {maxRows} of {rows.length} rows
        </Typography>
      )}
    </Box>
  );
};

export default CSVPreview;

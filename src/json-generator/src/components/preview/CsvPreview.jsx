import React, { useMemo } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Box,
  Paper
} from '@mui/material';
import Papa from 'papaparse';

/**
 * CSV Preview Component
 *
 * Displays CSV data as a table with:
 * - Table view (first 50 rows)
 * - Row and column counts
 * - Sticky headers
 * - Scrollable container
 */
const CsvPreview = ({ csv, filename }) => {
  const parsed = useMemo(() => {
    if (!csv) {
      return { data: [], meta: { fields: [] } };
    }
    return Papa.parse(csv, { header: true, skipEmptyLines: true });
  }, [csv]);

  const { data, meta } = parsed;
  const displayRows = data.slice(0, 50);
  const truncated = data.length > 50;

  if (data.length === 0) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          No data to display
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
        {data.length} rows • {meta.fields?.length || 0} columns
        {truncated && ` (showing first 50 rows)`}
      </Typography>

      <TableContainer
        component={Paper}
        sx={{
          maxHeight: 400,
          border: 1,
          borderColor: 'divider',
          borderRadius: 1
        }}
      >
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {meta.fields?.map((field, index) => (
                <TableCell
                  key={`${field}-${index}`}
                  sx={{
                    fontWeight: 'bold',
                    backgroundColor: 'grey.100',
                    whiteSpace: 'nowrap',
                    fontSize: 12
                  }}
                >
                  {field}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {displayRows.map((row, rowIndex) => (
              <TableRow key={rowIndex} hover>
                {meta.fields?.map((field, colIndex) => (
                  <TableCell
                    key={`${rowIndex}-${colIndex}`}
                    sx={{
                      whiteSpace: 'nowrap',
                      fontSize: 11,
                      py: 0.5
                    }}
                  >
                    {row[field] || ''}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {truncated && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
          ℹ️ Only showing first 50 rows. Download the file to view all {data.length} rows.
        </Typography>
      )}
    </Box>
  );
};

export default CsvPreview;

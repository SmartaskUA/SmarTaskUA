import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Alert,
  Typography,
  Box,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Paper
} from '@mui/material';

/**
 * ImportPreviewModal - Reusable confirmation dialog for CSV imports
 *
 * Props:
 *   open      - boolean
 *   title     - string, e.g. "Import Preview — 12 employees"
 *   summary   - string, e.g. "2 new, 1 updated, 0 skipped"
 *   warnings  - string[], one Alert per entry
 *   rows      - object[], data rows for preview table
 *   columns   - { field: string, label: string }[], table column definitions
 *   onConfirm - () => void
 *   onCancel  - () => void
 */
const ImportPreviewModal = ({
  open,
  title = 'Import Preview',
  summary,
  warnings = [],
  rows = [],
  columns = [],
  onConfirm,
  onCancel
}) => {
  const previewRows = rows.slice(0, 10);
  const hasMore = rows.length > 10;

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="md" fullWidth>
      <DialogTitle>{title}</DialogTitle>

      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 0.5 }}>
          {warnings.map((warning, i) => (
            <Alert key={i} severity="warning" sx={{ py: 0.5 }}>
              {warning}
            </Alert>
          ))}

          {summary && (
            <Typography variant="body2" color="text.secondary">
              {summary}
            </Typography>
          )}

          {columns.length > 0 && previewRows.length > 0 && (
            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 300 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    {columns.map(col => (
                      <TableCell
                        key={col.field}
                        sx={{ fontWeight: 700, whiteSpace: 'nowrap', backgroundColor: '#f5f5f5' }}
                      >
                        {col.label}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {previewRows.map((row, i) => (
                    <TableRow key={i} hover>
                      {columns.map(col => (
                        <TableCell key={col.field} sx={{ whiteSpace: 'nowrap' }}>
                          {row[col.field] ?? '—'}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {hasMore && (
            <Typography variant="caption" color="text.secondary">
              Showing first 10 of {rows.length} rows
            </Typography>
          )}

          {rows.length === 0 && warnings.length === 0 && (
            <Alert severity="info">No data to import.</Alert>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={onCancel} color="inherit" variant="outlined">
          Cancel
        </Button>
        <Button onClick={onConfirm} variant="contained" disabled={rows.length === 0 && warnings.length === 0}>
          Confirm Import
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ImportPreviewModal;

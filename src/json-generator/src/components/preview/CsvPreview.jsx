import React, { useMemo } from 'react';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Box, Paper } from '@mui/material';
import { readRows } from '../../v4/core';

const SHOWN = 100;

/** A generated CSV as a table. A header-only file is shown as such — v4 requires every grain's file. */
const CsvPreview = ({ csv }) => {
  const { header, rows } = useMemo(() => readRows(csv || ''), [csv]);
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
        {rows.length ? `${rows.length} row(s) · ${header.length} columns${rows.length > SHOWN ? ` (first ${SHOWN} shown)` : ''}` : 'Header only — no rows'}
        {' · UTF-8, LF line endings, no BOM'}
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 420 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {header.map((f, i) => (
                <TableCell key={`${f}-${i}`} sx={{ fontWeight: 700, bgcolor: 'grey.100', whiteSpace: 'nowrap', fontSize: 12, fontFamily: 'monospace' }}>{f}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.slice(0, SHOWN).map((row, r) => (
              <TableRow key={r} hover>
                {header.map((f, c) => (
                  <TableCell key={c} sx={{ whiteSpace: 'nowrap', fontSize: 11, py: 0.5, fontFamily: 'monospace' }}>{row[f]}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default CsvPreview;

import React, { useMemo, useState } from 'react';
import {
  Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, IconButton, Chip,
  Typography, TextField, InputAdornment, Stack
} from '@mui/material';
import { Edit, Delete, Search } from '@mui/icons-material';
import { pairLabel } from '../../v4/state';
import { getTeamColor } from '../../utils/helpers/colorHelpers';

/** A range label, or '' when the assignment spans the whole horizon. */
const range = (a, scope) => {
  const coversStart = !scope.start || a.start <= scope.start;
  const coversEnd = !a.end || (scope.end && a.end >= scope.end);
  if (coversStart && coversEnd) return '';
  return a.end ? ` ${a.start}→${a.end}` : ` from ${a.start}`;
};

/** The roster: contract periods and competencies as chips, filterable by any text. */
const EmployeeTable = ({ employees, scope, onEdit, onDelete }) => {
  const [query, setQuery] = useState('');
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return employees;
    return employees.filter((e) => [e.id, e.name, ...(e.contractAssignments || []).map((a) => a.contractType),
      ...(e.competencyAssignments || []).map((a) => pairLabel(a.tableName, a.tableValue))]
      .some((t) => String(t || '').toLowerCase().includes(q)));
  }, [employees, query]);

  return (
    <Box>
      <TextField
        size="small"
        placeholder="Filter by id, name, contract or dimension"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ mb: 1, width: 360 }}
        InputProps={{ startAdornment: <InputAdornment position="start"><Search fontSize="small" /></InputAdornment> }}
      />
      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Contract</TableCell>
              <TableCell>Competencies (level 1 = highest)</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {shown.map((e) => (
              <TableRow key={e.id} hover>
                <TableCell sx={{ fontWeight: 600 }}>{e.id}</TableCell>
                <TableCell>{e.name}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                    {(e.contractAssignments || []).map((a, i) => (
                      <Chip key={i} size="small" variant="outlined" label={`${a.contractType}${range(a, scope)}`} />
                    ))}
                  </Stack>
                </TableCell>
                <TableCell>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                    {(e.competencyAssignments || []).map((a, i) => (
                      <Chip
                        key={i}
                        size="small"
                        label={`${pairLabel(a.tableName, a.tableValue)} · L${a.level}${range(a, scope)}`}
                        sx={{ bgcolor: getTeamColor(pairLabel(a.tableName, a.tableValue)), color: '#fff' }}
                      />
                    ))}
                    {!(e.competencyAssignments || []).length && <Typography variant="caption" color="warning.main">none</Typography>}
                  </Stack>
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                  <IconButton size="small" onClick={() => onEdit(e)}><Edit fontSize="small" /></IconButton>
                  <IconButton size="small" color="error" onClick={() => onDelete(e)}><Delete fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {query && <Typography variant="caption" color="text.secondary">{shown.length} of {employees.length} shown</Typography>}
    </Box>
  );
};

export default EmployeeTable;

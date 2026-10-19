import React from 'react';
import {
  Alert, AlertTitle, Box, Button, FormControlLabel, Paper, Radio, RadioGroup, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Typography
} from '@mui/material';
import { minToHhmm } from '../../v4/core';

/** A menu row as people read it: its window (or that it is a rest), then its paid minutes and description. */
const Definition = ({ row }) => {
  const rest = row.startMin === null || row.startMin === undefined;
  return (
    <>
      <Typography variant="body2" fontWeight={600} sx={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
        {rest ? 'rest' : `${minToHhmm(row.startMin)}–${minToHhmm(row.endMin)}`}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {row.scheduleWeightMinutes} min · &ldquo;{row.description}&rdquo;
      </Typography>
    </>
  );
};

/**
 * The codes the problem's menu and the result's sidecar define differently,
 * one row each, with the user's choice of what to keep: the menu's
 * definition, the result's, or both (the result's under a new code, which its
 * fixed days move to). Nothing is chosen for the user.
 */
const MenuConflictChooser = ({ conflicts, menuFile, sidecarFile, choices, onChange }) => {
  const chosen = conflicts.filter((c) => choices[c.code]).length;
  const all = (choice) => onChange(Object.fromEntries(conflicts.map((c) => [c.code, choice])));
  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2, borderColor: 'warning.main' }}>
      <Alert severity="warning" sx={{ mb: 2 }}>
        <AlertTitle>{menuFile} and {sidecarFile} define {conflicts.length} code(s) differently</AlertTitle>
        Choose what to keep for each. <strong>Both</strong> keeps the menu&apos;s definition and adds the result&apos;s
        under a new code, moving the fixed days that use it there, so they keep the shift they were fixed with.
      </Alert>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5, alignItems: 'center' }}>
        <Typography variant="body2" sx={{ mr: 1 }}>For all:</Typography>
        <Button size="small" variant="outlined" onClick={() => all('menu')}>{menuFile}</Button>
        <Button size="small" variant="outlined" onClick={() => all('result')}>{sidecarFile}</Button>
        <Button size="small" variant="outlined" onClick={() => all('both')}>both</Button>
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="body2" color={chosen === conflicts.length ? 'success.main' : 'warning.dark'}>
          {chosen} of {conflicts.length} chosen
        </Typography>
      </Stack>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>code</TableCell>
              <TableCell>{menuFile}</TableCell>
              <TableCell>{sidecarFile}</TableCell>
              <TableCell align="right">fixed days</TableCell>
              <TableCell>keep</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {conflicts.map((c) => (
              <TableRow key={c.code}>
                <TableCell sx={{ fontWeight: 600 }}>{c.code}</TableCell>
                <TableCell><Definition row={c.menu} /></TableCell>
                <TableCell><Definition row={c.result} /></TableCell>
                <TableCell align="right">{c.fixedDays}</TableCell>
                <TableCell>
                  <RadioGroup
                    aria-label={`keep for ScheduleCode ${c.code}`}
                    value={choices[c.code] ?? ''}
                    onChange={(e) => onChange({ ...choices, [c.code]: e.target.value })}
                  >
                    <FormControlLabel value="menu" control={<Radio size="small" sx={{ py: 0.25 }} />} label="menu's" />
                    <FormControlLabel value="result" control={<Radio size="small" sx={{ py: 0.25 }} />} label="result's" />
                    <FormControlLabel value="both" control={<Radio size="small" sx={{ py: 0.25 }} />} label="both" />
                  </RadioGroup>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default MenuConflictChooser;

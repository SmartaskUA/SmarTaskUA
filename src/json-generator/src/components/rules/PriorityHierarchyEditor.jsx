import React from 'react';
import {
  Box, Typography, Table, TableHead, TableRow, TableCell, TableBody, IconButton, TextField, MenuItem, Button,
  Autocomplete, Alert, Tooltip
} from '@mui/material';
import { ArrowUpward, ArrowDownward, Delete, Add, PlaylistAdd } from '@mui/icons-material';
import { NumberField } from '../shared/fields';
import { GENERATION_SEQUENCE_SUGGESTIONS, MAX_ALARM_TABLE_TYPE_SUGGESTIONS, PRIORITY_DEFAULTS } from '../../v4/constants';
import { pairKey } from '../../v4/core';
import { pairLabel } from '../../v4/state';

const reRank = (entries) => entries.map((e, i) => ({ ...e, rank: i + 1 }));

const Suggest = ({ value, options, onChange, width = 170 }) => (
  <Autocomplete
    freeSolo
    options={options}
    value={value || ''}
    inputValue={value || ''}
    onInputChange={(_, v) => onChange(v)}
    renderInput={(params) => <TextField {...params} size="small" sx={{ width }} />}
  />
);

/**
 * priorityHierarchy: fill order plus the alarm-table settings that drive it.
 * Lower rank fills first; rank follows the list order here, so moving an entry
 * renumbers them all and ranks stay unique.
 */
const PriorityHierarchyEditor = ({ entries, dimensions, onChange }) => {
  const set = (i, patch) => onChange(entries.map((e, j) => (j === i ? { ...e, ...patch } : e)));
  const move = (i, delta) => {
    const next = [...entries];
    [next[i], next[i + delta]] = [next[i + delta], next[i]];
    onChange(reRank(next));
  };
  const entryFor = (d, label = '') => ({ rank: 0, label, tableName: d.tableName, tableValue: d.tableValue, ...PRIORITY_DEFAULTS });
  const listed = new Set(entries.map((e) => pairKey(e.tableName, e.tableValue)));
  const unlisted = dimensions.filter((d) => !listed.has(pairKey(d.tableName, d.tableValue)));
  const ranksOutOfOrder = entries.some((e, i) => Number(e.rank) !== i + 1);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
        <Box>
          <Typography variant="h6" fontWeight={600}>Priority hierarchy</Typography>
          <Typography variant="body2" color="text.secondary">
            Optional. A nine-field projection of SISQUAL&apos;s InpGenerationRules. Ability levels count down from
            1, the most senior — so the minimum level is the <em>smaller</em> number.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
          <Button size="small" startIcon={<Add />} disabled={!unlisted.length}
            onClick={() => onChange(reRank([...entries, entryFor(unlisted[0])]))}
          >
            Add rank
          </Button>
          <Tooltip title="One rank per declared dimension not listed yet">
            <span>
              <Button size="small" startIcon={<PlaylistAdd />} disabled={!unlisted.length}
                onClick={() => onChange(reRank([...entries, ...unlisted.map((d) => entryFor(d, d.tableName.toUpperCase()))]))}
              >
                Add all
              </Button>
            </span>
          </Tooltip>
        </Box>
      </Box>
      {ranksOutOfOrder && (
        <Alert severity="info" sx={{ mb: 1 }} action={<Button size="small" onClick={() => onChange(reRank(entries))}>Renumber</Button>}>
          The imported ranks are not 1..{entries.length} in list order. Ordering follows rank, not position.
        </Alert>
      )}
      {entries.length > 0 && (
        <Box sx={{ overflowX: 'auto' }}>
          <Table size="small" sx={{ '& td, & th': { px: 1 } }}>
            <TableHead>
              <TableRow>
                <TableCell>rank</TableCell>
                <TableCell>dimension</TableCell>
                <TableCell>label</TableCell>
                <TableCell>maxAlarmTableType</TableCell>
                <TableCell>generationSequenceType</TableCell>
                <TableCell>min level</TableCell>
                <TableCell>max level</TableCell>
                <TableCell>alarm %</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {entries.map((e, i) => {
                const levelsBad = Number(e.minAbilityLevel) > Number(e.maxAbilityLevel);
                return (
                  <TableRow key={i}>
                    <TableCell sx={{ fontWeight: 700 }}>{e.rank}</TableCell>
                    <TableCell>
                      <TextField select size="small" value={pairKey(e.tableName, e.tableValue)} sx={{ minWidth: 170 }}
                        onChange={(ev) => {
                          const d = dimensions.find((x) => pairKey(x.tableName, x.tableValue) === ev.target.value);
                          set(i, { tableName: d.tableName, tableValue: d.tableValue });
                        }}
                        error={!dimensions.some((d) => d.tableName === e.tableName && d.tableValue === e.tableValue)}
                      >
                        {dimensions.map((d) => <MenuItem key={pairKey(d.tableName, d.tableValue)} value={pairKey(d.tableName, d.tableValue)}>{pairLabel(d.tableName, d.tableValue)}</MenuItem>)}
                        {!dimensions.some((d) => d.tableName === e.tableName && d.tableValue === e.tableValue) && (
                          <MenuItem value={pairKey(e.tableName, e.tableValue)}>{pairLabel(e.tableName, e.tableValue)} (not declared)</MenuItem>
                        )}
                      </TextField>
                    </TableCell>
                    <TableCell><TextField size="small" value={e.label || ''} onChange={(ev) => set(i, { label: ev.target.value })} sx={{ width: 180 }} /></TableCell>
                    <TableCell><Suggest value={e.maxAlarmTableType} options={MAX_ALARM_TABLE_TYPE_SUGGESTIONS} onChange={(v) => set(i, { maxAlarmTableType: v })} width={290} /></TableCell>
                    <TableCell><Suggest value={e.generationSequenceType} options={GENERATION_SEQUENCE_SUGGESTIONS} onChange={(v) => set(i, { generationSequenceType: v })} width={200} /></TableCell>
                    <TableCell><NumberField value={e.minAbilityLevel} min={1} step={1} error={levelsBad} onChange={(v) => set(i, { minAbilityLevel: v })} sx={{ width: 72 }} /></TableCell>
                    <TableCell><NumberField value={e.maxAbilityLevel} min={1} step={1} error={levelsBad} onChange={(v) => set(i, { maxAbilityLevel: v })} sx={{ width: 72 }} /></TableCell>
                    <TableCell><NumberField value={e.alarmLevelPercentage} min={0} onChange={(v) => set(i, { alarmLevelPercentage: v })} sx={{ width: 72 }} /></TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <IconButton size="small" disabled={i === 0} onClick={() => move(i, -1)}><ArrowUpward fontSize="small" /></IconButton>
                      <IconButton size="small" disabled={i === entries.length - 1} onClick={() => move(i, 1)}><ArrowDownward fontSize="small" /></IconButton>
                      <IconButton size="small" color="error" onClick={() => onChange(reRank(entries.filter((_, j) => j !== i)))}><Delete fontSize="small" /></IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      )}
    </Box>
  );
};

export default PriorityHierarchyEditor;

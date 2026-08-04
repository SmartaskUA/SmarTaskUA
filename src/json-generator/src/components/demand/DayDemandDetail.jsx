import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  TextField,
  Typography,
  Box,
  Chip
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Add as AddIcon
} from '@mui/icons-material';
import AddDemandEntryDialog from './AddDemandEntryDialog';
import {
  getWorkPeriodTimeRange,
  isTimeOverride,
  validateOverrideTime
} from '../../utils/helpers/demandTimeHelpers';

/**
 * DayDemandDetail Component
 *
 * Modal showing detailed breakdown of demand for a specific date
 * - Lists all work periods with team coverage
 * - Inline editing capability
 * - Add/delete entries
 *
 * @param {boolean} open - Whether modal is open
 * @param {Function} onClose - Called when modal should close
 * @param {string} date - ISO date string
 * @param {Array} demandEntries - Demand entries for this date
 * @param {Function} onUpdate - Called when an entry is updated
 * @param {Function} onDelete - Called when an entry is deleted
 * @param {string} employeeModel - 'team' or 'competency'
 */
const DayDemandDetail = ({
  open,
  onClose,
  date,
  demandEntries = [],
  onUpdate,
  onDelete,
  onAdd,
  workPeriods = [],
  teams = [],
  workPeriodModel = 'fixed',
  employeeModel = 'team'
}) => {
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  const handleStartEdit = (entry) => {
    setEditingId(entry.date + entry.workPeriod + entry[employeeModel === 'team' ? 'team' : 'competency']);
    const effective = entry.timeRange || getWorkPeriodTimeRange(workPeriods, entry.workPeriod) || { start: '', end: '' };
    setEditValues({
      minimum: entry.minimum,
      ideal: entry.ideal,
      estimated: entry.estimated,
      start: effective.start || '',
      end: effective.end || ''
    });
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditValues({});
  };

  const handleSaveEdit = (entry) => {
    const validation = validateCoverage(editValues);
    if (!validation.valid) {
      alert(validation.error);
      return;
    }

    const timeRange = { start: editValues.start, end: editValues.end };
    const timeError = validateOverrideTime(timeRange, getWorkPeriodTimeRange(workPeriods, entry.workPeriod));
    if (timeError) {
      alert(timeError);
      return;
    }

    onUpdate(entry, {
      minimum: editValues.minimum,
      ideal: editValues.ideal,
      estimated: editValues.estimated,
      timeRange
    });
    setEditingId(null);
    setEditValues({});
  };

  const handleEditChange = (field, value) => {
    setEditValues({
      ...editValues,
      [field]: value === '' ? '' : parseInt(value, 10)
    });
  };

  const handleTimeEditChange = (field, value) => {
    setEditValues({
      ...editValues,
      [field]: value
    });
  };

  const validateCoverage = (values) => {
    const { minimum, ideal, estimated } = values;

    if (minimum === '' || ideal === '' || estimated === '') {
      return { valid: false, error: 'All coverage values are required' };
    }

    if (minimum < 0 || ideal < 0 || estimated < 0) {
      return { valid: false, error: 'Coverage values must be non-negative' };
    }

    if (!(minimum <= estimated && estimated <= ideal)) {
      return { valid: false, error: 'Must satisfy: minimum ≤ estimated ≤ ideal' };
    }

    return { valid: true };
  };

  const isEditing = (entry) => {
    return editingId === (entry.date + entry.workPeriod + entry[employeeModel === 'team' ? 'team' : 'competency']);
  };

  const teamLabel = employeeModel === 'team' ? 'Team' : 'Competency';

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box>
          <Typography variant="h6" fontWeight={600}>
            Demand Details
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {new Date(date).toLocaleDateString('en-US', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><strong>Work Period</strong></TableCell>
                <TableCell><strong>{teamLabel}</strong></TableCell>
                <TableCell><strong>Time</strong></TableCell>
                <TableCell align="center"><strong>Minimum</strong></TableCell>
                <TableCell align="center"><strong>Ideal</strong></TableCell>
                <TableCell align="center"><strong>Estimated</strong></TableCell>
                <TableCell align="center"><strong>Actions</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {demandEntries.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                      No demand entries for this date
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                demandEntries.map((entry) => {
                  const editing = isEditing(entry);

                  return (
                    <TableRow
                      key={entry.date + entry.workPeriod + entry[employeeModel === 'team' ? 'team' : 'competency']}
                      sx={{
                        backgroundColor: editing ? 'action.hover' : 'transparent'
                      }}
                    >
                      <TableCell>
                        <Chip label={entry.workPeriod} size="small" color="primary" variant="outlined" />
                      </TableCell>
                      <TableCell>{entry[employeeModel === 'team' ? 'team' : 'competency']}</TableCell>

                      {/* Time (per-day override) */}
                      <TableCell>
                        {editing ? (
                          <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                            <TextField
                              type="time"
                              value={editValues.start}
                              onChange={(e) => handleTimeEditChange('start', e.target.value)}
                              size="small"
                              InputLabelProps={{ shrink: true }}
                              sx={{ width: '110px' }}
                            />
                            <TextField
                              type="time"
                              value={editValues.end}
                              onChange={(e) => handleTimeEditChange('end', e.target.value)}
                              size="small"
                              InputLabelProps={{ shrink: true }}
                              sx={{ width: '110px' }}
                            />
                          </Box>
                        ) : (
                          (() => {
                            const def = getWorkPeriodTimeRange(workPeriods, entry.workPeriod);
                            const eff = entry.timeRange || def;
                            const override = isTimeOverride(entry.timeRange, def);
                            return (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <Typography variant="body2">
                                  {eff ? `${eff.start}–${eff.end}` : '—'}
                                </Typography>
                                {override && (
                                  <Chip label="override" size="small" color="warning" variant="outlined" sx={{ height: '18px', fontSize: '0.6rem' }} />
                                )}
                              </Box>
                            );
                          })()
                        )}
                      </TableCell>

                      {/* Minimum */}
                      <TableCell align="center">
                        {editing ? (
                          <TextField
                            type="number"
                            value={editValues.minimum}
                            onChange={(e) => handleEditChange('minimum', e.target.value)}
                            size="small"
                            inputProps={{ min: 0, style: { textAlign: 'center' } }}
                            sx={{ width: '70px' }}
                          />
                        ) : (
                          entry.minimum
                        )}
                      </TableCell>

                      {/* Ideal */}
                      <TableCell align="center">
                        {editing ? (
                          <TextField
                            type="number"
                            value={editValues.ideal}
                            onChange={(e) => handleEditChange('ideal', e.target.value)}
                            size="small"
                            inputProps={{ min: 0, style: { textAlign: 'center' } }}
                            sx={{ width: '70px' }}
                          />
                        ) : (
                          entry.ideal
                        )}
                      </TableCell>

                      {/* Estimated */}
                      <TableCell align="center">
                        {editing ? (
                          <TextField
                            type="number"
                            value={editValues.estimated}
                            onChange={(e) => handleEditChange('estimated', e.target.value)}
                            size="small"
                            inputProps={{ min: 0, style: { textAlign: 'center' } }}
                            sx={{ width: '70px' }}
                          />
                        ) : (
                          entry.estimated
                        )}
                      </TableCell>

                      {/* Actions */}
                      <TableCell align="center">
                        {editing ? (
                          <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                            <IconButton size="small" color="primary" onClick={() => handleSaveEdit(entry)}>
                              <SaveIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" onClick={handleCancelEdit}>
                              <CancelIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        ) : (
                          <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                            <IconButton size="small" onClick={() => handleStartEdit(entry)}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" color="error" onClick={() => onDelete(entry)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Summary */}
        {demandEntries.length > 0 && (
          <Box sx={{ mt: 2, p: 2, backgroundColor: 'background.default', borderRadius: 1 }}>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              Daily Summary
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Chip
                label={`Total Min: ${demandEntries.reduce((sum, e) => sum + e.minimum, 0)}`}
                color="primary"
                size="small"
              />
              <Chip
                label={`Total Ideal: ${demandEntries.reduce((sum, e) => sum + e.ideal, 0)}`}
                color="primary"
                size="small"
              />
              <Chip
                label={`Total Est: ${demandEntries.reduce((sum, e) => sum + e.estimated, 0)}`}
                color="primary"
                size="small"
              />
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={() => setAddDialogOpen(true)}
          sx={{ mr: 'auto' }}
        >
          Add Entry
        </Button>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>

      <AddDemandEntryDialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        onSave={(newEntry) => { onAdd(newEntry); setAddDialogOpen(false); }}
        date={date}
        workPeriods={workPeriods}
        teams={teams}
        workPeriodModel={workPeriodModel}
        employeeModel={employeeModel}
        existingEntries={demandEntries}
      />
    </Dialog>
  );
};

export default DayDemandDetail;

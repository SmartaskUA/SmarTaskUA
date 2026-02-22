import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  IconButton,
  Tooltip,
  Chip,
  Box,
  Typography,
  Alert
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Add as AddIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon
} from '@mui/icons-material';

/**
 * DemandTable - Editable table for demand entries
 *
 * Displays demand data filtered by selected team and date range
 * Supports inline editing with validation
 */
const DemandTable = ({
  demandData = [],
  filteredData = [],
  workPeriods = [],
  selectedTeam,
  onUpdate,
  onDelete,
  onAdd,
  employeeModel = 'team'
}) => {
  const [editingCell, setEditingCell] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [errors, setErrors] = useState({});

  const teamField = employeeModel === 'team' ? 'team' : 'competency';

  // Handle cell click to enter edit mode
  const handleCellClick = (entryKey, field, currentValue) => {
    setEditingCell({ key: entryKey, field });
    setEditValue(currentValue !== undefined ? currentValue.toString() : '');
    // Clear any previous errors for this cell
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[`${entryKey}-${field}`];
      return newErrors;
    });
  };

  // Handle cell value change
  const handleCellChange = (e) => {
    setEditValue(e.target.value);
  };

  // Validate and save cell value
  const handleCellBlur = () => {
    if (!editingCell) return;

    const { key, field } = editingCell;
    const entry = filteredData.find(e =>
      `${e.date}|${e.workPeriod}|${e[teamField]}` === key
    );

    if (!entry) {
      setEditingCell(null);
      return;
    }

    // Parse value
    const numValue = parseInt(editValue, 10);

    // Validate
    if (isNaN(numValue) || numValue < 0) {
      setErrors(prev => ({
        ...prev,
        [`${key}-${field}`]: 'Must be a non-negative integer'
      }));
      setEditingCell(null);
      return;
    }

    // Check logical order after update
    const updatedEntry = { ...entry, [field]: numValue };
    const { minimum, ideal, estimated } = updatedEntry;

    if (minimum > estimated) {
      setErrors(prev => ({
        ...prev,
        [`${key}-${field}`]: 'Minimum cannot be greater than estimated'
      }));
      setEditingCell(null);
      return;
    }

    if (estimated > ideal) {
      setErrors(prev => ({
        ...prev,
        [`${key}-${field}`]: 'Estimated cannot be greater than ideal'
      }));
      setEditingCell(null);
      return;
    }

    if (minimum > ideal) {
      setErrors(prev => ({
        ...prev,
        [`${key}-${field}`]: 'Minimum cannot be greater than ideal'
      }));
      setEditingCell(null);
      return;
    }

    // Update is valid
    onUpdate(entry, field, numValue);
    setEditingCell(null);
  };

  // Handle Enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleCellBlur();
    } else if (e.key === 'Escape') {
      setEditingCell(null);
    }
  };

  // Get validation status for entry
  const getEntryStatus = (entry) => {
    const { minimum, ideal, estimated } = entry;
    if (minimum === 0 && ideal === 0 && estimated === 0) {
      return 'empty';
    }
    if (minimum > estimated || estimated > ideal || minimum > ideal) {
      return 'invalid';
    }
    return 'valid';
  };

  // Render editable cell
  const renderEditableCell = (entry, field) => {
    const entryKey = `${entry.date}|${entry.workPeriod}|${entry[teamField]}`;
    const cellKey = `${entryKey}-${field}`;
    const value = entry[field];
    const isEditing = editingCell && editingCell.key === entryKey && editingCell.field === field;
    const hasError = errors[cellKey];

    if (isEditing) {
      return (
        <TextField
          value={editValue}
          onChange={handleCellChange}
          onBlur={handleCellBlur}
          onKeyDown={handleKeyPress}
          autoFocus
          type="number"
          size="small"
          inputProps={{ min: 0, step: 1 }}
          error={!!hasError}
          helperText={hasError}
          sx={{ width: '80px' }}
        />
      );
    }

    return (
      <Box
        onClick={() => handleCellClick(entryKey, field, value)}
        sx={{
          cursor: 'pointer',
          padding: '8px',
          '&:hover': {
            bgcolor: 'action.hover'
          },
          borderRadius: 1,
          color: hasError ? 'error.main' : 'text.primary'
        }}
      >
        <Typography variant="body2">{value !== undefined ? value : '-'}</Typography>
        {hasError && (
          <Typography variant="caption" color="error">{hasError}</Typography>
        )}
      </Box>
    );
  };

  if (filteredData.length === 0) {
    return null; // Don't show message - let parent handle it
  }

  return (
    <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
      <Table size="small">
        <TableHead>
          <TableRow sx={{ bgcolor: 'action.hover' }}>
            <TableCell><strong>Status</strong></TableCell>
            <TableCell><strong>Date</strong></TableCell>
            <TableCell><strong>Work Period</strong></TableCell>
            <TableCell><strong>{employeeModel === 'team' ? 'Team' : 'Competency'}</strong></TableCell>
            <TableCell align="center"><strong>Minimum</strong></TableCell>
            <TableCell align="center"><strong>Ideal</strong></TableCell>
            <TableCell align="center"><strong>Estimated</strong></TableCell>
            <TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredData.map((entry) => {
            const entryKey = `${entry.date}|${entry.workPeriod}|${entry[teamField]}`;
            const status = getEntryStatus(entry);

            return (
              <TableRow
                key={entryKey}
                hover
                sx={{
                  bgcolor: status === 'invalid' ? 'error.lighter' :
                           status === 'empty' ? 'grey.50' : 'inherit'
                }}
              >
                {/* Status indicator */}
                <TableCell>
                  {status === 'valid' && (
                    <Tooltip title="Valid entry">
                      <CheckCircleIcon color="success" fontSize="small" />
                    </Tooltip>
                  )}
                  {status === 'invalid' && (
                    <Tooltip title="Invalid: check minimum ≤ estimated ≤ ideal">
                      <WarningIcon color="error" fontSize="small" />
                    </Tooltip>
                  )}
                  {status === 'empty' && (
                    <Chip label="Empty" size="small" variant="outlined" />
                  )}
                </TableCell>

                {/* Date */}
                <TableCell>
                  <Typography variant="body2" fontFamily="monospace">
                    {entry.date}
                  </Typography>
                </TableCell>

                {/* Work Period */}
                <TableCell>
                  <Chip
                    label={entry.workPeriod}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                </TableCell>

                {/* Team/Competency */}
                <TableCell>
                  <Chip
                    label={entry[teamField]}
                    size="small"
                    color="secondary"
                    variant="outlined"
                  />
                </TableCell>

                {/* Minimum (editable) */}
                <TableCell align="center">
                  {renderEditableCell(entry, 'minimum')}
                </TableCell>

                {/* Ideal (editable) */}
                <TableCell align="center">
                  {renderEditableCell(entry, 'ideal')}
                </TableCell>

                {/* Estimated (editable) */}
                <TableCell align="center">
                  {renderEditableCell(entry, 'estimated')}
                </TableCell>

                {/* Actions */}
                <TableCell align="center">
                  <Tooltip title="Delete entry">
                    <IconButton
                      size="small"
                      onClick={() => onDelete(entry)}
                      color="error"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default DemandTable;

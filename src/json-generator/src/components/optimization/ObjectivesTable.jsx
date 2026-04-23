import React, { useState } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Button,
  Chip,
  Tooltip
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ArrowUpward as ArrowUpIcon
} from '@mui/icons-material';
import ObjectiveDialog from './ObjectiveDialog';

/**
 * ObjectivesTable Component
 *
 * Displays and manages optimization objectives with:
 * - Add/Edit/Delete operations
 * - Sorting by priority
 * - Visual indicators for weight and priority
 */
const ObjectivesTable = ({ objectives = [], onChange }) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingObjective, setEditingObjective] = useState(null);
  const [editingIndex, setEditingIndex] = useState(null);

  // Sort objectives by priority (ascending)
  const sortedObjectives = [...objectives].sort((a, b) => a.priority - b.priority);

  // Handle add
  const handleAdd = () => {
    setEditingObjective(null);
    setEditingIndex(null);
    setDialogOpen(true);
  };

  // Handle edit
  const handleEdit = (objective, index) => {
    setEditingObjective(objective);
    setEditingIndex(index);
    setDialogOpen(true);
  };

  // Handle delete
  const handleDelete = (index) => {
    const newObjectives = objectives.filter((_, i) => i !== index);
    onChange(newObjectives);
  };

  // Handle save from dialog
  const handleSave = (objectiveData) => {
    if (editingIndex !== null) {
      // Edit mode - update existing
      const newObjectives = [...objectives];
      newObjectives[editingIndex] = objectiveData;
      onChange(newObjectives);
    } else {
      // Add mode - append new
      onChange([...objectives, objectiveData]);
    }
  };

  // Get weight color
  const getWeightColor = (weight) => {
    if (weight >= 5000) return 'error';
    if (weight >= 1000) return 'warning';
    if (weight >= 100) return 'primary';
    return 'default';
  };

  // Get priority badge color
  const getPriorityColor = (priority) => {
    if (priority <= 2) return 'error';
    if (priority <= 5) return 'warning';
    return 'default';
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h6" fontWeight={600}>
            Custom Objectives
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Define custom optimization goals (optional). Objectives are evaluated in priority order.
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAdd}
          size="small"
        >
          Add Objective
        </Button>
      </Box>

      {/* Empty State */}
      {objectives.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center', backgroundColor: 'action.hover' }}>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            No custom objectives defined
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Objectives are optional. The solver will use default optimization goals if none are specified.
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleAdd}
          >
            Add Your First Objective
          </Button>
        </Paper>
      ) : (
        /* Table */
        <TableContainer component={Paper} sx={{ border: 1, borderColor: 'divider' }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell sx={{ fontWeight: 'bold' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <ArrowUpIcon fontSize="small" color="action" />
                    Priority
                  </Box>
                </TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Goal</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }} align="center">Weight</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }} align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedObjectives.map((objective, index) => {
                // Find original index for edit/delete
                const originalIndex = objectives.findIndex(
                  obj => obj.goal === objective.goal &&
                         obj.weight === objective.weight &&
                         obj.priority === objective.priority
                );

                return (
                  <TableRow
                    key={index}
                    hover
                    sx={{
                      '&:hover': { backgroundColor: 'action.hover' }
                    }}
                  >
                    {/* Priority */}
                    <TableCell>
                      <Chip
                        label={objective.priority}
                        size="small"
                        color={getPriorityColor(objective.priority)}
                        sx={{ fontWeight: 'bold', minWidth: 40 }}
                      />
                    </TableCell>

                    {/* Goal */}
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {objective.goal}
                      </Typography>
                    </TableCell>

                    {/* Weight */}
                    <TableCell align="center">
                      <Chip
                        label={objective.weight}
                        size="small"
                        color={getWeightColor(objective.weight)}
                        variant="outlined"
                        sx={{ fontWeight: 'bold', minWidth: 60 }}
                      />
                    </TableCell>

                    {/* Actions */}
                    <TableCell align="right">
                      <Tooltip title="Edit">
                        <IconButton
                          size="small"
                          onClick={() => handleEdit(objective, originalIndex)}
                          color="primary"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(originalIndex)}
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
      )}

      {/* Legend */}
      {objectives.length > 0 && (
        <Box sx={{ mt: 2, p: 2, backgroundColor: 'action.hover', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary" gutterBottom display="block">
            <strong>Priority:</strong> Lower numbers = evaluated first (1 = highest priority, 10 = lowest)
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            <strong>Weight:</strong> Relative importance of this objective in the optimization function
          </Typography>
        </Box>
      )}

      {/* Dialog */}
      <ObjectiveDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSave={handleSave}
        objective={editingObjective}
        existingObjectives={objectives}
      />
    </Box>
  );
};

export default ObjectivesTable;

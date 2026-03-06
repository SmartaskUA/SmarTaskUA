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
  Typography,
  Box,
  Chip,
  Alert
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon
} from '@mui/icons-material';

/**
 * DayDetailModal Component
 *
 * Shows all demand blocks for a specific day in a table format
 * Allows adding, editing, and deleting blocks without visual overlap issues
 *
 * @param {boolean} open - Whether modal is open
 * @param {Function} onClose - Called when modal should close
 * @param {string} dayOfWeek - Day key (monday, tuesday, etc.)
 * @param {string} dayLabel - Display label (Monday, Tuesday, etc.)
 * @param {Array} blocks - Demand blocks for this day
 * @param {Function} onAdd - Called to add a new block
 * @param {Function} onEdit - Called to edit a block
 * @param {Function} onDelete - Called to delete a block
 * @param {string} employeeModel - 'team' or 'competency'
 */
const DayDetailModal = ({
  open,
  onClose,
  dayOfWeek,
  dayLabel,
  blocks = [],
  onAdd,
  onEdit,
  onDelete,
  employeeModel = 'team'
}) => {
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const handleDelete = (block) => {
    if (deleteConfirm === block.id) {
      onDelete(block);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(block.id);
      // Auto-reset after 3 seconds
      setTimeout(() => setDeleteConfirm(null), 3000);
    }
  };

  const handleAdd = () => {
    onAdd(dayOfWeek);
  };

  // Sort blocks by start time
  const sortedBlocks = [...blocks].sort((a, b) => {
    if (!a.timeRange || !b.timeRange) return 0;
    return a.timeRange.start.localeCompare(b.timeRange.start);
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h6" fontWeight={600}>
              {dayLabel} Demand Blocks
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage all demand blocks for this day
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAdd}
            size="small"
          >
            Add Block
          </Button>
        </Box>
      </DialogTitle>
      <DialogContent>
        {blocks.length === 0 ? (
          <Alert severity="info" sx={{ mt: 2 }}>
            No demand blocks defined for {dayLabel}. Click "Add Block" to create one.
          </Alert>
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {blocks.length} {blocks.length === 1 ? 'block' : 'blocks'} defined for this day
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ backgroundColor: 'action.hover' }}>
                    <TableCell><strong>Time Range</strong></TableCell>
                    <TableCell><strong>Team</strong></TableCell>
                    <TableCell><strong>Work Period</strong></TableCell>
                    <TableCell align="center"><strong>Min</strong></TableCell>
                    <TableCell align="center"><strong>Ideal</strong></TableCell>
                    <TableCell align="center"><strong>Est</strong></TableCell>
                    <TableCell align="center"><strong>Actions</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sortedBlocks.map((block) => (
                    <TableRow
                      key={block.id}
                      sx={{
                        '&:hover': { backgroundColor: 'action.hover' },
                        backgroundColor: deleteConfirm === block.id ? 'error.light' : 'transparent'
                      }}
                    >
                      {/* Time Range */}
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {block.timeRange?.start} - {block.timeRange?.end}
                          {block.timeRange?.end < block.timeRange?.start && (
                            <Chip
                              label="Overnight"
                              size="small"
                              color="warning"
                              sx={{ ml: 1, height: '16px', fontSize: '0.65rem' }}
                            />
                          )}
                        </Typography>
                      </TableCell>

                      {/* Team/Competency */}
                      <TableCell>
                        <Box
                          sx={{
                            display: 'inline-block',
                            backgroundColor: block.color || '#2196F3',
                            color: 'white',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 600
                          }}
                        >
                          {block.team}
                        </Box>
                      </TableCell>

                      {/* Work Period */}
                      <TableCell>
                        <Chip
                          label={block.workPeriod}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: '0.7rem' }}
                        />
                      </TableCell>

                      {/* Coverage Values */}
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight={600}>
                          {block.coverage?.minimum}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight={600}>
                          {block.coverage?.ideal}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography variant="body2" fontWeight={600}>
                          {block.coverage?.estimated}
                        </Typography>
                      </TableCell>

                      {/* Actions */}
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => onEdit(block)}
                            title="Edit block"
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            color={deleteConfirm === block.id ? 'error' : 'default'}
                            onClick={() => handleDelete(block)}
                            title={deleteConfirm === block.id ? 'Click again to confirm delete' : 'Delete block'}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Box>
                        {deleteConfirm === block.id && (
                          <Typography variant="caption" color="error" sx={{ display: 'block', mt: 0.5 }}>
                            Click again to confirm
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Summary */}
            <Box sx={{ mt: 2, p: 2, backgroundColor: 'background.default', borderRadius: 1 }}>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Daily Summary
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip
                  label={`Total Min: ${blocks.reduce((sum, b) => sum + (b.coverage?.minimum || 0), 0)}`}
                  size="small"
                  color="primary"
                />
                <Chip
                  label={`Total Ideal: ${blocks.reduce((sum, b) => sum + (b.coverage?.ideal || 0), 0)}`}
                  size="small"
                  color="primary"
                />
                <Chip
                  label={`Total Est: ${blocks.reduce((sum, b) => sum + (b.coverage?.estimated || 0), 0)}`}
                  size="small"
                  color="primary"
                />
              </Box>
            </Box>

            {/* Overlapping blocks warning */}
            {blocks.length > 1 && hasOverlaps(blocks) && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                <strong>Warning:</strong> Some blocks have overlapping time ranges. This may cause visual overlap in the weekly view, but all blocks are saved correctly.
              </Alert>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

/**
 * Check if any blocks have overlapping time ranges
 */
function hasOverlaps(blocks) {
  for (let i = 0; i < blocks.length; i++) {
    for (let j = i + 1; j < blocks.length; j++) {
      const block1 = blocks[i];
      const block2 = blocks[j];

      if (!block1.timeRange || !block2.timeRange) continue;

      const start1 = block1.timeRange.start;
      const end1 = block1.timeRange.end;
      const start2 = block2.timeRange.start;
      const end2 = block2.timeRange.end;

      // Check for overlap: start1 < end2 && start2 < end1
      if (start1 < end2 && start2 < end1) {
        return true;
      }
    }
  }
  return false;
}

export default DayDetailModal;

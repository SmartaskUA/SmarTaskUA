import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Chip,
  Box,
  Typography,
  Alert
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { formatTimeRange, formatDuration } from '../../utils/helpers/timeHelpers';

/**
 * WorkPeriodTable Component - Display work periods in a table
 *
 * Shows all work periods with their details and action buttons
 */
const WorkPeriodTable = ({
  workPeriods = [],
  workPeriodModel,
  onEdit,
  onDelete
}) => {
  // Format time/duration column based on model
  const formatTimeDuration = (workPeriod) => {
    if (workPeriodModel === 'fixed' && workPeriod.timeRange) {
      return formatTimeRange(workPeriod.timeRange.start, workPeriod.timeRange.end);
    } else if (workPeriodModel === 'flexible' && workPeriod.duration) {
      const allowedTimesCount = workPeriod.allowedStartTimes?.length || 0;
      return `${workPeriod.duration}h (${allowedTimesCount} start times)`;
    }
    return 'N/A';
  };

  // Format breaks for display
  const formatBreaks = (breaks) => {
    if (!breaks || breaks.length === 0) {
      return <Chip label="No breaks" size="small" variant="outlined" />;
    }

    const totalDuration = breaks.reduce((sum, b) => sum + Number(b.duration), 0);
    return (
      <Tooltip
        title={
          <Box>
            {breaks.map((b, i) => (
              <Box key={i}>
                • {b.type}: {formatDuration(b.duration)} ({b.timingMode})
              </Box>
            ))}
          </Box>
        }
      >
        <Chip
          label={`${breaks.length} break${breaks.length > 1 ? 's' : ''} (${formatDuration(totalDuration)})`}
          size="small"
          color="primary"
        />
      </Tooltip>
    );
  };

  if (workPeriods.length === 0) {
    return (
      <Alert severity="info" icon={<ScheduleIcon />}>
        No work periods defined yet. Click <strong>"Add Work Period"</strong> to get started.
      </Alert>
    );
  }

  // Sort work periods by code
  const sortedWorkPeriods = [...workPeriods].sort((a, b) => a.code.localeCompare(b.code));

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow sx={{ bgcolor: 'action.hover' }}>
            <TableCell><strong>Code</strong></TableCell>
            <TableCell><strong>Name</strong></TableCell>
            <TableCell>
              <strong>
                {workPeriodModel === 'fixed' ? 'Time Range' : 'Duration'}
              </strong>
            </TableCell>
            <TableCell><strong>Breaks</strong></TableCell>
            <TableCell align="center"><strong>Actions</strong></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedWorkPeriods.map((workPeriod) => (
            <TableRow
              key={workPeriod.code}
              hover
              sx={{
                '&:hover': {
                  bgcolor: 'action.hover'
                }
              }}
            >
              {/* Code */}
              <TableCell>
                <Chip
                  label={workPeriod.code}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              </TableCell>

              {/* Name */}
              <TableCell>
                <Typography variant="body2">{workPeriod.name}</Typography>
              </TableCell>

              {/* Time Range / Duration */}
              <TableCell>
                <Typography variant="body2" fontFamily="monospace">
                  {formatTimeDuration(workPeriod)}
                </Typography>
                {workPeriodModel === 'flexible' && workPeriod.allowedStartTimes && (
                  <Tooltip
                    title={
                      <Box>
                        <Typography variant="caption" display="block" gutterBottom>
                          <strong>Allowed Start Times:</strong>
                        </Typography>
                        {workPeriod.allowedStartTimes.map((time) => (
                          <Typography key={time} variant="caption" display="block">
                            • {time}
                          </Typography>
                        ))}
                      </Box>
                    }
                  >
                    <Typography variant="caption" color="primary" sx={{ cursor: 'help' }}>
                      (view times)
                    </Typography>
                  </Tooltip>
                )}
              </TableCell>

              {/* Breaks */}
              <TableCell>
                {formatBreaks(workPeriod.breaks)}
              </TableCell>

              {/* Actions */}
              <TableCell align="center">
                <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                  <Tooltip title="Edit work period">
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => onEdit(workPeriod)}
                      aria-label="Edit work period"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete work period">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => onDelete(workPeriod.code)}
                      aria-label="Delete work period"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default WorkPeriodTable;

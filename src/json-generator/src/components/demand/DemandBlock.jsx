import React from 'react';
import { Box, Typography, IconButton, Chip, Tooltip } from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, DragIndicator as DragIcon } from '@mui/icons-material';

/**
 * DemandBlock Component
 *
 * Visual block representing a demand entry in the weekly template
 * - Displays team, work period, and coverage numbers
 * - Color-coded by team
 * - Draggable (for repositioning)
 * - Clickable to edit
 *
 * @param {Object} block - Demand block data
 * @param {Function} onEdit - Called when edit is clicked
 * @param {Function} onDelete - Called when delete is clicked
 * @param {number} slotHeight - Height of each 30-min time slot (for positioning)
 * @param {boolean} isContinuation - True if this is the "next day" portion of an overnight work period
 */
const DemandBlock = ({ block, onEdit, onDelete, slotHeight = 30, isContinuation = false }) => {
  if (!block) return null;

  const {
    team,
    workPeriod,
    timeRange,
    coverage,
    color = '#2196F3'
  } = block;

  // Calculate block position and height based on time range
  const calculatePosition = () => {
    if (!timeRange) return { top: 0, height: slotHeight, isOvernight: false };

    const [startHour, startMin] = timeRange.start.split(':').map(Number);
    const [endHour, endMin] = timeRange.end.split(':').map(Number);

    // Check if this is an overnight work period (end < start)
    const isOvernight = timeRange.end < timeRange.start;

    let startSlot, endSlot;

    if (isContinuation) {
      // This is the "next day" portion of an overnight work period
      // Start from 00:00 and go to the end time
      startSlot = 0;
      endSlot = endHour * 2 + (endMin >= 30 ? 1 : 0);
    } else {
      // Normal block or first part of overnight work period
      startSlot = startHour * 2 + (startMin >= 30 ? 1 : 0);
      endSlot = endHour * 2 + (endMin >= 30 ? 1 : 0);

      // For overnight work periods (first part), extend to end of day (24:00 = slot 48)
      if (isOvernight) {
        endSlot = 48; // 24:00 in 30-min slots
      }
    }

    const top = startSlot * slotHeight;
    const height = (endSlot - startSlot) * slotHeight;

    return { top, height, isOvernight };
  };

  const { top, height, isOvernight } = calculatePosition();

  const handleEdit = (e) => {
    e.stopPropagation();
    onEdit(block);
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    onDelete(block);
  };

  return (
    <Box
      sx={{
        position: 'absolute',
        top: `${top}px`,
        left: '4px',
        right: '4px',
        height: `${height}px`,
        backgroundColor: color,
        borderRadius: '4px',
        border: '1px solid',
        borderColor: 'rgba(0,0,0,0.2)',
        padding: '4px 6px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        overflow: 'hidden',
        '&:hover': {
          boxShadow: 3,
          zIndex: 10,
          transform: 'scale(1.02)'
        },
        display: 'flex',
        flexDirection: 'column',
        gap: 0.5
      }}
      onClick={handleEdit}
    >
      {/* Drag handle */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 0.5
        }}
      >
        <DragIcon sx={{ fontSize: '14px', color: 'rgba(255,255,255,0.7)', cursor: 'grab' }} />
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          <IconButton
            size="small"
            onClick={handleEdit}
            sx={{
              padding: '2px',
              color: 'white',
              backgroundColor: 'rgba(255,255,255,0.2)',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.3)' }
            }}
          >
            <EditIcon sx={{ fontSize: '14px' }} />
          </IconButton>
          <IconButton
            size="small"
            onClick={handleDelete}
            sx={{
              padding: '2px',
              color: 'white',
              backgroundColor: 'rgba(255,255,255,0.2)',
              '&:hover': { backgroundColor: 'rgba(255,0,0,0.5)' }
            }}
          >
            <DeleteIcon sx={{ fontSize: '14px' }} />
          </IconButton>
        </Box>
      </Box>

      {/* Team and Work Period */}
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        <Typography
          variant="caption"
          sx={{
            color: 'white',
            fontWeight: 600,
            fontSize: '0.75rem',
            display: 'block',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}
        >
          {team}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            color: 'rgba(255,255,255,0.9)',
            fontSize: '0.65rem',
            display: 'block',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}
        >
          {workPeriod} • {isContinuation ? `00:00-${timeRange?.end}` : `${timeRange?.start}-${timeRange?.end}`}
          {isContinuation && ' ⟸ From Prev'}
          {!isContinuation && isOvernight && ' ⟹ Next Day'}
        </Typography>
      </Box>

      {/* Coverage numbers */}
      {coverage && (
        <Box
          sx={{
            display: 'flex',
            gap: 0.5,
            flexWrap: 'wrap',
            alignItems: 'center'
          }}
        >
          <Tooltip title="Minimum">
            <Chip
              label={`Min:${coverage.minimum}`}
              size="small"
              sx={{
                height: '18px',
                fontSize: '0.65rem',
                backgroundColor: 'rgba(255,255,255,0.3)',
                color: 'white',
                fontWeight: 600,
                '& .MuiChip-label': { px: 0.5 }
              }}
            />
          </Tooltip>
          <Tooltip title="Ideal">
            <Chip
              label={`Ideal:${coverage.ideal}`}
              size="small"
              sx={{
                height: '18px',
                fontSize: '0.65rem',
                backgroundColor: 'rgba(255,255,255,0.3)',
                color: 'white',
                fontWeight: 600,
                '& .MuiChip-label': { px: 0.5 }
              }}
            />
          </Tooltip>
          <Tooltip title="Estimated">
            <Chip
              label={`Est:${coverage.estimated}`}
              size="small"
              sx={{
                height: '18px',
                fontSize: '0.65rem',
                backgroundColor: 'rgba(255,255,255,0.3)',
                color: 'white',
                fontWeight: 600,
                '& .MuiChip-label': { px: 0.5 }
              }}
            />
          </Tooltip>
        </Box>
      )}
    </Box>
  );
};

export default DemandBlock;

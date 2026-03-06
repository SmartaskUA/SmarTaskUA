import React, { useState } from 'react';
import { Box, Typography, Paper, Button, Tooltip, IconButton } from '@mui/material';
import { Add as AddIcon, ViewDay as ViewDayIcon } from '@mui/icons-material';
import TimeAxis from './TimeAxis';
import DemandBlock from './DemandBlock';
import DemandBlockDialog from './DemandBlockDialog';
import DayDetailModal from './DayDetailModal';

/**
 * WeeklyTemplateBuilder Component
 *
 * Phase 1 of Demand Calendar: Visual weekly template builder
 * - 7 columns for days of the week (Monday-Sunday)
 * - Vertical time axis with 30-min slots
 * - Draggable demand blocks showing team coverage requirements
 * - Click to add/edit blocks
 *
 * @param {Object} weeklyTemplate - Weekly template data (object with day keys)
 * @param {Function} onTemplateChange - Called when template is modified
 * @param {Array} teams - Available teams/competencies
 * @param {Array} workPeriods - Available work periods from Step 6
 * @param {string} workPeriodModel - 'fixed' or 'flexible'
 * @param {string} employeeModel - 'team' or 'competency'
 */
const WeeklyTemplateBuilder = ({
  weeklyTemplate = {},
  onTemplateChange,
  teams = [],
  workPeriods = [],
  workPeriodModel = 'fixed',
  employeeModel = 'team'
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editBlock, setEditBlock] = useState(null);
  const [selectedDay, setSelectedDay] = useState(null);
  const [dayModalOpen, setDayModalOpen] = useState(false);
  const [dayModalDay, setDayModalDay] = useState(null);

  const daysOfWeek = [
    { key: 'monday', label: 'Monday', short: 'Mon' },
    { key: 'tuesday', label: 'Tuesday', short: 'Tue' },
    { key: 'wednesday', label: 'Wednesday', short: 'Wed' },
    { key: 'thursday', label: 'Thursday', short: 'Thu' },
    { key: 'friday', label: 'Friday', short: 'Fri' },
    { key: 'saturday', label: 'Saturday', short: 'Sat' },
    { key: 'sunday', label: 'Sunday', short: 'Sun' }
  ];

  const slotHeight = 30; // pixels per 30-min slot
  const totalHeight = slotHeight * 48; // 24 hours * 2 slots per hour

  // Handle adding a new block
  const handleAddBlock = (dayKey) => {
    setSelectedDay(dayKey);
    setEditBlock(null);
    setDialogOpen(true);
  };

  // Handle editing existing block
  const handleEditBlock = (block) => {
    setEditBlock(block);
    setSelectedDay(block.dayOfWeek);
    setDialogOpen(true);
  };

  // Handle deleting a block
  const handleDeleteBlock = (block) => {
    const dayBlocks = weeklyTemplate[block.dayOfWeek] || [];
    const updatedBlocks = dayBlocks.filter(b => b.id !== block.id);

    onTemplateChange({
      ...weeklyTemplate,
      [block.dayOfWeek]: updatedBlocks
    });
  };

  // Handle saving a block (add or edit)
  const handleSaveBlock = (blockData) => {
    const dayKey = blockData.dayOfWeek;
    const dayBlocks = weeklyTemplate[dayKey] || [];

    let updatedBlocks;
    if (editBlock) {
      // Edit existing block
      updatedBlocks = dayBlocks.map(b => (b.id === blockData.id ? blockData : b));
    } else {
      // Add new block
      updatedBlocks = [...dayBlocks, blockData];
    }

    onTemplateChange({
      ...weeklyTemplate,
      [dayKey]: updatedBlocks
    });
  };

  // Get blocks for a specific day
  const getBlocksForDay = (dayKey) => {
    return weeklyTemplate[dayKey] || [];
  };

  // Get the previous day key (wraps around from Monday to Sunday)
  const getPreviousDayKey = (dayKey) => {
    const dayIndex = daysOfWeek.findIndex(d => d.key === dayKey);
    const prevIndex = dayIndex === 0 ? 6 : dayIndex - 1; // Wrap Sunday -> Monday
    return daysOfWeek[prevIndex].key;
  };

  // Get overnight blocks from previous day that continue into this day
  const getOvernightBlocksFromPreviousDay = (dayKey) => {
    const previousDayKey = getPreviousDayKey(dayKey);
    const previousDayBlocks = getBlocksForDay(previousDayKey);

    // Filter for overnight blocks (where end < start)
    return previousDayBlocks.filter(block => {
      return block.timeRange && block.timeRange.end < block.timeRange.start;
    });
  };

  // Handle opening day detail modal
  const handleOpenDayModal = (dayKey) => {
    setDayModalDay(dayKey);
    setDayModalOpen(true);
  };

  // Handle closing day detail modal
  const handleCloseDayModal = () => {
    setDayModalOpen(false);
    setDayModalDay(null);
  };

  return (
    <Box sx={{ width: '100%', height: '100%' }}>
      {/* Header with instructions */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Click on any day column to add demand blocks. Each block represents how many people are needed
          from a specific team during a specific work period.
        </Typography>
      </Box>

      {/* Weekly Grid */}
      <Paper
        elevation={2}
        sx={{
          height: 'calc(100vh - 400px)',
          minHeight: '500px',
          overflow: 'auto',
          border: '1px solid',
          borderColor: 'divider'
        }}
      >
        {/* Scrollable Content Wrapper */}
        <Box
          sx={{
            display: 'flex',
            minHeight: '100%'
          }}
        >
          {/* Time Axis */}
          <TimeAxis slotHeight={slotHeight} />

          {/* Day Columns */}
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              position: 'relative'
            }}
          >
          {daysOfWeek.map((day) => {
            const blocks = getBlocksForDay(day.key);
            const overnightBlocks = getOvernightBlocksFromPreviousDay(day.key);

            return (
              <Box
                key={day.key}
                sx={{
                  flex: 1,
                  minWidth: '120px',
                  borderRight: '1px solid',
                  borderColor: 'divider',
                  position: 'relative',
                  '&:last-child': {
                    borderRight: 'none'
                  }
                }}
              >
                {/* Day Header */}
                <Box
                  sx={{
                    position: 'sticky',
                    top: 0,
                    zIndex: 5,
                    backgroundColor: 'primary.main',
                    color: 'white',
                    padding: '8px',
                    borderBottom: '2px solid',
                    borderColor: 'primary.dark',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="subtitle2" fontWeight={600}>
                      {day.short}
                    </Typography>
                    {(blocks.length > 0 || overnightBlocks.length > 0) && (
                      <Typography
                        variant="caption"
                        sx={{
                          backgroundColor: 'rgba(255,255,255,0.3)',
                          padding: '2px 6px',
                          borderRadius: '10px',
                          fontSize: '0.65rem',
                          fontWeight: 600
                        }}
                      >
                        {blocks.length + overnightBlocks.length}
                      </Typography>
                    )}
                  </Box>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    <Tooltip title="View all blocks for this day">
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDayModal(day.key)}
                        sx={{
                          color: 'white',
                          backgroundColor: 'rgba(255,255,255,0.2)',
                          '&:hover': {
                            backgroundColor: 'rgba(255,255,255,0.3)'
                          },
                          padding: '4px'
                        }}
                      >
                        <ViewDayIcon sx={{ fontSize: '16px' }} />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Add demand block">
                      <IconButton
                        size="small"
                        onClick={() => handleAddBlock(day.key)}
                        sx={{
                          color: 'white',
                          backgroundColor: 'rgba(255,255,255,0.2)',
                          '&:hover': {
                            backgroundColor: 'rgba(255,255,255,0.3)'
                          },
                          padding: '4px'
                        }}
                      >
                        <AddIcon sx={{ fontSize: '16px' }} />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>

                {/* Time Slots Grid (clickable background) */}
                <Box
                  sx={{
                    height: `${totalHeight}px`,
                    position: 'relative',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: 'action.hover'
                    }
                  }}
                  onClick={() => handleAddBlock(day.key)}
                >
                  {/* Render 30-min slot guides */}
                  {Array.from({ length: 48 }).map((_, index) => (
                    <Box
                      key={index}
                      sx={{
                        height: `${slotHeight}px`,
                        borderTop: index % 2 === 0 ? '1px solid' : '1px dashed',
                        borderColor: index % 2 === 0 ? 'divider' : 'rgba(0,0,0,0.05)'
                      }}
                    />
                  ))}

                  {/* Demand Blocks for this day */}
                  {blocks.map((block) => (
                    <DemandBlock
                      key={block.id}
                      block={block}
                      onEdit={handleEditBlock}
                      onDelete={handleDeleteBlock}
                      slotHeight={slotHeight}
                    />
                  ))}

                  {/* Continuation blocks from previous day's overnight shifts */}
                  {overnightBlocks.map((block) => (
                    <DemandBlock
                      key={`continuation-${block.id}`}
                      block={block}
                      onEdit={handleEditBlock}
                      onDelete={handleDeleteBlock}
                      slotHeight={slotHeight}
                      isContinuation={true}
                    />
                  ))}
                </Box>
              </Box>
            );
          })}
        </Box>
        </Box>
      </Paper>

      {/* Dialog for adding/editing blocks */}
      <DemandBlockDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          setEditBlock(null);
          setSelectedDay(null);
        }}
        onSave={handleSaveBlock}
        editBlock={editBlock}
        dayOfWeek={selectedDay}
        teams={teams}
        workPeriods={workPeriods}
        workPeriodModel={workPeriodModel}
        employeeModel={employeeModel}
      />

      {/* Day Detail Modal - View all blocks for a specific day */}
      {dayModalDay && (
        <DayDetailModal
          open={dayModalOpen}
          onClose={handleCloseDayModal}
          dayOfWeek={dayModalDay}
          dayLabel={daysOfWeek.find(d => d.key === dayModalDay)?.label || ''}
          blocks={getBlocksForDay(dayModalDay)}
          onAdd={handleAddBlock}
          onEdit={handleEditBlock}
          onDelete={handleDeleteBlock}
          employeeModel={employeeModel}
        />
      )}
    </Box>
  );
};

export default WeeklyTemplateBuilder;

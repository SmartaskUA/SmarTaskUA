import React, { useState, useMemo } from 'react';
import { Box, Grid, Typography, Paper } from '@mui/material';
import DayDemandSummary from './DayDemandSummary';
import DayDemandDetail from './DayDemandDetail';

/**
 * DemandCalendarGrid Component
 *
 * Phase 2 of Demand Calendar: Full calendar view with all dates
 * - Shows each date as a summary cell
 * - Click to expand for details
 * - Heat map visualization of demand intensity
 *
 * @param {Array} dates - Array of date strings (YYYY-MM-DD)
 * @param {Array} demandData - All demand entries
 * @param {Array} workPeriods - Expected work periods
 * @param {Function} onUpdate - Called when demand is updated
 * @param {Function} onDelete - Called when demand is deleted
 * @param {string} employeeModel - 'team' or 'competency'
 */
const DemandCalendarGrid = ({
  dates = [],
  demandData = [],
  workPeriods = [],
  onUpdate,
  onDelete,
  employeeModel = 'team'
}) => {
  const [selectedDate, setSelectedDate] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  // Group demand by date for efficient lookup
  const demandByDate = useMemo(() => {
    const grouped = {};
    demandData.forEach((entry) => {
      if (!grouped[entry.date]) {
        grouped[entry.date] = [];
      }
      grouped[entry.date].push(entry);
    });
    return grouped;
  }, [demandData]);

  // Get demand entries for a specific date
  const getDemandForDate = (date) => {
    return demandByDate[date] || [];
  };

  // Handle clicking on a day cell
  const handleDayClick = (date) => {
    setSelectedDate(date);
    setDetailModalOpen(true);
  };

  // Handle updating demand from detail modal
  const handleUpdate = (entry, newValues) => {
    onUpdate({ ...entry, ...newValues });
  };

  // Handle deleting demand from detail modal
  const handleDelete = (entry) => {
    onDelete(entry);
  };

  // Group dates by week for better visual organization
  const weekGroups = useMemo(() => {
    const weeks = [];
    let currentWeek = [];

    dates.forEach((date, index) => {
      currentWeek.push(date);

      // Start new week on Monday or every 7 days
      const dayOfWeek = new Date(date).getDay();
      if (dayOfWeek === 0 || currentWeek.length === 7) {
        // Sunday or 7 days
        weeks.push(currentWeek);
        currentWeek = [];
      }
    });

    // Add remaining days
    if (currentWeek.length > 0) {
      weeks.push(currentWeek);
    }

    return weeks;
  }, [dates]);

  return (
    <Box sx={{ width: '100%' }}>
      {/* Instructions */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Click on any day to view and edit demand details. Colors indicate demand levels - darker means more coverage required.
        </Typography>
      </Box>

      {/* Calendar Grid - Organized by weeks */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {weekGroups.map((week, weekIndex) => (
          <Paper
            key={weekIndex}
            elevation={1}
            sx={{
              p: 1.5,
              border: '1px solid',
              borderColor: 'divider'
            }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              Week {weekIndex + 1}
            </Typography>
            <Grid container spacing={1}>
              {week.map((date) => {
                const entries = getDemandForDate(date);
                const dayOfWeek = new Date(date).toLocaleDateString('en-US', { weekday: 'short' });

                return (
                  <Grid item xs={12} sm={6} md={4} lg={3} xl={1.714} key={date}>
                    <Box>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: 'block', mb: 0.5, fontWeight: 500 }}
                      >
                        {dayOfWeek}
                      </Typography>
                      <DayDemandSummary
                        date={date}
                        demandEntries={entries}
                        workPeriods={workPeriods}
                        onClick={() => handleDayClick(date)}
                      />
                    </Box>
                  </Grid>
                );
              })}
            </Grid>
          </Paper>
        ))}
      </Box>

      {/* Detail Modal */}
      {selectedDate && (
        <DayDemandDetail
          open={detailModalOpen}
          onClose={() => {
            setDetailModalOpen(false);
            setSelectedDate(null);
          }}
          date={selectedDate}
          demandEntries={getDemandForDate(selectedDate)}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
          employeeModel={employeeModel}
        />
      )}
    </Box>
  );
};

export default DemandCalendarGrid;

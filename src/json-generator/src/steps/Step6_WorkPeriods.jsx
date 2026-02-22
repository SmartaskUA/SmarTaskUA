import React, { useState } from 'react';
import {
  Typography,
  Box,
  Button,
  Alert
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import WorkPeriodTable from '../components/shifts/WorkPeriodTable';
import WorkPeriodForm from '../components/shifts/WorkPeriodForm';
import { useWizard } from '../context/WizardContext';
import { validateWorkPeriodsExist } from '../utils/validators/workPeriodValidator';

/**
 * Step 6: Work Periods
 *
 * Define work period types (shifts), time ranges, and break rules.
 * Supports two models:
 * - Fixed: Specific time ranges (e.g., Morning: 08:00-16:00)
 * - Flexible: Duration + allowed start times (e.g., 8h, can start 06:00-08:00)
 */
const Step6_WorkPeriods = () => {
  const { state, updateState, goToStep } = useWizard();

  const [formOpen, setFormOpen] = useState(false);
  const [editWorkPeriod, setEditWorkPeriod] = useState(null);
  const [error, setError] = useState('');

  const currentModel = state.demand.workPeriodModel;
  const workPeriods = state.demand.workPeriods || [];

  // Open form for adding new work period
  const handleAddClick = () => {
    setEditWorkPeriod(null);
    setFormOpen(true);
  };

  // Open form for editing existing work period
  const handleEdit = (workPeriod) => {
    setEditWorkPeriod(workPeriod);
    setFormOpen(true);
  };

  // Delete work period
  const handleDelete = (code) => {
    const newWorkPeriods = workPeriods.filter((wp) => wp.code !== code);
    updateState('demand.workPeriods', newWorkPeriods);
  };

  // Save work period (add or edit)
  const handleSave = (workPeriodData) => {
    if (editWorkPeriod) {
      // Edit mode: replace existing work period
      const newWorkPeriods = workPeriods.map((wp) =>
        wp.code === editWorkPeriod.code ? workPeriodData : wp
      );
      updateState('demand.workPeriods', newWorkPeriods);
    } else {
      // Add mode: append new work period
      updateState('demand.workPeriods', [...workPeriods, workPeriodData]);
    }
    setFormOpen(false);
    setEditWorkPeriod(null);
    if (error) setError('');
  };

  // Validate before allowing Next
  const handleNext = () => {
    const validation = validateWorkPeriodsExist(workPeriods);
    if (!validation.valid) {
      setError(validation.error);
      return false;
    }
    return true;
  };

  return (
    <Box
      sx={{
        height: 'calc(100vh - 280px)',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* HEADER - Fixed */}
      <Box sx={{ flexShrink: 0, mb: 2 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Work Period Definitions
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Define shift types, time ranges, and break rules for your scheduling problem.
        </Typography>
      </Box>

      {/* CONTENT - Scrollable */}
      <Box
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          pr: 1
        }}
      >
        <StepCard>
          {/* Work Periods List */}
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                Work Periods
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleAddClick}
                size="small"
              >
                Add Work Period
              </Button>
            </Box>

            <WorkPeriodTable
              workPeriods={workPeriods}
              workPeriodModel={currentModel}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          </Box>

          {/* Error message */}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </StepCard>
      </Box>

      {/* NAVIGATION - Fixed at bottom */}
      <Box sx={{ flexShrink: 0, mt: 2 }}>
        <NavigationButtons
          onNext={handleNext}
          nextDisabled={workPeriods.length === 0}
        />
      </Box>

      {/* Work Period Form Dialog */}
      <WorkPeriodForm
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditWorkPeriod(null);
        }}
        onSave={handleSave}
        workPeriodModel={currentModel}
        existingWorkPeriods={workPeriods}
        editWorkPeriod={editWorkPeriod}
      />
    </Box>
  );
};

export default Step6_WorkPeriods;

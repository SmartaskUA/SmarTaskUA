import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Alert
} from '@mui/material';

/**
 * ObjectiveDialog Component
 *
 * Dialog for adding or editing optimization objectives.
 * Objectives have:
 * - goal: Unique name/description
 * - weight: Importance (1-10000)
 * - priority: Order of evaluation (1-10, lower = higher priority)
 */
const ObjectiveDialog = ({
  open,
  onClose,
  onSave,
  objective = null,  // null for add, objective object for edit
  existingObjectives = []
}) => {
  const [formData, setFormData] = useState({
    goal: '',
    weight: 100,
    priority: 1
  });
  const [errors, setErrors] = useState({});

  // Initialize form when objective changes or dialog opens
  useEffect(() => {
    if (objective) {
      // Edit mode - populate with existing data
      setFormData({
        goal: objective.goal || '',
        weight: objective.weight || 100,
        priority: objective.priority || 1
      });
    } else {
      // Add mode - reset to defaults
      setFormData({
        goal: '',
        weight: 100,
        priority: 1
      });
    }
    setErrors({});
  }, [objective, open]);

  // Handle field changes
  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  // Validate form
  const validate = () => {
    const newErrors = {};

    // Goal validation
    if (!formData.goal.trim()) {
      newErrors.goal = 'Goal is required';
    } else {
      // Check for duplicate goal (case-insensitive)
      const isDuplicate = existingObjectives.some(
        obj => obj.goal.toLowerCase() === formData.goal.toLowerCase() &&
               (!objective || obj.goal !== objective.goal)  // Allow same name when editing
      );
      if (isDuplicate) {
        newErrors.goal = 'An objective with this goal already exists';
      }
    }

    // Weight validation
    const weight = parseFloat(formData.weight);
    if (isNaN(weight) || weight < 1 || weight > 10000) {
      newErrors.weight = 'Weight must be between 1 and 10000';
    }

    // Priority validation
    const priority = parseInt(formData.priority);
    if (isNaN(priority) || priority < 1 || priority > 10) {
      newErrors.priority = 'Priority must be between 1 and 10';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle save
  const handleSave = () => {
    if (validate()) {
      onSave({
        goal: formData.goal.trim(),
        weight: parseFloat(formData.weight),
        priority: parseInt(formData.priority)
      });
      onClose();
    }
  };

  // Handle cancel
  const handleCancel = () => {
    setErrors({});
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>
        {objective ? 'Edit Objective' : 'Add Objective'}
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 1 }}>
          {/* Info Alert */}
          <Alert severity="info" sx={{ mb: 2 }}>
            Objectives are optional custom goals for the scheduler. Each objective has a weight (importance)
            and priority (evaluation order). Lower priority numbers = higher priority.
          </Alert>

          {/* Goal Field */}
          <TextField
            label="Goal"
            fullWidth
            value={formData.goal}
            onChange={(e) => handleChange('goal', e.target.value)}
            error={!!errors.goal}
            helperText={errors.goal || 'Unique name describing this optimization goal (e.g., "minimize_cost", "maximize_weekend_coverage")'}
            sx={{ mb: 2 }}
            required
          />

          {/* Weight Field */}
          <TextField
            label="Weight"
            type="number"
            fullWidth
            value={formData.weight}
            onChange={(e) => handleChange('weight', e.target.value)}
            error={!!errors.weight}
            helperText={errors.weight || 'Importance of this objective (1-10000). Higher weights = higher importance.'}
            inputProps={{ min: 1, max: 10000, step: 10 }}
            sx={{ mb: 2 }}
            required
          />

          {/* Priority Field */}
          <TextField
            label="Priority"
            type="number"
            fullWidth
            value={formData.priority}
            onChange={(e) => handleChange('priority', e.target.value)}
            error={!!errors.priority}
            helperText={errors.priority || 'Evaluation order (1-10). Lower numbers = evaluated first.'}
            inputProps={{ min: 1, max: 10, step: 1 }}
            required
          />
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleCancel} color="inherit">
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          {objective ? 'Save Changes' : 'Add Objective'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ObjectiveDialog;

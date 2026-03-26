import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Grid,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormHelperText,
  Autocomplete,
  Chip,
  Box,
  Typography,
  Divider
} from '@mui/material';
import CompetencyBuilder from './CompetencyBuilder';

/**
 * EmployeeForm Component
 *
 * Dialog for adding/editing employees.
 * Both models use teams field:
 * - Team model: teams is array of strings (team codes)
 * - Competency model: teams is array of {code, name, level}
 */
const EmployeeForm = ({
  open,
  onClose,
  onSave,
  editingEmployee = null,
  employeeModel,  // 'team' or 'competency'
  existingIds = [],
  availableTeams = [],
  availableContracts = []
}) => {
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    teams: [],  // Always teams (format depends on model)
    contractType: ''
  });
  const [errors, setErrors] = useState({});

  // Initialize form when editing
  useEffect(() => {
    if (editingEmployee) {
      setFormData(editingEmployee);
    } else {
      setFormData({
        id: '',
        name: '',
        teams: [],
        contractType: ''
      });
    }
    setErrors({});
  }, [editingEmployee, open]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    // ID validation
    if (!formData.id.trim()) {
      newErrors.id = 'Employee ID is required';
    } else if (
      !editingEmployee &&
      existingIds.includes(formData.id.trim())
    ) {
      newErrors.id = 'Employee ID already exists';
    }

    // Contract validation
    if (!formData.contractType) {
      newErrors.contractType = 'Contract type is required';
    } else if (!availableContracts.includes(formData.contractType)) {
      newErrors.contractType = 'Invalid contract type';
    }

    // Teams validation (always required for both models)
    if (formData.teams.length === 0) {
      newErrors.teams = 'At least one team is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validate()) {
      const employeeData = {
        id: formData.id.trim(),
        name: formData.name.trim() || formData.id.trim(),  // Use ID as name if no name provided
        teams: formData.teams,  // Always include teams (format depends on model)
        contractType: formData.contractType
      };

      onSave(employeeData);
      onClose();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      handleSave();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ pb: 2 }}>
        {editingEmployee ? 'Edit Employee' : 'Add New Employee'}
      </DialogTitle>
      <DialogContent sx={{ overflowX: 'hidden', pb: 3 }}>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          {/* Row 1: Employee ID, Name, and Contract Type in one row */}
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="Employee ID"
              value={formData.id}
              onChange={(e) => handleChange('id', e.target.value)}
              onKeyPress={handleKeyPress}
              error={!!errors.id}
              helperText={errors.id || 'Unique identifier'}
              required
              disabled={!!editingEmployee}
              placeholder="e.g., EMP001"
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="Employee Name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              onKeyPress={handleKeyPress}
              helperText="Optional"
              placeholder="e.g., John Doe"
            />
          </Grid>

          <Grid item xs={12} sm={4}>
            <FormControl fullWidth error={!!errors.contractType} required>
              <InputLabel>Contract Type</InputLabel>
              <Select
                value={formData.contractType}
                onChange={(e) => handleChange('contractType', e.target.value)}
                label="Contract Type"
              >
                {availableContracts.length === 0 ? (
                  <MenuItem value="">
                    <em>No contracts available</em>
                  </MenuItem>
                ) : (
                  availableContracts.map((contractId) => (
                    <MenuItem key={contractId} value={contractId}>
                      {contractId}
                    </MenuItem>
                  ))
                )}
              </Select>
              <FormHelperText>
                {errors.contractType || 'Select contract type'}
              </FormHelperText>
            </FormControl>
          </Grid>

          {/* Divider */}
          <Grid item xs={12} sx={{ my: 2 }}>
            <Divider sx={{ borderBottomWidth: 2, borderColor: 'divider' }} />
          </Grid>

          {/* Row 2: Teams or Competencies - Full width */}
          {/* TEAM MODEL: Team Selection */}
          {employeeModel === 'team' && (
            <Grid item xs={12}>
              <Box sx={{ width: '100%' }}>
                <Autocomplete
                  multiple
                  fullWidth
                  options={availableTeams.map(t => t.code)}
                  value={formData.teams}
                  onChange={(e, newValue) => handleChange('teams', newValue)}
                  getOptionLabel={(option) => {
                    const team = availableTeams.find(t => t.code === option);
                    return team ? `${team.code} - ${team.name}` : option;
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Teams"
                      error={!!errors.teams}
                      helperText={errors.teams || 'Select one or more teams'}
                      required
                      fullWidth
                    />
                  )}
                  renderTags={(value, getTagProps) =>
                    value.map((option, index) => {
                      const team = availableTeams.find(t => t.code === option);
                      return (
                        <Chip
                          label={team ? `${team.code} - ${team.name}` : option}
                          {...getTagProps({ index })}
                          color="primary"
                          size="small"
                        />
                      );
                    })
                  }
                />
              </Box>
            </Grid>
          )}

          {/* COMPETENCY MODEL: Team Assignment with Levels */}
          {employeeModel === 'competency' && (
            <Grid item xs={12}>
              <Box sx={{ width: '100%' }}>
                <CompetencyBuilder
                  competencies={formData.teams}
                  availableCompetencies={availableTeams}
                  onChange={(newTeams) => handleChange('teams', newTeams)}
                  error={errors.teams}
                />
              </Box>
            </Grid>
          )}

          {/* General Errors */}
          {Object.keys(errors).length > 0 && !errors.teams && (
            <Grid item xs={12}>
              <Alert severity="error">
                Please fix the errors above before saving.
              </Alert>
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, pt: 2 }}>
        <Button onClick={onClose} size="large">
          Cancel
        </Button>
        <Button variant="contained" onClick={handleSave} size="large">
          {editingEmployee ? 'Update' : 'Add'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EmployeeForm;

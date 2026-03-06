import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Grid,
  Alert
} from '@mui/material';

/**
 * OrganizationalUnitForm Component
 *
 * Dialog for adding/editing teams.
 */
const OrganizationalUnitForm = ({
  open,
  onClose,
  onSave,
  editingItem = null,
  existingCodes = []
}) => {
  const [formData, setFormData] = useState({
    code: '',
    name: ''
  });
  const [errors, setErrors] = useState({});

  // Initialize form when editing
  useEffect(() => {
    if (editingItem) {
      setFormData(editingItem);
    } else {
      setFormData({ code: '', name: '' });
    }
    setErrors({});
  }, [editingItem, open]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    // Code validation
    if (!formData.code.trim()) {
      newErrors.code = 'Team code is required';
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.code)) {
      newErrors.code = 'Code must be alphanumeric (letters, numbers, underscores only)';
    } else if (
      !editingItem &&
      existingCodes.some(c => c.toLowerCase() === formData.code.trim().toLowerCase())
    ) {
      newErrors.code = 'Team code already exists';
    }

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Team name is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validate()) {
      onSave({
        code: formData.code.trim(),
        name: formData.name.trim()
      });
      onClose();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {editingItem ? 'Edit Team' : 'Add New Team'}
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Team Code"
              value={formData.code}
              onChange={(e) => handleChange('code', e.target.value)}
              onKeyPress={handleKeyPress}
              error={!!errors.code}
              helperText={errors.code || 'Unique identifier (e.g., A, B, TEAM_1, SALES)'}
              required
              disabled={!!editingItem}
              placeholder="e.g., A, SALES"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Team Name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              onKeyPress={handleKeyPress}
              error={!!errors.name}
              helperText={errors.name || 'Human-readable name (e.g., Team A, Sales Team, Department B)'}
              required
              placeholder="e.g., Sales Team"
            />
          </Grid>
          {Object.keys(errors).length > 0 && (
            <Grid item xs={12}>
              <Alert severity="error">
                Please fix the errors above before saving.
              </Alert>
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave}>
          {editingItem ? 'Update' : 'Add'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default OrganizationalUnitForm;

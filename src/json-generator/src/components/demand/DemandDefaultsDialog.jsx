import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Button,
  TextField,
  Box,
  Typography,
  Alert
} from '@mui/material';
import { AutoAwesome as AutoAwesomeIcon } from '@mui/icons-material';
import { validateDemandDefaults } from '../../utils/validators/demandValidator';

/**
 * DemandDefaultsDialog - Dialog for setting default values for demand entries
 *
 * Allows user to set default minimum, ideal, and estimated values
 * that will be applied to all missing demand entries
 */
const DemandDefaultsDialog = ({
  open,
  onClose,
  onApply,
  missingCount = 0
}) => {
  const [defaults, setDefaults] = useState({
    minimum: 1,
    ideal: 1,
    estimated: 1
  });

  const [touched, setTouched] = useState({});
  const [errors, setErrors] = useState({});

  // Reset when dialog opens
  useEffect(() => {
    if (open) {
      setDefaults({ minimum: 1, ideal: 1, estimated: 1 });
      setTouched({});
      setErrors({});
    }
  }, [open]);

  const handleChange = (field, value) => {
    setDefaults(prev => ({ ...prev, [field]: value }));
    setTouched(prev => ({ ...prev, [field]: true }));

    // Clear error for this field
    setErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[field];
      return newErrors;
    });
  };

  const handleApply = () => {
    // Validate
    const validation = validateDemandDefaults(defaults);

    if (!validation.valid) {
      setErrors(validation.errors);
      setTouched({ minimum: true, ideal: true, estimated: true });
      return;
    }

    // Apply defaults
    onApply({
      minimum: Number(defaults.minimum),
      ideal: Number(defaults.ideal),
      estimated: Number(defaults.estimated)
    });
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <AutoAwesomeIcon color="secondary" />
        Auto-fill Missing Demand Entries
      </DialogTitle>

      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          You have <strong>{missingCount}</strong> missing demand entries (combinations of dates, work periods, and teams/competencies).
          Set the default values below to fill them automatically.
        </DialogContentText>

        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            These defaults will be applied to all missing entries. You can edit individual entries later if needed.
            Remember: <strong>minimum ≤ estimated ≤ ideal</strong>
          </Typography>
        </Alert>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Minimum */}
          <TextField
            label="Default Minimum Coverage"
            type="number"
            value={defaults.minimum}
            onChange={(e) => handleChange('minimum', e.target.value)}
            error={touched.minimum && !!errors.minimum}
            helperText={touched.minimum && errors.minimum ? errors.minimum : 'Absolute minimum staff required'}
            fullWidth
            inputProps={{ min: 0, step: 1 }}
          />

          {/* Estimated */}
          <TextField
            label="Default Estimated Coverage"
            type="number"
            value={defaults.estimated}
            onChange={(e) => handleChange('estimated', e.target.value)}
            error={touched.estimated && !!errors.estimated}
            helperText={touched.estimated && errors.estimated ? errors.estimated : 'Expected actual coverage'}
            fullWidth
            inputProps={{ min: 0, step: 1 }}
          />

          {/* Ideal */}
          <TextField
            label="Default Ideal Coverage"
            type="number"
            value={defaults.ideal}
            onChange={(e) => handleChange('ideal', e.target.value)}
            error={touched.ideal && !!errors.ideal}
            helperText={touched.ideal && errors.ideal ? errors.ideal : 'Optimal coverage (soft constraint)'}
            fullWidth
            inputProps={{ min: 0, step: 1 }}
          />
        </Box>

        <Alert severity="warning" sx={{ mt: 2 }}>
          <Typography variant="body2">
            This will create {missingCount} new demand entries. Existing entries will not be modified.
          </Typography>
        </Alert>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Button onClick={handleApply} variant="contained" color="secondary">
          Apply Defaults
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DemandDefaultsDialog;

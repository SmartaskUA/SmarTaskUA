import React, { useState } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Typography,
  Alert,
  Chip,
  Switch,
  FormControlLabel,
  Divider
} from '@mui/material';
import ConstraintCard from './ConstraintCard';

/**
 * ConstraintsList Component
 *
 * Displays all constraints organized into tabs:
 * - Hard Constraints
 * - Soft Constraints
 * - Advanced Settings
 */
const ConstraintsList = ({ constraints, onChange }) => {
  const [currentTab, setCurrentTab] = useState(0);

  const { hard = [], soft = [], advanced = {} } = constraints;

  // Count enabled constraints
  const enabledHardCount = hard.filter(c => c.enabled).length;
  const enabledSoftCount = soft.filter(c => c.enabled).length;

  // Handle constraint change
  const handleConstraintChange = (constraintType, index, updatedConstraint) => {
    const newConstraints = { ...constraints };

    if (constraintType === 'hard') {
      newConstraints.hard = [...hard];
      newConstraints.hard[index] = updatedConstraint;
    } else if (constraintType === 'soft') {
      newConstraints.soft = [...soft];
      newConstraints.soft[index] = updatedConstraint;
    }

    onChange(newConstraints);
  };

  // Handle advanced setting change
  const handleAdvancedChange = (setting, value) => {
    const newConstraints = {
      ...constraints,
      advanced: {
        ...advanced,
        [setting]: value
      }
    };
    onChange(newConstraints);
  };

  return (
    <Box>
      {/* Summary Stats */}
      <Box sx={{ mb: 2, p: 2, backgroundColor: 'action.hover', borderRadius: 1 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          Constraint Summary
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip
            label={`Hard: ${enabledHardCount}/${hard.length} enabled`}
            color={enabledHardCount > 0 ? 'error' : 'default'}
            variant={enabledHardCount > 0 ? 'filled' : 'outlined'}
          />
          <Chip
            label={`Soft: ${enabledSoftCount}/${soft.length} enabled`}
            color={enabledSoftCount > 0 ? 'warning' : 'default'}
            variant={enabledSoftCount > 0 ? 'filled' : 'outlined'}
          />
          <Chip
            label={`Advanced: ${advanced.dayOffSwapping?.enabled || advanced.breaks?.enabled ? 'Active' : 'Inactive'}`}
            color={advanced.dayOffSwapping?.enabled || advanced.breaks?.enabled ? 'primary' : 'default'}
            variant={advanced.dayOffSwapping?.enabled || advanced.breaks?.enabled ? 'filled' : 'outlined'}
          />
        </Box>
      </Box>

      {/* Tabs */}
      <Tabs
        value={currentTab}
        onChange={(e, newValue) => setCurrentTab(newValue)}
        sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              Hard Constraints
              {enabledHardCount > 0 && (
                <Chip
                  label={enabledHardCount}
                  size="small"
                  color="error"
                  sx={{ height: 20, minWidth: 20 }}
                />
              )}
            </Box>
          }
        />
        <Tab
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              Soft Constraints
              {enabledSoftCount > 0 && (
                <Chip
                  label={enabledSoftCount}
                  size="small"
                  color="warning"
                  sx={{ height: 20, minWidth: 20 }}
                />
              )}
            </Box>
          }
        />
        <Tab label="Advanced" />
      </Tabs>

      {/* Tab Panels */}
      <Box>
        {/* Hard Constraints Tab */}
        {currentTab === 0 && (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Hard constraints</strong> are strict requirements that must be satisfied.
                Violations will prevent the schedule from being generated.
              </Typography>
            </Alert>

            {hard.length === 0 ? (
              <Typography color="text.secondary">No hard constraints defined.</Typography>
            ) : (
              hard.map((constraint, index) => (
                <ConstraintCard
                  key={constraint.id}
                  constraint={constraint}
                  constraintType="hard"
                  onChange={(updated) => handleConstraintChange('hard', index, updated)}
                />
              ))
            )}
          </Box>
        )}

        {/* Soft Constraints Tab */}
        {currentTab === 1 && (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                <strong>Soft constraints</strong> are preferences that the solver will try to satisfy.
                Each has a <strong>weight</strong> that controls its priority. Higher weights = higher priority.
              </Typography>
            </Alert>

            {soft.length === 0 ? (
              <Typography color="text.secondary">No soft constraints defined.</Typography>
            ) : (
              soft.map((constraint, index) => (
                <ConstraintCard
                  key={constraint.id}
                  constraint={constraint}
                  constraintType="soft"
                  onChange={(updated) => handleConstraintChange('soft', index, updated)}
                />
              ))
            )}
          </Box>
        )}

        {/* Advanced Tab */}
        {currentTab === 2 && (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2">
                Advanced settings for special scheduling rules and break management.
              </Typography>
            </Alert>

            {/* Day-Off Swapping */}
            <Box sx={{ mb: 3, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Box>
                  <Typography variant="h6" fontSize={16} fontWeight={600}>
                    Day-Off Swapping
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Allow employees to swap days off within the same week
                  </Typography>
                </Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={advanced.dayOffSwapping?.enabled || false}
                      onChange={(e) =>
                        handleAdvancedChange('dayOffSwapping', {
                          ...(advanced.dayOffSwapping || {}),
                          enabled: e.target.checked
                        })
                      }
                    />
                  }
                  label={advanced.dayOffSwapping?.enabled ? 'Enabled' : 'Disabled'}
                  labelPlacement="start"
                />
              </Box>

              {advanced.dayOffSwapping?.enabled && (
                <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary">
                    Week Definition: {advanced.dayOffSwapping?.weekDefinition || 'monday-sunday'}
                  </Typography>
                </Box>
              )}
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Breaks */}
            <Box sx={{ mb: 3, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Box>
                  <Typography variant="h6" fontSize={16} fontWeight={600}>
                    Break Rules
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Apply break rules defined in work periods
                  </Typography>
                </Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={advanced.breaks?.enabled || false}
                      onChange={(e) =>
                        handleAdvancedChange('breaks', {
                          ...(advanced.breaks || {}),
                          enabled: e.target.checked
                        })
                      }
                    />
                  }
                  label={advanced.breaks?.enabled ? 'Enabled' : 'Disabled'}
                  labelPlacement="start"
                />
              </Box>

              {advanced.breaks?.enabled && (
                <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary">
                    Mode: {advanced.breaks?.mode || 'with_breaks'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Breaks configured in Step 6 (Work Periods) will be applied during scheduling.
                  </Typography>
                </Box>
              )}
            </Box>

            <Alert severity="warning" sx={{ mt: 2 }}>
              <Typography variant="body2">
                Note: Advanced settings require additional configuration in their respective steps.
                Enabling these features without proper setup may cause scheduling errors.
              </Typography>
            </Alert>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default ConstraintsList;

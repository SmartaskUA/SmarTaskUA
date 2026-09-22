import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Switch,
  FormControlLabel,
  Slider,
  Chip
} from '@mui/material';
import { CheckCircle, Circle } from '@mui/icons-material';
import ParamEditor from './ParamEditor';
import { CONSTRAINT_METADATA } from '../../utils/constraintMetadata';

/**
 * ConstraintCard Component
 *
 * Displays a single constraint with:
 * - Name and description
 * - Enable/disable toggle
 * - Parameter editors (if applicable)
 * - Weight slider (soft constraints only)
 */
const ConstraintCard = ({
  constraint,
  constraintType,  // 'hard' or 'soft'
  onChange
}) => {
  const metadata = CONSTRAINT_METADATA[constraint.id] || CONSTRAINT_METADATA[constraint.type];

  if (!metadata) {
    console.warn(`No metadata found for constraint: ${constraint.id}`);
    return null;
  }

  const { name, description, params: paramMetadata = {} } = metadata;

  // Handle enable/disable toggle
  const handleToggle = (event) => {
    onChange({
      ...constraint,
      enabled: event.target.checked
    });
  };

  // Handle parameter change
  const handleParamChange = (paramName, value) => {
    onChange({
      ...constraint,
      params: {
        ...(constraint.params || {}),
        [paramName]: value
      }
    });
  };

  // Handle weight change (soft constraints only)
  const handleWeightChange = (event, newValue) => {
    onChange({
      ...constraint,
      weight: newValue
    });
  };

  const hasParams = Object.keys(paramMetadata).length > 0;
  const isEnabled = constraint.enabled;

  return (
    <Card
      sx={{
        mb: 2,
        border: 1,
        borderColor: isEnabled ? 'primary.main' : 'divider',
        backgroundColor: isEnabled ? 'action.hover' : 'background.paper',
        transition: 'all 0.2s'
      }}
    >
      <CardContent>
        {/* Header: Name + Toggle */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Box sx={{ flexGrow: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              {isEnabled ? (
                <CheckCircle color="primary" fontSize="small" />
              ) : (
                <Circle color="disabled" fontSize="small" />
              )}
              <Typography variant="h6" fontSize={16} fontWeight={600}>
                {name}
              </Typography>
              {constraintType === 'hard' && (
                <Chip label="Hard" size="small" color="error" variant="outlined" />
              )}
              {constraintType === 'soft' && (
                <Chip label="Soft" size="small" color="warning" variant="outlined" />
              )}
            </Box>
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          </Box>

          <FormControlLabel
            control={
              <Switch
                checked={isEnabled}
                onChange={handleToggle}
                color="primary"
              />
            }
            label={isEnabled ? 'Enabled' : 'Disabled'}
            labelPlacement="start"
            sx={{ ml: 2, minWidth: 120 }}
          />
        </Box>

        {/* Parameters Editor */}
        {isEnabled && hasParams && (
          <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              Parameters
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              {Object.entries(paramMetadata).map(([paramName, paramConfig]) => (
                <ParamEditor
                  key={paramName}
                  paramName={paramName}
                  paramConfig={paramConfig}
                  value={constraint.params?.[paramName]}
                  onChange={(value) => handleParamChange(paramName, value)}
                />
              ))}
            </Box>
          </Box>
        )}

        {/* Weight Slider (Soft Constraints Only) */}
        {constraintType === 'soft' && isEnabled && (
          <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle2" color="text.secondary">
                Weight (Penalty Multiplier)
              </Typography>
              <Chip
                label={constraint.weight || 0}
                size="small"
                color="primary"
                sx={{ fontWeight: 'bold', minWidth: 60 }}
              />
            </Box>
            <Slider
              value={constraint.weight || 0}
              onChange={handleWeightChange}
              min={0}
              max={10000}
              step={10}
              marks={[
                { value: 0, label: '0' },
                { value: 100, label: '100' },
                { value: 1000, label: '1k' },
                { value: 5000, label: '5k' },
                { value: 10000, label: '10k' }
              ]}
              valueLabelDisplay="auto"
              sx={{ mt: 1 }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Higher weights prioritize this constraint more heavily in the optimization.
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default ConstraintCard;

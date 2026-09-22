import React from 'react';
import {
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Box
} from '@mui/material';

/**
 * ParamEditor Component
 *
 * Dynamic parameter editor that renders different input types based on configuration:
 * - Number inputs with min/max validation
 * - Text inputs
 * - Dropdown selectors for enum values
 */
const ParamEditor = ({
  paramName,
  paramConfig,
  value,
  onChange
}) => {
  const { label, type, min, max, options, defaultValue } = paramConfig;

  const currentValue = value !== undefined ? value : (defaultValue !== undefined ? defaultValue : '');

  // Handle change for all input types
  const handleChange = (event) => {
    const newValue = event.target.value;

    if (type === 'number') {
      const numValue = parseFloat(newValue);
      // Validate min/max
      if (!isNaN(numValue)) {
        if (min !== undefined && numValue < min) return;
        if (max !== undefined && numValue > max) return;
        onChange(numValue);
      } else if (newValue === '') {
        onChange(defaultValue !== undefined ? defaultValue : 0);
      }
    } else {
      onChange(newValue);
    }
  };

  // Render dropdown for options
  if (options && Array.isArray(options)) {
    return (
      <FormControl sx={{ minWidth: 200 }} size="small">
        <InputLabel>{label}</InputLabel>
        <Select
          value={currentValue}
          onChange={handleChange}
          label={label}
        >
          {options.map(option => (
            <MenuItem key={option.value || option} value={option.value || option}>
              {option.label || option}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  }

  // Render number input
  if (type === 'number') {
    return (
      <TextField
        label={label}
        type="number"
        value={currentValue}
        onChange={handleChange}
        size="small"
        sx={{ minWidth: 150 }}
        inputProps={{
          min: min,
          max: max,
          step: 1
        }}
        helperText={
          min !== undefined && max !== undefined
            ? `Range: ${min}-${max}`
            : min !== undefined
            ? `Min: ${min}`
            : max !== undefined
            ? `Max: ${max}`
            : undefined
        }
      />
    );
  }

  // Render text input (default)
  return (
    <TextField
      label={label}
      type="text"
      value={currentValue}
      onChange={handleChange}
      size="small"
      sx={{ minWidth: 200 }}
    />
  );
};

export default ParamEditor;

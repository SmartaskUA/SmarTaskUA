import React from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Paper,
  Grid,
  Chip
} from '@mui/material';

/**
 * ColumnMapper Component
 *
 * UI for mapping CSV columns to expected fields.
 * Used during CSV import to match user's CSV structure to our schema.
 */
const ColumnMapper = ({ csvColumns, fieldMappings, onMappingChange, requiredFields = [] }) => {
  const handleChange = (targetField, csvColumn) => {
    onMappingChange({
      ...fieldMappings,
      [targetField]: csvColumn
    });
  };

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        Map CSV Columns
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Match your CSV columns to the required fields below.
      </Typography>

      <Grid container spacing={2}>
        {Object.keys(fieldMappings).map((targetField) => {
          const isRequired = requiredFields.includes(targetField);
          const selectedValue = fieldMappings[targetField] || '';

          return (
            <Grid item xs={12} sm={6} key={targetField}>
              <FormControl fullWidth size="small">
                <InputLabel>
                  {formatFieldName(targetField)}
                  {isRequired && ' *'}
                </InputLabel>
                <Select
                  value={selectedValue}
                  onChange={(e) => handleChange(targetField, e.target.value)}
                  label={`${formatFieldName(targetField)}${isRequired ? ' *' : ''}`}
                >
                  <MenuItem value="">
                    <em>-- Skip this field --</em>
                  </MenuItem>
                  {csvColumns.map((col) => (
                    <MenuItem key={col} value={col}>
                      {col}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          );
        })}
      </Grid>

      {/* Required Fields Summary */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Required fields:{' '}
        </Typography>
        {requiredFields.map((field, idx) => (
          <Chip
            key={field}
            label={formatFieldName(field)}
            size="small"
            color={fieldMappings[field] ? 'success' : 'default'}
            sx={{ mr: 0.5 }}
          />
        ))}
      </Box>
    </Paper>
  );
};

/**
 * Helper function to format field names for display
 */
const formatFieldName = (fieldName) => {
  return fieldName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
};

export default ColumnMapper;

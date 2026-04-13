import React, { useMemo } from 'react';
import { Select, MenuItem, TextField } from '@mui/material';
import { styled } from '@mui/material/styles';
import { isTimeConstraint, getConstraintType } from '../../utils/validators/timeConstraintValidator';

/**
 * Get cell background color based on value type
 */
function getCellColor(value) {
  if (!value || value === '') return '#ffffff';

  const val = value.toString().trim();

  // Check for time window constraints first (v2.2: EQUALS, INCLUDE, EXCEPT)
  if (isTimeConstraint(val)) {
    const type = getConstraintType(val);
    switch (type) {
      case 'EQUALS':
        return '#e1bee7'; // purple - must work exactly this time
      case 'INCLUDE':
        return '#ffe0b2'; // orange - must cover minimum
      case 'EXCEPT':
        return '#f8bbd0'; // pink - unavailable
      default:
        return '#ffffff';
    }
  }

  const valUpper = val.toUpperCase();

  // Auto-allocate
  if (valUpper === 'A') return '#e8f5e9'; // light green

  // Vacation
  if (valUpper === 'VAC') return '#fff9c4'; // light yellow

  // Not available (plain NOT, not time constraint)
  if (valUpper === 'NOT') return '#ffebee'; // light red

  // Numeric hours (custom hours)
  const numVal = parseFloat(val);
  if (!isNaN(numVal) && numVal > 0) return '#e3f2fd'; // light blue

  return '#ffffff';
}

const StyledSelect = styled(Select)(({ theme, bgcolor }) => ({
  width: '100%',
  height: '100%',
  minHeight: '40px',
  backgroundColor: bgcolor,
  borderRadius: 0,
  '& .MuiSelect-select': {
    padding: '10px 8px',
    fontSize: '13px',
    fontWeight: 600,
    textAlign: 'center',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  '& .MuiOutlinedInput-notchedOutline': {
    border: '1px solid #e0e0e0',
    borderRadius: 0
  },
  '&:hover .MuiOutlinedInput-notchedOutline': {
    borderColor: theme.palette.primary.main
  },
  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
    borderColor: theme.palette.primary.main,
    borderWidth: '2px'
  }
}));

const StyledTextField = styled(TextField)(({ theme, bgcolor, error }) => ({
  width: '100%',
  height: '100%',
  '& .MuiInputBase-root': {
    height: '100%',
    minHeight: '40px',
    backgroundColor: bgcolor,
    borderRadius: 0
  },
  '& .MuiOutlinedInput-input': {
    padding: '10px 8px',
    fontSize: '13px',
    fontWeight: 600,
    textAlign: 'center',
    height: '100%'
  },
  '& .MuiOutlinedInput-notchedOutline': {
    border: error ? `2px solid ${theme.palette.error.main}` : '1px solid #e0e0e0',
    borderRadius: 0
  },
  '&:hover .MuiOutlinedInput-notchedOutline': {
    borderColor: error ? theme.palette.error.main : theme.palette.primary.main
  },
  '& .Mui-focused .MuiOutlinedInput-notchedOutline': {
    borderColor: error ? theme.palette.error.main : theme.palette.primary.main,
    borderWidth: '2px'
  }
}));

/**
 * MatrixCell - Cell for schedule matrix
 *
 * Supports 4 options:
 * - 'A' for auto-allocate
 * - Custom hours (any number input)
 * - 'VAC' for vacation
 * - 'NOT' for not available
 */
const MatrixCell = ({
  value,
  onChange,
  employeeId,
  date,
  employee,
  contracts
}) => {
  // Check if current value is numeric or custom input mode
  const isNumericValue = useMemo(() => {
    if (!value) return false;
    const val = value.toString().trim();

    // If it's '-', we're in custom input mode
    if (val === '-') return true;

    const numVal = parseFloat(val);
    return !isNaN(numVal) && numVal > 0;
  }, [value]);

  // Validate if the numeric value is valid (not '-', not empty, is a positive number <= 24)
  const isValidNumber = useMemo(() => {
    if (!value) return false;
    const val = value.toString().trim();

    // '-' is invalid
    if (val === '-' || val === '') return false;

    const numVal = parseFloat(val);
    return !isNaN(numVal) && numVal > 0 && numVal <= 24;
  }, [value]);

  // Define dropdown options (removed contract hours)
  const options = [
    { value: 'A', label: 'A - Auto-allocate', color: '#e8f5e9' },
    { value: 'CUSTOM', label: 'Custom hours', color: '#e3f2fd' },
    { value: 'VAC', label: 'VAC - Vacation', color: '#fff9c4' },
    { value: 'NOT', label: 'NOT - Not available', color: '#ffebee' }
  ];

  // Normalize value for display
  const displayValue = useMemo(() => {
    if (!value) return 'A';

    const val = value.toString().toUpperCase();

    if (['A', 'VAC', 'NOT'].includes(val)) {
      return val;
    }

    // If numeric or '-', we'll show the TextField instead
    if (isNumericValue) {
      return value.toString();
    }

    return 'A';
  }, [value, isNumericValue]);

  const handleSelectChange = (event) => {
    const newValue = event.target.value;

    if (newValue === 'CUSTOM') {
      // Switch to custom hours input with '-' as placeholder
      onChange(employeeId, date, '-');
    } else {
      onChange(employeeId, date, newValue);
    }
  };

  const handleTextFieldChange = (event) => {
    const newValue = event.target.value;

    // Allow empty or numeric values only (including decimal numbers)
    if (newValue === '' || /^\d*\.?\d*$/.test(newValue)) {
      onChange(employeeId, date, newValue || '-');
    }
  };

  const handleTextFieldKeyDown = (event) => {
    // Allow switching back to dropdown by pressing Escape
    if (event.key === 'Escape') {
      onChange(employeeId, date, 'A');
    }
  };

  // If value is numeric or in custom input mode, show TextField
  if (isNumericValue) {
    return (
      <StyledTextField
        value={displayValue === '-' ? '' : displayValue}
        onChange={handleTextFieldChange}
        onKeyDown={handleTextFieldKeyDown}
        type="text"
        size="small"
        bgcolor={getCellColor(value)}
        error={!isValidNumber}
        placeholder="Enter hours (max 24)"
        inputProps={{
          style: { textAlign: 'center' }
        }}
        InputProps={{
          sx: {
            '& input::placeholder': {
              textAlign: 'center',
              fontSize: '11px',
              opacity: 0.6
            }
          }
        }}
      />
    );
  }

  // Otherwise show Select
  return (
    <StyledSelect
      value={displayValue}
      onChange={handleSelectChange}
      size="small"
      bgcolor={getCellColor(displayValue)}
    >
      {options.map((opt) => (
        <MenuItem key={opt.value} value={opt.value}>
          {opt.label}
        </MenuItem>
      ))}
    </StyledSelect>
  );
};

export default MatrixCell;

import React, { useMemo } from 'react';
import { Select, MenuItem, Box } from '@mui/material';
import { styled } from '@mui/material/styles';

/**
 * Get cell background color based on value type
 */
function getCellColor(value) {
  if (!value || value === '') return '#ffffff';

  const val = value.toString().trim().toUpperCase();

  // Auto-allocate
  if (val === 'A') return '#e8f5e9'; // light green

  // Vacation
  if (val === 'VAC') return '#fff9c4'; // light yellow

  // Not available
  if (val === 'NOT') return '#ffebee'; // light red

  // Numeric hours (specific hours from contract)
  const numVal = parseFloat(val);
  if (!isNaN(numVal) && numVal > 0) return '#e3f2fd'; // light blue

  return '#ffffff';
}

const StyledSelect = styled(Select)(({ theme, bgcolor }) => ({
  minWidth: '90px',
  backgroundColor: bgcolor,
  border: 'none',
  '& .MuiSelect-select': {
    padding: '6px 8px',
    fontSize: '13px',
    fontWeight: 600,
    textAlign: 'center'
  },
  '& .MuiOutlinedInput-notchedOutline': {
    border: '1px solid #e0e0e0'
  },
  '&:hover .MuiOutlinedInput-notchedOutline': {
    borderColor: theme.palette.primary.main
  },
  '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
    borderColor: theme.palette.primary.main,
    borderWidth: '2px'
  }
}));

/**
 * MatrixCell - Dropdown cell for schedule matrix
 *
 * Supports 4 options:
 * - 'A' for auto-allocate
 * - Specific hours (from employee's contract)
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
  // Get employee's contract to determine specific hours
  const contractHours = useMemo(() => {
    if (!employee || !contracts) return 8; // default fallback

    const contract = contracts.find(c => c.id === employee.contractType);
    return contract?.workHoursPerDay || 8;
  }, [employee, contracts]);

  // Define dropdown options
  const options = [
    { value: 'A', label: 'A - Auto-allocate', color: '#e8f5e9' },
    { value: contractHours.toString(), label: `${contractHours}h - Specific hours`, color: '#e3f2fd' },
    { value: 'VAC', label: 'VAC - Vacation', color: '#fff9c4' },
    { value: 'NOT', label: 'NOT - Not available', color: '#ffebee' }
  ];

  // Ensure value matches one of the options (normalize numeric values)
  const normalizedValue = useMemo(() => {
    if (!value) return 'A';

    const val = value.toString();

    // Check if it matches exactly
    if (['A', 'VAC', 'NOT'].includes(val.toUpperCase())) {
      return val.toUpperCase();
    }

    // Check if it's a numeric value (specific hours)
    const numVal = parseFloat(val);
    if (!isNaN(numVal) && numVal > 0) {
      return contractHours.toString();
    }

    return 'A'; // default
  }, [value, contractHours]);

  const handleChange = (event) => {
    const newValue = event.target.value;
    onChange(employeeId, date, newValue);
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
      <StyledSelect
        value={normalizedValue}
        onChange={handleChange}
        size="small"
        bgcolor={getCellColor(normalizedValue)}
      >
        {options.map((opt) => (
          <MenuItem key={opt.value} value={opt.value}>
            {opt.label}
          </MenuItem>
        ))}
      </StyledSelect>
    </Box>
  );
};

export default MatrixCell;

import React, { useMemo, useState } from 'react';
import { Select, MenuItem, TextField, Box, Typography, IconButton, Tooltip } from '@mui/material';
import { Edit as EditIcon, Close as CloseIcon, ArrowDropDown as ArrowDropDownIcon } from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import {
  isTimeConstraint,
  getConstraintType,
  parseTimeWindowConstraint
} from '../../utils/validators/timeConstraintValidator';
import TimeConstraintDialog from './TimeConstraintDialog';

/**
 * Get cell background color based on value type
 */
function getCellColor(value) {
  if (!value || value === '') return '#ffffff';

  const val = value.toString().trim();

  if (isTimeConstraint(val)) {
    const type = getConstraintType(val);
    switch (type) {
      case 'EQUALS': return '#e1bee7';
      case 'INCLUDE': return '#ffe0b2';
      case 'EXCEPT':  return '#f8bbd0';
      default:        return '#ffffff';
    }
  }

  const valUpper = val.toUpperCase();
  if (valUpper === 'A')   return '#e8f5e9';
  if (valUpper === 'VAC') return '#fff9c4';
  if (valUpper === 'NOT') return '#ffebee';

  const numVal = parseFloat(val);
  if (!isNaN(numVal) && numVal > 0) return '#e3f2fd';

  return '#ffffff';
}

const TYPE_BADGE = { EQUALS: 'EQUALS', INCLUDE: 'INCLUDE', EXCEPT: 'EXCEPT' };
const TYPE_BORDER = { EQUALS: '#ce93d8', INCLUDE: '#ffb74d', EXCEPT: '#f48fb1' };

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
 * MatrixCell - Editable cell in the schedule input matrix
 *
 * Supports:
 * - 'A'   auto-allocate from contract (green)
 * - 0-24  specific hours (blue)
 * - 'VAC' vacation (yellow)
 * - 'NOT' unavailable (red)
 * - 'EQUALS:HH:MM-HH:MM'  exact time window (purple)
 * - 'INCLUDE:HH:MM-HH:MM' minimum cover window (orange)
 * - 'EXCEPT:HH:MM-HH:MM'  blocked window (pink)
 */
const MatrixCell = ({
  value,
  onChange,
  employeeId,
  date,
  employee,
  contracts
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pendingType, setPendingType] = useState('EQUALS');

  const isNumericValue = useMemo(() => {
    if (!value) return false;
    const val = value.toString().trim();
    if (val === '-') return true;
    const numVal = parseFloat(val);
    return !isNaN(numVal) && numVal > 0;
  }, [value]);

  const isValidNumber = useMemo(() => {
    if (!value) return false;
    const val = value.toString().trim();
    if (val === '-' || val === '') return false;
    const numVal = parseFloat(val);
    return !isNaN(numVal) && numVal > 0 && numVal <= 24;
  }, [value]);

  const isTC = useMemo(() => isTimeConstraint(value), [value]);

  const options = [
    { value: 'A',      label: 'A — Auto-allocate',    color: '#e8f5e9' },
    { value: 'CUSTOM', label: 'Custom hours',          color: '#e3f2fd' },
    { value: 'VAC',    label: 'VAC — Vacation',        color: '#fff9c4' },
    { value: 'NOT',    label: 'NOT — Not available',   color: '#ffebee' },
    { value: 'TC',     label: 'Time constraint…',      color: '#e1bee7' }
  ];

  const displayValue = useMemo(() => {
    if (!value) return 'A';
    const val = value.toString().toUpperCase();
    if (['A', 'VAC', 'NOT'].includes(val)) return val;
    if (isNumericValue) return value.toString();
    return 'A';
  }, [value, isNumericValue]);

  const handleSelectChange = (event) => {
    const newValue = event.target.value;

    if (newValue === 'CUSTOM') {
      onChange(employeeId, date, '-');
      return;
    }

    if (newValue === 'TC') {
      setPendingType('EQUALS');
      setDialogOpen(true);
      return;
    }

    onChange(employeeId, date, newValue);
  };

  const handleTextFieldChange = (event) => {
    const newValue = event.target.value;
    if (newValue === '' || /^\d*\.?\d*$/.test(newValue)) {
      onChange(employeeId, date, newValue || '-');
    }
  };

  const handleTextFieldKeyDown = (event) => {
    if (event.key === 'Escape') {
      onChange(employeeId, date, 'A');
    }
  };

  // Return a numeric/"custom hours" cell to the category dropdown
  const handleBackToOptions = () => {
    onChange(employeeId, date, 'A');
  };

  const handleDialogSave = (constraintString) => {
    onChange(employeeId, date, constraintString);
  };

  const handleEditConstraint = () => {
    const parsed = parseTimeWindowConstraint(value);
    if (parsed) {
      setPendingType(parsed.type);
    }
    setDialogOpen(true);
  };

  const handleClearConstraint = () => {
    onChange(employeeId, date, 'A');
  };

  // ── Branch 1: time window constraint display ────────────────────────────────
  if (isTC) {
    const parsed = parseTimeWindowConstraint(value);
    const type   = parsed?.type || 'EQUALS';
    const badge  = TYPE_BADGE[type] || type;
    const bg     = getCellColor(value);
    const border = TYPE_BORDER[type] || '#ccc';

    return (
      <>
        <Box
          sx={{
            width: '100%',
            height: '100%',
            minHeight: '2.5rem',
            backgroundColor: bg,
            border: `1px solid ${border}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 0.75,
            overflow: 'hidden',
            boxSizing: 'border-box'
          }}
        >
          <Box sx={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
            <Typography
              component="div"
              sx={{
                fontSize: '0.6rem',
                fontWeight: 700,
                lineHeight: 1.2,
                color: 'text.secondary',
                whiteSpace: 'nowrap',
                textTransform: 'uppercase'
              }}
            >
              {badge}
            </Typography>
            <Typography
              component="div"
              sx={{
                fontSize: '0.65rem',
                fontFamily: 'monospace',
                fontWeight: 600,
                lineHeight: 1.3,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
            >
              {parsed ? `${parsed.start}–${parsed.end}` : value}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
            <Tooltip title="Edit" placement="top">
              <IconButton size="small" onClick={handleEditConstraint}>
                <EditIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Clear" placement="top">
              <IconButton size="small" onClick={handleClearConstraint}>
                <CloseIcon fontSize="inherit" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <TimeConstraintDialog
          open={dialogOpen}
          initialType={parsed?.type || pendingType}
          initialStart={parsed?.start || ''}
          initialEnd={parsed?.end || ''}
          onSave={handleDialogSave}
          onClose={() => setDialogOpen(false)}
        />
      </>
    );
  }

  // ── Branch 2: numeric / custom hours ───────────────────────────────────────
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
        inputProps={{ style: { textAlign: 'center' } }}
        InputProps={{
          endAdornment: (
            <Tooltip title="Back to categories" placement="top">
              <IconButton
                size="small"
                onClick={handleBackToOptions}
                edge="end"
                sx={{ p: 0.25 }}
              >
                <ArrowDropDownIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          ),
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

  // ── Branch 3: standard select dropdown ─────────────────────────────────────
  return (
    <>
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

      <TimeConstraintDialog
        open={dialogOpen}
        initialType={pendingType}
        initialStart=""
        initialEnd=""
        onSave={handleDialogSave}
        onClose={() => setDialogOpen(false)}
      />
    </>
  );
};

export default MatrixCell;

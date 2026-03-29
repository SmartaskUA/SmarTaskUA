import React, { useState } from 'react';
import {
  Box,
  Select,
  MenuItem,
  TextField,
  IconButton,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Alert,
  Chip
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';

/**
 * CompetencyBuilder Component (Actually: Team Assignment with Levels)
 *
 * UI for building an employee's team assignments with competency levels.
 * Used in EmployeeForm for competency-based model.
 * Despite the component name, it now works with teams + levels.
 */
const CompetencyBuilder = ({
  competencies = [],  // Selected teams for this employee: [{code, level, name}]
  availableCompetencies = [],  // All teams from Step 3: [{code, name}]
  onChange,
  error
}) => {
  const [selectedCode, setSelectedCode] = useState('');
  const [level, setLevel] = useState(1);
  const [addError, setAddError] = useState('');

  const handleAdd = () => {
    // Validation
    if (!selectedCode) {
      setAddError('Please select a team');
      return;
    }

    if (level < 1) {
      setAddError('Level must be at least 1');
      return;
    }

    // Check if team already added
    if (competencies.some(c => c.code === selectedCode)) {
      setAddError('This team is already added');
      return;
    }

    // Find team name from available teams
    const teamInfo = availableCompetencies.find(c => c.code === selectedCode);
    const name = teamInfo ? teamInfo.name : '';

    // Add team with level
    onChange([
      ...competencies,
      {
        code: selectedCode,
        level: parseInt(level),
        name: name
      }
    ]);

    // Reset form
    setSelectedCode('');
    setLevel(1);
    setAddError('');
  };

  const handleDelete = (codeToDelete) => {
    onChange(competencies.filter(c => c.code !== codeToDelete));
  };

  // Get available teams that haven't been added yet
  const remainingCompetencies = availableCompetencies.filter(
    ac => !competencies.some(c => c.code === ac.code)
  );

  return (
    <Box>
      {/* Add Team with Competency Level Form */}
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Add Team with Competency Level
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl sx={{ flexGrow: 1, minWidth: 0 }}>
            <InputLabel>Team</InputLabel>
            <Select
              value={selectedCode}
              onChange={(e) => {
                setSelectedCode(e.target.value);
                if (addError) setAddError('');
              }}
              label="Team"
            >
              {remainingCompetencies.length === 0 ? (
                <MenuItem value="">
                  <em>All teams added</em>
                </MenuItem>
              ) : (
                remainingCompetencies.map((comp) => (
                  <MenuItem key={comp.code} value={comp.code}>
                    {comp.code} - {comp.name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>

          <TextField
            type="number"
            label="Level"
            value={level}
            onChange={(e) => {
              setLevel(e.target.value);
              if (addError) setAddError('');
            }}
            inputProps={{ min: 1, step: 1 }}
            sx={{ width: 120, flexShrink: 0, flexGrow: 0 }}
            helperText="Competency level"
          />

          <IconButton
            color="primary"
            onClick={handleAdd}
            disabled={!selectedCode || remainingCompetencies.length === 0}
            sx={{
              bgcolor: 'primary.main',
              color: 'white',
              flexShrink: 0,
              flexGrow: 0,
              width: 56,
              height: 56,
              '&:hover': { bgcolor: 'primary.dark' },
              '&:disabled': { bgcolor: 'action.disabledBackground' }
            }}
          >
            <AddIcon />
          </IconButton>
        </Box>

        {addError && (
          <Alert severity="error" sx={{ mt: 1 }}>
            {addError}
          </Alert>
        )}
      </Paper>

      {/* Error from parent */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Current Teams List */}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Employee Teams ({competencies.length})
        </Typography>

        {competencies.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No teams added yet. Add at least one team with competency level above.
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {competencies.map((comp) => (
              <Box
                key={comp.code}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  p: 1.5,
                  bgcolor: 'background.default'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip label={comp.code} size="small" color="primary" />
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {comp.name || comp.code}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Competency Level: {comp.level}
                    </Typography>
                  </Box>
                </Box>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => handleDelete(comp.code)}
                  sx={{ ml: 1 }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
            ))}
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default CompetencyBuilder;

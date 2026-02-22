import React, { useRef } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Typography,
  Chip,
  Alert
} from '@mui/material';
import {
  FileUpload as FileUploadIcon,
  FileDownload as FileDownloadIcon,
  AutoAwesome as AutoAwesomeIcon,
  Add as AddIcon
} from '@mui/icons-material';

/**
 * DemandFilters - Filter controls and action buttons for demand management
 *
 * Provides:
 * - Team/Competency selection
 * - Date range filtering (future feature)
 * - Import/Export CSV
 * - Auto-fill remaining entries
 * - Add new entry
 */
const DemandFilters = ({
  selectedTeam,
  onTeamChange,
  teams = [],
  workPeriods = [],
  onImport,
  onExport,
  onAutoFill,
  onAdd,
  employeeModel = 'team',
  demandDataCount = 0
}) => {
  const fileInputRef = useRef(null);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      onImport(file);
      // Reset input so same file can be selected again
      event.target.value = '';
    }
  };

  const teamFieldLabel = employeeModel === 'team' ? 'Team' : 'Competency';

  return (
    <Box>
      {/* Main filter bar */}
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          mb: 2
        }}
      >
        {/* Team/Competency selector */}
        <FormControl sx={{ minWidth: 250 }}>
          <InputLabel>{teamFieldLabel}</InputLabel>
          <Select
            value={selectedTeam}
            onChange={(e) => onTeamChange(e.target.value)}
            label={teamFieldLabel}
            size="small"
          >
            <MenuItem value="">
              <em>All {employeeModel === 'team' ? 'Teams' : 'Competencies'}</em>
            </MenuItem>
            {teams.map((team) => (
              <MenuItem key={team.code} value={team.code}>
                {team.name} ({team.code})
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Add entry button */}
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={onAdd}
          disabled={!selectedTeam}
          size="small"
        >
          Add Entry
        </Button>

        {/* Spacer */}
        <Box sx={{ flexGrow: 1 }} />

        {/* Action buttons */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<FileUploadIcon />}
            onClick={handleImportClick}
            size="small"
          >
            Import CSV
          </Button>

          <Button
            variant="outlined"
            startIcon={<FileDownloadIcon />}
            onClick={onExport}
            disabled={demandDataCount === 0}
            size="small"
          >
            Export CSV
          </Button>

          <Button
            variant="outlined"
            startIcon={<AutoAwesomeIcon />}
            onClick={onAutoFill}
            color="secondary"
            size="small"
          >
            Auto-fill Remaining
          </Button>
        </Box>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
      </Box>

      {/* Info chips */}
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Typography variant="body2" color="text.secondary">
          Filter:
        </Typography>
        {selectedTeam ? (
          <Chip
            label={`${teamFieldLabel}: ${selectedTeam}`}
            size="small"
            onDelete={() => onTeamChange('')}
            color="primary"
          />
        ) : (
          <Chip
            label={`All ${employeeModel === 'team' ? 'Teams' : 'Competencies'}`}
            size="small"
            variant="outlined"
          />
        )}

        <Box sx={{ ml: 'auto' }}>
          <Typography variant="body2" color="text.secondary">
            Total entries: <strong>{demandDataCount}</strong>
          </Typography>
        </Box>
      </Box>

      {/* Help text */}
      {demandDataCount === 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          <Typography variant="body2">
            No demand entries yet. Select a {teamFieldLabel.toLowerCase()} and click <strong>"Add Entry"</strong> to create entries,
            or use <strong>"Auto-fill Remaining"</strong> to generate entries for all combinations.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default DemandFilters;

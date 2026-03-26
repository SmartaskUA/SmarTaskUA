import React, { useRef } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Chip,
  Divider
} from '@mui/material';
import {
  CalendarMonth as CalendarIcon,
  Upload as UploadIcon,
  Download as DownloadIcon,
  AutoFixHigh as AutoFillIcon,
  DeleteSweep as ClearIcon
} from '@mui/icons-material';

/**
 * DemandCalendarToolbar Component
 *
 * Toolbar for Phase 2 with template application and bulk actions
 *
 * @param {Function} onApplyTemplate - Called to apply weekly template to calendar
 * @param {Function} onImportCSV - Called when CSV is imported
 * @param {Function} onExportCSV - Called to export demand to CSV
 * @param {Function} onClearAll - Called to clear all demand data
 * @param {number} totalEntries - Number of demand entries
 * @param {boolean} hasTemplate - Whether a weekly template exists
 */
const DemandCalendarToolbar = ({
  onApplyTemplate,
  onImportCSV,
  onExportCSV,
  onClearAll,
  totalEntries = 0,
  hasTemplate = false
}) => {
  const fileInputRef = useRef(null);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      onImportCSV(file);
      // Reset file input
      event.target.value = '';
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 2,
        mb: 2,
        p: 2,
        backgroundColor: 'background.paper',
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider'
      }}
    >
      {/* Left side - Template actions */}
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          startIcon={<AutoFillIcon />}
          onClick={onApplyTemplate}
          disabled={!hasTemplate}
          size="small"
        >
          Apply Weekly Template
        </Button>

        {!hasTemplate && (
          <Chip
            label="Create template in Phase 1 first"
            size="small"
            color="warning"
            variant="outlined"
          />
        )}
      </Box>

      {/* Center - Stats */}
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        <Chip
          icon={<CalendarIcon />}
          label={`${totalEntries} demand ${totalEntries === 1 ? 'entry' : 'entries'}`}
          color="primary"
          variant="outlined"
        />
      </Box>

      {/* Right side - Import/Export */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        <ButtonGroup size="small" variant="outlined">
          <Button startIcon={<UploadIcon />} onClick={handleImportClick}>
            Import CSV
          </Button>
          <Button startIcon={<DownloadIcon />} onClick={onExportCSV} disabled={totalEntries === 0}>
            Export CSV
          </Button>
        </ButtonGroup>

        <Divider orientation="vertical" flexItem />

        <Button
          size="small"
          variant="outlined"
          color="error"
          startIcon={<ClearIcon />}
          onClick={onClearAll}
          disabled={totalEntries === 0}
        >
          Clear All
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
  );
};

export default DemandCalendarToolbar;

import React, { useState } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import {
  FileUpload as FileUploadIcon,
  FileDownload as FileDownloadIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';

/**
 * MatrixToolbar - Action buttons for schedule matrix
 */
const MatrixToolbar = ({
  onImportCsv,
  onExportCsv,
  onClearAll
}) => {
  const [confirmClearOpen, setConfirmClearOpen] = useState(false);

  const handleClearAll = () => {
    setConfirmClearOpen(false);
    if (onClearAll) {
      onClearAll();
    }
  };

  return (
    <>
      <Box sx={{
        display: 'flex',
        gap: 2,
        mb: 2,
        flexWrap: 'wrap',
        alignItems: 'center'
      }}>
        <ButtonGroup variant="outlined" size="small">
          <Button
            startIcon={<FileUploadIcon />}
            onClick={onImportCsv}
          >
            Import CSV
          </Button>
          <Button
            startIcon={<FileDownloadIcon />}
            onClick={onExportCsv}
          >
            Export CSV
          </Button>
        </ButtonGroup>

        <Button
          variant="outlined"
          size="small"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={() => setConfirmClearOpen(true)}
        >
          Clear All
        </Button>
      </Box>

      {/* Confirm Clear Dialog */}
      <Dialog
        open={confirmClearOpen}
        onClose={() => setConfirmClearOpen(false)}
      >
        <DialogTitle>Clear All Data?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will clear all schedule input data for all employees. This action cannot be undone.
            Are you sure you want to continue?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmClearOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleClearAll} color="error" variant="contained">
            Clear All
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default MatrixToolbar;

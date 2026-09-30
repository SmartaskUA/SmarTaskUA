import React, { useRef, useState } from 'react';
import { Box, Button, ButtonGroup } from '@mui/material';
import { FileUpload, FileDownload, RestartAlt, ClearAll } from '@mui/icons-material';
import { ConfirmDialog } from '../shared/fields';

/** Import / export schedule_input.csv, and bulk resets. */
const MatrixToolbar = ({ onImportCsv, onExportCsv, onResetAuto, onClearBlank }) => {
  const fileRef = useRef(null);
  const [confirm, setConfirm] = useState(null); // 'auto' | 'blank'

  return (
    <>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <ButtonGroup variant="outlined" size="small">
          <Button startIcon={<FileUpload />} onClick={() => fileRef.current?.click()}>Import CSV</Button>
          <Button startIcon={<FileDownload />} onClick={onExportCsv}>Export CSV</Button>
        </ButtonGroup>
        <ButtonGroup variant="outlined" size="small" color="warning">
          <Button startIcon={<RestartAlt />} onClick={() => setConfirm('auto')}>Reset all to A</Button>
          <Button startIcon={<ClearAll />} onClick={() => setConfirm('blank')}>Clear all to blank</Button>
        </ButtonGroup>
      </Box>
      <input
        ref={fileRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onImportCsv(file);
          e.target.value = '';
        }}
      />
      <ConfirmDialog
        open={!!confirm}
        title={confirm === 'auto' ? 'Reset every cell to A?' : 'Clear every cell?'}
        confirmLabel={confirm === 'auto' ? 'Reset' : 'Clear'}
        confirmColor="warning"
        onCancel={() => setConfirm(null)}
        onConfirm={() => { (confirm === 'auto' ? onResetAuto : onClearBlank)(); setConfirm(null); }}
      >
        {confirm === 'auto'
          ? 'Every day a contract covers becomes A (work the contract length); uncovered days become blank. Day-off codes and windows are lost.'
          : 'Every cell becomes blank — no assignments at all. This cannot be undone.'}
      </ConfirmDialog>
    </>
  );
};

export default MatrixToolbar;

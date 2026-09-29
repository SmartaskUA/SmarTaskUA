import React from 'react';
import { Card, CardContent, Typography, Button, Stack } from '@mui/material';
import { Download } from '@mui/icons-material';
import { bundleEntries } from '../../v4/generate';
import { downloadText } from '../../utils/download';

/** Every file of the bundle, one button each. */
const DownloadPanel = ({ bundle, disabled }) => (
  <Card variant="outlined">
    <CardContent>
      <Typography variant="h6" fontWeight={600} gutterBottom>Individual files</Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {bundleEntries(bundle).map(([name, text]) => (
          <Button
            key={name}
            variant="outlined"
            size="small"
            startIcon={<Download />}
            disabled={disabled}
            onClick={() => downloadText(name, text, name.endsWith('.json') ? 'application/json' : 'text/csv;charset=utf-8')}
            sx={{ textTransform: 'none' }}
          >
            {name}
          </Button>
        ))}
      </Stack>
    </CardContent>
  </Card>
);

export default DownloadPanel;

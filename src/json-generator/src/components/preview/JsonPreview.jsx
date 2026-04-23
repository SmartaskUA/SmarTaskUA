import React, { useState } from 'react';
import { Box, IconButton, Tooltip, Typography } from '@mui/material';
import { ContentCopy, Check } from '@mui/icons-material';

/**
 * JSON Preview Component
 *
 * Displays JSON with:
 * - Syntax highlighting (basic monospace with colors)
 * - Copy to clipboard button
 * - Line count display
 * - Scrollable view
 */
const JsonPreview = ({ json }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const jsonString = JSON.stringify(json, null, 2);
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const jsonString = JSON.stringify(json, null, 2);
  const lineCount = jsonString.split('\n').length;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {lineCount} lines • {(new Blob([jsonString]).size / 1024).toFixed(2)} KB
        </Typography>
        <Tooltip title={copied ? "Copied!" : "Copy to clipboard"}>
          <IconButton onClick={handleCopy} size="small" color={copied ? "success" : "default"}>
            {copied ? <Check /> : <ContentCopy />}
          </IconButton>
        </Tooltip>
      </Box>

      <Box
        component="pre"
        sx={{
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
          fontSize: 12,
          lineHeight: 1.6,
          maxHeight: 500,
          overflow: 'auto',
          backgroundColor: '#1e1e1e',
          color: '#d4d4d4',
          p: 2,
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'divider',
          '&::-webkit-scrollbar': {
            width: 8,
            height: 8
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: '#2b2b2b'
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: '#555',
            borderRadius: 4,
            '&:hover': {
              backgroundColor: '#666'
            }
          }
        }}
      >
        {jsonString}
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        💡 Use the copy button to copy the entire JSON to clipboard
      </Typography>
    </Box>
  );
};

export default JsonPreview;

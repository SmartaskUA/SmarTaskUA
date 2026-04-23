import React, { useState } from 'react';
import { Box, IconButton, Tooltip, Typography } from '@mui/material';
import { ContentCopy, Check } from '@mui/icons-material';

// VS Code dark+ inspired token colors
const TOKEN_COLORS = {
  key: '#9cdcfe',       // light blue  — object keys
  string: '#ce9178',    // orange-red  — string values
  number: '#b5cea8',    // green       — numbers
  boolean: '#569cd6',   // blue        — true / false
  null: '#569cd6',      // blue        — null
  punctuation: '#d4d4d4' // default    — braces, brackets, colons, commas
};

/**
 * Converts a JSON string to HTML with inline <span> colors.
 * Input is always JSON.stringify output — we control it, so dangerouslySetInnerHTML is safe.
 */
function highlightJson(raw) {
  // Escape HTML entities first so injected spans are the only markup
  const escaped = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return escaped.replace(
    /("(?:\\u[0-9a-fA-F]{4}|\\[^u]|[^\\"])*"(?:\s*:)?|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let color;
      if (match.startsWith('"')) {
        color = match.endsWith(':') ? TOKEN_COLORS.key : TOKEN_COLORS.string;
      } else if (match === 'true' || match === 'false') {
        color = TOKEN_COLORS.boolean;
      } else if (match === 'null') {
        color = TOKEN_COLORS.null;
      } else {
        color = TOKEN_COLORS.number;
      }
      return `<span style="color:${color}">${match}</span>`;
    }
  );
}

const JsonPreview = ({ json }) => {
  const [copied, setCopied] = useState(false);

  const jsonString = JSON.stringify(json, null, 2);
  const lineCount = jsonString.split('\n').length;

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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
        dangerouslySetInnerHTML={{ __html: highlightJson(jsonString) }}
        sx={{
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace',
          fontSize: 12,
          lineHeight: 1.6,
          maxHeight: 500,
          overflow: 'auto',
          backgroundColor: '#1e1e1e',
          color: TOKEN_COLORS.punctuation,
          p: 2,
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'divider',
          m: 0,
          '&::-webkit-scrollbar': { width: 8, height: 8 },
          '&::-webkit-scrollbar-track': { backgroundColor: '#2b2b2b' },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: '#555',
            borderRadius: 4,
            '&:hover': { backgroundColor: '#666' }
          }
        }}
      />
    </Box>
  );
};

export default JsonPreview;

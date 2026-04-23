import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Divider,
  CircularProgress
} from '@mui/material';
import { Download, ContentCopy } from '@mui/icons-material';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

/**
 * Download Panel Component
 *
 * Provides download options:
 * - Download all as ZIP (recommended)
 * - Download individual files
 * - Copy JSON to clipboard
 */
const DownloadPanel = ({ files, problemId }) => {
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);

  const { problemJson, demandCsv, scheduleInputCsv } = files;

  /**
   * Download problem.json file
   */
  const downloadJson = () => {
    const blob = new Blob(
      [JSON.stringify(problemJson, null, 2)],
      { type: 'application/json' }
    );
    saveAs(blob, 'problem.json');
  };

  /**
   * Download demand.csv file
   */
  const downloadDemandCsv = () => {
    const blob = new Blob([demandCsv], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, 'demand.csv');
  };

  /**
   * Download schedule_input.csv file
   */
  const downloadScheduleInputCsv = () => {
    const blob = new Blob([scheduleInputCsv], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, 'schedule_input.csv');
  };

  /**
   * Download all files as ZIP
   */
  const downloadZip = async () => {
    try {
      setDownloading(true);
      const zip = new JSZip();

      // Add files to ZIP
      zip.file('problem.json', JSON.stringify(problemJson, null, 2));
      zip.file('demand.csv', demandCsv);
      zip.file('schedule_input.csv', scheduleInputCsv);

      // Generate ZIP blob
      const blob = await zip.generateAsync({ type: 'blob' });

      // Download ZIP
      const filename = `${problemId || 'problem'}_scheduling_problem.zip`;
      saveAs(blob, filename);
    } catch (error) {
      console.error('ZIP creation failed:', error);
      alert('Failed to create ZIP file. Try downloading individual files instead.');
    } finally {
      setDownloading(false);
    }
  };

  /**
   * Copy JSON to clipboard
   */
  const copyJsonToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(problemJson, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom fontWeight={600}>
          Download Files
        </Typography>

        <Stack spacing={2}>
          {/* Main ZIP Download */}
          <Button
            variant="contained"
            size="large"
            startIcon={downloading ? <CircularProgress size={20} color="inherit" /> : <Download />}
            onClick={downloadZip}
            disabled={downloading}
            fullWidth
          >
            {downloading ? 'Creating ZIP...' : 'Download as ZIP (Recommended)'}
          </Button>

          <Divider />

          {/* Individual Downloads */}
          <Typography variant="subtitle2" color="text.secondary">
            Individual Files
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button
              variant="outlined"
              size="small"
              startIcon={<Download />}
              onClick={downloadJson}
            >
              problem.json
            </Button>
            <Button
              variant="outlined"
              size="small"
              startIcon={<Download />}
              onClick={downloadDemandCsv}
            >
              demand.csv
            </Button>
            <Button
              variant="outlined"
              size="small"
              startIcon={<Download />}
              onClick={downloadScheduleInputCsv}
            >
              schedule_input.csv
            </Button>
          </Stack>

          <Divider />

          {/* Copy to Clipboard */}
          <Button
            variant="text"
            size="small"
            startIcon={<ContentCopy />}
            onClick={copyJsonToClipboard}
            color={copied ? "success" : "primary"}
          >
            {copied ? 'Copied!' : 'Copy JSON to Clipboard'}
          </Button>
        </Stack>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          💡 Download the ZIP file to get all files at once, or download individual files separately.
        </Typography>
      </CardContent>
    </Card>
  );
};

export default DownloadPanel;

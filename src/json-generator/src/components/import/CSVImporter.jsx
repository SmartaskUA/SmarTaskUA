import React, { useState } from 'react';
import {
  Box,
  Button,
  Paper,
  Typography,
  Alert,
  CircularProgress,
  LinearProgress
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CheckCircle as CheckIcon
} from '@mui/icons-material';
import Papa from 'papaparse';

/**
 * CSVImporter Component
 *
 * Reusable CSV file uploader with drag-drop support.
 * Parses CSV and returns data to parent via onDataParsed callback.
 */
const CSVImporter = ({ onDataParsed, onError, acceptedExtensions = ['.csv'] }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [fileName, setFileName] = useState('');

  const parseFile = (file) => {
    setIsProcessing(true);
    setUploadSuccess(false);
    setFileName(file.name);

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        setIsProcessing(false);

        if (results.errors.length > 0) {
          const errorMsg = `CSV parsing errors: ${results.errors.map(e => e.message).join(', ')}`;
          if (onError) onError(errorMsg);
          return;
        }

        if (results.data.length === 0) {
          if (onError) onError('CSV file is empty or has no valid rows');
          return;
        }

        setUploadSuccess(true);
        setTimeout(() => setUploadSuccess(false), 3000);

        // Pass parsed data to parent
        onDataParsed({
          columns: results.meta.fields || [],
          rows: results.data,
          fileName: file.name
        });
      },
      error: (error) => {
        setIsProcessing(false);
        if (onError) onError(`Failed to parse CSV: ${error.message}`);
      }
    });
  };

  const handleFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      parseFile(file);
    }
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
        parseFile(file);
      } else {
        if (onError) onError('Please upload a CSV file');
      }
    }
  };

  return (
    <Box>
      <Paper
        variant="outlined"
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          p: 4,
          textAlign: 'center',
          border: '2px dashed',
          borderColor: isDragging ? 'primary.main' : 'divider',
          bgcolor: isDragging ? 'action.hover' : 'background.paper',
          transition: 'all 0.2s ease',
          cursor: 'pointer',
          position: 'relative'
        }}
      >
        {isProcessing ? (
          <Box>
            <CircularProgress size={48} sx={{ mb: 2 }} />
            <Typography variant="body1" color="text.secondary">
              Processing CSV file...
            </Typography>
            <LinearProgress sx={{ mt: 2, maxWidth: 300, mx: 'auto' }} />
          </Box>
        ) : uploadSuccess ? (
          <Box>
            <CheckIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
            <Typography variant="body1" color="success.main">
              File uploaded successfully!
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {fileName}
            </Typography>
          </Box>
        ) : (
          <>
            <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              {isDragging ? 'Drop CSV file here' : 'Drag & drop CSV file'}
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              or
            </Typography>
            <Button
              variant="contained"
              component="label"
              startIcon={<UploadIcon />}
            >
              Choose File
              <input
                type="file"
                hidden
                accept={acceptedExtensions.join(',')}
                onChange={handleFileInput}
              />
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
              Supported format: CSV (.csv)
            </Typography>
          </>
        )}
      </Paper>
    </Box>
  );
};

export default CSVImporter;

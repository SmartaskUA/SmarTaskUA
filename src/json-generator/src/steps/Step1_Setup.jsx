import React, { useState, useEffect } from 'react';
import {
  Grid,
  TextField,
  Box,
  Typography,
  Alert,
  Paper,
  Chip,
  Divider,
  Card,
  CardContent,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Groups as GroupsIcon,
  Engineering as EngineeringIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';
import { StaticDatePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format, differenceInDays, getYear } from 'date-fns';
import NavigationButtons from '../components/wizard/NavigationButtons';
import { useWizard } from '../context/WizardContext';

/**
 * Step 1: Setup
 *
 * Collects:
 * - Metadata (problemId, description)
 * - Employee model selection (Team vs Competency)
 * - Temporal scope (year, numDays, date range)
 *
 * Layout: Two columns with left side for metadata+model, right side for calendar
 */
const Step1_Setup = () => {
  const { state, updateState } = useWizard();
  const [errors, setErrors] = useState({});

  // Extract values from state
  const { problemId, description } = state.metadata;
  const { year, numDays, targetPeriod } = state.temporalScope;
  const selectedModel = state.employees.model;

  // Local state for date range picker
  const [startDate, setStartDate] = useState(
    targetPeriod.start ? new Date(targetPeriod.start) : null
  );
  const [endDate, setEndDate] = useState(
    targetPeriod.end ? new Date(targetPeriod.end) : null
  );
  const [selectingStart, setSelectingStart] = useState(true);

  // Auto-calculate year and numDays when dates change
  useEffect(() => {
    if (startDate && endDate) {
      const calculatedYear = getYear(startDate);
      const calculatedDays = differenceInDays(endDate, startDate) + 1;

      updateState('temporalScope.year', calculatedYear);
      updateState('temporalScope.numDays', calculatedDays);
    }
  }, [startDate, endDate]);

  // Handlers
  const handleProblemIdChange = (e) => {
    updateState('metadata.problemId', e.target.value);
    if (errors.problemId) {
      setErrors({ ...errors, problemId: null });
    }
  };

  const handleDescriptionChange = (e) => {
    updateState('metadata.description', e.target.value);
  };

  const handleModelSelect = (model) => {
    updateState('employees.model', model);
    if (errors.model) {
      setErrors({ ...errors, model: null });
    }
  };

  // Handle date selection from single calendar
  const handleDateChange = (date) => {
    if (!date) return;

    if (selectingStart || !startDate) {
      setStartDate(date);
      const formatted = format(date, 'yyyy-MM-dd');
      updateState('temporalScope.targetPeriod.start', formatted);
      setSelectingStart(false);

      if (endDate && date > endDate) {
        setEndDate(null);
        updateState('temporalScope.targetPeriod.end', '');
      }

      if (errors.startDate) {
        setErrors({ ...errors, startDate: null });
      }
    } else {
      if (date >= startDate) {
        setEndDate(date);
        const formatted = format(date, 'yyyy-MM-dd');
        updateState('temporalScope.targetPeriod.end', formatted);

        if (errors.endDate) {
          setErrors({ ...errors, endDate: null });
        }
      }
    }
  };

  // Reset date range selection
  const handleResetDateRange = () => {
    setStartDate(null);
    setEndDate(null);
    setSelectingStart(true);
    updateState('temporalScope.targetPeriod.start', '');
    updateState('temporalScope.targetPeriod.end', '');
    updateState('temporalScope.year', new Date().getFullYear());
    updateState('temporalScope.numDays', 0);
  };

  // Employee model options
  const modelOptions = [
    {
      value: 'team',
      title: 'Team-Based',
      description: 'Fixed teams or departments',
      icon: GroupsIcon,
      tooltip: 'Employees belong to fixed teams (e.g., Team A, Team B). Simpler and ideal for organizations with clear departmental structures.',
      color: 'primary.main'
    },
    {
      value: 'competency',
      title: 'Competency-Based',
      description: 'Skills with proficiency levels',
      icon: EngineeringIcon,
      tooltip: 'Employees have specific skills or competencies with proficiency levels. More flexible and ideal for skill-based scheduling.',
      color: 'primary.main'
    }
  ];

  // Validation
  const validate = () => {
    const newErrors = {};

    if (!problemId.trim()) {
      newErrors.problemId = 'Problem ID is required';
    }

    if (!startDate) {
      newErrors.startDate = 'Start date is required';
    }

    if (!endDate) {
      newErrors.endDate = 'End date is required';
    }

    if (startDate && endDate && endDate < startDate) {
      newErrors.dateRange = 'End date must be after start date';
    }

    if (!selectedModel || selectedModel === '') {
      newErrors.model = 'Employee model selection is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    return validate();
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{
        height: 'calc(100vh - 280px)',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* HEADER - Fixed */}
        <Box sx={{ flexShrink: 0, mb: 2 }}>
          <Typography variant="h4" gutterBottom fontWeight={600}>
            Setup
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Define the basics: problem details, employee model, and scheduling period.
          </Typography>
        </Box>

        {/* CONTENT - Scrollable */}
        <Box sx={{
          flexGrow: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          pr: 1 // Small padding for scrollbar
        }}>
          {/* Two-Column Layout */}
          <Grid container spacing={4}>
          {/* LEFT COLUMN - Metadata + Employee Model */}
          <Grid item xs={12} md={5}>
            {/* Problem Metadata */}
            <Box sx={{ mb: 3 }}>
              <TextField
                fullWidth
                label="Problem ID"
                value={problemId}
                onChange={handleProblemIdChange}
                error={!!errors.problemId}
                helperText={errors.problemId || 'Unique identifier (e.g., COMPANY_OCTOBER_2025)'}
                required
                placeholder="EXAMPLE_JAN_2026"
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Description"
                value={description}
                onChange={handleDescriptionChange}
                helperText="Brief description of this scheduling problem"
                placeholder="Monthly schedule for retail employees..."
              />
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Employee Model Selection */}
            <Box>
              <Typography variant="h6" gutterBottom fontWeight={600}>
                Employee Model
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Choose how employees are organized:
              </Typography>

              {errors.model && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {errors.model}
                </Alert>
              )}

              <Grid container spacing={2}>
                {modelOptions.map((option) => {
                  const Icon = option.icon;
                  const isSelected = selectedModel === option.value;

                  return (
                    <Grid item xs={12} key={option.value}>
                      <Card
                        onClick={() => handleModelSelect(option.value)}
                        sx={{
                          cursor: 'pointer',
                          position: 'relative',
                          border: isSelected ? '2px solid' : '1px solid',
                          borderColor: isSelected ? option.color : 'divider',
                          boxShadow: isSelected ? 2 : 0,
                          transition: 'all 0.2s ease',
                          '&:hover': {
                            borderColor: option.color,
                            boxShadow: 1
                          }
                        }}
                      >
                        {/* Info Icon */}
                        <Tooltip title={option.tooltip} arrow placement="top">
                          <IconButton
                            sx={{
                              position: 'absolute',
                              top: 8,
                              right: 8,
                              color: 'text.secondary',
                              '&:hover': { color: option.color }
                            }}
                            onClick={(e) => e.stopPropagation()}
                            size="small"
                          >
                            <InfoIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>

                        {/* Selected Indicator */}
                        {isSelected && (
                          <CheckCircleIcon
                            sx={{
                              position: 'absolute',
                              top: 8,
                              left: 8,
                              color: option.color,
                              fontSize: 24
                            }}
                          />
                        )}

                        <CardContent
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            py: 2,
                            px: 2
                          }}
                        >
                          <Icon
                            sx={{
                              fontSize: 40,
                              color: isSelected ? option.color : 'text.secondary',
                              mr: 2
                            }}
                          />
                          <Box sx={{ flexGrow: 1 }}>
                            <Typography
                              variant="subtitle1"
                              fontWeight={600}
                              sx={{ color: isSelected ? option.color : 'text.primary' }}
                            >
                              {option.title}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {option.description}
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            </Box>
          </Grid>

          {/* VERTICAL DIVIDER */}
          <Grid
            item
            xs={12}
            md="auto"
            sx={{
              display: { xs: 'none', md: 'flex' },
              justifyContent: 'center'
            }}
          >
            <Divider orientation="vertical" flexItem />
          </Grid>

          {/* Horizontal divider for mobile */}
          <Grid item xs={12} sx={{ display: { xs: 'block', md: 'none' } }}>
            <Divider />
          </Grid>

          {/* RIGHT COLUMN - Calendar */}
          <Grid item xs={12} md={6} sx={{ overflow: 'hidden' }}>
            <Box sx={{ position: 'relative' }}>
              <Typography variant="h6" gutterBottom fontWeight={600}>
                Scheduling Period
              </Typography>

              {/* Instructions */}
              <Box sx={{ mb: 2, textAlign: 'center', justifyContent: 'center', display: 'flex' }}>
                <Typography variant="body2" color="text.secondary">
                  {selectingStart || !startDate
                    ? 'Click to select the start date'
                    : !endDate
                    ? 'Now select the end date'
                    : 'Date range selected'}
                </Typography>
              </Box>

              {/* Calendar - Fixed with padding for content below */}
              <Box sx={{ pb: '90px' }}>
                <Paper
                  elevation={0}
                  sx={{
                    border: (theme) => `1px solid ${theme.palette.divider}`,
                    borderColor: errors.startDate || errors.endDate ? 'error.main' : 'divider'
                  }}
                >
                  <StaticDatePicker
                    displayStaticWrapperAs="desktop"
                    value={selectingStart ? startDate : endDate}
                    onChange={handleDateChange}
                    minDate={selectingStart ? undefined : startDate}
                    slotProps={{
                      actionBar: { actions: [] }
                    }}
                  />
                </Paper>
              </Box>

              {/* Date Chips - Absolutely positioned */}
              <Box sx={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
                {startDate && (
                  <Chip
                    label={`Start: ${format(startDate, 'MMM dd, yyyy')}`}
                    color="primary"
                    variant="outlined"
                  />
                )}
                {endDate && (
                  <Chip
                    label={`End: ${format(endDate, 'MMM dd, yyyy')}`}
                    color="primary"
                    variant="outlined"
                  />
                )}
                {startDate && endDate && (
                  <>
                    <Chip label={`${numDays} days`} color="success" size="small" />
                    <Chip label={`Year: ${year}`} color="info" size="small" />
                  </>
                )}
                {startDate && (
                  <Chip
                    label="Reset"
                    onClick={handleResetDateRange}
                    onDelete={handleResetDateRange}
                    size="small"
                    variant="outlined"
                  />
                )}
              </Box>
            </Box>
          </Grid>
        </Grid>
        </Box>

        {/* NAVIGATION - Fixed at bottom */}
        <Box sx={{ flexShrink: 0, mt: 2 }}>
          <NavigationButtons onNext={handleNext} nextDisabled={false} />
        </Box>
      </Box>
    </LocalizationProvider>
  );
};

export default Step1_Setup;

import React, { useState } from 'react';
import {
  Stepper,
  Step,
  StepLabel,
  StepButton,
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Alert,
  List,
  ListItem,
  ListItemText
} from '@mui/material';
import {
  CheckCircle,
  RadioButtonUnchecked,
  Info,
  Assignment,
  Business,
  People,
  CalendarMonth,
  AccessTime,
  EventNote,
  Rule,
  Settings,
  Preview,
  Warning as WarningIcon
} from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';
import { themeConfig } from '../../theme.config';

/**
 * WizardStepper - Main stepper component showing all 10 steps
 *
 * Displays progress and allows navigation to any step with validation warnings
 */

// Step icons
const stepIcons = {
  0: Info,
  1: Assignment,
  2: Business,
  3: People,
  4: CalendarMonth,
  5: AccessTime,
  6: EventNote,
  7: Rule,
  8: Settings,
  9: Preview
};

const steps = [
  { label: 'Setup', description: 'Metadata & models & dates' },
  { label: 'Contracts', description: 'Contract types' },
  { label: 'Org Units', description: 'Teams/Competencies' },
  { label: 'Employees', description: 'Employee roster' },
  { label: 'Schedule Input', description: 'Availability matrix' },
  { label: 'Work Periods', description: 'Shift definitions' },
  { label: 'Demand', description: 'Coverage requirements' },
  { label: 'Constraints', description: 'Rules & constraints' },
  { label: 'Optimization', description: 'Solver settings' },
  { label: 'Review', description: 'Generate files' }
];

const WizardStepper = () => {
  const { state, navigateToStep, goToStep } = useWizard();
  const { currentStep, stepCompleted } = state;

  const [navigationWarningOpen, setNavigationWarningOpen] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState(null);
  const [validationErrors, setValidationErrors] = useState([]);

  const handleStepClick = (targetStep) => {
    // If clicking current step, do nothing
    if (targetStep === currentStep) {
      return;
    }

    // Try to navigate with validation
    const result = navigateToStep(targetStep, false);

    if (result.success) {
      // Navigation successful (no validation errors)
      return;
    }

    // Check validation result
    if (result.validation && !result.validation.valid && result.validation.errors.length > 0) {
      // Show warning dialog
      setPendingNavigation(targetStep);
      setValidationErrors(result.validation.errors);
      setNavigationWarningOpen(true);
    } else {
      // No validation errors, navigate immediately
      goToStep(targetStep);
    }
  };

  const handleConfirmNavigation = () => {
    // Navigate without validation
    navigateToStep(pendingNavigation, true);
    setNavigationWarningOpen(false);
    setPendingNavigation(null);
    setValidationErrors([]);
  };

  const handleCancelNavigation = () => {
    setNavigationWarningOpen(false);
    setPendingNavigation(null);
    setValidationErrors([]);
  };

  const getStepIcon = (step) => {
    const Icon = stepIcons[step];
    const isCompleted = stepCompleted[step];
    const isCurrent = currentStep === step;

    let color = themeConfig.custom.stepperInactive;
    if (isCompleted) {
      color = themeConfig.custom.stepperCompleted;
    } else if (isCurrent) {
      color = themeConfig.custom.stepperActive;
    }

    return (
      <Box sx={{ display: 'flex', alignItems: 'center', color }}>
        <Icon />
      </Box>
    );
  };

  return (
    <Box sx={{ width: '100%', mb: 4 }}>
      <Stepper activeStep={currentStep} alternativeLabel>
        {steps.map((step, index) => {
          const isCompleted = stepCompleted[index];

          return (
            <Step key={step.label} completed={isCompleted}>
              <StepButton
                onClick={() => handleStepClick(index)}
                sx={{
                  '& .MuiStepLabel-label': {
                    fontSize: '0.875rem',
                    fontWeight: index === currentStep ? 600 : 400
                  },
                  cursor: 'pointer'
                }}
              >
                <StepLabel
                  StepIconComponent={() => getStepIcon(index)}
                  optional={
                    <Typography variant="caption" color="text.secondary">
                      {step.description}
                    </Typography>
                  }
                >
                  {step.label}
                </StepLabel>
              </StepButton>
            </Step>
          );
        })}
      </Stepper>

      {/* Navigation Warning Dialog */}
      <Dialog
        open={navigationWarningOpen}
        onClose={handleCancelNavigation}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" />
          Current Step Has Validation Errors
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            The current step (<strong>{steps[currentStep].label}</strong>) has the following validation errors:
          </DialogContentText>

          <Alert severity="warning" sx={{ mb: 2 }}>
            <List dense disablePadding>
              {validationErrors.map((error, index) => (
                <ListItem key={index} disablePadding>
                  <ListItemText
                    primary={`• ${error}`}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              ))}
            </List>
          </Alert>

          <DialogContentText>
            Do you want to navigate to <strong>{steps[pendingNavigation]?.label}</strong> anyway?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelNavigation} variant="contained" color="inherit">
            Stay Here
          </Button>
          <Button onClick={handleConfirmNavigation} variant="contained" color="warning">
            Navigate Anyway
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WizardStepper;

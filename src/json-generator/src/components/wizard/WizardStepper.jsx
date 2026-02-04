import React from 'react';
import { Stepper, Step, StepLabel, StepButton, Box, Typography } from '@mui/material';
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
  Preview 
} from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';
import { themeConfig } from '../../theme.config';

/**
 * WizardStepper - Main stepper component showing all 10 steps
 *
 * Displays progress and allows navigation to completed steps
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
  { label: 'Setup', description: 'Metadata & model & dates' },
  { label: 'Contracts', description: 'Contract types' },
  { label: 'Org Units', description: 'Teams/Competencies' },
  { label: 'Employees', description: 'Employee roster' },
  { label: 'Schedule Input', description: 'Availability matrix' },
  { label: 'Shifts', description: 'Shift definitions' },
  { label: 'Demand', description: 'Coverage requirements' },
  { label: 'Constraints', description: 'Rules & constraints' },
  { label: 'Optimization', description: 'Solver settings' },
  { label: 'Review', description: 'Generate files' }
];

const WizardStepper = () => {
  const { state, goToStep } = useWizard();
  const { currentStep, stepCompleted } = state;

  const handleStepClick = (step) => {
    // Allow navigation to current step, previous steps, or next step if current is completed
    if (step <= currentStep || (step === currentStep + 1 && stepCompleted[currentStep])) {
      goToStep(step);
    }
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
          const canNavigate = index <= currentStep || (index === currentStep + 1 && stepCompleted[currentStep]);

          return (
            <Step key={step.label} completed={isCompleted}>
              <StepButton
                onClick={() => handleStepClick(index)}
                disabled={!canNavigate}
                sx={{
                  '& .MuiStepLabel-label': {
                    fontSize: '0.875rem',
                    fontWeight: index === currentStep ? 600 : 400
                  }
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
    </Box>
  );
};

export default WizardStepper;

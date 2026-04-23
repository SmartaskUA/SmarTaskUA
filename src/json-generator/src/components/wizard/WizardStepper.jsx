import React from 'react';
import {
  Stepper,
  Step,
  StepLabel,
  StepButton,
  Box,
  Typography
} from '@mui/material';
import {
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
  { label: 'Setup',          description: 'Metadata & models & dates' },
  { label: 'Contracts',      description: 'Contract types' },
  { label: 'Org Units',      description: 'Teams/Competencies' },
  { label: 'Employees',      description: 'Employee roster' },
  { label: 'Schedule Input', description: 'Availability matrix' },
  { label: 'Work Periods',   description: 'Work period definitions' },
  { label: 'Demand',         description: 'Coverage requirements' },
  { label: 'Constraints',    description: 'Rules & constraints' },
  { label: 'Optimization',   description: 'Solver settings' },
  { label: 'Review',         description: 'Generate files' }
];

const WizardStepper = () => {
  const { state, goToStep } = useWizard();
  const { currentStep, stepCompleted } = state;

  const primary = themeConfig.custom.stepperActive;

  const getStepIcon = (index) => {
    const Icon = stepIcons[index];
    const isCompleted = stepCompleted[index];
    const isCurrent = currentStep === index;

    let color = themeConfig.custom.stepperInactive;
    if (isCompleted) color = themeConfig.custom.stepperCompleted;
    else if (isCurrent) color = primary;

    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          color,
          fontSize: isCurrent ? '2rem' : '1.5rem',
          transition: 'font-size 0.15s ease'
        }}
      >
        <Icon fontSize="inherit" />
      </Box>
    );
  };

  return (
    <Box sx={{ width: '100%', mb: 4 }}>
      <Stepper activeStep={currentStep} alternativeLabel nonLinear sx={{ py: 2 }}>
        {steps.map((step, index) => {
          const isCompleted = stepCompleted[index];
          const isCurrent  = index === currentStep;

          return (
            <Step key={step.label} completed={isCompleted}>
              <StepButton
                onClick={() => { if (index !== currentStep) goToStep(index); }}
                sx={{
                  py: 1.5,
                  '& .MuiStepLabel-label': {
                    fontSize: isCurrent ? '0.9rem' : '0.875rem',
                    fontWeight: isCurrent ? 700 : 400,
                    color: isCurrent ? primary : 'inherit'
                  }
                }}
              >
                <StepLabel
                  StepIconComponent={() => getStepIcon(index)}
                  optional={
                    <Typography variant="caption" color={isCurrent ? primary : 'text.secondary'}>
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

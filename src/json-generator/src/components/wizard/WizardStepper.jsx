import React from 'react';
import {
  Stepper,
  Step,
  StepLabel,
  StepButton,
  Box,
  Typography
} from '@mui/material';
import { useWizard } from '../../context/WizardContext';
import { themeConfig } from '../../theme.config';
import { VISIBLE_STEPS } from '../../constants/wizardSteps';

const WizardStepper = () => {
  const { state, goToStep } = useWizard();
  const { currentStep, stepCompleted } = state;

  const primary = themeConfig.custom.stepperActive;

  // Map real step index to visible index (-1 when on a hidden step)
  const visibleIndex = VISIBLE_STEPS.findIndex(s => s.realIndex === currentStep);
  const activeVisibleStep = visibleIndex >= 0 ? visibleIndex : -1;

  const getStepIcon = (realIndex, isCurrent) => {
    const Icon = VISIBLE_STEPS.find(s => s.realIndex === realIndex)?.icon;
    if (!Icon) return null;

    const isCompleted = stepCompleted[realIndex];

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
      <Stepper activeStep={activeVisibleStep} alternativeLabel nonLinear sx={{ py: 2 }}>
        {VISIBLE_STEPS.map((step) => {
          const { realIndex } = step;
          const isCompleted = stepCompleted[realIndex];
          const isCurrent  = realIndex === currentStep;

          return (
            <Step key={step.label} completed={isCompleted}>
              <StepButton
                onClick={() => { if (realIndex !== currentStep) goToStep(realIndex); }}
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
                  StepIconComponent={() => getStepIcon(realIndex, isCurrent)}
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
